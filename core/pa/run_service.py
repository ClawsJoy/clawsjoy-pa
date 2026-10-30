"""PA RunService（P0-2b · 可注入 worker；不接路由/DshHarness/聊天）.

包装 core/pa/run_queue.AsyncRunQueue：

  · 单 worker 线程（daemon）；submit 入队后唤醒 worker；
  · worker claim_next → 调注入 runner(record) -> dict；
  · runner 可调用（函数/对象）；对象若有 cancel(run_id) 则 running 取消时调用；
  · 执行前/后发事件（started/finished/failed/cancelled/cancel_requested），可注入 event_sink；
  · 终态：runner 返回 status/ok 或异常 ⇒ done/failed；worker 见到 cancel_requested ⇒ cancelled；
  · cancel：queued 立即 cancelled；running 置 cancel_requested 并调 runner.cancel；
  · stop/shutdown：停 worker，queued 可取消（默认），running 等待 runner 收尾；
  · snapshot 供 API 读 runs/events/worker；本件不 import 路由/聊天/DSH。

runner 契约：
    result = runner(record)             # record 为 queued→running 公开 dict
    result = {"status": "done"|"failed"|"cancelled", "output": any,
              "error": str, "reason": str}   # 缺省 status 由 ok 推
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from datetime import datetime

from core.pa.run_queue import TERMINAL_STATES, AsyncRunQueue, RunNotFound


def _now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class RunServiceError(Exception):
    """RunService 层之基错。"""


class RunService:
    """单 worker 队列服务（可注入 runner；测试用 fake runner）。

    典型：
        q = AsyncRunQueue(path=tmp)
        svc = RunService(queue=q, runner=my_runner, auto_start=True)
        rec = svc.submit(session_id="s", user_id="u", client_request_id="c", task="t")
        ...
        svc.stop()
    """

    def __init__(self, queue=None, runner=None, *, auto_start=True, event_sink=None, event_limit=2000):
        # 兼容 RunService(runner) 之写法：首参可调用且无 runner ⇒ 视为 runner
        if runner is None and callable(queue) and not isinstance(queue, AsyncRunQueue):
            runner, queue = queue, None
        if queue is None:
            queue = AsyncRunQueue()
        if runner is None:
            raise RunServiceError("RunService 需要注入 runner（可调用对象）")
        if not callable(runner):
            raise RunServiceError("runner 须可调用")
        self.queue = queue
        self.runner = runner
        self._event_sink = event_sink
        self._event_limit = int(event_limit) if int(event_limit) > 0 else 2000
        self._events = deque(maxlen=self._event_limit)
        self._seq = 0
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop_evt = threading.Event()
        self._thread = None
        self._processed = 0
        self._last_error = ""
        self._started_at = ""
        if auto_start:
            self.start()

    # ---------------- 生命周期 ----------------

    def start(self):
        """启动单 worker（幂等）；已启动 ⇒ 返回 False。"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop_evt.clear()
            self._started_at = _now_iso()
            self._thread = threading.Thread(target=self._worker_loop, name="pa-run-worker", daemon=True)
            self._thread.start()
            return True

    def stop(self, timeout=10.0, cancel_queued=True, reason="shutdown"):
        """停 worker：置停止信号、可取消 queued、等 running 收尾（超时返回 False）。"""
        self._stop_evt.set()
        if cancel_queued:
            for rec in self.queue.cancel_all_queued(reason=reason):
                self._emit("cancelled", rec, {"reason": reason, "source": "shutdown"})
        self._wake.set()
        t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=float(timeout))
        return not (t is not None and t.is_alive())

    shutdown = stop

    @property
    def is_worker_alive(self):
        t = self._thread
        return bool(t is not None and t.is_alive())

    # ---------------- 提交 / 取消 ----------------

    def submit(self, **kwargs):
        """入队并唤醒 worker；返回 queue record（含 position）。"""
        rec = self.queue.submit(**kwargs)
        self._emit("submitted", rec, {"position": rec.get("position", 0)})
        self._wake.set()
        return rec

    def cancel(self, run_id, reason="user_cancel"):
        """queued 立即 cancelled；running 置 cancel_requested 并调 runner.cancel(若有)。"""
        before = self.queue.get(run_id)
        rec = self.queue.cancel(run_id, reason=reason)
        state = rec.get("state")
        if state == "cancelled":
            self._emit("cancelled", rec, {"reason": reason, "source": "cancel"})
        elif state == "running":
            self._emit("cancel_requested", rec, {"reason": reason})
            cb = getattr(self.runner, "cancel", None)
            if callable(cb):
                try:
                    cb(run_id)
                except Exception as exc:  # noqa: BLE001
                    self._record_error(f"runner.cancel: {type(exc).__name__}")
                    self._emit("cancel_error", rec, {"error": type(exc).__name__})
        else:
            if before.get("state") != state:
                self._emit("cancel_ignored", rec, {"reason": "terminal/idempotent"})
        self._wake.set()
        return rec

    # ---------------- 读面 ----------------

    def get(self, run_id):
        return self.queue.get(run_id)

    def snapshot(self):
        """供 API：queue snapshot ＋ events ＋ worker 状态。"""
        snap = self.queue.snapshot()
        with self._lock:
            events = list(self._events)
            snap["events"] = events
            snap["worker"] = {
                "alive": self.is_worker_alive,
                "processed": self._processed,
                "started_at": self._started_at,
                "last_error": self._last_error,
                "stopped": self._stop_evt.is_set(),
            }
            snap["next_seq"] = self._seq
        return snap

    def events(self):
        with self._lock:
            return list(self._events)

    # ---------------- worker ----------------

    def _worker_loop(self):
        while not self._stop_evt.is_set():
            rec = self.queue.claim_next()
            if rec is None:
                self._wake.wait(0.2)
                self._wake.clear()
                continue
            self._execute(rec)

    def _execute(self, rec):
        run_id = rec["run_id"]
        try:
            cur = self.queue.get(run_id)
            if cur.get("cancel_requested"):
                self._settle(run_id, "cancelled", reason="cancelled before start")
                return
            self._emit("started", cur, {})
            result = self.runner(cur)
            # runner 返回后：cancel 优先（协作式收敛）
            cur2 = self.queue.get(run_id)
            if cur2.get("cancel_requested"):
                self._settle(run_id, "cancelled", reason=cur2.get("reason") or "user_cancel")
                return
            status, output, err, reason = self._interpret(result)
            self._settle(run_id, status, output=output, error=err, reason=reason)
        except Exception as exc:  # noqa: BLE001
            self._record_error(f"{type(exc).__name__}: {exc}")
            try:
                self._settle(
                    run_id, "failed", error=f"{type(exc).__name__}: {str(exc)[:300]}", reason="runner_exception"
                )
            except Exception as exc2:  # noqa: BLE001
                self._record_error(f"settle failed: {type(exc2).__name__}")

    def _interpret(self, result):
        """runner 返回值 ⇒ (status, output, error, reason)。"""
        if not isinstance(result, dict):
            return "done", result, "", ""
        status = result.get("status")
        if status in ("done", "failed", "cancelled"):
            pass
        elif (
            result.get("ok") is False
            or result.get("success") is False
            or (result.get("error") and not result.get("output"))
        ):
            status = "failed"
        else:
            status = "done"
        return (status, result.get("output"), str(result.get("error") or ""), str(result.get("reason") or ""))

    def _settle(self, run_id, status, *, output=None, error="", reason=""):
        rec = self.queue.finish(run_id, status, reason=reason, error=error, output=output)
        self._processed += 1
        etype = {"done": "finished", "failed": "failed", "cancelled": "cancelled"}[status]
        self._emit(etype, rec, {"status": status, "error": error, "reason": reason})

    # ---------------- 事件 ----------------

    def _emit(self, etype, rec, data):
        with self._lock:
            self._seq += 1
            ev = {
                "seq": self._seq,
                "type": etype,
                "run_id": rec.get("run_id") if isinstance(rec, dict) else "",
                "state": rec.get("state") if isinstance(rec, dict) else "",
                "ts": _now_iso(),
                "data": data or {},
            }
            self._events.append(ev)
            sink = self._event_sink
        if sink is not None:
            try:
                sink(ev)
            except Exception:  # noqa: BLE001
                pass
        return ev

    def _record_error(self, msg):
        with self._lock:
            self._last_error = str(msg)[:300]


__all__ = ["RunServiceError", "RunService"]
