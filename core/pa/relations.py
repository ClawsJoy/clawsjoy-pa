# -*- coding: utf-8 -*-
u"""PA 外联脚手架 v1 —— **可执行校验器**（承 `docs/pa/relations/` v0 六件之契约）。

v0 六件（RACI ／ DECISION_LEDGER ／ EVIDENCE_CONTRACT ／ CHANNEL_IDS ／ WIP_QUEUE ／ README）
只到模板；本件把其中三条**可机检**之约落成纯函数（⛔ 改路由 ／ ⛔ 改 UI ／ ⛔ 触红线）：

  ① `make_evidence(path)`：为一件产「件之录」＝ 径 ＋ bytes ＋ sha16 ＋ 取刻（唯读文件 · ⛔ 写账）。
  ② `validate_evidence(rec)`：校「一次事务」之必填（§EVIDENCE_CONTRACT：
     path ／ bytes ／ sha16 ／ captured_at ／ rerun）＋ sha16 之形（16 位小写 hex）＋ bytes ≥0。
  ③ `validate_decision(rec)`：校裁决必填（§DECISION_LEDGER：id ／ 裁决 ／ owner ／ 状态 ／ 证据 ／ 重开条件）
     ＋ id 之形（`D-YYYYMMDD-NN`）＋ 状态枚举。
  ④ `check_wip(tasks)`：校「每席 WIP=1」（§WIP_QUEUE：同一 owner 多 `in_progress` ⇒ False）。

口径：
  · 校验器**只判形**（⛔ 读网络 ／ ⛔ 写盘 ／ ⛔ 判真伪）；「件到账印发」之真伪由取件／复跑两器核。
  · 坏形**不静默**：missing 列缺键、errors 列逐条人话；调用方 ⛔ 以 `ok=True` 充「已验」。
  · `check_wip` 之坏条目（非对象／缺 owner ／缺 status）⇒ **False（fail-closed）**：
    WIP 不可验 ⇒ 不得充「合」。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path

#: 证据录之必填（§EVIDENCE_CONTRACT「一次事务」）
EVIDENCE_FIELDS = ("path", "bytes", "sha16", "captured_at", "rerun")

#: 裁决录之必填（§DECISION_LEDGER「字段」）
DECISION_FIELDS = ("id", u"裁决", "owner", u"状态", u"证据", u"重开条件")

#: 裁决状态之枚举（§DECISION_LEDGER ＋ 3480 之 `transferred`）
DECISION_STATES = ("proposed", "approved", "executing", "done", "blocked", "transferred")

#: 裁决 id 之形：`D-YYYYMMDD-NN`
DECISION_ID_RE = re.compile(r"^D-(\d{8})-(\d{2})$")

#: 印之形：sha256 前 16 位（小写 hex · 同 `core/pa` 诸器之 `sha16`）
SHA16_RE = re.compile(r"^[0-9a-f]{16}$")

WIP_STATUS = "in_progress"


def _now_iso():
    u"""取刻：本机时区之 ISO 8601（⛔ UTC 冒充 ／ ⛔ 无时区）。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _sha16_bytes(blob):
    u"""件之印：sha256 前 16 位（小写 hex）。"""
    return hashlib.sha256(blob).hexdigest()[:16]


def _text_ok(value):
    return isinstance(value, str) and bool(value.strip())


def _result(missing, errors):
    return {"ok": not missing and not errors,
            "missing": list(missing),
            "errors": list(errors)}


def make_evidence(path):
    u"""件之录：`{path, bytes, sha16, captured_at}`（唯读文件 · ⛔ 写账 ／ ⛔ 改件）。

    ⛔ 目录 ／ 缺件／不可读 ⇒ 照抛（`IsADirectoryError` ／ `FileNotFoundError` ／ `OSError`）——
    「无件可录」⛔ 以空录充「已取」。
    """
    if path is None or not str(path).strip():
        raise ValueError("make_evidence(path)：path 须为非空径")
    target = Path(path)
    blob = target.read_bytes()
    return {
        "path": str(target),
        "bytes": len(blob),
        "sha16": _sha16_bytes(blob),
        "captured_at": _now_iso(),
    }


def validate_evidence(rec, require_owner=False):
    u"""校证据录之形 ⇒ `{ok, missing, errors}`（⛔ 静默 ／ ⛔ 以引用件之印充自身印——形上唯校其形）。

    `require_owner=True`（T89 · 读侧强制）：owner 必填 —— 缺 ⇒ `missing` 含 "owner"；
    给而空 ／ 非串 ⇒ `errors`。缺省 False ⇒ 旧行为（⛔ 破 T74/T76）。
    """
    if not isinstance(rec, dict):
        return _result([], [u"证据录须为对象（今 %s）" % type(rec).__name__])
    missing = [k for k in EVIDENCE_FIELDS if k not in rec or rec.get(k) is None]
    errors = []
    if "path" in rec and not _text_ok(rec.get("path")):
        errors.append(u"path 须为非空字串")
    if "bytes" in rec:
        n = rec.get("bytes")
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            errors.append(u"bytes 须为 ≥0 之整数（今 %r）" % (n,))
    if "sha16" in rec:
        h = rec.get("sha16")
        if not isinstance(h, str) or not SHA16_RE.match(h):
            errors.append(u"sha16 须为 16 位小写十六进制（今 %r）" % (h,))
    if "captured_at" in rec:
        at = rec.get("captured_at")
        if not _text_ok(at):
            errors.append(u"captured_at 须为非空 ISO 8601 字串（今 %r）" % (at,))
        else:
            try:
                datetime.fromisoformat(at.strip())
            except ValueError:
                errors.append(u"captured_at 不可解析为 ISO 8601（今 %r）" % (at,))
    if "rerun" in rec and not _text_ok(rec.get("rerun")):
        errors.append(u"rerun 须为非空字串（命令 ＋ 两次同结果 ∨ 反例）")
    if require_owner:
        if "owner" not in rec or rec.get("owner") is None:
            missing.append("owner")
        elif not _text_ok(rec.get("owner")):
            errors.append(u"owner 须为非空字串（require_owner=True）")
    return _result(missing, errors)


def validate_decision(rec):
    u"""校裁决录之形 ⇒ `{ok, missing, errors}`（必填六键 ＋ id 之形 ＋ 状态枚举）。"""
    if not isinstance(rec, dict):
        return _result([], [u"裁决录须为对象（今 %s）" % type(rec).__name__])
    missing = [k for k in DECISION_FIELDS if k not in rec or rec.get(k) is None]
    errors = []
    if "id" in rec:
        did = rec.get("id")
        matched = DECISION_ID_RE.match(did) if isinstance(did, str) else None
        if not matched:
            errors.append(u"id 须为 D-YYYYMMDD-NN（今 %r）" % (did,))
        else:
            try:
                datetime.strptime(matched.group(1), "%Y%m%d")
            except ValueError:
                errors.append(u"id 之日期非法（今 %r）" % (did,))
    if u"裁决" in rec and not _text_ok(rec.get(u"裁决")):
        errors.append(u"裁决 须为非空字串")
    if "owner" in rec and not _text_ok(rec.get("owner")):
        errors.append(u"owner 须为非空字串")
    if u"状态" in rec:
        st = rec.get(u"状态")
        if not isinstance(st, str) or st.strip() not in DECISION_STATES:
            errors.append(u"状态 须在 %s（今 %r）" % (u"／".join(DECISION_STATES), st))
    if u"证据" in rec:
        ev = rec.get(u"证据")
        if isinstance(ev, (list, dict)):
            if not ev:
                errors.append(u"证据 须为非空（径+sha16 ∨ 非空证据录）")
        elif not _text_ok(ev):
            errors.append(u"证据 须为非空（径+sha16 ∨ 非空证据录）")
    if u"重开条件" in rec and not _text_ok(rec.get(u"重开条件")):
        errors.append(u"重开条件 须为非空字串（何时可重议；无则书「无」）")
    return _result(missing, errors)


def check_wip(tasks):
    u"""每席 WIP=1：同一 owner 多 `in_progress` ⇒ **False**（合 ⇒ True）。

    `tasks` 须为列表（否则 ValueError）；条目非对象 ／ 缺 owner ／ 缺 status ⇒ False（不可验 ⛔ 充合）。
    """
    if not isinstance(tasks, list):
        raise ValueError("check_wip(tasks)：tasks 须为列表（今 %s）" % type(tasks).__name__)
    counts = {}
    for item in tasks:
        if not isinstance(item, dict):
            return False
        owner, status = item.get("owner"), item.get("status")
        if not _text_ok(owner) or not _text_ok(status):
            return False
        if status.strip().lower() == WIP_STATUS:
            key = owner.strip()
            counts[key] = counts.get(key, 0) + 1
    return all(n <= 1 for n in counts.values())


#: C15（PM D3）：证据保鲜之缺省 TTL（天）
FRESHNESS_TTL_DAYS = 30


def _local_tz():
    u"""本机时区（naive 之 ISO ⇒ 按本机时区解 · ⛔ 猜 UTC）。"""
    return datetime.now().astimezone().tzinfo


def _as_aware(value, name):
    u"""ISO 8601 字串 ∨ datetime ⇒ 带时区之 datetime（naive ⇒ 附本机时区 · ⛔ 抛时区歧义）。"""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s 不可解析为 ISO 8601：%r" % (name, value))
    else:
        raise ValueError("%s 须为 ISO 8601 字串或 datetime（今 %r）" % (name, value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_local_tz())
    return dt


def check_freshness(rec, now=None, ttl_days=FRESHNESS_TTL_DAYS):
    u"""C15 证据保鲜：`captured_at` 可解析 ISO ＋ 未超 TTL（缺省 30 天）＋ owner（可选）非空。

    边界（**明示** · ⛔ 默认值蒙）：age ≤ ttl ⇒ ok=True；**恰 30 日整 ＝ 未超 ⇒ ok=True**；
    30 日 ＋ 1 秒 ⇒ ok=False；未来之 `captured_at`（age < 0）⇒ ok=False（⛔ 以未来刻充今证）。
    `now`：datetime ∨ ISO 字串 ∨ None（＝此刻 · 本机时区）；`ttl_days`：>0 之数值。
    返回 `{ok, age_days, expires_at, errors}`；不可算者 age_days=None ／ expires_at=""。
    """
    out = {"ok": False, "age_days": None, "expires_at": "", "errors": []}
    errors = out["errors"]
    if not isinstance(rec, dict):
        errors.append(u"证据录须为对象（今 %s）" % type(rec).__name__)
        return out
    if "owner" in rec and not _text_ok(rec.get("owner")):
        errors.append(u"owner 须为非空字串（域主席）")
    if "captured_at" not in rec or rec.get("captured_at") is None:
        errors.append(u"captured_at 必填（ISO 8601 取刻）")
        return out
    if isinstance(ttl_days, bool) or not isinstance(ttl_days, (int, float)) or ttl_days <= 0:
        errors.append(u"ttl_days 须为 >0 之数值（今 %r）" % (ttl_days,))
        return out
    try:
        captured = _as_aware(rec.get("captured_at"), "captured_at")
    except ValueError as exc:
        errors.append(str(exc))
        return out
    try:
        ref = datetime.now().astimezone() if now is None else _as_aware(now, "now")
    except ValueError as exc:
        errors.append(str(exc))
        return out
    delta = ref - captured
    age_days = delta.total_seconds() / 86400.0
    out["age_days"] = round(age_days, 3)
    out["expires_at"] = (captured + timedelta(days=float(ttl_days))).isoformat(timespec="seconds")
    if delta < timedelta(0):
        errors.append(u"captured_at 在未来：age=%.3f 天（ref %s ∪ captured %s）"
                      % (age_days, ref.isoformat(timespec="seconds"),
                         captured.isoformat(timespec="seconds")))
    elif delta > timedelta(days=float(ttl_days)):
        errors.append(u"证据超期：age=%.3f 天 > ttl=%s 天（expires_at %s）"
                      % (age_days, ttl_days, out["expires_at"]))
    out["ok"] = not errors
    return out


__all__ = [
    "EVIDENCE_FIELDS",
    "DECISION_FIELDS",
    "DECISION_STATES",
    "DECISION_ID_RE",
    "SHA16_RE",
    "WIP_STATUS",
    "FRESHNESS_TTL_DAYS",
    "make_evidence",
    "validate_evidence",
    "validate_decision",
    "check_wip",
    "check_freshness",
]
