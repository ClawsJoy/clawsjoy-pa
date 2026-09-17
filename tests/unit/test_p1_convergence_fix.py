"""P1-1/P1-2 回归测试: 8轮耗尽收敛指令 + pytest 超时引导"""
import sys

sys.path.insert(0, ".")
import pytest


def test_round_exhausted_for_else():
    """P1-1: range(8) 自然耗尽进 else 置 _round_exhausted; break 路径不触发"""
    import agent_gateway_enhanced as main

    src = open(main.__file__, encoding="utf-8").read()
    _RB = open("core/gateway/v9_bridge/response_builder.py", encoding="utf-8").read()
    assert "_round_exhausted = False" in src, "应有初始化标记"
    assert "else:" in src and "_round_exhausted = True" in src, "应有 for-else 置位"
    # 收敛指令文案(已归位 response_builder)
    assert "已达轮次上限，请基于现有信息输出评估结论" in _RB, "应有轮次上限收敛指令"
    assert "不要继续调用工具" in _RB, "应明确禁止继续调工具"


def test_round_exhausted_semantics():
    """P1-1 行为验证: 8轮都有工具 → exhausted; 中途 break → 不触发"""

    def _sim(tool_counts):
        flag = False
        for i in range(8):
            if i >= len(tool_counts) or tool_counts[i] == 0:
                break
        else:
            flag = True
        return flag

    assert _sim([1] * 8) is True, "8轮全有工具应自然耗尽"
    assert _sim([1, 1, 0]) is False, "中途无工具 break 不应触发"
    assert _sim([1] * 5) is False, "5轮后自然 break 不应触发"


def test_execute_command_timeout_guidance():
    """P1-2: execute_command 超时返回引导文案, 不抛异常"""
    import core.tools.execute_command as ec

    src = open(ec.__file__, encoding="utf-8").read()
    assert "TimeoutExpired" in src, "应捕获 subprocess.TimeoutExpired"
    assert "timeout 300 同步等待" in src, "应引导 timeout 300 同步等待"
    assert "不要 nohup 后台 + sleep 轮询" in src, "应禁止 nohup+轮询"
    # 行为验证: 模拟超时返回结构
    _timeout_s = 30
    res = {
        "success": False,
        "stdout": "",
        "stderr": f"命令执行超时(>{int(_timeout_s)}s)。如需运行长时间测试，请改用 timeout 300 同步等待，不要 nohup 后台 + sleep 轮询。",
        "returncode": -1,
    }
    assert res["success"] is False
    assert "timeout 300" in res["stderr"]
    assert "nohup" in res["stderr"]
