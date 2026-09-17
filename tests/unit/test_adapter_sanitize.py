# -*- coding: utf-8 -*-
"""2026-09-06 根治: adapter 发送层强制净化 + 400 自动降级。任何上游消息构造缺陷在发送层兜底。"""
import io

_AD = io.open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()


def test_sanitize_function_exists():
    assert "def _sanitize_for_api" in _AD
    assert "reasoning_content" in _AD


def test_sanitize_called_before_send():
    i = _AD.find("def execute_with_tools")
    seg = _AD[i:i + 1500]
    assert "_sanitize_for_api(messages)" in seg


def test_400_degraded_retry():
    assert "resp.status_code == 400" in _AD
    assert "degraded" in _AD
    assert "_dm2.pop" in _AD


def test_sanitize_rules():
    i = _AD.find("def _sanitize_for_api")
    seg = _AD[i:i + 2000]
    assert 'nm["reasoning_content"] = rc if isinstance(rc, str) else ""' in seg
    assert "孤儿" in seg
    assert "tool_calls" in seg
