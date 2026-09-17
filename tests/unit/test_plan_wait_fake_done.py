# -*- coding: utf-8 -*-
"""2026-09-06: Agent 列计划不执行却完成 — 假完成第二层修复防回归。
1) 系统注入确认式规划指令 + agent 输出计划(无写入) → bridge 应转 plan_pending(blocked), 不 completed。
2) 用户显式要求直接落盘(完成条件=必须 write_draft) → 不应再注入「列计划等确认」。"""
import sys

sys.path.insert(0, ".")
import io

_GW = io.open("agent_gateway_enhanced.py", encoding="utf-8").read()


def test_plan_wait_gate_present():
    """bridge no-tool 收尾前应有 PLAN_WAIT 计划等待确认门（S6-C 归位 response_guard）"""
    _RG = io.open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    assert "[PLAN_WAIT] Agent 列出计划等待确认" in _RG
    assert '"status": "plan_pending"' in _RG
    assert '"reason": "blocked"' in _RG
    assert "计划等待老板确认" in _RG


def test_plan_wait_requires_sys_inject():
    """plan_pending 门只在系统注入过「询问用户确认后再执行」时触发(不误伤正常完成)"""
    _RG = io.open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    seg = _RG[_RG.index("_sys_injected_confirm") :]
    assert "_sys_injected_confirm = any(" in seg
    assert "询问用户确认后再执行" in seg


def test_plan_wait_uses_plan_message_detect():
    """只对计划结构文本(步骤+无✅)触发, 正常完成输出不含完成标记不误判"""
    _RG = io.open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    seg = _RG[_RG.index("_sys_injected_confirm = any(") :]
    assert "is_plan_message_fn" in seg


def test_direct_task_no_confirm_injection():
    """用户显式要求直接做(完成条件/必须 write_draft/实际落盘) → 注入逻辑跳过确认分支"""
    _REC = open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()  # P3-B: B 块已归位
    assert "_user_wants_direct" in _REC
    assert "完成条件" in _REC
    assert "必须 write_draft" in _REC
    # 直接做任务的新指令措辞: 列执行要点后直接执行, 不停在计划阶段
    assert "不要停在计划阶段等待确认" in _REC
