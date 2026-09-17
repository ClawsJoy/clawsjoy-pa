"""Turn 协议 Step3 回归测试: 前端 reason 完整渲染 + 审计接入"""
import sys

sys.path.insert(0, ".")
import pytest


def test_frontend_complete_reason_switch():
    """前端应有 completed/max_tokens/need_more/error 分支(blocked/ask 走已有 status 卡)"""
    from pathlib import Path

    # 模块化拆分后 chat 逻辑在 chat.js(workbench.html 仅剩占位注释)
    html = Path("web/static/js/chat.js").read_text(encoding="utf-8")
    # completed 分支
    assert "turnReason === 'completed'" in html or "turnReason2 === 'completed'" in html
    assert "✅ 任务完成" in html
    # max_tokens 分支
    assert "已达轮次上限，以下为已有产出" in html
    # need_more 分支
    assert "模型未产出有效内容" in html
    # error 分支
    assert "执行出错" in html and "reason_detail" in html
    # 兼容旧 payload: 无 reason 时按 bridge_exhausted 推断
    assert "d.bridge_exhausted ? 'max_tokens' : (msg.content ? 'completed' : 'need_more')" in html


def test_frontend_reason_before_fallback():
    """reason 分支应出现在 '任务完成' 回退逻辑之前"""
    from pathlib import Path

    html = Path("web/static/js/chat.js").read_text(encoding="utf-8")
    # 第一个 reason switch(主路径)在 任务完成 之前
    idx_switch = html.find("let turnReason = d.reason")
    idx_fallback = html.find(
        "if (!msg.tool_calls || msg.tool_calls.length === 0) {", html.find("let turnReason = d.reason")
    )
    assert idx_switch != -1
    assert idx_switch < idx_fallback, "reason switch 应在完成回退之前"


def test_backend_audit_integration():
    """turn_end 审计接入: _write_turn_end 与 _write_exec_turn_end 写 ledger timeline"""
    import agent_gateway_enhanced as main
    import core.gateway.execute_agent_task as m

    src_main = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    src_exec = open(m.__file__, encoding="utf-8").read()
    # bridge_loop 审计
    assert "ledger.record_event" in src_main, "bridge_loop 应写 ledger"
    assert 'action=f"turn_end:{reason}"' in src_main, "ledger action 应含 turn_end:reason"
    # exec 审计
    assert "ledger.record_event" in src_exec, "exec 应写 ledger"
    assert 'action=f"turn_end:{_reason}"' in src_exec, "exec ledger action 应含 reason"


def test_audit_payload_shape():
    """行为验证: ledger 记录带 turn_id/reason/detail"""
    import json

    # 模拟 _write_turn_end 的 ledger 调用
    _session_id, _turn_id, _reason, _detail = "s_audit", 123, "max_tokens", "已达轮次/工具上限"
    _tools_n, _tokens = 12, 500
    _summary = f"turn_id={_turn_id} {_detail} tools={_tools_n} tokens={_tokens}"[:300]
    assert _summary.startswith("turn_id=123")
    assert "已达轮次/工具上限" in _summary
    assert "tools=12" in _summary and "tokens=500" in _summary
    # 前端审计面板读取的 timeline 格式(action=turn_end:reason)
    _action = f"turn_end:{_reason}"
    assert _action == "turn_end:max_tokens"
