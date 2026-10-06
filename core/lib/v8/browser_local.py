# -*- coding: utf-8 -*-
"""V9 本地浏览器操作 — 后端 WS 服务 + 连接管理 + 工具实现

架构: Chrome Extension(SW) 作为 WebSocket 客户端连本服务(V9 侧独立 WS 线程, 端口
= 网关端口 + execution_policy.browser_local.ws_port_offset（pm_1558 §三 裁 ⒜: 由网关端口派生）。
⛔ 不复述数值, 一律经 ws_port()。V9 Agent 通过
browser_local_* 工具把指令发到该连接, 扩展用 chrome.debugger 操作用户本地浏览器。

安全: 只收 DOM/截图, 不转发 Cookies; 域名白名单 browser_policy.yaml; 敏感操作硬拒绝。
"""
import json
import logging
import os
import threading
import time
import uuid
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# {user_id: {"ws": conn, "connected_at": ts, "state": {...}, "tag": 客户端标识(如 python-client)}}
_browser_conns: Dict[str, dict] = {}
_browser_lock = threading.Lock()
# 待执行指令队列 {user_id: {cmd_id: (future, action, params)}}
_browser_pending: Dict[str, dict] = {}
# P2 审批队列: {user_id: {"op_id", "action", "params", "ts", "status": pending|approved|rejected}}
_browser_pending_ops: Dict[str, dict] = {}
_browser_ws_server = None
_browser_ws_thread = None

# ===== P2 敏感操作检测(click/fill 触发审批) =====

_SENSITIVE_CLICK_HINTS = ["publish", "发布", "submit", "提交", "发送", "发表", "confirm", "确认支付", "付款"]
_SENSITIVE_FILL_HINTS = ["password", "密码", "card", "卡号", "pay", "支付", "验证码", "captcha"]

# ===== 2026-09-10 老板治理要求: 在场 + 一次授权(会话级) + 随时停止 =====
# 外部站点(如专家页面)的浏览器交互属于"对外部世界说话", 必须老板在场并一次性授权;
# 授权在会话内有效(默认 30 分钟), 期间同类动作免逐次确认; 老板可随时 stop。
_DEFAULT_EXTERNAL_SITES = ("chat.deepseek.com", "deepseek.com")
_browser_grants = {}  # user_key -> {"hosts":[..], "actions":[..], "expires":ts, "note":str, "ts":ts}
_browser_stop = {}  # user_key -> {"ts":ts, "reason":str}
_data_grants = {}  # user_key -> {"session_id":str, "level":"L3", "ts":ts, "note":str}  # L3 原始数据授权(按任务/session 一次)


def _key_candidates(user_id: str) -> list:
    """治理态的键候选: 原键 + 连接解析键。

    (2026-09-10 事故) 写方用 _resolve_conn_user(user_id) 得到 _conn_user, 读方却拿原键查,
    两者在"多连接/兜底解析"场景下不相等 → 老板授了权、门却读不到(或反过来 stop 读不到),
    治理态静默不一致。统一为: 写方写全部候选键, 读方查全部候选键。
    """
    out = [user_id]
    try:
        _r = _resolve_conn_user(user_id)
        if _r and _r != user_id:
            out.append(_r)
    except Exception:
        pass
    return [k for k in out if k]


_PUBLISH_PLATFORMS = ["xiaohongshu.com", "douyin.com", "bilibili.com", "zhihu.com"]


def _op_fingerprint(action: str, params: dict) -> str:
    """操作指纹: action + 关键参数(selector/text/query), 供审批重放匹配"""
    _p = params or {}
    _key = json.dumps({k: _p.get(k) for k in ("selector", "text", "query", "url")}, ensure_ascii=False, sort_keys=True)
    return "%s:%s" % (action, _key)


def external_sites() -> List[str]:
    """外部站点(需老板在场授权): policy browser_local.external_sites 可覆盖。"""
    try:
        from core.gateway.shared_state import _load_v9_execution_policy

        _bl = (_load_v9_execution_policy() or {}).get("browser_local", {}) or {}
        return _bl.get("external_sites") or list(_DEFAULT_EXTERNAL_SITES)
    except Exception:
        return list(_DEFAULT_EXTERNAL_SITES)


def _host_of(url: str) -> str:
    try:
        from urllib.parse import urlparse

        h = urlparse(str(url or "")).hostname or ""
        return h.lower()
    except Exception:
        return ""


def _is_external_host(host: str) -> bool:
    if not host:
        return False
    h = host.lower()
    for s in external_sites():
        if h == s or h.endswith("." + s):
            return True
    return False


def is_external_action(action: str, params: dict) -> bool:
    """该动作是否触达外部站点(用 url 或页面状态判断)。"""
    _p = params or {}
    h = _host_of(_p.get("url"))
    if h and _is_external_host(h):
        return True
    # 无 url(click/fill/extract) 时看当前页面
    try:
        _k = _resolve_conn_user(_p.get("user_id") or "")
        st = connection_state(_k) if _k else None
        _u = (st or {}).get("url") or ""
        if _u and _is_external_host(_host_of(_u)):
            return True
    except Exception:
        pass
    return False


def grant_browser_session(user_id: str, hosts=None, actions=None, ttl_s: int = 1800, note: str = "") -> dict:
    """老板一次性授权: 会话内(默认 30 分钟)对指定站点/动作免逐次确认。"""
    _hosts = list(hosts) if hosts else list(external_sites())
    _acts = (
        list(actions)
        if actions
        else ["navigate", "fill", "click", "extract", "evaluate", "scroll", "screenshot", "upload"]
    )
    _keys = _key_candidates(user_id)  # 锁外计算: _resolve_conn_user 内部会取同一把锁
    with _browser_lock:
        for _k in _keys:  # 写全部候选键, 读方任一键都能查到
            _browser_grants[_k] = {
                "hosts": _hosts,
                "actions": _acts,
                "expires": time.time() + float(ttl_s),
                "note": note,
                "ts": time.time(),
            }
            _browser_stop.pop(_k, None)  # 授权即解除停止
    _audit(user_id, "grant", {"hosts": _hosts, "ttl_s": ttl_s}, {"success": True, "note": note})
    return {"success": True, "hosts": _hosts, "actions": _acts, "ttl_s": ttl_s}


def revoke_browser_session(user_id: str) -> dict:
    _keys = _key_candidates(user_id)
    with _browser_lock:
        for _k in _keys:
            _browser_grants.pop(_k, None)
    return {"success": True, "revoked": True}


def stop_browser_session(user_id: str, reason: str = "老板手动停止") -> dict:
    """老板随时停止: 置位后所有浏览器动作一律拒绝, 直到 resume/grant。"""
    _keys = _key_candidates(user_id)
    with _browser_lock:
        for _k in _keys:
            _browser_stop[_k] = {"ts": time.time(), "reason": reason}
    _audit(user_id, "stop", {"reason": reason}, {"success": True})
    return {"success": True, "stopped": True, "reason": reason}


def resume_browser_session(user_id: str) -> dict:
    _keys = _key_candidates(user_id)
    with _browser_lock:
        for _k in _keys:
            _browser_stop.pop(_k, None)
    return {"success": True, "stopped": False}


def session_gate(user_id: str, action: str = "", params: dict = None) -> dict:
    """查询当前门状态(供前端/PA 显示): stop / grant 情况。"""
    _keys = _key_candidates(user_id)
    with _browser_lock:
        st, gr = {}, {}
        for _k in _keys:
            st = st or dict(_browser_stop.get(_k) or {})
            gr = gr or dict(_browser_grants.get(_k) or {})
    _alive = bool(gr) and gr.get("expires", 0) > time.time()
    return {
        "stopped": bool(st),
        "stop_reason": st.get("reason", ""),
        "granted": _alive,
        "grant_hosts": gr.get("hosts", []) if _alive else [],
        "grant_expires_in": max(0, int(gr.get("expires", 0) - time.time())) if _alive else 0,
    }


def _stop_reason(user_key: str) -> Optional[str]:
    _keys = _key_candidates(user_key)
    with _browser_lock:
        for _k in _keys:
            st = _browser_stop.get(_k)
            if st:
                return st.get("reason")
    return None


def _grant_allows(user_key: str, action: str, params: dict) -> bool:
    _keys = _key_candidates(user_key)
    with _browser_lock:
        gr = None
        for _k in _keys:
            gr = _browser_grants.get(_k)
            if gr:
                break
    if not gr or gr.get("expires", 0) <= time.time():
        return False
    _p = params or {}
    h = _host_of(_p.get("url"))
    if not h:
        try:
            st = connection_state(user_key) or {}
            h = _host_of(st.get("url") or "")
        except Exception:
            h = ""
    if h:
        if not any(h == x or h.endswith("." + x) for x in (gr.get("hosts") or [])):
            return False
    return action in (gr.get("actions") or [])


def _needs_approval(action: str, params: dict) -> Optional[str]:
    """判断操作是否需要用户确认。返回原因或 None(自动执行)。"""
    if action == "fill":
        sel = str(params.get("selector") or "").lower()
        text = str(params.get("text") or "").lower()
        for h in _SENSITIVE_FILL_HINTS:
            if h in sel or h in text:
                return "敏感表单填写(含 %s)" % h
        # 发布类平台关键表单: 标题/正文输入也需确认(防误发)
        return None
    if action == "click":
        sel = str(params.get("selector") or "").lower()
        for h in _SENSITIVE_CLICK_HINTS:
            if h in sel:
                return "关键操作点击(含 %s)" % h
    # 2026-09-10: 外部站点交互 → 需老板在场授权(可被会话级 grant 覆盖)
    if is_external_action(action, params):
        return "外部站点交互(需老板在场并一次性授权)"
    return None


# ===== 数据分级(2026-09-11): 外发内容分级 — L4 硬拒 / L3 任务级授权 / L1L2 自动 =====
def _outbound_text(action: str, params: dict) -> str:
    """提取真正出机器的内容(fill 输入 / publish 标题+正文)。"""
    _p = params or {}
    if action == "fill":
        return str(_p.get("text") or "")
    if action == "publish":
        return str(_p.get("title") or "") + chr(10) + str(_p.get("content") or "")
    return ""


def _classify_outbound(action: str, params: dict):
    """分级外发内容。返回 (level, reason)。非外发内容动作返回 (None, "")。"""
    if action not in ("fill", "publish"):
        return None, ""
    if not is_external_action(action, params):
        return None, ""  # 本机(localhost/自家端口)不出机器, 不分级
    text = _outbound_text(action, params)
    if not text.strip():
        return None, ""
    try:
        from core.pa.classifier import classify, classify_with_reason

        lvl = classify(text)
        _r = classify_with_reason(text)
        return lvl, "、".join(_r.get("reasons") or [])
    except Exception as e:
        logger.warning("[BROWSER_LOCAL] 分级器不可用, 保守按 L3 处理: %s", e)
        return "L3", "分级器异常, 保守按原始数据 L3 处理"


def grant_data_session(user_id: str, session_id: str = "", note: str = "L3 原始数据授权") -> dict:
    """老板授权 L3 原始数据: 按任务(session_id)一次, 任务结束(换 session)即失效。"""
    _keys = _key_candidates(user_id)  # 锁外计算
    with _browser_lock:
        for _k in _keys:
            _data_grants[_k] = {"session_id": str(session_id or ""), "level": "L3", "ts": time.time(), "note": note}
    _audit(user_id, "grant-data:L3", {"session_id": str(session_id or "")}, {"success": True, "note": note})
    return {"success": True, "session_id": str(session_id or "")}


def revoke_data_session(user_id: str) -> dict:
    _keys = _key_candidates(user_id)
    with _browser_lock:
        for _k in _keys:
            _data_grants.pop(_k, None)
    return {"success": True, "revoked": True}


def _data_grant_allows(user_key: str, session_id: str) -> bool:
    """本任务(session_id)是否已授权 L3 原始数据(查全部候选键, 同 _grant_allows 语义)。"""
    _keys = _key_candidates(user_key)
    with _browser_lock:
        g = None
        for _k in _keys:
            g = _data_grants.get(_k)
            if g:
                break
    return bool(g) and str(g.get("session_id", "")) == str(session_id or "")


def pending_browser_op(user_id: str) -> Optional[dict]:
    """查询待确认的浏览器操作(供前端/审批路由)。user_id 归一化: 支持扩展 web_xxx vs Agent user-mtxxx"""
    _k = _resolve_conn_user(user_id)
    with _browser_lock:
        op = _browser_pending_ops.get(_k if _k else user_id)
        if op and op.get("status") == "pending":
            return dict(op)
        return None


# ===== P3 发布能力(publish + 发布历史) =====

_PUBLISH_HISTORY_DIR = "data/v9/publish_history"


def _publish_history_file(user_id: str):
    from pathlib import Path

    _d = Path(_PUBLISH_HISTORY_DIR)
    _d.mkdir(parents=True, exist_ok=True)
    return _d / ("%s.jsonl" % user_id)


def record_publish(user_id: str, platform: str, content_summary: str, result: dict, op_id: str = "") -> dict:
    """发布历史落盘(对齐 promo-manager publishHistory): 平台/内容摘要/时间/结果/链接"""
    import time as _t

    _rec = {
        "ts": _t.time(),
        "time": _t.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform,
        "content_summary": str(content_summary)[:200],
        "op_id": op_id,
        "success": bool(result.get("success")),
        "link": (result.get("data") or {}).get("link", "") if result.get("data") else "",
        "error": str(result.get("error", ""))[:200] if not result.get("success") else "",
    }
    try:
        with open(_publish_history_file(user_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(_rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("[BROWSER_LOCAL] publish history 落盘失败: %s", e)
    return _rec


def list_publish_history(user_id: str, limit: int = 20) -> list:
    """查询发布历史(最近 limit 条, 倒序)"""
    _f = _publish_history_file(user_id)
    _recs = []
    try:
        if _f.exists():
            for ln in _f.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                try:
                    _recs.append(json.loads(ln))
                except Exception:
                    pass
    except Exception:
        pass
    _recs.sort(key=lambda r: r.get("ts", 0), reverse=True)
    return _recs[:limit]


def _needs_publish_approval(params: dict) -> bool:
    """发布操作强制逐篇审批(无论内容)"""
    _p = params or {}
    return bool(_p.get("title") or _p.get("content") or _p.get("platform"))


def approve_browser_op(user_id: str, op_id: str, approve: bool, scope: str = "once") -> dict:
    """审批通过/拒绝浏览器操作。通过 → 立即执行(重放 op)。user_id 归一化(web_xxx vs user-mtxxx)"""
    _k = _resolve_conn_user(user_id)
    with _browser_lock:
        op = _browser_pending_ops.get(_k if _k else user_id)
        if not op or op.get("op_id") != op_id or op.get("status") != "pending":
            return {"success": False, "error": "待确认操作不存在或已过期"}
        op["status"] = "approved" if approve else "rejected"
        if approve:
            # 打指纹标记, 重放 execute 时放行(免二次审批)
            op["params"] = dict(op.get("params", {}))
            op["params"]["_op"] = _op_fingerprint(op.get("action", ""), op["params"])
        _snapshot = dict(op)
    if approve and scope == "session":
        _hosts = None
        try:
            _h = _host_of((_snapshot.get("params") or {}).get("url"))
            _hosts = [_h] if _h else None
        except Exception:
            _hosts = None
        grant_browser_session(user_id, hosts=_hosts, note="老板一次通过(op=%s)" % op_id)
    if approve and _snapshot.get("data_l3"):
        grant_data_session(user_id, _snapshot.get("data_session_id", ""), note="老板授权 L3 原始数据(按任务一次)")
    _audit(user_id, "approve:" + op["action"], op.get("params", {}), {"success": approve, "scope": scope})
    if not approve:
        return {"success": True, "status": "browser_rejected", "message": "已拒绝该浏览器操作，Agent 将调整方案。"}
    # 通过 → 重放执行(execute 检测 _op 指纹放行)
    _replay_params = {k: v for k, v in _snapshot.get("params", {}).items() if k != "_op"}
    return execute(
        user_id,
        _snapshot["action"],
        _replay_params,
        timeout=float(_snapshot.get("params", {}).get("timeout", 30)),
        session_id=_snapshot.get("params", {}).get("session_id", ""),
    )


def _policy():
    try:
        from core.gateway.shared_state import _load_v9_execution_policy

        return _load_v9_execution_policy() or {}
    except Exception:
        return {}


def _whitelist() -> List[str]:
    """域名白名单(默认小红书/抖音/B站/知乎/公众号/微博, 可配置)"""
    try:
        from core.gateway.shared_state import _load_v9_execution_policy

        _bl = (_load_v9_execution_policy() or {}).get("browser_local", {}) or {}
        return _bl.get("domain_whitelist") or [
            "xiaohongshu.com",
            "xhslink.com",
            "douyin.com",
            "iesdouyin.com",
            "bilibili.com",
            "b23.tv",
            "fanqieopen.com",
            "kol.fanqieopen.com",
            "fanqienovel.com",
            "daren.fanqienovel.com",  # 2026-08-30 番茄达人中心(提交发布/回填必需)
            "zhihu.com",
            "mp.weixin.qq.com",
            "weibo.com",
            "bytedance.larkoffice.com",  # 2026-09-07 飞书文档(官方可信)
        ]
    except Exception:
        return ["xiaohongshu.com", "douyin.com", "bilibili.com", "zhihu.com"]


def _blacklist() -> List[str]:
    """硬黑名单(支付/银行/邮箱/云盘类)"""
    return ["alipay.com", "paypal.com", "bank", "mail.", "icloud.com", "drive.google.com"]


def _host_allowed(host: str) -> bool:
    if not host:
        return False
    host = host.lower().strip()
    for b in _blacklist():
        if b in host:
            return False
    for w in _whitelist():
        if host == w or host.endswith("." + w):
            return True
    return False


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LOCAL_PORTS = {5002, 3080, 5173}


def _is_local_host(host):
    return str(host or "").lower() in LOCAL_HOSTS


def _port_of(url):
    try:
        from urllib.parse import urlparse

        u = urlparse(str(url or ""))
        if u.port is not None:
            return u.port
        return 443 if u.scheme == "https" else 80
    except Exception:
        return 0


def _url_allowed(url):
    """navigate/search URL 白名单: localhost/127.0.0.1 仅允许自家端口(5002/3080/5173), 其余本地端口(如5432)拒绝; 外部站点走 domain_whitelist。"""
    h = _host_of(url)
    if not h:
        return False
    if _is_local_host(h):
        return _port_of(url) in LOCAL_PORTS
    return _host_allowed(h)


def _is_python_client(tag) -> bool:
    """python-client 标识(tag 以 python 开头; 独立进程客户端, 无需专属标签页)。"""
    return str(tag or "").startswith("python")


def register_ws_connection(user_id: str, conn, tag: str = ""):
    """客户端连接注册(每次 WS 连接/重连调用)。

    适配 Python 客户端: 同一 user 已有 python-client 连接时, 扩展/其他客户端重连不覆盖
    (避免扩展(需标签页)覆盖独立进程, 导致 Agent 报「无专属标签页」)。
    """
    with _browser_lock:
        _existing = _browser_conns.get(user_id)
        if _existing and not _is_python_client(tag) and _is_python_client(_existing.get("tag", "")):
            logger.info("[BROWSER_LOCAL] 保留 python-client 连接 user=%s (忽略非 python 重连 tag=%s)", user_id, tag)
            return
        _browser_conns[user_id] = {
            "ws": conn,
            "connected_at": time.time(),
            "tag": tag,
            "state": {"state": "connected", "url": ""},
        }
        _browser_pending.setdefault(user_id, {})
    # #17 多实例共享: 连接元数据同步 Redis(供其他网关实例发现远端连接)
    try:
        from core.lib.v8.shared_state_redis import sync_conn_meta

        try:
            import platform as _pl

            _inst = _pl.node()
        except Exception:
            _inst = "unknown"
        sync_conn_meta(
            user_id,
            {"connected_at": time.time(), "tag": tag, "state": {"state": "connected", "url": ""}, "instance": _inst},
        )
    except Exception:
        pass
    logger.info("[BROWSER_LOCAL] 连接注册 user=%s tag=%s", user_id, tag)


def unregister_ws_connection(user_id: str, reason: str = "disconnect"):
    """连接失效(客户端断线/退出)"""
    with _browser_lock:
        prev = _browser_conns.pop(user_id, None)
        _browser_pending.pop(user_id, None)
    # #17 多实例共享: 清除远端元数据
    try:
        from core.lib.v8.shared_state_redis import clear_conn_meta

        clear_conn_meta(user_id)
    except Exception:
        pass
    if prev:
        logger.info("[BROWSER_LOCAL] 连接失效 user=%s reason=%s", user_id, reason)
    return bool(prev)


def _resolve_conn_user(user_id: str) -> Optional[str]:
    """用户 id 归一化: 连接模型 = WS 连接存在即可执行。

    - 精确匹配优先;
    - 无精确匹配时任意现存连接兜底(单机版; 多连接时优先 python-client, 否则最近连接)。
    """
    with _browser_lock:
        if user_id in _browser_conns:
            return user_id
        if _browser_conns:
            _pool = [k for k in _browser_conns if _is_python_client(_browser_conns[k].get("tag", ""))] or list(
                _browser_conns.keys()
            )
            return max(_pool, key=lambda k: _browser_conns[k].get("connected_at", 0))
    # #17 多实例共享: 本机无连接 → 查询远端实例 Redis 元数据(连接在另一网关实例上)
    try:
        from core.lib.v8.shared_state_redis import get_conn_meta

        _remote = get_conn_meta(user_id)
        if _remote and _remote.get("state", {}).get("state") == "connected":
            return user_id
    except Exception:
        pass
    return None


def is_connected(user_id: str) -> bool:
    return _resolve_conn_user(user_id) is not None


def get_connection_info(user_id: str) -> dict:
    """客户端连接状态(供 /v9/browser/status 与插件状态显示): 连接是否存在 + 客户端类型 + 状态。"""
    _k = _resolve_conn_user(user_id)
    if not _k:
        return {"connected": False, "client": "", "user_id": "", "state": {}, "login_status": {}, "verify": None}
    with _browser_lock:
        c = _browser_conns.get(_k) or {}
        tag = str(c.get("tag", ""))
        st = dict(c.get("state", {})) if c else {}
        _ca = float(c.get("connected_at") or 0)
    return {
        "connected": True,
        "client": "python-client" if _is_python_client(tag) else (tag or "unknown"),
        "user_id": _k,
        "state": st,
        "login_status": st.get("login_status", {}),
        "verify": st.get("verify"),
        # 批196: 供 PA 页显示「已连接 Ns」（老板一键启动后要能看出有没有连上）
        "connected_at": _ca,
        "age_s": round(max(0.0, time.time() - _ca), 1) if _ca else None,
    }


def connection_state(user_id: str) -> Optional[dict]:
    _k = _resolve_conn_user(user_id)
    with _browser_lock:
        c = _browser_conns.get(_k) if _k else None
        return dict(c["state"]) if c else None


def _update_state(user_id: str, state: dict):
    with _browser_lock:
        c = _browser_conns.get(user_id)
        if c:
            c["state"].update(state)


# ===== 指令收发 =====
# 同步 WS(sync serve): conn 是 websockets.sync 对象, send 是同步方法, 无需 asyncio


def _send(user_id: str, payload: dict) -> bool:
    _k = _resolve_conn_user(user_id)
    with _browser_lock:
        c = _browser_conns.get(_k) if _k else None
        conn = c["ws"] if c else None
    if conn is None:
        return False
    try:
        conn.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception as e:
        logger.warning("[BROWSER_LOCAL] send 失败: %s", e)
        return False


def _audit(user_id: str, action: str, params: dict, result: dict):
    """browser 操作审计落盘(SessionLog user_message 事件, 与工具流一致)"""
    try:
        from core.gateway.session_log import get_session_log

        _sid = params.get("session_id", "") if isinstance(params, dict) else ""
        get_session_log(_sid or user_id).append(
            "user_message",
            {
                "role": "system",
                "content": "[BROWSER_LOCAL] %s %s → success=%s" % (action, str(params)[:120], result.get("success")),
                "source": "browser_local",
            },
        )
    except Exception:
        pass


def execute(user_id: str, action: str, params: dict, timeout: float = 30.0, session_id: str = "") -> dict:
    """V9 Agent 工具入口: 发指令到本地浏览器, 等结果(同步 WS)。

    user_id 归一化: 扩展连接注册为 web_xxx, Agent 工具用 user-mtxxx, 经
    _resolve_conn_user 映射到实际连接(单机版任意连接兜底), 避免 ConnectionReset。
    """
    _conn_user = _resolve_conn_user(user_id)
    if _conn_user is None:
        return {
            "success": False,
            "error": "本地浏览器未连接。" + agent_client_hint(),
        }
    # 2026-09-10 老板随时停止: 置位后一切浏览器动作拒绝
    _stop = _stop_reason(_conn_user)
    if _stop:
        return {"success": False, "stopped": True, "error": "已被老板停止(%s)。需要继续请先 resume/grant。" % _stop}
    # 数据分级(2026-09-11): 外发内容分级 — L4 硬拒 / L3 任务级授权 / L1L2 自动
    _lvl, _lvl_reason = _classify_outbound(action, params)
    if _lvl == "L4":
        _audit(user_id, "blocked-L4:" + action, params, {"success": False, "level": "L4"})
        return {
            "success": False,
            "blocked": True,
            "level": "L4",
            "reason": "外发内容含 %s，属 L4 隐私，禁止出机器" % _lvl_reason,
            "suggestion": "脱敏后重试（去除手机号/身份证/银行卡/住址 → 变为 L2 自动放行）",
            "error": "L4 隐私数据禁止外发（%s）。请脱敏后重试。" % _lvl_reason,
        }
    # P2/P3 审批: 敏感操作(发布/提交/敏感表单)先挂起等确认; 已 approved 的重放直接放行
    if action in ("click", "fill", "publish"):
        with _browser_lock:
            _existing = _browser_pending_ops.get(_conn_user)
            # 已 approved 且参数匹配 → 放行执行(approve_browser_op 重放路径)
            _was_approved = bool(
                _existing
                and _existing.get("status") == "approved"
                and _existing.get("action") == action
                and _existing.get("params", {}).get("_op") == _op_fingerprint(action, params)
            )
        if _was_approved:
            with _browser_lock:
                _browser_pending_ops.pop(_conn_user, None)
        else:
            # P3: publish 强制逐篇审批(内容完整预览); P2: 敏感 click/fill 审批
            _reason = None
            if action == "publish":
                if _needs_publish_approval(params):
                    _reason = "发布操作需逐篇确认"
            else:
                _reason = _needs_approval(action, params)
            # L3 原始数据(2026-09-11): 任务级授权, 优先于站点级 reason; 站点级 grant 不覆盖 L3
            _data_blocked = _lvl == "L3" and not _data_grant_allows(_conn_user, session_id)
            if _data_blocked:
                _reason = "外发内容含原始数据（%s），需老板授权（按任务一次，任务结束失效）" % _lvl_reason
            if _reason and not _data_blocked and _grant_allows(_conn_user, action, params):
                _reason = None  # 会话级站点授权覆盖(老板一次通过, 不覆盖 L3 数据授权)
                _audit(user_id, "grant-allow:" + action, params, {"success": True})
            if _reason:
                op_id = uuid.uuid4().hex[:12]
                with _browser_lock:
                    _browser_pending_ops[_conn_user] = {
                        "op_id": op_id,
                        "action": action,
                        "params": dict(params or {}),
                        "ts": time.time(),
                        "status": "pending",
                        "data_l3": bool(_data_blocked),
                        "data_session_id": str(session_id or ""),
                    }
                _audit(user_id, "pending:" + action, params, {"success": False, "reason": _reason})
                return {
                    "success": False,
                    "pending": True,
                    "op_id": op_id,
                    "reason": _reason,
                    "action": action,
                    "params": params,
                    "error": "需要确认: %s" % _reason,
                }
    cmd_id = uuid.uuid4().hex[:12]
    if session_id:
        params = dict(params or {})
        params["session_id"] = session_id
    with _browser_lock:
        _browser_pending.setdefault(_conn_user, {})[cmd_id] = None  # 占位
    _update_state(_conn_user, {"state": "busy", "last_action": action})
    # (2026-09-10) 信封已带 action, params 里不再重复下发。
    # 客户端各动作的参数白名单只认业务参数(open_document 只收 path/wait_ms 等),
    # 重复的 action 键会被"不接受参数"安全校验拒掉 → 端到端全断。
    _send_params = {k: v for k, v in (params or {}).items() if k not in ("action", "session_id")}
    ok = _send(_conn_user, {"type": "exec", "cmd_id": cmd_id, "action": action, "params": _send_params})
    if not ok:
        with _browser_lock:
            _browser_pending.get(_conn_user, {}).pop(cmd_id, None)
        _result = {"success": False, "error": "指令发送失败(连接可能已断开)"}
        _audit(user_id, action, params, _result)
        if action == "publish":
            _result["publish_record"] = record_publish(
                user_id,
                str(params.get("platform", "")),
                str(params.get("title", "") or params.get("content", "")),
                _result,
                op_id="",
            )
        return _result
    # 等待结果(轮询 pending 结果; 用事件而非 sleep — 简化用 deadline 轮询)
    deadline = time.time() + timeout
    while time.time() < deadline:
        with _browser_lock:
            holder = _browser_pending.get(_conn_user, {}).get(cmd_id)
        if isinstance(holder, dict) and holder.get("done"):
            with _browser_lock:
                _browser_pending.get(_conn_user, {}).pop(cmd_id, None)
            _update_state(_conn_user, {"state": "idle"})
            _result = holder.get("result", {"success": False, "error": "empty result"})
            _audit(user_id, action, params, _result)
            # P3: 发布结果记录发布历史(成功含平台链接, 失败含错误原因)
            if action == "publish":
                _result["publish_record"] = record_publish(
                    user_id,
                    str(params.get("platform", "")),
                    str(params.get("title", "") or params.get("content", ""))[:200],
                    _result,
                    op_id=cmd_id,
                )
            return _result
        time.sleep(0.1)
    with _browser_lock:
        _browser_pending.get(_conn_user, {}).pop(cmd_id, None)
    _update_state(_conn_user, {"state": "idle"})
    _result = {"success": False, "error": "指令超时(%.0fs)" % timeout}
    _audit(user_id, action, params, _result)
    if action == "publish":
        _result["publish_record"] = record_publish(
            user_id,
            str(params.get("platform", "")),
            str(params.get("title", "") or params.get("content", "")),
            _result,
            op_id=cmd_id,
        )
    return _result


def _fail_result(data):
    """客户端失败结果 -> 规整为可读的错误。

    (2026-09-10) 原写法 `str(data)[:300]` 有两个毛病:
      1. dict 直接被 str() → 报错里全是 Python repr, 人和 PA 都难读
      2. 截断到 300 字符 → computer_use 的 how_to_enable 启用步骤被截掉,
         等于"告诉你有问题但不说怎么解决"
    这里 error 取纯字符串, 同时保留结构化字段(probe/how_to_enable/selector_diag 等)。
    """
    if isinstance(data, dict):
        _msg = data.get("error")
        if not isinstance(_msg, str):
            _msg = str(_msg if _msg is not None else data)
        out = {"success": False, "error": _msg[:500]}
        for _k in ("probe", "how_to_enable", "selector_diag", "guard_denied"):
            if _k in data:
                out[_k] = data[_k]
        return out
    return {"success": False, "error": str(data)[:500]}


def _handle_result(user_id: str, cmd_id: str, ok: bool, data):
    with _browser_lock:
        # R5(2026-08-31): browser_local 结果截断 — extract/evaluate 可能返回整页 DOM,
        # 不截断则单次结果数万字符 → 上下文爆炸(11 次调用涨到 48K/轮)。
        # 保留头尾(状态/结构可见), 中间标记截断。数据源(data)截断, 非字符串(截图等)原样。
        if ok and isinstance(data, str) and len(data) > 4000:
            data = (
                data[:2000]
                + chr(10)
                + "...[TRUNCATED] browser_local 结果原文 "
                + str(len(data))
                + " 字符, 保留头尾各 2000"
                + chr(10)
                + data[-2000:]
            )
        _browser_pending.setdefault(user_id, {})[cmd_id] = {
            "done": True,
            "result": {"success": ok, "data": data} if ok else _fail_result(data),
        }


# ===== WS 服务端 =====
# 根因修复: 原 asyncio.run(_serve()) 在 Flask threading 线程里 event loop 不处理连接
# → 握手时服务端直接关闭(客户端 ERR_CONNECTION_REFUSED / 握手失败)。
# 改用 websockets.sync(12.0 同步接口): 同步 handler + serve_forever 阻塞在线程里, 无需 event loop。


def _ws_handler_sync(websocket):
    """同步客户端连接处理: 首帧注册 user_id, 收 result/state/login_status/verify_required, 断开注销。"""
    user_id = None
    try:
        for raw in websocket:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            mtype = msg.get("type", "")
            if mtype == "hello":
                user_id = msg.get("user_id", "")
                tag = str(msg.get("tag", ""))
                register_ws_connection(user_id, websocket, tag=tag)
                websocket.send(
                    json.dumps({"type": "hello_ack", "ok": True, "whitelist": _whitelist()}, ensure_ascii=False)
                )
            elif mtype == "result" and user_id:
                _handle_result(user_id, msg.get("cmd_id", ""), bool(msg.get("ok")), msg.get("data"))
            elif mtype == "state" and user_id:
                _update_state(user_id, {"state": msg.get("state", "idle"), "url": str(msg.get("url", ""))})
            elif mtype == "login_status" and user_id:
                # Python 客户端上报平台登录态: 存连接 state, 供前端/Agent 查询
                _update_state(user_id, {"login_status": {str(msg.get("platform", "")): bool(msg.get("logged_in"))}})
            elif mtype == "verify_required" and user_id:
                # 风控验证: 存 state + 告警(Agent 侧经 exec 结果已感知, 此处供工作台显示)
                _update_state(
                    user_id,
                    {
                        "verify": {
                            "platform": str(msg.get("platform", "")),
                            "url": str(msg.get("url", "")),
                            "ts": time.time(),
                        }
                    },
                )
                logger.warning("[BROWSER_LOCAL] 用户需手动过验证 platform=%s url=%s", msg.get("platform"), msg.get("url"))
            elif mtype == "closed" and user_id:
                # 客户端退出/浏览器关闭 → 显式注销
                unregister_ws_connection(user_id, reason="client_closed")
                break
    except Exception as e:
        logger.info("[BROWSER_LOCAL] ws 异常: %s", e)
    finally:
        if user_id:
            unregister_ws_connection(user_id, reason="disconnect")


#: WS 端口之**兜底偏移**（真源 = execution_policy.browser_local.ws_port_offset）。
WS_PORT_OFFSET_DEFAULT = 5


def ws_port() -> int:
    """WS 端口 = **网关端口 + 偏移**（pm_1558 §三 裁 ⒜ · 一处定形）。

    真源二：``config/v9/execution_policy.yaml`` 之 ``browser_local.ws_port_offset``
    ＋ ``config/system/system_unified.yaml`` 之 ``services.gateway.port``（经 ``core.lib.port_config``）。

    为何**派生**（⛔ 固定值）：固定值时 5102/5103 两实例共读同键 ⇒
    WS 端口必撞 ⇒ 5103 之客户端连到 5102 之 WS（本机动作发到别实例）。
    派生 ⇒ 5102⇒5107（＝旧值 · 现役不变） ／ 5103⇒5108（错峰）。

    其他调用点(启动命令/报错文案)必须调本函数, 不得复述数值
    (否则改端口时只改一处, 另一处静默指向旧端口 —— Windows 副本曾正因此
    把本机动作发到 WSL 网关。)

    ⚠ 网关端口不可读（真源未配）⇒ 抛 ``PortUnconfigured``（fail-loud）· ⛔ 回落字面量。
    """
    off = WS_PORT_OFFSET_DEFAULT
    try:
        _bl = _policy().get("browser_local", {}) or {}
        _o = _bl.get("ws_port_offset")
        if _o is not None:
            off = int(_o)
    except Exception:
        pass
    from core.lib.port_config import gateway_port

    return int(gateway_port()) + off


def _port_in_use(host: str, port: int, timeout: float = 0.6) -> bool:
    """起前检占用（pm_1558 §三 裁 ⒞）：连得上 ⇒ 有物在听。⛔ 抛。"""
    import socket

    for _h in ("127.0.0.1", host if host not in ("0.0.0.0", "") else None):
        if not _h:
            continue
        _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _s.settimeout(timeout)
        try:
            _s.connect((_h, int(port)))
            return True
        except OSError:
            pass
        finally:
            _s.close()
    return False


# 本文件在 core/lib/v8/ 下 ⇒ 要剥四层才到仓库根(少剥一层会算成 core/scripts/agent_client)。
_REPO_AGENT_CLIENT = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
    "scripts",
    "agent_client",
)


def agent_client_hint() -> str:
    """拉起本地客户端的命令提示(端口与目录同源, 不复述)。

    ⚠ 端口取不到（真源未配）⇒ 照实明书，⛔ 抛（本函数常在报错之路上）。
    """
    try:
        _ws = str(ws_port())
    except Exception:
        _ws = "端口未配（services.gateway.port 不可读）"
    return (
        "请在 PA 页点「启动本地浏览器」，或手动运行本仓库客户端（"
        + _REPO_AGENT_CLIENT
        + "，命令示例：python agent_client.py --user-id <你的ID> --ws ws://127.0.0.1:"
        + _ws
        + " --chrome）。"
    )


def start_browser_ws(host: str = "0.0.0.0", port: int = None):
    """启动 WS 服务线程(幂等): 同步 serve 阻塞在线程里, Flask threading 兼容。"""
    global _browser_ws_server, _browser_ws_thread
    if _browser_ws_thread and _browser_ws_thread.is_alive():
        return
    if port is None:
        port = ws_port()
    # pm_1558 §三 裁 ⒞：起前检占用 ⇒ fail-loud 显形（⛔ 静默、⛔ 崩）。
    #   旧病：端口被占 ⇒ 线程内 bind 失败 ⇒ 仅一行 logger.error ⇒ 屏上⛔ 见
    #   ⇒ 本实例之本机动作静默发往别实例（同旧端口之族）。
    if _port_in_use(host, port):
        _msg = ("[BROWSER_LOCAL] ⛔ WS 端口 %d 已被占用 ⇒ 本实例之本机浏览器 ⛔ 可用"
                "（其动作或发往另一实例 —— 旧病之形）。同机多实例须错峰端口"
                "（WS 端口 = 网关端口 + ws_port_offset）。核：Get-NetTCPConnection -LocalPort %d" % (port, port))
        print(_msg)
        logger.error(_msg)
        return
    from websockets.sync.server import serve as _sync_serve

    def _run():
        global _browser_ws_server
        try:
            # websockets.sync.server.serve 无 ping_interval/ping_timeout 参数(同步接口签名不同)
            _browser_ws_server = _sync_serve(
                _ws_handler_sync,
                host,
                port,
            )
            logger.info("[BROWSER_LOCAL] WS 服务启动 ws://%s:%s (sync)", host, port)
            _browser_ws_server.serve_forever()  # 阻塞, 线程内常驻
        except Exception as _ws_err:
            logger.error("[BROWSER_LOCAL] WS 同步服务异常: %s", _ws_err)

    _browser_ws_thread = threading.Thread(target=_run, daemon=True, name="browser-local-ws")
    _browser_ws_thread.start()
    logger.info("[BROWSER_LOCAL] WS 线程启动 port=%s", port)
    # P4: 监控调度线程(与 WS 同生命周期)
    start_monitor_scheduler()


# ===== P4 自动化运营: monitor + 定时 + 回复队列 =====

_MONITOR_JOBS: Dict[str, dict] = {}  # {job_id: {"user_id","platform","target","interval","last_snapshot","status"}}
_MONITOR_LOCK = threading.Lock()
_MONITOR_SCHEDULER = None
_MONITOR_SCHEDULER_STOP = threading.Event()

_REPLY_QUEUE: Dict[
    str, list
] = {}  # {user_id: [{id, item, suggested_reply, status: pending|approved|replied|rejected, ts, result}]}
_REPLY_LOCK = threading.Lock()

_REPLY_HISTORY_DIR = "data/v9/reply_history"


# ===== monitor =====


def _monitor_key(user_id: str, platform: str, target: str) -> str:
    return "%s|%s|%s" % (user_id, platform, target)


def _snapshot_fingerprint(extract_result: dict) -> str:
    """内容快照指纹: 提取结果前 N 字符(用于变化检测)"""
    _data = extract_result.get("data") or {}
    _content = str(_data.get("content") or _data.get("results") or "")
    return _content[:2000]


def monitor_start(user_id: str, platform: str, target: str, interval: int = 60, url: str = "") -> dict:
    """启动监控: 记录初始快照, 调度线程周期 extract 对比, 变化时 notify_boss"""
    if not is_connected(user_id):
        return {"success": False, "error": "本地浏览器未连接。"}
    _k = _monitor_key(user_id, platform, target)
    # 初始快照
    _init = execute(user_id, "extract", {"url": url} if url else {}, timeout=20, session_id="")
    with _MONITOR_LOCK:
        _MONITOR_JOBS[_k] = {
            "user_id": user_id,
            "platform": platform,
            "target": target,
            "interval": max(int(interval), 10),
            "url": url,
            "last_snapshot": _snapshot_fingerprint(_init),
            "status": "running",
            "changes": 0,
        }
    _audit(user_id, "monitor:start", {"platform": platform, "target": target, "interval": interval}, {"success": True})
    return {"success": True, "job_id": _k, "initial": bool(_init.get("success"))}


def monitor_stop(user_id: str, platform: str, target: str) -> dict:
    _k = _monitor_key(user_id, platform, target)
    with _MONITOR_LOCK:
        _j = _MONITOR_JOBS.pop(_k, None)
    if _j:
        _audit(user_id, "monitor:stop", {"platform": platform, "target": target}, {"success": True})
        return {"success": True}
    return {"success": False, "error": "监控任务不存在"}


def list_monitor_jobs(user_id: str) -> list:
    with _MONITOR_LOCK:
        return [dict(v) for v in _MONITOR_JOBS.values() if v.get("user_id") == user_id]


def _monitor_check(job: dict) -> dict:
    """单次监控检查: extract 当前内容 → 对比快照 → 变化则通知"""
    _uid = job.get("user_id", "")
    _k = _monitor_key(_uid, job.get("platform", ""), job.get("target", ""))
    _cur = execute(_uid, "extract", {"url": job.get("url", "")} if job.get("url") else {}, timeout=20, session_id="")
    _fp = _snapshot_fingerprint(_cur)
    with _MONITOR_LOCK:
        _job = _MONITOR_JOBS.get(_k)
        if _job is None:
            return {"changed": False}
        _prev = _job.get("last_snapshot", "")
        _job["last_snapshot"] = _fp
        _job["last_check"] = time.time()
        _changed = bool(_prev) and _fp != _prev
        if _changed:
            _job["changes"] = _job.get("changes", 0) + 1
    if _changed:
        # 通知老板 + 加入回复队列(若平台目标匹配评论/私信模式)
        _summary = str((_cur.get("data") or {}).get("content", ""))[:120]
        try:
            from core.gateway.sandbox_util import notify_boss

            notify_boss(
                message="🖥️ [监控] %s %s 内容有更新" % (job.get("platform", ""), job.get("target", "")),
                detail="新内容: %s" % _summary,
                event_type="browser_monitor",
                level="warn",
                extra={"platform": job.get("platform", ""), "target": job.get("target", ""), "user_id": _uid},
            )
        except Exception:
            pass
        _audit(
            _uid,
            "monitor:change",
            {"platform": job.get("platform", ""), "target": job.get("target", "")},
            {"success": True, "summary": _summary},
        )
    return {"changed": _changed}


def _monitor_scheduler_loop():
    """调度线程: 每 5s 扫一次, 命中 interval 的 job 执行检查"""
    while not _MONITOR_SCHEDULER_STOP.is_set():
        try:
            with _MONITOR_LOCK:
                _jobs = [dict(v) for v in _MONITOR_JOBS.values()]
            for _j in _jobs:
                _last = _j.get("last_check", 0)
                _iv = _j.get("interval", 60)
                if time.time() - _last >= _iv:
                    try:
                        _monitor_check(_j)
                    except Exception as _mce:
                        logger.warning("[BROWSER_LOCAL] monitor check err: %s", _mce)
        except Exception:
            pass
        _MONITOR_SCHEDULER_STOP.wait(5)


def start_monitor_scheduler():
    """启动监控调度线程(幂等)"""
    global _MONITOR_SCHEDULER
    if _MONITOR_SCHEDULER and _MONITOR_SCHEDULER.is_alive():
        return
    _MONITOR_SCHEDULER_STOP.clear()
    _MONITOR_SCHEDULER = threading.Thread(target=_monitor_scheduler_loop, daemon=True, name="browser-monitor-sched")
    _MONITOR_SCHEDULER.start()


# ===== 回复队列 =====


def _reply_history_file(user_id: str):
    from pathlib import Path

    _d = Path(_REPLY_HISTORY_DIR)
    _d.mkdir(parents=True, exist_ok=True)
    return _d / ("%s.jsonl" % user_id)


def _record_reply_history(user_id: str, rec: dict):
    try:
        with open(_reply_history_file(user_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("[BROWSER_LOCAL] reply history 落盘失败: %s", e)


def enqueue_reply(user_id: str, item: dict, suggested_reply: str) -> dict:
    """监控到新内容 → 加入回复队列(待审批)"""
    _rid = uuid.uuid4().hex[:12]
    with _REPLY_LOCK:
        _REPLY_QUEUE.setdefault(user_id, []).append(
            {
                "id": _rid,
                "item": item,
                "suggested_reply": str(suggested_reply)[:500],
                "status": "pending",
                "ts": time.time(),
            }
        )
    _audit(user_id, "reply:enqueue", item, {"success": True, "reply_id": _rid})
    return {"success": True, "reply_id": _rid}


def list_reply_queue(user_id: str, status: str = "") -> list:
    with _REPLY_LOCK:
        _items = [dict(r) for r in _REPLY_QUEUE.get(user_id, [])]
    if status:
        _items = [r for r in _items if r.get("status") == status]
    _items.sort(key=lambda r: r.get("ts", 0), reverse=True)
    return _items


def approve_reply(user_id: str, reply_id: str, approve: bool, reply_text: str = "") -> dict:
    """审批回复建议: 通过 → 执行回复(本地浏览器) + 历史; 拒绝 → 标记"""
    with _REPLY_LOCK:
        _q = _REPLY_QUEUE.get(user_id, [])
        _r = next((x for x in _q if x.get("id") == reply_id), None)
        if _r is None:
            return {"success": False, "error": "回复项不存在"}
        if _r.get("status") != "pending":
            return {"success": False, "error": "回复项已处理"}
        _r["status"] = "approved" if approve else "rejected"
        _snapshot = dict(_r)
    _audit(user_id, "reply:" + ("approve" if approve else "reject"), {"reply_id": reply_id}, {"success": True})
    if not approve:
        return {"success": True, "status": "reply_rejected", "message": "已拒绝该回复建议。"}
    # 通过 → 执行回复(填回复框 + 点击发送, 走审批重放机制)
    _text = reply_text or _snapshot.get("suggested_reply", "")
    _item = _snapshot.get("item", {}) or {}
    _exec = execute(
        user_id, "fill", {"selector": _item.get("reply_selector", "textarea"), "text": _text}, timeout=20, session_id=""
    )
    _send = {"success": False}
    if _exec.get("success"):
        _send = execute(
            user_id,
            "click",
            {
                "selector": _item.get(
                    "send_selector", "button[type=submit], button:has-text('发送'), button:has-text('回复')"
                )
            },
            timeout=20,
            session_id="",
        )
    _rec = {
        "ts": time.time(),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reply_id": reply_id,
        "platform": _item.get("platform", ""),
        "target": _item.get("target", ""),
        "text": _text[:200],
        "success": bool(_send.get("success")),
        "error": str(_send.get("error", ""))[:200],
    }
    _record_reply_history(user_id, _rec)
    return {"success": bool(_send.get("success")), "status": "reply_executed", "result": _send, "reply_record": _rec}


def list_reply_history(user_id: str, limit: int = 20) -> list:
    _f = _reply_history_file(user_id)
    _recs = []
    try:
        if _f.exists():
            for ln in _f.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    try:
                        _recs.append(json.loads(ln))
                    except Exception:
                        pass
    except Exception:
        pass
    _recs.sort(key=lambda r: r.get("ts", 0), reverse=True)
    return _recs[:limit]
