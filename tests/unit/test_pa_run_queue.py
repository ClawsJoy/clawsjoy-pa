"""core/pa/run_queue.py 之测：六态 / FIFO / 单主 / 幂等 / 背压 / 取消 / 持久化 / 恢复.

以何形调用：
    python -X utf8 -B -m pytest tests/unit/test_pa_run_queue.py -q
"""

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import run_queue as RQ  # noqa: E402


def _submit(q, n=1, session="s1", prefix="c"):
    out = []
    for i in range(n):
        out.append(
            q.submit(
                session_id=session,
                user_id="u",
                client_request_id=f"{prefix}-{session}-{i}",
                task=f"task {i}",
            )
        )
    return out


def _q(tmp_path):
    return RQ.AsyncRunQueue(path=tmp_path / "async_queue.json")


# ---------- 基本状态 / FIFO / claim ----------


def test_submit_queued_position_and_snapshot(tmp_path):
    q = _q(tmp_path)
    a = q.submit(session_id="s1", user_id="u", client_request_id="c1", task="t1")
    b = q.submit(session_id="s2", user_id="u", client_request_id="c2", task="t2")
    assert a["state"] == "queued" and a["position"] == 1
    assert b["state"] == "queued" and b["position"] == 2
    assert q.queue_depth() == 2 and q.running_run() is None
    snap = q.snapshot()
    assert snap["schema_version"] == RQ.SCHEMA_VERSION
    assert [r["run_id"] for r in snap["runs"]] == [a["run_id"], b["run_id"]]
    assert a["run_id"] != b["run_id"]


def test_global_fifo_across_sessions(tmp_path):
    q = _q(tmp_path)
    a = _submit(q, 1, "s1", "a")[0]
    b = _submit(q, 1, "s2", "b")[0]
    c = _submit(q, 1, "s1", "c")[0]
    got = [q.claim_next()["run_id"], q.finish(q.running_run()["run_id"], "done")["run_id"]]
    second = q.claim_next()
    assert second["run_id"] == b["run_id"]
    q.finish(second["run_id"], "done")
    third = q.claim_next()
    assert third["run_id"] == c["run_id"]
    q.finish(third["run_id"], "done")
    assert q.claim_next() is None
    assert got[1] == a["run_id"]


def test_claim_next_only_one_running(tmp_path):
    q = _q(tmp_path)
    a = _submit(q, 1, "s1", "a")[0]
    b = _submit(q, 1, "s1", "b")[0]
    first = q.claim_next()
    assert first["run_id"] == a["run_id"] and first["state"] == "running"
    assert q.claim_next() is None, "已有 running ⇒ 单执行权"
    assert q.running_run()["run_id"] == a["run_id"]
    q.finish(a["run_id"], "done")
    second = q.claim_next()
    assert second["run_id"] == b["run_id"]


def test_concurrent_claims_only_one(tmp_path):
    q = _q(tmp_path)
    for s in ("s0", "s1", "s2"):
        _submit(q, RQ.MAX_QUEUED_PER_SESSION, s, "c")
    assert q.queue_depth() == 9
    barrier = threading.Barrier(8)
    results = []

    def _claim(_i):
        barrier.wait()
        results.append(q.claim_next())

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(_claim, range(8)))
    won = [r for r in results if r is not None]
    assert len(won) == 1, results
    assert q.running_run() is not None
    assert q.queue_depth() == 8


# ---------- 终态 / 转移 ----------


def test_finish_done_failed_cancelled(tmp_path):
    q = _q(tmp_path)
    a, b, c = _submit(q, 3, "s1", "a")
    for rec, state in zip((a, b, c), ("done", "failed", "cancelled")):
        q.claim_next()
        q.finish(rec["run_id"], state, error="E" if state == "failed" else "")
    assert q.get(a["run_id"])["state"] == "done"
    assert q.get(b["run_id"])["state"] == "failed" and q.get(b["run_id"])["error"] == "E"
    assert q.get(c["run_id"])["state"] == "cancelled"


def test_finish_terminal_idempotent_and_illegal(tmp_path):
    q = _q(tmp_path)
    a = _submit(q, 1, "s1", "a")[0]
    q.claim_next()
    done = q.finish(a["run_id"], "done", output="ok")
    assert done["state"] == "done" and done["output"] == "ok"
    assert q.finish(a["run_id"], "done")["state"] == "done"  # 幂等
    with pytest.raises(RQ.InvalidTransition):
        q.finish(a["run_id"], "failed")  # 终态不可重开


def test_finish_queued_requires_cancelled(tmp_path):
    q = _q(tmp_path)
    a = _submit(q, 1, "s1", "a")[0]
    with pytest.raises(RQ.InvalidTransition):
        q.finish(a["run_id"], "done")
    assert q.finish(a["run_id"], "cancelled")["state"] == "cancelled"


# ---------- 幂等 ----------


def test_client_request_id_idempotent(tmp_path):
    q = _q(tmp_path)
    a = q.submit(session_id="s1", user_id="u", client_request_id="same", task="t1")
    b = q.submit(session_id="s1", user_id="u", client_request_id="same", task="DIFFERENT")
    assert b["run_id"] == a["run_id"]
    assert q.queue_depth() == 1
    assert q.by_client_request_id("same")["run_id"] == a["run_id"]
    q.claim_next()
    q.finish(a["run_id"], "done")
    c = q.submit(session_id="s1", user_id="u", client_request_id="same", task="again")
    assert c["run_id"] == a["run_id"] and c["state"] == "done", "终态幂等"
    assert q.queue_depth() == 0


# ---------- 背压 ----------


def test_per_session_backpressure(tmp_path):
    q = _q(tmp_path)
    _submit(q, RQ.MAX_QUEUED_PER_SESSION, "s1", "p")
    with pytest.raises(RQ.QueueFull) as ei:
        q.submit(session_id="s1", user_id="u", client_request_id="p-extra", task="x")
    assert ei.value.session_queued == 3
    # 别的 session 仍可入队（per-session 限，不是全局满）
    ok = q.submit(session_id="s2", user_id="u", client_request_id="s2-1", task="y")
    assert ok["state"] == "queued"
    # 取走一个 running 后，queued 名额释放
    q.claim_next()
    q.submit(session_id="s1", user_id="u", client_request_id="p-after", task="z")


def test_global_backpressure(tmp_path):
    q = _q(tmp_path)
    n = 0
    for si in range(10):
        for j in range(RQ.MAX_QUEUED_PER_SESSION):
            if n >= RQ.MAX_QUEUED:
                break
            q.submit(
                session_id=f"s{si}",
                user_id="u",
                client_request_id=f"g-{si}-{j}",
                task="t",
            )
            n += 1
        if n >= RQ.MAX_QUEUED:
            break
    assert q.queue_depth() == RQ.MAX_QUEUED
    with pytest.raises(RQ.QueueFull) as ei:
        q.submit(session_id="sx", user_id="u", client_request_id="overflow", task="x")
    assert ei.value.global_queued == RQ.MAX_QUEUED


def test_cancel_queued_frees_backpressure(tmp_path):
    q = _q(tmp_path)
    rows = _submit(q, RQ.MAX_QUEUED_PER_SESSION, "s1", "q")
    q.cancel(rows[0]["run_id"])
    q.submit(session_id="s1", user_id="u", client_request_id="q-new", task="new")
    assert q.queue_depth() == RQ.MAX_QUEUED_PER_SESSION


# ---------- 取消 ----------


def test_cancel_queued_immediate_and_position_reflow(tmp_path):
    q = _q(tmp_path)
    a, b, c = _submit(q, 3, "s1", "a")
    assert q.cancel(b["run_id"])["state"] == "cancelled"
    assert q.get(b["run_id"])["position"] == 0
    assert q.position(a["run_id"]) == 1 and q.position(c["run_id"]) == 2
    assert q.queue_depth() == 2
    assert q.cancel(b["run_id"])["state"] == "cancelled"  # 终态幂等


def test_cancel_running_sets_flag_then_finish(tmp_path):
    q = _q(tmp_path)
    a = _submit(q, 1, "s1", "a")[0]
    q.claim_next()
    got = q.cancel(a["run_id"], reason="user_stop")
    assert got["state"] == "running" and got["cancel_requested"] is True
    assert got["reason"] == "user_stop"
    fin = q.finish(a["run_id"], "cancelled", reason="user_stop")
    assert fin["state"] == "cancelled" and fin["cancel_requested"] is True
    assert q.running_run() is None


def test_cancel_all_queued_keeps_running(tmp_path):
    q = _q(tmp_path)
    a, b = _submit(q, 2, "s1", "a")
    q.claim_next()
    out = q.cancel_all_queued(reason="shutdown")
    assert [r["run_id"] for r in out] == [b["run_id"]]
    assert q.get(b["run_id"])["state"] == "cancelled"
    assert q.get(a["run_id"])["state"] == "running"
    q.finish(a["run_id"], "cancelled")


# ---------- 持久化 / 恢复 ----------


def test_persistence_schema_atomic_and_no_tmp(tmp_path):
    p = tmp_path / "q.json"
    q = RQ.AsyncRunQueue(path=p)
    _submit(q, 2, "s1", "a")
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["schema_version"] == RQ.SCHEMA_VERSION
    assert len(doc["runs"]) == 2
    assert not (tmp_path / "q.json.tmp").exists(), "原子写后 ⛔ 留 tmp"
    # 公开/落盘字段
    assert doc["runs"][0]["state"] == "queued" and doc["runs"][0]["position"] == 1


def test_restore_queued_kept_and_running_failed(tmp_path):
    p = tmp_path / "q.json"
    q1 = RQ.AsyncRunQueue(path=p)
    a, b = _submit(q1, 2, "s1", "a")
    q1.claim_next()  # a running
    q1.finish(q1.running_run()["run_id"], "done") if False else None
    # b 仍 queued；a 仍 running（不 finish，模拟进程崩溃）
    q2 = RQ.AsyncRunQueue(path=p)
    ra = q2.get(a["run_id"])
    rb = q2.get(b["run_id"])
    assert ra["state"] == "failed" and ra["error"] == "process_restart", ra
    assert rb["state"] == "queued" and rb["position"] == 1, rb
    assert q2.running_run() is None
    # 重启后仍可 claim queued
    assert q2.claim_next()["run_id"] == b["run_id"]


def test_restore_terminal_and_idempotency_index(tmp_path):
    p = tmp_path / "q.json"
    q1 = RQ.AsyncRunQueue(path=p)
    a = q1.submit(session_id="s1", user_id="u", client_request_id="idem", task="t")
    q1.claim_next()
    q1.finish(a["run_id"], "done", output="ok")
    q2 = RQ.AsyncRunQueue(path=p)
    assert q2.get(a["run_id"])["state"] == "done"
    same = q2.submit(session_id="s1", user_id="u", client_request_id="idem", task="x")
    assert same["run_id"] == a["run_id"] and same["state"] == "done"


def test_env_path_priority(tmp_path, monkeypatch):
    monkeypatch.setenv(RQ.QUEUE_PATH_ENV, str(tmp_path / "env.json"))
    assert RQ.default_queue_path() == tmp_path / "env.json"
    monkeypatch.setenv(RQ.QUEUE_PATH_ENV, "   ")
    assert RQ.default_queue_path() == RQ.DEFAULT_QUEUE_PATH


def test_corrupt_file_fail_loud(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not-json", encoding="utf-8")
    with pytest.raises(RQ.QueueCorrupt):
        RQ.AsyncRunQueue(path=p)
    p.write_text(json.dumps({"schema_version": 99, "runs": []}), encoding="utf-8")
    with pytest.raises(RQ.QueueCorrupt):
        RQ.AsyncRunQueue(path=p)


# ---------- 未知 / 参数 ----------


def test_unknown_run_errors(tmp_path):
    q = _q(tmp_path)
    with pytest.raises(RQ.RunNotFound):
        q.get("nope")
    with pytest.raises(RQ.RunNotFound):
        q.cancel("nope")
    with pytest.raises(RQ.RunNotFound):
        q.finish("nope", "done")


@pytest.mark.parametrize(
    "bad",
    [
        {"session_id": ""},
        {"user_id": ""},
        {"client_request_id": ""},
        {"task": ""},
        {"timeout": -1},
        {"timeout": "x"},
    ],
)
def test_submit_validation(tmp_path, bad):
    q = _q(tmp_path)
    kw = dict(session_id="s1", user_id="u", client_request_id="c", task="t")
    kw.update(bad)
    with pytest.raises(ValueError):
        q.submit(**kw)


def test_list_filters_and_snapshot(tmp_path):
    q = _q(tmp_path)
    a = _submit(q, 1, "s1", "a")[0]
    b = _submit(q, 1, "s2", "b")[0]
    assert [r["run_id"] for r in q.list_runs(session_id="s1")] == [a["run_id"]]
    assert [r["run_id"] for r in q.list_runs(state="queued")] == [a["run_id"], b["run_id"]]
    q.claim_next()
    assert q.get(a["run_id"])["position"] == 0
    assert q.snapshot()["queue_depth"] == 1
