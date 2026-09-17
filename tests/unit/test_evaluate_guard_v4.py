"""evaluate 写保护精细化测试: function( 仅当含写操作时拦截(不误伤只读函数探针)"""
import sys

sys.path.insert(0, ".")
import pytest


def test_function_readonly_probe_allowed():
    """纯函数探针 function(){return document.title} 不应被拦(无写操作)"""
    _SRC = open("core/tools/browser_local.py", encoding="utf-8").read()
    assert '_has_fn_write = "function(" in _expr_low and _has_write' in _SRC, "function( 应条件拦截(仅含写操作时)"
    assert "_has_write = any" in _SRC, "应有写操作标记检测"


def test_function_with_write_blocked():
    """函数体内含 click/submit → 拦截(绕过载体)"""
    _SRC = open("core/tools/browser_local.py", encoding="utf-8").read()
    # 逻辑: _has_fn_write = function( in expr AND _has_write → 拦
    assert "function(" in _SRC and "_has_write" in _SRC.split("_has_fn_write")[1], "函数+写操作应拦"


def test_eval_still_blocked_unconditionally():
    """eval( 仍无条件拦截"""
    _SRC = open("core/tools/browser_local.py", encoding="utf-8").read()
    assert '("eval(", "new function(", "settimeout(", "setinterval(")' in _SRC, "绕过载体仍无条件拦"
