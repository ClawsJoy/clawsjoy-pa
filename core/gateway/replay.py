"""#6 LLM 端到端回放 — 从 SessionLog 事件日志重建完整对话

前置: session_log.py 事件日志(SessionEvent JSONL) + derive_messages(投影) + derive_turns。

- replay_session(session_id)   → 重建完整对话(仅 user/assistant/tool 投影消息, 与 bridge_loop
  每轮喂给 adapter.execute_with_tools 的输入同源 — P2b 已确立 derive_messages 为唯一入口)
- replay_session(at_turn=N)    → 回放到第 N 轮 LLM 调用前的输入(逐轮 step-through)
- replay_messages(session_id)  → 仅返回消息列表(路由便捷)
- verify_replay(session_id)    → 一致性校验: 角色白名单 / assistant tool_calls 与 tool 响应配对
  / 与 derive_messages 全等(可选 expected 对照)
"""
import json
from typing import Dict, List, Optional

from core.gateway.session_log import (
    get_session_log,
    EV_USER_MESSAGE,
    EV_ASSISTANT_MESSAGE,
    EV_TOOL_RESULT,
    EV_TOOL_CALL,
)

# 回放白名单: 仅这三类事件投影为 LLM 消息(与 derive_messages 一致)
_REPLAY_ROLES = {"user", "assistant", "tool"}


def _resolved_ids(events):
    """已收到 tool_result 的 call_id 集合(P2b 过滤未执行 tool_calls 用)"""
    return {
        ev.payload.get("call_id")
        for ev in events
        if ev.type == EV_TOOL_RESULT and ev.payload.get("call_id")
    }


def replay_session(session_id: str, at_turn: Optional[int] = None) -> Dict:
    """从事件日志重建完整对话(LLM 调用输入等价)。

    at_turn=None → 全量重建(== derive_messages)。
    at_turn=N    → 第 N 轮 LLM 调用前的输入窗口: user 消息全保留,
                   assistant/tool 事件仅取 turn_id < N(排除本轮及之后)。
    """
    slog = get_session_log(session_id)
    events = list(slog._events)
    msgs = _derive_upto(events, at_turn)
    return {
        "session_id": session_id,
        "exists": bool(events),
        "messages": msgs,
        "count": len(msgs),
        "roles": _role_breakdown(msgs),
        "source": "session_log",
        "events": len(events),
        "turns": slog.derive_turns(),
        "at_turn": at_turn,
    }


def _derive_upto(events, at_turn: Optional[int] = None) -> List[dict]:
    """回放窗口投影: 与 derive_messages 同规则。

    at_turn=None → 全量(所有 assistant/tool 事件); at_turn=N → 仅取 turn_id < N 的
    assistant/tool 事件(user 消息全保留)。独立实现, 供与 session_log.derive_messages 交叉校验。
    """
    _resolved = _resolved_ids(events)  # 全量结果集(容忍跨轮乱序)
    msgs = []
    for ev in events:
        if ev.type == EV_USER_MESSAGE:
            _m = {"role": ev.payload.get("role", "user"), "content": ev.payload.get("content", "")}
            _m.update(ev.payload.get("extra", {}))
            msgs.append(_m)
        elif ev.type == EV_ASSISTANT_MESSAGE and (at_turn is None or (ev.turn_id or 0) < at_turn):
            m = {"role": "assistant", "content": ev.payload.get("content", "")}
            if ev.payload.get("tool_calls"):
                _valid = [tc for tc in ev.payload["tool_calls"]
                          if isinstance(tc, dict) and tc.get("id") in _resolved]
                if _valid:
                    m["tool_calls"] = _valid
            # 与 derive_messages 同规则: 带 tool_calls 的 assistant 必须带 reasoning_content 字符串(可为空)
            if isinstance(ev.payload.get("reasoning_content"), str):
                m["reasoning_content"] = ev.payload["reasoning_content"]
            elif m.get("tool_calls"):
                m["reasoning_content"] = ""
            msgs.append(m)
        elif ev.type == EV_TOOL_RESULT and (at_turn is None or (ev.turn_id or 0) < at_turn):
            msgs.append({"role": "tool", "tool_call_id": ev.payload.get("call_id", ""),
                         "content": ev.payload.get("content", "")})
    return msgs


def replay_messages(session_id: str) -> List[dict]:
    """便捷: 仅返回重建消息列表。"""
    return get_session_log(session_id).derive_messages()


def verify_replay(session_id: str, expected: Optional[list] = None) -> Dict:
    """回放一致性校验。

    checks:
      - roles_only:      投影角色 ⊆ {user, assistant, tool}(输入过滤正确)
      - tool_pairing:    每条 tool 消息的 call_id 都能在 assistant tool_calls 中找到(配对)
      - calls_resolved:  assistant 的每个 tool_calls 都有 tool 响应(P2b 过滤后无悬挂)
      - matches_derive:  重建 == get_session_log().derive_messages()(与投影一致性)
      - matches_expected: 与调用方提供的原 LLM 输入全等(可选 expected)
    """
    slog = get_session_log(session_id)
    events = list(slog._events)
    msgs = slog.derive_messages()
    # 交叉校验: replay.py 独立投影实现 vs session_log.derive_messages(防实现漂移)
    _own = _derive_upto(events, None)
    checks = {
        "roles_only": set(m.get("role") for m in msgs) <= _REPLAY_ROLES,
        "tool_pairing": True,
        "calls_resolved": True,
        "matches_derive": _own == msgs,
    }
    if expected is not None:
        checks["matches_expected"] = msgs == expected
    _tool_ids = {m.get("tool_call_id") for m in msgs if m.get("role") == "tool"}
    _call_ids = {tc.get("id") for m in msgs if m.get("role") == "assistant"
                 for tc in (m.get("tool_calls") or [])}
    for _tid in _tool_ids:
        if _tid not in _call_ids:
            checks["tool_pairing"] = False
    for m in msgs:
        if m.get("role") == "assistant":
            for tc in (m.get("tool_calls") or []):
                if tc.get("id") not in _tool_ids:
                    checks["calls_resolved"] = False
    return {
        "session_id": session_id,
        "ok": all(checks.values()),
        "checks": checks,
        "count": len(msgs),
    }


def _role_breakdown(msgs: List[dict]) -> Dict[str, int]:
    from collections import Counter
    return dict(Counter(m.get("role", "?") for m in msgs))


__all__ = ["replay_session", "replay_messages", "verify_replay", "_REPLAY_ROLES"]
