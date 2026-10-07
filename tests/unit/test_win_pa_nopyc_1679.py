# -*- coding: utf-8 -*-
u"""pm_1679 \u00a7\u4e94.1 \u4e4b\u9f7f \u2014\u2014 \u24dc \u5b50\u8fdb\u7a0b \u26d4 \u5199 `.pyc` \uff08\u8f7d\u8377\u4e4b\u6839 \u21d2 \u88c5\u6839\uff09\uff1b\u249d \u8d77\u6570\u4e4b\u5f84\u5f52\u4e00\u3002

\u4ee5\u4f55\u5f62\u8c03\u7528\uff1a
  python -X utf8 -B -m pytest tests/unit/test_win_pa_nopyc_1679.py -q

\u5224\u636e\uff1a
  N1 \u4e00\u5904\u5b9a\u5f62\uff1a`pa_nowindow.py` \u4e4b\u5b50\u8fdb\u7a0b\u5fc5\u7ecf `py_argv`\uff08\u5e26 `-B`\uff09\u00b7 `child_env`\uff08`PYTHONDONTWRITEBYTECODE=1`\uff09\uff1b
     \u6e90\u5185 \u26d4 \u590d\u73b0\u88f8\u5f62\uff08`[sys.executable, '-X', 'utf8'`\uff09\u3002
  N2 \u884c\u4e3a\u4e4b\u6b63\u53cd\u63a7\uff1a`-B` \u21d2 \u26d4 \u843d `__pycache__`\uff08\u6b63\uff09\uff1b\u65e0 `-B` \u21d2 \u843d\uff08\u53cd \u21d2 \u8bc1\u9f7f\u975e\u7a7a\u8f6c\uff09\u3002
  N3 \u8d77\u670d\u4e4b argv \u4e0e env\uff1a`-B` \u5728 `-u` \u4e4b\u524d \u00b7 \u4e14\u8d77\u670d\u4e4b Popen \u5e26 `env=child_env()`\u3002
  N4 \u5f52\u4e00\uff1a`feedback_dir` \u21d2 `os.path.normpath`\uff08\u26d4 \u6df7\u5206\u9694\u7b26\uff09\uff1b\u53cd\u63a7\uff1a`os.path.join` \u4e4b\u539f\u5f62\u542b `/`\u3002
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
sys.path.insert(0, str(WPA))
sys.path.insert(0, str(ROOT))

import pa_nowindow as PN  # noqa: E402
from core.lib import feedback_target as FT  # noqa: E402


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


# ---------- N1 \u4e00\u5904\u5b9a\u5f62 ----------

def test_N1_argv_and_env_one_place():
    a = PN.py_argv("x.py")
    assert a[:4] == [sys.executable, "-X", "utf8", "-B"], a
    au = PN.py_argv("x.py", "--go", unbuffered=True)
    assert au[:5] == [sys.executable, "-X", "utf8", "-B", "-u"], au
    assert au[5:] == ["x.py", "--go"], au
    e = PN.child_env({"A": "1"})
    assert e["PYTHONDONTWRITEBYTECODE"] == "1" and e["A"] == "1", e
    assert PN.child_env()["PYTHONDONTWRITEBYTECODE"] == "1"


def test_N1b_source_has_no_bare_python_spawn():
    t = _read(WPA / "pa_nowindow.py")
    bare = u"[sys.executable, '-X', 'utf8'"
    assert t.count(bare) == 1, u"\u88f8\u5f62\u987b\u552f\u5728 `py_argv` \u4e4b\u5185\uff08\u5176\u4f59\u7686\u7ecf\u4e00\u5904\u5b9a\u5f62\uff09"
    i = t.find(bare)
    assert u"def py_argv" in t[:i], u"\u8be5\u88f8\u5f62\u987b\u5c5e\u4e8e py_argv"
    assert t.count(u"env=child_env()") >= 4, u"\u5b50\u8fdb\u7a0b\u7686\u987b\u5e26 env\uff08\u542b\u8d77\u670d \u2044 preflight \u2044 \u81ea\u6d3e\u9063\uff09"


# ---------- N2 \u884c\u4e3a\u4e4b\u6b63\u53cd\u63a7 ----------

def test_N2_no_pyc_positive_and_negative(tmp_path):
    pkg = tmp_path / "pkgz"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(u"X = 1\n", encoding="utf-8")
    code = u"import sys;sys.path.insert(0,%r);import pkgz" % str(tmp_path)

    subprocess.run([sys.executable, "-B", "-c", code], check=True, timeout=120)
    hit_pos = list(pkg.glob("__pycache__/*.pyc"))
    assert not hit_pos, u"\u6709 `-B` \u21d2 \u26d4 \u5f97\u843d `.pyc`\uff08\u6b63\u63a7\uff09\uff1a%s" % (hit_pos,)

    subprocess.run([sys.executable, "-c", code], check=True, timeout=120)
    hit_neg = list(pkg.glob("__pycache__/*.pyc"))
    assert hit_neg, u"\u65e0 `-B` \u21d2 \u987b\u843d\uff08\u53cd\u63a7 \u21d2 \u8bc1\u9f7f\u975e\u7a7a\u8f6c\uff09"


def test_N2b_runtime_python_respects_env(tmp_path):
    u"""env \u4e4b\u8986\u76d6\uff08\u5b59\u8fdb\u7a0b\uff09\uff1a\u7f6e env \u21d2 \u65e0 `-B` \u4ea6 \u26d4 \u843d\u3002"""
    pkg = tmp_path / "pkgy"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(u"Y = 1\n", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, "-c", u"import sys;sys.path.insert(0,%r);import pkgy" % str(tmp_path)],
                   check=True, timeout=120, env=env)
    assert not list(pkg.glob("__pycache__/*.pyc")), u"env \u7f6e\u4e4b \u21d2 \u26d4 \u843d"


# ---------- N3 \u8d77\u670d\u4e4b argv/env ----------

def test_N3_start_spawn_is_covered():
    t = _read(WPA / "pa_nowindow.py")
    assert u"_argv = py_argv(APP, unbuffered=True)" in t, u"\u8d77\u670d\u4e4b argv \u987b\u7ecf\u4e00\u5904\u5b9a\u5f62"
    i = t.find(u"_argv = py_argv(APP, unbuffered=True)")
    blk = t[i:i + 260]
    assert u"env=child_env()" in blk, u"\u8d77\u670d\u7684 Popen \u987b\u5e26 env" + blk
    assert u"cmd = py_argv(PREFLIGHT" in t, u"preflight \u4e4b\u5b50\u8fdb\u7a0b\u540c\u987b\u7ecf\u6b64"


# ---------- N4 \u5f52\u4e00 ----------

def test_N4_feedback_dir_normalized(tmp_path):
    src = {u"dir": u"data/pa/feedback"}
    got = FT.feedback_dir(str(tmp_path), src)
    want = os.path.normpath(os.path.join(str(tmp_path), u"data/pa/feedback"))
    assert got == want, (got, want)
    raw = os.path.join(str(tmp_path), u"data/pa/feedback")
    if os.name == u"nt":
        assert u"/" not in got, u"\u26d4 \u5f97\u6df7\u5206\u9694\u7b26\uff1a" + got
        assert u"/" in raw, u"\u53cd\u63a7\uff1a\u539f\u5f62\u672c\u542b `/` \u21d2 \u9f7f\u53ef\u8fa8"


def test_N4b_feedback_dir_absolute_is_normpath(tmp_path):
    src = {u"dir": str(tmp_path) + u"/x/y"}
    got = FT.feedback_dir(None, src)
    assert got == os.path.normpath(str(tmp_path) + u"/x/y"), got