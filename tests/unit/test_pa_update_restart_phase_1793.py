# -*- coding: utf-8 -*-
u"""pm_1790 §二.2 ／ §二.3 ＋ pm_1793 §一 之齿：restart 相位**落盘** ∧ begin 幂等 ∧
器**崩**亦收相位（TD f202f89 · 2026-10-08）。

病（一手 · 老板所见「版本更新无效」）：
  ⒜ restart 相位昔**唯在器之内存** ⇒ 器停网关 ⇒ 应答之服即死 ⇒ 面无从问 ⇒
     那约 40 s 之空窗，面唯能显「更新面未答」；
  ⒝ begin() 二处皆调（端 ＋ 器）⇒ 昔**覆** from ／ started_at ⇒ 终态 from ＝ to
     （「从哪升到哪」不可考）；
  ⒞ STALE_S 之陈阈昔唯罩 running ⇒ 陈 restart **长挂**；
  ⒟ 器若**崩**（⛔ 返）⇒ main 之 finish 到不了 ⇒ 盘上之 restart 相位**长挂**
     ⇒ 面恒显「正在重启…」（pm_1793 §一 之新病）。

判据：
  U1 正控（落盘 · 停前）：restart() ⇒ 盘上 phase=restart ∧ from ／ started_at **沿用**起态
     ∧ to ＝ 显式所给 ∧ note 载起讫。
  U2 正控（幂等）：begin() 二唤 ⇒ from ／ started_at ⛔ 变（唯 phase 归一 running）。
  U3 反控（陈阈罩 restart）：陈 restart ⇒ phase() 报 failed（⛔ 长挂「正在重启」）。
  U4 正控（to 延续）：restart(to=X) 后 finish(rc=0) ⇒ to ＝ X（⛔ 覆以今之盘号）。
  P1 正控（崩亦收）：run 抛 ⇒ main 仍落终态（phase=failed ∧ rc=2 ∧ 报因）。
  P2 反控（干跑 ⛔ 落）：⛔ --go ⇒ 盘上**无**跑态（⛔ 占「跑」之名）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_update_restart_phase_1793.py -q
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIN_PA = ROOT / "scripts" / "win_pa"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import update_run as UR          # noqa: E402 — 须先正 sys.path


def _load_pa_update():
    spec = importlib.util.spec_from_file_location("pa_update_1793", str(WIN_PA / "pa_update.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PU = _load_pa_update()


def _root(tmp_path, monkeypatch, ver=u"9.0.1"):
    u"""装根（带 version.json）＋ LOCALAPPDATA 隔离（免污真机之态）。"""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "la"))
    r = tmp_path / "root"
    r.mkdir()
    (r / "version.json").write_text(json.dumps({"version": ver}), encoding="utf-8")
    return str(r)


def _doc(root):
    with open(UR.state_path(root), encoding="utf-8-sig") as fh:
        return json.loads(fh.read())


def test_u1_restart_phase_lands_and_keeps_from(tmp_path, monkeypatch):
    u"""U1：restart() 落盘 ∧ from ／ started_at 沿用起态（⛔ 覆）＋ to ＝ 显式所给。"""
    root = _root(tmp_path, monkeypatch)
    UR.begin(root, from_version=u"9.0.1")
    d0 = _doc(root)
    assert d0[u"phase"] == u"running" and d0[u"from"] == u"9.0.1"
    UR.restart(root, to_version=u"9.0.2")
    d1 = _doc(root)
    assert d1[u"phase"] == u"restart", d1
    assert d1[u"from"] == u"9.0.1", d1
    assert d1[u"to"] == u"9.0.2", d1
    assert d1[u"started_at"] == d0[u"started_at"], (d0, d1)
    assert u"9.0.1" in d1[u"note"] and u"9.0.2" in d1[u"note"], d1[u"note"]
    assert UR.phase(root)[u"phase"] == u"restart"


def test_u2_begin_is_idempotent(tmp_path, monkeypatch):
    u"""U2：begin() 二唤（端 ＋ 器）⇒ from ／ started_at ⛔ 变 —— 承「起时定死」。"""
    root = _root(tmp_path, monkeypatch)
    UR.begin(root, from_version=u"9.0.1")
    d0 = _doc(root)
    UR.restart(root, to_version=u"9.0.2")
    UR.begin(root, from_version=u"9.0.2")          # 器再起 ⇒ 昔覆 from ⇒ 今须 ⛔ 覆
    d1 = _doc(root)
    assert d1[u"from"] == u"9.0.1", d1
    assert d1[u"started_at"] == d0[u"started_at"], (d0, d1)
    assert d1[u"phase"] == u"running", d1


def test_u3_stale_restart_is_reported_failed(tmp_path, monkeypatch):
    u"""U3 反控：陈 restart ⇒ phase() 报 failed（⛔ 长挂「正在重启」而面恒转）。"""
    root = _root(tmp_path, monkeypatch)
    UR.begin(root, from_version=u"9.0.1")
    UR.restart(root, to_version=u"9.0.2")
    out = UR.phase(root, now=time.time() + UR.STALE_S + 1.0)
    assert out[u"phase"] == u"failed", out
    assert out[u"note_why"] == u"stale", out


def test_u4_finish_keeps_restart_to(tmp_path, monkeypatch):
    u"""U4：finish(rc=0) 沿用 restart() 所落之 to（⛔ 覆以今之盘号）。"""
    root = _root(tmp_path, monkeypatch, ver=u"9.0.2")
    UR.begin(root, from_version=u"9.0.1")
    UR.restart(root, to_version=u"9.0.2")
    UR.finish(root, 0)
    d = _doc(root)
    assert d[u"phase"] == u"done", d
    assert d[u"from"] == u"9.0.1" and d[u"to"] == u"9.0.2", d


def test_p1_crash_still_closes_the_phase(tmp_path, monkeypatch, capsys):
    u"""P1 正控：run 抛 ⇒ main 仍收相位（phase=failed ∧ rc=2 ∧ 原样报因）。"""
    root = _root(tmp_path, monkeypatch)

    def _boom(_a):
        raise RuntimeError(u"桩：器崩")

    monkeypatch.setattr(PU, "run", _boom)
    rc = PU.main(["--root", root, "--go"])
    out = capsys.readouterr().out
    assert rc == 2, out
    d = _doc(root)
    assert d[u"phase"] == u"failed", d
    assert d[u"phase"] != u"restart", d
    assert u"器崩" in out


def test_p2_dry_run_writes_no_phase(tmp_path, monkeypatch):
    u"""P2 反控：⛔ --go ⇒ 盘上无跑态（干跑 ⛔ 占「跑」之名 —— 承「一名一义」）。"""
    root = _root(tmp_path, monkeypatch)
    monkeypatch.setattr(PU, "run", lambda _a: 0)
    rc = PU.main(["--root", root])
    assert rc == 0
    assert not os.path.exists(UR.state_path(root)), UR.state_path(root)
