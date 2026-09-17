# -*- coding: utf-8 -*-
"""2026-09-05 三个机制修复测试: 空回复摘要重试 / 「继续」复用 goal / 新任务上下文隔离"""
import sys

sys.path.insert(0, ".")
import agent_gateway_enhanced as main

_SRC = (
    open("agent_gateway_enhanced.py", encoding="utf-8").read()
    + open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()
)  # P3-B: G 块已归位
POC_TEXT = (
    "任务：Computer Use 混合方案 POC——a11y 树 + VLM 语义映射。  ## 验证目标 证明「playwright "
    "a11y 树枚举元素 + VLM 只做选择」能可靠驱动点击，而不是让 VLM 独立产坐标。"
)


def test_a_empty_retry_single_with_summary():
    """a) 空回复: 注入上一轮上下文摘要自动重试 1 次; 重试仍空 → need_more"""
    _RG = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    assert "empty_reply_count < 1" in _RG, "应只自动重试 1 次(非 2 次)"
    assert "ctx_summary_fn(messages)" in _RG, "重试应注入上一轮上下文摘要"
    assert "上一轮进展摘要" in _RG
    # helper: 摘要取最后非空 assistant 内容
    msgs = [
        {"role": "user", "content": "任务A"},
        {"role": "assistant", "content": "已完成侦察：元素 25 个，百度一下=1"},
        {"role": "assistant", "content": ""},
    ]
    s = main._v9_ctx_summary(msgs)
    assert "百度一下=1" in s, s


def test_b_resume_utterance():
    """b) 「继续」短文本识别(复用 goal 不新建)"""
    assert main._v9_is_resume_utterance("继续") is True
    assert main._v9_is_resume_utterance("继续任务") is True
    assert main._v9_is_resume_utterance("接着做") is True
    assert main._v9_is_resume_utterance("恢复上次任务") is True
    assert main._v9_is_resume_utterance(POC_TEXT) is False
    assert main._v9_is_resume_utterance("继续执行当前目标，请基于已有进度继续") is False  # >12字


def test_b_goal_reuse_wired():
    """b) 后端: 继续文本 / goal_id → 复用最近 active goal, 不新建"""
    assert "objective=继续 幽灵 goal" in _SRC or "幽灵 goal" in _SRC or "不新建" in _SRC
    assert "is_resume_fn(_last_user_goal)" in _SRC  # P3-B: 归位 recovery 后参数化
    assert 'data.get("goal_id")' in _SRC, "应支持显式 goal_id 续跑"
    assert '_g_cur.get("status") in ("active", "paused", "failed")' in _SRC


def test_c_new_task_isolation():
    """c) 长新任务(含 继续/下一步 关键词)不触发旧任务上下文注入"""
    assert main._v9_looks_like_new_task(POC_TEXT) is True
    assert main._v9_looks_like_new_task("继续执行上个任务，把剩余步骤跑完") is False  # 继续开头→同任务
    assert main._v9_looks_like_new_task("好的") is False
    _REC = open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()  # P3-B: C 块已归位
    assert "_is_long_new_task" in _REC, "注入处应有新任务门禁(recovery)"
    # 新任务与旧任务低相似 → keep_old_task False(不注入旧摘要)
    assert main._v9_keep_old_task("排查 Microduck 报告残缺", POC_TEXT) is False
    assert main._v9_keep_old_task("排查 Microduck 报告残缺", "继续") is True  # 恢复指令保留旧摘要
    assert main._v9_keep_old_task("POC a11y 试验任务", "继续 POC a11y 试验任务") is True  # 高相似续写


def test_round_checkpoint_build():
    """S2: 单一轮检查点 = 上一轮结束原因 + 已执行步骤(✓/✗/⚪) + 最后进展(合并三兄弟)"""
    events = [
        {"type": "user_message", "payload": {"source": "user_input", "content": "任务A"}},
        {"type": "tool_call", "payload": {"name": "list_dir", "call_id": "c1", "arguments": {"path": "data"}}},
        {"type": "tool_result", "payload": {"call_id": "c1", "success": True, "content": "data/tmp …"}},
        {"type": "tool_call", "payload": {"name": "curl", "call_id": "c2", "arguments": {}}},
        {"type": "tool_result", "payload": {"call_id": "c2", "success": False, "content": "超时"}},
        {"type": "assistant_message", "payload": {"content": "侦察完成：找到 25 个元素"}},
        {"type": "turn_end", "payload": {"reason": "max_tokens"}},
        {"type": "user_message", "payload": {"source": "user_input", "content": "继续"}},
        {"type": "tool_call", "payload": {"name": "read_file", "call_id": "c3", "arguments": {"path": "x"}}},
    ]
    s = main._v9_round_checkpoint(events)
    assert "[轮检查点]" in s, s
    assert "上一轮结束: max_tokens" in s, s
    assert "✓ list_dir" in s and "data" in s, s
    assert "✗ curl" in s and "超时" in s, s
    assert "侦察完成" in s, "应含最后进展"
    # read_file 属于「继续」之后的下一轮 → 不应进上一轮 checkpoint
    assert "read_file" not in s
    # 无上一轮 → 空; 事件层不被修改
    assert main._v9_round_checkpoint(events[:1]) == ""
    assert events[3]["payload"]["name"] == "curl"
    # cap
    many = [
        {"type": "tool_call", "payload": {"name": "read_file", "call_id": "m%d" % i, "arguments": {"path": "f%d" % i}}}
        for i in range(30)
    ]
    d2 = main._v9_round_checkpoint(many, cap=16)
    assert d2.count("read_file") == 16, d2.count("read_file")


def test_checkpoint_single_injection_wired():
    """S2: 注入单点化 — 只保留 _v9_round_checkpoint 一处; 旧三层逻辑与旁路移除"""
    _CU = open("core/gateway/v9_bridge/context_utils.py", encoding="utf-8").read()
    assert "def _v9_round_checkpoint" in _CU, "应实现单一轮检查点"
    assert "[轮检查点]" in _CU
    assert "def _v9_recon_digest" not in _SRC, "旧 recon-digest 应删除"
    assert "def _v9_prior_round_summary" not in _SRC, "旧轮摘要应删除"
    assert "def _v9_steps_memory" not in _SRC, "旧步骤断点应删除"
    assert "本任务已执行过的工具" not in _SRC, "旧注入文案应移除"
    assert "[历史轮摘要(压缩)]" not in _SRC
    assert "[已完成步骤(断点)]" not in _SRC
    _REC2 = open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()
    assert "not _is_long_new_task" in _REC2, "隔离门禁保留(recovery)"
