# -*- coding: utf-8 -*-
u"""pm_1651 §二.6（卸得净）＋ §三.3⒝ 之齿 —— 卸器 ⛔ 动用户数据（技术总监席 f202f89 · 2026-10-07）。

病（PM 一手 · pm_1651 §二.6）：卸器之「⛔ 动用户数据」**今唯人验**（老板净机之一手）
⇒ 无齿 ⇒ 改一行即可静默变「删你资料」而无人知（承「⛔ 以 rc 0 代成」）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_uninstall_1651.py -q

判据：
  U1 正控：`KEEP == "data"` —— 一名一义（留下之物唯此一名）
  U2 结构齿：缺省之清理批 ⇒ 唯「**逐名比较** `data`」之路 ∧ ⛔ 含对装根之整根删
  U3 正控：`--purge` ⇒ 含整根删（**唯 --purge** —— 免「缺省即毁」）
  U4 正控：`plan()` 之 files 条 ⇒ `keep == ["data"]`；`purge=True` ⇒ `keep == []`
  U5 正控：干跑之明书 ⇒ 言「留 …data」∧ ⛔ 言删 `data`
  U6 **行为齿**（真删 · 唯临根）：以缺省之批真跑一次 ⇒ `data/` **在** ∧ 程序件 **⛔ 在**
  U7 反控（U6 之镜）：以 `--purge` 之批 ⇒ 整根 **⛔ 在**（证 U6 非「批 ⛔ 跑」之假绿）
"""
from __future__ import annotations

import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location(
    "_up1651", str(ROOT / "scripts" / "win_pa" / "uninstall_pa.py"))
UP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UP)


def _fake_root(t):
    u"""临根（⛔ 触真仓）：`data/` 之哨兵 ＋ 程序件 ＋ 根级之件。"""
    r = os.path.join(t, "PA")
    os.makedirs(os.path.join(r, "data", "pa"), exist_ok=True)
    os.makedirs(os.path.join(r, "core", "lib"), exist_ok=True)
    os.makedirs(os.path.join(r, "logs"), exist_ok=True)
    io.open(os.path.join(r, "data", "pa", "sentinel.json"), "w", encoding="utf-8").write(u"哨兵")
    io.open(os.path.join(r, "core", "lib", "x.py"), "w", encoding="utf-8").write(u"程序件")
    io.open(os.path.join(r, "agent_gateway_enhanced.py"), "w", encoding="utf-8").write(u"入口")
    io.open(os.path.join(r, "logs", "gateway.log"), "w", encoding="utf-8").write(u"日志")
    return r


def _run_batch(text, where):
    u"""真跑一批（`cmd /c`）—— 批落 `where`（⛔ 入临根，免被自身删）。"""
    bp = os.path.join(where, "cleanup_%d.bat" % (abs(hash(text)) % 10 ** 8))
    io.open(bp, "w", encoding="utf-8", newline="").write(text)   # 镜像 `spawn_cleanup`
    return subprocess.run(["cmd", "/c", bp], capture_output=True, text=True, timeout=60)


def test_U1_one_name():
    assert UP.KEEP == u"data", UP.KEEP


def test_U2_structure_keeps_data_by_name():
    t = tempfile.mkdtemp(prefix="cjpa_up1651a_")
    try:
        r = _fake_root(t)
        txt = UP.cleanup_text(r)
        assert (u'if /i not "%%~nxD"=="' + UP.KEEP + u'"') in txt, txt
        cmd_lines = [ln for ln in txt.splitlines() if not ln.strip().lower().startswith(u"echo")]
        assert not [ln for ln in cmd_lines if (u'rmdir /s /q "' + r + u'"') in ln], \
            u"缺省之批之**令行** ⛔ 得整根删（echo 之提示可）"
        assert u'if /i not "%%~nxD"=="' + UP.KEEP + u'" rmdir' in txt, txt
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_U3_purge_only_when_asked():
    t = tempfile.mkdtemp(prefix="cjpa_up1651b_")
    try:
        r = _fake_root(t)
        txt = UP.cleanup_text(r, purge=True)
        assert u'rmdir /s /q "%s"' % r in txt, txt
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_U4_plan_keep_key():
    t = tempfile.mkdtemp(prefix="cjpa_up1651c_")
    try:
        r = _fake_root(t)
        files = [i for i in UP.plan(r) if i["item"] == "files"][0]
        assert files["keep"] == [UP.KEEP], files
        assert files["purge"] is False, files
        files2 = [i for i in UP.plan(r, purge=True) if i["item"] == "files"][0]
        assert files2["keep"] == [], files2
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_U5_dry_run_says_keep():
    t = tempfile.mkdtemp(prefix="cjpa_up1651d_")
    try:
        r = _fake_root(t)
        rc, lines = UP.render(r, False, True)
        blob = u"\n".join(lines)
        assert rc == 0, lines
        assert u"干跑" in blob, blob
        assert (u"留 %s" % UP.KEEP) in blob, blob
        assert u"干跑（⛔ 未撤）" in blob, blob
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_U6_real_run_keeps_data():
    u"""行为齿：缺省之批**真跑** ⇒ `data/` 在 ∧ 程序件 ⛔ 在（⛔ 唯看源码）。"""
    t = tempfile.mkdtemp(prefix="cjpa_up1651e_")
    try:
        r = _fake_root(t)
        _run_batch(UP.cleanup_text(r), t)
        assert os.path.isfile(os.path.join(r, "data", "pa", "sentinel.json")), u"**data 被删了**"
        assert os.path.isdir(os.path.join(r, "data")), u"**data 被删了**"
        assert not os.path.isdir(os.path.join(r, "core")), u"程序件 ⛔ 删"
        assert not os.path.isdir(os.path.join(r, "logs")), u"程序件 ⛔ 删"
        assert not os.path.isfile(os.path.join(r, "agent_gateway_enhanced.py")), u"根级件 ⛔ 删"
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_U8_control_lines_are_ascii():
    u"""结构齿：批之**令行**须 ASCII（中文唯入 `echo` ／ `rem`）—— UTF-8 之中文若被 cmd 以 GBK 解，
    其尾字节有 `0x5C`（反斜杠）之可能 ⇒ **吃下一行**（经典之坑）。故令行 ⛔ 载中文。
    """
    t = tempfile.mkdtemp(prefix="cjpa_up1651g_")
    try:
        r = _fake_root(t)
        bad = []
        for ln in UP.cleanup_text(r).splitlines():
            st = ln.strip().lower()
            if st.startswith((u"echo", u"rem", u"@")):
                continue
            try:
                ln.encode(u"ascii")
            except UnicodeEncodeError:
                bad.append(ln)
        assert not bad, bad
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_U7_purge_run_removes_all():
    u"""反控（U6 之镜）：`--purge` 之批真跑 ⇒ 整根 ⛔ 在（证 U6 非「批 ⛔ 跑」之假绿）。"""
    t = tempfile.mkdtemp(prefix="cjpa_up1651f_")
    try:
        r = _fake_root(t)
        _run_batch(UP.cleanup_text(r, purge=True), t)
        assert not os.path.exists(r), u"--purge 期整根 ⛔ 在"
    finally:
        shutil.rmtree(t, ignore_errors=True)
