# -*- coding: utf-8 -*-
u"""PA HarnessPort v1 —— PA 核心 ⇄ harness 之**唯一**接口面（依赖倒置之落点）。

【本件解决什么】（承 docs/reports/_pa_groundwork_20261027/62_PA_HarnessPort_v1.md）
  PA core（registry ／ ledger ／ vault ／ doors ／ policy ／ memory ／ Today ／ Focus）只依赖
  **本件**；DSH ／ Codex ／ Claude ／ API ／ Paseo ／ Mock 皆在此接口**之下**作 adapter。
  ⇒ harness 之私有 session 格式（v3/v4）、并发锁、GUI 变更，⛔ 传导进 PA 账。

【最小面（§二）】probe ／ run ／ resume ／ cancel ／ stream ／ permissions ／ cost ／ audit ／ team?
  · run(spec)：spec ＝ task, cwd, tools, permission_level, timeout, model, resume_id；
  · resume：不回放历史者须**显式** `history_replay=False`（§四.4）；
  · team：**可选**能力；不支持者须显式 `TeamState(available=False, reason=...)`（⛔ 静默造替身）。

【canonical 记录归 PA（§三）】`RunRecord` 之字段即 PA 账 schema（H4 之基）：
  run_id ／ harness ／ session_id ／ model ／ cwd ／ started_at ／ ended_at ／ status ／
  cost{tokens,cny,turns} ／ artifacts[] ／ receipt_sha16 ／ harness_meta{}。
  `harness_meta` 为**唯一**容纳 harness 私有物之处（session 格式等）；⛔ 升格为 PA 账真源。

【依赖边界（§四.1 ／ H5）】本件**唯 stdlib**：⛔ import dsh ／ paseo ／ obsidian，⛔ 起进程、触网。
  adapter 在 `core/pa/harness/` 之下另立件（如 `mock.py`；日後 `dsh.py` ／ `paseo.py`），
  且 ⛔ 由 `core/pa/harness/__init__.py` 隐式引入。

【H1】`MockHarness` 跑一任务 ⇒ canonical `RunRecord` 落 PA 侧 `RunLedger`（内存）· 无 DSH import。
  `RunLedger` 之 `dump()` 即「交 PA ledger／vault」之可序列化形；真落件／落库为后续期。
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

PA_HARNESS_PORT_VERSION = "v1"

#: run 之终态（⛔ 增：PA 账 schema 之枚举 —— 增须随 §三 同步；H4）
RUN_STATUSES = ("ok", "failed", "cancelled")

#: stream 事件之类（"增量输出"之最小枚举；adapter 可只用 log ／ stdout ／ stderr）
STREAM_KINDS = ("start", "log", "stdout", "stderr", "artifact", "done", "error")

#: permissions 之门值（必显式：allow ／ ask ／ deny —— ⛔ 布尔二义）
PERMISSION_GATES = ("allow", "ask", "deny")

#: canonical RunRecord 之字段名（H4：此集即 PA 账 schema；序同 §三 之例）
RUN_RECORD_FIELDS = (
    "run_id", "harness", "session_id", "model", "cwd", "started_at", "ended_at",
    "status", "cost", "artifacts", "receipt_sha16", "harness_meta",
)

#: run(spec) 之 spec 字段（§二）
RUN_SPEC_FIELDS = ("task", "cwd", "tools", "permission_level", "timeout", "model", "resume_id")

#: HarnessPort 之方法名（H5 之面集；team 为可选）
HARNESS_METHODS = (
    "probe", "run", "resume", "cancel", "stream", "permissions", "cost", "audit", "team",
)

_SHA16_RE = re.compile(r"^[0-9a-f]{16}$")


# ============================ 小工具（一处定形） ============================

def _now_iso():
    u"""此刻之 ISO 8601（本机时区）—— PA 账之刻（⛔ 各 adapter 各造格式）。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def canonical_json(payload):
    u"""canonical JSON（键序定 · 紧凑）—— receipt 之唯一料（⛔ 逐 adapter 各序）。"""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha16(payload):
    u"""canonical sha256 前 16 位（承 `agent_scan` 之 `sha16` 同形）。bytes ／ str ／ 可 JSON 者皆可。"""
    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
    elif isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _req_str(value, name, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s 须为字符串（今 %s）" % (name, type(value).__name__))
    if not allow_empty and not value.strip():
        raise ValueError("%s 须为非空字符串" % name)
    return value


def _str_tuple(value, name):
    if value is None:
        return ()
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Iterable):
        raise ValueError("%s 须为字符串之序列（今 %s）" % (name, type(value).__name__))
    out = tuple(value)
    if any(not isinstance(x, str) for x in out):
        raise ValueError("%s 须逐项为字符串" % name)
    return out


def _mapping(value, name):
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("%s 须为 mapping（今 %s）" % (name, type(value).__name__))
    return dict(value)


# ============================ 异常（可分辨 · ⛔ 静默） ============================

class HarnessError(Exception):
    u"""harness 层之基错（PA 侧可辨「接口之错」⇔「任务之败」）。"""


class UnknownRun(HarnessError):
    u"""run_id 不在 PA 账（⛔ 以空记录冒充「已查」）。"""


class UnknownSession(HarnessError):
    u"""session_id 不在本 adapter 之知（⛔ 假续）。"""


class UnsupportedCapability(HarnessError):
    u"""可选能力（如 team）不支持（adapter 亦可返 available=False 之态；二者须显式选一）。"""


# ============================ 数据类（唯一之「形」） ============================

@dataclass(frozen=True)
class RunSpec:
    u"""一次任务之入参（§二）：task ／ cwd ／ tools ／ permission_level ／ timeout ／ model ／ resume_id。"""

    task: str
    cwd: str = ""
    tools: tuple = ()
    permission_level: str = ""
    timeout: float = 0.0
    model: str = ""
    resume_id: str = ""

    def __post_init__(self):
        _req_str(self.task, "RunSpec.task")
        for _n in ("cwd", "permission_level", "model", "resume_id"):
            _req_str(getattr(self, _n), "RunSpec." + _n, allow_empty=True)
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float)):
            raise ValueError("RunSpec.timeout 须为数值（今 %s）" % type(self.timeout).__name__)
        if self.timeout < 0:
            raise ValueError("RunSpec.timeout ⛔ 为负")
        object.__setattr__(self, "tools", _str_tuple(self.tools, "RunSpec.tools"))

    @classmethod
    def from_any(cls, spec):
        u"""接 RunSpec ∨ mapping（路由／调用方常给 dict）；未知字段 ⇒ 显错（⛔ 静默吞）。"""
        if isinstance(spec, cls):
            return spec
        if not isinstance(spec, Mapping):
            raise ValueError("RunSpec 须为 RunSpec ∨ mapping（今 %s）" % type(spec).__name__)
        unknown = sorted(str(k) for k in spec if k not in RUN_SPEC_FIELDS)
        if unknown:
            raise ValueError("RunSpec 未知字段：%s" % ", ".join(unknown))
        if "task" not in spec:
            raise ValueError("RunSpec 缺 task")
        kw = {k: spec[k] for k in RUN_SPEC_FIELDS if k in spec and spec[k] is not None}
        return cls(**kw)

    def to_dict(self):
        return {
            "task": self.task,
            "cwd": self.cwd,
            "tools": list(self.tools),
            "permission_level": self.permission_level,
            "timeout": float(self.timeout),
            "model": self.model,
            "resume_id": self.resume_id,
        }


@dataclass(frozen=True)
class ProbeResult:
    u"""probe() 之果：可用性 ＋ 版本 ＋ 刻（§二）。"""

    harness: str
    available: bool
    version: str = ""
    at: str = ""
    detail: str = ""
    meta: Mapping = field(default_factory=dict)

    def __post_init__(self):
        _req_str(self.harness, "ProbeResult.harness")
        if not isinstance(self.available, bool):
            raise ValueError("ProbeResult.available 须为 bool")
        for _n in ("version", "detail"):
            _req_str(getattr(self, _n), "ProbeResult." + _n, allow_empty=True)
        _req_str(self.at, "ProbeResult.at")
        object.__setattr__(self, "meta", _mapping(self.meta, "ProbeResult.meta"))

    def to_dict(self):
        return {
            "harness": self.harness,
            "available": self.available,
            "version": self.version,
            "at": self.at,
            "detail": self.detail,
            "meta": dict(self.meta),
        }


@dataclass(frozen=True)
class StreamEvent:
    u"""stream() 之一条增量（seq 单调；⛔ 回改）。"""

    run_id: str
    seq: int
    at: str
    kind: str
    text: str = ""
    data: Mapping = field(default_factory=dict)

    def __post_init__(self):
        _req_str(self.run_id, "StreamEvent.run_id")
        if isinstance(self.seq, bool) or not isinstance(self.seq, int) or self.seq < 1:
            raise ValueError("StreamEvent.seq 须为 ≥1 之整数")
        _req_str(self.at, "StreamEvent.at")
        if self.kind not in STREAM_KINDS:
            raise ValueError("StreamEvent.kind 须在 %s 中（今 %r）" % (list(STREAM_KINDS), self.kind))
        _req_str(self.text, "StreamEvent.text", allow_empty=True)
        object.__setattr__(self, "data", _mapping(self.data, "StreamEvent.data"))

    def to_dict(self):
        return {"run_id": self.run_id, "seq": self.seq, "at": self.at,
                "kind": self.kind, "text": self.text, "data": dict(self.data)}


@dataclass(frozen=True)
class RunHandle:
    u"""run()／resume() 之柄：run_id ＋ session_id ＋ 本次已可读之增量。"""

    run_id: str
    session_id: str
    harness: str
    history_replay: bool = True
    stream: tuple = ()

    def __post_init__(self):
        for _n in ("run_id", "session_id", "harness"):
            _req_str(getattr(self, _n), "RunHandle." + _n)
        if not isinstance(self.history_replay, bool):
            raise ValueError("RunHandle.history_replay 须为 bool（＋不回放须显式 False）")
        events = tuple(self.stream or ())
        if any(not isinstance(e, StreamEvent) for e in events):
            raise ValueError("RunHandle.stream 须逐项为 StreamEvent")
        object.__setattr__(self, "stream", events)

    def to_dict(self, with_stream=False):
        out = {"run_id": self.run_id, "session_id": self.session_id,
               "harness": self.harness, "history_replay": self.history_replay}
        if with_stream:
            out["stream"] = [e.to_dict() for e in self.stream]
        return out


@dataclass(frozen=True)
class PermissionState:
    u"""permissions() 之果：级别 ＋ 门 ＋ 待批（§二）。"""

    harness: str
    level: str = ""
    allowed_tools: tuple = ()
    pending: tuple = ()
    gates: Mapping = field(default_factory=dict)
    note: str = ""

    def __post_init__(self):
        _req_str(self.harness, "PermissionState.harness")
        _req_str(self.level, "PermissionState.level", allow_empty=True)
        object.__setattr__(self, "allowed_tools", _str_tuple(self.allowed_tools, "PermissionState.allowed_tools"))
        object.__setattr__(self, "pending", _str_tuple(self.pending, "PermissionState.pending"))
        gates = _mapping(self.gates, "PermissionState.gates")
        for _k, _v in gates.items():
            if _v not in PERMISSION_GATES:
                raise ValueError("PermissionState.gates[%r] 须在 %s 中（今 %r）"
                                 % (_k, list(PERMISSION_GATES), _v))
        object.__setattr__(self, "gates", gates)
        _req_str(self.note, "PermissionState.note", allow_empty=True)

    def to_dict(self):
        return {"harness": self.harness, "level": self.level,
                "allowed_tools": list(self.allowed_tools), "pending": list(self.pending),
                "gates": dict(self.gates), "note": self.note}


@dataclass(frozen=True)
class Cost:
    u"""cost() 之果：tokens ／ 金额（cny） ／ 轮次（turns）—— ⛔ 各 adapter 各自造数。"""

    tokens: int = 0
    cny: float = 0.0
    turns: int = 0

    def __post_init__(self):
        for _n in ("tokens", "turns"):
            _v = getattr(self, _n)
            if isinstance(_v, bool) or not isinstance(_v, int) or _v < 0:
                raise ValueError("Cost.%s 须为 ≥0 之整数" % _n)
        if isinstance(self.cny, bool) or not isinstance(self.cny, (int, float)) or self.cny < 0:
            raise ValueError("Cost.cny 须为 ≥0 之数值")
        object.__setattr__(self, "cny", float(self.cny))

    def to_dict(self):
        return {"tokens": self.tokens, "cny": self.cny, "turns": self.turns}


@dataclass(frozen=True)
class AuditResult:
    u"""audit() 之果：回执（canonical sha16）＋ 产物 ＋ harness 私有 meta。"""

    run_id: str
    status: str
    receipt_sha16: str
    artifacts: tuple = ()
    harness_meta: Mapping = field(default_factory=dict)
    started_at: str = ""
    ended_at: str = ""

    def __post_init__(self):
        _req_str(self.run_id, "AuditResult.run_id")
        if self.status not in RUN_STATUSES:
            raise ValueError("AuditResult.status 须在 %s 中（今 %r）" % (list(RUN_STATUSES), self.status))
        if not isinstance(self.receipt_sha16, str) or not _SHA16_RE.match(self.receipt_sha16):
            raise ValueError("AuditResult.receipt_sha16 须为 16 位小写十六进制（今 %r）" % (self.receipt_sha16,))
        object.__setattr__(self, "artifacts", _str_tuple(self.artifacts, "AuditResult.artifacts"))
        object.__setattr__(self, "harness_meta", _mapping(self.harness_meta, "AuditResult.harness_meta"))
        for _n in ("started_at", "ended_at"):
            _req_str(getattr(self, _n), "AuditResult." + _n, allow_empty=True)

    def to_dict(self):
        return {"run_id": self.run_id, "status": self.status,
                "receipt_sha16": self.receipt_sha16, "artifacts": list(self.artifacts),
                "harness_meta": dict(self.harness_meta),
                "started_at": self.started_at, "ended_at": self.ended_at}


@dataclass(frozen=True)
class TeamState:
    u"""team() 之果（**可选**能力）：不支者须显式 available=False ＋ reason（⛔ 静默替身）。"""

    harness: str
    available: bool
    reason: str = ""
    meta: Mapping = field(default_factory=dict)

    def __post_init__(self):
        _req_str(self.harness, "TeamState.harness")
        if not isinstance(self.available, bool):
            raise ValueError("TeamState.available 须为 bool")
        _req_str(self.reason, "TeamState.reason", allow_empty=True)
        object.__setattr__(self, "meta", _mapping(self.meta, "TeamState.meta"))

    def to_dict(self):
        return {"harness": self.harness, "available": self.available,
                "reason": self.reason, "meta": dict(self.meta)}


@dataclass(frozen=True)
class RunRecord:
    u"""canonical run 记录（**PA 账 schema** · §三）。`harness_meta` 为唯一 harness 私有之域。"""

    run_id: str
    harness: str
    session_id: str
    model: str
    cwd: str
    started_at: str
    ended_at: str
    status: str
    cost: Cost
    artifacts: tuple = ()
    receipt_sha16: str = ""
    harness_meta: Mapping = field(default_factory=dict)

    def __post_init__(self):
        for _n in ("run_id", "harness", "session_id", "started_at", "ended_at"):
            _req_str(getattr(self, _n), "RunRecord." + _n)
        for _n in ("model", "cwd"):
            _req_str(getattr(self, _n), "RunRecord." + _n, allow_empty=True)
        if self.status not in RUN_STATUSES:
            raise ValueError("RunRecord.status 须在 %s 中（今 %r）" % (list(RUN_STATUSES), self.status))
        if not isinstance(self.cost, Cost):
            raise ValueError("RunRecord.cost 须为 Cost（今 %s）" % type(self.cost).__name__)
        object.__setattr__(self, "artifacts", _str_tuple(self.artifacts, "RunRecord.artifacts"))
        object.__setattr__(self, "harness_meta", _mapping(self.harness_meta, "RunRecord.harness_meta"))
        expected = sha16(self.payload())
        if self.receipt_sha16:
            if not isinstance(self.receipt_sha16, str) or not _SHA16_RE.match(self.receipt_sha16):
                raise ValueError("RunRecord.receipt_sha16 须为 16 位小写十六进制")
            if self.receipt_sha16 != expected:
                raise ValueError("RunRecord.receipt_sha16 与 canonical payload 不符（⛔ 以错印充真）")
        else:
            object.__setattr__(self, "receipt_sha16", expected)

    def payload(self):
        u"""receipt 之料：canonical 字段**去** `receipt_sha16`（⛔ 自指）。"""
        out = self.to_dict()
        out.pop("receipt_sha16", None)
        return out

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "harness": self.harness,
            "session_id": self.session_id,
            "model": self.model,
            "cwd": self.cwd,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "cost": self.cost.to_dict(),
            "artifacts": list(self.artifacts),
            "receipt_sha16": self.receipt_sha16,
            "harness_meta": dict(self.harness_meta),
        }


# ============================ PA 侧账（内存 · H1） ============================

class RunLedger:
    u"""PA 侧 canonical `RunRecord` 账（**内存** · H1 用；⛔ 解析 harness session）。

    后续期可 `dump()` 后交 PA ledger（`core.pa.ledger`）／vault；本件 ⛔ 写盘、⛔ 起进程。
    """

    def __init__(self, records=None):
        self._lock = threading.RLock()
        self._records = {}
        self._order = []
        for _r in (records or ()):
            self.append(_r)

    def append(self, record):
        u"""记一条（⛔ 同 run_id 二记 ⇒ ValueError；⛔ 静默覆）。"""
        if not isinstance(record, RunRecord):
            raise ValueError("RunLedger 只收 RunRecord（今 %s）" % type(record).__name__)
        with self._lock:
            if record.run_id in self._records:
                raise ValueError("RunLedger：run_id 已存（⛔ 覆）：%s" % record.run_id)
            self._records[record.run_id] = record
            self._order.append(record.run_id)
        return record

    def get(self, run_id):
        with self._lock:
            rec = self._records.get(run_id)
        if rec is None:
            raise UnknownRun("PA 账无此 run_id：%r" % (run_id,))
        return rec

    def has(self, run_id):
        with self._lock:
            return run_id in self._records

    def records(self):
        with self._lock:
            return tuple(self._records[rid] for rid in self._order)

    def by_session(self, session_id):
        with self._lock:
            return tuple(self._records[rid] for rid in self._order
                         if self._records[rid].session_id == session_id)

    def latest(self):
        with self._lock:
            return self._records[self._order[-1]] if self._order else None

    def count(self):
        with self._lock:
            return len(self._records)

    def dump(self):
        u"""可序列化之账（交 PA ledger／vault 之形；⛔ 写盘）。"""
        return [r.to_dict() for r in self.records()]


# ============================ 接口（Protocol · 适配器之契约） ============================

@runtime_checkable
class HarnessPort(Protocol):
    u"""PA 核心所依赖之**唯一** harness 面（§二）。adapter 实现本协议；PA ⛔ 识 adapter 私有。"""

    name: str

    def probe(self):
        u"""可用性 ＋ 版本 ＋ 刻（⛔ 谎报可用；不应 = 照实 available=False）。"""
        ...

    def run(self, spec):
        u"""起一次任务 ⇒ RunHandle（run_id ／ session_id ／ 本次已可读之增量）。"""
        ...

    def resume(self, session_id):
        u"""续会话；不回放历史者须 `RunHandle.history_replay=False`（⛔ 默认 True 蒙混）。"""
        ...

    def cancel(self, run_id):
        u"""停；1s 内。返 True ＝ 已停；已知而不可停（如已结束） ⇒ False（⛔ 谎报已停）。"""
        ...

    def stream(self, run_id):
        u"""本次之增量输出（Iterable[StreamEvent]；seq 单调）。"""
        ...

    def permissions(self):
        u"""门 ／ 级别 ／ 待批（PermissionState）。"""
        ...

    def cost(self, run_id):
        u"""tokens ／ 金额 ／ 轮次（Cost）。"""
        ...

    def audit(self, run_id):
        u"""回执 ／ 产物 ／ 哈希（AuditResult）。"""
        ...

    def team(self):
        u"""spawn ／ message ／ tasks —— **可选**能力；不支者返 TeamState(available=False) ∨ raise UnsupportedCapability。"""
        ...
