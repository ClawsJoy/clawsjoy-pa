"""PA AsyncRunQueue 核心（P0-2a · 不接路由/worker）.

六态 queued/running/done/failed/cancelled（idle 不落 record）；全局 FIFO；
claim_next 单执行权；per-session queued≤3/全局≤20；client_request_id 幂等；
cancel queued 立即 / running 置 cancel_requested；finish 终态；
position 1-based；env PA_ASYNC_QUEUE_PATH 或 data/v9/pa/async_queue.json
原子持久化（schema_version=1）；restore 旧 running→failed process_restart。
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 1
QUEUE_PATH_ENV = "PA_ASYNC_QUEUE_PATH"
DEFAULT_QUEUE_PATH = Path("data") / "v9" / "pa" / "async_queue.json"
STATES = ("queued", "running", "done", "failed", "cancelled")
ACTIVE_STATES = ("queued", "running")
TERMINAL_STATES = ("done", "failed", "cancelled")
MAX_QUEUED_PER_SESSION = 3
MAX_QUEUED = 20


class AsyncQueueError(Exception):
    pass


class QueueFull(AsyncQueueError):
    def __init__(self, message, session_queued=0, global_queued=0):
        super().__init__(message)
        self.session_queued = int(session_queued)
        self.global_queued = int(global_queued)


class RunNotFound(AsyncQueueError):
    pass


class InvalidTransition(AsyncQueueError):
    pass


class QueueCorrupt(AsyncQueueError):
    pass


def _now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _req(value, name, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError(f"{name} 须为字符串")
    if not allow_empty and not value.strip():
        raise ValueError(f"{name} 须为非空字符串")
    return value


def default_queue_path():
    raw = (os.environ.get(QUEUE_PATH_ENV) or "").strip()
    return Path(raw) if raw else DEFAULT_QUEUE_PATH


class AsyncRunQueue:
    def __init__(self, path=None):
        self.path = Path(path if path is not None else default_queue_path())
        self._lock = threading.RLock()
        self._runs = []
        self._by_client = {}
        self._load()

    # ---------- 读 ----------
    def get(self, run_id):
        with self._lock:
            return self._public_locked(self._find_locked(run_id))

    get_run = get

    def by_client_request_id(self, client_request_id):
        with self._lock:
            rid = self._by_client.get(str(client_request_id))
            return None if rid is None else self._public_locked(self._find_locked(rid))

    def position(self, run_id):
        with self._lock:
            rec = self._find_locked(run_id)
            return self._position_locked(rec["run_id"]) if rec["state"] == "queued" else 0

    def queue_depth(self):
        with self._lock:
            return len(self._queued_locked())

    def running_run(self):
        with self._lock:
            for rec in self._runs:
                if rec["state"] == "running":
                    return self._public_locked(rec)
            return None

    def list_runs(self, state=None, session_id=None):
        with self._lock:
            out = []
            for rec in self._runs:
                if state is not None and rec["state"] != state:
                    continue
                if session_id is not None and rec["session_id"] != session_id:
                    continue
                out.append(self._public_locked(rec))
            return out

    def snapshot(self):
        with self._lock:
            return {
                "schema_version": SCHEMA_VERSION,
                "queue_depth": self.queue_depth(),
                "running": self.running_run(),
                "runs": [self._public_locked(r) for r in self._runs],
            }

    # ---------- 写 ----------
    def submit(
        self, *, session_id, user_id, client_request_id, task, model="", permission_level="", cwd="", timeout=0.0
    ):
        _req(session_id, "session_id")
        _req(user_id, "user_id")
        _req(client_request_id, "client_request_id")
        _req(task, "task")
        _req(model, "model", allow_empty=True)
        _req(permission_level, "permission_level", allow_empty=True)
        _req(cwd, "cwd", allow_empty=True)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("timeout 须为数值")
        if timeout < 0:
            raise ValueError("timeout 禁止为负")
        with self._lock:
            existing = self._by_client.get(client_request_id)
            if existing is not None:
                return self._public_locked(self._find_locked(existing))
            queued = self._queued_locked()
            sess_n = sum(1 for r in queued if r["session_id"] == session_id)
            if sess_n >= MAX_QUEUED_PER_SESSION:
                raise QueueFull(f"session queued 上限 {MAX_QUEUED_PER_SESSION}", sess_n, len(queued))
            if len(queued) >= MAX_QUEUED:
                raise QueueFull(f"全局 queued 上限 {MAX_QUEUED}", sess_n, len(queued))
            now = _now_iso()
            rec = {
                "run_id": uuid.uuid4().hex,
                "client_request_id": client_request_id,
                "session_id": session_id,
                "user_id": user_id,
                "task": task,
                "model": model,
                "permission_level": permission_level,
                "cwd": cwd,
                "timeout": float(timeout),
                "state": "queued",
                "cancel_requested": False,
                "reason": "",
                "error": "",
                "output": None,
                "created_at": now,
                "updated_at": now,
                "started_at": "",
                "terminal_at": "",
            }
            self._runs.append(rec)
            self._by_client[client_request_id] = rec["run_id"]
            self._persist_locked()
            return self._public_locked(rec)

    enqueue = submit

    def claim_next(self):
        with self._lock:
            if any(r["state"] == "running" for r in self._runs):
                return None
            for rec in self._runs:
                if rec["state"] != "queued":
                    continue
                now = _now_iso()
                rec["state"] = "running"
                rec["started_at"] = now
                rec["updated_at"] = now
                self._persist_locked()
                return self._public_locked(rec)
            return None

    def cancel(self, run_id, reason="user_cancel"):
        _req(reason, "reason", allow_empty=True)
        with self._lock:
            rec = self._find_locked(run_id)
            state = rec["state"]
            now = _now_iso()
            if state == "queued":
                rec.update(
                    state="cancelled",
                    cancel_requested=True,
                    reason=reason or "queue_cancelled",
                    terminal_at=now,
                    updated_at=now,
                )
                self._persist_locked()
                return self._public_locked(rec)
            if state == "running":
                rec.update(cancel_requested=True, reason=reason, updated_at=now)
                self._persist_locked()
                return self._public_locked(rec)
            return self._public_locked(rec)

    def finish(self, run_id, status, *, reason="", error="", output=None):
        if status not in TERMINAL_STATES:
            raise ValueError("finish status 须为 done/failed/cancelled")
        _req(reason, "reason", allow_empty=True)
        _req(error, "error", allow_empty=True)
        with self._lock:
            rec = self._find_locked(run_id)
            cur = rec["state"]
            if cur in TERMINAL_STATES:
                if cur == status:
                    return self._public_locked(rec)
                raise InvalidTransition(f"终态不可重开：{cur} -> {status}")
            if cur == "queued" and status != "cancelled":
                raise InvalidTransition("queued 只能 finish 为 cancelled")
            now = _now_iso()
            rec.update(state=status, reason=reason, error=error, terminal_at=now, updated_at=now)
            if output is not None:
                rec["output"] = output
            self._persist_locked()
            return self._public_locked(rec)

    def cancel_all_queued(self, reason="shutdown"):
        _req(reason, "reason", allow_empty=True)
        with self._lock:
            now = _now_iso()
            out = []
            for rec in self._runs:
                if rec["state"] == "queued":
                    rec.update(
                        state="cancelled",
                        cancel_requested=True,
                        reason=reason or "shutdown",
                        terminal_at=now,
                        updated_at=now,
                    )
                    out.append(self._public_locked(rec))
            if out:
                self._persist_locked()
            return out

    # ---------- 持久化 ----------
    def reload(self):
        with self._lock:
            self._runs = []
            self._by_client = {}
            self._load()

    def restore(self):
        self.reload()
        return self

    def _load(self):
        if not self.path.is_file():
            return
        try:
            doc = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise QueueCorrupt(f"队列文件不可解：{type(exc).__name__}")
        if not isinstance(doc, dict) or doc.get("schema_version") != SCHEMA_VERSION:
            raise QueueCorrupt("队列文件 schema 不合")
        runs = doc.get("runs")
        if not isinstance(runs, list):
            raise QueueCorrupt("runs 须为列表")
        now = _now_iso()
        changed = False
        for item in runs:
            if not isinstance(item, dict) or not _text(item.get("run_id")):
                raise QueueCorrupt("run 记录形坏")
            rec = dict(item)
            if rec.get("state") not in STATES:
                raise QueueCorrupt("run state 非法")
            rec.setdefault("cancel_requested", False)
            rec.setdefault("reason", "")
            rec.setdefault("error", "")
            rec.setdefault("output", None)
            rec.setdefault("started_at", "")
            rec.setdefault("terminal_at", "")
            if rec["state"] == "running":
                rec.update(
                    state="failed",
                    error="process_restart",
                    reason="进程重启：旧 running 未收敛",
                    terminal_at=now,
                    updated_at=now,
                )
                changed = True
            self._runs.append(rec)
            cid = rec.get("client_request_id")
            if _text(cid):
                self._by_client[cid] = rec["run_id"]
        if changed:
            self._persist_locked()

    def _persist_locked(self):
        payload = {
            "schema_version": SCHEMA_VERSION,
            "updated_at": _now_iso(),
            "runs": [self._public_locked(r) for r in self._runs],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8", newline=chr(10)) as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=1)
                fh.write(chr(10))
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass

    # ---------- 内部 ----------
    def _find_locked(self, run_id):
        for rec in self._runs:
            if rec["run_id"] == run_id:
                return rec
        raise RunNotFound(f"run_id 不存在：{run_id}")

    def _queued_locked(self):
        return [r for r in self._runs if r["state"] == "queued"]

    def _position_locked(self, run_id):
        for i, rec in enumerate(self._queued_locked(), 1):
            if rec["run_id"] == run_id:
                return i
        return 0

    def _public_locked(self, rec):
        out = dict(rec)
        out["position"] = self._position_locked(rec["run_id"]) if rec["state"] == "queued" else 0
        return out


RunQueue = AsyncRunQueue

__all__ = [
    "SCHEMA_VERSION",
    "QUEUE_PATH_ENV",
    "DEFAULT_QUEUE_PATH",
    "STATES",
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "MAX_QUEUED_PER_SESSION",
    "MAX_QUEUED",
    "AsyncQueueError",
    "QueueFull",
    "RunNotFound",
    "InvalidTransition",
    "QueueCorrupt",
    "default_queue_path",
    "AsyncRunQueue",
    "RunQueue",
]
