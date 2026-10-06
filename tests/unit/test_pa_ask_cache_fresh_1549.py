# -*- coding: utf-8 -*-
"""pm_1549 §一 之齿：复问缓存（`_ASK_CACHE`）须**面变即失效**（⛔ 复问复用旧据）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_ask_cache_fresh_1549.py -q

病（CW `1546 §三` 一手 · 我 `1541` 活端复算）：键 `(q, kb, limit)` 无 TTL ／ 无失效
  ⇒ 复问复用「整份扫描之果」（含 `face_snapshot_at` 与 evidence）⇒ **面变而果不变**
  ⇒ 屏上之刻旧 ∧ 其「据」亦旧（用户以为新 · 实为旧）—— 活端实证：同问二次
  ⇒ `from_cache=true` ／ `snap=19:25:12`（⛔ 当刻）。

判据：
  ⒜ 正控（本齿之的）：**面变（加一件）⇒ 复问 ⇒ `from_cache=false` ∧ `face_snapshot_at` 新
     ∧ `searched` 增**。
  ⒝ 反控（性能之守）：**面 ⛔ 变 ⇒ 复问 ⇒ `from_cache=true`**（可复用 · 印相同）。
  ⒞ 一处定形：`pa_ask_scan_specs` 之单 ≡ `PA_KB_ASK_SCOPES` ＋ `pa_faces()` 之展开
     （扫与印**同轴** · ⛔ 二处各列）。
  ⒟ 同轴（要）：`_cached_lines` 之粒度为 **ns** —— 同秒内**同长**之改写 ⇒ ⛔ 读旧
     （否则「印变而读旧」＝假新鲜）。
  ⒠ 唯加键：回执既有键 ⛔ 失（`from_cache` ／ `scanned` ／ `saved_wall_s` 在）。
"""
from __future__ import annotations

import os
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
def kb(tmp_path):
    u"""唯本齿之 fixtures（⛔ 真数据）：一枚**可命中**之件。"""
    d = tmp_path / u"vault"
    (d / u"收件箱").mkdir(parents=True)
    (d / u"收件箱" / u"角色卡.md").write_text(
        u"老板叫什么名字：此件唯本齿之 fixtures（⛔ 真数据）\n", encoding="utf-8")
    return d


@pytest.fixture()
def client(tmp_path, monkeypatch, kb):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / u"pa"))
    monkeypatch.setattr(GR, "vault_root", lambda: kb)
    monkeypatch.setattr(GR, "ws_root", lambda: None)        # 组织面（工作区）⇒ 缺基 ⇒ ⛔ 入表
    monkeypatch.setattr(GR, "org_enabled", lambda: False)   # 门关 ⇒ 唯产品面（死件账）
    monkeypatch.setattr(GR, "_ASK_CACHE", {})               # ⭐ 本齿自「冷」起（⛔ 跨齿之果）
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


# ---------- ⒜ 正控：面变 ⇒ 自失效 ----------

def test_face_change_invalidates_cache(client, kb):
    j1 = _ask(client)
    assert j1[u"from_cache"] is False, u"首问须冷（⛔ 复用）"
    assert j1[u"searched"] >= 1, u"fixtures 须被扫到（否则本齿之 0 是「无料」而非「守」）"

    j2 = _ask(client)
    assert j2[u"from_cache"] is True, u"面 ⛔ 变 ⇒ 复问须复用（性能之守）"
    assert j2[u"judge"][u"face_snapshot_at"] == j1[u"judge"][u"face_snapshot_at"]

    # ⭐ 面变：加一件
    (kb / u"收件箱" / u"新件.md").write_text(
        u"老板叫什么名字：新加之件（本齿之面变）\n", encoding="utf-8")

    j3 = _ask(client)
    assert j3[u"from_cache"] is False, u"面变 ⇒ 缓存须**自失效**（本齿之的）"
    assert j3[u"searched"] == j1[u"searched"] + 1, u"新件须入扫（据亦新）"


# ---------- ⒝ 反控：面 ⛔ 变 ⇒ 复用 ----------

def test_same_face_reuses(client):
    a = _ask(client)
    b = _ask(client)
    c = _ask(client)
    assert a[u"from_cache"] is False
    assert b[u"from_cache"] is True and c[u"from_cache"] is True
    assert a[u"searched"] == b[u"searched"] == c[u"searched"]


# ---------- ⒠ 唯加键 ----------

def test_receipt_keys_intact(client):
    j = _ask(client)
    for k in (u"from_cache", u"scanned", u"saved_wall_s", u"judge", u"searched",
              u"refusal_canon", u"refusal_stale", u"gate", u"verdict", u"answer_source"):
        assert k in j, k
    assert u"face_snapshot_at" in j[u"judge"]


# ---------- ⒞ 一处定形：扫与印同轴 ----------

def test_scan_specs_single_source(kb):
    specs = GR.pa_ask_scan_specs(kb)
    names = [f for _r, f, _g in specs]
    assert names[:len(GR.PA_KB_ASK_SCOPES)] == list(GR.PA_KB_ASK_SCOPES), u"先二面 ＝ 收件箱／知识库"
    expect = [f[0] for f in GR.pa_faces() for _ in f[1]]
    assert names[len(GR.PA_KB_ASK_SCOPES):] == expect, u"余者 ≡ pa_faces() 之展开（同轴）"


def test_stamp_tracks_files(kb):
    s1 = GR.pa_ask_scan_stamp(kb)
    assert s1 == GR.pa_ask_scan_stamp(kb), u"面 ⛔ 变 ⇒ 印同"
    (kb / u"收件箱" / u"又一件.md").write_text(u"x\n", encoding="utf-8")
    assert GR.pa_ask_scan_stamp(kb) != s1, u"加件 ⇒ 印变"


# ---------- ⒟ 同轴：行缓存之分辨率为 ns ----------

def test_line_cache_ns_resolution(tmp_path):
    p = tmp_path / u"同秒同长.md"
    t0 = 1_700_000_000_000_000_000
    p.write_text(u"AAAA\n", encoding="utf-8")
    os.utime(p, ns=(t0, t0))
    assert GR._cached_lines(p) == [u"AAAA"]

    p.write_text(u"BBBB\n", encoding="utf-8")          # 同长（5 字节）
    os.utime(p, ns=(t0 + 500, t0 + 500))               # 同秒（int 秒同）· ns 异
    assert GR._cached_lines(p) == [u"BBBB"], u"同秒同长之改写 ⇒ 须读新（ns 分辨率）"