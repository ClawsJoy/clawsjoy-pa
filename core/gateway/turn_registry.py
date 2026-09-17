# -*- coding: utf-8 -*-
"""turn 持久注册表（P0-2，2026-09-13）。

为什么必须持久：此前 turn 的取消/超时状态全在内存（shared_state 的 _cancel_flags），
网关一重启，正在跑的 turn 就「没有终态」——用户回来看到的是空白，不知道是失败了、
还在跑、还是丢了。本模块给每个 turn 一条持久记录，重启后靠心跳扫描判成 STALE。

键用 uuid4 而不是时间戳：现有 loop.py:142 用 int(time.time()) 生成 turn_id，
秒级、同秒两个 turn 会撞号。它在今天是「关联标签」不是唯一键（全仓无 turn_id 作索引的用法），
但一旦建表就会变成主键 → 必须换 uuid4。turn_id 保留为可读标签。

心跳必须异步/批量：SSE 热路径上每 5s 写一次库会拖慢流；且 tool_timeout_ms=320000
（大于 5 分钟 STALE 阈值）意味着长工具期可能长时间没有心跳，所以心跳由独立线程批量落库，
且阈值要留足余量（默认 900s）。

状态机（7 态）：
  CREATED → RUNNING → {COMPLETED, FAILED, CANCELLED, DETACHED}
  RUNNING → STALE（重启后扫描：心跳超时）
  DETACHED → {RUNNING, CANCELLED, STALE}
"""
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

DB_PATH = os.getenv("V9_TURN_DB", "data/v9/turns.db")
STALE_AFTER_SEC = int(os.getenv("V9_TURN_STALE_SEC", "900"))
HEARTBEAT_FLUSH_SEC = 2.0

STATUSES = ("CREATED", "RUNNING", "DETACHED", "COMPLETED", "FAILED", "CANCELLED", "STALE")
TERMINAL = ("COMPLETED", "FAILED", "CANCELLED")
MODES = ("interactive", "background", "budget_protected")
ALLOWED = {
    "CREATED": {"RUNNING", "FAILED", "CANCELLED"},
    "RUNNING": {"DETACHED", "COMPLETED", "FAILED", "CANCELLED", "STALE"},
    "DETACHED": {"RUNNING", "CANCELLED", "STALE", "COMPLETED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
    "STALE": {"CANCELLED", "RUNNING"},
}

_LOCK = threading.Lock()
_pending_hb = set()
_flusher_started = False


def _db_path():
    p = Path(DB_PATH)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def _conn():
    c = sqlite3.connect(_db_path(), timeout=5)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    """建表 + 索引（幂等）。"""
    with _LOCK, _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS turns(
            turn_key TEXT PRIMARY KEY,
            turn_id INTEGER,
            session_id TEXT, user_id TEXT, task_id TEXT,
            mode TEXT DEFAULT 'interactive',
            status TEXT DEFAULT 'CREATED',
            created_at REAL, updated_at REAL, heartbeat_at REAL,
            worker_id TEXT, reason TEXT, meta TEXT
        )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_turns_status_hb ON turns(status, heartbeat_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, updated_at)")
    return True


def _now():
    return time.time()


def create_turn(session_id, user_id="", task_id="", mode="interactive", worker_id=""):
    """新建 turn。契约：返回 turn_key(uuid4 字符串)；mode 非法时退回 interactive。"""
    init_db()
    key = uuid.uuid4().hex
    if mode not in MODES:
        mode = "interactive"
    t = _now()
    with _LOCK, _conn() as c:
        c.execute(
            "INSERT INTO turns(turn_key, turn_id, session_id, user_id, task_id, mode, status,"
            " created_at, updated_at, heartbeat_at, worker_id, reason, meta)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (key, int(t), session_id, user_id, task_id, mode, "RUNNING", t, t, t, worker_id or os.getpid(), "", ""),
        )
    _start_flusher()
    return key


def heartbeat(turn_key, status=None):
    """同步写一次心跳（测试与收尾用）。"""
    t = _now()
    with _LOCK, _conn() as c:
        if status:
            c.execute(
                "UPDATE turns SET heartbeat_at=?, updated_at=?, status=? WHERE turn_key=?", (t, t, status, turn_key)
            )
        else:
            c.execute("UPDATE turns SET heartbeat_at=?, updated_at=? WHERE turn_key=?", (t, t, turn_key))
    return True


def heartbeat_async(turn_key):
    """热路径用：只入队，由后台线程批量落库（SSE 每 5s 调一次也不拖慢流）。"""
    _pending_hb.add(turn_key)
    _start_flusher()
    return True


def _flush_once():
    with _LOCK:
        keys = list(_pending_hb)
        _pending_hb.clear()
    if not keys:
        return 0
    t = _now()
    try:
        with _LOCK, _conn() as c:
            for k in keys:
                c.execute("UPDATE turns SET heartbeat_at=?, updated_at=? WHERE turn_key=?", (t, t, k))
    except Exception:
        return 0
    return len(keys)


def _start_flusher():
    global _flusher_started
    if _flusher_started:
        return
    _flusher_started = True

    def _loop():
        while True:
            time.sleep(HEARTBEAT_FLUSH_SEC)
            try:
                _flush_once()
            except Exception:
                pass

    threading.Thread(target=_loop, daemon=True, name="turn-hb-flusher").start()


def _transition(turn_key, to_status, reason=""):
    """按 ALLOWED 转移；非法转移返回 False 且不改库（防状态乱跳）。"""
    if to_status not in STATUSES:
        return False
    with _LOCK, _conn() as c:
        row = c.execute("SELECT status FROM turns WHERE turn_key=?", (turn_key,)).fetchone()
        if row is None:
            return False
        cur = row["status"]
        if cur == to_status:
            return True
        if to_status not in ALLOWED.get(cur, set()):
            return False
        c.execute(
            "UPDATE turns SET status=?, updated_at=?, reason=? WHERE turn_key=?",
            (to_status, _now(), str(reason)[:300], turn_key),
        )
    return True


def detach_turn(turn_key, reason="客户端断开"):
    return _transition(turn_key, "DETACHED", reason)


def finish_turn(turn_key, status="COMPLETED", reason=""):
    """收尾。status 取 COMPLETED / FAILED / CANCELLED 之一，非法值按 FAILED。"""
    if status not in TERMINAL:
        status = "FAILED"
    return _transition(turn_key, status, reason)


def scan_stale(now=None, stale_after=STALE_AFTER_SEC):
    """启动扫描：RUNNING/DETACHED 且心跳超时 → STALE。

    契约：返回被标 STALE 的列表 [{turn_key, session_id, status, age_sec, reason}]。
    不自动续跑（memory / tool state / external side effect 都可能已丢），交用户三选一。
    """
    init_db()
    t = now if now is not None else _now()
    cutoff = t - int(stale_after)
    out = []
    with _LOCK, _conn() as c:
        rows = c.execute(
            "SELECT turn_key, session_id, user_id, mode, status, heartbeat_at"
            " FROM turns WHERE status IN ('RUNNING','DETACHED') AND heartbeat_at < ?",
            (cutoff,),
        ).fetchall()
        for r in rows:
            c.execute(
                "UPDATE turns SET status='STALE', updated_at=?, reason=? WHERE turn_key=?",
                (t, "心跳超时(%ds)无更新" % int(stale_after), r["turn_key"]),
            )
            out.append(
                {
                    "turn_key": r["turn_key"],
                    "session_id": r["session_id"],
                    "status": r["status"],
                    "age_sec": round(t - (r["heartbeat_at"] or 0), 1),
                    "reason": "心跳超时",
                }
            )
    return out


def get_turn(turn_key):
    init_db()
    with _LOCK, _conn() as c:
        r = c.execute("SELECT * FROM turns WHERE turn_key=?", (turn_key,)).fetchone()
        return dict(r) if r else None


def list_turns(session_id=None, limit=20):
    init_db()
    with _LOCK, _conn() as c:
        if session_id:
            rows = c.execute(
                "SELECT * FROM turns WHERE session_id=? ORDER BY updated_at DESC LIMIT ?", (session_id, int(limit))
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM turns ORDER BY updated_at DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]


def active_turns(stale_after=STALE_AFTER_SEC, limit=10):
    """批189 · #6：返回**仍活跃**的回合（RUNNING/DETACHED 且心跳未超时）。

    用途：网关入口的「单活动 run」守卫（PA 单线程 ⇒ 后端不得允许多个活动 run）。
    心跳超时的回合视为 STALE，不计入（防崩溃回合永久阻塞）。
    """
    _cut = _now() - int(stale_after)
    out = []
    try:
        c = _conn()
        try:
            rows = c.execute(
                "SELECT turn_key, session_id, user_id, status, heartbeat_at, updated_at"
                " FROM turns WHERE status IN ('RUNNING','DETACHED') AND heartbeat_at >= ?"
                " ORDER BY heartbeat_at DESC LIMIT ?",
                (_cut, int(limit)),
            ).fetchall()
        finally:
            c.close()
        for r in rows:
            out.append(
                {
                    "turn_key": r[0],
                    "session_id": r[1],
                    "user_id": r[2],
                    "status": r[3],
                    "heartbeat_at": r[4],
                    "updated_at": r[5],
                }
            )
    except Exception:
        return []
    return out


def reset_for_test():
    """测试用：清空表。"""
    init_db()
    with _LOCK, _conn() as c:
        c.execute("DELETE FROM turns")
    _pending_hb.clear()
    return True
