# -*- coding: utf-8 -*-
u"""PM 2110：计划回执之 `source` **按实书**（⛔ 恒书 template）＋ 细化之痕（⛔ 静默）。

其病（PM 2110 §一）：`generate_plan` 之 label 实经模型细化（PM 一手：「交付周报」≠ 模板「交付产物」）
  而 `source` **恒书** `template` ⇒ 面 `renderPlan` 直书之 ⇒ **屏上之字与实不合**（违「不实之辞 ⛔ 入屏」）。
其病（PM 2110 §二.2）：`except: pass` ⇒ 「模型未跑 ／ 跑而败」**二态一名蔽** ⇒ 今留痕于 `refine`。

以何形调用：python -X utf8 -B -m pytest tests/unit/test_pa_plan_source_2110.py -q
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import decision as D      # noqa: E402
from core.lib import llm_client as LC  # noqa: E402

TASK = u"给小王的项目出一份周报，明早发我"


@pytest.fixture()
def fake_llm(monkeypatch):
    u"""替模型之 `generate`（⛔ 真调 —— 其首跑 ~58 s；本齿唯判**回执之形**）。"""
    def _set(fn):
        monkeypatch.setattr(LC.LLMClient, "generate", fn, raising=True)
    return _set


def _n_stages(task=TASK):
    return len(D.TASK_TEMPLATES[D._detect_task_type(task)])


def test_细化成_则_source书llm且label取模型(fake_llm):
    n = _n_stages()
    fake_llm(lambda self, prompt, **kw: json.dumps([u"第%d步" % (i + 1) for i in range(n)]))
    r = D.generate_plan(TASK)
    assert r["source"] == "llm", r
    assert r["refine"]["ok"] is True and r["refine"]["error"] == "", r["refine"]
    assert r["refine"]["ms"] >= 0, r["refine"]
    assert [s["label"] for s in r["steps"]] == [u"第%d步" % (i + 1) for i in range(n)], r["steps"]


def test_模型抛_则_source书template且留痕(fake_llm):
    def _boom(self, prompt, **kw):
        raise RuntimeError(u"模型不可达")
    fake_llm(_boom)
    r = D.generate_plan(TASK)
    assert r["source"] == "template", r
    assert r["refine"]["ok"] is False and u"RuntimeError" in r["refine"]["error"], r["refine"]
    assert [s["label"] for s in r["steps"]] == [t[1] for t in D.TASK_TEMPLATES[r["task_type"]]], r["steps"]


def test_回形不符_则留痕而非静默(fake_llm):
    fake_llm(lambda self, prompt, **kw: u"这不是数组")
    r = D.generate_plan(TASK)
    assert r["source"] == "template", r
    assert r["refine"]["error"], r["refine"]


def test_回空_留痕为回空(fake_llm):
    fake_llm(lambda self, prompt, **kw: u"")
    r = D.generate_plan(TASK)
    assert r["source"] == "template" and r["refine"]["error"] == u"模型回空", r["refine"]


def test_stage恒自模板_label之出处方为source(fake_llm):
    u"""`source` 之义 ＝ **label 之出处**；stage **恒**自模板（⛔ 受模型所动）。"""
    n = _n_stages()
    fake_llm(lambda self, prompt, **kw: json.dumps([u"x" * 30] * n))
    r = D.generate_plan(TASK)
    assert [s["stage"] for s in r["steps"]] == [t[0] for t in D.TASK_TEMPLATES[r["task_type"]]], r["steps"]
    assert r["source"] == "llm", r


def test_长不合_则template(fake_llm):
    u"""回数组而**长 ⛔ 合** ⇒ ⛔ 采（照旧之判）∧ 留痕。"""
    fake_llm(lambda self, prompt, **kw: json.dumps([u"a"] * (_n_stages() + 2)))
    r = D.generate_plan(TASK)
    assert r["source"] == "template" and r["refine"]["error"], r

