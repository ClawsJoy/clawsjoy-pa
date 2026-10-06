# -*- coding: utf-8 -*-
"""pm_1500 §二 之齿：库根未接 ⇒ **早返**（⛔ `Path("")` ⇒ 误扫 CWD · 潜在假有据）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_kb_unset_no_cwd_scan.py -q

病（本刻一手）：`kb = os.getenv("PA_VAULT_DIR") or (str(_vr) if _vr is not None else "")`
  ⇒ 空串充「未接」⇒ `pa_kb_search(q, "")` 之 `Path("") / "收件箱"` ＝ **CWD 相对**
  ⇒ 若 CWD 恰有同名子目录 ⇒ **误扫**（假有据）。
  二路之别：`PA_FACES` 路有守（`_rel_under` 缺基 ⇒ None ⇒ 该面 ⛔ 入表）；`PA_KB_ASK_SCOPES` 一路无守。

判据：
  ⒜ 空 `kb` ⇒ `searched=0` ∧ `hits=[]` ∧ `no_kb_root=True`。
  ⒝ 反控（本齿之的）：**CWD 有同名目录 ∧ 件可命中 ⇒ 亦 ⛔ 得其一**。
  ⒞ 反控：给**真根** ⇒ 同件**能**被扫到（证 fixtures 为真 ⇒ ⒜ 之 0 是「守」而非「无料」）。
  ⒟ 活端：`/v9/pa/ask`（未接）⇒ `kb_state="unset"` ∧ `answer_source="not_applicable"`
     ∧ 判词含「待选目录」（**可分**于「扫了而无」 · 承「空 ≠ 缺」）。
  ⒠ 一处定形：`kb_root` 之判唯 `_kb_root_str()` 一处出（⛔ 二处各判「空」）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as GR  # noqa: E402

Q = u"老板叫什么名字"


@pytest.fixture()
def cwd_with_face(tmp_path, monkeypatch):
    u"""CWD 内造 `收件箱/` ＋ 一枚**可命中**件（唯本齿之 fixtures）。"""
    d = tmp_path / u"cwd"
    (d / u"收件箱").mkdir(parents=True)
    (d / u"收件箱" / u"probe.md").write_text(
        u"老板叫什么名字：此件唯本齿之 fixtures（⛔ 真数据）\n", encoding="utf-8")
    monkeypatch.chdir(d)
    return d


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / u"pa"))
    monkeypatch.delenv("PA_VAULT_DIR", raising=False)
    monkeypatch.setattr(GR, "vault_root", lambda: None)

    def _fake_llm_brain(system_prompt=None, model=None, max_tokens=None):
        def _b(context_text):
            return u"已收到"

        _b._is_pa_brain = True
        return _b

    monkeypatch.setattr(GR, "llm_brain", _fake_llm_brain)
    app = Flask(__name__)
    GR.register_pa_routes(app, brain=GR.llm_brain())
    return app.test_client()


# ---------- ⒜ ----------

def test_unset_kb_early_return():
    r = GR.pa_kb_search(Q, "", limit=5)
    assert r["searched"] == 0, r
    assert r["hits"] == [], r
    assert r.get("no_kb_root") is True, r


# ---------- ⒝ 反控（本齿之的） ----------

def test_cwd_named_face_not_picked_up(cwd_with_face):
    u"""旧码此处必中（`Path("")/"收件箱"` ＝ CWD 之同名目录）—— 今须 0。"""
    r = GR.pa_kb_search(Q, "", limit=5)
    assert r["searched"] == 0, r
    assert not any(x.get("rel") == u"收件箱" for x in r["hits"]), r


# ---------- ⒞ 反控 ----------

def test_real_root_still_hits(cwd_with_face):
    r = GR.pa_kb_search(Q, str(cwd_with_face), limit=5)
    assert r["searched"] >= 1, r
    assert any(x.get("rel") == u"收件箱" for x in r["hits"]), r


# ---------- ⒟ 活端 ----------

def test_ask_reports_unset_state(client):
    r = client.post("/v9/pa/ask", json={"question": Q})
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d.get("kb_state") == "unset", d
    assert d.get("kb_root") == "", d
    assert d.get("searched") == 0, d
    assert d.get("answer_source") == "not_applicable", d
    assert u"待选目录" in (d.get("verdict") or ""), d


# ---------- ⒠ 一处定形 ----------

def test_single_judge_source():
    import inspect
    src = inspect.getsource(GR)
    assert src.count(u"def _kb_root_str(") == 1
    seg = inspect.getsource(GR.pa_kb_search)
    # ⚠ 判**调用形之序**（⛔ 判「文中提到同名」 —— 忍者注释自指 ⇒ 假红 · 承 install_win_pa 自测之训）
    assert seg.count(u"no_kb_root") == 1
    #   判**真叫形**之序 —— ⛔ 判「加号引文字」（注释亦含 `Path("")` ⇒ 假红）
    #   ⭐ pm_1549 §一.2：扫面清单移入 `pa_ask_scan_specs`（一处定形）
    #     ⇒ 本处改判「早返（`no_kb_root`）先于**扫面之调用**」；
    #       并断 `pa_kb_search` 内**⛔ 直触**径形（其唯一出处 ⇒ `pa_ask_scan_specs`）。
    assert seg.index(u"no_kb_root") < seg.index(u"pa_ask_scan_specs("), u"早返须在触扫面之前"
    assert u"Path(kb_root)" not in seg, u"扫面之径形须唯 `pa_ask_scan_specs` 一处"
