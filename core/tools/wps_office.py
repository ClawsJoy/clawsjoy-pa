# -*- coding: utf-8 -*-
"""wps_office 工具: PA 生成 PPT/Word 的统一入口(2026-09-10, provider=wpsai 落地)。

Provider 策略(按优先级自动选择):
  1. WPS_AI_URL(env) -> wpsai: 真实桌面 WPS(Windows) + 灵犀AI(WPS-AI) MCP 桥,
                        预设模板排版(cover/content/closing), 实证 WPS build 28505 可用
  2. WPS_MCP_URL(env) -> mcp: 社区 wps-mcp-server(FastMCP, 文件级 python-pptx 路线) [待接入客户端]
  3. WPS_CLI(env)     -> cli: 本地 WPS 命令行 [待接入]
  4. python-pptx      -> 确定性降级生成(无 WPS 环境兜底)     [可用]

wpsai 前置(调用前必须满足, 否则明确报错不假成功):
  - 网关可达 WPS-AI proxy(同机 127.0.0.1:3890 或 ssh -L 转发), env WPS_AI_URL/WPS_AI_TOKEN
  - WPS 演示正打开且【已保存】的空白演示文稿(1 页)作为工作区(灵犀拒绝未保存临时文档)
  - 生成期间保持 WPS 前台/不切宿主; 每调用 25s 超时, 首败即停(唯一例外: **读类**遇"宿主未命中"形状 ⇒ 有限重试; 写类不重试, 见 _wpsai_call_retry)
md 约定与 python-pptx 兜底一致: 顶层 '#' 或 '## P?N' 一页一条; 每条 bullet 压至 <=120 字
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from core.tools.base import ToolPlugin

WPS_OFFICE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "wps_office",
        "strict": True,
        "description": (
            "用 WPS/office 引擎生成或编辑文档(PPT/Word)。输入 markdown 大纲文件与目标格式, "
            "输出排版后的文件。优先真 WPS 排版(wpsai: 真实 WPS 预设模板 / mcp / cli); "
            "无 WPS 环境时确定性降级 python-pptx, 保证不溢出、结构完整。"
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action": {"type": "string", "enum": ["pptx_from_md", "docx_from_md"], "description": "动作"},
                "md_path": {"type": "string", "description": "源 markdown 文件(沙箱相对路径)"},
                "out_path": {
                    "type": "string",
                    "description": "输出文件路径(缺省 data/reports/同名 .pptx/.docx，锚定在执行沙箱下；绝对路径原样)"
                },
                "provider": {"type": "string", "description": "可选强制: auto/wpsai/mcp/cli/pptx"},
            },
            "required": ["action", "md_path"],
        },
    },
}

_MAX_BULLET = 120
_MAX_LINES = 8


def _detect_provider(forced="auto"):
    if forced and forced != "auto":
        return forced
    if os.getenv("WPS_AI_URL"):
        return "wpsai"
    if os.getenv("WPS_MCP_URL"):
        return "mcp"
    if os.getenv("WPS_CLI"):
        return "cli"
    return "pptx"


# ---------- md -> deck plan (纯函数, 双路线共用) ----------


def plan_from_md(text):
    """把 md 切成页: [{'title': str, 'lines': [str,...]}]; '#'/'## P?N' 起新页。"""
    pages = []
    cur = None
    for ln in text.splitlines():
        s = ln.strip()
        m2 = re.match(r"^##\s*P?(\d*)\s*(.*)$", s)
        m1 = re.match(r"^#\s*(.*)$", s)
        m = m2 or m1
        if m and (s.startswith("##") or s.startswith("# ")):
            if cur:
                pages.append(cur)
            t = m.group(2) if m2 else m.group(1)
            t = re.sub(r"^(P?\d+)\s*[｜|]?\s*", "", (t or "").strip())
            cur = {"title": (t or s.lstrip("# ").strip())[:80], "lines": []}
        elif cur is not None and s and not s.startswith("#"):
            cur["lines"].append(s)
    if cur:
        pages.append(cur)
    return pages


def _clean_lines(lines):
    out = []
    for b in lines:
        b2 = re.sub(r"^[-•*>\s]*", "", b).strip()
        if b2 and len(out) < _MAX_LINES:
            out.append(b2[:_MAX_BULLET])
    return out


def _template_kind(index, total, page):
    title = page["title"]
    if index == 1:
        return "cover-split"
    if index == total and re.search(r"谢谢|结尾|Q\s*&\s*A|下一步|行动|收尾", title):
        return "closing-thanks"
    return "content-sidebar"


def _template_args(kind, page):
    lines = _clean_lines(page["lines"])
    body = "\n".join(lines)
    if kind == "cover-split":
        # 封面: 标题留大, 副题取第一条 bullet(有 '|' 则取其后半)
        subtitle = ""
        if lines:
            subtitle = lines[0]
            if "|" in subtitle:
                subtitle = subtitle.split("|", 1)[1].strip()
        return {"title": page["title"], "subtitle": subtitle[:_MAX_BULLET]}
    if kind == "closing-thanks":
        return {"title": page["title"], "subtitle": lines[0] if lines else ""}
    return {"title": page["title"], "body": body}


# ---------- wpsai 驱动(HTTP 桥, 协议实证自 proxy-server.js) ----------


def _wpsai_base():
    return os.getenv("WPS_AI_URL", "http://127.0.0.1:3890").rstrip("/")


def _wpsai_token():
    return os.getenv("WPS_AI_TOKEN", "")


def _wpsai_http(method, path, body=None, timeout=25):
    url = _wpsai_base() + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    tok = _wpsai_token()
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"ok": False, "error": raw[:300]}
    except Exception as e:
        return -1, {"ok": False, "error": "WPS-AI 连接失败: %s" % str(e)[:150]}


def _wpsai_call(name, args, timeout=25):
    st, body = _wpsai_http("POST", "/mcp/call", {"name": name, "args": args}, timeout=timeout)
    return st, body


# ---------- 宿主未命中兼容层(2026-09-19 · 本线 · v2 收窄) ----------
# 根因(只读实证): 灵犀桥(plugin-wps proxy-server.js)在多 add-in 连接之间"轮流派发",
#   落到非目标宿主的请求其 Application.ActivePresentation 为 null ⇒ 报"未检测到打开的 WPS 演示"。
#   实测: wpp_* 连打 12 次 = 恰好 6 成 6 败; get_host_info 连打 12 次严格交替(wps<->wpp)。
# 判据: 同一工具连打 N 次 host 必须恒定; 现网不恒定 ⇒ 红(桥侧根因仍在, 本层只是兼容层)。
#
# v2 收窄三处(DSH 初审 198a63b8 危险方向 ②③⑤; 另修 ④):
#   ① **只给读类重试**(调用方显式 retry_ok=True); 写类**一律不重试** —— 重试会把写搬到
#      **另一个宿主**上, 而起点校验过的"空白工作区"只属于起点那个宿主 ⇒ 可能改到别的实例里
#      开着的真实文件; `wpp_delete_slide` 还非幂等。**写类 = 硬闸: 无开关可开**(见下行 v3)。
# v3(2026-09-19 · DSH 二轮 38286268 §三-8「库层死开关」): 删 `WPS_AI_RETRY_WRITES`。
#   原因: 产品路径的三处写(模板/删页/另存)本来就**不接**重试层 ⇒ 那个 env 零消费 = 死开关,
#   而"开了也不生效"会被下一个人读成设计。现行口径 = 「写类永不重试」; 要恢复写类重试, 必须
#   先有宿主粘性/幂等判据(见未覆盖面 3/4), 而不是先有这个开关。
#   ② 形状判据从"**包含**"收紧为"**以之为首**" —— 反例: error="保存失败：未检测到打开的 WPS 演示"
#      本质是**保存失败**, 含目标子串却不是宿主未命中 ⇒ 旧写法会去重试一个写调用。
#   ③ 重试上限解析失败一律落 **1**(fail-closed, 不再 fail-open 回落 3); 要开读类重试须显式设 >=2。
# 回退开关: WPS_AI_RETRY_ATTEMPTS=1 ⇒ 读类也不重试 = 改前口径(逐项一致, 由复算器 A' 格钉住)。
_HOST_MISS_MARK = "未检测到打开的 WPS 演示"


def _wpsai_retry_attempts():
    try:
        n = int(os.getenv("WPS_AI_RETRY_ATTEMPTS", "3"))
    except Exception:
        n = 1
    return max(1, n)


def _is_host_miss(body):
    """形状判据(收窄版): **以**标记为首**才算宿主未命中(不是包含)。"""
    return str(body.get("error") or "").strip().startswith(_HOST_MISS_MARK)


def _wpsai_call_retry(name, args, timeout=25, attempts=None, retry_ok=False):
    """只在"宿主未命中"形状上重试的调用层; 返回 (status, body, 重试次数)。

    retry_ok: 调用方**声明这是读类**(只读、可安全重做)。
              **False ⇒ 永不重试**(写类硬闸 · 无 env 开关 · v3)。
    """
    if not retry_ok:
        st, body = _wpsai_call(name, args, timeout=timeout)
        return st, body, 0
    n = _wpsai_retry_attempts() if attempts is None else max(1, int(attempts))
    used = 0
    st, body = -1, {}
    for i in range(1, n + 1):
        st, body = _wpsai_call(name, args, timeout=timeout)
        if st == 200 and body.get("ok"):
            return st, body, used
        if not _is_host_miss(body) or i >= n:
            return st, body, used
        used += 1
        time.sleep(0.4)
    return st, body, used


def _win_path(linux_path):
    """把 /mnt/c /mnt/d 相对输出路径翻译成 Windows 路径(供 WPS 写盘)。"""
    p = str(linux_path).replace("/", "\\")
    if p.startswith("\\mnt\\c\\"):
        return "C:" + p[len("\\mnt\\c") :]
    if p.startswith("\\mnt\\d\\"):
        return "D:" + p[len("\\mnt\\d") :]
    return ""


def _require_alive():
    st, body = _wpsai_http("GET", "/mcp/status")
    if st != 200 or not body.get("ok") or not body.get("pluginAlive"):
        return False, "WPS-AI proxy/plugin 不在线(status=%s): 请确认 WPS 打开且 MCP 服务开启" % st
    return True, ""


def _require_clean_workspace():
    """要求 WPS 演示打开且已保存的空白工作区(<=2 页且正文为空), 避免误写真实文件。"""
    st, body, host_retries = _wpsai_call_retry("wpp_get_presentation_info", {}, retry_ok=True)
    if st != 200 or not body.get("ok"):
        return False, body.get("error") or "未检测到打开的 WPS 演示(请先 Ctrl+S 保存空白演示文稿并保持前台)"
    info = body.get("value") or {}
    if info.get("saved") is False:
        return False, "当前演示未保存: 灵犀拒绝未落盘临时文档, 请先在 WPS 演示里 Ctrl+S 保存"
    total = int(info.get("slideCount") or 0)
    if total < 1 or total > 2:
        return False, "工作区应只有 1 张空白页(当前 %d 页): 请新建并保存空白演示文稿" % total
    for i in range(1, total + 1):
        st2, b2, _r2 = _wpsai_call_retry("wpp_read_slide", {"index": i}, retry_ok=True)
        shapes = ((b2.get("value") or {}).get("shapes") or []) if b2.get("ok") else []
        for s in shapes:
            if (s.get("text") or "").strip():
                return False, "工作区第 %d 页含已有内容, 请新建空白演示文稿避免误写" % i
    return True, {"initial": total, "host_miss_retries": host_retries}


def _pptx_from_md_wpsai(pages, out_path):
    """真 WPS 排版: 预检 -> 逐页 apply_template -> 删工作区空白页 -> save_as。"""
    ok, msg = _require_alive()
    if not ok:
        return {"success": False, "error": msg}
    ok, msg = _require_clean_workspace()
    if not ok:
        return {"success": False, "error": msg}
    initial = msg["initial"]

    win_out = _win_path(out_path)
    if not win_out:
        win_out = os.getenv("WPS_AI_OUT_DIR", "C:\\Users\\flybo\\Desktop") + "\\" + Path(out_path).name

    total = len(pages)
    try:
        for i, page in enumerate(pages, 1):
            kind = _template_kind(i, total, page)
            args = _template_args(kind, page)
            args["templateName"] = kind
            st, body = _wpsai_call("wpp_apply_template", args)   # 写类: 不重试(v2 收窄①)
            if st != 200 or not body.get("ok"):
                return {"success": False, "error": "第 %d 页模板失败: %s" % (i, body.get("error") or ("HTTP %d" % st))}
        for _ in range(initial):
            st_d, body_d = _wpsai_call("wpp_delete_slide", {"index": 1})
            if st_d != 200 or not body_d.get("ok"):
                return {"success": False, "error": "删除工作区占位页失败(不冒充成功): %s" % (body_d.get("error") or ("HTTP %d" % st_d))}
        st, body = _wpsai_call("wpp_save_as", {"path": win_out, "format": "pptx"})   # 写类: 不重试
        if st != 200 or not body.get("ok"):
            return {"success": False, "error": "另存失败: %s" % (body.get("error") or ("HTTP %d" % st))}

        st_v, body_v, _rv = _wpsai_call_retry("wpp_get_presentation_info", {}, retry_ok=True)
        got = -1
        if st_v == 200 and body_v.get("ok"):
            got = int((body_v.get("value") or {}).get("slideCount") or -1)
        if got != total:
            return {"success": False, "error": "产物页数核对未过: 期望 %d 页, 实读 %s(读回失败或页数不符) —— 不冒充成功" % (total, got)}
    except Exception as e:
        return {"success": False, "error": "wpsai 排版中断: %s" % str(e)[:200]}

    mirrored = _win_path(out_path) != ""
    return {
        "success": True,
        "wps_path": win_out,
        "mirrored": mirrored,
        "out_path": str(out_path) if mirrored else "",
        "provider": "wpsai",
        "pages": total,
    }


def _pptx_from_md(md_path, out_path):
    """确定性降级: python-pptx(结构完整: bullet<=120 字, 每页<=8 条)。"""
    from pptx import Presentation

    text = Path(md_path).read_text(encoding="utf-8")
    pages = plan_from_md(text)
    prs = Presentation()
    for i, page in enumerate(pages or [], 1):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        try:
            slide.shapes.title.text = page["title"][:80] or ("P%d" % i)
        except Exception:
            pass
        body = slide.placeholders[1].text_frame
        body.clear()
        first = True
        for b in _clean_lines(page["lines"]):
            para = body.paragraphs[0] if first else body.add_paragraph()
            first = False
            para.text = b
            para.level = 1
    prs.save(out_path)
    return out_path, len(pages)


def _is_abs_out_path(p):
    """绝对路径判据：posix 绝对 / UNC / Windows 盘符都要认（勿用 Path.is_absolute）。"""
    s = str(p or "")
    if s.startswith("/") or s.startswith("\\"):
        return True
    return len(s) > 1 and s[1] == ":"


def _join_base(base, rel):
    """把相对路径锚定到 base 下；剥掉重复的 clawsjoy_dev/ 前缀（防双重嵌套）。"""
    r = str(rel or "").replace("\\", "/").strip()
    b = str(base or "").strip()
    if not b:
        return r
    while r.startswith("./"):
        r = r[2:]
    while r.startswith("clawsjoy_dev/"):
        r = r[len("clawsjoy_dev/"):]
    return str(Path(b) / r)


def _resolve_out_path(out_path, action, md_path, base):
    """输出落点必须与输入同根。

    历史缺陷：缺省为裸相对路径 ⇒ 落点随**调用进程 cwd** 漂移（活进程 cwd=仓库根、沙箱
    进程 cwd=沙箱）⇒ 同一产品分裂到两个根（实测 2026-09-11 18:30 `pa_mtuu37ds`：md 在
    沙箱、pptx 在仓库根；`data/v8/audit/tool_audit.jsonl:3976` 与文件 mtime 差 5ms）。
    规则：base 已知 ⇒ 缺省与**显式相对路径**都锚定在 base 下；绝对路径（含盘符/UNC）原样；
    base 未知 ⇒ 保持旧行为（缺省裸相对路径），不臆造根。
    """
    stem = Path(str(md_path or "")).stem
    default_name = "data/reports/%s.%s" % (stem, "pptx" if action == "pptx_from_md" else "docx")
    p = str(out_path or "").strip()
    if not p:
        return _join_base(base, default_name)
    if _is_abs_out_path(p):
        return p
    return _join_base(base, p)


def execute_wps_office(action, md_path, out_path="", provider="auto", base=""):
    """确定性入口(供插件与上层直接调用)。返回 {success, out_path, provider, pages|error}。

    out_path 统一走 _resolve_out_path：base(执行沙箱)已知 ⇒ 缺省与显式相对路径都
    锚定在 base 下（与输入同根）；绝对路径原样；base 未知 ⇒ 保持缺省裸相对路径。
    """
    md_path = str(md_path or "")
    if not md_path:
        return {"success": False, "error": "wps_office 需要 md_path"}
    if base:
        cand = Path(str(base)) / md_path
        if cand.exists():
            md_path = str(cand)
    if not Path(md_path).exists():
        return {"success": False, "error": "源文件不存在: %s" % md_path}
    prov = _detect_provider(provider)
    out_path = _resolve_out_path(out_path, action, md_path, base)
    if action != "pptx_from_md":
        return {"success": False, "error": "docx_from_md 待接入; 当前仅 pptx_from_md"}
    try:
        if prov == "pptx":
            out, n = _pptx_from_md(md_path, out_path)
            return {"success": True, "out_path": str(out), "provider": "python-pptx", "pages": n}
        if prov == "wpsai":
            text = Path(md_path).read_text(encoding="utf-8")
            pages = plan_from_md(text)
            if not pages:
                return {"success": False, "error": "md 无页面结构(需要 '#' 或 '## P?N' 标题)"}
            return _pptx_from_md_wpsai(pages, out_path)
        return {
            "success": False,
            "error": "provider=%s 需要真实 WPS 环境(WPS-AI MCP 桥或 wps-mcp-server/WPS_CLI); "
            "headless Linux 无 WPS, 请设 WPS_AI_URL/WPS_AI_TOKEN 或改用 provider=pptx 兜底" % prov,
        }
    except Exception as e:
        return {"success": False, "error": "wps_office 失败: %s" % str(e)[:200]}


class WpsOfficePlugin(ToolPlugin):
    name = "wps_office"
    quota = 5
    schema = WPS_OFFICE_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        action = str((args or {}).get("action") or "")
        md_path = str((args or {}).get("md_path") or "")
        out_path = str((args or {}).get("out_path") or "")
        provider = str((args or {}).get("provider") or "auto")
        base = getattr(ctx, "base", None)
        return execute_wps_office(action, md_path, out_path=out_path, provider=provider, base=str(base) if base else "")
