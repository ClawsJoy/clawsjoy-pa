"""P0-1/P0-2/P0-3 回归测试: bridge_exhausted 防重发 + 后端清残留 tool_calls"""
import sys

sys.path.insert(0, ".")
import pytest


def test_backend_budget_limit_sets_exhausted_true():
    """P0-1: max_total_tools 超限路径 _bridge_exhausted 应为 True(前端才能 break)"""
    import agent_gateway_enhanced as main

    src = open(main.__file__, encoding="utf-8").read()
    # 超限路径: _bridge_exhausted = True
    assert "_bridge_exhausted = True  # P0-1" in src, "超限应置 exhausted=True"
    assert "# 正常结束(已有足够产出)" not in src, "不应再有'正常结束'误导注释"


def test_backend_exhausted_clears_messages_tool_calls():
    """P0-3: exhausted 时清空 messages 最后 assistant 的 tool_calls(_loop_data2 来源)"""
    src = open("core/gateway/v9_bridge/response_builder.py", encoding="utf-8").read()
    assert "for _m_r in reversed(messages)" in src, "应遍历 messages 清残留 tool_calls"
    assert '_m_r["tool_calls"] = []' in src, "应清空 assistant tool_calls"
    # 验证行为: 模拟 exhausted 清理逻辑
    messages = [
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
    ]
    _bridge_exhausted = True
    if _bridge_exhausted:
        for _m_r in reversed(messages):
            if _m_r.get("role") == "assistant":
                if _m_r.get("tool_calls"):
                    _m_r["tool_calls"] = []
                break
    assert messages[-1]["tool_calls"] == [], "最后 assistant 的 tool_calls 应被清空"
    assert messages[0]["role"] == "user"


def test_frontend_break_before_continue():
    """P0-1/P0-2: 前端 bridge_exhausted 在 continue 之前 break; SSE done 设标记"""
    from pathlib import Path

    html = Path("web/static/js/chat.js").read_text(encoding="utf-8")
    # P0-1: exhausted 检查在 continue 判断之前, 且 continue 排除 exhausted
    exhausted_idx = html.find("if (d.bridge_exhausted) {")
    continue_idx = html.find("d.tool_steps && d.tool_steps.length > 0 && msg.tool_calls")
    assert exhausted_idx != -1 and continue_idx != -1
    assert exhausted_idx < continue_idx, "bridge_exhausted 应出现在 continue 之前"
    assert "!d.bridge_exhausted" in html, "continue 应排除 exhausted 场景"
    # P0-2: SSE done 事件设 bridge_exhausted 标记
    assert "donePayload.bridge_exhausted = true" in html, "SSE done 应设 exhausted 标记"
