"""derive_messages 重建后 tool_calls assistant 必须带 reasoning_content 回归测试

用户实测: 上下文过大压缩后 → 400 "The reasoning_content in the thinking mode must be passed back to the API."
机制: 事件 payload 存 reasoning_content=None(旧事件/API未返回) → derive_messages 重建时
if payload.get("reasoning_content") 为 False → 字段缺失 → 带 tool_calls 的 assistant 无
reasoning_content → DeepSeek 400。
"""
import sys
import tempfile

sys.path.insert(0, ".")
from pathlib import Path

import pytest

from core.gateway.message_assembler import _finalize_messages
from core.gateway.session_log import SessionLog


def _mk_log(tmp, rc_value=None, with_rc_field=True):
    log = SessionLog("s_rebuild", base_dir=Path(tmp))
    log.append("user_message", {"role": "user", "content": "任务"})
    _pl = {
        "content": "",
        "tool_calls": [
            {"id": "t1", "type": "function", "function": {"name": "read_file", "arguments": '{"path":"a.py"}'}}
        ],
    }
    if with_rc_field:
        _pl["reasoning_content"] = rc_value
    log.append("assistant_message", _pl)
    log.append("tool_result", {"name": "read_file", "call_id": "t1", "content": "结果", "success": True})
    return log


def test_derive_rebuild_has_reasoning_for_tool_calls(tmp_path):
    """事件 payload reasoning=None → derive 重建后 tool_calls assistant 带空字符串 reasoning"""
    log = _mk_log(str(tmp_path), rc_value=None)
    msgs = log.derive_messages()
    asst = [m for m in msgs if m.get("role") == "assistant" and m.get("tool_calls")]
    assert asst, "应有 tool_calls assistant"
    assert "reasoning_content" in asst[0], "derive 重建后应带 reasoning_content 字段"
    assert asst[0]["reasoning_content"] == "", "应为空字符串(实测 DeepSeek 合法)"


def test_derive_rebuild_missing_field_also_fixed(tmp_path):
    """事件 payload 完全无 reasoning_content 字段 → derive 重建仍补空字符串"""
    log = _mk_log(str(tmp_path), with_rc_field=False)
    msgs = log.derive_messages()
    asst = [m for m in msgs if m.get("role") == "assistant" and m.get("tool_calls")]
    assert asst and asst[0].get("reasoning_content") == ""


def test_derive_rebuild_preserves_real_reasoning(tmp_path):
    """事件有真实 reasoning → derive 保留原文"""
    log = _mk_log(str(tmp_path), rc_value="真实思考过程")
    msgs = log.derive_messages()
    asst = [m for m in msgs if m.get("role") == "assistant" and m.get("tool_calls")]
    assert asst[0]["reasoning_content"] == "真实思考过程"


def test_derive_finalize_chain_produces_api_safe(tmp_path):
    """derive 重建 → finalize(唯一出口) → 结构对 DeepSeek 安全"""
    log = _mk_log(str(tmp_path), rc_value=None)
    msgs = _finalize_messages(log.derive_messages())
    asst = [m for m in msgs if m.get("role") == "assistant" and m.get("tool_calls")]
    assert asst and isinstance(asst[0].get("reasoning_content"), str)
    assert asst[0]["tool_calls"][0].get("type") == "function"
    # tool 配对完整
    ids = {tc.get("id") for m in asst for tc in m.get("tool_calls", [])}
    for m in msgs:
        if m.get("role") == "tool":
            assert m.get("tool_call_id") in ids


def test_source_bridge_loop_finalize_after_derive():
    """源码: bridge_loop 每轮 derive 重建后应过 _finalize_messages"""
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    # R5(2026-08-31): bridge 每轮 derive 启用 last_task_only=True(任务隔离)
    seg = src[src.index("messages = get_session_log(session_id).derive_messages(last_task_only=True)") :]
    assert "_finalize_messages(messages)" in seg, "derive 重建后应 finalize"
