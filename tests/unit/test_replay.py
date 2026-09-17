"""#6 LLM 端到端回放回归测试: 重建 / 过滤 / 与 derive_messages 一致性"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """磁盘隔离: 注册表默认落 data/session_logs/ 会跨 run 累积(JSONL 重放)"""
    import core.gateway.session_log as sl

    monkeypatch.setattr(sl, "_logs", {})
    _orig = sl.get_session_log

    def _get_iso(sid, base_dir=None):
        return _orig(sid, base_dir=tmp_path)

    monkeypatch.setattr(sl, "get_session_log", _get_iso)
    yield


def _seed(sid, extra_goal=False):
    """写一段典型事件: user → assistant(tool_calls) → tool_call → tool_result → turn_end"""
    from core.gateway.session_log import log_event

    log_event(sid, "user_message", {"role": "user", "content": "分析项目"})
    log_event(sid, "turn_start", {"turn_id": 1}, turn_id=0, step_id=0)
    log_event(
        sid,
        "assistant_message",
        {"content": "先读文件", "tool_calls": [{"id": "c1", "function": {"name": "read_file", "arguments": "{}"}}]},
        turn_id=0,
        step_id=0,
    )
    log_event(sid, "tool_call", {"name": "read_file", "call_id": "c1"}, turn_id=0, step_id=0)
    log_event(
        sid,
        "tool_result",
        {"name": "read_file", "call_id": "c1", "content": '{"ok": 1}', "success": True},
        turn_id=0,
        step_id=0,
    )
    log_event(sid, "turn_end", {"turn_id": 1, "reason": "max_tokens"}, turn_id=0, step_id=0)
    if extra_goal:
        log_event(sid, "goal_event", {"goal_id": "g1", "action": "created"})


def test_replay_rebuild():
    """回放重建: 完整对话 + turns 结构"""
    from core.gateway.replay import replay_session

    _seed("rp1")
    rep = replay_session("rp1")
    assert rep["exists"] and rep["count"] == 3, rep
    roles = [m["role"] for m in rep["messages"]]
    assert roles == ["user", "assistant", "tool"], roles
    assert rep["messages"][1]["tool_calls"][0]["id"] == "c1"
    assert rep["messages"][2]["tool_call_id"] == "c1"
    assert rep["roles"] == {"user": 1, "assistant": 1, "tool": 1}
    assert len(rep["turns"]) == 1 and rep["turns"][0]["reason"] == "max_tokens"


def test_replay_filter_only_three_roles():
    """输入过滤: 只取 user/assistant/tool; turn/goal 事件不投影"""
    from core.gateway.replay import replay_session

    _seed("rp2", extra_goal=True)
    rep = replay_session("rp2")
    assert all(m["role"] in ("user", "assistant", "tool") for m in rep["messages"])
    assert rep["count"] == 3, f"turn_start/turn_end/goal_event 不应投影: {rep['count']}"


def test_replay_matches_derive_messages():
    """与 derive_messages 一致性: replay 输出 == derive_messages, 且 verify 全过"""
    from core.gateway.replay import replay_session, verify_replay
    from core.gateway.session_log import get_session_log

    _seed("rp3")
    rep = replay_session("rp3")
    assert rep["messages"] == get_session_log("rp3").derive_messages()
    v = verify_replay("rp3")
    assert v["ok"], v["checks"]
    assert v["checks"]["roles_only"] and v["checks"]["tool_pairing"]
    assert v["checks"]["calls_resolved"] and v["checks"]["matches_derive"]


def test_replay_at_turn_window():
    """逐轮回放: at_turn=N 只含前 N 轮 assistant/tool, user 全保留"""
    from core.gateway.replay import replay_session
    from core.gateway.session_log import log_event

    _seed("rp4")
    # 第二轮: 纯文本 assistant
    log_event("rp4", "assistant_message", {"content": "第二轮总结"}, turn_id=1, step_id=0)
    log_event("rp4", "turn_end", {"turn_id": 2, "reason": "completed"}, turn_id=1, step_id=0)
    full = replay_session("rp4")
    assert full["count"] == 4, f"全量应 4 条: {full['count']}"
    t1 = replay_session("rp4", at_turn=1)
    assert t1["count"] == 3, f"at_turn=1 应 3 条(不含第二轮): {[m['role'] for m in t1['messages']]}"
    assert all(
        m.get("role") == "assistant" and "第二轮" not in str(m.get("content"))
        for m in t1["messages"]
        if m.get("role") == "assistant"
    )
    t0 = replay_session("rp4", at_turn=0)
    assert t0["count"] == 1 and t0["messages"][0]["role"] == "user", "at_turn=0 应只有 user"


def test_verify_replay_pairing_and_p2b():
    """校验: 孤儿 tool 消息 → tool_pairing False; 未执行 tool_calls → P2b 过滤后 calls_resolved True"""
    from core.gateway.replay import verify_replay
    from core.gateway.session_log import get_session_log, log_event

    # 孤儿 tool 消息(无对应 assistant tool_calls)
    log_event("rp5", "tool_result", {"call_id": "orphan", "content": "x", "success": True}, turn_id=0, step_id=0)
    v = verify_replay("rp5")
    assert not v["ok"] and not v["checks"]["tool_pairing"], v["checks"]
    # 未执行 tool_calls(P2b 过滤) → 配对仍成立
    log_event("rp6", "user_message", {"role": "user", "content": "hi"})
    log_event(
        "rp6",
        "assistant_message",
        {"content": "计划调用", "tool_calls": [{"id": "cX", "function": {"name": "read_file", "arguments": "{}"}}]},
        turn_id=0,
        step_id=0,
    )
    v2 = verify_replay("rp6")
    assert v2["ok"], v2["checks"]
    msgs = get_session_log("rp6").derive_messages()
    assert all("tool_calls" not in m for m in msgs if m.get("role") == "assistant"), "未执行的 tool_calls 应被过滤"


def test_verify_replay_expected():
    """expected 对照: 提供原 LLM 输入 → matches_expected 校验"""
    from core.gateway.replay import verify_replay
    from core.gateway.session_log import get_session_log, log_event

    log_event("rp7", "user_message", {"role": "user", "content": "任务X"})
    log_event("rp7", "assistant_message", {"content": "回复"}, turn_id=0, step_id=0)
    msgs = get_session_log("rp7").derive_messages()
    assert verify_replay("rp7", expected=msgs)["checks"]["matches_expected"] is True
    wrong = [{"role": "user", "content": "别的任务"}]
    assert verify_replay("rp7", expected=wrong)["checks"]["matches_expected"] is False


def test_replay_route_registered():
    """源码级: /v9/replay/<session_id> 路由注册, 调用 replay_session + verify_replay"""
    src = open("routes/session.py", encoding="utf-8").read()
    assert '"/v9/replay/<path:session_id>"' in src, "应注册回放路由"
    assert "from core.gateway.replay import replay_session, verify_replay" in src
    assert "at_turn" in src
