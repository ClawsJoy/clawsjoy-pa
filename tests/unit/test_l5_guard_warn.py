# -*- coding: utf-8 -*-
"""L5 单测: 空参拦截(不进审批) + 预算 80% 预警"""
import sys

sys.path.insert(0, ".")
import agent_gateway_enhanced as main
from core.gateway.shared_state import empty_arg_error as _empty_arg

_SRC = open(main.__file__, encoding="utf-8").read()


def test_empty_arg_helper():
    assert _empty_arg("write_file", {}) != ""
    assert _empty_arg("write_file", {"path": "  "}) != ""
    assert _empty_arg("write_file", {"path": "data/tmp/x.py"}) == ""
    assert _empty_arg("execute_command", {}) != ""
    assert _empty_arg("read_file", {"path": "x"}) == ""
    assert _empty_arg("list_dir", {}) == ""  # 不在必填清单
    # (2026-09-05) action 类工具空参拦截(封面任务 obsidian_knowledge() 空参循环)
    assert _empty_arg("obsidian_knowledge", {}) != ""
    assert _empty_arg("obsidian_knowledge", {"action": "read", "sop_key": "x"}) == ""
    assert _empty_arg("browser_hybrid", {}) != ""
    assert _empty_arg("cu_learning", {"action": "start"}) == ""
    assert _empty_arg("playwright_browser", {}) != ""


def test_empty_arg_single_source():
    """S3: 空参逻辑单点 — shared_state.empty_arg_error 唯一实现; 桥接与守卫只调用"""
    ss = open("core/gateway/shared_state.py", encoding="utf-8").read()
    assert "def empty_arg_error" in ss and "_EMPTY_REQUIRED" in ss
    reg = open("core/gateway/guards/registry.py", encoding="utf-8").read()
    assert "from core.gateway.shared_state import empty_arg_error" in reg, "守卫应调用共享实现"
    gw = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "from core.gateway.shared_state import empty_arg_error as _v9_empty_arg_error" in gw, "桥接应调用共享实现"


def test_empty_arg_intercept_wired_before_guards():
    """空参工具调用 → param_error deny 收集, 走不到审批(guard 前拦截)"""
    gw = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "空参单点(shared_state.empty_arg_error)" in gw or "空参拦截" in gw
    assert "_v9_empty_arg_error(_bfn, _bargs)" in gw.replace('"', "")
    i_err = gw.index("_l5e = _v9_empty_arg_error")
    i_guard = gw.index("_gdeny = run_pre_guards")
    assert i_err < i_guard, "空参拦截应先于审批守卫"


def test_empty_arg_repeat_steer_wired():
    """(2026-09-05) 空参连续 ≥2 次注入格式引导, 打断 arg 生成故障循环"""
    gw = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "_ea_seen = {}" in _SRC or "ea_seen" in gw
    assert "连续以空参数/缺必填参数调用" in gw, "应有引导文案"
    assert "obsidian_knowledge 需 action=" in gw, "引导应含 obsidian 示例"
    assert "_ea_cnt == 2" in gw, "连续 2 次即引导"


def test_budget_warn80_wired():
    """预算 80% 时注入收敛预警(不中断); 100% 才正常收尾（S6-E 归位 loop.py _token_water_guard）"""
    _LOOP = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    assert "_budget_warned80 = False" in _SRC  # 调用方初始化
    assert "[预算预警]" in _LOOP and "80%%" in _LOOP
    assert "_warn80_tok = int(water_tok * _wr_s5)" in _LOOP
    assert "_token_water_hit = True" in _SRC  # 调用方消费 break
    assert _LOOP.index("_warn80_tok = int") < _LOOP.index("if tokens >= water_tok:")
