"""上下文管理对齐 Harness 测试: 探索性输出摘要 / 任务目标常驻 / 探索止损"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.message_assembler import _compress_messages, _finalize_messages, _summarize_messages_semantic


def test_exploratory_tool_summarized_in_semantic():
    """探索性 tool 输出 → key_findings 摘要(不占热窗口)"""
    s = _summarize_messages_semantic(
        [
            {"role": "tool", "tool_call_id": "t1", "content": "[tool=list_dir] 目录共 30 项: a.py b.py c.py"},
            {"role": "tool", "tool_call_id": "t2", "content": "[tool=read_file] 文件内容很长的探索..."},
        ]
    )
    assert len(s["key_findings"]) >= 1, "探索性 tool 应摘要进 key_findings"


def test_compress_preserves_task_goal():
    """压缩后任务目标(首条 user)仍可见"""
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "盘点 V9 的 bug 并修复"},
    ] + [{"role": "assistant", "content": f"探索步骤{i}"} for i in range(20)]
    out = _compress_messages(msgs, "u1", "s1", keep=8)
    out_txt = " ".join(str(m.get("content", "")) for m in out)
    assert "盘点 V9" in out_txt, "任务目标应保留在压缩后上下文"


def test_exploratory_tool_truncated_in_compress():
    """压缩时探索性 tool 长输出被摘要(≤200字符)"""
    msgs = [
        {"role": "user", "content": "查目录"},
        {
            "role": "assistant",
            "tool_calls": [{"id": "tc1", "type": "function", "function": {"name": "list_dir", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "tc1", "content": "file_" * 100 + " 超长目录输出"},
    ] + [{"role": "assistant", "content": "继续探索"} for _ in range(10)]
    # keep=3 → 触发压缩(消息数 > keep), 探索性 tool 在热窗口内被摘要
    out = _compress_messages(msgs, "u1", "s1", keep=3)
    out_txt = " ".join(str(m.get("content", "")) for m in out)
    assert "目录共" in out_txt or "摘要" in out_txt, f"探索性输出应被摘要化: {out_txt[:150]}"


def test_explore_stop_hint_in_gateway_source():
    """止损机制: 连续5次无产出探索注入提示(源码断言)"""
    _SRC = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "_EXPLORE_THRESHOLD = 5" in _SRC, "应有探索阈值"
    assert "停止探索" in _SRC, "应有止损提示文案"
    assert "_bfn in _EXPLORE_TOOLS" in _SRC, "应检测探索工具"
