# -*- coding: utf-8 -*-
u"""pm_1712 §三.3⒜ ＋ pm_1713 §二.2 之齿：`pa_update` 之「起服之形」三件
（TD f202f89 · 2026-10-07）。

病（老板净机 · 一手之日志）：`[更新] 9/10 重启：成` 而第⑩步探 `/health` 42.6 s ⛔ 达
（WinError 10061）⇒ 回滚 ⇒「更新一直失败」。三件共归一处 —— `ctl(root, …)` 之
「起 ／ 停」之形 ＋「成」之据：
  ⒜ `ctl` 之子进程 ⛔ 传 `cwd` ⇒ 随调用者之 CWD（承规七：凡起服须与「根」绑定）
  ⒝ 「重启：成」唯凭起令之 `rc` ＝ 假绿（⛔ 凭「服真在」）
  ⒞ 探败之支回滚而 ⛔ 重起 ⇒ 服留「停」之态（老板之面必断）

判据：
  T1 正控（根绑 · 器取）：`ctl(root, 'start')` 于**他处** CWD 调 ⇒ 子进程之 CWD 须 ＝ root。
  T2 正控（假绿 ⛔ 立）：起令 rc=0 而探 ⛔ 得 ⇒ ⛔ 称「成」（其行明书「待探活」）。
  T3 正控（探败亦重起）：探 ⛔ 得 ⇒ 回滚毕**再起一次**（ctl 之第三唤）＋ 重探（短窗）。
  T4 反控（明书）：重探亦 ⛔ 得 ⇒ 明书「停」之态 ＋ 去处（⛔ 留「停」而不言）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_update_restart_1713.py -q
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIN_PA = ROOT / "scripts" / "win_pa"
if str(WIN_PA) not in sys.path:
    sys.path.insert(0, str(WIN_PA))


def _load_pa_update():
    spec = importlib.util.spec_from_file_location("pa_update_1713", str(WIN_PA / "pa_update.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PU = _load_pa_update()


def test_ctl_child_cwd_is_root(tmp_path, monkeypatch):
    u"""T1 正控：`ctl` 之子进程 CWD 须 ＝ root（⛔ 随调用者之 CWD）。"""
    root = tmp_path / "root"
    (root / "scripts" / "win_pa").mkdir(parents=True)
    (root / "scripts" / "win_pa" / "pa_nowindow.py").write_text(
        u"import os, sys\n"
        u"print('CHILD_CWD=' + os.path.normcase(os.getcwd()))\n"
        u"print('CHILD_ACT=' + sys.argv[1])\n",
        encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    rc, out = PU.ctl(str(root), "start")
    assert rc == 0, out
    assert ("CHILD_CWD=" + os.path.normcase(str(root))) in out, out
    assert "CHILD_ACT=start" in out, out
    assert os.path.normcase(str(elsewhere)) not in out, out


class _Rec(object):
    def __init__(self):
        self.ctl = []
        self.probe = []


def _wire(monkeypatch, tmp_path, probe_seq):
    u"""以桩替「网 ＋ core」之诸面，唯留 `run()` 之步序与「起服 ／ 探活」之逻辑。"""
    rec = _Rec()
    man = {u"version": u"9.0.1", u"base_version": u"9.0.0", u"channel": u"internal",
           u"built_at": u"2026-10-07T00:00:00+0800",
           u"files": [{u"path": u"core/lib/version.py", u"mode": u"mod",
                       u"sha256": u"0" * 64, u"size": 1}]}

    class _UM(object):
        @staticmethod
        def totals(_m):
            return {u"n": 1, u"add": 0, u"mod": 1, u"del": 0, u"bytes": 1}

    core = type(sys)("core")
    core.__path__ = []
    cored = type(sys)("core.lib")
    cored.__path__ = []
    cored.update_manifest = _UM
    core.lib = cored
    monkeypatch.setitem(sys.modules, "core", core)
    monkeypatch.setitem(sys.modules, "core.lib", cored)
    monkeypatch.setitem(sys.modules, "core.lib.update_manifest", _UM)

    monkeypatch.setattr(PU, "load_manifest",
                        lambda a, r: (man, u"", u"", {u"channel": u"internal",
                                                      u"url": u"stub", u"file": u"stub"}))
    monkeypatch.setattr(PU, "cur_version", lambda r: (u"9.0.0", u""))
    monkeypatch.setattr(PU, "fetch_all",
                        lambda m, s, d, timeout=None: ([], [u"[OK] stub 下毕"]))
    monkeypatch.setattr(PU, "verify_all", lambda m, d: (True, [u"[OK] stub 校"]))
    monkeypatch.setattr(PU, "backup", lambda r, e, b: ([u"[OK] stub 备"], []))
    monkeypatch.setattr(PU, "backup_dir", lambda v, r: str(tmp_path / "bk"))
    monkeypatch.setattr(PU, "apply_all", lambda e, r, s: (True, [u"[OK] stub 换"], []))
    monkeypatch.setattr(PU, "rollback", lambda r, rc2, done: [u"[回滚] stub 已复原"])
    monkeypatch.setattr(PU, "locked", lambda p: False)

    def _ctl(root, act, timeout=180):
        rec.ctl.append(act)
        return 0, u"stub"

    def _probe(root, port=None, wait_s=PU.HEALTH_WAIT_S):
        rec.probe.append(wait_s)
        ok = bool(probe_seq.pop(0)) if probe_seq else False
        return ok, [(u"[OK] stub 探得" if ok else u"[FAIL] stub 探 ⛔ 达")]

    monkeypatch.setattr(PU, "ctl", _ctl)
    monkeypatch.setattr(PU, "probe_health", _probe)
    return rec


def _args(tmp_path):
    return argparse.Namespace(root=str(tmp_path / "root"), src=None, manifest=None,
                              staged=str(tmp_path / "stage"), force=False,
                              no_restart=False, go=True, json=False)


def test_probe_fail_never_says_done_and_restarts(tmp_path, monkeypatch, capsys):
    u"""T2 ＋ T3：探 ⛔ 得 ⇒ ⛔ 称「成」∧ 回滚毕**再起一次**（＋ 短窗重探）。"""
    (tmp_path / "root").mkdir()
    rec = _wire(monkeypatch, tmp_path, [False, True])
    rc = PU.run(_args(tmp_path))
    out = capsys.readouterr().out
    assert rc == 2
    assert rec.ctl == [u"stop", u"start", u"start"], rec.ctl
    assert rec.probe[0] == PU.HEALTH_WAIT_S
    assert rec.probe[1] == PU.RESTART_WAIT_S
    assert u"待探活" in out
    assert u"服已重起" in out
    assert u"重启：成" not in out


def test_restart_probe_fail_books_the_stop(tmp_path, monkeypatch, capsys):
    u"""T4 反控：重探亦 ⛔ 得 ⇒ 明书「停」之态 ＋ 去处（⛔ 留「停」而不言）。"""
    (tmp_path / "root").mkdir()
    rec = _wire(monkeypatch, tmp_path, [False, False])
    rc = PU.run(_args(tmp_path))
    out = capsys.readouterr().out
    assert rc == 2
    assert rec.ctl == [u"stop", u"start", u"start"], rec.ctl
    assert u"回滚后之服 ⛔ 答探活" in out
    assert u"关窗重开" in out