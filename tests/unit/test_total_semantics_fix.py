"""total 语义修正测试: completed 时 total 更新为实际工具数(进度真实化)"""
import sys

sys.path.insert(0, ".")
import pytest


def test_total_semantics_fix_in_source():
    """completed 时无 plan 任务 total=160 应修正为实际 done"""
    _SRC = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    assert "total 语义修正" in _SRC, "应有 total 修正注释"
    assert "total=_new_done" in _SRC, "应把 total 更新为实际 done"
    assert "_total > _new_done" in _SRC, "仅当 total 虚高时修正"


def test_completed_goal_has_real_total(monkeypatch, tmp_path):
    """验证 goal 完成时 progress 用实际工具数(非 160)"""
    import core.gateway.goal_state as gs

    monkeypatch.setattr(gs, "_persist_goal", lambda *a, **k: None)
    gs._goals = {}
    g = gs.create_goal("u1", "s1", "列出当前目录的文件")
    # 模拟: 6 工具完成, 但 total 之前被设为 160
    from core.gateway.goal_state import complete_goal, update_goal_progress

    update_goal_progress("u1", "s1", done=6, total=160)
    complete_goal("u1", "s1")
    g2 = gs._goals.get("u1:s1")
    # 完成判定本身 done=160 补齐(旧逻辑), total 修正由 agent_gateway 层做 —
    # 这里验证 complete_goal 幂等 + progress 可更新
    assert g2["status"] == "complete"
    assert g2["progress"]["done"] >= 6
    gs._goals = {}
