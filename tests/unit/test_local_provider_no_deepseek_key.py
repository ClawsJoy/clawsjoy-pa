"""B：本地 provider 不依赖 DeepSeek key（B1 build_prompt / B2 entry 本地 adapter）.

判据：
  · 无 key ＋ local ⇒ build_prompt **不短路**、api_key=''；本地 Ollama 真回话；
  · 无 key ＋ deepseek ⇒ 明确报错（不静默降级）；
  · 有 key ＋ deepseek ⇒ 不回归（api_key 取到、仍 DeepSeekAdapter）；
  · entry 本地 model ⛔ 实例化 DeepSeekAdapter。
"""

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.gateway.v9_chat import entry, recovery  # noqa: E402


def _base(model, data=None, messages=None):
    return dict(
        data=data if data is not None else {},
        messages=messages if messages is not None else [{"role": "user", "content": "hi"}],
        model=model,
        user_id="u",
        session_id="s",
        allowed_commands=[],
        deepseek_key_loaded="",
        execute_agent_task_fn=lambda *a, **k: None,
    )


def _no_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)


# ---------- B1：build_prompt 条件校验 ----------


def test_local_no_key_no_short_circuit(monkeypatch):
    _no_key(monkeypatch)
    got = recovery.build_prompt(**_base("ollama"))
    assert got["short_circuit"] is None, got
    assert got["api_key"] == "", "local ⇒ api_key=''（不依赖 DeepSeek key）"
    assert got["messages"][0]["role"] == "system"


def test_local_qwen_no_key_no_short_circuit(monkeypatch):
    _no_key(monkeypatch)
    got = recovery.build_prompt(**_base("qwen2.5:7b-instruct-q4_0-gpu"))
    assert got["short_circuit"] is None and got["api_key"] == ""


def test_local_with_key_still_api_key_empty(monkeypatch):
    """本地 model 即使环境有 key 亦不依赖之（api_key=''）。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-should-not-be-used")
    got = recovery.build_prompt(**_base("ollama"))
    assert got["short_circuit"] is None
    assert got["api_key"] == ""


def test_local_async_no_key_starts(monkeypatch):
    _no_key(monkeypatch)
    got = recovery.build_prompt(**_base("ollama", data={"async": True, "task_id": "t1"}))
    assert got["short_circuit"] is not None
    assert got["short_circuit"]["success"] is True
    assert got["short_circuit"]["status"] == "started"


def test_deepseek_no_key_explicit_error(monkeypatch):
    _no_key(monkeypatch)
    got = recovery.build_prompt(**_base("deepseek-v4-flash"))
    sc = got["short_circuit"]
    assert sc is not None and sc["success"] is False, got
    assert "Key丢失" in sc["error"], sc
    assert "api_key" not in got, "短路路径不产 api_key"


def test_deepseek_with_key_no_regression(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
    got = recovery.build_prompt(**_base("deepseek-v4-flash"))
    assert got["short_circuit"] is None, got
    assert got["api_key"] == "sk-test-123"


# ---------- B2：entry 本地 adapter 选择 ----------


def test_make_local_adapter_not_deepseek():
    a = entry._make_model_adapter("ollama", "")
    assert isinstance(a, entry._LocalOllamaAdapter)
    assert type(a).__name__ != "DeepSeekAdapter"
    assert a.model == entry.os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_0-gpu")


def test_make_qwen_local_adapter_keeps_model():
    a = entry._make_model_adapter("qwen2.5:7b-instruct-q4_0-gpu", "")
    assert isinstance(a, entry._LocalOllamaAdapter)
    assert a.model == "qwen2.5:7b-instruct-q4_0-gpu"


def test_make_deepseek_adapter_with_key():
    a = entry._make_model_adapter("deepseek-v4-flash", "sk-test-123")
    assert type(a).__name__ == "DeepSeekAdapter"


def test_entry_uses_local_helper_not_direct_deepseek():
    src = inspect.getsource(entry.run_chat_entry)
    assert "adapter = _make_model_adapter(model, api_key)" in src
    assert "adapter = DeepSeekAdapter(" not in src, "本地 ⛔ 直建 DeepSeekAdapter"


def test_local_adapter_delegates_to_ollama(monkeypatch):
    captured = {}

    def _fake(messages, tools, model="", temperature=0.7, max_tokens=2000):
        captured.update(
            dict(messages=messages, tools=tools, model=model, temperature=temperature, max_tokens=max_tokens)
        )
        return {"success": True, "data": {"choices": [{"message": {"content": "OK"}}]}, "tokens": 1}

    import core.gateway.execute_agent_task as eat

    monkeypatch.setattr(eat, "_ollama_execute_with_tools", _fake)
    a = entry._LocalOllamaAdapter("ollama")
    out = a.execute_with_tools(messages=[{"role": "user", "content": "hi"}], tools=[], temperature=0.2, max_tokens=32)
    assert out["success"] is True
    assert captured["model"] == a.model and captured["max_tokens"] == 32
    assert captured["temperature"] == 0.2


def _tool_defs():
    return [
        {
            "type": "function",
            "function": {"name": "noop", "description": "noop", "parameters": {"type": "object", "properties": {}}},
        }
    ]


def _fake_ollama(monkeypatch, results):
    calls = []

    def _fake(messages, tools, model="", temperature=0.7, max_tokens=2000):
        calls.append(
            {"messages": messages, "tools": tools, "model": model, "temperature": temperature, "max_tokens": max_tokens}
        )
        return results[min(len(calls) - 1, len(results) - 1)]

    import core.gateway.execute_agent_task as eat

    monkeypatch.setattr(eat, "_ollama_execute_with_tools", _fake)
    return calls


def test_local_adapter_forces_tools_empty(monkeypatch):
    """P0：本地只纯聊天，即便调用方给 tools 也不下发。"""
    calls = _fake_ollama(
        monkeypatch,
        [{"success": True, "data": {"choices": [{"message": {"content": "收到"}}]}, "tokens": 1}],
    )
    a = entry._LocalOllamaAdapter("ollama")
    out = a.execute_with_tools(messages=[{"role": "user", "content": "hi"}], tools=_tool_defs(), max_tokens=32)
    assert out.get("success") is True, out
    assert len(calls) == 1, calls
    assert calls[0]["tools"] == [], "本地必须 tools=[]"


def test_local_adapter_tools_empty_ok(monkeypatch):
    """调用方传空 tools 也照常纯聊天。"""
    calls = _fake_ollama(
        monkeypatch,
        [{"success": True, "data": {"choices": [{"message": {"content": "ok"}}]}}],
    )
    a = entry._LocalOllamaAdapter("ollama")
    out = a.execute_with_tools(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert out.get("success") is True
    assert len(calls) == 1


def test_local_adapter_failure_explicit_error(monkeypatch):
    """纯聊天失败 ⇒ success=false ＋ 明确人话。"""
    calls = _fake_ollama(monkeypatch, [{"success": False, "error": "Ollama 连接被拒"}])
    a = entry._LocalOllamaAdapter("ollama")
    out = a.execute_with_tools(messages=[{"role": "user", "content": "hi"}], tools=_tool_defs())
    assert out.get("success") is False, out
    assert len(calls) == 1
    assert "本地 Ollama 纯聊天失败" in out["error"], out
    assert "连接被拒" in out["error"], out


def test_local_adapter_success_first_no_retry(monkeypatch):
    calls = _fake_ollama(
        monkeypatch,
        [
            {"success": True, "data": {"choices": [{"message": {"content": "ok"}}]}},
        ],
    )
    a = entry._LocalOllamaAdapter("ollama")
    out = a.execute_with_tools(messages=[{"role": "user", "content": "hi"}], tools=_tool_defs())
    assert out.get("success") is True and len(calls) == 1


def test_no_key_local_real_ollama_reply(monkeypatch):
    """无 key ＋ local ⇒ 本地 Ollama 真回话（需本机 11434；本地默认可跑）。"""
    _no_key(monkeypatch)
    a = entry._make_model_adapter("ollama", "")
    out = a.execute_with_tools(
        messages=[{"role": "user", "content": "只回复两个字：收到"}], tools=[], temperature=0.0, max_tokens=24
    )
    assert out.get("success") is True, out
    content = ((out.get("data") or {}).get("choices") or [{}])[0].get("message", {}).get("content") or ""
    assert str(content).strip(), out


def test_no_key_local_real_ollama_reply_with_tools(monkeypatch):
    """真实本地无 key ＋ 带 tools ⇒ success=true（失败则走 tools=[] 重试）。"""
    _no_key(monkeypatch)
    a = entry._make_model_adapter("ollama", "")
    out = a.execute_with_tools(
        messages=[{"role": "user", "content": "用一句话说明你在"}],
        tools=_tool_defs(),
        temperature=0.0,
        max_tokens=48,
    )
    assert out.get("success") is True, out
