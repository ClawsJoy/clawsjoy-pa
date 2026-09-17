"""断点1 路径认知回归: PROJECT_TREE 非空 + 含核心目录 + 有界"""
import sys

sys.path.insert(0, ".")
import pytest


def test_project_tree_non_empty_has_core_dirs():
    """断点1 修复: 项目树扫项目根(非空), Agent 能知道 core/config/data 在哪"""
    from core.lib.sandbox_tools import _generate_project_tree

    tree = _generate_project_tree("test_user", "test_sess")
    assert tree, "项目树不应为空(旧实现扫空沙箱 → len=0)"
    assert "core" in tree, f"应含 core 目录: {tree[:200]}"
    assert "config" in tree, f"应含 config 目录: {tree[:200]}"
    assert "data" in tree, f"应含 data 目录: {tree[:200]}"
    # 有界: 注入体积不失控(摘要模式)
    assert len(tree) < 4000, f"树应紧凑(≤4KB): {len(tree)}"


def test_project_tree_fast():
    """项目树生成应快(大项目摘要模式跳过逐文件 meta)"""
    import time

    from core.lib.sandbox_tools import _generate_project_tree

    t0 = time.time()
    _generate_project_tree("test_user", "test_sess")
    assert time.time() - t0 < 2.0, "项目树生成应 <2s(旧实现会全量读 .py 文件)"
