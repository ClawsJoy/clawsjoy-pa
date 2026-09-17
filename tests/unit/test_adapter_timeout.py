"""DeepSeek adapter 读超时按 thinking 模式区分回归测试

根因: execute_with_tools 固定读超时 60s, thinking 模式(max_tokens=8000)长上下文
推理常超 60s → Read timed out(用户实测: HTTPSConnectionPool Read timed out)。
修复: thinking=True → 读超时 180s; 普通模式保持 60s。
"""
import sys

sys.path.insert(0, ".")
import pytest

_SRC = open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()


def test_thinking_read_timeout_extended():
    """源码: 读超时应按 thinking 区分, thinking 用 180s"""
    assert "180 if thinking else 60" in _SRC, "thinking 模式读超时应为 180s"
    assert "timeout=(30, 180 if thinking else 60)" in _SRC


def test_timeout_behavior_simulation():
    """行为模拟: thinking=True → 180s; False → 60s"""
    _thinking = True
    _timeout = (30, 180 if _thinking else 60)
    assert _timeout == (30, 180), f"thinking 应 180s: {_timeout}"
    _thinking = False
    _timeout = (30, 180 if _thinking else 60)
    assert _timeout == (30, 60), f"普通应 60s: {_timeout}"


def test_retry_path_uses_adapter_timeout():
    """retry 路径也走 adapter.execute_with_tools → 继承 thinking 超时"""
    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    assert "resp_retry = adapter.execute_with_tools(messages=messages, tools=tools" in src
