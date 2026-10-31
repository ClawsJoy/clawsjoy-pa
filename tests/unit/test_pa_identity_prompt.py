# -*- coding: utf-8 -*-
"""PA 身份提示：不能自称 Qwen / 编造 agent 列表。"""
from core.pa.pa_routes_dialog_threads import pa_system_for, PA_IDENTITY


def test_identity_prompt_for_both_modes():
    for mode in ("work", "companion"):
        s = pa_system_for(mode)
        assert "Personal Assistant" in s
        assert "不是 Qwen" in s
        assert "不是另一个 agent" in s
        assert "编造 agent 名单" in s


def test_identity_is_shared():
    assert "Personal Assistant" in PA_IDENTITY
    assert "Qwen 只是本机推理引擎" in PA_IDENTITY


def test_agent_chat_gets_identity_system():
    from core.gateway.v9_chat.entry import _ensure_agent_identity
    msgs = [{"role": "user", "content": "你是谁"}]
    out = _ensure_agent_identity(msgs)
    assert out[0]["role"] == "system"
    assert "不是 Qwen" in out[0]["content"]
    _ensure_agent_identity(out)
    assert sum(1 for m in out if m.get("role") == "system") == 1


def test_chat_ui_has_identity_fallback():
    p = __import__("pathlib").Path("web/pa/faces/chat.js").read_text(encoding="utf-8")
    assert "我是 PA（Personal Assistant，私人助理）" in p
    assert "由阿里云开发" in p
