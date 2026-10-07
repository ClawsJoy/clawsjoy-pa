# -*- coding: utf-8 -*-
u"""pm_1715 §三.1⒜ 之齿：探活之窗**与壳同**（`40 s ⇒ 120 s`）＋ 探中之心跳（TD f202f89 · 2026-10-07）。

病（老板净机 · 一手之日志）：起服令 `rc 0` 而探 `/health` `42.4 s` ⛔ 达 ⇒ 回滚 ⇒「一直失败」。
⭐ 一处之疑（我 `1714 §二.5` 所报 · 你 `1715 §三.1⒜` 所裁）：
  **壳之 `startService` 等 `waitHealth(120000)` ＝ 120 s；器之 `probe_health` 窗唯 `40 s`**
  ⇒ 慢起（向量库 ／ 杀软扫新件 ／ 冷盘）⇒ 器必判败而回滚（而服或旋起）⇒ 「每次都败」之形。
⭐ 并须「凡等待必有进度 ＋ 时长」（pm_1617 §一.3）⇒ 探中每 `PROBE_TICK_S` 一行心跳（⛔ 刷屏）。

判据：
  W1 一处定形：`HEALTH_WAIT_S` **须 ＝ 壳之窗**（自 `shell/main.js` 之 `waitHealth(<毫秒>)` 取读 ⇒ 比）。
  W2 一处定形：`PROBE_TICK_S` ＝ `10.0`（⛔ 刷屏 · 每 10 s 一行）。
  W3 正控（心跳）：窗内 ⛔ 答之形 ⇒ 首行**恰一次** ∧ 心跳**至少一行**（`已 N s ／ 窗 M s`）。
  W4 反控（快答 ⛔ 心跳）：服即答 ⇒ ⛔ 有「已」之行（免常态刷屏）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_probe_window_1715.py -q
"""
from __future__ import annotations

import importlib.util
import re
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIN_PA = ROOT / "scripts" / "win_pa"
if str(WIN_PA) not in sys.path:
    sys.path.insert(0, str(WIN_PA))


def _load_pa_update():
    spec = importlib.util.spec_from_file_location("pa_update_1715", str(WIN_PA / "pa_update.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PU = _load_pa_update()


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_W1_window_matches_shell(tmp_path):
    u"""W1：器之窗 ＝ 壳之窗（一处定形；改一处而 ⛔ 改另一处 ⇒ 此齿必红）。"""
    main_js = (ROOT / "shell" / "main.js").read_text(encoding="utf-8")
    ms = [int(x) for x in re.findall(r"waitHealth\((\d+)\)", main_js)]
    assert ms, u"shell/main.js 未见 waitHealth(<ms>) ⇒ 齿之根 ⛔ 立"
    want = ms[0] / 1000.0
    assert PU.HEALTH_WAIT_S == want, (PU.HEALTH_WAIT_S, want, ms)


def test_W2_tick_is_ten_seconds():
    u"""W2：心跳之刻 ＝ 10 s（一处定形 · ⛔ 刷屏）。"""
    assert PU.PROBE_TICK_S == 10.0, PU.PROBE_TICK_S


def test_W3_heartbeat_while_waiting(tmp_path, monkeypatch, capsys):
    u"""W3 正控：窗内 ⛔ 答 ⇒ 首行恰一次 ∧ 心跳至少一行。"""
    monkeypatch.setattr(PU, "PROBE_TICK_S", 0.5)
    R = tmp_path / "root"
    R.mkdir()
    (R / "version.json").write_text(u"{}", encoding="utf-8")
    ok, rows = PU.probe_health(str(R), port=_free_port(), wait_s=1.8)
    out = capsys.readouterr().out
    assert ok is False, rows
    head = [ln for ln in out.splitlines() if re.match(r"^\[\.\.\] 探 .*（窗 ", ln)]
    beats = [ln for ln in out.splitlines() if u"已 " in ln and u"／ 窗 " in ln]
    assert len(head) == 1, out
    assert len(beats) >= 1, out
    assert any(u"[FAIL]" in r for r in rows), rows


def test_W4_no_heartbeat_when_fast(tmp_path, capsys):
    u"""W4 反控：根之端口 ⛔ 可读（即答之形）⇒ ⛔ 有「已」之行。"""
    R = tmp_path / "bare"
    R.mkdir()
    (R / "version.json").write_text(u"{}", encoding="utf-8")
    ok, rows = PU.probe_health(str(R), wait_s=1.0)
    out = capsys.readouterr().out
    assert ok is False, rows
    assert not [ln for ln in out.splitlines() if u"已 " in ln], out
    assert any(u"端口取不得" in r for r in rows), rows