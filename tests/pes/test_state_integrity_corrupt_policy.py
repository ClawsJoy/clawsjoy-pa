# -*- coding: utf-8 -*-
"""`X-17②` 批 1：`update_runtime(on_corrupt=...)` 的坏状态策略（含反例证明）。

背景（受控复现 `data/tmp/pa_ui_corrupt_probe.txt`）：
`read()` 判 `corrupted` 之后，`update_runtime()` **原本仍会写**（**判定在写之后**）
⇒ 「接统一出口」只得到「**可恢复的重置**」，**不是** fail-loud。
本批加 `on_corrupt`，其中 `"refuse"` ＝ **拒绝写入**。

反例证明（改前必假 / 改后必真）：
  · 改前（HEAD）：**无** `on_corrupt` ⇒ 传它即 `TypeError`（本文件在 HEAD 上跑不起来）
  · 改后：`refuse` ⇒ 坏状态下**一个字节都不写**
本文件的**护栏**：默认 `"salvage"` 的行为必须与改前**逐字节一致**。
"""
import json

import pytest

from core.pes.state_integrity import CORRUPT_POLICIES, StateFile, StateReport


def _sf(tmp_path, name="s.json"):
    return StateFile(tmp_path / name, writer="test.corrupt_policy")


def _write(tmp_path, text, name="s.json"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _writes(tmp_path):
    return list(tmp_path.glob(".quarantine/*.bad"))


# ------------------------------------------------------------ refuse 主体
def test_refuse_坏状态一个字节都不写(tmp_path):
    """**核心反例**：`refuse` 下坏状态必须**零写入**（含不得执行 mutate）。"""
    sf = _sf(tmp_path)
    p = _write(tmp_path, '{"a": 1, "b": ')          # 半截 JSON
    before = p.read_bytes()
    called = []

    doc, rep = sf.update_runtime(lambda d: called.append(1), writer="t", on_corrupt="refuse")

    assert rep.corrupted is True
    assert rep.ok is False
    assert rep.written is False, "refuse ⇒ written 必须为 False"
    assert rep.reason == "invalid_json", "reason 必须被透传（改前这里恒为空串）"
    assert rep.degradations, "必须记降级（无静默降级）"
    assert called == [], "refuse 下不得执行 mutate"
    assert p.read_bytes() == before, "refuse ⇒ 活文件一个字节都不写"


def test_refuse_原文件仍进隔离区_证据不丢(tmp_path):
    sf = _sf(tmp_path)
    _write(tmp_path, '{"a": ')
    sf.update_runtime(lambda d: None, writer="t", on_corrupt="refuse")
    assert _writes(tmp_path), "拒绝写不等于丢证据 —— 原文件必须已隔离"


def test_refuse_只在坏状态生效_合法状态照常写(tmp_path):
    """护栏：`refuse` 不得把**正常路径**一起改坏。"""
    sf = _sf(tmp_path)
    p = _write(tmp_path, json.dumps({"a": 1, "threads": []}))
    doc, rep = sf.update_runtime(lambda d: d.update({"b": 2}), writer="t", on_corrupt="refuse")
    assert rep.ok is True and rep.written is True
    assert json.loads(p.read_text(encoding="utf-8")) == {"a": 1, "threads": [], "b": 2}


def test_refuse_顶层非dict也算坏(tmp_path):
    sf = _sf(tmp_path)
    p = _write(tmp_path, "[1, 2, 3]")
    before = p.read_bytes()
    doc, rep = sf.update_runtime(lambda d: d.update({"x": 1}), writer="t", on_corrupt="refuse")
    assert rep.corrupted is True and rep.reason == "not_object"
    assert p.read_bytes() == before


# ------------------------------------------------------------ 默认行为不变（护栏）
def test_默认salvage_行为与改前一致(tmp_path):
    """**护栏**：默认策略下坏状态**照写**（＝改前行为，一字不变）。"""
    sf = _sf(tmp_path)
    p = _write(tmp_path, '{"a": 1, "b": ')
    doc, rep = sf.update_runtime(lambda d: d.update({"new": 1}), writer="t")
    assert rep.corrupted is True and rep.ok is False
    assert rep.written is True, "默认 salvage ⇒ 仍写（既有行为）"
    assert json.loads(p.read_text(encoding="utf-8")) == {"new": 1}


def test_overwrite_是salvage的显式别名(tmp_path):
    sf = _sf(tmp_path)
    p = _write(tmp_path, '{"a": 1, "b": ')
    doc, rep = sf.update_runtime(lambda d: d.update({"new": 1}), writer="t", on_corrupt="overwrite")
    assert rep.written is True
    assert json.loads(p.read_text(encoding="utf-8")) == {"new": 1}


def test_正常路径written为True(tmp_path):
    sf = _sf(tmp_path)
    doc, rep = sf.update_runtime(lambda d: d.update({"a": 1}), writer="t")
    assert rep.written is True and rep.corrupted is False


def test_as_dict_暴露written(tmp_path):
    d = StateReport(str(tmp_path / "s.json")).as_dict()
    assert "written" in d


# ------------------------------------------------------------ 非法值必须 fail-loud
@pytest.mark.parametrize("bad", ["", "Refuse", "salvag", "ignore", None])
def test_非法策略必须报错不得静默回落(tmp_path, bad):
    """**反例**：拼错的策略**不得**静默当成默认值（那会静默放宽判据）。"""
    sf = _sf(tmp_path)
    _write(tmp_path, '{"a": 1, "b": ')
    with pytest.raises(ValueError):
        sf.update_runtime(lambda d: None, writer="t", on_corrupt=bad)


def test_策略表内容固定():
    assert CORRUPT_POLICIES == ("salvage", "refuse", "overwrite")


# ------------------------------------------------------------ L-16 锚点（本批的诚实边界）
def test_StateFile的坏不含业务结构_L16锚点(tmp_path):
    """**L-16 锚点**：`StateFile` 的「坏」只到「顶层是否 dict」，
    **不校验业务结构**（如 `threads` 必须为 list）⇒
    **接出口时 PA 侧业务判据必须保留**，否则会被静默放宽（`refuse` 也不会触发）。"""
    sf = _sf(tmp_path)
    # (a) 顶层非 dict ⇒ 算坏
    _write(tmp_path, "[1, 2, 3]")
    assert sf.read().corrupted is True
    # (b) 顶层 dict、但业务结构不符 ⇒ **不算坏**（这正是 L-16 的锚点）
    p = _write(tmp_path, json.dumps({"threads": "oops"}))
    rep = sf.read()
    assert rep.corrupted is False, "StateFile 不校验业务结构（L-16）"
    before = p.read_bytes()
    sf.update_runtime(lambda d: d.update({"x": 1}), writer="t", on_corrupt="refuse")
    assert p.read_bytes() != before, "业务结构不符 ⇒ refuse **不触发** ⇒ 照写（故 PA 侧判据必须自留）"
