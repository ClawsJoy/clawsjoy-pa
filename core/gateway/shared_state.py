import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path

import psutil
import yaml
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

from core.lib.precision_feed import _init_precision_feed_cache, _load_asset, _precision_feed_cache
from core.lib.sandbox_tools import _generate_project_tree

"""共享全局状态 — 从 agent_gateway_enhanced.py 抽取

所有需要跨模块访问的全局变量集中在这里。
主网关和执行模块都从这里 import，避免循环依赖。
"""

# ===== Session 追踪 =====
_session_write_tracker = {}
_session_git_tracker = {}
_session_tool_tracker = {}
# #106 P1 tracker 并发锁：跨请求共享 dict 的读改写保护
_tracker_lock = None


def _get_tracker_lock():
    """延迟初始化全局 tracker 锁（避免 import 顺序问题）"""
    global _tracker_lock
    if _tracker_lock is None:
        import threading as _th_tk

        _tracker_lock = _th_tk.Lock()
    return _tracker_lock


def _tracker_setdefault(tracker, session_id, factory):
    """加锁的 setdefault：防止跨请求对同一 session 的 tracker 并发写覆盖"""
    with _get_tracker_lock():
        if session_id not in tracker:
            tracker[session_id] = factory()
        return tracker[session_id]


# ===== V9 default session auto-assign (从 agent_gateway_enhanced 归位) =====
_V9_DEFAULT_SESSION_LOCK = None


def _v9_default_session_lock():
    global _V9_DEFAULT_SESSION_LOCK
    if _V9_DEFAULT_SESSION_LOCK is None:
        _V9_DEFAULT_SESSION_LOCK = threading.Lock()
    return _V9_DEFAULT_SESSION_LOCK


def _resolve_v9_session_id(user_id, raw_session_id):
    if raw_session_id and str(raw_session_id).strip() and str(raw_session_id).strip() != "default":
        return str(raw_session_id).strip(), False
    uid = str(user_id or "default").strip() or "default"
    _map_file = Path(_PROJECT_ROOT) / "data" / "projects" / uid / ".v9_default_session.json"
    with _v9_default_session_lock():
        try:
            if _map_file.exists():
                _d = json.loads(_map_file.read_text(encoding="utf-8"))
                if _d.get("session_id"):
                    return str(_d["session_id"]), False
        except Exception:
            pass
        _new_sid = "v9auto_" + uuid.uuid4().hex[:12]
        try:
            _map_file.parent.mkdir(parents=True, exist_ok=True)
            _map_file.write_text(
                json.dumps(
                    {"user_id": uid, "session_id": _new_sid, "created": time.time()}, ensure_ascii=False, indent=2
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
        print("[V9_SESSION] default session auto-assign: user=" + uid + " -> " + _new_sid)
        return _new_sid, True


# ===== 搜索缓存 =====
_search_file_cache = {}
_search_empty_cache = {}
_search_empty_task = {}

# ===== SAG 索引缓存 =====
_sag_index_cache = {}

# ===== 自动合并冷却 =====
_auto_merge_cooldown = {}

# ===== 文件读取缓存 =====
_read_cache = {}
_intercept_cache = {}
_session_artifacts = {}
_content_hashes = {}
_recursion_tracker = {}
# R2(2026-08-30 架构根治): read_file 内容缓存幂等 — session 级 {session_id: {path_md5: content_hash}}
# 同 session 重复读同一路径且内容未变 → 返回 cached 标记, 不再重复全量注入上下文(防重复信息膨胀)
_read_content_cache = {}


def _invalidate_read_content_cache(session_id=None, path_key=None):
    """R2: 文件变更后失效 read_file 内容缓存。写工具(sandbox_write)成功后调用。

    幂等: 无匹配条目时静默。path_key 为空 → 清整个 session(保守, 防漏)。
    S3(2026-09-05): 同服务同时失效统一执行缓存(_tool_exec_cache)。
    """
    try:
        if session_id is None:
            _read_content_cache.clear()
            _tool_exec_cache.clear()
            return
        if path_key is None:
            _read_content_cache.pop(session_id, None)
            _tool_exec_cache.pop(session_id, None)
            return
        _sess = _read_content_cache.get(session_id)
        if _sess:
            _sess.pop(path_key, None)
        _tool_exec_cache.pop(session_id, None)
    except Exception:
        pass


# ===== S3(2026-09-05): 统一执行缓存(合并 L4 同参缓存; R2 内容缓存同一文件/同一失效入口) =====
_tool_exec_cache = {}  # session_id -> {key: {"r": result, "stat": sig}}
_TOOL_EXEC_READISH = {
    "read_file",
    "list_dir",
    "search_files",
    "query_index",
    "fetch_web",
    "browse_web",
    "obsidian_knowledge",
}
_TOOL_EXEC_LOCK = None
_EMPTY_REQUIRED = {
    "write_file": "path",
    "write_large": "path",
    "edit_file": "path",
    "execute_command": "command",
    "read_file": "path",
    # (2026-09-05) action 类工具空参(封面任务 obsidian_knowledge() 反复无 action → 未知 action: None)
    "obsidian_knowledge": "action",
    "browser_hybrid": "action",
    "cu_learning": "action",
    "playwright_browser": "action",
    "browser_local": "action",
    # (2026-09-07 修复) fetch_web/browse_web schema 与 handler 只要求 url(action 非其参数) —
    # 误标 action 使每次调用都被拦「缺少 action」→ 模型反复空参重试烧步数(红果漫剧调研 8+ 次)。
    "browse_web": "url",
    "fetch_web": "url",
}


def empty_arg_error(tool, args):
    """S3: 空参校验单点逻辑(write/命令/读工具缺必填 → 错误文案; 桥接与守卫共用)。

    write_file 的 reason 强制在桥接 agent 路径单独执行(2026-09-07, 见 bridge):
    守卫层保持 reason 宽容(卡内带提示), 避免波及非 agent 写入路径。
    """
    req = _EMPTY_REQUIRED.get(tool)
    if req and not str((args or {}).get(req) or "").strip():
        return "%s 缺少必填参数 %s(空参调用, 直接拦截, 不触发审批)" % (tool, req)
    return ""


# (2026-09-07) 浏览器不可用标记 — 熔断 Agent 对 browser_local/playwright_browser 的反复重试
_BROWSER_UNAVAIL_MARKERS = (
    "browser has been closed",
    "浏览器不可用",
    "Target page, context or browser",
    "browser or context has been closed",
)


def browser_unavailable_error(result):
    """工具结果是否为「浏览器实例不可用」(不可用属环境问题, 重试无益 → 熔断提示换路)。

    返回错误文本(命中)或 ""(未命中/成功)。browser_local/playwright_browser 连 2 次命中
    → 桥接注入换路 steer(2026-09-07 红果漫剧调研反复重试 5+ 次烧步数根因之二)。
    """
    if not isinstance(result, dict) or result.get("success"):
        return ""
    err = str(result.get("error") or "")
    if any(_m in err for _m in _BROWSER_UNAVAIL_MARKERS):
        return err[:160]
    return ""


# (2026-09-07) 通用「环境阻塞」标记 — 登录墙/空表/无限重定向/页面加载不出/浏览器不可用。
# Agent 面对这类阻塞常"换法硬闯"(逐格读 canvas/反复 extract/换抓取工具)烧预算;
# 同一任务累计 ≥3 次 → 桥接注入硬收敛(EnvBlockGuard): 报告阻塞请老板提供 登录态/CSV/截图。
_ENV_BLOCK_MARKERS = (
    "浏览器不可用",
    "browser has been closed",
    "需登录",
    "登录墙",
    "未登录",
    "0 行",
    "未检测到表格",
    "infinite redirect",
    "无限重定向",
    "HTTP 302",
    "HTTPError",
    "加载中",
    "Target page, context or browser",
)


def env_block_error(result):
    """工具结果是否属「环境阻塞」(非可重试瞬时错误)。返回命中文本或 ""。"""
    if not isinstance(result, dict) or result.get("success"):
        return ""
    err = str(result.get("error") or "")
    hits = [_m for _m in _ENV_BLOCK_MARKERS if _m in err]
    if hits:
        return hits[0]
    return ""


def _tool_exec_key(tool, args):
    import hashlib as _h

    return _h.md5(
        (tool + "|" + json.dumps(args, ensure_ascii=False, sort_keys=True, default=str)).encode("utf-8", "ignore")
    ).hexdigest()


def _vault_file_for_stat(args):
    """把 obsidian_knowledge 的 read 目标解析成真实文件路径(拿不到就 None)。"""
    a = args or {}
    if str(a.get("action") or "") != "read":
        return None
    key = str(a.get("sop_key") or a.get("path") or "").strip()
    if not key or ("/" not in key and not key.endswith(".md")):
        return None  # 固定键(平台发布工作流 等)不走这里, 靠写侧失效兜底
    try:
        import os as _os2

        from core.gateway.precision_inject import _vault_path as _vp

        p = _os2.path.join(str(_vp()), key)
        return p if _os2.path.exists(p) else None
    except Exception:
        return None


def _tool_stat_sig(tool, args):
    """路径类工具(读文件/列目录/vault 笔记)记录 mtime+size, 变更即失效(防 stale 复用)。

    2026-09-13 修(bug #6): 此前只认 read_file/list_dir —— 而 obsidian_knowledge 也在
    _TOOL_EXEC_READISH 里(会被缓存), 却拿不到 stat 签名 → 缓存条目**永不失效**。
    """
    try:
        import os as _os

        if tool == "obsidian_knowledge":
            path = _vault_file_for_stat(args)
            if not path:
                return None
        else:
            path = str((args or {}).get("path") or "")
            if not path or tool not in ("read_file", "list_dir"):
                return None
        if not _os.path.exists(path):
            return "missing"
        st = _os.stat(path)
        return "%d:%d" % (st.st_mtime_ns, st.st_size)
    except Exception:
        return None


def tool_exec_cache_get(session_id, tool, args, with_meta=False):
    """执行级同参缓存(读类工具): 命中且未过期(mtime/size 一致) → 返回结果 dict。

    with_meta=True 时额外附 `_cached_at`(快照时点) —— 默认关闭, 不改变既有返回契约
    (2026-09-13: 一开始无条件加, 被 test_l4_output_policy 的「返回与写入一致」断言当场抓住;
     改成 opt-in, 契约不动, 需要时点的调用方显式索取)。
    """
    global _TOOL_EXEC_LOCK
    if _TOOL_EXEC_LOCK is None:
        import threading as _th

        _TOOL_EXEC_LOCK = _th.Lock()
    key = _tool_exec_key(tool, args)
    with _TOOL_EXEC_LOCK:
        e = (_tool_exec_cache.get(session_id) or {}).get(key)
        if e is None:
            return None
        sig = _tool_stat_sig(tool, args)
        if sig is not None and e.get("stat") != sig:
            (_tool_exec_cache.get(session_id) or {}).pop(key, None)
            return None
        r = dict(e.get("r") or {})
        if with_meta and e.get("at"):
            r["_cached_at"] = e["at"]  # 快照时点(opt-in): 调用方据此判断这是不是旧快照
        return r


def tool_exec_cache_put(session_id, tool, args, result):
    """执行级同参缓存写入(仅读类且成功); 写工具成功由 _invalidate_read_content_cache 统一失效。"""
    global _TOOL_EXEC_LOCK
    if _TOOL_EXEC_LOCK is None:
        import threading as _th

        _TOOL_EXEC_LOCK = _th.Lock()
    if tool not in _TOOL_EXEC_READISH or not (result and result.get("success")):
        return
    key = _tool_exec_key(tool, args)
    with _TOOL_EXEC_LOCK:
        import time as _t_put

        _tool_exec_cache.setdefault(session_id, {})[key] = {
            "r": dict(result),
            "stat": _tool_stat_sig(tool, args),
            "at": _t_put.strftime("%Y-%m-%d %H:%M:%S"),
        }


# ===== 后台任务 =====
_background_tasks = {}
_fake_done_count = {}
_code_indexers = {}

# ===== 连续操作计数器 =====
# #106 C1 并发修复：配额计数改 per-session dict（原模块级整数多线程串扰）
_consecutive_reads = {}  # session_id -> 读取计数
_consecutive_lists = {}  # session_id -> list_dir 计数
_last_read_fingerprints = []

# ===== JS 回滚 =====
_js_rollback_count = {}

# ===== 连续失败自动暂停（#86）=====
_consecutive_failures = {}  # {session_id: count} — 工具连续失败计数
_paused_breakpoints = {}  # {session_id: {tool, count, at, reason, last_error}} — 强制暂停断点
_consecutive_lock = None  # P3: 连续失败计数并发锁(并行工具池多线程递增需互斥)


def _get_consecutive_lock():
    """P3: 连续失败计数器并发锁(延迟初始化; tool_router 并行路径使用)"""
    global _consecutive_lock
    if _consecutive_lock is None:
        import threading as _th_cf

        _consecutive_lock = _th_cf.Lock()
    return _consecutive_lock


# ===== inbox 三通道（P0: followup/steer/inject）=====
# 每项: {session_id: [text,...]}。drain 后即清, 不累积。
_inbox = {"followup": {}, "steer": {}, "inject": {}}  # session_id -> list[str]
_inbox_lock = None


def _get_inbox_lock():
    """inbox 并发锁(延迟初始化)"""
    global _inbox_lock
    if _inbox_lock is None:
        import threading as _th_ib

        _inbox_lock = _th_ib.Lock()
    return _inbox_lock


def add_steer(session_id, text):
    """steer 通道: 下一 step 指导, 不开启新 turn。bridge_loop 每轮消费注入 LLM 输入。"""
    if not session_id or not text:
        return
    with _get_inbox_lock():
        _inbox["steer"].setdefault(session_id, []).append(str(text)[:500])


def add_followup(session_id, text):
    """followup 通道: 下一 turn 输入(新任务/追问), 开启新 turn 时消费。"""
    if not session_id or not text:
        return
    with _get_inbox_lock():
        _inbox["followup"].setdefault(session_id, []).append(str(text)[:2000])


def add_inject(session_id, text):
    """inject 通道: 静默附加上下文(不唤醒), 作为 system 上下文注入。"""
    if not session_id or not text:
        return
    with _get_inbox_lock():
        _inbox["inject"].setdefault(session_id, []).append(str(text)[:2000])


def drain_steer(session_id):
    """消费 steer 队列(取走并清空)。返回 list[str] 或 []。"""
    with _get_inbox_lock():
        items = _inbox["steer"].pop(session_id, [])
    return list(items)


def drain_followup(session_id):
    """消费 followup 队列。返回 list[str] 或 []。"""
    with _get_inbox_lock():
        items = _inbox["followup"].pop(session_id, [])
    return list(items)


def peek_inject(session_id):
    """只读 inject 上下文(不消费, 供 system 前缀拼接)。"""
    with _get_inbox_lock():
        items = _inbox["inject"].get(session_id, [])
    return list(items)


# ===== #1 协作取消(AbortSignal): {session_id: threading.Event} — 不硬杀, 标记后下轮退出 =====
_cancel_flags = {}

# ===== 完成核验重试计数（2026-09-13，接 verifier）=====
# 完成分支跑 run_verification_chain 未通过 → 把 failures 回灌让 agent 续跑；
# 但不能无限续跑（会被 max_bridge_rounds=100 兜住，但会白烧 token），故设会话级上限。
_verification_retry = {}  # session_id -> 已重试次数

# ===== 续跑哨兵（2026-09-13，统一 vault 写守卫用）=====
# 用途：完成核验触发续跑时置位，续跑期间**禁止写 vault**（防一次误判污染知识库）。
# 为什么必须在**运行时**置位而不是写进文档：vault 写有三条互不相同的通道
#   ① obsidian_knowledge（core/lib/gateway_helpers.py 的 _handle_obsidian_knowledge）
#   ② cu_learning.persist_sop（直调 write_vault_note，绕过 ①）
#   ③ execute_command（core/gateway/security.py 的 _SYS_ESCAPE_PATTERNS **不含 /mnt**，不拦）
# 只在一条上加规矩必漏另两条 → 哨兵置位后由工具执行统一入口（tool_runner._run_item）裁决。
_continuation = {}  # session_id -> True


def set_continuation(session_id, on=True):
    """置/清续跑哨兵。契约：返回当前值。"""
    try:
        if on:
            _continuation[session_id] = True
        else:
            _continuation.pop(session_id, None)
        return bool(_continuation.get(session_id))
    except Exception:
        return False


def is_continuation(session_id):
    """是否处于「续跑轮」。"""
    try:
        return bool(_continuation.get(session_id))
    except Exception:
        return False


VERIFICATION_RETRY_CAP = 2  # 最多回灌 2 次；第 3 次不再拦，交回正常完成（防卡死）


def verification_retry_bump(session_id, cap=VERIFICATION_RETRY_CAP):
    """返回本次是否**允许**再回灌一次（True=允许，并自增计数）。契约：超限返回 False 且不再自增。"""
    try:
        n = int(_verification_retry.get(session_id, 0))
        if n >= int(cap):
            return False
        _verification_retry[session_id] = n + 1
        return True
    except Exception:
        return False


def verification_retry_reset(session_id=None):
    """清计数（新 turn 开始时调用；session_id 为空清全部）。"""
    try:
        if session_id is None:
            _verification_retry.clear()
        else:
            _verification_retry.pop(session_id, None)
    except Exception:
        pass


_cancel_lock = None


def _get_cancel_lock():
    """取消标志并发锁(延迟初始化)"""
    global _cancel_lock
    if _cancel_lock is None:
        import threading as _th_c

        _cancel_lock = _th_c.Lock()
    return _cancel_lock


def request_cancel(session_id):
    """请求协作取消(置位)。幂等。"""
    if not session_id:
        return
    with _get_cancel_lock():
        _cancel_flags.setdefault(session_id, _new_cancel_event()).set()


def reset_cancel(session_id):
    """新任务开始前清旧取消标记(防误杀新任务)。"""
    if not session_id:
        return
    with _get_cancel_lock():
        _cancel_flags.pop(session_id, None)


def is_cancel_requested(session_id):
    """检查是否请求取消(每轮/每工具前调用, 廉价 is_set)。"""
    if not session_id:
        return False
    with _get_cancel_lock():
        ev = _cancel_flags.get(session_id)
    return bool(ev and ev.is_set())


def _new_cancel_event():
    import threading as _th_c2

    return _th_c2.Event()


# ===== 审批已批准文件指纹(死循环修复): {session_id: {path: ts}} =====
# 同 session 同文件首次审批通过后, 后续 write_file 该文件免审 —
# Agent 分片/重试时每次生成新 tool_call_id, 若只按 id 放行则反复弹审批。
_approved_files = {}
_approved_files_lock = None


def _get_approved_files_lock():
    """已批准文件集并发锁(延迟初始化)"""
    global _approved_files_lock
    if _approved_files_lock is None:
        import threading as _th_af

        _approved_files_lock = _th_af.Lock()
    return _approved_files_lock


def _norm_approval_path(path):
    """审批路径归一化: 去掉 clawsjoy_dev/ 前缀与首尾 /, 用 basename 兜底。
    修复(2026-08-30): Agent 重试时 path 在 相对/绝对/带前缀 间切换,
    精确匹配失败 → 同文件反复弹审批(用户确认 N 次循环)。"""
    p = str(path or "").strip()
    p = p.split("clawsjoy_dev/", 1)[-1]
    p = p.lstrip("/")
    return p


def mark_file_approved(session_id, path):
    """审批通过后记录文件指纹(同 session 后续该文件写入免审)。"""
    if not session_id or not path:
        return
    with _get_approved_files_lock():
        _approved_files.setdefault(session_id, {})[_norm_approval_path(path)] = time.time()


_last_compact = {}


def set_last_compact(session_id, stats):
    """批189 · #5：记录本 session 最近一次上下文压缩统计（供 done 载荷回给前端显示）。"""
    if not session_id or not isinstance(stats, dict):
        return
    try:
        _last_compact[str(session_id)] = dict(stats)
    except Exception:
        pass


def get_last_compact(session_id):
    """读最近一次压缩统计；无则 {}。"""
    try:
        return dict(_last_compact.get(str(session_id)) or {})
    except Exception:
        return {}


def clear_last_compact(session_id):
    """批191 · #5 补完：回合**开始**清空本 session 的压缩统计。

    为什么必须清：统计是「最近一次压缩」，若本轮没压缩，done 载荷会带上**上一轮**的数字
    ⇒ 前端显示「已压缩 N 条」而本轮其实没压缩 = 假可见。
    """
    try:
        _last_compact.pop(str(session_id), None)
    except Exception:
        pass


def approved_files(session_id, within_s=None):
    """批188 · 缺陷2：返回本 session 已批准的文件路径（可按时间窗过滤）。

    用途：**审批后补执行的写入不在本 turn 的 tool_steps 里**（审批路径
    core/gateway/approval.py::_handle_write_approval 直接执行、不 append tool_step）
    ⇒ 链核验会报「未检测到任何成功写入记录」（假失败）。
    这里只把它当**线索**：真伪仍由产物存在性/体积/内容判定（**不制造假绿**）。
    """
    if not session_id:
        return []
    _now = time.time()
    with _get_approved_files_lock():
        _m = dict(_approved_files.get(session_id) or {})
    _out = []
    for _p, _ts in _m.items():
        try:
            if within_s is not None and (_now - float(_ts or 0)) > float(within_s):
                continue
        except Exception:
            pass
        _out.append(_p)
    return sorted(_out)


def is_file_approved(session_id, path):
    """检查文件是否已在本 session 批准(免审)。相对/绝对/带前缀路径均可命中。"""
    if not session_id or not path:
        return False
    with _get_approved_files_lock():
        _m = _approved_files.get(session_id) or {}
        return _norm_approval_path(path) in _m


def clear_approved_files(session_id=None):
    """清已批准指纹(会话清理/新任务)。None 清全部。"""
    with _get_approved_files_lock():
        if session_id is None:
            _approved_files.clear()
        else:
            _approved_files.pop(session_id, None)


# ===== #12 工具优先级抢占: {session_id: [{priority, ts, reason, target_tool, requester}]} =====
# 高优先级任务到达时登记抢占请求; 调度器每工具执行前检查, 当前工具优先级 < 请求优先级 → 打断。
# 防饿死(#12审核): 同一 session 同一工具连续被抢占 >= _PREEMPT_MAX_STARVE 次 → 放行该工具(忽略后续抢占)
_PREEMPT_MAX_STARVE = 3
_preempt_requests = {}
_preempt_starve = {}  # {(session_id, tool): count} — 同工具连续被抢占计数
_preempt_lock = None


def _get_preempt_lock():
    """抢占请求并发锁(延迟初始化)"""
    global _preempt_lock
    if _preempt_lock is None:
        import threading as _th_p

        _preempt_lock = _th_p.Lock()
    return _preempt_lock


def request_preempt(session_id, priority, reason="", target_tool=None, requester="boss"):
    """登记高优先级抢占请求(紧急任务打断低优工具)。

    priority: 请求优先级(数字越大越紧急, 与工具优先级同尺度)
    target_tool: 可选, 指定要打断的工具(None = 打断所有低于该优先级的工具)
    """
    if not session_id:
        return
    import time as _th_t

    with _get_preempt_lock():
        _preempt_requests.setdefault(session_id, []).append(
            {
                "priority": int(priority),
                "ts": _th_t.time(),
                "reason": str(reason or "")[:200],
                "target_tool": target_tool,
                "requester": str(requester or "boss")[:40],
            }
        )
        # 按优先级降序, 同优先级按时间升序(先进先抢)
        _preempt_requests[session_id].sort(key=lambda r: (-r["priority"], r["ts"]))


def drain_preempt(session_id, current_priority=0, current_tool=""):
    """调度器每工具执行前调用: 检查是否有比当前工具优先级更高的抢占请求。

    返回最高优先级请求 dict 或 None(无抢占 / 请求优先级不高于当前工具)。
    消费语义: 返回即认为该请求已被响应(从队列移除), 防止重复打断。
    """
    if not session_id:
        return None
    global _preempt_starve
    with _get_preempt_lock():
        _reqs = _preempt_requests.get(session_id)
        if not _reqs:
            return None
        # 只看最高优先级请求
        _top = _reqs[0]
        if _top["priority"] <= int(current_priority):
            return None
        if _top.get("target_tool") and _top["target_tool"] != current_tool:
            return None
        # 防饿死: 同一工具连续被抢占达上限 → 放行(消费该请求但不再打断, 保低优任务能推进)
        _sk = (session_id, str(current_tool or ""))
        _sc = _preempt_starve.get(_sk, 0)
        if _sc >= _PREEMPT_MAX_STARVE:
            _reqs.pop(0)
            if not _reqs:
                _preempt_requests.pop(session_id, None)
            _preempt_starve.pop(_sk, None)  # 放行后重置(后续新请求重新计数)
            print(f"[PREEMPT] 防饿死放行 {current_tool}(已连续被抢占 {_sc} 次)")
            return None
        _preempt_starve[_sk] = _sc + 1
        _reqs.pop(0)
        if not _reqs:
            _preempt_requests.pop(session_id, None)
        return _top


def peek_preempt(session_id):
    """只读当前最高抢占请求(不消费)。"""
    if not session_id:
        return None
    with _get_preempt_lock():
        _reqs = _preempt_requests.get(session_id)
        return dict(_reqs[0]) if _reqs else None


def clear_preempt(session_id):
    """清空该 session 全部抢占请求 + 防饿死计数(任务结束/取消时)。"""
    if not session_id:
        return
    global _preempt_starve
    with _get_preempt_lock():
        _preempt_requests.pop(session_id, None)
        _preempt_starve = {k: v for k, v in _preempt_starve.items() if k[0] != session_id}


# ===== 工具分发共享上下文（P2c: messages 单例已删, 由 session_log.derive_messages() 替代）=====
_round = 0
_task_name_async = ""
_code_indexer = None

__all__ = [
    "_session_write_tracker",
    "_session_git_tracker",
    "_session_tool_tracker",
    "_tracker_setdefault",
    "_resolve_v9_session_id",
    "_v9_default_session_lock",
    "_search_file_cache",
    "_search_empty_cache",
    "_search_empty_task",
    "_sag_index_cache",
    "_auto_merge_cooldown",
    "_read_cache",
    "_intercept_cache",
    "_session_artifacts",
    "_content_hashes",
    "_recursion_tracker",
    "_background_tasks",
    "_fake_done_count",
    "_code_indexers",
    "_consecutive_reads",
    "_consecutive_lists",
    "_last_read_fingerprints",
    "_js_rollback_count",
    "_consecutive_failures",
    "_paused_breakpoints",
    "_consecutive_lock",
    "_get_consecutive_lock",
    "_inbox",
    "add_steer",
    "add_followup",
    "add_inject",
    "drain_steer",
    "drain_followup",
    "peek_inject",
    "_cancel_flags",
    "request_cancel",
    "reset_cancel",
    "is_cancel_requested",
    "_round",
    "_task_name_async",
    "_code_indexer",
]

_EXECUTION_POLICY_CACHE = None

# ===== 常量与缓存 =====
_PROJECT_ROOT = os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent.parent))
_keyword_cache = {"keywords": None, "last_updated": 0}
_layer_store = {}
_query_melt_cache = {}  # 查询循环熔断计数器
_query_empty_cache = {}  # 同一 query 连续返回空计数器
_query_cache = {}
_retry_cache = {}
_session_failed = {}  # {session_id: timestamp}，5分钟自动恢复
_RETRIEVAL_CACHE_FILE = "data/v8/retrieval_cache.json"
_policy = None


def _load_v9_execution_policy():
    """加载 config/v9/execution_policy.yaml 执行策略，失败返回 {}（模块级缓存）。"""
    global _EXECUTION_POLICY_CACHE
    if _EXECUTION_POLICY_CACHE is not None:
        return _EXECUTION_POLICY_CACHE
    try:
        _p = Path("config/v9/execution_policy.yaml")
        if not _p.exists():
            return {}
        with open(_p, "r", encoding="utf-8") as _f:
            _EXECUTION_POLICY_CACHE = yaml.safe_load(_f) or {}
            return _EXECUTION_POLICY_CACHE
    except Exception as _e:
        print(f"[EXEC_POLICY] V9 execution policy 加载失败: {_e}")
        return {}


# ===== 沙箱常量 =====
_SANDBOX_ENV = {
    k: v
    for k, v in os.environ.items()
    if k
    in {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "PYTHONIOENCODING",
        "PYTHONPATH",
        "TMPDIR",
        "TEMP",
        "TMP",
        "PWD",
        "VIRTUAL_ENV",
        "SYSTEMROOT",
        "USER",
        "LOGNAME",
        # #27: 透传代理变量(yt-dlp/下载/外网访问需要; 代理仅指向本机 clash)
        "http_proxy",
        "https_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "no_proxy",
        "NO_PROXY",
    }
}
# 统一 heredoc 标记列表（模块级单一定义）：三处使用点共享，取并集（#192）
_HEREDOC_MARKERS = [
    "<< 'PYEOF'",
    '<< "PYEOF"',
    "<< 'EOF'",
    '<< "EOF"',
    "<< 'REGISTER_EOF'",
    "<< 'ENDOFFILE'",
    "<< 'HEREDOC_END'",
    "<<-",
    "<< ",
]


def _strip_quoted_and_comments(text):
    """剥离单/双引号字符串与 # 注释内容（保留长度占位），
    避免注释/字符串字面量中的 heredoc 标记误触发检测（#192）"""
    out = []
    i, n = 0, len(text)
    quote = None
    while i < n:
        ch = text[i]
        if quote is not None:
            out.append(" ")
            if ch == "\\" and i + 1 < n:
                out.append(" ")
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(" ")
            i += 1
            continue
        if ch == "#":
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# ========== 守卫机制日志（print 同时追加写入 logs/） ==========
def _guard_log(tag, msg, logfile):
    """守卫机制日志：print 同时追加写入 logs/<logfile>"""
    print(msg)
    try:
        _log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(_log_dir, exist_ok=True)
        with open(os.path.join(_log_dir, logfile), "a", encoding="utf-8") as _f:
            _f.write(msg + "\n")
    except Exception:
        pass


logger = logging.getLogger(__name__)
# ========== 命令分类器 ==========
_READ_CMDS = {
    "cat",
    "head",
    "tail",
    "ls",
    "find",
    "grep",
    "wc",
    "sort",
    "diff",
    "cut",
    "tr",
    "file",
    "stat",
    "which",
    "echo",
    "printf",
    "awk",
    "sed",
    "du",
    "df",
    "free",
    "ps",
    "top",
    "htop",
    "uptime",
    "uname",
    "whoami",
    "id",
    "env",
    "printenv",
    "pwd",
    "date",
    "cal",
    "true",
    "false",
    "test",
    "[",
    "expr",
    "basename",
    "dirname",
    "realpath",
    "readlink",
    "xargs",
    "tee",
    "fc-list",
    "fc-match",
    "fc-cache",
    "curl",
    "wget",
    "git",
}
_WRITE_CMDS = {
    "cp",
    "mv",
    "rm",
    "mkdir",
    "rmdir",
    "touch",
    "chmod",
    "chown",
    "ln",
    "dd",
    "mount",
    "umount",
    "mkfs",
    "tar",
    "zip",
    "unzip",
    "gzip",
    "gunzip",
    "rsync",
    "scp",
    "ssh",
    "systemctl",
    "service",
    "kill",
    "killall",
    "pkill",
    "reboot",
    "shutdown",
    "init",
    "poweroff",
    "halt",
}


_SAFE_EXEC_CMDS = {"python3", "python", "bash", "sh"}


ALLOWED_COMMANDS = [
    "python",
    "python3",
    "pip",
    "grep",
    "cat",
    "ls",
    "pwd",
    "echo",
    "pytest",
    "node",
    "npm",
    "head",
    "tail",
    "wc",
    "find",
    "cd",
    "go",
    "gofmt",
    "psql",
    "which",
    "pg_isready",
    "sleep",
    "timeout",
    "mkdir",
    "rm",
    "mv",
    "cp",
    "git",
]

# ===== P0: 收编注册到 V9Context 容器(零行为变化 — 容器持有 dict 引用, 业务代码仍操作原变量) =====
# 见 docs/reports/v9context_p0_design.md §3.1。置于文件末尾: 所有变量已定义。
# P2 才做真正的 per-scope 迁移(业务改为 ctx.get)。
try:
    from core.os.context import get_v9_context as _get_v9_ctx_p0

    _v9_ctx_p0 = _get_v9_ctx_p0()
    _v9_ctx_p0.provide(
        "shared_state",
        {
            # per-session 追踪器(P2 迁 V9Scope)
            "_session_write_tracker": _session_write_tracker,
            "_session_git_tracker": _session_git_tracker,
            "_session_tool_tracker": _session_tool_tracker,
            "_consecutive_reads": _consecutive_reads,
            "_consecutive_lists": _consecutive_lists,
            "_consecutive_failures": _consecutive_failures,
            "_paused_breakpoints": _paused_breakpoints,
            "_js_rollback_count": _js_rollback_count,
            # 单值共享上下文(P2 迁 scope)
            "_round": _round,
            "_task_name_async": _task_name_async,
            "_code_indexer": _code_indexer,
            # 进程级缓存(保持全局)
            "_search_file_cache": _search_file_cache,
            "_search_empty_cache": _search_empty_cache,
            "_search_empty_task": _search_empty_task,
            "_sag_index_cache": _sag_index_cache,
            "_auto_merge_cooldown": _auto_merge_cooldown,
            "_read_cache": _read_cache,
            "_intercept_cache": _intercept_cache,
            "_session_artifacts": _session_artifacts,
            "_content_hashes": _content_hashes,
            "_recursion_tracker": _recursion_tracker,
            "_query_melt_cache": _query_melt_cache,
            "_query_empty_cache": _query_empty_cache,
            "_query_cache": _query_cache,
            "_retry_cache": _retry_cache,
            "_session_failed": _session_failed,
        },
    )
except Exception as _ss_ctx_err:
    print(f"[SHARED_STATE] P0 容器收编失败(不影响运行): {_ss_ctx_err}")
