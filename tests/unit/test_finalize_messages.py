"""_finalize_messages 唯一出口回归测试 — 根治 V9 thinking 400

覆盖 4 类损坏形态(实测 DeepSeek 400) + retry 截断场景:
- 孤立 tool(无前置 assistant tool_calls) → 400
- tool_calls 无 tool 响应 → 400
- tool 在 assistant 之前(顺序颠倒) → 400
- tool_calls 缺 type 字段 → 400
"""
import sys, json
sys.path.insert(0, ".")
import pytest
from core.gateway.message_assembler import _finalize_messages, _normalize_tool_calls, _validate_messages


def _tc(tid, name="read_file", args=None, has_type=True):
    tc = {"id": tid, "function": {"name": name, "arguments": json.dumps(args or {"path": "a.py"})}}
    if has_type:
        tc["type"] = "function"
    return tc


def test_source_has_finalize_and_normalize():
    """源码: _finalize_messages = normalize + validate 唯一出口"""
    src = open("core/gateway/message_assembler.py", encoding="utf-8").read()
    assert "def _finalize_messages(messages):" in src
    assert "def _normalize_tool_calls(messages):" in src
    assert "_normalize_tool_calls(_validate_messages(messages))" in src, "finalize 应组合 normalize+validate"
    assert 'tc.setdefault("type", "function")' in src, "normalize 应补 type"


def test_fix_orphan_tool():
    """孤立 tool(无前置 assistant tool_calls) → 被移除"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "tool", "tool_call_id": "t_orphan", "content": "结果"},
        {"role": "user", "content": "继续"},
    ]
    out = _finalize_messages(msgs)
    assert all(m.get("role") != "tool" for m in out), "孤立 tool 应被移除"


def test_fix_unresolved_tool_calls():
    """assistant tool_calls 无 tool 响应 → tool_calls 被剥离(退化为文本)或保留含 content 消息"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "", "reasoning_content": "思考",
         "tool_calls": [_tc("t1")]},
        {"role": "user", "content": "继续"},
    ]
    out = _finalize_messages(msgs)
    # 无 tool 响应 → 无 assistant 带 tool_calls(未配对)
    for m in out:
        if m.get("role") == "assistant":
            assert not m.get("tool_calls"), f"未配对 tool_calls 应剥离: {m}"


def test_fix_tool_before_assistant():
    """tool 在 assistant 之前(顺序颠倒) → _validate_messages 重排为 assistant→tool"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "tool", "tool_call_id": "t1", "content": "结果"},
        {"role": "assistant", "content": "", "tool_calls": [_tc("t1")]},
    ]
    out = _finalize_messages(msgs)
    # tool 必须在其 assistant 之后(DeepSeek 要求 tool 响应前置 tool_calls)
    _asst_idx = next(i for i, m in enumerate(out) if m.get("role") == "assistant")
    _tool_idx = next(i for i, m in enumerate(out) if m.get("role") == "tool")
    assert _asst_idx < _tool_idx, f"tool 应重排到 assistant 之后: {out}"


def test_fix_missing_type():
    """tool_calls 缺 type 字段 → normalize 补 type=function"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "", "tool_calls": [_tc("t1", has_type=False)]},
        {"role": "tool", "tool_call_id": "t1", "content": "结果"},
    ]
    out = _finalize_messages(msgs)
    for m in out:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                assert tc.get("type") == "function", f"缺 type 应补齐: {tc}"


def test_fix_missing_reasoning_on_tool_calls():
    """带 tool_calls 的 assistant 缺 reasoning_content → 补空字符串(实测 DeepSeek 400 规则)"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "", "tool_calls": [_tc("t1")]},
        {"role": "tool", "tool_call_id": "t1", "content": "结果"},
    ]
    out = _finalize_messages(msgs)
    for m in out:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            assert isinstance(m.get("reasoning_content"), str), f"tool_calls assistant 必须带 reasoning_content 字符串: {m}"


def test_reasoning_none_fixed():
    """reasoning_content=None 的 tool_calls assistant → 补为空字符串"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "", "reasoning_content": None, "tool_calls": [_tc("t1")]},
        {"role": "tool", "tool_call_id": "t1", "content": "结果"},
    ]
    out = _finalize_messages(msgs)
    for m in out:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            assert m.get("reasoning_content") == "", f"None 应补空字符串: {m}"


def test_text_assistant_reasoning_untouched():
    """纯文本 assistant 的 reasoning_content 保留(不补不删)"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "分析", "reasoning_content": "思考过程"},
        {"role": "assistant", "content": "纯文本无reasoning"},
    ]
    out = _finalize_messages(msgs)
    assert out[1]["reasoning_content"] == "思考过程", "已有 reasoning 应保留"
    assert "reasoning_content" not in out[2], "纯文本 assistant 不应被强加 reasoning"


def test_fix_arguments_dict():
    """arguments 是 dict → normalize 转 json 字符串"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "t1", "type": "function",
                         "function": {"name": "read_file", "arguments": {"path": "a.py"}}}]},
        {"role": "tool", "tool_call_id": "t1", "content": "结果"},
    ]
    out = _finalize_messages(msgs)
    for m in out:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            args = m["tool_calls"][0]["function"]["arguments"]
            assert isinstance(args, str), f"arguments 应为 json 字符串: {type(args)}"
            assert json.loads(args)["path"] == "a.py"


def test_retry_truncation_scenario():
    """retry 路径截断(tail=4 切出孤立 tool) → finalize 后无孤立/未配对"""
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "", "reasoning_content": "r1", "tool_calls": [_tc("t1")]},
        {"role": "tool", "tool_call_id": "t1", "content": "结果1"},
        {"role": "assistant", "content": "", "reasoning_content": "r2", "tool_calls": [_tc("t2")]},
        {"role": "tool", "tool_call_id": "t2", "content": "结果2"},
        {"role": "assistant", "content": "结论", "reasoning_content": "r3"},
    ]
    # 模拟 retry 路径: sys[:2] + 摘要 + tail[-4:] (tail=4 会切出孤立 t2)
    _tg_sys = [m for m in msgs if m.get("role") == "system"][:2]
    _tg_tail = msgs[-4:]
    truncated = _tg_sys + [{"role": "system", "content": "摘要"}] + _tg_tail
    out = _finalize_messages(truncated)
    # 配对完整性: 每个 tool 有前置 assistant tool_calls
    for i, m in enumerate(out):
        if m.get("role") == "tool":
            found = any(j < i and out[j].get("role") == "assistant" and
                        any(tc.get("id") == m.get("tool_call_id") for tc in out[j].get("tool_calls", []))
                        for j in range(i))
            assert found, f"finalize 后仍有孤立 tool: {m}"
    # 无未配对 assistant tool_calls
    for i, m in enumerate(out):
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                assert any(j > i and out[j].get("role") == "tool" and out[j].get("tool_call_id") == tc.get("id") for j in range(i + 1, len(out))),                     f"未配对 tool_calls: {tc}"
                assert tc.get("type") == "function", f"应补 type: {tc}"


def test_finalize_idempotent():
    """finalize 幂等: 二次调用不改变结果"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "", "tool_calls": [_tc("t1")]},
        {"role": "tool", "tool_call_id": "t1", "content": "结果"},
    ]
    out1 = _finalize_messages(json.loads(json.dumps(msgs)))
    out2 = _finalize_messages(json.loads(json.dumps(out1)))
    assert out1 == out2, "finalize 应幂等"
