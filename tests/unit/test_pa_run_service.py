"""core/pa/run_service.py 之测：单 worker / 顺序 / 单主 / 取消 / 失败 / 停机 / 事件.

以何形调用：
    python -X utf8 -B -m pytest tests/unit/test_pa_run_service.py -q
"""

import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa.run_queue import AsyncRunQueue  # noqa: E402
from core.pa.run_service import RunService  # noqa: E402


def _wait(predicate, timeout=4.0, interval=0.01):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _q(tmp_path):
    return AsyncRunQueue(path=tmp_path / "async_queue.json")


def _ok_runner(calls=None):
    calls = calls if calls is not None else []

    def _run(rec):
        calls.append(rec["run_id"])
        return {"status": "done", "output": "out:" + rec["run_id"]}

    return _run


# ---------- 单 worker / 顺序 ----------


def test_worker_processes_fifo_order(tmp_path):
    calls = []
    svc = RunService(queue=_q(tmp_path), runner=_ok_runner(calls), auto_start=False)
    a = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="ta")
    b = svc.submit(session_id="s1", user_id="u", client_request_id="b", task="tb")
    c = svc.submit(session_id="s2", user_id="u", client_request_id="c", task="tc")
    svc.start()
    assert _wait(
        lambda: calls == [a["run_id"], b["run_id"], c["run_id"]]
        and all(svc.get(x["run_id"])["state"] == "done" for x in (a, b, c))
    )
    assert svc.get(a["run_id"])["state"] == "done"
    assert svc.get(b["run_id"])["state"] == "done"
    assert svc.get(c["run_id"])["state"] == "done"
    assert svc.get(a["run_id"])["output"] == "out:" + a["run_id"]
    svc.stop(cancel_queued=False)
    assert not svc.is_worker_alive


def test_single_main_second_waits(tmp_path):
    started = []
    gate = threading.Event()

    class _Block:
        def __call__(self, rec):
            started.append(rec["run_id"])
            gate.wait(4)
            return {"status": "done"}

    svc = RunService(queue=_q(tmp_path), runner=_Block(), auto_start=True)
    a = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="ta")
    b = svc.submit(session_id="s1", user_id="u", client_request_id="b", task="tb")
    assert _wait(lambda: started == [a["run_id"]])
    assert svc.get(b["run_id"])["state"] == "queued", "单主：第二单必须等"
    assert svc.queue.queue_depth() == 1
    gate.set()
    assert _wait(lambda: svc.get(a["run_id"])["state"] == "done" and svc.get(b["run_id"])["state"] == "done")
    svc.stop(cancel_queued=False)


def test_snapshot_worker_and_events(tmp_path):
    svc = RunService(queue=_q(tmp_path), runner=_ok_runner(), auto_start=True)
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="c", task="t")
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "done")
    snap = svc.snapshot()
    assert snap["queue_depth"] == 0 and snap["worker"]["alive"] is True
    assert snap["worker"]["processed"] >= 1
    types = [e["type"] for e in snap["events"]]
    assert "submitted" in types and "started" in types and "finished" in types
    assert [e["seq"] for e in snap["events"]] == sorted(e["seq"] for e in snap["events"])
    svc.stop(cancel_queued=False)


# ---------- 终态 / 事件 ----------


def test_runner_failed_result(tmp_path):
    def _run(rec):
        return {"status": "failed", "error": "boom", "reason": "test"}

    svc = RunService(queue=_q(tmp_path), runner=_run, auto_start=True)
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="f", task="t")
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "failed")
    got = svc.get(rec["run_id"])
    assert got["error"] == "boom" and got["reason"] == "test"
    assert any(e["type"] == "failed" for e in svc.events())
    svc.stop(cancel_queued=False)


def test_runner_exception_failed(tmp_path):
    def _run(rec):
        raise RuntimeError("kaboom")

    svc = RunService(queue=_q(tmp_path), runner=_run, auto_start=True)
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="x", task="t")
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "failed")
    assert "RuntimeError" in svc.get(rec["run_id"])["error"]
    svc.stop(cancel_queued=False)


def test_runner_status_cancelled(tmp_path):
    def _run(rec):
        return {"status": "cancelled", "reason": "runner cancelled"}

    svc = RunService(queue=_q(tmp_path), runner=_run, auto_start=True)
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="c", task="t")
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "cancelled")
    assert any(e["type"] == "cancelled" for e in svc.events())
    svc.stop(cancel_queued=False)


def test_event_sink_receives_events(tmp_path):
    got = []
    svc = RunService(queue=_q(tmp_path), runner=_ok_runner(), auto_start=True, event_sink=lambda ev: got.append(ev))
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="e", task="t")
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "done")
    assert [e["type"] for e in got][:2] == ["submitted", "started"]
    assert "finished" in [e["type"] for e in got]
    svc.stop(cancel_queued=False)


# ---------- 取消 ----------


def test_cancel_queued_immediate(tmp_path):
    svc = RunService(queue=_q(tmp_path), runner=_ok_runner(), auto_start=False)
    a = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="ta")
    b = svc.submit(session_id="s1", user_id="u", client_request_id="b", task="tb")
    got = svc.cancel(b["run_id"])
    assert got["state"] == "cancelled" and got["position"] == 0
    assert svc.get(a["run_id"])["state"] == "queued"
    assert any(e["type"] == "cancelled" for e in svc.events())
    svc.stop(cancel_queued=False)


def test_cancel_running_sets_flag_and_calls_runner_cancel(tmp_path):
    started = threading.Event()
    gate = threading.Event()
    cancel_calls = []

    class _Slow:
        def __call__(self, rec):
            started.set()
            gate.wait(4)
            return {"status": "done"}

        def cancel(self, run_id):
            cancel_calls.append(run_id)

    svc = RunService(queue=_q(tmp_path), runner=_Slow(), auto_start=True)
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="t")
    assert started.wait(4)
    got = svc.cancel(rec["run_id"])
    assert got["state"] == "running" and got["cancel_requested"] is True
    assert cancel_calls == [rec["run_id"]]
    gate.set()
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "cancelled")
    evs = [e["type"] for e in svc.events()]
    assert "cancel_requested" in evs and "cancelled" in evs
    svc.stop(cancel_queued=False)


def test_cancel_running_runner_ignores_flag_still_cancelled(tmp_path):
    started = threading.Event()
    gate = threading.Event()

    class _Ignore:
        def __call__(self, rec):
            started.set()
            gate.wait(4)
            return {"status": "done", "output": "should-not-win"}

    svc = RunService(queue=_q(tmp_path), runner=_Ignore(), auto_start=True)
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="t")
    assert started.wait(4)
    svc.cancel(rec["run_id"])
    gate.set()
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "cancelled")
    assert svc.get(rec["run_id"])["output"] != "should-not-win"
    svc.stop(cancel_queued=False)


def test_cancel_terminal_idempotent(tmp_path):
    svc = RunService(queue=_q(tmp_path), runner=_ok_runner(), auto_start=True)
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="t")
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "done")
    assert svc.cancel(rec["run_id"])["state"] == "done"
    svc.stop(cancel_queued=False)


def test_cancel_unknown_raises(tmp_path):
    svc = RunService(queue=_q(tmp_path), runner=_ok_runner(), auto_start=False)
    with pytest.raises(Exception):
        svc.cancel("nope")
    svc.stop(cancel_queued=False)


# ---------- 停机 ----------


def test_stop_cancels_queued_and_joins_worker(tmp_path):
    started = threading.Event()
    gate = threading.Event()

    class _Block:
        def __call__(self, rec):
            started.set()
            gate.wait(4)
            return {"status": "done"}

    svc = RunService(queue=_q(tmp_path), runner=_Block(), auto_start=True)
    a = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="ta")
    b = svc.submit(session_id="s1", user_id="u", client_request_id="b", task="tb")
    assert started.wait(4)
    ok = svc.stop(timeout=2, cancel_queued=True)
    assert ok is False, "running 在飞 ⇒ 不能硬杀"
    assert svc.get(b["run_id"])["state"] == "cancelled"
    gate.set()
    assert _wait(lambda: svc.get(a["run_id"])["state"] == "done")
    ok2 = svc.stop(timeout=2, cancel_queued=False)
    assert ok2 is True and not svc.is_worker_alive


def test_auto_start_false_manual_start(tmp_path):
    svc = RunService(queue=_q(tmp_path), runner=_ok_runner(), auto_start=False)
    rec = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="t")
    assert svc.get(rec["run_id"])["state"] == "queued"
    assert svc.start() is True
    assert _wait(lambda: svc.get(rec["run_id"])["state"] == "done")
    svc.stop(cancel_queued=False)


def test_submit_position_and_queue_depth(tmp_path):
    svc = RunService(queue=_q(tmp_path), runner=_ok_runner(), auto_start=False)
    a = svc.submit(session_id="s1", user_id="u", client_request_id="a", task="t")
    b = svc.submit(session_id="s1", user_id="u", client_request_id="b", task="t")
    assert a["position"] == 1 and b["position"] == 2
    assert svc.snapshot()["queue_depth"] == 2
    svc.stop(cancel_queued=True)
