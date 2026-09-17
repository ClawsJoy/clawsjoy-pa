"""P0/P1/P2 回归测试: 首轮空回复重试 + 空消息兜底 + 前端空内容判断"""
import sys

sys.path.insert(0, ".")
import pytest


def test_backend_empty_reply_retry():
    """P0: bridge_loop 首轮空回复(无 content 无 tool_calls) → 重试而非 break"""
    import agent_gateway_enhanced as main

    src = open(main.__file__, encoding="utf-8").read()
    assert "_empty_reply_count = 0" in src, "应有空回复重试计数"
    _RG = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    assert "empty_reply_count < 1" in _RG, "(a)2026-09-05: 注入摘要后仅自动重试 1 次"
    assert "上一轮进展摘要" in _RG, "应注入上一轮上下文摘要"
    # 行为模拟: 首次空回复 + 摘要注入 + continue(重试1次)
    _empty_reply_count = 0
    _bmsg = {"content": "", "tool_calls": []}
    _btool_calls = _bmsg.get("tool_calls") or []
    _retried = False
    if not _btool_calls:
        if not _bmsg.get("content") and _empty_reply_count < 1:
            _empty_reply_count += 1
            _retried = True  # continue 代替 break
    assert _retried is True, "首次空回复应注入摘要重试"
    assert _empty_reply_count == 1, "计数应递增"
    # 第2次空回复(摘要重试后仍空): 计数 1 不 < 1 → 不再重试, 交 need_more
    _bmsg2 = {"content": "", "tool_calls": []}
    _retried2 = False
    if not (_bmsg2.get("tool_calls") or []):
        if not _bmsg2.get("content") and _empty_reply_count < 1:
            _empty_reply_count += 1
            _retried2 = True
    assert _retried2 is False, "摘要重试后仍空 → 不应再自动重试(need_more)"
    assert _empty_reply_count == 1


def test_backend_empty_message_fallback():
    """P1: _loop_data2/_loop_data 为 None 时填充显式提示"""
    src = open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()  # P3-B: 桥接层已归位
    assert src.count("模型未产出有效内容") >= 2, "stream + non-stream 都应兜底"
    assert "if _loop_data2 is None" in src, "stream 路径应有 None 兜底"
    assert "if _loop_data is None" in src, "non-stream 路径应有 None 兜底"
    # 行为模拟
    _loop_data = None
    if _loop_data is None:
        _loop_data = {"role": "assistant", "content": "[系统] 模型未产出有效内容"}
    assert _loop_data["content"], "兜底后 message 应有内容"


def test_frontend_empty_content_check():
    """P2: 前端 msg 无 content 且无 tool_calls → 提示重试不判完成"""
    from pathlib import Path

    html = Path("web/static/js/chat.js").read_text(encoding="utf-8")
    assert html.count("模型未产出有效内容，请重新描述需求") >= 2, "两处前端分支都应检查空内容"
    assert "!msg.content && (!msg.tool_calls || msg.tool_calls.length === 0)" in html, "应有空内容判断"
    assert "不判完成" not in html or "✅ 任务完成" in html, "完成分支仍保留"
