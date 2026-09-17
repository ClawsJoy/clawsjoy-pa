# -*- coding: utf-8 -*-
"""审核 bug 修复回归: #4 Retry-After / #6 docstring / #7 tool加回检查 / #12 快照深拷贝"""
import sys

sys.path.insert(0, ".")
import pytest


def test_b4_retry_after():
    """#4: 429 读 Retry-After header"""
    src = open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()
    assert "Retry-After" in src, "缺 Retry-After 读取"
    assert 'resp.headers.get("Retry-After"' in src, "缺 header 读取"
    assert "min(int(_ra), 30)" in src, "缺 Retry-After 上限"


def test_b6_docstring_clean():
    """#6: docstring 不嵌代码注释"""
    src = open("routes/audit.py", encoding="utf-8").read()
    # #15 注释应在 docstring 外
    idx = src.find("def v9_audit_approvals")
    block = src[idx : idx + 350]
    assert '"""' in block, "docstring 应存在"
    # docstring 闭合后才是 #15 注释
    import re

    m = re.search(r'""".*?"""', block, re.S)
    assert m, "docstring 未闭合"
    after = block[m.end() :]
    assert "#15 P0" in after, "#15 注释应在 docstring 外"


def test_b7_tool_addback_check():
    """#7: tool 加回前检查超限"""
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "_est_with_tool" in src, "缺 tool 加回估算"
    assert "跳过加回" in src, "缺跳过逻辑"


def test_b12_snapshot_deepcopy():
    """#12: 快照 tool_calls 深拷贝"""
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "tool_calls=[dict(tc) for tc in" in src, "缺 tool_calls 深拷贝"
