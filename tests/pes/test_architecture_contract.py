# -*- coding: utf-8 -*-
"""架构契约测试：五层 + 三层外围 + 三条术语修正（总任务书工程版 v1）。

这些断言的价值：把「文档说了什么」变成「代码里必须成立什么」——
日后任何一层被删掉/改名、或 Audit 被拿掉，这里立刻红。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.pes import (
    ARCH_NAME,
    ARCH_SHORT,
    CORE_LAYERS,
    EDGE_LAYERS,
    OWNERSHIP_TIERS,
    __version__,
)

PES_DIR = Path(__file__).resolve().parents[2] / "core" / "pes"

LAYER_MODULES = {
    "State Integrity": "state_integrity",
    "Execution Contract": "contract",
    "Capability Registry": "capability_registry",
    "Audit": "audit",
    "Memory": "memory",
}


def test_架构名与术语修正一():
    """术语修正 ①：正式写法是 V9-PES，不用裸「PES」缩写。"""
    assert ARCH_NAME == "V9 Personal Execution System"
    assert ARCH_SHORT == "V9-PES"
    assert isinstance(__version__, str) and __version__


def test_五层固定且必须有_Audit():
    """术语修正 ③：五层里必须有 Audit。"""
    assert CORE_LAYERS == (
        "State Integrity",
        "Execution Contract",
        "Capability Registry",
        "Audit",
        "Memory",
    )
    assert "Audit" in CORE_LAYERS


def test_三层外围与状态所有权三层():
    assert EDGE_LAYERS == ("UI", "Agent", "Storage")
    assert OWNERSHIP_TIERS == ("execution", "summary", "context_source")


@pytest.mark.parametrize("layer,mod", sorted(LAYER_MODULES.items()))
def test_每层模块可导入且有文档(layer, mod):
    m = __import__("core.pes.%s" % mod, fromlist=["__doc__"])
    assert m.__doc__ and len(m.__doc__.strip()) > 30, "层 %s 缺模块文档" % layer


@pytest.mark.parametrize("name", sorted(p.name for p in PES_DIR.glob("*.py")))
def test_模块级不依赖_fcntl(name):
    """Windows 化硬约束：``fcntl`` 只能在使用点 try-import，**不得**模块级 import。"""
    tree = ast.parse((PES_DIR / name).read_text(encoding="utf-8"))
    top: list = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            top.append(node.module or "")
    assert not any(n == "fcntl" or n.startswith("fcntl.") for n in top), "%s 在模块级 import fcntl" % name


def test_contract_在既有_P0_负三_上补字段():
    """术语修正 ②：**不新造第二套契约** —— 新契约必须仍带既有 P0-负三 的字段。"""
    from core.pes import contract as ct

    c = ct.new_contract("t-1", objective="目标", nodes=[{"id": "n1"}])
    assert c["task_id"] == "t-1"
    for k in ("task_id", "objective", "phase", "nodes", "active_node", "evidence", "budget"):
        assert k in c, "丢失既有 P0-负三 字段：%s" % k
    for k in ct.CONTRACT_DEFAULTS:
        assert k in c, "缺 M1/M2 补充字段：%s" % k


def test_M1_四条判据都有机械抓手():
    """M1「状态可信」四条判据在代码里各有一个可调用件（不靠人读日志）。"""
    from core.pes import state_integrity as si

    assert callable(si.detect_uninstrumented)          # ① 无未插桩写者
    assert callable(si.StateFile.read)                 # ② 坏状态不抛异
    assert callable(si.StateFile.recover)              # ② 可自助恢复
    assert si.DEFAULT_SEED_KEYS and callable(si.StateFile.set_seed)  # ③ seed/runtime 分离
    assert "degradations" in si.StateReport("x").as_dict()          # ④ 无静默降级
