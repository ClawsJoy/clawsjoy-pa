# -*- coding: utf-8 -*-
"""pm_1478 §二 之齿：回执必给**取数刻** `read_at`（一处定形 · ⛔ 二处各打时戳）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_receipt_read_at.py -q

判据：
  ⒜ 式：`_pa_read_at()` ≡ `%Y-%m-%d %H:%M:%S`。
  ⒝ 正控（行为）：`POST /v9/pa/dialog` 之回执**含** `read_at`（前端走径行刻之真源 · `more.js` 探针取 `read_at || at`）。
  ⒞ 反控（回归）：`POST /v9/pa/ask` 之回执仍含 `read_at`（⛔ 破）。
  ⒟ 一处定形：定义唯一 ∧ 三路（dialog ／ ask ／ 会话元）同源（⛔ 各打时戳）。
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tests.pa_src import gr_src  # noqa: E402

from core.pa import gateway_routes as GR  # noqa: E402

STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


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

def test_stamp_shape():
    u"""⒜：取数刻之式（一处定形）。"""
    assert STAMP.match(GR._pa_read_at()), GR._pa_read_at()


# ---------- ⒝ 正控 ----------

def test_dialog_receipt_has_read_at(client):
    u"""⒝：`/v9/pa/dialog` 回执含 `read_at`（⛔ 缺 ⇒ 前端「取数刻未给」）。"""
    r = client.post("/v9/pa/dialog", json={"user_id": "u1", "text": u"你好"})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert "read_at" in d, sorted(d.keys())
    assert STAMP.match(str(d["read_at"])), d["read_at"]


# ---------- ⒞ 反控（回归） ----------

def test_ask_receipt_still_has_read_at(client):
    u"""⒞：`/v9/pa/ask` 之 `read_at` ⛔ 破（既有名同义）。"""
    r = client.post("/v9/pa/ask", json={"question": u"库里没有的问题xyzzy"})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert "read_at" in d, sorted(d.keys())
    assert STAMP.match(str(d["read_at"])), d["read_at"]


# ---------- ⒟ 一处定形 ----------

def test_read_at_single_definition():
    u"""⒟：定义唯一 ∧ 三路同源（⛔ 二处各打时戳）。"""
    src = gr_src()
    assert len(re.findall(r"def _pa_read_at\(", src)) == 1, u"取数刻之定义须唯一"
    calls = re.findall(r"(?<!def )_pa_read_at\(\)", src)
    assert len(calls) >= 3, u"三路（dialog ／ ask ／ 会话元）须同源：%d" % len(calls)
    live = [ln.strip() for ln in src.splitlines()
            if re.search(r"now\(\)\.strftime\(\"%Y-%m-%d %H:%M:%S\"\)", ln.split("#", 1)[0])]
    assert len(live) == 1, u"格式之字面唯许于 `_pa_read_at` 之内：%r" % (live,)