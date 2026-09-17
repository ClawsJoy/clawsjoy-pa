"""暂停恢复: bridge loop 在 _guard_paused 时返回 status=paused 载荷 + 恢复指令"""
import sys

sys.path.insert(0, ".")
import pytest

_SRC = open("agent_gateway_enhanced.py", encoding="utf-8").read()
import core.gateway.turn_protocol as _tp

_TP = open(_tp.__file__, encoding="utf-8").read()
_RB = open("core/gateway/v9_bridge/response_builder.py", encoding="utf-8").read()


def test_paused_reason_branch():
    """reason 计算有 paused 分支(集中式 _compute_turn_reason, 不误报 completed/max_tokens)"""
    assert '"paused"' in _RB, "网关载荷应带 paused 状态(response_builder)"
    assert "guard_paused" in _TP, "turn_protocol 应接收 guard_paused 参数"
    assert "连续失败 8 次，任务已暂停" in _TP, "暂停文案在 turn_protocol"
    assert "_compute_turn_reason" in _RB, "网关应调用统一 reason 计算(response_builder)"


def test_paused_payload_with_recovery():
    """暂停载荷: status=paused + continue_messages(换策略系统指令) + paused_breakpoint"""
    seg = _RB[_RB.index("if guard_paused:") : _RB.index("return (messages, tool_steps, bridge_exhausted, None")]
    assert '"status": "paused"' in seg
    assert '"continue_messages"' in seg
    assert "换一种实现方式" in seg
    assert "paused_breakpoint" in seg
    assert "_pause_recursion" in seg
    assert "连续失败 8 次已暂停。可选择继续执行" in seg
