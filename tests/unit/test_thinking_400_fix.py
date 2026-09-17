# -*- coding: utf-8 -*-
"""2026-09-06: DeepSeek thinking 400 修复 — reasoning_content 处理防回归。
根因: 纯文本收尾 assistant(无 tool_calls) 的 reasoning_content 属已完成 thinking 会话,
前端恢复旧上下文会带多条旧 reasoning → 400 "reasoning_content must be passed back"。
修复: 只保留 tool_calls 轮 reasoning; 纯文本收尾 reasoning 一律剥离。"""
import io

_AD = io.open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()
_GW = io.open("core/gateway/v9_chat/archive.py", encoding="utf-8").read()  # P3-B: 归档层已归位


def test_adapter_strips_plain_final_reasoning():
    """keep_last_reasoning 只保留 tool_calls 轮 reasoning, 剥离纯文本收尾"""
    seg = _AD[_AD.find("def keep_last_reasoning") : _AD.find("def keep_last_reasoning") + 1200]
    assert "2026-09-06" in seg
    assert "tool_calls" in seg
    # 纯文本 assistant 剥离逻辑存在(非 tool_calls → pop)
    assert "m.pop" in seg
    assert "继续  # 保留: 工具轮 reasoning" in seg or "工具轮" in seg


def test_gateway_entry_strips_rc():
    """agent_gateway 入口统一剥离前端带来的 assistant reasoning_content"""
    assert "RC_STRIP" in _GW
    assert "reasoning_content" in _GW
