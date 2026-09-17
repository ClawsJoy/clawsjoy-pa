"""#101 G6: 目标跨轮次持久化 — goal 生命周期（create/get/complete/恢复注入）"""
import json
import os
import sys
import time

sys.path.insert(0, ".")
import pytest

from core.gateway import goal_state as GS


@pytest.fixture(autouse=True)
def _clean_goal():
    GS._goals.clear()
    yield


def test_create_and_get_goal():
    """创建 active goal → 内存 + 磁盘均可读"""
    uid, sid = "g6_u1", "g6_s1"
    g = GS.create_goal(uid, sid, "修改 report.py 并加测试", plan=["改 report.py", "加测试"])
    assert g["status"] == "active"
    assert g["objective"] == "修改 report.py 并加测试"
    assert len(g["plan"]) == 2
    assert g["goal_id"].startswith("goal_")
    g2 = GS.get_goal(uid, sid)
    assert g2["goal_id"] == g["goal_id"]
    assert g2["status"] == "active"


def test_create_reuses_active():
    """②(2026-09-13) 口径更新: 同目标复用 / 不同目标隔离(2026-08-29 目标隔离修复)

    旧断言"不同 objective 也复用同一 goal_id"是废弃语义: 复用 active goal 并覆盖 objective
    会让多任务目标互相污染(Agent 跑新任务却延续旧任务思维)。现语义:
    - 同 session + 同 objective → 复用(续跑/重复)
    - 同 session + 不同 objective → 旧 goal 置 archived, 建新 goal
    """
    uid, sid = "g6_u2", "g6_s2"
    g1 = GS.create_goal(uid, sid, "任务A")
    # 同目标 → 复用同一 goal_id(续跑/重复调用)
    g_same = GS.create_goal(uid, sid, "任务A")
    assert g_same["goal_id"] == g1["goal_id"], "同目标应复用 goal"
    # 不同目标 → 新建 goal, 旧 goal 被归档(原地标记, g1 是同一 dict 对象)
    g2 = GS.create_goal(uid, sid, "任务B 更新")
    assert g2["goal_id"] != g1["goal_id"], "不同目标不应复用(防目标污染)"
    assert g2["objective"] == "任务B 更新"
    assert g2["status"] == "active"
    assert g1["status"] == "archived", f"旧 goal 应归档: {g1['status']}"


def test_complete_goal():
    """完成 → status=complete + 持久化"""
    uid, sid = "g6_u3", "g6_s3"
    GS.create_goal(uid, sid, "任务C")
    g = GS.complete_goal(uid, sid)
    assert g["status"] == "complete"
    g2 = GS.get_goal(uid, sid)
    assert g2["status"] == "complete"


def test_goal_context_injection():
    """③(2026-09-13) 口径更新: active 全量注入; 非 active 注入"最近目标"; 无 goal → 空串

    W3 修复(2026-08-30): 用户"继续"深挖任务时 goal 可能中途被置为非 active,
    但 objective 仍应注入(否则 Agent 丢失任务上下文, 退化到"任务目标只有一句 hi")。
    """
    uid, sid = "g6_u4", "g6_s4"
    GS.create_goal(uid, sid, "跨轮次目标", plan=["步骤1", "步骤2"])
    ctx = GS.goal_context_injection(uid, sid)
    assert "当前目标" in ctx and "跨轮次目标" in ctx
    assert "步骤1" in ctx and "步骤2" in ctx
    GS.complete_goal(uid, sid)
    ctx2 = GS.goal_context_injection(uid, sid)
    assert "跨轮次目标" in ctx2, "非 active goal 也应注入 objective"
    assert "非active" in ctx2, f"应标注非 active: {ctx2}"
    # 无 goal → 空串(该分支保留)
    assert GS.goal_context_injection("g6_none", "g6_none") == ""


def test_restore_from_disk_after_clear():
    """重启模拟：清内存后从磁盘恢复"""
    uid, sid = "g6_u5", "g6_s5"
    g = GS.create_goal(uid, sid, "重启前目标")
    GS._goals.clear()  # 模拟进程重启
    g2 = GS.get_goal(uid, sid)
    assert g2 is not None
    assert g2["objective"] == "重启前目标"
