# -*- coding: utf-8 -*-
"""test_ast_patcher.py — ast_patcher.replace_function 的冒烟测试。

流程:
1. 在临时目录创建 dummy_target.py，内含 ``def old_func(): return 1``。
2. 调用 ``replace_function`` 将 old_func 替换为返回 2 的实现。
3. 重新执行替换后的文件，断言 old_func() == 2。
"""
from __future__ import annotations

import os
import sys
import tempfile

# 将项目根目录加入 sys.path，保证 from core.lib.ast_patcher import ... 可用
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.lib.ast_patcher import replace_function


def main() -> None:
    tmpdir = tempfile.mkdtemp(prefix="ast_patcher_test_")
    target = os.path.join(tmpdir, "dummy_target.py")

    # 1. 创建原始 dummy_target.py
    with open(target, "w", encoding="utf-8") as f:
        f.write("def old_func():\
    return 1\
")

    # 2. 调用 replace_function 替换
    ok, err = replace_function(target, "old_func", "def old_func():\
    return 2\
")
    if not ok:
        raise AssertionError(f"replace_function 失败: {err}")

    # 3. 读取替换后的文件并执行
    with open(target, "r", encoding="utf-8") as f:
        source = f.read()
    ns: dict = {}
    exec(compile(source, target, "exec"), ns)

    # 4. 断言执行结果
    result = ns["old_func"]()
    if result != 2:
        raise AssertionError(f"预期 old_func() == 2，实际 {result}")

    print("PASS: replace_function 替换成功，dummy_target.old_func() == 2")


if __name__ == "__main__":
    main()
