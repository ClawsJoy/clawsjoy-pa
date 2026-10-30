"""PA AsyncRunQueue 核心（P0-2a · 不接路由/worker）。

实现设计 docs/design/PA_ASYNC_TWO_LANE_v1.md 的队列层：

  · 六态：queued / running / done / failed / cancelled（idle 不落 record）；
  · 全局 FIFO；execution claim_next() 全进程单执行权（调用方保证单 worker）；
  · per-session queued ≤3、全局 queued ≤20（超限 QueueFull）；
  · client_request_id 幂等（重复返回原 run，不重复入队）；
  · cancel：queued 立即 cancelled；running 仅置 cancel_requested（由 worker 收敛）；
  · finish：done/failed/cancelled 终态，终态幂等；
  · position 1-based 派生并随队列重排；
  · 持久化 env PA_ASYNC_QUEUE_PATH 或 data/v9/pa/async_queue.json，
    原子写（tmp + os.replace，schema_version=1）；restore 时旧 running→failed
    process_restart、queued 保留。

只读/写入边界：本件只写自己的 queue path；不 import 路由/聊天/DSH。
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

#: 六态（idle 为车道空闲，不落 record）
STATES = ("queued", "running", "done", "failed", "cancelled")
ACTIVE_STATES = ("queued", "running")
TERMINAL_STATES = ("done", "failed", "cancelled")

MAX_QUEUED_PER_SESSION = 3
MAX_QUEUED = 20


class AsyncQueueError(Exception):
    """队列层之基错。"""


class QueueFull(AsyncQueueError):
    """背压：per-session queued 或全局 queued 超限。"""

    def __init__(self, message, session_queued=0, global_queued=0):
        super().__init__(message)
        self.session_queued = int(session_queued)
        self.global_queued = int(global_queued)


class RunNotFound(AsyncQueueError):
    """run_id 不存在。"""


class InvalidTransition(AsyncQueueError):
    """非法状态转移（终态不可重开等）。"""


class QueueCorrupt(AsyncQueueError):
    """队列文件坏件（fail-loud，⛔ 静默清空）。"""


def _now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _require_text(value, name, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError(f"{name} 须为字符串（今 {type(value).__name__}）")
    if not allow_empty and not value.strip():
        raise ValueError(f"{name} 须为非空字符串")
    return value


def default_queue_path():
    """队列径：env PA_ASYNC_QUEUE_PATH > data/v9/pa/async_queue.json。"""
    raw = (os.environ.get(QUEUE_PATH_ENV) or "").strip()
    return Path(raw) if raw else DEFAULT_QUEUE_PATH


class AsyncRunQueue:
    """单进程、线程安全的 AsyncRunQueue。

    用法：
      q = AsyncRunQueue()                         # 默认持久化径
      q = AsyncRunQueue(path=tmp_path/q.json)     # 测试/隔离
      rec = q.submit(session_id=..., user_id=..., client_request_id=..., task=...)
      rec = q.claim_next()                        # 返回 running record 或 None
      q.finish(rec["run_id"], "done", output="...")
    """

    def __init__(self, path=None):
        raw = path if path is not None else default_queue_path()
        self.path = Path(raw)
        self._lock = threading.RLock()
        self._runs = []  # list[dict]，顺序＝创建顺序（queued FIFO 依此过滤）
        self._by_client = {}  # client_request_id -> run_id
        self._load()

    # ---------------- 读面 ----------------

    def get(self, run_id):
        """按 run_id 取公开记录（含派生 position）；未知 ⇒ RunNotFound。"""
        with self._lock:
            rec = self._find_locked(run_id)
            return self._public_locked(rec)

    get_run = get

    def by_client_request_id(self, client_request_id):
        """按幂等键取公开记录；无 ⇒ None。"""
        with self._lock:
            rid = self._by_client.get(str(client_request_id))
            if rid is None:
                return None
            return self._public_locked(self._find_locked(rid))

    def position(self, run_id):
        """queued ⇒ 1-based 位置；running/终态 ⇒ 0。"""
        with self._lock:
            rec = self._find_locked(run_id)
            if rec.get("state") != "queued":
                return 0
            return self._position_locked(rec["run_id"])

    def queue_depth(self):
        with self._lock:
            return sum(1 for r in self._runs if r.get("state") == "queued")

    def running_run(self):
        with self._lock:
            for r in self._runs:
                if r.get("state") == "running":
                    return self._public_locked(r)
            return None

    def list_runs(self, state=None, session_id=None):
        """列公开记录；state/session_id 可选过滤（按创建顺序）。"""
        with self._lock:
            out = []
            for r in self._runs:
                if state is not None and r.get("state") != state:
                    continue
                if session_id is not None and r.get("session_id") != session_id:
                    continue
                out.append(self._public_locked(r))
            return out

    def snapshot(self):
        with self._lock:
            return {
                "schema_version": SCHEMA_VERSION,
                "queue_depth": self.queue_depth(),
                "running": self.running_run(),
                "runs": [self._public_locked(r) for r in self._runs],
            }

    # ---------------- 写面：submit ----------------

    def submit(
        self, *, session_id, user_id, client_request_id, task, model="", permission_level="", cwd="", timeout=0.0
    ):
        """受理一个执行请求 ⇒ queued record。

        · client_request_id 已存在 ⇒ 原 record（幂等，⛔ 重复入队）；
        · queued 背压：per-session >3 或全局 >20 ⇒ QueueFull；
        · 此层 ⛔ 自动 claim；worker 调 claim_next() 取头。
        """
        _require_text(session_id, "session_id")
        _require_text(user_id, "user_id")
        _require_text(client_request_id, "client_request_id")
        _require_text(task, "task")
        _require_text(model, "model", allow_empty=True)
        _require_text(permission_level, "permission_level", allow_empty=True)
        _require_text(cwd, "cwd", allow_empty=True)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("timeout 须为数值")
        if timeout < 0:
            raise ValueError("timeout 禁止为负")
        with self._lock:
            existing = self._by_client.get(client_request_id)
            if existing is not None:
                return self._public_locked(self._find_locked(existing))
            queued = [r for r in self._runs if r.get("state") == "queued"]
            sess_n = sum(1 for r in queued if r.get("session_id") == session_id)
            if sess_n >= MAX_QUEUED_PER_SESSION:
                raise QueueFull(
                    f"session queued 已达上限 {MAX_QUEUED_PER_SESSION}（session={session_id}）",
                    sess_n,
                    len(queued),
                )
            if len(queued) >= MAX_QUEUED:
                raise QueueFull(f"全局 queued 已达上限 {MAX_QUEUED}", sess_n, len(queued))
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

    # ---------------- 写面：claim / finish / cancel ----------------

    def claim_next(self):
        """取 FIFO 头 ⇒ running；已有 running ⇒ None（单执行权）。

        只改状态，不执行任务；worker 必须在本进程内串行调用。
        """
        with self._lock:
            if any(r.get("state") == "running" for r in self._runs):
                return None
            for rec in self._runs:  # 创建顺序中的首个 queued = FIFO 头
                if rec.get("state") != "queued":
                    continue
                now = _now_iso()
                rec["state"] = "running"
                rec["started_at"] = now
                rec["updated_at"] = now
                rec["cancel_requested"] = bool(rec.get("cancel_requested", False))
                self._persist_locked()
                return self._public_locked(rec)
            return None

    def cancel(self, run_id, reason="user_cancel"):
        """取消：queued 立即 cancelled；running 置 cancel_requested；终态幂等。"""
        _require_text(reason, "reason", allow_empty=True)
        with self._lock:
            rec = self._find_locked(run_id)
            state = rec.get("state")
            now = _now_iso()
            if state == "queued":
                rec["state"] = "cancelled"
                rec["cancel_requested"] = True
                rec["reason"] = reason or "queue_cancelled"
                rec["terminal_at"] = now
                rec["updated_at"] = now
                self._persist_locked()
                return self._public_locked(rec)
            if state == "running":
                rec["cancel_requested"] = True
                rec["reason"] = reason
                rec["updated_at"] = now
                self._persist_locked()
                return self._public_locked(rec)
            # terminal：幂等；⛔ 重开
            return self._public_locked(rec)

    def finish(self, run_id, status, *, reason="", error="", output=None):
        """落终态：done/failed/cancelled；queued 仅允许 cancelled；终态幂等。"""
        if status not in TERMINAL_STATES:
            raise ValueError(f"finish status 须为 done/failed/cancelled（今 {status!r}）")
        _require_text(reason, "reason", allow_empty=True)
        _require_text(error, "error", allow_empty=True)
        with self._lock:
            rec = self._find_locked(run_id)
            cur = rec.get("state")
            if cur in TERMINAL_STATES:
                if cur == status:
                    return self._public_locked(rec)  # 幂等
                raise InvalidTransition(f"终态不可重开：{cur} -> {status}")
            if cur == "queued" and status != "cancelled":
                raise InvalidTransition(f"queued 只能 finish 为 cancelled（今 {status}）")
            now = _now_iso()
            rec["state"] = status
            rec["reason"] = reason
            rec["error"] = error
            if output is not None:
                rec["output"] = output
            rec["terminal_at"] = now
            rec["updated_at"] = now
            self._persist_locked()
            return self._public_locked(rec)

    def cancel_all_queued(self, reason="shutdown"):
        """停机/清理：所有 queued ⇒ cancelled（running 保持，由 worker 收尾）。"""
        _require_text(reason, "reason", allow_empty=True)
        with self._lock:
            now = _now_iso()
            out = []
            for rec in self._runs:
                if rec.get("state") == "queued":
                    rec["state"] = "cancelled"
                    rec["cancel_requested"] = True
                    rec["reason"] = reason or "shutdown"
                    rec["terminal_at"] = now
                    rec["updated_at"] = now
                    out.append(self._public_locked(rec))
            if out:
                self._persist_locked()
            return out

    # ---------------- 持久化 / 恢复 ----------------

    def reload(self):
        """从盘重载（测试/多实例只读场景）；会再走 restore 规则。"""
        with self._lock:
            self._runs = []
            self._by_client = {}
            self._load()

    def _load(self):
        path = self.path
        if not path.is_file():
            return
        try:
            raw = path.read_text(encoding="utf-8")
            doc = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            raise QueueCorrupt(f"队列文件不可解：{type(exc).__name__}: {exc}")
        if not isinstance(doc, dict):
            raise QueueCorrupt("队列文件非对象")
        ver = doc.get("schema_version")
        if ver != SCHEMA_VERSION:
            raise QueueCorrupt(f"schema_version 不符：{ver!r} != {SCHEMA_VERSION!r}")
        runs = doc.get("runs")
        if not isinstance(runs, list):
            raise QueueCorrupt("runs 须为列表")
        self._runs = []
        self._by_client = {}
        changed = False
        now = _now_iso()
        for item in runs:
            if not isinstance(item, dict) or not _text(item.get("run_id")):
                raise QueueCorrupt(f"run 记录形坏：{item!r}")
            rec = dict(item)
            state = rec.get("state")
            if state not in STATES:
                raise QueueCorrupt(f"run state 非法：{state!r}")
            rec.setdefault("cancel_requested", False)
            rec.setdefault("reason", "")
            rec.setdefault("error", "")
            rec.setdefault("output", None)
            rec.setdefault("started_at", "")
            rec.setdefault("terminal_at", "")
            if state == "running":
                # 重启：旧 running 不可能仍在执行 ⇒ failed process_restart（⛔ 自动重跑）
                rec["state"] = "failed"
                rec["error"] = "process_restart"
                rec["reason"] = "进程重启：旧 running 未收敛"
                rec["terminal_at"] = now
                rec["updated_at"] = now
                changed = True
            self._runs.append(rec)
            cid = rec.get("client_request_id")
            if _text(cid):
                self._by_client[cid] = rec["run_id"]
        if changed:
            self._persist_locked()

    def _persist_locked(self):
        """原子写：tmp + os.replace；含 schema_version 与派生 position。"""
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

    # ---------------- 内部 ----------------

    def _find_locked(self, run_id):
        for rec in self._runs:
            if rec.get("run_id") == run_id:
                return rec
        raise RunNotFound(f"run_id 不存在：{run_id}")

    def _queued_locked(self):
        return [r for r in self._runs if r.get("state") == "queued"]

    def _position_locked(self, run_id):
        for i, rec in enumerate(self._queued_locked(), 1):
            if rec.get("run_id") == run_id:
                return i
        return 0

    def _public_locked(self, rec):
        out = dict(rec)
        out["position"] = self._position_locked(rec["run_id"]) if rec.get("state") == "queued" else 0
        return out


#: 兼容别名（实现方可用 RunQueue 名称）
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
