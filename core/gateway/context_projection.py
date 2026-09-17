"""#2 运行时上下文投影 — 当前策略快照渲染为持久 user 消息

- render_policy_snapshot(user_id, session_id, approval) → 实时策略快照 dict
  (沙箱模式/审批模式/工具指导; 内容每次从 live 状态读取)
- project_runtime_context(session_id, snapshot) → 指纹比对: 变化才返回渲染文本(≤600字), 未变 None
- "不从日志重建": 内容源为实时策略状态; 注入决策靠内存指纹缓存, 不从 SessionLog 推导

bridge_loop 每轮开始调用, 返回文本时追加为持久 user 消息 + 写 user_message 事件
(轮起始位, 不破坏 assistant tool_call/tool_result 配对 — 与 P0 steer 同安全位)。
"""
import json
import threading
from typing import Dict, Optional

from core.gateway.shared_state import _load_v9_execution_policy

# 内存指纹缓存: {session_id: fingerprint} — 变化才追加
_snapshot_cache: Dict[str, str] = {}
_snapshot_lock = threading.Lock()

_MAX_SNAPSHOT_LEN = 600


def render_policy_snapshot(user_id: str, session_id: str, approval: Optional[Dict] = None) -> Dict:
    """实时策略快照(每次从 live 状态读取)。

    approval: bridge 传入 {write_pending: bool, plan_pending: bool}
    (_pending_writes/_plan_pending 在 agent_gateway 模块级, 避免循环依赖)。
    """
    _pol = _load_v9_execution_policy() or {}
    _eb = _pol.get("execution_budget", {}) or {}
    _read = _pol.get("read_policy", {}) or {}
    _write = _pol.get("write_policy", {}) or {}
    _forbidden = _pol.get("forbidden", []) or []
    _task_types = _pol.get("task_types", {}) or {}
    _ws = _pol.get("workspace", {}) or {}
    # 沙箱根(模式标识): 取 basename, 避免绝对路径漂移
    try:
        from core.lib.gateway_helpers import _get_sandbox_base

        _sb = str(_get_sandbox_base(user_id, session_id) or "")
    except Exception:
        _sb = ""
    _sb_name = _sb.rstrip("/").split("/")[-1] if _sb else ""
    _ap = approval or {}
    return {
        "sandbox_mode": {
            "root": _sb_name,
            "project_prefix": _ws.get("project_prefix", "clawsjoy_dev/"),
            "forbidden_prefix": _ws.get("forbidden_prefix", ""),
        },
        "approval_mode": {
            "write_pending": bool(_ap.get("write_pending")),
            "plan_pending": bool(_ap.get("plan_pending")),
        },
        "tool_guidance": {
            "read": {
                "max_files": _read.get("max_files", 5),
                "max_list_dir": _read.get("max_list_dir", 3),
                "prefer_query_index": _read.get("prefer_query_index", True),
            },
            "write": {
                "small_edit": _write.get("small_edit", ""),
                "large_edit": _write.get("large_edit", ""),
                "comment_style": _write.get("comment_style", "#"),
            },
            "forbidden": list(_forbidden)[:3],
            "exclusive_tools": list(
                _eb.get("exclusive_tools", ["write_file", "write_large", "edit_file", "execute_command"])
            ),
            "max_parallel_tools": int(_eb.get("max_parallel_tools", 4) or 0),
        },
        "task_types": {k: (v or {}).get("deliverable", "") for k, v in list(_task_types.items())[:3]},
    }


def _render_text(snap: Dict) -> str:
    """快照渲染为紧凑中文文本(≤600 字符)。"""
    _s = snap.get("sandbox_mode", {})
    _a = snap.get("approval_mode", {})
    _t = snap.get("tool_guidance", {})
    _r = _t.get("read", {})
    _w = _t.get("write", {})
    _tt = snap.get("task_types", {})
    parts = ["[系统] 当前运行环境快照："]
    parts.append(
        f"沙箱：{_s.get('root', '') or '?'}(前缀 {_s.get('project_prefix', '')}"
        f"{' / 禁止 ' + str(_s.get('forbidden_prefix', '')) if _s.get('forbidden_prefix') else ''})"
    )
    _apn = []
    if _a.get("write_pending"):
        _apn.append("写操作待老板确认")
    if _a.get("plan_pending"):
        _apn.append("计划待老板确认")
    parts.append(f"审批：{'、'.join(_apn) if _apn else '无待确认'}")
    parts.append(
        f"读策略：单次最多 {_r.get('max_files', 5)} 文件 / list {_r.get('max_list_dir', 3)} 目录"
        f"({'优先 query_index' if _r.get('prefer_query_index') else ''})"
    )
    parts.append(
        f"写策略：{_w.get('small_edit', '') or '小改行级'}; {_w.get('large_edit', '') or '大改用完整写入'}"
        f"({_w.get('comment_style', '#')} 注释)"
    )
    if _t.get("forbidden"):
        parts.append(f"禁止：{'、'.join(str(x)[:20] for x in _t['forbidden'])}")
    parts.append(f"工具：并行上限 {_t.get('max_parallel_tools', 4)}; 串行工具 " f"{'/'.join(_t.get('exclusive_tools', []))}")
    if _tt:
        _tt_txt = "；".join(f"{k}({v})" for k, v in list(_tt.items())[:3] if v)
        if _tt_txt:
            parts.append(f"任务类型：{_tt_txt}")
    parts.append("[约定] 只读探测用 read_file / list_dir / search_files；不要用 python3 -c 做只读探测（会被判「任意代码」转审批）")  # 批186 · B3
    return " ".join(parts)[:_MAX_SNAPSHOT_LEN]


def project_runtime_context(session_id: str, snapshot: Dict) -> Optional[str]:
    """指纹比对: 变化 → 缓存并返回渲染文本; 未变 → None(不重复注入)。"""
    if not session_id:
        return None
    try:
        _fp = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
    except Exception:
        return None
    with _snapshot_lock:
        if _snapshot_cache.get(session_id) == _fp:
            return None
        _snapshot_cache[session_id] = _fp
    return _render_text(snapshot)


def reset_context_projection(session_id: str) -> None:
    """清指纹缓存(强制下次注入; 新任务/新会话时可调用)。"""
    with _snapshot_lock:
        _snapshot_cache.pop(session_id, None)


__all__ = ["render_policy_snapshot", "project_runtime_context", "reset_context_projection"]
