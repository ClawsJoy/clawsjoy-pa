# -*- coding: utf-8 -*-
u"""去种子（pm_1770 §二.1⒝⒞）：首启 **⛔ 灌** ＋ 「已落之种子」之清（逐字比 · 留痕 · 幂等）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_no_seed_1770.py -q

判据（正控 2 ＋ 反控 3）：
  ⒈ **正控（⛔ 灌）**：全新之 `PaCore` ⇒ 画像 ／ 账本皆空（承「空库之诚」）。
  ⒉ **正控（清毕 ＋ 留痕）**：以昔之 `add()` 形写入旧种子（12 ＋ 3）⇒ `PaCore` 起 ⇒ 尽去，
     且 `events` 内一 `legacy_seed_purged`（其载荷载**所删之原值**）。
  ⒊ **反控一（⛔ 滥删）**：与种子**同源而值异**之真条 ⇒ 存（证「逐字比」之要）。
  ⒋ **反控二（⛔ 滥删）**：五元组**唯 `status` 异**之条 ⇒ 存（证「全同」之严）。
  ⒌ **反控三（幂等）**：清已毕 ⇒ 再清 ⇒ 返 `(0, 0)` ∧ **⛔ 造事件**（承「无中 ⛔ 写盘」）。
"""
import io
import json
import os
import sys

sys.path.insert(0, ".")

from core.pa import seed as SEEDMOD
from core.pa.events import EventLog
from core.pa.ledger import TodoStore
from core.pa.pa_core import PaCore
from core.pa.profile import ProfileStore


def _write_legacy(d):
    u"""以**昔之 `add()` 之形**落「旧种子」（⛔ 手拼 JSON —— 须与昔同其道，方是正控）。"""
    st = ProfileStore(str(d / "profile.json"))
    for domain, value, source, conf, status in SEEDMOD.LEGACY_SEED:
        st.add(domain, value, source=source, confidence=conf, status=status)
    ld = TodoStore(str(d / "ledger.json"))
    for title, kind, note in SEEDMOD.LEGACY_LEDGER:
        ld.add(title, kind=kind, note=note)
    return st, ld


def _read_json(p):
    return json.loads(io.open(str(p), encoding="utf-8").read())


def test_正控一_首启不再灌注(tmp_path):
    pa = PaCore(data_dir=str(tmp_path / "pa"))
    assert pa.profile.entries == [], u"首启 ⛔ 得灌种子（画像）"
    assert pa.ledger.items == [], u"首启 ⛔ 得灌种子（账本）"


def test_正控二_已落之种子尽清且留痕(tmp_path):
    d = tmp_path / "pa"
    d.mkdir(parents=True, exist_ok=True)
    _write_legacy(d)
    assert len(_read_json(d / "profile.json")["entries"]) == 12
    assert len(_read_json(d / "ledger.json")["items"]) == 3
    pa = PaCore(data_dir=str(d))
    assert pa.profile.entries == [], u"旧种子未清（画像）"
    assert pa.ledger.items == [], u"旧种子未清（账本）"
    assert len(_read_json(d / "profile.json")["entries"]) == 0, u"盘上未清"
    ev = pa.handle("events_tail", {"n": 20})["events"]
    hit = [e for e in ev if e.get("kind") == "legacy_seed_purged"]
    assert hit, u"删前留痕 ⛔ 在"
    pay = hit[-1]["payload"]
    assert len(pay["profile"]) == 12 and len(pay["ledger"]) == 3, u"留痕须载原值"


def test_反控一_同源而值异之真条不删(tmp_path):
    d = tmp_path / "pa"
    d.mkdir(parents=True, exist_ok=True)
    st = ProfileStore(str(d / "profile.json"))
    dom, val, src, conf, _st = SEEDMOD.LEGACY_SEED[0]
    keep = st.add(dom, val + u"（老板二次确认之增）", source=src, confidence=conf, status=_st)
    pa = PaCore(data_dir=str(d))
    assert keep["id"] in [e["id"] for e in pa.profile.entries], u"同源而值异 ⇒ 误删（逐字比败）"


def test_反控二_同值而异态之条不删(tmp_path):
    d = tmp_path / "pa"
    d.mkdir(parents=True, exist_ok=True)
    st = ProfileStore(str(d / "profile.json"))
    dom, val, src, conf, _st = SEEDMOD.LEGACY_SEED[0]
    keep = st.add(dom, val, source=src, confidence=conf, status="proposed")   # ⚠ 唯 status 异
    pa = PaCore(data_dir=str(d))
    assert keep["id"] in [e["id"] for e in pa.profile.entries], u"五元组 ⛔ 全同 ⇒ 不应删"


def test_反控三_幂等_再清无果且不造事件(tmp_path):
    d = tmp_path / "pa"
    d.mkdir(parents=True, exist_ok=True)
    st, ld = _write_legacy(d)
    assert SEEDMOD.purge(st, ld) == (12, 3)
    ev = EventLog(str(d / "events.jsonl"))
    assert SEEDMOD.purge(st, ld, events=ev) == (0, 0), u"再清须无果"
    assert not os.path.exists(str(d / "events.jsonl")), u"无中 ⇒ ⛔ 造事件（幂等败）"