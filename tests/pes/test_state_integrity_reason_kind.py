# -*- coding: utf-8 -*-
"""`detect_uninstrumented` 的**成因分报**（`reason_kind`）—— `X-16` 批 D · `D2`（DS 2026-09-18 拍做）。

背景（受控复现，`data/tmp/b5_work/x21/d2_repro_head.txt`）：

    S1 真·无台账（handwritten.json）      ⇒ reason「无写台账：该文件**从未经由唯一出口写过**」
    S2 **台账存在但整份不可解析**         ⇒ 旧版把**同一句**也给了它 ⇒ 「红」的两种成因**零鉴别力**
    S3 台账**部分**坏（1 好 1 坏）         ⇒ 静默忽略坏行、**无任何计数**
    S4 文件不存在                          ⇒ instrumented=True + reason「文件不存在」
    S5 绕过出口改盘                        ⇒ reason「…不符 ⇒ 存在未插桩写者」

⇒ 旧版红条只有 `reason` 一句**人读文本**（`L-01`/`L-06` 同族：判据与被判定的事不同层，
且成因不可机读）。本批加 `reason_kind`（**机器可读、永远存在**）＋ `log_lines`/`log_bad_lines`。

判据（与「被判定的事」同层）：
 ① 五类成因**分报**，且**旧版合并的两类必须不同**（`no_log` ≠ `log_unreadable`）；
 ② 「台账坏」**不得**说成「无台账」（`reason` 里不得出现「从未经由唯一出口写过」/「无写台账」）；
 ③ **部分损坏可见**：`log_bad_lines` 计数（旧版恒 0）；
 ④ 契约：`detect_uninstrumented` 与 `scan_state_dir` 每条输出**都带** `reason_kind`，取值在枚举内；
 ⑤ 反例（有牙）：若把 `log_unreadable` 折叠回 `no_log`（或删掉计数）⇒ 判据必须红。
"""
from __future__ import annotations

import json

import pytest

from core.pes.state_integrity import (
    WRITE_LOG_SUFFIX,
    StateFile,
    detect_uninstrumented,
    scan_state_dir,
)

_KINDS = {"ok", "missing", "no_log", "log_unreadable", "mismatch"}


def _write_via_exit(p, writer="w.test", payload=None):
    sf = StateFile(p, writer=writer)
    sf.update_runtime(lambda d: d.update(payload or {"a": 1}), writer=writer)
    return sf


def test_五类成因分报且互不混同(pes_dir):
    """① 五类成因各归其位；旧版合并的 `no_log`/`log_unreadable` 必须不同。"""
    # ok
    p_ok = pes_dir / "ok.json"
    _write_via_exit(p_ok, writer="w.ok")
    # no_log（真·从未经出口写）
    p_no = pes_dir / "hand.json"
    p_no.write_text('{"a": 1}', encoding="utf-8")
    # log_unreadable（台账存在但整份坏）
    p_bad = pes_dir / "broken.json"
    p_bad.write_text('{"a": 2}', encoding="utf-8")
    (pes_dir / ("broken.json" + WRITE_LOG_SUFFIX)).write_text("not-json\n{also broken\n", encoding="utf-8")
    # mismatch（绕过出口改盘）
    p_mis = pes_dir / "tamper.json"
    _write_via_exit(p_mis, writer="w.tamper", payload={"a": 5})
    p_mis.write_text(json.dumps({"a": 999}), encoding="utf-8")

    kinds = {
        "ok": detect_uninstrumented(p_ok)["reason_kind"],
        "no_log": detect_uninstrumented(p_no)["reason_kind"],
        "log_unreadable": detect_uninstrumented(p_bad)["reason_kind"],
        "mismatch": detect_uninstrumented(p_mis)["reason_kind"],
        "missing": detect_uninstrumented(pes_dir / "nope.json")["reason_kind"],
    }
    assert kinds == {
        "ok": "ok",
        "no_log": "no_log",
        "log_unreadable": "log_unreadable",
        "mismatch": "mismatch",
        "missing": "missing",
    }, kinds
    assert kinds["no_log"] != kinds["log_unreadable"], "「无台账」与「台账坏了」又被合并 ⇒ 零鉴别力"


def test_台账坏不得说成无台账(pes_dir):
    """② 「台账存在但整份不可解析」不得被描述成「从未经出口写过」。"""
    p = pes_dir / "broken.json"
    p.write_text('{"a": 2}', encoding="utf-8")
    (pes_dir / ("broken.json" + WRITE_LOG_SUFFIX)).write_text("garbage\n", encoding="utf-8")
    r = detect_uninstrumented(p)
    assert r["instrumented"] is False
    assert r["reason_kind"] == "log_unreadable"
    assert "从未经由唯一出口写过" not in r["reason"], r["reason"]
    assert "无写台账" not in r["reason"], r["reason"]
    assert "人工核对" in r["reason"], r["reason"]


def test_部分损坏也必须可见(pes_dir):
    """③ 台账部分坏（1 好 1 坏）：磁盘仍与最后可读行一致 ⇒ ok，但**坏行计数不得为 0**。"""
    p = pes_dir / "partial.json"
    _write_via_exit(p, writer="w.partial", payload={"a": 3})
    log = pes_dir / ("partial.json" + WRITE_LOG_SUFFIX)
    log.write_text(log.read_text(encoding="utf-8") + "garbage-line\n", encoding="utf-8")
    r = detect_uninstrumented(p)
    assert r["reason_kind"] == "ok" and r["instrumented"] is True
    assert r["log_lines"] == 2 and r["log_bad_lines"] == 1, r
    assert r["last_writer"] == "w.partial"


def test_reason_kind_是契约_detect_与_scan_都带(pes_dir):
    """④ 机器可读字段恒存在，且 `scan_state_dir` 的每条都带它（消费方不必再猜）。"""
    p = pes_dir / "loose.json"
    p.write_text("{}", encoding="utf-8")
    rows = scan_state_dir(pes_dir)
    assert rows, "扫描结果为空 ⇒ 判据可能空转"
    for r in rows:
        assert "reason_kind" in r, r
        assert r["reason_kind"] in _KINDS, r
        assert "log_lines" in r and "log_bad_lines" in r, r
    one = detect_uninstrumented(p)
    assert set(("reason_kind", "log_lines", "log_bad_lines")).issubset(one.keys())
    assert one["reason_kind"] == "no_log"
