# -*- coding: utf-8 -*-
"""故障注入 · 输出被截断（finish_reason=length）。纪律：先能失败，再能通过。

背景（真实事故）：_v9_bridge_loop 里 line 572 用 _tg_estimate，而 line 590 又函数内
import 了它 → 函数级局部名遮蔽 → 长输出被 max_tokens 截断（finish_reason=length）时
抛 UnboundLocalError，整轮死掉；短任务永不触发，长交付必崩。
本测试盯住这个分支的源码契约，防止再退化。
"""
import ast
import sys

sys.path.insert(0, ".")


def _fn_src(path, name):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(src, node)
    return None


def test_FAULT_the_truncation_branch_still_exists():
    """① 先能失败：截断分支必须存在（否则本测试失去意义）。"""
    seg = _fn_src("agent_gateway_enhanced.py", "_v9_bridge_loop")
    assert seg
    assert "finish_reason" in seg and "length" in seg


def test_PASS_no_shadowing_in_main():
    """② 再能通过：主网关内不得再出现遮蔽 _tg_estimate/_calc_token_budget 的 import。"""
    from tests.unit.test_no_shadowing_imports import scan_file

    bad = [b for b in scan_file("agent_gateway_enhanced.py") if b[2] in ("_tg_estimate", "_calc_token_budget")]
    assert not bad, bad


def test_PASS_full_repo_has_no_shadowing():
    """全仓守卫。"""
    from tests.unit.test_no_shadowing_imports import _iter_py_files, scan_file

    offenders = []
    for p in _iter_py_files():
        try:
            offenders.extend(scan_file(p))
        except SyntaxError:
            continue
    assert not offenders, offenders
