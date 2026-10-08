# -*- coding: utf-8 -*-
u"""PM 2112：计划回执之 `route` —— 本轮**实际所走**之路（⛔ 猜）＋ 模型名唯自注册表（⛔ 硬编）。

其病（PM 2112 §三.3 · 我一手实测）：`generate_plan` 之调用 **⛔ 给 model** ⇒ `LLMClient._call`
  落 `LLMConfig.default_model`（**本机 qwen**）⇒ 云端诸支**永不入** ⇒ 实测 `get_last_route()`
  ＝ {"provider": "ollama", "model": "qwen2.5:7b-instruct-q4_0-gpu", "fell_back": false, "reason": ""}
  ⇒ 与注册表「默认 ＝ remote:deepseek」**二处漂**。今：模型名取 `default_route()` ＋ `route` 入回执。

以何形调用：python -X utf8 -B -m pytest tests/unit/test_pa_plan_route_2112.py -q
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import decision as D            # noqa: E402
from core.pa import providers as PV          # noqa: E402
from core.lib.llm_client import LLMClient    # noqa: E402

TASK = u"给小王的项目出一份周报，明早发我"


def _n():
    return len(D.TASK_TEMPLATES[D._detect_task_type(TASK)])


@pytest.fixture()
def capture(monkeypatch):
    u"""替 `LLMClient.generate` —— 记其 `model` 实参 ＋ **仿 `_call`** 置 `last_route`（同真形）。"""
    seen = {}

    def _mk(route=None, reply=None, attempts=1):
        def _g(self, prompt, model=None, **kw):
            seen["model"] = model
            seen["max_tokens"] = kw.get("max_tokens")
            self.last_route = dict(route) if route is not None else {}
            self.last_attempts = attempts
            if reply is not None:
                return reply
            return json.dumps([u"第%d步" % (i + 1) for i in range(_n())])
        monkeypatch.setattr(LLMClient, "generate", _g, raising=True)
        return seen
    return _mk


def test_模型名取自注册表默认(capture):
    u"""旧形 ⛔ 给 model ⇒ 落本机；今必取 `default_route()` 之**实名**（一处定形）。"""
    seen = capture()
    D.generate_plan(TASK)
    assert seen["model"] == PV.default_route()[0]["model"], seen


def test_route入回执(capture):
    u"""回执之 `route` ≡ `get_last_route()`（真源 · ⛔ 猜）。"""
    capture(route={"provider": "deepseek", "model": "deepseek-flash",
                   "fell_back": False, "reason": ""})
    out = D.generate_plan(TASK)
    assert out["route"]["provider"] == "deepseek", out["route"]
    assert out["route"]["model"] == "deepseek-flash", out["route"]
    assert out["source"] == "llm", out


def test_代者之note亦入回执(monkeypatch, capture):
    u"""`default_route()[1]` 之显形辞（可用者优先 · ⛔ 静默换）亦入 `route`。"""
    monkeypatch.setattr(PV, "default_route", lambda: (
        {"provider": "local:ollama", "model": "qwen2.5:7b-instruct-q4_0-gpu", "thinking": None},
        u"默认之 DeepSeek 不可用 · 由 Qwen 代之"))
    capture(route={"provider": "ollama", "model": "qwen2.5:7b-instruct-q4_0-gpu",
                   "fell_back": True, "reason": "no_api_key"})
    out = D.generate_plan(TASK)
    assert out["route"]["note"] == u"默认之 DeepSeek 不可用 · 由 Qwen 代之", out["route"]
    assert out["route"]["fell_back"] is True, out["route"]


def test_模型抛时route仍留痕(monkeypatch):
    u"""⛔ 静默：模型抛 ⇒ `refine.error` 留痕 ∧ `route` 亦在（可辨「跑而败」走的是哪一路）。"""
    def _boom(self, prompt, model=None, **kw):
        self.last_route = {"provider": "deepseek", "model": "deepseek-flash",
                           "fell_back": True, "reason": "cloud_unavailable"}
        self.last_attempts = 2
        raise RuntimeError(u"云端不可用")
    monkeypatch.setattr(LLMClient, "generate", _boom, raising=True)
    out = D.generate_plan(TASK)
    assert out["source"] == "template", out
    assert u"RuntimeError" in out["refine"]["error"], out["refine"]
    assert out["route"]["reason"] == "cloud_unavailable", out["route"]


def test_route恒在回执(capture):
    u"""`route` 恒为 dict（⛔ 缺键 ⇒ 面侧照实渲不必判无）。"""
    capture()
    out = D.generate_plan(TASK)
    assert isinstance(out.get("route"), dict), out


def test_max_tokens取自注册表(capture):
    u"""pm_2117 §三.2：额度唯自 `default_max_tokens()`（⛔ 硬编 200 ／ 800）—— 旧 `200` 遇推理模型必空。"""
    seen = capture()
    out = D.generate_plan(TASK)
    assert seen["max_tokens"] == int(PV.default_max_tokens()), seen
    assert out["refine"]["max_tokens"] == int(PV.default_max_tokens()), out["refine"]
    assert out["refine"]["max_tokens"] > 200, out["refine"]


def test_attempts入回执(capture):
    u"""pm_2117 §三.3：`attempts`（试数）入回执 ⇒ 「白调」可查。"""
    capture(attempts=3)
    out = D.generate_plan(TASK)
    assert out["refine"]["attempts"] == 3, out["refine"]


def test_一调即成时attempts为一(capture):
    u"""额度足 ⇒ 一调即成（`attempts` ＝ 1 · ⛔ 白调）。"""
    capture(attempts=1)
    out = D.generate_plan(TASK)
    assert out["refine"]["attempts"] == 1, out["refine"]
