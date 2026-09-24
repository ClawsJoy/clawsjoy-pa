# -*- coding: utf-8 -*-
"""L5 单测: 空参拦截(不进审批) + 预算 80% 预警"""
import sys
import re

sys.path.insert(0, ".")
import agent_gateway_enhanced as main
from core.gateway.shared_state import empty_arg_error as _empty_arg

_SRC = open(main.__file__, encoding="utf-8").read()

def _guard_block(src, name):
    """(a) 块定位: 按「函数签名 + 块首标记」取函数块 —— 不按行号、不按某行字面(承 DS 2026-09-23 前置 (a))"""
    m = re.search(r"^def " + re.escape(name) + r"\(", src, re.M)
    if not m:
        return ""
    nxt = re.search(r"^def ", src[m.end():], re.M)
    return src[m.start(): m.end() + (nxt.start() if nxt else len(src))]


def _a_ok(loop_src):
    """(a) 判据本体 —— 可对任意源跑(供负向对照): 块内见 token_stage(..., water_tok) 调用, 且不自算阈值"""
    _g = _guard_block(loop_src, "_token_water_guard")
    if not _g:
        return False
    if "from core.gateway.budget import token_stage" not in _g.replace('"', ""):
        return False
    if not re.search(r"token_stage\(\s*[^)]*\bwater_tok\b", _g):
        return False
    return not ("_warn80_tok" in _g or re.search(r"water_tok\s*\*", _g))


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
    """预算 80% 预警(不中断)+100% 收尾 —— (a) 接线面: 走单一来源 budget.token_stage  (b) 语义面: token_stage 返回值"""
    _LOOP = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    assert "_budget_warned80 = False" in _SRC  # 调用方初始化
    assert "[预算预警]" in _LOOP and "80%%" in _LOOP  # 行为文案仍在(不中断)
    assert "_token_water_hit = True" in _SRC  # 调用方消费 break
    # (a) 接线: 80% 判定必须走单一来源 budget.token_stage(⛔ 不再自算阈值 · 承 DS 拍板 (a))
    assert "from core.gateway.budget import token_stage" in _LOOP.replace('"', "")
    # 断言粒度 = 「签名/块首标记」+ 块内调用(不断「某一行字面」—— 承 DS 2026-09-23 前置 (a))
    assert _a_ok(_LOOP), "(a) 接线: _token_water_guard 块内须见 token_stage(..., water_tok) 且不自算阈值"
    assert _a_ok(_LOOP.replace("token_stage(tokens, water_tok)", "0")) is False  # 负向对照: 判据有齿
    # (b) 语义: token_stage 的返回值(单一判定面 · 承 DS 拍板 (b))
    from core.gateway.budget import token_stage, WARN_RATIO, CTX_COMPRESS_RATIO
    b = 1000
    assert (WARN_RATIO, CTX_COMPRESS_RATIO) == (0.8, 0.8)  # 同值不同源: 两个语义各自单源
    assert token_stage(int(b * WARN_RATIO) - 1, b) == "ok"
    assert token_stage(int(b * WARN_RATIO), b) == "warn80"
    assert token_stage(b, b) == "water"
    assert token_stage(b + 1, b) == "over"
    # 窗口侧语义: ⛔ 不得留裸 0.8 字面(单一来源 = CTX_COMPRESS_RATIO)
    # 面(承 初审_219 §三 · 面须写清): 窗口侧 = agent_gateway_enhanced.py + core/gateway/v9_chat/bridge_call.py
    # 面界(承 初审_220 低危 · 补等价式): 去空白后比字面 ⇒ 覆盖 *0.8 / * 0.8 / *0.80 / *4/5 / *80/100 / *(0.8);
    #   ⛔ 面外 = 经变量/别名绕开(如 _r=0.8; x*_r) 或跨行拆写 ⇒ 残余敞口如实留
    for _p in ("agent_gateway_enhanced.py", "core/gateway/v9_chat/bridge_call.py"):
        _s = open(_p, encoding="utf-8").read()
        assert "CTX_COMPRESS_RATIO" in _s, "窗口侧阈值须走常量: " + _p
        _n = re.sub(r"[ \t]+", "", _s)
        for _lit in ("*0.8", "*0.80", "*4/5", "*80/100", "*(0.8)"):
            assert _lit not in _n, "窗口侧 ⛔ 不得留裸 0.8 等价字面(" + _lit + "): " + _p
