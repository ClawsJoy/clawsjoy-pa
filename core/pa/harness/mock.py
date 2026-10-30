# -*- coding: utf-8 -*-
u"""MockHarness —— HarnessPort v1 之**测试／H1**适配器（in-process · 确定性 · 零外依）。

【边界（§四.1 ／ H5）】⛔ import dsh ／ paseo ／ obsidian；⛔ 起进程；⛔ 触网；⛔ 写盘。
  本件只造「接口之形 ＋ canonical 记录」，并按 §四.4 显式 `history_replay=False`。

【H1 之流】run(RunSpec) ⇒ 同步跑完（mock 任务）⇒ canonical `RunRecord` 落 PA 侧 `RunLedger`
  （内存）⇒ 返 `RunHandle`（run_id ／ session_id ／ 本次增量）。随后 `cost` ／ `audit` ／
  `stream` 皆自该记录读（⛔ 另取）。

【⛔ 越界】本 adapter 之 session 格式（`mock-v1`）只存 `harness_meta`，⛔ 升格为 PA 账字段；
  PA 账 schema 见 `port.RUN_RECORD_FIELDS`（H4：换 adapter ／ 换 session 版本皆 ⛔ 改）。
"""

from __future__ import annotations

import threading
import uuid

from core.pa.harness.port import (
    AuditResult,
    Cost,
    PermissionState,
    ProbeResult,
    RunHandle,
    RunLedger,
    RunRecord,
    RunSpec,
    StreamEvent,
    TeamState,
    UnknownRun,
    UnknownSession,
    _now_iso,
)

MOCK_VERSION = "mock-1.0.0"

MOCK_SESSION_FORMAT = "mock-v1"


class MockHarness:
    u"""HarnessPort 之测试实现：一分任务之入 ⇒ 一 canonical `RunRecord` 之出（＋增量）。

    `ledger` 可注入（与 PA 侧共用一本账）；缺省自立内存账。`fail=True` 造失败终态；
    `script` 为附加日志（⛔ 真执行 —— mock 之「任务」是**定造**，⛔ 充实测）。
    """

    name = "mock"

    def __init__(self, ledger=None, *, fail=False, script="", model="mock-model",
                 version=MOCK_VERSION):
        if ledger is None:
            ledger = RunLedger()
        if not isinstance(ledger, RunLedger):
            raise ValueError("MockHarness.ledger 须为 RunLedger（今 %s）" % type(ledger).__name__)
        self.ledger = ledger
        self.fail = bool(fail)
        self.script = str(script)
        self.model = str(model)
        self.version = str(version)
        self._lock = threading.RLock()
        self._events = {}
        self._handles = {}
        self._sessions = {}
        self._finished = set()

    def __repr__(self):
        return "<MockHarness version=%s runs=%d>" % (self.version, self.ledger.count())

    # ---------------------------- 探 ----------------------------

    def probe(self):
        u"""in-process 之「可用」＝ 真（⛔ 外依）；版本与刻照实出（⛔ 谎报外部能力）。"""
        return ProbeResult(
            harness=self.name,
            available=True,
            version=self.version,
            at=_now_iso(),
            detail="in-process mock（⛔ 起进程 · ⛔ 触网 · ⛔ 写盘）",
            meta={"external": False, "session_format": MOCK_SESSION_FORMAT},
        )

    # ---------------------------- 跑 ----------------------------

    def run(self, spec):
        u"""同步跑一 mock 任务 ⇒ RunHandle；canonical RunRecord 落 `self.ledger`。

        `spec.resume_id` 有值 ⇒ 续该 session（须已知；否则 UnknownSession），并
        `history_replay=False`。⛔ 回放历史（§四.4）：PA 用自有回执／摘要补。
        """
        spec = RunSpec.from_any(spec)
        with self._lock:
            started_at = _now_iso()
            run_id = "pa-run-%s" % uuid.uuid4().hex[:12]
            resumed_from = ""
            if spec.resume_id:
                if spec.resume_id not in self._sessions:
                    raise UnknownSession("MockHarness 无此 session：%r" % (spec.resume_id,))
                session_id = spec.resume_id
                resumed_from = self._sessions[session_id]
            else:
                session_id = "mock-sess-%s" % uuid.uuid4().hex[:12]

            status = "failed" if self.fail else "ok"
            events = []

            def _emit(kind, text, data=None):
                events.append(StreamEvent(
                    run_id=run_id, seq=len(events) + 1, at=_now_iso(),
                    kind=kind, text=text, data=data or {},
                ))

            _emit("start", "mock: run 起（session_format=%s · history_replay=False）"
                  % MOCK_SESSION_FORMAT, {"model": spec.model or self.model})
            _emit("log", "mock: task %d 字 · tools=%d · permission_level=%s"
                  % (len(spec.task), len(spec.tools), spec.permission_level or "-"))
            if self.script:
                _emit("log", "mock: script=%s" % self.script)
            if status == "ok":
                _emit("done", "mock: 任务完成（同步 · 定造）")
            else:
                _emit("error", "mock: 任务失败（fail=True 之定造）")
            ended_at = _now_iso()

            record = RunRecord(
                run_id=run_id,
                harness=self.name,
                session_id=session_id,
                model=spec.model or self.model,
                cwd=spec.cwd,
                started_at=started_at,
                ended_at=ended_at,
                status=status,
                cost=Cost(tokens=len(spec.task), cny=0.0, turns=1),
                artifacts=(),
                harness_meta={
                    "mock": True,
                    "version": self.version,
                    "session_format": MOCK_SESSION_FORMAT,
                    "history_replay": False,
                    "resume_from": resumed_from,
                    "fail": self.fail,
                    "script": self.script,
                    "tools": list(spec.tools),
                    "permission_level": spec.permission_level,
                    "timeout": float(spec.timeout),
                },
            )
            self.ledger.append(record)
            handle = RunHandle(
                run_id=run_id,
                session_id=session_id,
                harness=self.name,
                history_replay=False,
                stream=tuple(events),
            )
            self._events[run_id] = tuple(events)
            self._handles[run_id] = handle
            self._sessions[session_id] = run_id
            self._finished.add(run_id)
            return handle

    # ---------------------------- 续 ----------------------------

    def resume(self, session_id):
        u"""续会话之**柄**（⛔ 跑任务 ⇒ ⛔ 落 RunRecord；下一 `run(spec.resume_id=...)` 方落账）。

        历史不回放 ⇒ `history_replay=False` **显式**（§四.4）。
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("resume(session_id) 须为非空字符串")
        with self._lock:
            if session_id not in self._sessions:
                raise UnknownSession("MockHarness 无此 session：%r" % (session_id,))
            run_id = "pa-run-%s" % uuid.uuid4().hex[:12]
            handle = RunHandle(
                run_id=run_id,
                session_id=session_id,
                harness=self.name,
                history_replay=False,
                stream=(),
            )
            self._handles[run_id] = handle
            self._events[run_id] = ()
            return handle

    # ---------------------------- 停 ----------------------------

    def cancel(self, run_id):
        u"""MockHarness **同步**执行 ⇒ 无「在跑」窗口：已知之 run 必已结束 ⇒ 恒 False（⛔ 谎报已停）。

        未知 run ⇒ UnknownRun（⛔ 以 False 充「不存在」）。
        """
        with self._lock:
            if run_id not in self._handles:
                raise UnknownRun("MockHarness 无此 run_id：%r" % (run_id,))
            return False

    # ---------------------------- 增量 ----------------------------

    def stream(self, run_id):
        u"""本次之增量（seq 单调 · 只读快照）。"""
        with self._lock:
            if run_id not in self._events:
                raise UnknownRun("MockHarness 无此 run_id：%r" % (run_id,))
            return self._events[run_id]

    # ---------------------------- 门 ----------------------------

    def permissions(self):
        u"""门／级别／待批之**示范形**（⛔ 本件作授权源 —— 真门在 PA doors／policy）。"""
        return PermissionState(
            harness=self.name,
            level="mock",
            allowed_tools=("read_file", "list_dir"),
            pending=(),
            gates={"run": "allow", "write": "ask", "network": "deny", "spawn": "ask"},
            note="MockHarness 只示范门形；真授权在 PA doors/policy（⛔ 此件作授权源）",
        )

    # ---------------------------- 成本 ----------------------------

    def cost(self, run_id):
        u"""自 PA 账之 canonical 记录读成本（⛔ 另自 adapter 造数）。"""
        return self.ledger.get(run_id).cost

    # ---------------------------- 审计 ----------------------------

    def audit(self, run_id):
        u"""回执（canonical sha16）／产物／harness meta —— 皆自 PA 账。"""
        rec = self.ledger.get(run_id)
        return AuditResult(
            run_id=rec.run_id,
            status=rec.status,
            receipt_sha16=rec.receipt_sha16,
            artifacts=rec.artifacts,
            harness_meta=dict(rec.harness_meta),
            started_at=rec.started_at,
            ended_at=rec.ended_at,
        )

    # ---------------------------- 团队（可选） ----------------------------

    def team(self):
        u"""**可选**能力：MockHarness v1 ⛔ team ⇒ 显式 available=False ＋ reason（⛔ 静默替身）。"""
        return TeamState(
            harness=self.name,
            available=False,
            reason="MockHarness v1 ⛔ team 能力（可选面 · 真实现见 adapter）",
            meta={"optional": True},
        )
