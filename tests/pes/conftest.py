# -*- coding: utf-8 -*-
"""``tests/pes`` 的测试隔离。

两条硬要求：

1. **绝不写仓库 ``data/v9/``** —— PES 各层的默认路径都指向真实仓库目录；
   autouse fixture 把**审计流**换成 tmp 下的实例，其余 store 由用例显式传 ``tmp_path``；
2. 隔离的是**审计流**（与执行态分文件的独立流，总任务书 §3.1），
   而不是把测试和被测逻辑一起改掉。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_pes_audit(tmp_path, monkeypatch):
    """把进程内审计流指向 tmp —— 用例产生的授权/状态审计不落仓库。"""
    from core.pes import audit as audit_mod

    log = audit_mod.AuditLog(tmp_path / "isolated-audit.jsonl")
    monkeypatch.setattr(audit_mod, "_log", log, raising=False)
    return log


@pytest.fixture()
def pes_dir(tmp_path):
    """一份干净的 PES 工作目录（状态文件 / 账本都落这里）。"""
    d = tmp_path / "pes"
    d.mkdir(parents=True, exist_ok=True)
    return d
