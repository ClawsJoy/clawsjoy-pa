# -*- coding: utf-8 -*-
u"""pm_1571 §三 之齿：`archive` 面之件 —— **⛔ 入 `evidence`**（只索引之独立出口 ＝ `archive_hits`）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_archive_only_1571.py -q

由（pm_1571 §三 · PM 一手）：`role: archive` 之册辞「⛔ 作据 · 只索引」须与实相符 ——
  我 1570 之探「二列皆空」⇒ ⛔ 足证 ⇒ 须**造一控**：一问之命中**唯在 archive 面**。

判据：
  ⒜ 正控：命中唯在 archive 面 ⇒ `archive_hits >= 1` ∧ `evidence == []` ∧ `refused is True`
     ∧ `answer_source == "archive_only"`（⛔ 入答据）。
  ⒝ 反控：同件、面角色改 `knowledge` ⇒ 入 `evidence`（`>= 1`）∧ `archive_hits == []`
     ∧ `refused is False`（证「archive ⇒ ⛔ 入 evidence」之判**唯因角色** · ⛔ 因他）。
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

Q = u"珠穆朗玛峰有多高"


@pytest.fixture()
def kb(tmp_path):
    u"""唯本齿之 fixtures（⛔ 真数据）：一枚**只索引面**之件。"""
    d = tmp_path / u"vault"
    (d / u"_dsh").mkdir(parents=True)
    (d / u"_dsh" / u"会话报述.md").write_text(
        u"珠穆朗玛峰有多高\n", encoding="utf-8")
    return d


def _client(tmp_path, monkeypatch, kb, role):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / u"pa"))
    monkeypatch.setattr(GR, "vault_root", lambda: kb)
    monkeypatch.setattr(GR, "ws_root", lambda: None)
    monkeypatch.setattr(GR, "org_enabled", lambda: True)
    # 唯一之面 ＝ 本齿之造面（角色可换）· 收件箱 ／ 知识库 皆 ⛔ 入（唯测本轴）
    monkeypatch.setattr(GR, "PA_KB_ASK_SCOPES", ())
    monkeypatch.setattr(GR, "pa_faces", lambda: [(u"dsh面", (u"@vault:_dsh",), (u"*.md",))])
    monkeypatch.setattr(GR, "PA_FACE_ROLE", {u"dsh面": role})
    monkeypatch.setattr(GR, "_ASK_CACHE", {})
    monkeypatch.setattr(GR, "_LINE_CACHE", {})

    def _fake_llm_brain(system_prompt=None, model=None, max_tokens=None):
        def _b(context_text):
            return u"已收到"

        _b._is_pa_brain = True
        return _b

    monkeypatch.setattr(GR, "llm_brain", _fake_llm_brain)
    app = Flask(__name__)
    GR.register_pa_routes(app, brain=GR.llm_brain())
    return app.test_client()


def _ask(c, q=Q):
    r = c.post(u"/v9/pa/ask", json={u"question": q})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    return r.get_json()


# ---------- ⒜ 正控：唯 archive 之命中 ⇒ ⛔ 入 evidence ----------

def test_archive_only_hit_never_enters_evidence(tmp_path, monkeypatch, kb):
    j = _ask(_client(tmp_path, monkeypatch, kb, u"archive"))
    assert len(j[u"archive_hits"]) >= 1, u"fixtures 须命中 archive 面（否则本齿之 0 是「无料」而非「守」）"
    assert j[u"evidence"] == [], u"archive 之件**须 ⛔ 入答据**（本齿之的）"
    assert j[u"refused"] is True, u"唯 archive 有据 ⇒ 须**拒答**（⛔ 以报述充世界之实）"
    assert j[u"answer_source"] == u"archive_only", j[u"answer_source"]
    assert u"archive_hits" in j and u"evidence" in j


# ---------- ⒝ 反控：同件 · 角色改 knowledge ⇒ 入 evidence ----------

def test_same_file_as_knowledge_enters_evidence(tmp_path, monkeypatch, kb):
    j = _ask(_client(tmp_path, monkeypatch, kb, u"knowledge"))
    assert len(j[u"evidence"]) >= 1, u"knowledge 面之件须入答据（⛔ 假红）"
    assert j[u"archive_hits"] == [], u"knowledge 面 ⛔ 入 archive_hits"
    assert j[u"refused"] is False, u"有知识面之据 ⇒ ⛔ 拒答"