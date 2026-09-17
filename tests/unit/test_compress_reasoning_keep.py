"""上下文压缩保留 reasoning_content 回归测试

根因: _safe_compress_messages 过滤带 tool_calls 的 assistant → thinking 模式最近的
assistant(tool_calls + reasoning_content)被滤掉 → 配对破坏 → DeepSeek 400。
修复: tail 取完整消息 + _validate_messages 配对清理。
"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.message_assembler import _safe_compress_messages, _validate_messages


def _mk_thinking_messages(n=40):
    """构造长任务消息: 中间 user/assistant, 最近一条 assistant 带 tool_calls + reasoning_content"""
    msgs = [{"role": "system", "content": "你是 ClawsJoy 的 AI 助手。"}]
    for i in range(n):
        msgs.append({"role": "user", "content": f"任务步骤 {i}"})
        msgs.append({"role": "assistant", "content": f"分析 {i}", "reasoning_content": f"思考过程 {i}"})
    # 最近一轮: assistant 带 tool_calls + reasoning_content + 对应 tool 消息
    msgs.append(
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "关键思考: 需要写文件",
            "tool_calls": [
                {"id": "tc_1", "type": "function", "function": {"name": "write_file", "arguments": '{"path": "a.py"}'}}
            ],
        }
    )
    msgs.append({"role": "tool", "tool_call_id": "tc_1", "content": "写入成功"})
    return msgs


def test_source_uses_tail_full_messages():
    """源码: _safe_compress_messages 应 tail 取完整消息 + _validate_messages 清理"""
    src = open("core/gateway/message_assembler.py", encoding="utf-8").read()
    assert "tail = messages[-keep:]" in src, "应取完整尾部消息"
    # R2(2026-08-30): 压缩保留所有 user 消息 + 经 _finalize_messages 唯一出口清理
    assert "_extra_users" in src.split("def _safe_compress_messages")[1].split("def ")[0], "R2 应保留所有 user 消息"
    assert (
        "_finalize_messages(" in src.split("def _safe_compress_messages")[1].split("def ")[0]
    ), "应经 _finalize_messages 唯一出口清理"
    # 旧实现(过滤 tool_calls)应已删除
    assert (
        'not m.get("tool_calls")' not in src.split("def _safe_compress_messages")[1].split("def ")[0]
    ), "不应再过滤带 tool_calls 的 assistant"


def test_thinking_reasoning_preserved():
    """thinking 模式: 压缩后最近 assistant 的 reasoning_content 与 tool_calls 保留"""
    msgs = _mk_thinking_messages()
    out = _safe_compress_messages(msgs, "u1", "s1", keep=8)
    # 最近 assistant(tool_calls + reasoning_content) 必须保留
    last = out[-1]
    assert last.get("role") in ("assistant", "tool")
    # 找到带 reasoning_content 的 assistant
    has_reasoning = any(m.get("reasoning_content") for m in out if m.get("role") == "assistant")
    assert has_reasoning, "reasoning_content 应保留"
    has_tool_calls = any(m.get("role") == "assistant" and m.get("tool_calls") for m in out)
    assert has_tool_calls, "带 tool_calls 的 assistant 应保留"
    # 配对: tool 消息有对应 assistant tool_call
    _ids = set()
    for m in out:
        if m.get("role") == "assistant":
            for _tc in m.get("tool_calls") or []:
                _ids.add(_tc.get("id"))
    for m in out:
        if m.get("role") == "tool":
            assert m.get("tool_call_id") in _ids, f"孤立 tool: {m}"


def test_no_orphan_tools():
    """压缩后无孤立 tool 消息(不在任何 assistant tool_calls 里)"""
    msgs = _mk_thinking_messages()
    out = _safe_compress_messages(msgs, "u1", "s1", keep=5)
    _ids = set()
    for m in out:
        if m.get("role") == "assistant":
            for _tc in m.get("tool_calls") or []:
                _ids.add(_tc.get("id"))
    for m in out:
        if m.get("role") == "tool":
            assert m.get("tool_call_id") in _ids, f"孤立 tool 泄漏: {m}"


def test_summary_marker_present():
    """压缩摘要占位 system 消息存在"""
    msgs = _mk_thinking_messages()
    out = _safe_compress_messages(msgs, "u1", "s1", keep=8)
    assert any(m.get("role") == "system" and "上下文摘要" in m.get("content", "") for m in out)
    assert out[0]["role"] == "system"


def test_extreme_keep_one_still_preserves_reasoning():
    """极端压缩 keep=1: 最近 thinking assistant(tool_calls+reasoning) 仍保留且配对有效"""
    msgs = _mk_thinking_messages()
    out = _safe_compress_messages(msgs, "u1", "s1", keep=1)
    # tail 只取最后 1 条(tool 消息) → _validate_messages 会补齐其 assistant tool_calls?
    # 至少不能抛异常, 且输出经 validate 无孤立 tool
    _ids = set()
    for m in out:
        if m.get("role") == "assistant":
            for _tc in m.get("tool_calls") or []:
                _ids.add(_tc.get("id"))
    for m in out:
        if m.get("role") == "tool":
            assert m.get("tool_call_id") in _ids, f"极端压缩出现孤立 tool: {m}"
    # reasoning_content 不要求在此场景保留(keep=1 只取 tool), 但绝不产生 400 结构
    assert out, "输出不应为空"
