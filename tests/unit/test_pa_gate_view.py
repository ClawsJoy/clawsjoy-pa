# -*- coding: utf-8 -*-
"""pm_1486 §二 之齿：**闸之实 ⇒ 结构化判据**（一处定形 · ⛔ 以模型之辞判果）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_gate_view.py -q

病（老板一手 · session_pa_muwdx6o7）：**同一问**（「你使用的模型是什么」）二次之屏果不同
  —— 因前端旧 Fork-2 以**模型之辞之词形**（`paSelfRefusal`）判果。本齿即断此路。

判据：
  ⒜ 式：`pa_gate_view` 之值域（decision ／ display）俱在册。
  ⒝ 三控（本裁之的）：有据 ⇒ display=model｜无据＋回落 ⇒ display=model｜无据＋事实问 ⇒ display=refuse。
  ⒞ 齿（要）：**同一问连打二次 ⇒ 果须同**（`/v9/pa/ask` ∧ `/v9/pa/dialog`）。
  ⒟ 一处定形：定义唯一 ∧ 其入参**⛔ 含模型之辞**（即：果 ⛔ 由辞定）。
  ⒠ 唯加键：`gate` 入回执 ∧ 既有键 ⛔ 失。
"""
from __future__ import annotations

import inspect
import io
import re
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as GR  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))

    def _fake_llm_brain(system_prompt=None, model=None, max_tokens=None):
        def _b(context_text):
            return u"已收到"

        _b._is_pa_brain = True
        return _b

    monkeypatch.setattr(GR, "llm_brain", _fake_llm_brain)
    app = Flask(__name__)
    GR.register_pa_routes(app, brain=GR.llm_brain())
    return app.test_client()


# ---------- ⒜ 式 ----------

def test_value_domains():
    u"""⒜：值域在册（一名一义 · ⛔ 前端自拟）。"""
    assert GR.PA_GATE_DECISIONS == ("not_asked", "grounded", "refused", "not_applicable")
    assert GR.PA_GATE_DISPLAY == ("model", "refuse")
    r = GR.pa_gate_view()
    assert set(r) == {"decision", "display", "fact_yn", "refusal_canon", "why"}
    assert r["decision"] in GR.PA_GATE_DECISIONS
    assert r["display"] in GR.PA_GATE_DISPLAY
    assert r["refusal_canon"] == GR.PA_ASK_REFUSAL


# ---------- ⒝ 三控（本裁之的） ----------

def test_control1_grounded_shows_model():
    u"""⒝①：有据 ⇒ 显模型之答（⛔ 拒答）。"""
    assert GR.pa_gate_view(decision="grounded", fact_yn=False)["display"] == "model"
    assert GR.pa_gate_view(decision="grounded", fact_yn=True)["display"] == "model"


def test_control2_refused_fallback_shows_model_even_if_wording_is_cha_budao():
    u"""⒝②（本裁之要 · 老板之实）：无据 ＋ 回落 ⇒ **显模型之答** ＋ 「回落」之标
    —— **其辞或以「查不到」起首 ⇒ ⛔ 改果**（旧 Fork-2 即在此失手）。"""
    v = GR.pa_gate_view(decision="refused", fact_yn=False)
    assert v["decision"] == "refused"
    assert v["display"] == "model"


def test_control3_refused_fact_shows_canonical_refusal():
    u"""⒝③：无据 ＋ ⛔ 回落（事实问）⇒ canonical 拒答。"""
    v = GR.pa_gate_view(decision="refused", fact_yn=True)
    assert v["decision"] == "refused"
    assert v["display"] == "refuse"
    assert v["refusal_canon"] == GR.PA_ASK_REFUSAL


def test_not_applicable_is_not_refusal():
    u"""⒝④（三态纪律）：searched==0 ⇒ 不适用 ⇒ ⛔ 以拒答论。"""
    v = GR.pa_gate_view(decision="not_applicable", fact_yn=True)
    assert v["decision"] == "not_applicable"
    assert v["display"] == "model"


# ---------- ⒞ 齿 ----------

def test_ask_same_question_twice_same_gate(client):
    u"""⒞：`/v9/pa/ask` 同一问连打二次 ⇒ `gate` 须同。"""
    q = u"库里没有的问题xyzzy"
    a = client.post("/v9/pa/ask", json={"question": q}).get_json()
    b = client.post("/v9/pa/ask", json={"question": q}).get_json()
    assert "gate" in a and "gate" in b, (sorted(a.keys()), sorted(b.keys()))
    assert a["gate"] == b["gate"], (a["gate"], b["gate"])


def test_dialog_same_turn_twice_same_gate(client):
    u"""⒞：`/v9/pa/dialog` 同一轮连打二次 ⇒ `gate` 须同（本裁之的：同一实 ⇒ 同一果）。"""
    body = {"user_id": "u1", "text": u"你使用的模型是什么", "gate_decision": "refused"}
    a = client.post("/v9/pa/dialog", json=body).get_json()
    b = client.post("/v9/pa/dialog", json=body).get_json()
    assert a["gate"] == b["gate"], (a["gate"], b["gate"])
    assert a["gate"]["decision"] == "refused"
    assert a["gate"]["display"] == "model", u"回落之轮 ⇒ 显模型之答（⛔ 拒答）"


def test_dialog_echoes_relayed_judgement(client):
    u"""⒞：回执**回带**所转交之闸实（前端唯读键 ⇒ ⛔ 判辞）。"""
    d = client.post("/v9/pa/dialog", json={"user_id": "u1", "text": u"你好"}).get_json()
    assert d["gate"]["decision"] == "not_asked", d["gate"]
    d2 = client.post("/v9/pa/dialog",
                     json={"user_id": "u1", "text": u"你好", "grounded": True}).get_json()
    assert d2["gate"]["decision"] == "grounded", d2["gate"]


# ---------- ⒟ 一处定形 ----------

def test_helper_takes_no_model_wording():
    u"""⒟：其入参**⛔ 含模型之辞** —— 即：果之定 ⛔ 由辞（本裁之根）。"""
    params = set(inspect.signature(GR.pa_gate_view).parameters)
    assert params == {"decision", "origin", "grounded", "answer_source", "fact_yn"}, params
    for bad in ("reply", "answer", "text", "content", "raw"):
        assert bad not in params, u"⛔ 许模型之辞入判：%s" % bad


def test_single_definition():
    u"""⒟：定义唯一（一处定形）。"""
    src = io.open(GR.__file__, encoding="utf-8").read()
    assert len(re.findall(r"def pa_gate_view\(", src)) == 1, u"判据之定义须唯一"


# ---------- ⒠ 唯加键 ----------

def test_gate_key_present_and_no_regression(client):
    u"""⒠：`gate` 入 `dialog` ／ `ask` 回执 ∧ 既有键 ⛔ 失。"""
    d = client.post("/v9/pa/dialog", json={"user_id": "u1", "text": u"你好"}).get_json()
    for k in ("read_at", "reply", "route", "src", "model", "model_source",
              "fell_back", "fallback_note", "cost", "activity", "persisted"):
        assert k in d, (k, sorted(d.keys()))
    assert "gate" in d
    a = client.post("/v9/pa/ask", json={"question": u"库里没有的问题xyzzy"}).get_json()
    for k in ("read_at", "refusal_canon", "refused", "grounded", "ask_domain", "judge"):
        assert k in a, (k, sorted(a.keys()))
    assert "gate" in a
