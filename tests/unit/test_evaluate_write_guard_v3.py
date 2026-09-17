"""evaluate 写保护加强测试: eval/new Function 绕过载体拦截 + 尾换行"""
import sys

sys.path.insert(0, ".")
import pytest


def test_eval_bypass_marker_in_guard():
    """写保护含 eval/new Function 绕过载体检测"""
    _SRC = open("core/tools/browser_local.py", encoding="utf-8").read()
    assert "_bypass_markers" in _SRC, "应有绕过载体标记"
    assert '"eval("' in _SRC or "eval(" in _SRC, "应检测 eval"
    assert '"new function("' in _SRC or "new function(" in _SRC, "应检测 new Function"


def test_trailing_newline():
    """文件应以换行结尾"""
    txt = open("core/tools/browser_local.py", encoding="utf-8").read()
    assert txt.endswith("\n"), "文件尾应有换行"
