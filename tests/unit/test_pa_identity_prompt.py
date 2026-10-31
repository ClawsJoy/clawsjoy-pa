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
