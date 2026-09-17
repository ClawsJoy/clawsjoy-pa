# -*- coding: utf-8 -*-
"""H1 审核修复: _v9_bridge_loop 内部初始化 + 参数化（源码断言）

S7(2026-09-12): 初始化归位 core/gateway/v9_bridge/loop.py::_init_bridge_state,
桥接循环改为从返回 dict 解包; 本测试同步改断言目标。
"""
import ast
import sys

sys.path.insert(0, ".")
import pytest


def _func_source(src, name):
    """①(2026-09-13) 抗重构: 用 AST 取顶层函数源码。

    旧写法 `src.find(chr(10) + "def ", idx + 10)` 依赖"函数后面还有别的顶层 def" —
    _v9_bridge_loop 成为主文件最后一个顶层 def 后 find 返回 -1, 回退 idx+2000 硬窗口,
    而 `def _ts_progress` 在 +2530 处 → 假失败(产品其实完好)。
    """
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(src, node) or ""
    raise AssertionError(f"未找到顶层函数: {name}")


def test_bridge_loop_has_init():
    """桥接循环解包 _init_bridge_state + 定义 _ts_progress + 参数化缺失变量"""
    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    fn = _func_source(src, "_v9_bridge_loop")  # ①: AST 精确边界, 不依赖后续 def 存在
    # S7: 初始化归位 loop.py, 桥接循环解包
    assert "from core.gateway.v9_bridge.loop import _init_bridge_state" in fn, "缺 _init_bridge_state import"
    assert 'tokens = _st["tokens"]' in fn, "缺 tokens 解包"
    assert '_tool_steps = _st["_tool_steps"]' in fn, "缺 _tool_steps 解包"
    assert '_bridge_exhausted = _st["_bridge_exhausted"]' in fn, "缺 _bridge_exhausted 解包"
    assert '_task_start_ts = _st["_task_start_ts"]' in fn, "缺 _task_start_ts 解包(审计复核用)"
    assert "def _ts_progress" in fn, "缺 _ts_progress 定义"
    assert "from core.gateway.tool_router import _execute_sandbox_tool as _exec_tool_94" in fn, "缺 _exec_tool_94 import"
    # 参数化（model/plan_status/current_plan）
    assert "model=None" in fn, "缺 model 参数"
    assert "plan_status=None" in fn, "缺 plan_status 参数"
    assert "current_plan=None" in fn, "缺 current_plan 参数"
    # 6 个退出点都是元组返回（return 改写模式）
    import re

    bad_returns = re.findall(r"return jsonify", fn)
    assert not bad_returns, f"函数内仍有 return jsonify: {bad_returns}"
    # 元组返回至少 2 个(循环内 error/7B fail); post-loop 尾段已归位 response_builder
    tuple_returns = fn.count("return (messages, _tool_steps")
    assert tuple_returns >= 2, f"循环内元组返回应>=2, 实际 {tuple_returns}"
    # post-loop 尾段归位 response_builder: 其最终返回也是 7 元组(不 jsonify)
    _rb = open("core/gateway/v9_bridge/response_builder.py", encoding="utf-8").read()
    assert "return (messages, tool_steps, bridge_exhausted, None, tokens, _turn_reason, _turn_reason_detail)" in _rb
    assert "return (_pause_msgs, tool_steps, True, {" in _rb
    # S7: 初始化本体在 loop.py::_init_bridge_state
    loop_src = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    assert "tokens = 0" in loop_src, "loop.py 缺 tokens 初始化"
    assert "_tool_steps = []" in loop_src, "loop.py 缺 _tool_steps 初始化"
    assert "_bridge_exhausted = True" in loop_src, "loop.py 缺 _bridge_exhausted 初始化"
    assert "_task_start_ts = " in loop_src, "loop.py 缺 _task_start_ts 初始化"


def test_callsite_passes_params():
    """调用点传 model/plan_status/current_plan"""
    src = open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()  # P3-B: 桥接层已归位
    idx = src.find("_loop_out = bridge_loop_fn(")
    call = src[idx : idx + 200]
    assert "model" in call and "plan_status" in call and "current_plan" in call, "调用点缺参数"
    assert "_final_resp is not None" in src[src.find("_loop_out =") : src.find("_loop_out =") + 400], "缺提前退出判断"
