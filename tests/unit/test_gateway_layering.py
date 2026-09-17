# -*- coding: utf-8 -*-
"""分层规则的可执行约束（2026-09-12，防「涨回来」）

三道防线，全部进回归套件：
  1. 主文件行数预算（薄壳，不内联业务）
  2. 路由归位（@app.route 不许在主文件）
  3. bridge_loop 行数预算（只做编排骨架，不内联业务）

P1/P2 完成后这些断言应全绿；在完成前用 skip 标记（避免打断当前回归）。
"""
import ast
import sys

sys.path.insert(0, ".")

import pytest

_MAIN = open("agent_gateway_enhanced.py", encoding="utf-8").read()
_MAIN_LINES = _MAIN.count("\n")


def _func_span(src, name):
    """①(2026-09-13) AST 取顶层函数的行范围。

    防回潮条1 首次兑现: 旧写法 seg.find("\ndef ", 10) 依赖"函数后面还有顶层 def" —
    _v9_bridge_loop 成为主文件最后一个顶层 def 后 find 返回 -1, 退化成"取到文件尾",
    断言从"测 bridge_loop 行数"变成"测文件剩余行数"(假绿)。
    """
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node.lineno, node.end_lineno
    raise AssertionError(f"未找到顶层函数: {name}")


def test_main_file_line_budget():
    assert _MAIN_LINES < 2000, "主文件 %d 行超预算——新功能归位 routes/core，不塞主文件" % _MAIN_LINES


def test_no_routes_in_main():
    assert "@app.route" not in _MAIN, "主文件仍有 @app.route，应迁到 routes/"


def test_bridge_loop_line_budget():
    _start, _end = _func_span(_MAIN, "_v9_bridge_loop")
    lines = _end - _start + 1
    assert lines < 500, "bridge_loop %d 行超预算——只做循环+调模块，业务归位" % lines


def test_routes_are_thin():
    import glob

    for f in glob.glob("routes/*.py"):
        if f.endswith("__init__.py"):
            continue
        n = open(f, encoding="utf-8").read().count("\n")
        assert n < 200, "%s %d 行超 200——路由应是薄适配器(解析请求→调core→jsonify)" % (f, n)
