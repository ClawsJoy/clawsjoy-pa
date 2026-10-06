# -*- coding: utf-8 -*-
u"""P2 ② 之钉：`llm_brain(model=…)` ⇒ 传至 `LLMClient.generate(model=…)`（pm_1447 §二.3①）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_brain_model.py -q

判据：
  ⒜ 传 `model` ⇒ `generate` 收到**同值**（唯加一参之链）
  ⒝ 缺省（⛔ 传）⇒ `generate` 收到 `None`（**反控**：⛔ 改既有行为 · ⛔ 硬编其名）
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


def test_brain_reverse_control_model_defaults_none(monkeypatch):
    u"""⒝ 反控：缺省 ⇒ `None`（⛔ 硬编远端之名 ⇒ 本机之默认⛔破）。"""
    seen, _ = _run(monkeypatch)
    assert seen["model"] is None, seen


def test_brain_passes_max_tokens(monkeypatch):
    u"""并钉：`max_tokens` 之链 ⛔ 变（同一处）。"""
    seen, _ = _run(monkeypatch, max_tokens=123)
    assert seen["max_tokens"] == 123, seen