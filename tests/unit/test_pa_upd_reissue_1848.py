# -*- coding: utf-8 -*-
u"""pm_1848 §三 之齿：**同版号之新册（重发）⛔ 可装**（旧病）＋ 早返之辞如实（§三.3）。

病（一手 · 本夜 · 同版号 9.0.8 三出）：pa_update.py 旧 :560
  "if cur and str(cur) == str(man['version']): return 0"
  **先于** :563 之 base_version ／ --force 检 ⇒ **同版号之新册 ⛔ 可装**（连 --force 亦不可）
  ⇒ 若已装首包 ⇒ 老板被**锁**在病版。

治（pm_1848 §三.3）：判据 ＝ 装根 version.json 之 **built_at** vs 册之 built_at ——
  戳**同** ⇒ 已是最新 ⇒ ⛔ 动（照旧）；戳 **⛔ 同**（含任一戳⛔读）⇒ 认「重发」⇒
  **可装** ∧ **明书二戳**（日志 ／ 终态 ／ --json 皆载）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_upd_reissue_1848.py -q

判据：
  R1 正控：同版号 ∧ 戳**同** ⇒ rc 0 ∧ 明书「已是最新」∧ **未动盘**（⛔ 建备份 ／ 装件不换）。
  R2 反控（本件之的）：同版号 ∧ 戳 ⛔ 同 ⇒ rc 0 ∧ 明书「重发」＋ 二戳 ∧ **真换件**。
  R3 反控：异版号 ∧ 异戳 ⇒ base_version 之闸**照旧**（不符 ⇒ rc 2 ∧ 「基础版」）。
  R4 反控：装根之戳 ⛔ 读 ⇒ ⛔ 充「已是最新」⇒ 认重发照装（rc 0 ∧ 明书「⛔ 读」）。
  R5 正控：终态之辞 —— noop ⇒ 「已是最新 … ⛔ 动一物」（⛔ 书「已就位」）；
     reissue ⇒ 载二戳（⛔ 书「已是最新」）；常路 ⇒ 照旧「已就位」。
  R6 正控：--json 之体 —— 重发之路载 reissue ＋ 二戳 ∧ 常路 ⛔ 载。
  R7 正控：_tail 之早返 ⇒ 明书「未动一物」（⛔ 泛辞「若上文言…」）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIN_PA = ROOT / "scripts" / "win_pa"
for _p in (str(ROOT), str(WIN_PA)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_update as PU  # noqa: E402

STAMP_OLD = u"2026-10-08T02:55:31+0800"
STAMP_NEW = u"2026-10-08T03:53:17+0800"
PAYLOAD = b"hi-new"
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


def _reset_diag():
    u"""复 _DIAG（进程内共用 ⇒ 齿须自清 · ⛔ 赖前测之残）。"""
    PU._DIAG.update({u"step": u"", u"from": None, u"to": None, u"touched": False,
                     u"rolled_back": False, u"noop": False, u"reissue": False,
                     u"stamp_from": None, u"stamp_to": None})


def _root(tmp_path, version, built_at=STAMP_OLD, with_stamp=True):
    r = tmp_path / u"root"
    (r / u"core").mkdir(parents=True, exist_ok=True)
    (r / u"core" / u"a.txt").write_bytes(b"old")
    d = {u"version": version, u"commit": u"c", u"tree": u"t", u"channel": u"internal"}
    if with_stamp:
        d[u"built_at"] = built_at
    (r / u"version.json").write_text(json.dumps(d), encoding=u"utf-8")
    return r


def _man(version=u"9.0.8", base=u"9.0.7", built_at=STAMP_NEW):
    return {u"version": version, u"base_version": base, u"channel": u"internal",
            u"built_at": built_at,
            u"files": [{u"path": u"core/a.txt", u"sha256": PAYLOAD_SHA,
                        u"size": len(PAYLOAD), u"mode": u"mod"}]}


def _stage(tmp_path):
    stg = tmp_path / u"stage"
    (stg / u"core").mkdir(parents=True, exist_ok=True)
    (stg / u"core" / u"a.txt").write_bytes(PAYLOAD)
    return stg


def _wire(monkeypatch, tmp_path, man):
    u"""以桩替「网 ＋ 落件」，唯留步序与「版 ／ 戳」之判（真跑 verify ／ backup ／ apply）。"""
    _reset_diag()
    upd = tmp_path / u"upd"
    monkeypatch.setattr(PU, "upd_dir", lambda root=None, env=None: str(upd))
    monkeypatch.setattr(PU, "_log_open", lambda root, version: None)
    monkeypatch.setattr(PU, "locked", lambda p: False)
    monkeypatch.setattr(PU, "load_manifest",
                        lambda a, r: (man, u"", u"", {u"channel": u"internal",
                                                      u"url": u"stub", u"file": u"stub"}))
    monkeypatch.setattr(PU, "fetch_all",
                        lambda m, s, d, timeout=None: (list(m[u"files"]), [u"[OK] stub 下毕"]))
    return upd


def _args(tmp_path, stg, **kw):
    d = dict(root=str(tmp_path / u"root"), src=None, manifest=None, staged=str(stg),
             force=False, no_restart=True, go=True, json=False)
    d.update(kw)
    return argparse.Namespace(**d)


def _json_of(out):
    i = out.index(u'"ok": true')
    j = out.rindex(u"{", 0, i)
    return json.loads(out[j:])


def test_R1_同版号同戳_不动(tmp_path, monkeypatch, capsys):
    u"""R1 正控：同版号 ∧ 戳同 ⇒ 已是最新 ⇒ ⛔ 动（未建备份 ／ 装件不换）。"""
    _root(tmp_path, u"9.0.8", built_at=STAMP_NEW)
    stg = _stage(tmp_path)
    upd = _wire(monkeypatch, tmp_path, _man(built_at=STAMP_NEW))
    rc = PU.run(_args(tmp_path, stg))
    out = capsys.readouterr().out
    assert rc == 0, out
    assert u"已是最新" in out, out
    assert PU._DIAG[u"noop"] is True, PU._DIAG
    assert PU._DIAG[u"reissue"] is False, PU._DIAG
    assert (tmp_path / u"root" / u"core" / u"a.txt").read_bytes() == b"old", u"装件被换 ⇒ 误动"
    assert not (upd / u"backup").exists(), u"早返之路 ⛔ 应建备份"


def test_R2_同版号异戳_认重发可装(tmp_path, monkeypatch, capsys):
    u"""R2 反控（本件之的）：同版号 ∧ 戳 ⛔ 同 ⇒ 认「重发」⇒ **可装** ∧ 明书二戳。"""
    _root(tmp_path, u"9.0.8", built_at=STAMP_OLD)
    stg = _stage(tmp_path)
    _wire(monkeypatch, tmp_path, _man(built_at=STAMP_NEW))
    rc = PU.run(_args(tmp_path, stg))
    out = capsys.readouterr().out
    assert rc == 0, out
    assert u"重发" in out, out
    assert (STAMP_OLD in out) and (STAMP_NEW in out), out
    assert PU._DIAG[u"reissue"] is True, PU._DIAG
    assert PU._DIAG[u"noop"] is False, PU._DIAG
    assert (tmp_path / u"root" / u"core" / u"a.txt").read_bytes() == PAYLOAD, u"重发之路须真换件"


def test_R3_异版号_基础版闸照旧(tmp_path, monkeypatch, capsys):
    u"""R3 反控：异版号 ⇒ base_version 之闸**照旧**（不符 ⇒ rc 2）。"""
    _root(tmp_path, u"9.0.5", built_at=STAMP_OLD)
    stg = _stage(tmp_path)
    _wire(monkeypatch, tmp_path, _man(version=u"9.0.8", base=u"9.0.7", built_at=STAMP_NEW))
    rc = PU.run(_args(tmp_path, stg))
    out = capsys.readouterr().out
    assert rc == 2, out
    assert u"基础版" in out, out
    assert PU._DIAG[u"reissue"] is False, PU._DIAG
    assert (tmp_path / u"root" / u"core" / u"a.txt").read_bytes() == b"old", out


def test_R4_装根之戳缺_照实认重发(tmp_path, monkeypatch, capsys):
    u"""R4 反控：装根之戳 ⛔ 读 ⇒ ⛔ 充「已是最新」（承「空 ⛔ 混 缺」）⇒ 认重发照装。"""
    _root(tmp_path, u"9.0.8", with_stamp=False)
    stg = _stage(tmp_path)
    _wire(monkeypatch, tmp_path, _man(built_at=STAMP_NEW))
    rc = PU.run(_args(tmp_path, stg))
    out = capsys.readouterr().out
    assert rc == 0, out
    assert (u"重发" in out) and (u"⛔ 读" in out), out
    assert (tmp_path / u"root" / u"core" / u"a.txt").read_bytes() == PAYLOAD, out


def test_R5_终态之辞_三态分书(tmp_path):
    u"""R5 正控：noop ⇒ 「已是最新 … ⛔ 动一物」；reissue ⇒ 载二戳；常路 ⇒ 「已就位」。"""
    _reset_diag()
    ns_manual = type("_NS", (), {"no_restart": True})()
    PU._DIAG.update({u"from": u"9.0.7", u"to": u"9.0.8"})
    n0 = PU.final_note(0, ns_manual) or u""
    assert (u"已就位" in n0) and (u"关窗重开" in n0), n0
    _reset_diag()
    PU._DIAG.update({u"noop": True, u"from": u"9.0.8", u"to": u"9.0.8"})
    n1 = PU.final_note(0, ns_manual) or u""
    assert (u"已是最新" in n1) and (u"⛔ 动一物" in n1), n1
    assert u"已就位" not in n1, n1
    _reset_diag()
    PU._DIAG.update({u"reissue": True, u"to": u"9.0.8", u"stamp_from": STAMP_OLD,
                     u"stamp_to": STAMP_NEW})
    n2 = PU.final_note(0, ns_manual) or u""
    assert (u"重发" in n2) and (STAMP_OLD in n2) and (STAMP_NEW in n2), n2
    assert u"已是最新" not in n2, n2
    n3 = PU.final_note(0, type("_NS", (), {"no_restart": False})())
    assert n3 is not None, u"重发之路 ⛔ 可返 None（默认辞将误书「已是最新」）"
    assert (u"重发" in n3) and (STAMP_OLD in n3) and (STAMP_NEW in n3), n3
    _reset_diag()


def test_R6_json之体载重发二戳(tmp_path, monkeypatch, capsys):
    u"""R6 正控：--json 之体 —— 重发路载 reissue ＋ 二戳。"""
    _root(tmp_path, u"9.0.8", built_at=STAMP_OLD)
    stg = _stage(tmp_path)
    _wire(monkeypatch, tmp_path, _man(built_at=STAMP_NEW))
    rc = PU.run(_args(tmp_path, stg, json=True))
    out = capsys.readouterr().out
    assert rc == 0, out
    d = _json_of(out)
    assert d[u"reissue"] is True and d[u"stamp_from"] == STAMP_OLD and d[u"stamp_to"] == STAMP_NEW, d


def test_R6b_json之体_常路不载(tmp_path, monkeypatch, capsys):
    u"""R6b 反控：常路（异版号）之 --json ⛔ 载 reissue。"""
    _root(tmp_path, u"9.0.7", built_at=STAMP_OLD)
    stg = _stage(tmp_path)
    _wire(monkeypatch, tmp_path, _man(built_at=STAMP_NEW))
    rc = PU.run(_args(tmp_path, stg, json=True))
    out = capsys.readouterr().out
    assert rc == 0, out
    d = _json_of(out)
    assert u"reissue" not in d, d


def test_R7_尾话早返明书(capsys):
    u"""R7 正控：_tail 之早返 ⇒ 明书「未动一物」（⛔ 唯泛辞）。"""
    _reset_diag()
    PU._DIAG.update({u"noop": True, u"from": u"9.0.8", u"to": u"9.0.8", u"stamp_to": STAMP_NEW})
    a = argparse.Namespace(go=True, json=False)
    PU._tail(a, 0, time.time())
    out = capsys.readouterr().out
    assert (u"未动一物" in out) and (u"已是最新" in out), out
    _reset_diag()
