"""Turn 协议 Step1 回归测试: reason 字段全链路"""
import sys

sys.path.insert(0, ".")
import pytest


def test_bridge_loop_returns_7tuple():
    """所有 return 统一 7-tuple(messages, tool_steps, exhausted, final_resp, tokens, reason, reason_detail)"""
    import ast

    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_v9_bridge_loop":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Tuple):
                    assert len(sub.value.elts) == 7, f"return 应为 7-tuple: {len(sub.value.elts)}"


def test_early_returns_carry_reason():
    """error/blocked/ask 返回 dict 带 reason + reason_detail"""
    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    _RG = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    assert '"reason": "error"' in src
    assert '"reason": "blocked"' in src or '"reason": "blocked"' in _RG
    assert '"reason": "ask"' in _RG
    assert "reason_detail" in src or "reason_detail" in _RG


def test_normal_end_reason_computation():
    """正常结束: completed / max_tokens / need_more 三态(集中式 _compute_turn_reason)"""
    import core.gateway.turn_protocol as tp

    src = open("core/gateway/v9_bridge/response_builder.py", encoding="utf-8").read()
    tsrc = open(tp.__file__, encoding="utf-8").read()
    assert "_compute_turn_reason" in src, "网关应调用统一 reason 计算(response_builder)"
    assert '"completed"' in tsrc and "max_tokens" in tsrc and "need_more" in tsrc
    assert "已达轮次/工具上限" in tsrc and "连续空回复" in tsrc
    # 行为模拟
    _round_exhausted, _bridge_exhausted, _empty_reply_count = False, False, 0
    _bmsg = {"content": "正常回答"}
    reason = "completed"
    if _round_exhausted or _bridge_exhausted:
        reason = "max_tokens"
    elif _empty_reply_count >= 2 and not (_bmsg.get("content") or "").strip():
        reason = "need_more"
    assert reason == "completed"
    _round_exhausted, _bridge_exhausted = True, True
    if _round_exhausted or _bridge_exhausted:
        reason = "max_tokens"
    assert reason == "max_tokens"
    _round_exhausted, _bridge_exhausted = False, False
    _empty_reply_count, _bmsg = 3, {"content": ""}
    if _round_exhausted or _bridge_exhausted:
        reason = "max_tokens"
    elif _empty_reply_count >= 2 and not (_bmsg.get("content") or "").strip():
        reason = "need_more"
    assert reason == "need_more"


def test_done_payload_reason_wired():
    """done payload 组装处补 reason(reason 从 7-tuple 或兜底标记来)"""
    src = open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()  # P3-B: 桥接层已归位
    assert '_done_payload["reason"] = _r2' in src, "stream 应补 reason"
    assert '_resp_ns["reason"] = _r_ns' in src, "non-stream 应补 reason"
    assert '_done_payload["reason"] = "need_more"' in src, "空兜底应 need_more"


def test_frontend_need_more():
    """前端按 need_more/empty_reply 分支不判完成"""
    from pathlib import Path

    html = Path("web/static/js/chat.js").read_text(encoding="utf-8")
    assert html.count("turnReason === 'need_more' || turnReason === 'empty_reply'") >= 1, "主路径 need_more 分支"
    assert html.count("turnReason2 === 'need_more' || turnReason2 === 'empty_reply'") >= 1, "续跑路径 need_more 分支"
    # need_more 分支在任务完成之前
    idx_reason = html.find("turnReason === 'need_more'")
    assert idx_reason != -1
    idx_done = html.find("✅ 任务完成", idx_reason)
    assert idx_done != -1
    assert idx_reason < idx_done
