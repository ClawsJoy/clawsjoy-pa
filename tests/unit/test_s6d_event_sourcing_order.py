# -*- coding: utf-8 -*-
"""S6-D 事件溯源双写顺序测试锁: assistant_message → tool_call → tool_result。
顺序敏感是 S6-D 最大风险, 每拆一段(D1/D2/D3/D4)都跑本锁。
实现: 源码级断言 tool_runner.py + agent_gateway_enhanced.py 合并源码中三事件的先后。
"""
import sys

sys.path.insert(0, ".")
import pytest


def test_s6d_event_sourcing_order():
    """S6-D 事件溯源双写顺序: assistant_message → tool_call → tool_result"""
    tr = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    main = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    combined = tr + "\n" + main  # tool_runner(pre/exec 阶段) 先于 main
    i_assistant = combined.find('log_event(session_id, "assistant_message"')
    i_tool_call = combined.find('log_event(session_id, "tool_call"')
    i_tool_result = combined.find('log_event(session_id, "tool_result"')
    assert i_assistant >= 0, "缺 assistant_message 事件溯源"
    assert i_tool_call >= 0, "缺 tool_call 事件溯源"
    assert i_tool_result >= 0, "缺 tool_result 事件溯源"
    assert (
        i_assistant < i_tool_call < i_tool_result
    ), f"顺序应为 assistant_message → tool_call → tool_result: {i_assistant} {i_tool_call} {i_tool_result}"


def test_s6d_assistant_reasoning_content_key():
    """tool_calls assistant 必须带 reasoning_content 键(值可空串) — 防 DeepSeek 400"""
    tr = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "reasoning_content" in tr, "assistant 应带 reasoning_content 键"
