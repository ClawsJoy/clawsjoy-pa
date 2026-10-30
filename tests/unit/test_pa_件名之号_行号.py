# -*- coding: utf-8 -*-
u"""齿：CEO 2221 §八.3 ／ PM 2222 §四 之「**件名之号 ⇒ 须 ≡ 行号**」∧ PM 2237 §四 ／ 2241 §一 之
   「**件内 `序号:` 栏 ⇒ 须 ≡ 行号**」（器在 `scripts/dev/投一步.py` · 一处出 · 回填在落箱之前）。

⭐ 离机 · 临时目录（器之 selftest 自持）⇒ ⛔ 触本仓 ／ ⛔ 触真箱 ／ ⛔ 触台账。
⚠ 一处定形：齿居器内（同源）⇒ 本件唯**挂**之（⛔ 另写一套断言 —— 免得漂）；
   ⭐ 且以**子进程**挂（器于导入期走 `sys.stdout.reconfigure` ⇒ ⛔ 直接 import）。
⚠ 名之字（照实）：PM 2241 §一.4 荐名 `test_序栏_≡_名之号` —— `≡`（U+2261）⛔ 是 Python 之标识符字
   ⇒ 用之 ⛔ 得（SyntaxError：invalid character）⇒ 本件取 `test_tou1_序栏_同_名之号`。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V9 = os.path.dirname(os.path.dirname(HERE))
_TOU = os.path.join(V9, "scripts", "dev", u"投一步.py")


def _run(args):
    return subprocess.run([sys.executable, "-X", "utf8", "-B", _TOU] + args,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _selftest_out():
    r = _run(["--self-test"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert u"[总判] PASS" in r.stdout, r.stdout + r.stderr
    return r.stdout


def test_tou1_name_num_selftest():
    out = _selftest_out()
    assert u"自证 8.2 件名之号" in out, out
    assert u"名 ⛔ ≡ 号 ⇒ False" in out, out


def test_tou1_序栏_同_名之号():
    u"""PM 2237 §四 ／ 2241 §一 之齿：件内 `序号:` 栏 ⇒ 须 ≡ 行号。

    ⭐ 反控（真咬）：造栏 2234 而号 2235 ⇒ 必红（＝ False）。
    ⭐ 报 ＋ 拒：件无 `序号:` 栏 ⇒ rc 4（⛔ 静默 · ⛔ 半落）。"""
    out = _selftest_out()
    assert u"自证 8.4 件内" in out, out
    assert u"造栏 2234 而号 2235 ⇒ 必红" in out, out
    assert u"真办 ⇒ 栏回填 ∧ 回读核 ⇒ 2235" in out, out
    assert u"演 ⇒ rc 0 ∧ ⛔ 落盘" in out, out
    assert u"无栏件 ⇒ rc 4（报 ＋ 拒" in out, out


def test_tou1_序栏_逐次报数():
    u"""PM 2241 §一.4 之「并报其数（逐次）」∧ 第 14 条：行号取台账之行 · 栏唯附核。"""
    r = _run(["--audit-name-num"])
    out = r.stdout + r.stderr
    assert u"核C · 件内" in out, out
    assert u"判据A · 名含 _dddd_" in out, out
    assert u"箱内在者核" in out, out


def test_tou1_name_gate_seven_forms():
    u"""庚（七式）之齿：三处同刻正（NAME_PAT ＋ docstring ＋ 反控）⇒ 见器之 self-test。"""
    out = _selftest_out()
    assert u"正控（七式）" in out, out
    assert u"不合「式清单」" in out, out
    assert u"首中 ＝ 庚" in out, out


def test_tou1_name_gate_report_no_deadword():
    u"""PM 2237 §一 之齿：报错文 ⛔ 书死字 ⇒ 须载「器所取之版号 ＋ 印（二形）＋ 取数刻」。"""
    out = _selftest_out()
    assert u"报错文 ⛔ 载死字（「今 v」）" in out, out
    assert u"报错文载「器所取之版号 ＋ 印（二形）＋ 取数刻」" in out, out
    assert u"印 md5[:16] " in out, out
    assert u"取数刻 " in out, out
