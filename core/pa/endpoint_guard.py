# -*- coding: utf-8 -*-
"""本地服务端点强制门（2026-09-10）

【事故驱动】做能力发现时，我用脚本对 3890 代理的每个候选路径都发了 POST {}，
其中 POST /kv/clear 无参数即清空全部键值 → 灵犀插件配置库 8 条全灭
(含老板的 provider 配置与对话历史)。事后用 sqlite3 .recover 全量找回，但那不是
每次都能救回来的。

【根因】把"能力发现"当成了无副作用的读操作。破坏性端点混在普通端点里，瞎探就会打到。

【本模块的规矩】
  1. 只读优先: 未知端点只允许 GET。非 GET 命中未登记路径 → **默认拒绝**
  2. 破坏性端点(删除/清空/覆盖/恢复) → 必须先在场的显式授权, 否则拒绝
  3. 写端点 → 放行但强制记账
  4. 每次调用(含被拒)都进审计, 让"谁在什么时候想动什么"可追溯

设计取舍: 拒绝是默认值。宁可拦住一个合法调用(有明确报错可循), 也不要放过一次静默破坏。
"""
import json
import logging
import time

log = logging.getLogger("pa.endpoint_guard")

# ---- 端点分级 -------------------------------------------------------------
# 破坏性: 删除 / 清空 / 覆盖写 / 恢复。一旦误调, 数据可能不可逆。
DESTRUCTIVE = (
    ("POST", "/kv/clear"),
    ("POST", "/doc-restore"),  # 覆盖写回文档
    ("POST", "/save-local-image-as"),  # 写本地文件
    ("POST", "/load-local-file"),  # 载入外部文件进文档
)

# 写: 会改变状态, 但通常是增量/可预期的
WRITE = (
    ("POST", "/kv/batch"),
    ("POST", "/kv/merge-list"),
    ("POST", "/kv/merge-object"),
    ("POST", "/mcp/register"),
    ("POST", "/mcp/result"),
    ("POST", "/upload-image"),
    ("POST", "/image-edit"),
    ("POST", "/toapis-upload-image"),
)

# 只读: 允许任意方法探测(但仍会被记账)
READ = (
    ("GET", "/mcp/status"),
    ("GET", "/mcp/tools"),
    ("GET", "/kv/all"),
    ("GET", "/kv/stats"),
    ("POST", "/doc-snapshot"),  # 生成快照=读文档(不覆盖原文), 实测需 docPath
    ("GET", "/active-pdf-path"),
    ("POST", "/fetch-web"),
    ("POST", "/fetch-remote-image"),
    ("POST", "/image-search"),
)

READ_PREFIXES = ("/asset/", "/forward/")

# ---- MCP 桥工具分级（2026-09-13, C 块）-------------------------------------
# 背景: /mcp/call 是灵犀桥的**唯一执行入口** —— 161 个工具（查页数/导出图/改页/删页）
# 全从这一个 POST 端点进出。按**路径**登记只有两种下场:
#   登记成 read/write -> wpp_delete_slide 这类破坏性工具被一并放行, 门形同虚设;
#   不登记(原状)      -> PA 连"查页数/导出缩略图"都做不了, 只能绕过门直连 3890(= 退回老路)。
# 两条都不能接受, 所以 /mcp/call 改为**按 body 里的工具名分级**:
#   读工具 -> read(放行) / 写工具 -> write(放行+记账) / 破坏性工具 -> destructive(需在场授权)
#   未登记的工具名 -> unknown(非 GET 默认拒绝), 与路径级同一条规矩: 拒绝是默认值。
# 注意: 这是"按内容分级", 不是"给 /mcp/call 开白名单" —— 门没有被绕开, 只是看得更细了。
MCP_CALL_PATH = "/mcp/call"

MCP_READ_TOOLS = frozenset(
    (
        "wpp_get_presentation_info",
        "wpp_list_slides",
        "wpp_read_slide",
        "wpp_get_notes",
        "wpp_read_comments",
        "wpp_doc_properties",
        "wpp_get_style_preset",
        "wpp_export_slide_as_image",
        "wpp_export_pdf",
        "et_get_sheet_info",
        "et_list_sheets",
        "et_read_range",
        "et_read_comments",
        "et_doc_properties",
        "et_export_pdf",
        "pdf_get_info",
        "pdf_read_document",
        "pdf_read_page",
        "get_host_info",
        "query_materials",
        "reveal_location",
        "web_fetch",
        "web_image_search",
    )
)

MCP_WRITE_TOOLS = frozenset(
    (
        "wpp_render_html_template",
        "wpp_render_full_deck",
        "wpp_render_chart",
        "wpp_save",
        "wpp_save_as",
        "wpp_add_slide",
        "wpp_add_picture",
        "wpp_add_text_box",
        "wpp_add_table",
        "wpp_add_shape",
        "wpp_add_media",
        "wpp_add_smartart",
        "wpp_add_section",
        "wpp_add_animation",
        "wpp_set_title",
        "wpp_set_notes",
        "wpp_set_slide_layout",
        "wpp_set_slide_background",
        "wpp_set_slide_transition",
        "wpp_set_table_cell",
        "wpp_set_action",
        "wpp_set_view",
        "wpp_apply_template",
        "wpp_apply_theme",
        "wpp_apply_style_preset",
        "wpp_apply_visual_template",
        "wpp_edit_html_slide",
        "wpp_replace_shape_text",
        "wpp_format_shape_text",
        "wpp_align_shapes",
        "wpp_move_slide",
        "wpp_duplicate_slide",
        "wpp_select_slide",
        "wpp_print",
        "generate_image",
        "save_skill",
        "et_write_range",
        "et_set_formula",
        "et_add_sheet",
        "et_rename_sheet",
        "et_insert_rows",
        "et_insert_columns",
        "et_insert_chart",
        "et_insert_image",
        "et_add_comment",
        "et_add_hyperlink",
        "et_save_as",
        "et_print",
    )
)

MCP_DESTRUCTIVE_TOOLS = frozenset(
    (
        "wpp_delete_slide",
        "wpp_delete_shape",
        "wpp_undo_full_deck_batch",
        "et_delete_sheet",
        "et_delete_rows",
        "et_delete_columns",
        "et_clear",
    )
)


def mcp_grant_key(tool):
    """MCP 破坏性工具的授权粒度键。

    为什么不能直接用 "/mcp/call": 那样一次授权会连带放行该路径下**所有**破坏性工具,
    "授权按端点隔离"就没了。所以粒度下沉到工具名: "/mcp/call#wpp_delete_slide"。
    """
    return MCP_CALL_PATH + "#" + str(tool or "").strip()


def classify_mcp_tool(name):
    """MCP 工具名 -> 'read' | 'write' | 'destructive' | 'unknown'"""
    n = (name or "").strip()
    if n in MCP_DESTRUCTIVE_TOOLS:
        return "destructive"
    if n in MCP_WRITE_TOOLS:
        return "write"
    if n in MCP_READ_TOOLS:
        return "read"
    return "unknown"


def classify(method, path, body=None):
    """端点分级 -> 'read' | 'write' | 'destructive' | 'unknown'

    body 仅用于 /mcp/call: 该端点的真实风险由 body.name(工具名) 决定, 不由路径决定。
    """
    m = (method or "GET").upper()
    p = (path or "").split("?")[0]
    if m == "POST" and p == MCP_CALL_PATH and isinstance(body, dict):
        return classify_mcp_tool(body.get("name"))
    for mm, pp in DESTRUCTIVE:
        if m == mm and p == pp:
            return "destructive"
    for mm, pp in WRITE:
        if m == mm and p == pp:
            return "write"
    for mm, pp in READ:
        if m == mm and p == pp:
            return "read"
    for pre in READ_PREFIXES:
        if p.startswith(pre):
            return "read"
    # 同路径但方法不同的只读条目: 也算已登记(GET 探测常见)
    for mm, pp in READ:
        if p == pp:
            return "read"
    return "unknown"


# ---- 在场授权（会话级，与浏览器治理门同源语义）----------------------------
_grants = {}  # user_id -> {"expires": ts, "paths": [...], "note": str}


def approve_destructive(user_id, path=None, ttl_s=1800, note=""):
    """老板在场授权: 允许在会话内调用破坏性端点。默认只授权被点名的那个端点。"""
    _grants[user_id] = {
        "expires": time.time() + float(ttl_s),
        "paths": [path] if path else [p for _, p in DESTRUCTIVE],
        "note": note,
        "ts": time.time(),
    }
    return {"ok": True, "paths": _grants[user_id]["paths"], "ttl_s": ttl_s}


def revoke(user_id):
    _grants.pop(user_id, None)
    return {"ok": True, "revoked": True}


def gate_state(user_id):
    g = _grants.get(user_id) or {}
    alive = bool(g) and g.get("expires", 0) > time.time()
    return {
        "approved": alive,
        "paths": g.get("paths", []) if alive else [],
        "expires_in": max(0, int(g.get("expires", 0) - time.time())) if alive else 0,
    }


def _grant_covers(user_id, path):
    g = _grants.get(user_id) or {}
    if not g or g.get("expires", 0) <= time.time():
        return False
    return path in (g.get("paths") or [])


def check(method, path, user_id="", body=None):
    """强制门。返回 (allowed: bool, level: str, reason: str)。

    - read        -> 放行
    - write       -> 放行(调用方负责记账)
    - destructive -> 需在场授权, 否则拒绝
    - unknown     -> GET 放行; 非 GET 一律拒绝(今天的坑就在这)

    body: 仅 /mcp/call 使用 —— 门按 body.name(工具名) 分级, 见 classify_mcp_tool。
    """
    level = classify(method, path, body)
    p = (path or "").split("?")[0]
    if level == "read":
        return True, level, ""
    if level == "write":
        return True, level, ""
    if level == "destructive":
        tool = (body or {}).get("name") if isinstance(body, dict) else None
        # MCP 破坏性工具按**工具名**授权, 不按路径 —— 否则一次授权放行一整条路径
        _is_mcp = (method or "GET").upper() == "POST" and p == MCP_CALL_PATH and bool(tool)
        key = mcp_grant_key(tool) if _is_mcp else p
        if _grant_covers(user_id, key):
            return True, level, "已授权"
        return False, level, ("破坏性端点 %s 需要老板在场授权: 先 approve_destructive()。" "本次未授权, 已拒绝执行。" % key)
    # unknown
    if (method or "GET").upper() == "GET":
        return True, level, "未登记路径的只读探测"
    return False, level, ("未登记端点 %s %s 默认拒绝(只读优先原则)。" "若确需调用, 请先登记到 endpoint_guard 并说明用途。" % (method, p))


def describe(method, path, user_id="", body=None):
    allowed, level, reason = check(method, path, user_id, body)
    return {"allowed": allowed, "level": level, "reason": reason, "method": (method or "GET").upper(), "path": path}
