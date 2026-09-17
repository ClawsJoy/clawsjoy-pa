"""P0 inbox 三通道回归测试: steer/followup/inject 语义 + failure_pause 改走 steer(修 400 断点)"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest

from core.gateway.session_log import EV_ASSISTANT_MESSAGE, EV_TOOL_CALL, EV_TOOL_RESULT, SessionLog


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    import core.gateway.shared_state as ss

    monkeypatch.setattr(ss, "_inbox", {"followup": {}, "steer": {}, "inject": {}})
    import core.gateway.session_log as sl

    monkeypatch.setattr(sl, "_logs", {})
    yield tmp_path


def test_steer_roundtrip():
    """P0: steer 通道 add → drain 返回并清空; 二次 drain 为空"""
    from core.gateway.shared_state import add_steer, drain_steer

    add_steer("sx", "提示A")
    add_steer("sx", "提示B")
    got = drain_steer("sx")
    assert got == ["提示A", "提示B"], f"drain 应返回全部并清空: {got}"
    assert drain_steer("sx") == [], "二次 drain 应为空(不累积)"


def test_followup_inject_semantics():
    """P0: followup drain 清空; inject peek 不清空"""
    from core.gateway.shared_state import add_followup, add_inject, drain_followup, peek_inject

    add_followup("sy", "下个turn消息")
    assert drain_followup("sy") == ["下个turn消息"]
    assert drain_followup("sy") == []
    add_inject("sy", "system前缀")
    assert peek_inject("sy") == ["system前缀"], "peek 应返回不消费"
    assert peek_inject("sy") == ["system前缀"], "peek 二次仍返回(不消费)"


def test_steer_truncated_to_500():
    """P0: steer 内容超长截断到 500 字符(防 token 膨胀)"""
    from core.gateway.shared_state import add_steer, drain_steer

    add_steer("sz", "长" * 1000)
    got = drain_steer("sz")
    assert len(got) == 1 and len(got[0]) <= 500, f"应截断到 500: {len(got[0]) if got else 0}"


def test_tool_router_failure_steer_instead_of_user_event(tmp_path):
    """P0 核心: 连续失败>=5 → 走 steer 通道(不再写 user_message 事件, 防投影配对破坏→400)"""
    from core.gateway.shared_state import drain_steer
    from core.gateway.tool_router import _check_consecutive_failure

    # 行为级: 3 次失败后 drain_steer 出现提示(断点2 阈值 5→3)
    for _i in range(3):
        _r = _check_consecutive_failure({"success": False, "error": "boom"}, "read_file", "s_fail1")
    assert _r.get("success") is False
    _steer = drain_steer("s_fail1")
    assert _steer and "换一个工具或路径" in _steer[0], f"失败提示应进 steer: {_steer}"
    # 事件级: SessionLog 不应出现 failure_pause 的 user_message(投影配对完好)
    log = SessionLog("s_fail1", base_dir=tmp_path)
    log.append(EV_ASSISTANT_MESSAGE, {"content": "", "tool_calls": [{"id": "c1"}]})
    log.append(EV_TOOL_CALL, {"name": "read_file", "arguments": {}, "call_id": "c1"})
    log.append(EV_TOOL_RESULT, {"name": "read_file", "call_id": "c1", "content": "{}", "success": False})
    for _i in range(5):
        _check_consecutive_failure({"success": False, "error": "boom"}, "read_file", "s_fail1")
    msgs = log.derive_messages()
    # assistant(tool_calls) 后紧跟 tool 结果, 中间不得插入 user/system
    assert msgs[0].get("tool_calls"), "assistant 应保留 tool_calls"
    assert msgs[1]["role"] == "tool" and msgs[1]["tool_call_id"] == "c1", f"tool 结果应紧随 assistant: {msgs}"
    assert len(msgs) == 2, f"投影不得因失败提示新增消息: {msgs}"


def test_tool_router_source_no_user_event():
    """P0 源码级: tool_router 失败提示已改 add_steer, 不再 log_event(user_message)"""
    src = open("core/gateway/tool_router.py", encoding="utf-8").read()
    assert "add_steer(session_id" in src, "应调用 add_steer"
    assert 'log_event(session_id, "user_message"' not in src, "不应再写 user_message 事件"
    assert "换一个工具或路径" in src


def test_bridge_loop_round_start_drains_steer():
    """P0 源码级: bridge_loop 每轮开始 drain_steer 并注入 user 消息（S6-A 归位 round_start）"""
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "drain_steer(session_id)" in src, "bridge_loop 应每轮消费 steer"
    assert (
        'messages = messages + [{"role": "user", "content": str(_s)[:500]} for _s in _steer_msgs]' in src
    ), "steer 应注入为 user 消息"
    # S6-A 归位后: steer 消费在 round_start(轮首), 结构上早于 llm_call 的 execute_with_tools


def test_bridge_loop_turn_start_drains_followup():
    """P0 源码级: bridge_loop turn 开始 drain_followup 注入为最新 user 指令"""
    src = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    assert "drain_followup(session_id)" in src, "turn 开始应消费 followup"
    assert (
        'messages = messages + [{"role": "user", "content": str(_f)[:2000]} for _f in _followups]' in src
    ), "followup 应注入为 user 消息"
    # 消费发生在 _init_bridge_state（函数头初始化，早于骨架的 for 循环）
    assert "for _bridge_round" not in src, "loop.py 只含初始化，不应含轮循环"
