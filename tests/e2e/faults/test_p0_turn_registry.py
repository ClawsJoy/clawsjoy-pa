# -*- coding: utf-8 -*-
"""P0-2 turn 持久注册表回归。纪律：先能失败，再能通过。"""
import sys
import time

sys.path.insert(0, ".")
import pytest

from core.gateway import turn_registry as tr


@pytest.fixture()
def reg(tmp_path, monkeypatch):
    monkeypatch.setattr(tr, "DB_PATH", str(tmp_path / "turns.db"))
    tr.reset_for_test()
    yield tr
    tr.reset_for_test()


def test_FAULT_same_second_turns_do_not_collide(reg):
    """① 先能失败：同一秒建两个 turn 必须是**两个不同的键**（旧实现 int(time.time()) 会撞号）。"""
    k1 = reg.create_turn("s1")
    k2 = reg.create_turn("s1")
    assert k1 != k2
    assert len(k1) == 32 and len(k2) == 32  # uuid4 hex
    assert reg.get_turn(k1)["turn_id"] == reg.get_turn(k2)["turn_id"]  # 可读标签可能相同
    assert reg.get_turn(k1)["turn_key"] != reg.get_turn(k2)["turn_key"]  # 但键必须不同


def test_FAULT_terminal_state_cannot_go_back(reg):
    """终态不可逆：COMPLETED 之后不得再转 RUNNING（防状态乱跳）。"""
    k = reg.create_turn("s1")
    assert reg.finish_turn(k, "COMPLETED") is True
    assert reg.finish_turn(k, "COMPLETED") is True  # 幂等
    assert reg._transition(k, "RUNNING") is False
    assert reg.get_turn(k)["status"] == "COMPLETED"


def test_PASS_lifecycle_create_heartbeat_finish(reg):
    """② 再能通过：正常生命周期。"""
    k = reg.create_turn("s_ok", user_id="u1")
    assert reg.get_turn(k)["status"] == "RUNNING"
    before = reg.get_turn(k)["heartbeat_at"]
    time.sleep(0.05)
    reg.heartbeat(k)
    assert reg.get_turn(k)["heartbeat_at"] > before
    assert reg.finish_turn(k, "COMPLETED", "done") is True
    assert reg.get_turn(k)["status"] == "COMPLETED"


def test_heartbeat_async_is_batched(reg):
    """热路径心跳只入队，由批量 flush 落库（不拖慢 SSE）。"""
    k = reg.create_turn("s_hb")
    before = reg.get_turn(k)["heartbeat_at"]
    reg.heartbeat_async(k)
    reg.heartbeat_async(k)
    assert reg.get_turn(k)["heartbeat_at"] == before  # 尚未落库
    n = reg._flush_once()
    assert n >= 1
    assert reg.get_turn(k)["heartbeat_at"] > before


def test_FAULT_stale_scan_marks_dead_turns(reg):
    """重启扫描：心跳超时的 RUNNING/DETACHED → STALE（这就是「挂死后有归宿」）。"""
    k_run = reg.create_turn("s_dead1")
    k_det = reg.create_turn("s_dead2")
    reg.detach_turn(k_det)
    k_done = reg.create_turn("s_live")
    reg.finish_turn(k_done, "COMPLETED")

    out = reg.scan_stale(now=time.time() + 100000, stale_after=900)
    keys = {o["turn_key"] for o in out}
    assert k_run in keys and k_det in keys
    assert k_done not in keys  # 终态不动
    assert reg.get_turn(k_run)["status"] == "STALE"
    assert reg.get_turn(k_det)["status"] == "STALE"
    assert reg.get_turn(k_done)["status"] == "COMPLETED"


def test_fresh_turns_are_not_marked_stale(reg):
    """不退化：心跳新鲜时不得被误判 STALE。"""
    k = reg.create_turn("s_fresh")
    assert reg.scan_stale(stale_after=900) == []
    assert reg.get_turn(k)["status"] == "RUNNING"


def test_stale_does_not_auto_resume(reg):
    """STALE 不自动续跑：scan_stale 只标状态并返回清单，不产生任何执行。"""
    k = reg.create_turn("s_s")
    reg.scan_stale(now=time.time() + 100000, stale_after=900)
    assert reg.get_turn(k)["status"] == "STALE"
    assert reg.scan_stale(now=time.time() + 100001, stale_after=900) == []  # 幂等


def test_detach_then_resume_allowed(reg):
    """DETACHED 可以被重新接管（用户选「重新继续」时）。"""
    k = reg.create_turn("s_d")
    assert reg.detach_turn(k) is True
    assert reg.get_turn(k)["status"] == "DETACHED"
    assert reg._transition(k, "RUNNING", "用户重新继续") is True
