# -*- coding: utf-8 -*-
"""`scan_state_dir` 的**判据范围收敛**（PA store 白名单）—— `X-16` 批 D · `D1`（DS 2026-09-18 拍做）。

口径来源：方案稿 §十二 `D1` —— 判据只问「**必须走出口**的那些 store 有没有走」。
把「不必走出口」的东西（契约快照 `contracts/*.json`、`pa/artifacts/` 等**产物派生**、审计探针
残留）一并算红 ⇒ 判据**恒不可能为 0** ⇒ 退化成噪声后被无视（＝判据失效）。

判据：
 ① 默认（`scope="pa"`）只收 白名单 ∩ `pa/` 直下 ⇒ **白名单外文件增减不影响结果**；
 ② `scope="all"` = 旧全域口径（显式 opt-in）⇒ 白名单外**会被**计入（**对照**，证明过滤真在起作用）；
 ③ 非法 `scope` ⇒ `ValueError`（**不静默回落**，同 `update_runtime(on_corrupt=...)` 口径）；
 ④ 默认值与白名单内容**被 pin 住**（改默认／改白名单**必须显式改判据**）。

注：`tests/pes/` 其他扫描用例（`test_state_integrity.py::test_scan_state_dir_*`、
`test_run_registry.py::test_汇总态记账本身走唯一出口`、`test_state_integrity_reason_kind.py` 的 ④/⑥）
判的是**机制**（逐文件的 `detect_uninstrumented` 语义），不是**范围** ⇒ 它们显式传 `scope="all"`。
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from core.pes.state_integrity import (
    PA_STORE_DIRNAME,
    PA_STORE_WHITELIST,
    scan_state_dir,
)


def _tree(tmp_path):
    """造一棵 `data/v9` 同形树：**白名单内 2 件** + **白名单外 3 件**。"""
    pa = tmp_path / "pa"
    (pa / "artifacts").mkdir(parents=True)
    (tmp_path / "contracts").mkdir()
    (pa / "ledger.json").write_text('{"items": []}', encoding="utf-8")             # 白名单内
    (pa / "threads_u1.json").write_text('{"threads": []}', encoding="utf-8")       # 白名单内
    (pa / "other.json").write_text('{"x": 1}', encoding="utf-8")                   # `pa/` 下但不在白名单
    (pa / "artifacts" / "derived.json").write_text('{"x": 1}', encoding="utf-8")   # 产物派生
    # 产物派生 **同名**（名字在白名单里，但不在 `pa/` 直下）⇒ 用来钉住「**直下**」这一条
    (pa / "artifacts" / "ledger.json").write_text('{"items": []}', encoding="utf-8")
    (tmp_path / "contracts" / "t1.json").write_text('{"x": 1}', encoding="utf-8")  # 契约快照
    return tmp_path


def _rel(rows, root):
    """相对路径（posix）—— 用路径而非文件名：本树里有**同名**的 `artifacts/ledger.json`。"""
    return sorted(Path(r["path"]).relative_to(Path(root)).as_posix() for r in rows)


def test_默认范围只收白名单内的_pa_store(tmp_path):
    """① 白名单外（`other.json`／`artifacts/*`／`contracts/t1.json`）**不计入**；

    含 **`pa/artifacts/ledger.json`**（**同名**但在产物派生目录）⇒ 钉住「**直下**」这一条。
    """
    root = _tree(tmp_path)
    assert _rel(scan_state_dir(root), root) == ["pa/ledger.json", "pa/threads_u1.json"]


def test_白名单外文件增减不影响结果(tmp_path):
    """① 再加 3 件「不必走出口」的东西 ⇒ 结果**一个都不变**（范围外不参与判规）。"""
    root = _tree(tmp_path)
    before = _rel(scan_state_dir(root), root)
    (root / "pa" / "yet_another.json").write_text('{"x": 1}', encoding="utf-8")
    (root / "contracts" / "t2.json").write_text('{"x": 1}', encoding="utf-8")
    (root / "pa" / "artifacts" / "more.json").write_text('{"x": 1}', encoding="utf-8")
    assert _rel(scan_state_dir(root), root) == before


def test_scope_all_是旧全域口径的显式_opt_in(tmp_path):
    """② **对照**：`scope="all"` 必须**会**计入白名单外的 3 件 ⇒ 证明过滤真在起作用（非空转）。"""
    root = _tree(tmp_path)
    assert _rel(scan_state_dir(root, scope="all"), root) == [
        "contracts/t1.json",
        "pa/artifacts/derived.json",
        "pa/artifacts/ledger.json",
        "pa/ledger.json",
        "pa/other.json",
        "pa/threads_u1.json",
    ]


def test_非法_scope_抛_ValueError(tmp_path):
    """③ 非法值**不静默回落默认值**（只差一个空格也必须抛，不得被当成 `"pa"`）。"""
    root = _tree(tmp_path)
    with pytest.raises(ValueError):
        scan_state_dir(root, scope="pa ")
    with pytest.raises(ValueError):
        scan_state_dir(root, scope="ALL")


def test_默认_scope_与白名单内容被钉住():
    """④ 改默认值／改白名单 = 改判据范围 ⇒ **必须显式改本用例**（防「悄悄放宽」）。"""
    assert inspect.signature(scan_state_dir).parameters["scope"].default == "pa"
    assert PA_STORE_DIRNAME == "pa"
    assert PA_STORE_WHITELIST == (
        "threads_*.json",
        "ledger.json",
        "profile.json",
        "roster.json",
        "permission.json",
        "decision*.json",
    )