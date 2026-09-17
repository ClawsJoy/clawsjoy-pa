"""max_tokens 空产出修复回归测试

问题: 达到轮次/工具上限时最后 assistant content 为空, 前端显示"以下为已有产出"但产出为空。
修复:
1. content 为空 → 基于 tool_steps 提取摘要(不调 LLM): "已完成 N 个工具调用，成功 M 个。关键发现：{...}"
2. tool_steps 也为空 → reason 降级 error, detail="无工具产出，任务未完成"
3. 前端 max_tokens 分支 content 为空 → 显示摘要而非"已有产出"
"""
import sys

sys.path.insert(0, ".")
import pytest

_SRC = open("agent_gateway_enhanced.py", encoding="utf-8").read()
_CHAT = open("web/static/js/chat.js", encoding="utf-8").read()


def test_backend_summary_helper_exists():
    """_build_tool_steps_summary 应存在且从 tool_steps 提取(不调 LLM) — 已归位 response_helpers"""
    _RH = open("core/gateway/v9_bridge/response_helpers.py", encoding="utf-8").read()
    assert "def _build_tool_steps_summary(tool_steps, limit=160):" in _RH, "缺摘要助手"
    assert "已完成 {len(tool_steps)} 个工具调用，成功 {len(_ok)} 个。" in _RH, "缺 N/M 计数格式"
    assert "关键发现：" in _RH, "缺关键发现格式"
    assert '_last.get("result")' in _RH, "应从最后成功步骤的 result 提取"


def test_backend_tool_steps_carry_result():
    """tool_steps 条目应携带 result 摘要(供摘要提取)（D3 归位 tool_runner）"""
    _TR = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert '"result": _step_result' in _TR, "tool_steps 缺 result 字段"


def test_backend_empty_content_uses_summary():
    """content 为空且 tool_steps 非空 → 摘要注入最终 content — 已归位 response_builder"""
    _RB = open("core/gateway/v9_bridge/response_builder.py", encoding="utf-8").read()
    assert '_final_empty = not str(_bmsg_final.get("content") or "").strip()' in _RB
    assert "if _final_empty and tool_steps:" in _RB
    assert "_step_summary = build_tool_steps_summary_fn(tool_steps)" in _RB
    # 注入到 messages 最后 assistant + _bmsg_final
    assert '_new_content = (_step_summary or str(_bmsg_final.get("content") or "")) + _round_msg' in _RB


def test_backend_no_output_degrades_reason():
    """content 与 tool_steps 皆空 → reason=error, detail=无工具产出(集中式 _compute_turn_reason) — 已归位 response_builder"""
    import core.gateway.turn_protocol as _tp

    _TP = open(_tp.__file__, encoding="utf-8").read()
    _RB = open("core/gateway/v9_bridge/response_builder.py", encoding="utf-8").read()
    assert "_exhausted_no_output" in _RB  # 响应构建仍计算该标记
    assert "if _final_empty and not tool_steps:" in _RB
    assert "无工具产出，任务未完成" in _TP, "降级文案在 turn_protocol"
    assert "exhausted_no_output" in _TP, "turn_protocol 应接收 exhausted_no_output 参数"


def test_frontend_max_tokens_empty_uses_summary():
    """前端 max_tokens 分支: content 为空 → 显示摘要而非"已有产出" """
    assert "function buildToolStepsSummary(steps)" in _CHAT, "缺前端摘要助手"
    assert "已完成 ' + steps.length + ' 个工具调用，成功 " in _CHAT, "缺 N/M 格式"
    assert "关键发现：" in _CHAT
    # 两个分支(主路径 + continuePausedTask)都应在 content 为空时走摘要
    assert "const _sumTxt = buildToolStepsSummary(d.tool_steps)" in _CHAT
    assert "const _sumTxt2 = buildToolStepsSummary(d.tool_steps)" in _CHAT
    # 摘要替代"已有产出"
    assert "已按工具调用汇总产出" in _CHAT
    assert "未产生有效产出，请重新描述需求" in _CHAT
