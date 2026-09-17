# -*- coding: utf-8 -*-
"""L1 单测: deepseek adapter 发送前只保留最近一条 reasoning_content(旧推理剥离不进输入)"""
import sys
sys.path.insert(0, ".")
from core.lib.v8.adapters.deepseek_adapter import keep_last_reasoning


def test_keep_only_last_reasoning():
    """2026-09-06 更新: 纯文本 assistant(无 tool_calls)的 reasoning 全部剥离 —
    DeepSeek thinking 只接受 tool_calls 轮的 reasoning(纯文本收尾 reasoning 属已完成
    thinking 会话, 带旧 reasoning + 新 user → 400 reasoning_content must be passed back)。"""
    msgs = [
        {"role": "user", "content": "任务"},
        {"role": "assistant", "content": "第一轮分析", "reasoning_content": "思考AAAA"},
        {"role": "assistant", "content": "", "reasoning_content": "思考BBBB", "tool_calls": []},
        {"role": "assistant", "content": "最终", "reasoning_content": "思考CCCC"},
    ]
    out = keep_last_reasoning(msgs)
    for m in out:
        if m.get("role") == "assistant" and not m.get("tool_calls"):
            assert "reasoning_content" not in m, "纯文本 assistant 的 reasoning 应剥离(防 400)"
    # 原列表不被修改(事件层保留全量)
    assert msgs[1].get("reasoning_content") == "思考AAAA", "原 messages 不应被改动"


def test_no_reasoning_unchanged():
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "ok"}]
    assert keep_last_reasoning(msgs) == msgs
    assert keep_last_reasoning([]) == []
    assert keep_last_reasoning(None) == []


def test_tool_calls_reasoning_kept_even_if_not_last():
    """Q2+2026-09-06: tool_calls assistant 的 reasoning 保留(工具轮续跑防 400);
    纯文本收尾(最终分析)的 reasoning 剥离(已完成 thinking 会话不续传)。"""
    msgs = [
        {"role": "assistant", "content": "旧分析", "reasoning_content": "OLD分析思考"},
        {"role": "assistant", "content": "", "reasoning_content": "TOOL思考", "tool_calls": [{"id": "c1"}]},
        {"role": "tool", "tool_call_id": "c1", "content": "结果"},
        {"role": "assistant", "content": "最终结论", "reasoning_content": "FINAL思考"},
    ]
    out = keep_last_reasoning(msgs)
    def rc(i):
        return out[i].get("reasoning_content")
    assert rc(1) == "TOOL思考", "tool_calls assistant 的 reasoning 保留(防 400)"
    assert "reasoning_content" not in out[0], "旧的非工具轮推理剥离"
    assert "reasoning_content" not in out[3], "纯文本收尾 reasoning 剥离(防新 user 400)"
    # 原列表不变
    assert msgs[0].get("reasoning_content") == "OLD分析思考"


def test_single_plain_reasoning_stripped():
    """2026-09-06: 单条纯文本 assistant reasoning(无 tool_calls)剥离 — 已完成 thinking 会话"""
    msgs = [{"role": "assistant", "content": "", "reasoning_content": "only"}]
    out = keep_last_reasoning(msgs)
    assert "reasoning_content" not in out[0]


def test_wired_in_execute_with_tools():
    src = open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()
    assert "messages = keep_last_reasoning(messages)" in src, "发送前应剥离旧 reasoning"
    assert "def keep_last_reasoning" in src


def test_token_reduction_estimate():
    """验收代理: 多段 reasoning 时输入字符显著下降(中文≈0.3 tok/字符)"""
    msgs = []
    for i in range(10):
        msgs.append({"role": "assistant", "content": "步骤%d" % i,
                     "reasoning_content": "这段思考比较长用来模拟每轮推理开销的文本内容%d" % i})
    def chars(m):
        return sum(len(str(x.get("reasoning_content") or "")) for x in m if x.get("role") == "assistant")
    before = chars(msgs)
    after = chars(keep_last_reasoning(msgs))
    assert before > 0 and after < before * 0.3, (before, after)
