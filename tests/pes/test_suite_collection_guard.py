# -*- coding: utf-8 -*-
r"""套件级守卫：**测试模块 basename 不得重名**。

背景（本仓库本轮实测踩到）：`tests/` 下各目录**没有 `__init__.py`**，
pytest 以「文件 basename」作模块名导入。两个不同目录下的同名文件会互相顶掉：

    ERROR tests/unit/test_x.py
    import file mismatch: imported module 'test_x' has this __file__ attribute:
      D:\...\tests\pes\test_x.py

后果**不是"少跑几条"，而是整个套件中断收集**（`Interrupted: 2 errors during collection`）：
门禁解析到的失败数变成 0，反而被读成"台账里登记的失败都好了"。
**这是最坏的一种红：它把"根本没跑"伪装成"全绿"。**

所以把这条钉成用例 —— 这条用例住在 `tests/pes/`，但守卫的是**整个套件**。
"""

from __future__ import annotations

import collections
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parents[1]


def test_测试模块_basename_全仓唯一():
    files = sorted(TESTS_DIR.rglob("test_*.py"))
    assert files, "一条用例文件都没扫到 ⇒ 路径解析错了（守卫本身失效）"
    counter = collections.Counter(p.name for p in files)
    dupes = {
        name: [p.as_posix() for p in files if p.name == name]
        for name, count in counter.items()
        if count > 1
    }
    assert dupes == {}, (
        "测试模块 basename 重名会让**整个套件中断收集**"
        "（无 __init__.py，pytest 按 basename 导入 ⇒ import file mismatch）。请改名。重名清单：%s" % dupes
    )


def test_守卫确实扫到了_pes_自己的用例():
    """自证：守卫扫的目录必须包含本目录，否则它守着的是空集。"""
    names = {p.name for p in TESTS_DIR.rglob("test_*.py")}
    assert "test_architecture_contract.py" in names
    assert "test_audit_layer.py" in names
