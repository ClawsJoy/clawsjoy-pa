# -*- coding: utf-8 -*-
u"""P2 ② 之钉：`llm_brain(model=…)` ⇒ 传至 `LLMClient.generate(model=…)`（pm_1447 §二.3①）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_brain_model.py -q

判据：
  ⒜ 传 `model` ⇒ `generate` 收到**同值**（唯加一参之链）
  ⒝ 缺省（⛔ 传）⇒ **改约（pm_1609 §二.1 令一）**：唯 `providers.default_route()` 一处出
      （可用者优先）⇒ ⛔ 硬编本机之名（旧形尽付 `config.default_model` ＝ 本机 7B
      ⇒ 净机无 Ollama 仍取本机 ⇒ `[WinError 2]` —— pm_1609 §〇 之逐字）
  ⒞ 皆不可用 ⇒ **⛔ 调模型** ＋ 出人话（`PA_NO_PROVIDER_TEXT` · ⛔ 以失败充答）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import llm_client as LC  # noqa: E402
from core.pa import gateway_routes as G  # noqa: E402


class _Fake:
    def __init__(self, *a, **kw):
        self.seen = None

    def generate(self, prompt, model=None, max_tokens=None, **kw):
        self.seen = {"model": model, "max_tokens": max_tokens, "prompt_head": prompt[:24]}
        return "ok"

    def get_last_route(self):
        return {}

    def get_stats(self):
        return {}


def _run(monkeypatch, **mk):
    made = {}

    def _ctor(*a, **kw):
        made["c"] = _Fake(*a, **kw)
        return made["c"]

    monkeypatch.setattr(LC, "LLMClient", _ctor)
    b = G.llm_brain(**mk)
    out = b("ctx")
    return made["c"].seen, out


def test_brain_passes_model_when_given(monkeypatch):
    u"""⒜：显式给名 ⇒ 逐字至 `generate`（⛔ 剥 ／ ⛔ 改）。"""
    seen, out = _run(monkeypatch, model="deepseek-flash")
    assert out == "ok", out
    assert seen["model"] == "deepseek-flash", seen


def test_brain_default_route_is_single_source(monkeypatch):
    u"""⒝ 缺省 ⇒ 唯 `providers.default_route()` 一处出（pm_1609 §二.1 令一）。

    反控之义（⛔ 硬编 `config.default_model` ＝ 本机 7B）：取路由之实名 ⇒ 与路由**同值**。
    """
    from core.pa import providers as P
    _exp, _ = P.default_route()
    seen, _ = _run(monkeypatch)
    assert seen["model"] == _exp.get("model"), seen
    assert seen["model"] is not None, seen


def test_brain_no_provider_never_calls_model(monkeypatch):
    u"""⒞ 皆不可用 ⇒ **⛔ 调模型** ⇒ 出人话（pm_1609 §二.1／§二.3）。"""
    from core.pa import providers as P
    monkeypatch.setattr(P, "default_route",
                        lambda: ({"provider": "remote:deepseek", "model": "deepseek-flash",
                                  "thinking": None}, u"亦无可用者（照实）"))
    monkeypatch.setattr(P, "available_state", lambda pid: (u"未配钥", u"密钥 ⛔ 在"))
    _made = []

    def _ctor(*a, **kw):
        _made.append(1)
        return _Fake(*a, **kw)

    monkeypatch.setattr(LC, "LLMClient", _ctor)
    out = G.llm_brain()("ctx")
    assert _made == [], u"皆不可用 ⇒ ⛔ 调模型（承「⛔ 以失败充答」）"
    assert out == G.PA_NO_PROVIDER_TEXT, out


def test_brain_passes_max_tokens(monkeypatch):
    u"""并钉：`max_tokens` 之链 ⛔ 变（同一处）。"""
    seen, _ = _run(monkeypatch, max_tokens=123)
    assert seen["max_tokens"] == 123, seen