# -*- coding: utf-8 -*-
"""死模块双扫描：自检 + 盲区回归（2026-09-13）。

**本文件的价值在自检那一条** —— 2026-09-13 的教训：
扫描器有**设计盲区**（只认裸模块名，漏 from core.lib.X import 与 X.get_stats()），
导致批量归档时 **10 个里 6 个其实在用**。若扫描器失效而测试永真，这个错误会一路带到生产。

所以：**删除类工具必须对「已知有引用的样本」断言非 0**。
"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tools")
from dead_module_scan import scan

# 2026-09-13 批量归档因扫描器盲区**已全部回滚**，故此处为空 —— 留空是**事实**，不是占位。
ARCHIVED_CLEAN = []


def test_FAULT_scanner_is_not_a_noop():
    """① 先能失败（自检）：对**已知有引用**的模块必须返回非 0。

    这条挂了就说明扫描器失效 —— 那「0 引用」的结论全部不可信（本批真实发生过）。
    """
    r = scan("json", "core")
    assert sum(len(v) for v in r.values()) > 0, "扫描器对已知有引用的模块返回 0 → 扫描器失效"


def test_PASS_scanner_detects_dotted_import():
    """② 再能通过（盲区回归）：点号路径 import 必须被识别 —— 正是导致 6/10 误归档的盲区。"""
    r = scan("route_vectorizer", "core")
    assert sum(len(v) for v in r.values()) > 0, "点号路径 import 未被识别（盲区回归）"


def test_PASS_scanner_detects_attribute_access():
    """属性访问（X.get_stats(...)）也要算引用 —— 它没有 import 行。"""
    r = scan("route_vectorizer", "core")
    assert "属性访问" in " ".join(sum(r.values(), [])), r


def test_archived_clean_list_is_actually_clean():
    """归档清单里每个模块都必须真的 0 引用（清单为空时平凡通过 —— 见文件头说明）。"""
    bad = {}
    for name in ARCHIVED_CLEAN:
        r = scan(name, "core")
        if sum(len(v) for v in r.values()) > 0:
            bad[name] = {k: v[:2] for k, v in r.items() if v}
    assert not bad, "归档后仍有引用：%s" % bad
