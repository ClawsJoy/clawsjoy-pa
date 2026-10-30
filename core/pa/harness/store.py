# -*- coding: utf-8 -*-
u"""FileRunLedger —— PA 自有**真账**：canonical `RunRecord` 之 append-only JSONL（H2b）。

【本件解决什么】`port.RunLedger` 是内存账（H1）；本件把它推进到 **PA 自有**之盘上真账：
  · 每 run 一行 canonical JSON（键序定 · 字段 ≡ `port.RUN_RECORD_FIELDS`）；
  · 追加后 **flush ＋ fsync**（落盘为凭 · ⛔ 只停在页缓存）；
  · 回读（`reload`）逐行重建 `RunRecord` ⇒ **receipt_sha16 自验**（⛔ 收被改之记录）；
  · DSH 等 adapter ⛔ 解析其私有会话格式 —— 盘上唯 PA canonical schema（H4）。

【路径】默认 `<PA_DATA_DIR ／ 'data/v9/pa'>/harness_runs.jsonl`；`PA_HARNESS_LEDGER_PATH`
  可覆（测试恒用 tmp 路径 ⇒ ⛔ 写仓、⛔ 写用户数据）。

【单写者（single-writer）不变量 —— 本件之核心】
  · **一文件一写者**：同一 `FileRunLedger` 实例独占该 path；⛔ 两个实例同写一文件；
  · append-only：⛔ 改写 ／ ⛔ 删除既有行；每行一次 `os.write` 整行（＋ fsync）；
  · 进程内 `RLock` 串行化（同实例之并发 append ⛔ 交错）；
  · **偏移守卫**：实例记 `_offset`（上次读 ／ 写后之字节数）；append 前若盘上 size ≠ `_offset`
    ⇒ 判「他者已改」显错（⛔ 静默续写 · ⛔ 覆盖）—— 须先 `reload()` 再写。
  跨进程协作用「一写者 ＋ 别者只读 reload」；分布式写非本件之域。

【边界（§四.1 ／ H5）】⛔ import dsh ／ paseo ／ obsidian；唯 stdlib ＋ `port`；
  唯写**本 path**（⛔ vault ／ registry ／ 别处）；⛔ 起进程。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from core.pa.harness.port import (
    RUN_RECORD_FIELDS,
    Cost,
    HarnessError,
    RunLedger,
    RunRecord,
    canonical_json,
)

#: 缺省账件名（`data/v9/pa/` 之下）
DEFAULT_LEDGER_BASENAME = "harness_runs.jsonl"

#: 路径覆盖之 env（显式 ⇒ 用之；否则由 `PA_DATA_DIR` 推）
LEDGER_PATH_ENV = "PA_HARNESS_LEDGER_PATH"


class FileRunLedgerError(HarnessError):
    u"""真账层之基错（落盘失败 ／ 单写者违约 ／ 路径不可写）。"""


class LedgerCorrupt(FileRunLedgerError):
    u"""账件不可回读（坏 JSON ／ 字段不合 canonical ／ receipt 不符 ／ run_id 重复）。"""

    def __init__(self, path, line_no, reason):
        self.path = str(path)
        self.line_no = int(line_no)
        self.reason = str(reason)
        super().__init__("账件腐坏：%s:%s：%s" % (self.path, self.line_no, self.reason))


def default_ledger_path():
    u"""缺省账件径：env `PA_HARNESS_LEDGER_PATH` ⇒ 否则 `<PA_DATA_DIR>/harness_runs.jsonl`。"""
    raw = (os.environ.get(LEDGER_PATH_ENV) or "").strip()
    if raw:
        return Path(raw)
    return Path(os.environ.get("PA_DATA_DIR", "data/v9/pa")) / DEFAULT_LEDGER_BASENAME


def _record_from_dict(doc):
    u"""JSONL 之一行 ⇒ `RunRecord`（**逐键**重建 · ⛔ 收陌生键 · receipt 由构造校验）。"""
    if not isinstance(doc, dict):
        raise ValueError("行须为 JSON 对象（今 %s）" % type(doc).__name__)
    extra = sorted(str(k) for k in doc if k not in RUN_RECORD_FIELDS)
    if extra:
        raise ValueError("行含 canonical 之外之键：%s" % ", ".join(extra))
    missing = [k for k in RUN_RECORD_FIELDS if k not in doc]
    if missing:
        raise ValueError("行缺 canonical 字段：%s" % ", ".join(missing))
    cost = doc.get("cost")
    if not isinstance(cost, dict):
        raise ValueError("cost 须为对象（今 %s）" % type(cost).__name__)
    return RunRecord(
        run_id=doc["run_id"],
        harness=doc["harness"],
        session_id=doc["session_id"],
        model=doc["model"],
        cwd=doc["cwd"],
        started_at=doc["started_at"],
        ended_at=doc["ended_at"],
        status=doc["status"],
        cost=Cost(**cost),
        artifacts=tuple(doc.get("artifacts") or ()),
        receipt_sha16=doc.get("receipt_sha16") or "",
        harness_meta=dict(doc.get("harness_meta") or {}),
    )


class FileRunLedger(RunLedger):
    u"""append-only JSONL 真账：与 `port.RunLedger` 同面（`append/get/records/by_session/latest/
    count/dump`）＋ `path` ／ `reload()`。`isinstance(..., port.RunLedger)` 成立 ⇒ adapter 直注。

    `fsync=False` 只供测试（验「不落盘」之反例）；生产缺省 True（flush＋fsync 恒为）。
    """

    def __init__(self, path=None, *, fsync=True, create_parents=True, reload=True):
        self.path = Path(path) if path is not None else default_ledger_path()
        self.fsync = bool(fsync)
        self.create_parents = bool(create_parents)
        self._offset = 0
        super().__init__()
        if reload:
            self.reload()

    def __repr__(self):
        return "<FileRunLedger path=%r runs=%d offset=%d>" % (str(self.path), self.count(), self._offset)

    # ---------------------------- 写（唯一写者之唯一入口） ----------------------------

    def append(self, record):
        u"""记一条：先验重 ⇒ 写一行（flush＋fsync）⇒ 内存账再收（⛔ 写后才发现重复）。"""
        if not isinstance(record, RunRecord):
            raise ValueError("FileRunLedger 只收 RunRecord（今 %s）" % type(record).__name__)
        line = (canonical_json(record.to_dict()) + "\n").encode("utf-8")
        with self._lock:
            if record.run_id in self._records:
                raise ValueError("FileRunLedger：run_id 已存（⛔ 覆）：%s" % record.run_id)
            self._persist_line(line)
            RunLedger.append(self, record)
        return record

    def _persist_line(self, line):
        u"""一行一次写：`O_APPEND|O_CREAT` ＋ `os.write` 整行 ＋ `fsync`（⛔ 缓冲停内存）。"""
        path = self.path
        try:
            if self.create_parents:
                path.parent.mkdir(parents=True, exist_ok=True)
            exists = path.exists()
            current = path.stat().st_size if exists else 0
            if current != self._offset:
                raise FileRunLedgerError(
                    "单写者违约：盘上 size=%d ≠ 本实例 offset=%d（他者已改 ⇒ 先 reload()）"
                    % (current, self._offset))
            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
            fd = os.open(str(path), flags, 0o644)
            try:
                written = os.write(fd, line)
                if written != len(line):
                    raise FileRunLedgerError("落账只写 %d／%d 字节（%s）"
                                             % (written, len(line), path))
                if self.fsync:
                    os.fsync(fd)
            finally:
                os.close(fd)
            self._offset = current + len(line)
        except FileRunLedgerError:
            raise
        except Exception as exc:
            raise FileRunLedgerError("落账失败（%s）：%s: %s"
                                     % (path, type(exc).__name__, str(exc)[:200])) from exc

    # ---------------------------- 读（回读 ＋ receipt 自验） ----------------------------

    def reload(self):
        u"""逐行重建内存账（⛔ 收坏行）：JSON ／ canonical 字段 ／ receipt_sha16 ／ run_id 唯一。"""
        path = self.path
        with self._lock:
            rows = []
            offset = 0
            if path.exists():
                try:
                    raw = path.read_bytes()
                    offset = len(raw)
                    text = raw.decode("utf-8")
                except Exception as exc:
                    raise LedgerCorrupt(path, 0, "不可读（%s: %s）"
                                        % (type(exc).__name__, str(exc)[:120])) from exc
                for line_no, line in enumerate(text.splitlines(), 1):
                    if not line.strip():
                        continue
                    try:
                        doc = json.loads(line)
                    except Exception as exc:
                        raise LedgerCorrupt(path, line_no, "JSON 解析失败（%s）"
                                            % type(exc).__name__) from exc
                    try:
                        rows.append(_record_from_dict(doc))
                    except Exception as exc:
                        raise LedgerCorrupt(path, line_no, str(exc)[:200]) from exc
            seen = set()
            records, order = {}, []
            for rec in rows:
                if rec.run_id in seen:
                    raise LedgerCorrupt(path, 0, "run_id 重复：%s" % rec.run_id)
                seen.add(rec.run_id)
                records[rec.run_id] = rec
                order.append(rec.run_id)
            self._records = records
            self._order = order
            self._offset = offset
            return len(order)

    # ---------------------------- 明示（报告 ／ 台面） ----------------------------

    def describe(self):
        u"""账件之台面（径 ／ 行数 ／ 末印）—— 供报告与自检（⛔ 写盘）。"""
        with self._lock:
            last = self._records[self._order[-1]] if self._order else None
        return {
            "path": str(self.path),
            "runs": self.count(),
            "offset": self._offset,
            "last_run_id": last.run_id if last else "",
            "last_receipt_sha16": last.receipt_sha16 if last else "",
        }
