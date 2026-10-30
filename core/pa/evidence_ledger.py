# -*- coding: utf-8 -*-
u"""件—账—印 之可追加账本（evidence ledger · task-82）。

【本件解决什么】T74/T76 有「取件之录／CLI」，但**无账**：件到账未记、用旧证充今证、
账件被改而无据 —— 本件把「件—账—印」落成 append-only JSONL ＋ 幂等登记 ＋ 逐行复核：

  · `build_record(path, owner, decision, rerun, captured_at=None)`：
    `relations.make_evidence` 取件录 ＋ owner（域主席）／decision（裁决 id）／rerun（复跑命令），
    过 `relations.validate_evidence`；⛔ 合 ⇒ raise `RecordInvalid`（⛔ 静默入账）。
  · `register(ledger_path, rec)`：**幂等键 ＝ path ＋ sha16 ＋ decision**；已存在 ⇒
    `registered=False`（⛔ 重记）；否则追加一行 canonical JSON ＋ `O_APPEND` ＋ **fsync**。
  · `verify(ledger_path, base_dir=None)`：逐行 JSON／`validate_evidence`，并**重算件之 sha16**
    （与 bytes）⇒ 逐行 `ok/bad` 汇总；⛔ 只信账内自述之印（篡改必抓）。

边界：⛔ 改 `core/pa/relations.py` 语义（唯调用）／路由／UI；本件唯写**给定 ledger_path**
（父目录建 · ⛔ 触 vault／别处）；单写者＝同一进程之 `_LOCK` 串行化（跨进程依 JSONL 追加之原子性）。
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime
from pathlib import Path

from core.pa import relations as R

#: 缺省账件径之 env 覆（显式 ⇒ 用之；优先级最高）
LEDGER_ENV = "PA_EVIDENCE_LEDGER"

#: PA 数据根 env（装根之真实数据根；次优先）
DATA_ROOT_ENV = "CLAWSJOY_DATA_DIR"

#: 缺省账之相对子径（对数据根追加）
LEDGER_REL = Path("v9") / "pa" / "evidence_ledger.jsonl"

#: 末选回退：仓内 data（装根无 env 时之开发/仓内形态）
DEFAULT_LEDGER_PATH = Path("data") / LEDGER_REL

#: 进程内串行（同进程并发 register ⛔ 交错读-判-写）
_LOCK = threading.RLock()


class EvidenceLedgerError(Exception):
    u"""账本层之基错。"""


class RecordInvalid(EvidenceLedgerError, ValueError):
    u"""件／账之形不合契约（⛔ 静默入账）。"""


class LedgerCorrupt(EvidenceLedgerError):
    u"""账件有坏行（非 JSON ／ 非对象）；register 拒写、verify 记 bad。"""


def _text_ok(value):
    return isinstance(value, str) and bool(value.strip())


def default_ledger_path():
    u"""缺省账件径（T123 · 装根之真数据根优先）：

      ① env `PA_EVIDENCE_LEDGER`（显式全径）
      ② env `CLAWSJOY_DATA_DIR` ＋ `v9/pa/evidence_ledger.jsonl`
      ③ `%LOCALAPPDATA%\\ClawsJoyPA\\data` ＋ 同子径
      ④ 仓内 `data/v9/pa/evidence_ledger.jsonl`

    只**解析径**：⛔ 建目录 ／ ⛔ 写账 ／ ⛔ 探存在性（缺径 ⇒ 上选，⛔ 存在即回落）。
    """
    raw = (os.environ.get(LEDGER_ENV) or "").strip()
    if raw:
        return Path(raw)
    root = (os.environ.get(DATA_ROOT_ENV) or "").strip()
    if root:
        return Path(root) / LEDGER_REL
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local:
        return Path(local) / "ClawsJoyPA" / "data" / LEDGER_REL
    return DEFAULT_LEDGER_PATH


def _canonical(rec):
    return json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _key_of(rec):
    u"""幂等键：path ＋ sha16 ＋ decision（⛔ 含 captured_at —— 旧证重取仍同一条）。"""
    return (str(rec.get("path") or ""), str(rec.get("sha16") or ""),
            str(rec.get("decision") or ""))


def _read_records(ledger):
    u"""读账 ⇒ 记录列（逐行 JSON）；坏行 ⇒ LedgerCorrupt（⛔ 静默跳过）。"""
    if not ledger.exists():
        return []
    text = ledger.read_text(encoding="utf-8")
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise LedgerCorrupt("账件空行（%s:%d）" % (ledger, no))
        try:
            doc = json.loads(line)
        except Exception as exc:
            raise LedgerCorrupt("账件坏行（%s:%d）：%s: %s"
                                % (ledger, no, type(exc).__name__, str(exc)[:120]))
        if not isinstance(doc, dict):
            raise LedgerCorrupt("账件第 %d 行非对象（%s）" % (no, type(doc).__name__))
        out.append(doc)
    return out


def build_record(path, owner, decision, rerun, captured_at=None):
    u"""造「件—账—印」之一条 ⇒ dict（含 evidence 五键 ＋ owner ／ decision ／ rerun）。

    `captured_at` 缺省 ＝ 取件此刻（`make_evidence`）；显给（ISO 字串 ∨ datetime）⇒ 覆之。
    件不可读 ⇒ 照抛 OSError；字段不合／形不合 ⇒ `RecordInvalid`（⛔ 空串入账）。
    """
    if not _text_ok(owner):
        raise RecordInvalid("owner 须为非空字串（域主席）")
    if not _text_ok(decision):
        raise RecordInvalid("decision 须为非空字串（裁决 id）")
    if not _text_ok(rerun):
        raise RecordInvalid("rerun 须为非空字串（复跑命令）")
    rec = dict(R.make_evidence(path))
    if captured_at is not None:
        if isinstance(captured_at, datetime):
            captured_at = captured_at.isoformat(timespec="seconds")
        if not _text_ok(captured_at):
            raise RecordInvalid("captured_at 须为 ISO 8601 字串或 datetime")
        rec["captured_at"] = str(captured_at)
    rec["owner"] = str(owner)
    rec["decision"] = str(decision)
    rec["rerun"] = str(rerun)
    got = R.validate_evidence(rec)
    if not got["ok"]:
        raise RecordInvalid("证据录不合契约：missing=%s errors=%s"
                            % (got["missing"], got["errors"]))
    return rec


def _append_line(ledger, line):
    u"""追加一行：父目录建 ＋ `O_APPEND|O_CREAT` ＋ 单次写 ＋ **fsync**（⛔ 停页缓存）。"""
    ledger = Path(ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    data = (line + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
    fd = os.open(str(ledger), flags, 0o644)
    try:
        written = os.write(fd, data)
        if written != len(data):
            raise EvidenceLedgerError("账件只写 %d／%d 字节（%s）"
                                      % (written, len(data), ledger))
        os.fsync(fd)
    finally:
        os.close(fd)


def register(ledger_path, rec):
    u"""登记一条 ⇒ `{registered, path, count, key}`；**幂等**（同 key 已存 ⇒ False，⛔ 重记）。

    T89：**写侧亦强制 owner**（`require_owner=True`）—— 新账 ⛔ 无主；旧账之读容忍见 verify。
    """
    got = R.validate_evidence(rec, require_owner=True)
    if not got["ok"]:
        raise RecordInvalid("证据录不合契约：missing=%s errors=%s"
                            % (got["missing"], got["errors"]))
    if not _text_ok(rec.get("decision")):
        raise RecordInvalid("decision 须为非空字串（幂等键之一）")
    if "owner" in rec and not _text_ok(rec.get("owner")):
        raise RecordInvalid("owner 若给须为非空字串")
    ledger = Path(ledger_path)
    key = _key_of(rec)
    with _LOCK:
        records = _read_records(ledger)
        if any(_key_of(existing) == key for existing in records):
            return {"registered": False, "path": str(ledger),
                    "count": len(records),
                    "key": {"path": key[0], "sha16": key[1], "decision": key[2]}}
        _append_line(ledger, _canonical(rec))
        return {"registered": True, "path": str(ledger),
                "count": len(records) + 1,
                "key": {"path": key[0], "sha16": key[1], "decision": key[2]},
                "line": len(records) + 1}


SUPERSEDE_FIELDS = ("path", "sha16", "decision", "owner", "reason", "captured_at")


def _now_iso():
    u"""取刻：本机时区 ISO 8601（supersede 记录之用）。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _supersede_key(rec):
    u"""supersede 之键：path ＋ sha16（＝其所退旧证据之键；⛔ 含 decision）。"""
    return (str(rec.get("path") or ""), str(rec.get("sha16") or ""))


def _validate_supersede(rec):
    u"""supersede 记录之形 ⇒ 违例列（空 ＝ 合）。"""
    errs = []
    if not _text_ok(rec.get("path")):
        errs.append(u"path 须为非空字串")
    h = rec.get("sha16")
    if not isinstance(h, str) or not R.SHA16_RE.match(h):
        errs.append(u"sha16 须为 16 位小写十六进制")
    for name in ("decision", "owner", "reason"):
        if not _text_ok(rec.get(name)):
            errs.append(u"%s 须为非空字串" % name)
    at = rec.get("captured_at")
    if not _text_ok(at):
        errs.append(u"captured_at 须为 ISO 8601 字串")
    else:
        try:
            datetime.fromisoformat(at.strip())
        except ValueError:
            errs.append(u"captured_at 不可解析为 ISO 8601")
    return errs


def _superseded_row(line_no, srec):
    u"""verify 之 superseded 行（旧印已退役之据）。"""
    return {"line": line_no,
            "path": str(srec.get("path") or ""),
            "sha16": str(srec.get("sha16") or ""),
            "reason": "superseded",
            "decision": str(srec.get("decision") or ""),
            "supersede_reason": str(srec.get("reason") or "")}


def supersede(ledger_path, path, sha16, decision, owner, reason):
    u"""显式退旧印：追加一条 `kind="supersede"`（⛔ 改／删旧行）；幂等键 path＋sha16。

    由：合法改件后旧记录之印必 stale，但**历史不可删** ⇒ 以 supersede 显式标「此旧印已退役」，
    verify 方将其归 `superseded`（不计 bad）。缺旧键 ⇒ `RecordInvalid`（⛔ 空退）；
    同键已 supersede ⇒ `registered=False`（⛔ 重记）。
    """
    if not _text_ok(path):
        raise RecordInvalid("supersede：path 须为非空字串")
    if not isinstance(sha16, str) or not R.SHA16_RE.match(sha16):
        raise RecordInvalid("supersede：sha16 须为 16 位小写十六进制")
    for name, val in (("decision", decision), ("owner", owner), ("reason", reason)):
        if not _text_ok(val):
            raise RecordInvalid("supersede：%s 须为非空字串" % name)
    ledger = Path(ledger_path)
    key = (str(path), str(sha16))
    with _LOCK:
        records = _read_records(ledger)
        target_exists = any(
            str(r.get("kind") or "") != "supersede" and _supersede_key(r) == key
            for r in records)
        if not target_exists:
            raise RecordInvalid("supersede：无旧记录（path+sha16 未在账）：%s ＋ %s" % key)
        if any(str(r.get("kind") or "") == "supersede" and _supersede_key(r) == key
               for r in records):
            return {"registered": False, "kind": "supersede", "path": str(ledger),
                    "count": len(records),
                    "key": {"path": key[0], "sha16": key[1]}}
        doc = {"kind": "supersede", "path": key[0], "sha16": key[1],
               "decision": str(decision), "owner": str(owner),
               "reason": str(reason), "captured_at": _now_iso()}
        _append_line(ledger, _canonical(doc))
        return {"registered": True, "kind": "supersede", "path": str(ledger),
                "count": len(records) + 1, "line": len(records) + 1,
                "key": {"path": key[0], "sha16": key[1]}}


def verify(ledger_path, base_dir=None, max_age_days=None, require_owner=True):
    u"""逐行复核 ⇒ `{ok, total, bad, superseded}`：形（validate_evidence）＋ **重算件 sha16／bytes**
    ＋（可选）**C15 保鲜**（`max_age_days` 非空 ⇒ `relations.check_freshness`）。

    **supersede（T93）**：首遍收 `kind="supersede"` 之（path＋sha16）退役集；某旧证据
    若已被 supersede **且当前文件已不同** ⇒ 归 `superseded`（reason="superseded"，⛔ 计 bad）；
    `total` 只计**证据行**（supersede 行不计）；旧行**原样保留**（⛔ 删史）。

    件径为相对 ⇒ 以 `base_dir`（缺省 cwd）拼。账件不在 ⇒ ok=False（⛔ 以空账充「已验」）。
    `require_owner=True`（**缺省** · T89）：owner 缺／空／非串 ⇒ bad `reason="owner"`（⛔ 冒绿）；
    旧账（无 owner）须显式 `require_owner=False` 方可通过（T82/T84 兼容口）。
    `max_age_days=None`（缺省）⇒ 行为**与旧同**（只校形／印）；非空 ⇒ 过期 ⇒ bad `reason="stale"`、
    未来 ⇒ bad `reason="future"`（行内附 age_days／expires_at／freshness_errors）。
    """
    if max_age_days is not None:
        if isinstance(max_age_days, bool) or not isinstance(max_age_days, (int, float)) or max_age_days <= 0:
            raise ValueError("max_age_days 须为 >0 之数值（今 %r）" % (max_age_days,))
    ledger = Path(ledger_path)
    out = {"ok": False, "total": 0, "bad": [], "superseded": []}
    if not ledger.exists():
        out["bad"].append({"line": 0, "reason": u"账件不存在：%s" % ledger})
        return out
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    try:
        text = ledger.read_text(encoding="utf-8")
    except Exception as exc:
        out["bad"].append({"line": 0, "reason": u"账件不可读：%s: %s"
                           % (type(exc).__name__, str(exc)[:120])})
        return out
    bad = []
    superseded = []
    lines = text.splitlines()

    # 首遍：收集 supersede 记录（path+sha16 之退役集）＋ 其形之错
    sup_keys = {}
    for no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            doc = json.loads(line)
        except Exception:
            continue
        if not isinstance(doc, dict) or doc.get("kind") != "supersede":
            continue
        errs = _validate_supersede(doc)
        if errs:
            bad.append({"line": no, "reason": "supersede 形坏", "errors": errs})
            continue
        sup_keys[_supersede_key(doc)] = doc

    # 二遍：逐证据行复核；supersede 行跳过（已首遍处理）且不计 total
    total = 0
    for no, line in enumerate(lines, 1):
        if not line.strip():
            total += 1
            bad.append({"line": no, "reason": u"空行（⛔ 静默）"})
            continue
        try:
            rec = json.loads(line)
        except Exception as exc:
            total += 1
            bad.append({"line": no, "reason": u"坏 JSON：%s" % type(exc).__name__})
            continue
        if not isinstance(rec, dict):
            total += 1
            bad.append({"line": no, "reason": u"非对象（%s）" % type(rec).__name__})
            continue
        if rec.get("kind") == "supersede":
            continue
        total += 1
        got = R.validate_evidence(rec, require_owner=require_owner)
        if not got["ok"]:
            owner_bad = require_owner and (
                "owner" in (got.get("missing") or [])
                or any("owner" in str(e) for e in (got.get("errors") or [])))
            bad.append({"line": no, "reason": "owner" if owner_bad else u"证据录不合契约",
                        "missing": got["missing"], "errors": got["errors"]})
            continue
        key = _supersede_key(rec)
        target = Path(str(rec.get("path") or ""))
        if not target.is_absolute():
            target = base / target
        try:
            blob = target.read_bytes()
        except Exception as exc:
            if key in sup_keys:
                superseded.append(_superseded_row(no, sup_keys[key]))
                continue
            bad.append({"line": no, "reason": u"件不可读：%s" % type(exc).__name__,
                        "path": str(target)})
            continue
        actual_sha16 = hashlib.sha256(blob).hexdigest()[:16]
        if len(blob) != rec.get("bytes") or actual_sha16 != rec.get("sha16"):
            if key in sup_keys:
                row = _superseded_row(no, sup_keys[key])
                row.update({"expected_sha16": rec.get("sha16"),
                            "actual_sha16": actual_sha16})
                superseded.append(row)
                continue
            bad.append({"line": no, "reason": u"印不符（疑篡改）",
                        "path": str(target),
                        "expected_bytes": rec.get("bytes"),
                        "actual_bytes": len(blob),
                        "expected_sha16": rec.get("sha16"),
                        "actual_sha16": actual_sha16})
            continue
        if max_age_days is not None:
            fresh = R.check_freshness(rec, ttl_days=max_age_days)
            if not fresh["ok"]:
                errs = list(fresh.get("errors") or [])
                if any(u"未来" in e for e in errs):
                    reason = "future"
                elif any(u"超期" in e for e in errs):
                    reason = "stale"
                else:
                    reason = "freshness"
                bad.append({"line": no, "reason": reason,
                            "age_days": fresh.get("age_days"),
                            "expires_at": fresh.get("expires_at"),
                            "freshness_errors": errs})
    out["total"] = total
    out["bad"] = bad
    out["superseded"] = superseded
    out["ok"] = not bad
    return out


__all__ = [
    "LEDGER_ENV",
    "DATA_ROOT_ENV",
    "LEDGER_REL",
    "DEFAULT_LEDGER_PATH",
    "EvidenceLedgerError",
    "RecordInvalid",
    "LedgerCorrupt",
    "default_ledger_path",
    "SUPERSEDE_FIELDS",
    "build_record",
    "register",
    "supersede",
    "verify",
]
