"""Turn 协议 Step2 回归测试: turn/step 事件写入 + derive_turns 回放"""
import json
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    import core.gateway.session_log as sl

    monkeypatch.setattr(sl, "_logs", {})
    # 磁盘隔离: registry 默认落 data/session_logs/ 会跨 run 累积(JSONL 重放),
    # 注入 tmp_path 使每次测试独立(与 test_session_log.py 的 tmp_path 用法一致)
    _orig_get = sl.get_session_log

    def _get_isolated(sid, base_dir=None):
        return _orig_get(sid, base_dir=tmp_path)

    monkeypatch.setattr(sl, "get_session_log", _get_isolated)
    yield


def test_bridge_loop_writes_turn_events():
    """bridge_loop 经 turn_protocol 写 turn_start/step_start/step_end/turn_end(EV_ 常量)"""
    import agent_gateway_enhanced as main
    import core.gateway.turn_protocol as tp

    src = open(main.__file__, encoding="utf-8").read()
    _LOOP = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    tsrc = open(tp.__file__, encoding="utf-8").read()
    assert "write_turn_start" in _LOOP and "write_step_start" in src, "应经 turn_protocol 写 turn/step_start"
    assert "write_step_end" in src and "_write_turn_end" in src, "应写 step_end + 统一 turn_end helper"
    assert "EV_TURN_START" in tsrc and "EV_STEP_START" in tsrc
    assert "EV_TURN_END" in tsrc and "EV_STEP_END" in tsrc


def test_bridge_uses_ev_turn_end_constant():
    """_write_turn_end 事件写入用 EV_TURN_END 常量(非字面量)"""
    import agent_gateway_enhanced as main

    src = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    assert "EV_TURN_END as _EV_TE" in src, "turn_end 事件应引用 EV_TURN_END 常量"


def test_execute_agent_task_writes_turn_events():
    """execute_agent_task 同样写 turn/step 事件(EV_ 常量) + 统一 reason"""
    import core.gateway.execute_agent_task as m

    src = open(m.__file__, encoding="utf-8").read()
    assert "EV_TURN_START" in src, "应写 turn_start(EV 常量)"
    assert "EV_STEP_START" in src and "EV_STEP_END" in src, "应写 step_start/step_end(EV 常量)"
    assert "_write_exec_turn_end" in src, "应有 exec turn_end helper"
    assert '"completed"' in src, "done 路径应写 completed"
    assert "_compute_turn_reason" in src, "exec 应调用统一 reason 计算"


def test_derive_turns_replay():
    """derive_turns 从事件重建 turn 结构"""
    from core.gateway.session_log import get_session_log, log_event

    log_event("t1", "turn_start", {"turn_id": 1}, turn_id=1, step_id=0)
    log_event("t1", "step_start", {"turn_id": 1, "step_id": 1}, turn_id=1, step_id=1)
    log_event("t1", "tool_call", {"name": "read_file", "call_id": "c1"}, turn_id=1, step_id=1)
    log_event("t1", "tool_result", {"call_id": "c1", "content": "ok", "success": True}, turn_id=1, step_id=1)
    log_event("t1", "step_end", {"turn_id": 1, "step_id": 1}, turn_id=1, step_id=1)
    log_event("t1", "turn_end", {"turn_id": 1, "reason": "completed"}, turn_id=1, step_id=1)
    turns = get_session_log("t1").derive_turns()
    assert len(turns) == 1
    assert turns[0]["turn_id"] == 1
    assert turns[0]["reason"] == "completed"
    assert turns[0]["steps"][0]["step_id"] == 1
    assert turns[0]["steps"][0]["tools"][0]["name"] == "read_file"
    assert turns[0]["steps"][0]["tools"][0]["success"] is True


def test_derive_turns_multiple_turns():
    """多个 turn 各自独立重建"""
    from core.gateway.session_log import get_session_log, log_event

    for tid in (1, 2):
        log_event("t2", "turn_start", {"turn_id": tid}, turn_id=tid, step_id=0)
        log_event("t2", "step_start", {"turn_id": tid, "step_id": 1}, turn_id=tid, step_id=1)
        log_event("t2", "step_end", {"turn_id": tid, "step_id": 1}, turn_id=tid, step_id=1)
        log_event("t2", "turn_end", {"turn_id": tid, "reason": "max_tokens"}, turn_id=tid, step_id=1)
    turns = get_session_log("t2").derive_turns()
    assert len(turns) == 2
    assert [t["turn_id"] for t in turns] == [1, 2]
    assert [t["reason"] for t in turns] == ["max_tokens", "max_tokens"]


def test_derive_turns_complements_derive_messages():
    """turns(审计)与 messages(LLM)互补: turns 含 reason, messages 含对话"""
    from core.gateway.session_log import get_session_log, log_event

    log_event("t3", "turn_start", {"turn_id": 1}, turn_id=1, step_id=0)
    log_event("t3", "user_message", {"role": "user", "content": "hi"}, turn_id=1, step_id=0)
    log_event("t3", "assistant_message", {"content": "hello"}, turn_id=1, step_id=1)
    log_event("t3", "turn_end", {"turn_id": 1, "reason": "completed"}, turn_id=1, step_id=1)
    slog = get_session_log("t3")
    turns = slog.derive_turns()
    msgs = slog.derive_messages()
    assert len(turns) == 1 and turns[0]["reason"] == "completed"
    assert [m["role"] for m in msgs] == ["user", "assistant"], "messages 应只含对话角色"
    assert all("reason" not in m for m in msgs), "messages 不应含 turn 元数据"
