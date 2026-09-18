# -*- coding: utf-8 -*-
"""X-16 余项（2026-09-18 拍「`events.py::tail()` 吞坏行 —— 做，但先做受控复现」）验收。

背景：`core/pa/events.py::EventLog.tail()` 原文是

    for ln in open(self.path, encoding="utf-8"):
        try:      out.append(json.loads(ln))
        except Exception:  continue        # ← 跳过但**无计数、无上报**

与 `DispatchRecord._load()`（`core/pa/dispatch.py`，`5ab9d29`）**同族**（append-only 读），
差别在**可见性**：后者有计数 + stderr，前者完全静默（经验库 `L-08`：吞异常把「文件坏了」
变成「数据没了」）。

**受控复现（改前基线，`data/tmp/b5_work/x21/events_repro_head.txt`）**：
  · 末行半截 ⇒ 静默跳过，**stderr 空**，无计数；
  · **非对象行（JSON 数组）⇒ 原样返回 ⇒ 下游 `export_markdown()` 抛 `AttributeError`**（真崩）。

**处置口径**：append-only 的坏行**不抛**（不像状态文件那样 fail-loud），但必须**可见**
—— 跳过该行 + 计数（`corrupt_lines`）+ 写 stderr；其余历史保留。

判据（与「被判定的事」同层）：
 ① 坏行 ⇒ 其余历史保留 + `corrupt_lines == 1` + stderr 有报（不许静默、不许当空历史）；
 ② 非对象行 ⇒ 跳过 + 计数 + **下游 `export_markdown()` 不再崩**（改前必假）；
 ③ 空行/结尾换行 ⇒ **不算坏行**（防「把正常当坏行」的假警报）；
 ④ 干净文件 ⇒ `corrupt_lines == 0` + stderr 空（防假警报）；
 ⑤ 文件不存在 ⇒ `[]` + 0（新用户正常，**不是**损坏）；
 ⑥ 静态防回潮（AST，带反空转下限）：`tail()` 里解析失败路径**必须**可达 `_report`。
"""
from __future__ import annotations

import ast
import json
import pathlib

import pytest

from core.pa.events import EventLog

_REPO = pathlib.Path(__file__).resolve().parents[2]
_EVENTS_PY = _REPO / "core" / "pa" / "events.py"

_GOOD = [
    '{"seq": 1, "ts": "t1", "domain": "d1", "kind": "k1", "source": "s1", "payload": {"value": 1}}',
    '{"seq": 2, "ts": "t2", "domain": "d2", "kind": "k2", "source": "s2", "payload": {"value": 2}}',
]


def _write(tmp_path, name, lines, trailing_newline=True):
    p = tmp_path / name
    body = "".join(l + "\n" for l in lines)
    if not trailing_newline and lines:
        body = body[:-1]
    p.write_text(body, encoding="utf-8")
    return p


def test_坏行必须可见_其余历史保留(tmp_path, capsys):
    """① 末行半截 ⇒ 跳过 + 计数 + stderr；其余历史保留（改前：静默、无计数）。"""
    p = _write(tmp_path, "trunc.jsonl", _GOOD + ['{"seq": 3, "domain": "d3", "kind": "trunc'],
               trailing_newline=False)
    log = EventLog(p)
    assert [r["kind"] for r in log.tail(50)] == ["k1", "k2"]
    assert log.corrupt_lines == 1
    assert "第 3 行不可解析" in capsys.readouterr().err


def test_非对象行不再打穿下游(tmp_path, capsys):
    """② 非对象行（JSON 数组）⇒ 跳过 + 计数 + 下游不再抛（改前必假：AttributeError）。"""
    p = _write(tmp_path, "nonobj.jsonl", _GOOD + ["[1, 2, 3]"])
    log = EventLog(p)
    assert [type(r).__name__ for r in log.tail(50)] == ["dict", "dict"]
    assert log.corrupt_lines == 1
    assert "第 3 行结构不符" in capsys.readouterr().err
    md = EventLog(p).export_markdown()          # 改前：AttributeError: 'list' object has no attribute 'get'
    assert md.startswith("# PA ")


def test_空行与结尾换行不算坏行(tmp_path, capsys):
    """③ 空白行 ⇒ 静默跳过且**不计入** `corrupt_lines`（防假警报）。"""
    p = _write(tmp_path, "blank.jsonl", _GOOD + ["", "   "])
    log = EventLog(p)
    assert [r["kind"] for r in log.tail(50)] == ["k1", "k2"]
    assert log.corrupt_lines == 0
    assert capsys.readouterr().err == ""


def test_干净文件不留噪声(tmp_path, capsys):
    """④ 干净文件 ⇒ 0 计数 + stderr 空（防假警报：不能把正常读变成告警）。"""
    p = _write(tmp_path, "clean.jsonl", _GOOD)
    log = EventLog(p)
    assert [r["kind"] for r in log.tail(50)] == ["k1", "k2"]
    assert log.corrupt_lines == 0
    assert capsys.readouterr().err == ""


def test_文件不存在是空历史不是损坏(tmp_path):
    """⑤ 文件不存在 ⇒ `[]` + 0（新用户正常路径）。"""
    log = EventLog(tmp_path / "missing.jsonl")
    assert log.tail(50) == []
    assert log.corrupt_lines == 0


def test_静态防回潮_解析失败路径必须可达_report():
    """⑥ 结构判据（AST）：`tail()` 内 `json.loads` 的失败分支**必须**调 `_report`。

    带**反空转下限**：源长度 / 必须找到 `EventLog.tail` / 必须找到一个含 `json.loads` 的 `try`。
    """
    src = _EVENTS_PY.read_text(encoding="utf-8")
    assert len(src) > 2000, "读取的源码过短 ⇒ 判据可能空转"
    assert "def _report" in src, "`_report` 不存在 ⇒ 判据可能空转"
    tree = ast.parse(src)
    tail = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "EventLog":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "tail":
                    tail = item
    assert tail is not None, "没找到 `EventLog.tail` ⇒ 判据可能空转"
    checked = 0
    for node in ast.walk(tail):
        if not isinstance(node, ast.Try):
            continue
        parses = any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "loads"
            for stmt in node.body for c in ast.walk(stmt)
        )
        if not parses:
            continue
        checked += 1
        calls = [
            n.func.attr for h in node.handlers for n in ast.walk(h)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        ]
        assert "_report" in calls, "解析失败分支没有调 `_report` ⇒ 坏行又变静默（X-16 回潮）"
    assert checked == 1, "含 `json.loads` 的 try 数异常（实测 %d）⇒ 判据可能空转" % checked
