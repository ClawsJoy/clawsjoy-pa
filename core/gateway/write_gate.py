# -*- coding: utf-8 -*-
"""Write Approval Gate（写审批核心状态与函数）。

从 agent_gateway_enhanced.py 归位而来（2026-09-12，纯搬移无逻辑改动）。

职责：
- 待审批写操作状态 _pending_writes（含批量 batch/items/content/reason）
- 待审批多文件计划 _plan_pending
- 并发锁 + TTL 过期清理
- 会话恢复持久化（.agent_state.json 的 pending_writes 字段）
- 子任务审批隔离清理服务（经 V9Context 容器供 core 侧取用）

不 import 主文件（无循环依赖）。审批 handler（_handle_write_approval 等）仍在主文件。
"""

import json
import time
from pathlib import Path

# #102 锚点A：写操作前确认（Write Approval Gate）
# session_id → {"id": tool_call_id, "tool": str, "path": str, "content_preview": str,
#               "command": str, "ts": float, "approved": bool}
_pending_writes = {}

# #101 G2 计划确认强制：多文件/多意图任务先列计划等确认
# session_id → {"ts": float, "approved": bool, "plan": str, "files": [str], "intents": int}
_plan_pending = {}

# #106 C5：pending 并发锁 + TTL（60s 过期清理）；threading 延迟工厂
_pending_lock = None
_PENDING_TTL = 300.0  # 2026-08-30 对齐 harness: 审批 60s 过短(大文章/多文件审核不够), 放宽到 5 分钟; 过期显式提示非假成功


def _get_pending_lock():
    global _pending_lock
    if _pending_lock is None:
        import threading as _th_lock

        _pending_lock = _th_lock.Lock()
    return _pending_lock


def _persist_pending_writes(user_id, session_id):
    """#106 会话恢复：把未确认的 pending 写操作落盘到 .agent_state.json 的 pending_writes 字段。
    仅保存可展示信息（path/content_preview/ts），完整续跑依赖前端回传 messages。
    """
    try:
        _st_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
        from core.gateway.state_json import read_json, update_json
        _st = read_json(_st_file)      # 批220：容错读
        # 2026-08-24 防御: 旧版本曾把 pending_writes 写成字符串(双重序列化) → 解析回 dict 再合并
        if isinstance(_st.get("pending_writes"), str):
            try:
                _pw_str_fix = json.loads(_st["pending_writes"])
                if isinstance(_pw_str_fix, dict):
                    _st["pending_writes"] = _pw_str_fix
            except Exception:
                _st["pending_writes"] = {}
        _now = time.time()
        # 仅保留未过期（TTL 内）的 pending；清理历史过期项
        _valid = {}
        for sid, p in _pending_writes.items():
            if _now - p.get("ts", 0) <= _PENDING_TTL:
                # 完整 content 也持久化(2026-08-29 修复): 跨轮/恢复场景 pending.content 丢失
                # → 确认时 fallback 用 500 字符 preview → 覆盖大文件新内容被截断成 1 行 → 相似度 0% 误拒。
                # 限长 100KB 防 .agent_state.json 膨胀(超限仍只存 preview, 恢复场景尽力而为)。
                # R3(2026-08-30): 批量结构(batch/items)与 reason 持久化
                _pw_fields = {"id", "tool", "path", "content_preview", "ts", "reason", "command", "batch"}
                _c_full = p.get("content") or ""
                if _c_full and len(_c_full) <= 100 * 1024:
                    _pw_fields.add("content")
                _items_raw = p.get("items") if p.get("batch") else None
                if _items_raw:
                    _items_save = []
                    for _it in _items_raw:
                        _it_save = {
                            k: _it.get(k)
                            for k in ("id", "tool", "path", "content_preview", "ts", "reason", "command")
                            if k in _it
                        }
                        _it_c = _it.get("content") or ""
                        if _it_c and len(_it_c) <= 100 * 1024:
                            _it_save["content"] = _it_c
                        _items_save.append(_it_save)
                    _valid[sid] = {k: p.get(k) for k in _pw_fields if k in p}
                    _valid[sid]["items"] = _items_save
                else:
                    _valid[sid] = {k: p.get(k) for k in _pw_fields}
        _st["pending_writes"] = _valid
        update_json(_st_file, lambda _d: (_d.clear(), _d.update(_st)))   # 批220：原子写
    except Exception as _pw_err:
        print(f"[WRITE_GATE] pending 落盘失败: {_pw_err}")


def _pending_cleanup(now=None):
    """清理过期的 pending 写操作（TTL 60s）"""
    if now is None:
        now = time.time()
    with _get_pending_lock():
        _expired = [sid for sid, p in _pending_writes.items() if now - p.get("ts", 0) > _PENDING_TTL]
        for sid in _expired:
            _pending_writes.pop(sid, None)
            print(f"[WRITE_GATE] pending 已过期清理: {sid}")


def _clear_pending_write(session_key):
    """#76 反依赖解耦: 按会话 key 清除残留 pending 写审批态(子任务审批隔离用)。

    供 V9Context 容器注册为服务, 供 core/gateway 底层模块(如 subtask_executor)
    经容器取用, 不 import 本网关主文件(防循环依赖)。
    """
    with _get_pending_lock():
        _pending_writes.pop(session_key, None)


# #76 反依赖解耦: 把 pending 写清理服务注册进 V9Context 容器(幂等, 测试/重载安全)
try:
    from core.os.context import get_v9_context as _get_v9_ctx_76

    _v9_ctx_76 = _get_v9_ctx_76()
    if not _v9_ctx_76.has("pending_writes_cleaner"):
        _v9_ctx_76.provide("pending_writes_cleaner", _clear_pending_write)
except Exception as _reg76_err:
    print(f"[V9CTX] pending_writes_cleaner 注册失败(忽略): {_reg76_err}")


__all__ = [
    "_pending_writes",
    "_plan_pending",
    "_pending_lock",
    "_PENDING_TTL",
    "_get_pending_lock",
    "_persist_pending_writes",
    "_pending_cleanup",
    "_clear_pending_write",
]


def _v9_restore_pending_writes(user_id, session_id):
    """H1 提取: 会话恢复 - 内存无 pending 但落盘有时恢复(老板可 approve/reject)。"""
    # #15 P0: 恢复前触发 TTL 清理(过期 pending 不恢复)
    try:
        _pending_cleanup()
    except Exception:
        pass
    # #106 会话恢复：内存无 pending 但落盘有 → 恢复（老板可 approve/reject）
    if not _pending_writes.get(session_id):
        try:
            _st_restore = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
            if _st_restore.exists():
                _st_data = json.loads(_st_restore.read_text(encoding="utf-8"))
                # 2026-08-24 容错: 旧数据 pending_writes 可能被双重序列化成字符串
                _pw_stored = _st_data.get("pending_writes", {}) or {}
                if isinstance(_pw_stored, str):
                    try:
                        _pw_stored = json.loads(_pw_stored) or {}
                    except Exception:
                        _pw_stored = {}
                _pw_saved = (_pw_stored or {}).get(session_id)
                if _pw_saved and isinstance(_pw_saved, dict):
                    # content 恢复带回(2026-08-29 修复): 跨轮确认时用完整内容(非 preview 截断)
                    _pending_writes[session_id] = {
                        "id": _pw_saved.get("id", ""),
                        "tool": _pw_saved.get("tool", "write_file"),
                        "path": _pw_saved.get("path", ""),
                        "content_preview": _pw_saved.get("content_preview", ""),
                        "content": _pw_saved.get("content", ""),
                        "command": "",
                        "ts": _pw_saved.get("ts", time.time()),
                        "approved": False,
                    }
                    print(f"[WRITE_GATE] 已恢复未确认写操作: {_pending_writes[session_id].get('path','')[:60]}")
        except Exception:
            pass
