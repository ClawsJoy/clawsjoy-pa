# -*- coding: utf-8 -*-
u"""pm_1569 §二 之齿：净机 Python 锁 **CPython 3.12 · 64 位**（前置闸 fail-loud · 一处定形）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_py_required_1569.py -q

由（pm_1569 §二）：包内 wheel 21 件皆 `cp312-cp312-win_amd64`（我一手器取）⇒ 3.10 ／ 3.11 ／ 32 位
  之机**装必败**；旧稿（安装页 §〇.2）书「3.10 或更新」＝ **假言** ⇒ 须正 ＋ 前置闸须**检版 fail-loud**。

判据：
  ⒜ 常量：`PY_REQUIRED == (3, 12)` ∧ `PY_REQUIRED_BITS == 64`。
  ⒝ 纯函数：CPython ∧ >= 3.12 ∧ 64 位 ⇒ 过；3.10 ／ 32 位 ／ 非 CPython ⇒ 判红 ＋ **点名 ＋ 修之门**。
  ⒞ 探针：本机（CPython 3.12.10 · 64 位）⇒ 过。
  ⒟ 一处定形：安装器之 Python 闸**承前置器之出**（名含 `3.12` ／ `64` 位 · 辞同轴）。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WP = ROOT / "scripts" / "win_pa"
if str(WP) not in sys.path:
    sys.path.insert(0, str(WP))

import preflight_start as PF  # noqa: E402


def _install_mod():
    spec = importlib.util.spec_from_file_location("install_win_pa_1569", WP / "install_win_pa.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------- ⒜ 常量 ----------

def test_constants():
    assert PF.PY_REQUIRED == (3, 12), PF.PY_REQUIRED
    assert PF.PY_REQUIRED_BITS == 64, PF.PY_REQUIRED_BITS


# ---------- ⒝ 纯函数：正 ＋ 三反 ----------

def test_classify_ok():
    ok, why, door = PF.classify_python(u"cpython", (3, 12, 10), 64)
    assert ok is True and door == u"", (ok, why, door)
    assert u"3.12.10" in why and u"64" in why, why


def test_classify_310_red():
    ok, why, door = PF.classify_python(u"cpython", (3, 10, 11), 64)
    assert ok is False
    assert u"3.10.11" in why, why
    assert u"3.12" in door and u"修之门" in door, door


def test_classify_32bit_red():
    ok, why, door = PF.classify_python(u"cpython", (3, 12, 10), 32)
    assert ok is False and u"64" in door, (why, door)


def test_classify_non_cpython_red():
    ok, _why, _door = PF.classify_python(u"pypy", (3, 12, 0), 64)
    assert ok is False, u"非 CPython（wheel 不相容）⇒ 判红"


# ---------- ⒞ 探针（本机之实）----------

def test_probe_python_ok_on_this_machine():
    ok, why, _door = PF.probe_python()
    assert ok is True, u"本机 ＝ CPython 3.12.10 · 64 位（齿之基）—— 实：%s" % why


# ---------- ⒟ 一处定形：安装器之闸承前置器 ----------

def test_install_gate_uses_preflight_wording():
    m = _install_mod()
    g = m.preflight_gates(offline=False)
    py = [x for x in g if u"Python" in x["name"]]
    assert py, g
    assert u"3.12" in py[0]["name"] and u"64" in py[0]["name"], py[0]
    assert py[0]["reason"], py[0]
    if not py[0]["ok"]:
        assert py[0]["note"], (u"败之闸须附修之门", py[0])