"""goal 目标隔离修复测试: 新任务归档旧 active goal(防多目标污染)"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso_goals(monkeypatch):
    """隔离: 落盘 no-op + 内存清空"""
    import core.gateway.goal_state as gs

    monkeypatch.setattr(gs, "_persist_goal", lambda *a, **k: None)
    gs._goals = {}
    yield
    gs._goals = {}


def test_create_goal_new_objective_archives_old():
    """新目标 → 旧 active goal 归档, 新建独立 goal(不覆盖不污染)"""
    import core.gateway.goal_state as gs

    g1 = gs.create_goal("u1", "s1", "盘点V9系统的BUG")
    assert g1["status"] == "active"
    # 新任务: 列出目录 → 旧 goal 归档, 新 goal active
    g2 = gs.create_goal("u1", "s1", "列出目录")
    assert g1["status"] == "archived", "旧 active goal 应被归档"
    assert g2["status"] == "active"
    assert g2["goal_id"] != g1["goal_id"], "应新建独立 goal"
    assert "列出目录" in g2["objective"]
    # 同目标复用(续跑) → 不归档
    g3 = gs.create_goal("u1", "s1", "列出目录")
    assert g3["goal_id"] == g2["goal_id"], "同目标应复用"


def test_create_goal_archive_persists_archived(monkeypatch):
    """归档时旧 goal 落盘 archived(记录调用)"""
    import core.gateway.goal_state as gs

    calls = []
    monkeypatch.setattr(gs, "_persist_goal", lambda *a, **k: calls.append(a))
    gs._goals = {}
    gs.create_goal("u1", "s2", "任务A")
    gs.create_goal("u1", "s2", "任务B")
    assert any(len(a) >= 5 and a[3] == "status" and a[4] == {"status": "archived"} for a in calls), calls
    gs._goals = {}
