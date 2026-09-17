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
    """① 先能失败：同一秒建两个 turn 必须是**两个不同的键**（旧实现用 int(time.time()) 当**键** 会撞号）。

    断言语义修正（2026-09-18，未登记台账的**秒级 flake**，见未闭 `X-06`）：
    原写法把 `turn_id` 钉死为「两次调用必归同一秒」（`turn_id == int(_now())`，秒级可读标签）
    ⇒ 满负载全量跑两次调用**跨秒**就红（假红）。契约本来就是「**标签可以相同、键必须唯一**」
    ⇒ 改为按「创建前后的秒窗口」断言，**两种情形都合法**。
    """
    t0 = int(time.time())
    k1 = reg.create_turn("s1")
    k2 = reg.create_turn("s1")
    t1 = int(time.time())
    assert k1 != k2
    assert len(k1) == 32 and len(k2) == 32  # uuid4 hex
    l1 = reg.get_turn(k1)["turn_id"]
    l2 = reg.get_turn(k2)["turn_id"]
    # 标签是秒级：落在 [t0, t1] 窗口内且单调不减（同秒 ⇒ 相同；跨秒 ⇒ 递增）——两种都合法，**不再依赖两次调用落在同一秒**
    assert t0 <= l1 <= l2 <= t1, (t0, l1, l2, t1)
    assert reg.get_turn(k1)["turn_key"] != reg.get_turn(k2)["turn_key"]  # 真契约：键必须不同


def test_turn_label_is_second_granular_and_key_stays_unique(reg, monkeypatch):
    """契约钉死（确定性，与实时时钟无关）：标签是**秒级**（同秒相同 / 跨秒递增），**键永远唯一**。

    为什么需要它：X-06 的 flake 根因是「断言写死了同秒假设」，**不是时钟本身**。
    这里用可控时钟把**两种情形都钉死**（仅本用例内 monkeypatch，不改测试基础设施）
    —— 旧断言在跨秒分支上必然失败（可复现，见未闭 `X-06`）。
    """
    clock = {"t": 1000.4}
    monkeypatch.setattr(tr, "_now", lambda: clock["t"])
    clock["t"] = 1000.1
    k1 = reg.create_turn("s1")
    clock["t"] = 1000.9                      # 同一秒内的两次创建
    k2 = reg.create_turn("s1")
    assert k1 != k2
    assert reg.get_turn(k1)["turn_id"] == reg.get_turn(k2)["turn_id"] == 1000
    clock["t"] = 1001.2                      # 跨秒
    k3 = reg.create_turn("s1")
    assert reg.get_turn(k3)["turn_id"] == 1001
    assert len({k1, k2, k3}) == 3            # 键与时间无关：永远唯一
    assert all(len(k) == 32 for k in (k1, k2, k3))


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


def test_heartbeat_async_is_batched(reg, monkeypatch):
    """热路径心跳只入队，由批量 flush 落库（不拖慢 SSE）。

    隔离（A2，2026-09-18 · 老板/DS 拍）：
    `heartbeat_async()` 会 `_start_flusher()` 起一个**进程级 daemon 线程**
    （`HEARTBEAT_FLUSH_SEC = 2.0`；`reset_for_test()` 既不复位 `_flusher_started`、
    也不停线程）⇒ 它可能抢在本用例的显式 `_flush_once()` 之前
    清空 `_pending_hb`。反例证明（`data/tmp/hb_proof_a3.py`：把 tick 压到 20ms）：
    **原样断言 300 次失败 26 次**；本版 **300 次 0 失败**、再跑 1000 次仍 0 失败
    （只做 A2 / 只做 A1 的中间版本各残 1–3/300 ⇒ 二者互补、都必须）。
    这里把**后台线程的 tick** 换成 no-op，`_pending_hb` 的消费者只剩本用例自己。
    残留（诚实标注）：打补丁那一瞬**已经在真函数里**的 tick 仍可能吃掉这一轮
    （20ms tick 压测下 300 次里 1–3 次）⇒ 用「**至多 3 轮**」把它压到 ~1e-8；彻底消除需产品侧停线程（另开小批 B）。
    """
    real_flush_once = reg._flush_once
    monkeypatch.setattr(reg, "_flush_once", lambda: 0)   # 后台 flusher 的 tick 不再消费

    k = reg.create_turn("s_hb")
    observed = False
    for _ in range(3):
        reg._pending_hb.clear()
        before = reg.get_turn(k)["heartbeat_at"]
        reg.heartbeat_async(k)
        reg.heartbeat_async(k)
        if reg.get_turn(k)["heartbeat_at"] != before:
            # 本轮被「**打补丁那一瞬已经在真函数里**」的后台 tick 抢跑污染（µs 级窗口）
            # ⇒ 换一轮（**不放宽判据**：若 heartbeat_async 变成**同步落库**，
            #   每一轮都会走到这里 ⇒ 3 轮后下面的 `assert observed` 失败）
            continue
        # 到这里 ⇒ ① 只入队：**尚未落库**（不拖慢 SSE 的契约）
        # ② 批量 flush 落库（A1：按「最终落库」表达 —— 极罕见的残留抢跑用**幂等重入队**兜住）
        n, deadline = 0, time.time() + 2.0
        while n < 1 and time.time() < deadline:
            reg.heartbeat_async(k)                    # 热路径幂等：重复入队是允许的
            n = real_flush_once()
        assert n >= 1, "批量 flush 未把心跳落库（等待 2s）"
        assert reg.get_turn(k)["heartbeat_at"] > before   # ③ 心跳前进
        observed = True
        break
    assert observed, "未观察到「先只入队、后批量落库」（同步落库会走到这里）"


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
