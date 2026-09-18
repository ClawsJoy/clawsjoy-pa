# -*- coding: utf-8 -*-
"""PA 网关接线 v0(2026-09-10): 把 core.pa 暴露为 HTTP 服务层(/v9/pa/*)。

设计原则(老板拍板 2026-09-10):
  - 最小侵入: 网关只加 register_pa_routes(app) 一行; 本模块不 import 网关, 可独立单测
  - 聊天不是闲聊: dialog 走"任务目标导向"的就事论事(响应=画像brief+账本brief+本会话上下文)
  - 聊天模式不触发执行循环: /v9/pa/dialog 纯商量, 要干活走 /v9/pa/dispatch(带契约+代理审核)
  - 画像沉淀: 审美/情感/口径/禁忌 均可随手落档(emotion 域与 aesthetic 并列)

路由:
  GET  /v9/pa/context          画像+账本 brief(前端右栏)
  GET  /v9/pa/profile          画像条目(status/domain 过滤)
  POST /v9/pa/sediment         沉淀一条(domain/value/source/confidence/status)
  POST /v9/pa/dialog           追加式会话(随时打断/换话题), 可选 brain 注入 LLM
  GET  /v9/pa/dialog           会话历史(?user_id&session_id&n)
  GET  /v9/pa/ledger           账本
  POST /v9/pa/ledger/add       加待办
  POST /v9/pa/ledger/done      完成待办
  POST /v9/pa/dispatch         分派(契约->执行->代理审核)
  GET  /v9/pa/dispatch/history 分派历史
  POST /v9/pa/vault/sync       账本/站会/未读 同步到 Obsidian
  POST /v9/pa/archive         归档正文落服务端(X-11 层 1; 按 id 合并, 只写 archived, 写后读回确认)
  GET  /v9/pa/archive/<id>     按 id 取归档正文(查不到 404, 不拿空对象冒充)
"""
import os
from pathlib import Path

from flask import Blueprint, jsonify, request

from core.pa.pa_core import PaCore
from core.lib.paths import cmd_exe, vault_root

PA_SYSTEM = (
    "你是老板的私人 PA(主权 agent)，不是通用聊天机器人。铁律：\n"
    "1) 就事论事、任务目标导向：始终围绕老板的目标/决策，不闲聊、不空转；\n"
    "2) 结论先行：给结论 + 可选项 + 默认项(少开放式提问)；\n"
    "3) 诚实底线：不编造数字/事实，未查到就写「待核实」，不说假完成；\n"
    "4) 积累画像：每次交互留意老板的决策口径/审美/情感(在意点、情绪反应)，"
    "能提炼时用一句话复述确认，便于沉淀；\n"
    "5) 不越权：不承诺未授权的外部动作(写入/发布/付款)。\n"
    "回复简洁，控制在 160 字内，中文。"
)


def llm_brain(system_prompt=None, model=None, max_tokens=420):
    """构造对话脑: 用 V9 LLMClient 生成 PA 回复; 失败返回 None(上层降级为模板回复)。"""

    def _brain(context_text):
        try:
            from core.lib.llm_client import LLMClient

            prompt = "%s\n\n【上下文(画像/账本/本会话)】\n%s" % (system_prompt or PA_SYSTEM, context_text)
            out = LLMClient().generate(prompt, max_tokens=max_tokens)
            return (out or "").strip() or None
        except Exception:
            return None

    return _brain


def _data_dir():
    return os.getenv("PA_DATA_DIR", "data/v9/pa")


def _core(user_id=None):
    """单 principal 先跑通(多租户后续: data/v9/pa/users/<uid>)。"""
    return PaCore(data_dir=_data_dir())


# ---- 批176 · 副指标 A：知识库 ↔ 沙箱映射（只读三列 + 状态枚举）----
KB_STATUS_MIRRORED = "已镜像"
KB_STATUS_STALE = "过期"
KB_STATUS_MISSING = "缺失"
KB_STATUS_UNMIRRORED = "未镜像"
KB_STATUSES = (KB_STATUS_MIRRORED, KB_STATUS_STALE, KB_STATUS_MISSING, KB_STATUS_UNMIRRORED)
KB_MAPPING_DEFAULT_SCOPE = "收件箱"


def _kb_safe_rel(scope):
    """scope 必须是 vault 内的**相对**子路径（拒绝绝对路径 / .. 穿越 / 空字节）。"""
    s = str(scope or "").strip().replace(chr(92), "/").strip("/")
    if chr(0) in s:
        raise ValueError("scope 含非法字符")
    parts = [p for p in s.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError("scope 不允许 .. 穿越: %r" % scope)
    return "/".join(parts)


def build_kb_mapping(*, kb_root, sandbox_root, scope=KB_MAPPING_DEFAULT_SCOPE, limit=100, mirror_manifest=None):
    """知识库 ↔ 沙箱映射（批176 副指标 A）。**只读**：不写知识库、不写沙箱、不改 mtime。

    主语 = 知识库：kb_path（相对 kb_root）→ sandbox_path（沙箱内映射目标）→ status。
    状态判据（可机械复核）：
      已镜像 = 沙箱有副本，且大小相同、副本 mtime >= 源 mtime
      过期   = 沙箱有副本，但大小不同 或 副本更旧
      缺失   = 沙箱无副本，但**有镜像记录**（mirror_manifest；镜像功能落地后才可能出现）
      未镜像 = 沙箱无副本且无记录（默认态）
    """
    from datetime import datetime as _dt

    rel = _kb_safe_rel(scope)
    lim = max(1, min(int(limit or 100), 500))
    src_dir = (Path(kb_root) / rel) if rel else Path(kb_root)
    out = {
        "kb_root": str(kb_root),
        "sandbox_root": str(sandbox_root or ""),
        "scope": rel,
        "limit": lim,
        "readonly": True,
        "statuses": list(KB_STATUSES),
        "rows": [],
        "counts": {s: 0 for s in KB_STATUSES},
        "total": 0,
        "truncated": False,
        "degraded": "",
    }
    if not src_dir.is_dir():
        out["degraded"] = "知识库目录不存在: %s" % src_dir
        return out
    try:
        entries = [p for p in src_dir.iterdir() if p.is_file()]
    except Exception as _e_dir:
        out["degraded"] = "知识库目录不可读: %s" % _e_dir
        return out
    entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out["total"] = len(entries)
    if len(entries) > lim:
        entries = entries[:lim]
        out["truncated"] = True
    sb_root = Path(sandbox_root) if sandbox_root else None
    if sb_root is None or not sb_root.is_dir():
        out["degraded"] = "沙箱目录不存在（状态一律按未镜像显示，不猜）"
    manifest = set()
    if isinstance(mirror_manifest, dict):
        _mf = mirror_manifest.get("files", mirror_manifest)
        manifest = set(_mf.keys()) if isinstance(_mf, dict) else set(map(str, _mf or []))
    elif isinstance(mirror_manifest, (list, tuple, set)):
        manifest = set(map(str, mirror_manifest))
    for p in entries:
        kb_rel = ("%s/%s" % (rel, p.name)) if rel else p.name
        sb_path = (sb_root / rel / p.name) if sb_root else (Path(rel) / p.name)
        _st = p.stat()
        row = {
            "name": p.name,
            "kb_path": kb_rel,
            "kb_abs": str(p),
            "sandbox_path": str(sb_path),
            "kb_bytes": _st.st_size,
            "kb_mtime": _dt.fromtimestamp(_st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "mirror_bytes": None,
            "mirror_mtime": None,
            "status": KB_STATUS_UNMIRRORED,
            "reason": "沙箱无此副本",
        }
        try:
            if sb_path.is_file():
                _sm = sb_path.stat()
                row["mirror_bytes"] = _sm.st_size
                row["mirror_mtime"] = _dt.fromtimestamp(_sm.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                if _sm.st_size != row["kb_bytes"]:
                    row["status"] = KB_STATUS_STALE
                    row["reason"] = "大小不同（源 %d / 副本 %d 字节）" % (row["kb_bytes"], _sm.st_size)
                elif _sm.st_mtime < _st.st_mtime:
                    row["status"] = KB_STATUS_STALE
                    row["reason"] = "副本比源旧（%s < %s）" % (row["mirror_mtime"], row["kb_mtime"])
                else:
                    row["status"] = KB_STATUS_MIRRORED
                    row["reason"] = "内容一致（%d 字节）" % row["kb_bytes"]
            elif kb_rel in manifest:
                row["status"] = KB_STATUS_MISSING
                row["reason"] = "有镜像记录但沙箱副本不存在"
        except Exception as _e_row:
            row["reason"] = "状态判定异常: %s" % _e_row
        out["counts"][row["status"]] = out["counts"].get(row["status"], 0) + 1
        out["rows"].append(row)
    return out


# ---- 批196 · 本地浏览器「一键启动 + 富状态」（老板：不能让老板自己去 PowerShell 起客户端）----
# 设计要点：
#   · 启动命令与参数**硬编码在模块级**（页面只能传 user_id）⇒ 页面无法把它指向别的账号/别的端口/别的程序；
#   · 已连接时**不重复启动**；15s 冷却（防连点）；
#   · 走 WSL→Windows interop（cmd.exe start）⇒ 客户端在 Windows 侧运行（它要驱动 Windows Chrome）。
LOCAL_CLIENT = {
    "cmd_exe": cmd_exe(),
    "win_dir": r"C:\Users\flybo\Desktop\agent_client",
    "win_python": r"C:\Users\flybo\AppData\Local\Programs\Python\Python312\pythonw.exe",
    "script": "agent_client.py",
    "ws": "ws://127.0.0.1:5007",
    "extra_args": ["--chrome"],
}
LOCAL_CLIENT_COOLDOWN_S = 15.0
LOCAL_CLIENT_GUARD = {"ts": 0.0}  # 模块级（可测：单测直接重置它）


def local_client_launchable():
    """能不能一键启动：Windows 侧 cmd.exe 与 agent_client.py 都在（**未观察到 ≠ 可用**）。"""
    try:
        _script = os.path.join(LOCAL_CLIENT["win_dir"], LOCAL_CLIENT["script"])
        return bool(os.path.exists(LOCAL_CLIENT["cmd_exe"])) and bool(os.path.exists(_script))
    except Exception:
        return False


def local_client_command(user_id):
    """构造启动命令（**唯一出口**：单测断言它不接受任何请求侧字符串）。"""
    return [
        LOCAL_CLIENT["cmd_exe"],
        "/c",
        "start",
        "",
        "/D",
        LOCAL_CLIENT["win_dir"],
        LOCAL_CLIENT["win_python"],
        LOCAL_CLIENT["script"],
        "--user-id",
        str(user_id),
        "--ws",
        LOCAL_CLIENT["ws"],
    ] + list(LOCAL_CLIENT["extra_args"])


def register_pa_routes(app, brain=None):
    """把 PA 路由挂到 Flask app。brain: 可选 callable(context_text)->str (LLM 对话脑)。"""
    bp = Blueprint("pa_routes", __name__)

    def ok(payload=None, **kw):
        doc = {"ok": True}
        if payload is not None:
            doc.update(payload)
        doc.update(kw)
        return jsonify(doc)

    def err(msg, code=400):
        return jsonify({"ok": False, "error": str(msg)[:300]}), code

    # ---- 批196 · 本地浏览器：一键启动 + 富状态（实现见模块顶部 LOCAL_CLIENT / local_client_command）----
    @bp.route("/v9/pa/local_client/status", methods=["GET"])
    def pa_local_client_status():
        uid = request.args.get("user_id") or ""
        info = {"connected": False, "client": ""}
        try:
            from core.lib.v8 import browser_local as _bl

            info = _bl.get_connection_info(uid)
        except Exception as _e_info:
            info = {"connected": False, "client": "", "error": str(_e_info)[:200]}
        out = dict(info)
        out["launchable"] = local_client_launchable()
        return ok(out)

    @bp.route("/v9/pa/local_client/start", methods=["POST"])
    def pa_local_client_start():
        """一键启动 Windows 侧 agent_client（命令硬编码；页面只能传 user_id）。"""
        import subprocess
        import time as _time

        data = request.get_json(silent=True) or {}
        uid = str(data.get("user_id") or request.args.get("user_id") or "")
        if not uid.startswith("web_"):
            return err("user_id 非法（只允许 web_* 本机用户）", 400)
        try:
            from core.lib.v8 import browser_local as _bl

            _info = _bl.get_connection_info(uid)
        except Exception:
            _info = {"connected": False}
        if _info.get("connected"):
            return ok({"started": False, "already": True, "client": _info.get("client", "")})
        now = _time.time()
        _last = float(LOCAL_CLIENT_GUARD.get("ts") or 0)
        if now - _last < LOCAL_CLIENT_COOLDOWN_S:
            return ok({"started": False, "cooldown": round(LOCAL_CLIENT_COOLDOWN_S - (now - _last), 1)})
        if not local_client_launchable():
            return err("Windows 侧客户端不可启动：cmd.exe 或 agent_client.py 未找到", 500)
        cmd = local_client_command(uid)
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as _e_start:
            return err("启动失败：%s" % _e_start, 500)
        LOCAL_CLIENT_GUARD["ts"] = now
        print("[PA_LOCAL_CLIENT] 已请求启动桌面 agent_client user=%s（参数硬编码，未接受前端输入）" % uid)
        return ok({"started": True, "hint": "已在 Windows 侧启动；等 5~20 秒，状态会自动变为已连接"})

    @bp.route("/v9/pa/context", methods=["GET"])
    def pa_context():
        pa = _core(request.args.get("user_id"))
        r = pa.handle("context")
        _conf = sorted(pa.profile.entries_by_domain(status="confirmed"), key=lambda e: e.get("date", ""), reverse=True)
        prof = _conf[:20]
        led = pa.ledger.open_items()
        return ok(
            {
                "brief": r.get("profile", ""),
                "ledger_brief": r.get("ledger", ""),
                "profile": prof,
                "ledger": led,
                "counts": {"profile": len(prof), "ledger": len(led)},
            }
        )

    @bp.route("/v9/pa/profile", methods=["GET"])
    def pa_profile():
        pa = _core(request.args.get("user_id"))
        d = request.args.get("domain") or None
        return ok({"entries": pa.profile.active(d)})

    @bp.route("/v9/pa/profile/schema", methods=["GET"])
    def pa_profile_schema():
        """字段表 + 当前取值 + 推导能力开关 —— 前端按此渲染表单（不硬编码字段）。"""
        from core.pa.profile import FIELD_SCHEMA, capability_switches, field_schema, get_fields

        pa = _core(request.args.get("user_id"))
        vals = get_fields(pa.profile)
        # order: Flask jsonify 默认按 key 排序, 字段顺序必须显式下发(表单按语义排, 不按字母)
        return ok(
            {
                "fields": field_schema(),
                "order": list(FIELD_SCHEMA.keys()),
                "values": vals,
                "switches": capability_switches(vals),
            }
        )

    @bp.route("/v9/pa/profile", methods=["POST"])
    def pa_profile_write():
        """参数化收集写入口：表单(source=form) 与 聊天(source=chat) **同一条落库路径**。

        body: {values:{字段:取值}, source, user_id}；取值不合法进 rejected 不落库。
        """
        from core.pa.profile import capability_switches, collect_fields, get_fields

        p = request.json or {}
        values = p.get("values") or {}
        if not isinstance(values, dict) or not values:
            return err("profile 写入需要 values:{字段:取值}")
        src = p.get("source") or "form"
        pa = _core(p.get("user_id"))
        r = collect_fields(pa.profile, values, source=src)
        pa.events.append(
            "fact",
            "field_collect",
            {
                "source": src,
                "values": values,
                "written": [w["key"] for w in r["written"]],
                "rejected": [x["key"] for x in r["rejected"]],
            },
            source=src,
        )
        vals = get_fields(pa.profile)
        return ok(
            {
                "written": r["written"],
                "unchanged": r["unchanged"],
                "rejected": r["rejected"],
                "fields": vals,
                "switches": capability_switches(vals),
            }
        )

    @bp.route("/v9/pa/sediment", methods=["POST"])
    def pa_sediment():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        if not p.get("domain") or not p.get("value"):
            return err("sediment 需要 domain + value")
        r = pa.handle("profile_sediment", p)
        return ok(r) if r.get("ok") else err(r.get("error"))

    @bp.route("/v9/pa/dialog", methods=["POST"])
    def pa_dialog():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        text = (p.get("text") or "").strip()
        if not text:
            return err("dialog 需要 text")
        sid = p.get("session_id") or "pa_default"
        # 就事论事: 把"目标/议题"一起带给对话脑, 不是闲聊
        r = pa.handle("dialog_post", {"sid": sid, "text": text, "topic": p.get("topic"), "brain": brain})
        reply = (r.get("dialog") or {}).get("reply") or "（PA 脑暂不可用：已记录本条，稍后可继续商量）"
        # 聊天层参数化收集：从这句话识别字段取值 -> 与表单同一条写入路径(collect_fields)
        from core.pa.collect import detect_fields, recap_line
        from core.pa.profile import collect_fields

        hits = detect_fields(text)
        collected = {"written": [], "unchanged": [], "rejected": []}
        if hits:
            collected = collect_fields(pa.profile, hits, source="chat")
            if collected["written"] or collected["unchanged"]:
                reply = reply + "\n\n" + recap_line(hits)
        return ok(
            {
                "reply": reply,
                "topic": (r.get("dialog") or {}).get("topic", ""),
                "session_id": sid,
                "collected": collected,
            }
        )

    @bp.route("/v9/pa/dialog", methods=["GET"])
    def pa_dialog_history():
        pa = _core(request.args.get("user_id"))
        n = int(request.args.get("n") or 30)
        r = pa.handle("dialog_context", {"sid": request.args.get("session_id") or "pa_default", "n": n})
        return ok(r)

    @bp.route("/v9/pa/threads", methods=["GET"])
    def pa_threads_get():
        from core.pa.threads import ThreadStore, ThreadStoreCorrupt

        ts = ThreadStore(_data_dir())
        try:
            _tstate = ts.load(request.args.get("user_id"))
        except ThreadStoreCorrupt as _c:
            # X-17：坏状态**不回落空状态**（前端是 `if(r.ok)` ⇒ 自动跳过，不会炸页面）
            return jsonify({"ok": False, "error": "thread_state_corrupt",
                            "message": str(_c), "path": _c.path}), 409
        return ok(_tstate)

    @bp.route("/v9/pa/threads", methods=["POST"])
    def pa_threads_post():
        # 批189 · #3（老板要求）：PA 单线程 ⇒ **关闭线程状态写入**（前端不得创建/切换线程）。
        # 历史仍可经 GET 只读查询（ThreadStore.load）。理由：POST 开着 = 前端仍可多线程 ⇒ 单线程不成立。
        print("[PA_SINGLE_THREAD] 拒绝 POST /v9/pa/threads（单线程模式；历史请用 GET）")
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "single_thread_mode",
                    "message": "PA 已切到单线程：线程状态写入已关闭（历史可用 GET /v9/pa/threads 只读查询）",
                }
            ),
            410,
        )

    @bp.route("/v9/pa/ledger", methods=["GET"])
    def pa_ledger():
        pa = _core(request.args.get("user_id"))
        return ok({"items": pa.ledger.items, "open": pa.ledger.open_items()})

    @bp.route("/v9/pa/ledger/add", methods=["POST"])
    def pa_ledger_add():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        if not p.get("title"):
            return err("ledger/add 需要 title")
        r = pa.handle(
            "todo_add",
            {"title": p["title"], "kind": p.get("kind", "todo"), "note": p.get("note", ""), "due": p.get("due")},
        )
        return ok(r) if r.get("ok") else err(r.get("error"))

    @bp.route("/v9/pa/ledger/done", methods=["POST"])
    def pa_ledger_done():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        if not p.get("id"):
            return err("ledger/done 需要 id")
        r = pa.handle("todo_done", {"id": p["id"]})
        return ok(r) if r.get("ok") else err(r.get("error"))

    @bp.route("/v9/pa/dispatch", methods=["POST"])
    def pa_dispatch():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        task = (p.get("task_text") or "").strip()
        if not task:
            return err("dispatch 需要 task_text")
        action = "dispatch_v9" if p.get("via_gateway") else "dispatch"
        r = pa.handle(action, {"task_text": task, "url": p.get("url")})
        return ok(r) if r.get("ok") else err(r.get("error"))

    # ---- 编队花名册: PA 派活前先查"谁能干、怎么调、边界在哪" ----
    @bp.route("/v9/pa/roster", methods=["GET"])
    def pa_roster():
        from core.pa import roster as R

        if request.args.get("full"):
            return ok({"cards": R.load().get("cards", [])})
        return ok(R.summary())

    @bp.route("/v9/pa/roster/find", methods=["GET"])
    def pa_roster_find():
        """按能力找人 —— 派活第一步。"""
        from core.pa import roster as R

        cap = request.args.get("cap") or ""
        return ok({"cap": cap, "candidates": R.by_capability(cap)})

    @bp.route("/v9/pa/roster/<agent_id>", methods=["GET"])
    def pa_roster_card(agent_id):
        from core.pa import roster as R

        c = R.get(agent_id)
        return ok({"card": c}) if c else err("无此卡片: %s" % agent_id, 404)

    @bp.route("/v9/pa/roster/upsert", methods=["POST"])
    def pa_roster_upsert():
        """新增/更新卡片: 把新获得的能力认识固化下来(迭代的落点)。"""
        from core.pa import roster as R

        p = request.json or {}
        card = p.get("card") or p
        r = R.upsert(card)
        if r.get("ok"):
            try:
                _core(p.get("user_id")).events.append(
                    "fact", "roster_upsert", {"id": card.get("id"), "keys": sorted(card.keys())}, source="pa/roster"
                )
            except Exception:
                pass
            return ok(r)
        return err(r.get("error"))

    @bp.route("/v9/pa/proxy", methods=["POST"])
    def pa_proxy():
        """PA 调用本地灵犀服务(3890)的【唯一入口】—— 强制经过端点分级门。

        为什么必须走这里: 2026-09-10 我用脚本对每个候选路径盲发 POST {},
        其中 POST /kv/clear 无参数即清空全部 → 插件配置库 8 条全灭。
        现在起 PA 不允许直连 3890; 一切经本路由, 由 endpoint_guard 分级:
          只读 -> 放行 / 写 -> 放行并记账 / 破坏性 -> 需在场授权 / 未登记非 GET -> 默认拒绝
        """
        import json as _json

        from core.pa import endpoint_guard as G

        p = request.json or {}
        method = (p.get("method") or "GET").upper()
        path = (p.get("path") or "").strip()
        body = p.get("body")
        user_id = p.get("user_id") or ""
        if not path:
            return err("proxy 需要 path")

        # /mcp/call 按 body.name(工具名) 分级, 其余端点按路径分级(见 endpoint_guard)
        _mcp_tool = (body or {}).get("name") if isinstance(body, dict) else None
        allowed, level, reason = G.check(method, path, user_id, body)
        # 记账(含被拒): 谁在什么时候想动什么, 必须可追溯
        try:
            pa = _core(user_id)
            _ev = {"method": method, "path": path, "level": level, "allowed": bool(allowed), "reason": reason}
            if _mcp_tool:
                _ev["mcp_tool"] = _mcp_tool
            pa.events.append("fact", "proxy_call", _ev, source="pa/proxy")
        except Exception:
            pass
        if not allowed:
            return jsonify({"ok": False, "error": reason, "blocked_by": "endpoint_guard", "level": level}), 403

        base = os.getenv("LINGXI_PROXY_BASE", "http://127.0.0.1:3890")
        url = base.rstrip("/") + path
        try:
            import urllib.request

            headers = {"Content-Type": "application/json"}
            # token 从插件 KV 现取(read 级), 避免硬编码
            try:
                _kv = urllib.request.urlopen(base.rstrip("/") + "/kv/all", timeout=5)
                _tok = (_json.loads(_kv.read().decode("utf-8")) or {}).get("items", {}).get("wpsAiMcpBridgeToken")
                if _tok:
                    headers["Authorization"] = "Bearer " + str(_tok)
            except Exception:
                pass
            data = None
            if method in ("POST", "PUT", "PATCH"):
                data = _json.dumps(body if body is not None else {}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=float(p.get("timeout", 20))) as resp:
                raw = resp.read().decode("utf-8", "replace")
                try:
                    parsed = _json.loads(raw)
                except Exception:
                    parsed = {"raw": raw[:2000]}
                return ok({"level": level, "status": resp.status, "data": parsed})
        except urllib.error.HTTPError as e:
            try:
                _b = _json.loads(e.read().decode("utf-8", "replace"))
            except Exception:
                _b = {"raw": ""}
            return jsonify({"ok": False, "level": level, "status": e.code, "error": str(e)[:200], "data": _b}), e.code
        except Exception as e:
            return err("proxy 调用失败: %s" % str(e)[:200])

    @bp.route("/v9/pa/proxy/gate", methods=["GET"])
    def pa_proxy_gate():
        from core.pa import endpoint_guard as G

        return ok(G.gate_state(request.args.get("user_id") or ""))

    @bp.route("/v9/pa/proxy/approve", methods=["POST"])
    def pa_proxy_approve():
        """老板在场授权破坏性端点(会话级, 默认 30 分钟)。"""
        from core.pa import endpoint_guard as G

        p = request.json or {}
        if p.get("revoke"):
            return ok(G.revoke(p.get("user_id") or ""))
        r = G.approve_destructive(
            p.get("user_id") or "", p.get("path"), float(p.get("ttl_s") or 1800), p.get("note") or ""
        )
        try:
            _core(p.get("user_id")).events.append("fact", "proxy_approve", {"paths": r.get("paths")}, source="pa/proxy")
        except Exception:
            pass
        return ok(r)

    # ---- 验收器官: 审核(preflight + 内容合规 + postcheck) ----
    # ---- 口径卡: 政策数字定状态 + 与内容合规联动 ----
    @bp.route("/v9/pa/caliber", methods=["GET"])
    def pa_caliber():
        from core.pa import caliber as C

        return ok({"cards": C.summary(), "counts": C.counts()})

    @bp.route("/v9/pa/caliber/check", methods=["POST"])
    def pa_caliber_check():
        from core.pa import caliber as C

        p = request.json or {}
        pages = p.get("pages") or []
        if not isinstance(pages, list):
            return err("caliber/check 需要 pages 列表")
        hits = C.check(pages)
        return ok({"hits": hits, "hit_count": len(hits)})

    @bp.route("/v9/pa/audit/preflight", methods=["POST"])
    def pa_audit_preflight():
        """渲染前字段级预检 + 内容合规。规则从画像读(extra_marks 由画像禁忌抽取)。"""
        from core.pa import audit as A

        p = request.json or {}
        pages = p.get("pages") or []
        if not isinstance(pages, list) or not pages:
            return err("audit/preflight 需要 pages 列表")
        extra = p.get("extra_marks") or []
        try:
            _pa = _core(p.get("user_id"))
            extra = list(extra) + A.profile_forbidden_marks(
                _pa.profile.entries("aesthetic") + _pa.profile.entries("decision")
            )
        except Exception:
            pass
        issues = A.preflight(pages, extra_marks=extra)
        fails = [x for x in issues if x[1] == "fail"]
        warns = [x for x in issues if x[1] == "warn"]
        out = {
            "pages": len(pages),
            "issues": issues,
            "fail_count": len(fails),
            "warn_count": len(warns),
            "pass": len(fails) == 0,
        }
        try:
            _pa.events.append(
                "fact",
                "audit_preflight",
                {"pages": len(pages), "fail": len(fails), "warn": len(warns), "pass": out["pass"]},
                source="pa/audit",
            )
        except Exception:
            pass
        return ok(out)

    @bp.route("/v9/pa/audit/postcheck", methods=["POST"])
    def pa_audit_postcheck():
        from core.pa import audit as A

        p = request.json or {}
        if not p.get("png_dir") or not p.get("prefix") or not p.get("pptx_dir"):
            return err("audit/postcheck 需要 png_dir/prefix/pptx_dir")
        rep = A.postcheck(p["png_dir"], p["prefix"], p["pptx_dir"], p.get("expected"))
        fails = [x for x in rep["issues"] if x[1] == "fail"]
        rep["pass"] = len(fails) == 0
        try:
            _core(p.get("user_id")).events.append(
                "fact", "audit_postcheck", {"pass": rep["pass"], "issues": len(rep["issues"])}, source="pa/audit"
            )
        except Exception:
            pass
        return ok(rep)

    @bp.route("/v9/pa/act", methods=["POST"])
    def pa_act():
        """PA 本地动作直派(分派层执行原语)。

        用途: 老板说"打开第 7 页给我看"/"关掉 WPS 释放文件锁"时, PA 不必为一次
        系统动作起一整轮 agent 对话 —— 直接派发到 agent_client 白名单执行。

        边界(硬): 只放行 LOCAL_SYSTEM_ACTIONS(open_document/close_wps/lingxi_mcp);
        浏览器动作(navigate/click/publish 等)不走这里, 必须走 agent + 治理门。
        治理门同源: 仍经 browser_local.execute() → 随时停止(stop)对本地动作同样生效。
        """
        from core.tools.browser_local import LOCAL_SYSTEM_ACTIONS, BrowserLocalPlugin

        p = request.json or {}
        action = (p.get("action") or "").strip()
        params = p.get("params") or {}
        if action not in LOCAL_SYSTEM_ACTIONS:
            return err("仅支持本地动作: %s(收到 %r)" % (sorted(LOCAL_SYSTEM_ACTIONS), action))
        if not isinstance(params, dict):
            return err("params 需为对象")
        import types as _types

        args = dict(params)
        args["action"] = action
        ctx = _types.SimpleNamespace(user_id=p.get("user_id") or "", session_id=p.get("session_id") or "")
        r = BrowserLocalPlugin().execute(args, ctx)
        # 记账: 本地动作入 PA 事件流(可追溯老板授权过什么)
        try:
            pa = _core(p.get("user_id"))
            pa.events.append(
                "fact",
                "local_action",
                {
                    "action": action,
                    "path": params.get("path", ""),
                    "ok": bool(r.get("success")),
                    "error": r.get("error", ""),
                },
                source="pa/act",
            )
        except Exception:
            pass
        if r.get("success"):
            return ok({"result": r})
        return jsonify({"ok": False, "error": str(r.get("error") or "动作失败")[:300], "result": r}), 400

    @bp.route("/v9/pa/dispatch/history", methods=["GET"])
    def pa_dispatch_history():
        pa = _core(request.args.get("user_id"))
        return ok(pa.handle("dispatch_history"))

    @bp.route("/v9/pa/vault/sync", methods=["POST"])
    def pa_vault_sync():
        """账本 -> Obsidian(待办/站会/未读索引)。vault 路径可用 env PA_VAULT_DIR 覆盖。"""
        from core.pa.vault_brain import BrainSync

        pa = _core((request.json or {}).get("user_id"))
        vault = os.getenv("PA_VAULT_DIR") or str(vault_root())
        brain_sync = BrainSync(pa.ledger, vault_dir=vault)
        out = {
            "ledger_md": brain_sync.sync_ledger(),
            "unread": brain_sync.unread_index(),
            "standup": brain_sync.daily_standup(),
        }
        return ok(out)

    # ---- 拍板(决策) + 计划时间轴(2026-09-11): 老板对 PA 产物四选一拍板, 留痕 decision_log.json ----
    @bp.route("/v9/pa/plan", methods=["POST"])
    def pa_plan():
        """派活后 PA 先出「语义步骤计划」(时间轴节点=拍板点), 再执行。"""
        from core.pa.decision import generate_plan

        p = request.json or {}
        task = (p.get("task") or "").strip()
        if not task:
            return err("plan 需要 task")
        return ok(generate_plan(task, mode=p.get("mode") or "work", user_id=p.get("user_id")))

    @bp.route("/v9/pa/decision", methods=["POST"])
    def pa_decision():
        """老板拍板: 采纳/小改/大改/退回/暂缓 → 写 decision_log.json。"""
        from core.pa.decision import DECISIONS, DecisionStore

        p = request.json or {}
        decision = (p.get("decision") or "").strip()
        if decision not in DECISIONS:
            return err("decision 必须是: %s" % "/".join(DECISIONS))
        ds = DecisionStore(_data_dir())
        rec = ds.record(
            p.get("user_id"),
            p.get("session_id"),
            p.get("node"),
            p.get("stage"),
            decision,
            p.get("note") or "",
            p.get("task") or "",
        )
        try:
            _core(p.get("user_id")).events.append(
                "fact",
                "pa_decision",
                {"decision": decision, "node": p.get("node"), "stage": p.get("stage")},
                source="pa/decision",
            )
        except Exception:
            pass
        return ok({"decision": rec})

    @bp.route("/v9/pa/decision/log", methods=["GET"])
    def pa_decision_log():
        from core.pa.decision import DecisionStore

        ds = DecisionStore(_data_dir())
        return ok({"decisions": ds.list(request.args.get("user_id"), request.args.get("session_id"))})

    # ---- 能改(2026-09-11): cfgPerm 后端持久化。PA 不能自改规则(见 registry._CONFIG_FILES 写保护) ----
    @bp.route("/v9/pa/permission", methods=["GET"])
    def pa_permission_get():
        from core.pa.permission import PermissionStore

        ps = PermissionStore(os.path.join(_data_dir(), "permission.json"))
        return ok({"level": ps.get()})

    @bp.route("/v9/pa/permission", methods=["POST"])
    def pa_permission_post():
        """老板在场改权限档。只认白名单值; PA 无工具触达本路由, 直写被 ForbiddenGuard 拦。"""
        from core.pa.permission import PermissionStore

        p = request.json or {}
        ps = PermissionStore(os.path.join(_data_dir(), "permission.json"))
        r = ps.set(p.get("level"), p.get("user_id") or "")
        if not r.get("ok"):
            return err(r.get("error"))
        try:
            _core(p.get("user_id")).events.append(
                "fact", "permission_change", {"level": r["level"]}, source="pa/permission"
            )
        except Exception:
            pass
        return ok(r)

    @bp.route("/v9/pa/ppt/comments", methods=["GET"])
    def pa_ppt_comments_get():
        """读批注（C2 后端，2026-09-13）。读方：前端加载批注(C3) + 发布清单回溯。"""
        from core.pa import ppt_comments as _pc

        try:
            _deck = request.args.get("deck") or ""
            return jsonify({"ok": True, "comments": _pc.list_comments(_data_dir(), _deck or None)})
        except Exception as _e:
            return jsonify({"ok": False, "error": str(_e)}), 500

    @bp.route("/v9/pa/ppt/comments", methods=["POST"])
    def pa_ppt_comments_post():
        """写批注（C2 后端，2026-09-13）。前端双写：localStorage 保留离线可用，后端为准。"""
        from core.pa import ppt_comments as _pc

        try:
            _body = request.get_json(silent=True) or {}
            _rec = _pc.add_comment(
                _data_dir(), _body.get("deck") or "", _body.get("page_index"), _body.get("comment") or ""
            )
            return jsonify({"ok": True, "comment": _rec})
        except ValueError as _ve:
            return jsonify({"ok": False, "error": str(_ve)}), 400
        except Exception as _e:
            return jsonify({"ok": False, "error": str(_e)}), 500

    @bp.route("/v9/pa/artifact/thumbs", methods=["POST"])
    def pa_artifact_thumbs_post():
        """C1(批73): 缩略图上传落盘。**后端定位置**，出参只给相对 url_base。"""
        from core.pa import artifact_thumbs as _at

        try:
            _b = request.get_json(silent=True) or {}
            _r = _at.save_thumbs(_b.get("deck"), _b.get("files") or [])
            return jsonify(_r), (200 if _r.get("ok") else 400)
        except Exception as _e:
            return jsonify({"ok": False, "error": str(_e)}), 500

    @bp.route("/v9/pa/kb_mapping", methods=["GET"])
    def pa_kb_mapping():
        """知识库 ↔ 沙箱映射（批176 副指标 A）：**只读**三列 + 状态枚举。

        只 stat，不写任何一侧（N1–N6 零噪音的前置约束）；镜像记录（若有）读沙箱 .kb_mirror.json。
        """
        import json as _json

        from core.lib.gateway_helpers import _get_sandbox_base as _gsb

        try:
            _uid = request.args.get("user_id")
            _sid = (request.args.get("session_id") or "").strip()
            _scope = request.args.get("scope") or KB_MAPPING_DEFAULT_SCOPE
            _limit = request.args.get("limit") or 100
            _kb = os.getenv("PA_VAULT_DIR") or str(vault_root())
            _sb = ""
            _man = None
            if _sid:
                try:
                    _sb = str(_gsb(_uid or "default", _sid))
                except Exception:
                    _sb = ""
                _mf = (Path(_sb) / ".kb_mirror.json") if _sb else None
                if _mf is not None and _mf.is_file():
                    try:
                        _man = _json.loads(_mf.read_text(encoding="utf-8"))
                    except Exception:
                        _man = None
            return jsonify(
                {
                    "ok": True,
                    **build_kb_mapping(kb_root=_kb, sandbox_root=_sb, scope=_scope, limit=_limit, mirror_manifest=_man),
                }
            )
        except ValueError as _ve:
            return jsonify({"ok": False, "error": str(_ve)}), 400
        except Exception as _e:
            return jsonify({"ok": False, "error": str(_e)}), 500

    # ---- 层 1 · 归档正文落服务端（X-11；老板/DS 2026-09-18 拍 A：Windows 起本机网关 + 端口错峰）----
    # 目的：**本地足迹与归档条数解耦** —— 正文搬进 data/v9/pa/threads_<uid>.json，
    #       前端随即将本地 archived[].msgs 换成最小索引（id/title/archived_at/msg_count/server）。
    # 纪律（与方案 §三 逐条对应）：
    #   1) **按 id 合并**：不覆盖既有条、不产生重复；同一批重发 ⇒ written=0（幂等）；
    #   2) **只碰 archived**：不改 POST /v9/pa/threads 的单线程关闭语义，不动 threads/activeThread；
    #   3) **写完立刻读回**：缺任一条 ⇒ ok:False（**不得假装成功**）；
    #   4) 校验**全部通过才 save**（本端点自身不留半截；前端「本地一字不改」由前端保证）；
    #   5) items 空 / 项缺 id / 缺 user_id / uid 非法 ⇒ 400 且**零写入**；
    #   6) 按 user_id 隔离（threads_<uid>.json）；非法 uid（路径分隔/穿越）⇒ 400；
    #   7) **不自动删除任何数据**（批221·A：归档不设上限、不裁剪）。
    def _archive_uid(raw):
        """uid 必须是**单段**标识：拒空/拒路径分隔/拒 '..'/拒空字节（防穿越出 data/v9/pa/）。"""
        s = str(raw or "").strip()
        if not s:
            raise ValueError("user_id 缺失")
        if chr(0) in s:
            raise ValueError("user_id 含非法字符")
        if s in (".", "..") or "/" in s or "\\" in s or ":" in s:
            raise ValueError("user_id 必须是单段标识（不允许路径分隔/穿越）")
        return s

    @bp.route("/v9/pa/archive", methods=["POST"])
    def pa_archive_post():
        """归档正文落服务端（层 1）。入参 {user_id, items:[{id,title,archived_at,msgs}]}。"""
        import json as _json

        from core.pa.threads import ThreadStore, ThreadStoreCorrupt

        body = request.get_json(silent=True) or {}
        try:
            uid = _archive_uid(body.get("user_id"))
        except ValueError as _ve:
            return err(_ve, 400)
        items = body.get("items")
        if not isinstance(items, list) or not items:
            return err("items 必须是非空数组", 400)
        for _it in items:
            if not isinstance(_it, dict) or not str(_it.get("id") or "").strip():
                return err("每个 item 必须有非空 id", 400)

        ts = ThreadStore(_data_dir())
        try:
            state = ts.load(uid)
        except ThreadStoreCorrupt as _c:
            # X-17 关键止损：坏状态**不得当空基线**（否则一次写即清空历史归档）⇒ 报错且**零写入**
            return jsonify({"ok": False, "error": "thread_state_corrupt",
                            "message": str(_c), "path": _c.path, "written": 0}), 409
        archived = state.get("archived")
        if not isinstance(archived, list):
            archived = []
        by_id = {}
        order = []
        for _a in archived:
            if isinstance(_a, dict) and _a.get("id") is not None:
                _k = str(_a["id"])
                if _k not in by_id:
                    order.append(_k)
                by_id[_k] = _a
        written = 0
        for _it in items:
            _k = str(_it.get("id"))
            _old = by_id.get(_k)
            _new = dict(_it)
            if _old is None or _json.dumps(_old, ensure_ascii=False, sort_keys=True) != _json.dumps(
                _new, ensure_ascii=False, sort_keys=True
            ):
                written += 1
            if _old is None:
                order.append(_k)
            by_id[_k] = _new
        state["archived"] = [by_id[_k] for _k in order]
        try:
            res = ts.save(uid, state)
        except ThreadStoreCorrupt as _c:
            # X-17② 批 2：save 现在也 fail-loud（坏状态拒绝写入）⇒ 与 load 同形状回报，
            # 不把「读→写」窗口内变坏的情况漏成 Flask HTML 500（前端 `if(r.ok)` 依赖 JSON 形状）。
            return jsonify({"ok": False, "error": "thread_state_corrupt",
                            "message": str(_c), "path": _c.path, "written": 0}), 409
        if not (isinstance(res, dict) and res.get("ok")):
            return jsonify({"ok": False, "error": "写入失败：save 未返回 ok", "written": 0}), 500
        # **读回确认**（本项目既有教训：测试绿 ≠ 数据在）
        back = ts.load(uid)
        back_ids = {
            str(_a["id"]) for _a in (back.get("archived") or []) if isinstance(_a, dict) and _a.get("id") is not None
        }
        missing = [str(_it.get("id")) for _it in items if str(_it.get("id")) not in back_ids]
        if missing:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "读回不一致：缺 %d 条" % len(missing),
                        "missing": missing[:10],
                        "written": 0,
                    }
                ),
                500,
            )
        return ok(
            {
                "written": written,
                "archived_total": len(back.get("archived") or []),
                "path": str(res.get("path") or ""),
            }
        )

    @bp.route("/v9/pa/archive/<archive_id>", methods=["GET"])
    def pa_archive_get(archive_id):
        """按 id 取一条归档（含正文）。**查不到返 404，不得拿空对象冒充**。"""
        from core.pa.threads import ThreadStore, ThreadStoreCorrupt

        try:
            uid = _archive_uid(request.args.get("user_id"))
        except ValueError as _ve:
            return err(_ve, 400)
        try:
            state = ThreadStore(_data_dir()).load(uid)
        except ThreadStoreCorrupt as _c:
            # X-17：损坏**不得谎报 404「不存在」**（404 = 确实没这条；读不动 ≠ 不存在）
            return jsonify({"ok": False, "error": "thread_state_corrupt",
                            "message": str(_c), "path": _c.path}), 409
        for _a in state.get("archived") or []:
            if isinstance(_a, dict) and str(_a.get("id")) == str(archive_id):
                return ok({"item": _a})
        return jsonify({"ok": False, "error": "archive_not_found"}), 404
    # ---- X-16 批 B（DS 2026-09-18 拍）：PA 状态不可用 ⇒ **可读提示**，不外泄原始 traceback ----
    from core.pa.state_out import PAStateCorrupt

    @bp.errorhandler(PAStateCorrupt)
    def _pa_state_corrupt(e):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "pa_state_corrupt",
                    "message": str(e),
                    "path": getattr(e, "path", ""),
                    "hint": "状态文件已隔离到同目录 .quarantine/；可人工核对后放回，或按业务重建。",
                }
            ),
            409,
        )

    app.register_blueprint(bp)
    return bp
