# -*- coding: utf-8 -*-
"""会话上下文清理核心（/v9/session/clean 路由 + V5 /clean 指令共用）。

清运行态（messages 快照 / pending / plan / goal / 检索缓存 / 配额计数 / subtask 已完成状态）。
保留归档/审计（user_messages / tool_audit / tool_flow）——审计链完整性。只清会话状态，不删除用户文件。
"""

import json
from pathlib import Path

from core.gateway.write_gate import _get_pending_lock, _pending_writes, _plan_pending


def _clean_session_context(user_id, session_id):
    """清理会话上下文核心（/v9/session/clean 路由 + V5 /clean 指令共用）

    清运行态（messages 快照 / pending / plan / goal / 检索缓存 / 配额计数 /
    subtask 已完成状态）。
    保留归档/审计（user_messages / tool_audit / tool_flow）——审计链完整性。
    只清会话状态，不删除用户文件。
    """
    # 1) 内存 pending 状态（加锁）
    try:
        with _get_pending_lock():
            _pending_writes.pop(session_id, None)
    except Exception:
        pass
    _plan_pending.pop(session_id, None)
    # 2) goal 状态
    try:
        from core.gateway.goal_state import _goal_lock as _goal_lock_state
        from core.gateway.goal_state import _goals as _goals_state

        with _goal_lock_state:
            _goals_state.pop(f"{user_id}:{session_id}", None)
    except Exception:
        pass
    # 3) 任务快照 messages（.task_state.json 保留文件结构，仅清 messages）
    _cl_snap = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.task_state.json")
    if _cl_snap.exists():
        try:
            _cl_st = json.loads(_cl_snap.read_text(encoding="utf-8"))
            if isinstance(_cl_st, dict):
                _cl_st["messages"] = []
                _cl_st["task_name"] = ""
                _cl_snap.write_text(json.dumps(_cl_st, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    # 4) .agent_state.json 的 pending_writes 持久化字段（_persist_pending_writes 残留，防止恢复时复活）
    _cl_st_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
    if _cl_st_file.exists():
        try:
            _cl_st2 = json.loads(_cl_st_file.read_text(encoding="utf-8"))
            if isinstance(_cl_st2, dict) and "pending_writes" in _cl_st2:
                _cl_st2.pop("pending_writes", None)
                _cl_st_file.write_text(json.dumps(_cl_st2, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    # 5) 运行态缓存/计数（session 级前缀匹配：k == sid 或 k.startswith(sid + "_")，覆盖子任务后缀 key）
    try:
        from core.gateway.shared_state import (
            _consecutive_lists,
            _consecutive_reads,
            _query_cache,
            _retry_cache,
            _search_empty_cache,
        )

        for _cache in (_query_cache, _search_empty_cache, _retry_cache):
            for _ck in [k for k in list(_cache.keys()) if k == session_id or str(k).startswith(session_id + "_")]:
                _cache.pop(_ck, None)
        for _counter in (_consecutive_reads, _consecutive_lists):
            _counter.pop(session_id, None)
    except Exception:
        pass
    try:
        from core.gateway.tool_router import _consecutive_failures

        _consecutive_failures.pop(session_id, None)
    except Exception:
        pass
    # 6) subtask 状态（done/failed 清；running/queued 保留——执行不中断，前端显示不丢）
    try:
        from core.gateway.subtask_executor import _subtask_lock, _subtasks

        with _subtask_lock:
            _st_map = _subtasks.get(f"{user_id}:{session_id}", {})
            for _tid in [t for t, e in list(_st_map.items()) if e.get("status") in ("done", "failed")]:
                _st_map.pop(_tid, None)
    except Exception:
        pass
