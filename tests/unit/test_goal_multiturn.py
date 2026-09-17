"""Goal 驱动多 turn 执行循环测试: config + 后端守卫 + continue_goal + steer + goal_info"""
import sys

sys.path.insert(0, ".")
import pytest

_SRC = (
    open("agent_gateway_enhanced.py", encoding="utf-8").read()
    + open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()
)  # P3-B: G 块已归位
_CFG = open("config/v9/execution_policy.yaml", encoding="utf-8").read()


def test_config_goal_max_turns():
    """execution_policy.yaml 应含 goal_max_turns"""
    assert "goal_max_turns" in _CFG, "配置缺 goal_max_turns"


def test_write_turn_end_done_guard():
    """_write_turn_end: completed 即 complete(不依赖 done>=total); error/budget_limit → failed"""
    _TP = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    assert "_new_done >= _total" not in _SRC, "不应再有 done>=total 守卫(已改 reason 判定)"
    seg = _TP[_TP.index('if reason == "completed" and _g.get("status")') :]
    seg = seg[: seg.index("_goal_info = {")]
    # S5: 完成经 completion_guard.complete_if_valid 单点执行(goal_state.complete_goal 作执行器)
    assert "complete_if_valid as _cif_s5" in seg or "complete_if_valid" in seg
    assert '"active", "paused", "failed"' in seg, "completed 应含 failed 翻转分支"
    assert '"error", "budget_limit"' in seg, "真失败/预算超限 → failed"
    assert "max_tokens" not in seg or "不置 failed" in seg, "max_tokens 是续跑中断, 不应置 failed"


def test_continue_goal_branch():
    """v9_agent_chat: continue_goal=true 跳过 objective 覆盖"""
    assert 'data.get("continue_goal")' in _SRC, "应读 continue_goal 字段"
    assert '_goal_continue = bool(data.get("continue_goal"))' in _SRC
    assert "if _last_user_goal and not _goal_continue:" in _SRC, "continue 时不应 create_goal"
    assert "get_goal_by_session_id(session_id)" in _SRC


def test_continue_steer_injection():
    """续跑时注入 steer '继续目标 X，已完成 a/b 步'"""
    assert "继续目标 {str(_g_turn.get('goal_id',''))[-12:]}" in _SRC or "继续目标" in _SRC
    assert "add_steer(session_id, f" in _SRC
    assert "已完成 {_gd_t}/{_gt_t} 步" in _SRC


def test_goal_info_helper_and_payload():
    """_goal_info_for_response + 两个响应都带 goal_info"""
    _RH = open("core/gateway/v9_bridge/response_helpers.py", encoding="utf-8").read()
    assert "def _goal_info_for_response(session_id):" in _RH
    assert '"goal_active": _g.get("status") == "active"' in _RH
    assert '"goal_complete"' in _RH
    assert '"turn"' in _RH and '"max_turns"' in _RH
    _BC = open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()  # P3-B: 桥接层已归位
    assert '"goal_info": goal_info_fn(session_id)' in _BC, "非流式响应应带 goal_info"
    # 流式 done payload 也带
    assert '"goal_info": goal_info_fn(session_id)' in _BC


def test_no_plan_total_default():
    """无 plan goal: total 默认 = max_total_tools × goal_max_turns"""
    assert 'not _g_created.get("plan")' in _SRC
    assert "update_goal_progress(user_id, session_id, done=0, total=_gtotal)" in _SRC
    assert "_gtotal = int(max_total_tools) * _gmt" in _SRC  # P3-B: 归位 recovery 后参数化


def test_goal_info_turn_counts_history():
    """turn = goal.history 唯一 turn_id 数(复用 update_goal_progress 追加)"""
    import agent_gateway_enhanced as main
    import core.gateway.goal_state as gs

    # 行为级: 模拟 goal history 计数
    _g = {
        "status": "active",
        "goal_id": "g1",
        "progress": {"done": 3, "total": 5},
        "history": [{"turn_id": 1}, {"turn_id": 1}, {"turn_id": 2}],
        "session_id": "sx",
        "user_id": "ux",
    }
    gs._goals = {"ux:sx": _g}
    info = main._goal_info_for_response("sx")
    assert info["turn"] == 2, f"唯一 turn_id 数应为 2: {info}"
    assert info["goal_active"] is True
    assert info["goal_done"] == 3 and info["goal_total"] == 5


def test_frontend_goal_continuation():
    """前端: max_tokens 分支 goal 未完成且未达上限 → 自动续跑 + continue_goal 字段"""
    _CHAT = open("web/static/js/chat.js", encoding="utf-8").read()
    assert "continue_goal: _goalContinue" in _CHAT, "runAgentLoop 请求应带 continue_goal"
    assert "continue_goal: _goalContinue2" in _CHAT, "continuePausedTask 请求应带 continue_goal"
    assert "第 ' + ((_gi.turn || 0) + 1) + ' 轮继续执行" in _CHAT, "应有'第 N 轮继续执行'"
    assert "_gi.goal_active && !_gi.goal_complete" in _CHAT, "应判断 goal 未完成"
    assert "_gi.turn || 0) < (_gi.max_turns || 5)" in _CHAT, "应判断未达上限"
    assert "继续执行当前目标" in _CHAT, "应追加继续指令消息"
    assert "goal_turn: true" in _CHAT, "进度条应标 goal_turn"
    assert "📊 目标进度" in _CHAT, "进度条应显示目标进度文案"
    assert "第 ' + progress.step_index + '/' " in _CHAT, "进度条应显示轮次"
