# -*- coding: utf-8 -*-
"""V9-PES · **Audit 层** —— 审批 / 越权 / 验证 / 产物 / 复验的独立留痕。

对应总任务书工程版 v1 §3.1（术语修正 ③：**五层里必须有 Audit**）
与 §5 M2「审批→回执→落库→产物 全链可查」。

四条硬性质：

1. **独立**：审计流与执行态**分文件**（`data/v9/pes/audit.jsonl`），
   查询审计**不读**执行态、**不读**来源生成日志；
2. **append-only**：只追加，不修改既有行；篡改由 :meth:`AuditLog.verify_chain` 检出；
3. **哈希链**：每行带 `prev_hash`/`hash`，断链即可定位到第一处被改的序号；
4. **run_id 是资格位**：缺 ``run_id`` 的条目 **不合格**（`qualified=False`），
   **不得计入对账证据**（`PA汇总审计对账层 §③④` 原文）。

零第三方依赖。
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.pes.windows import REPO_ROOT, normalize_path

DEFAULT_AUDIT_PATH = REPO_ROOT / "data" / "v9" / "pes" / "audit.jsonl"

_GENESIS = "0" * 64
_LOCK = threading.RLock()
_log: Optional["AuditLog"] = None


#: 链起点
GENESIS = _GENESIS


def chain_hash(prev_hash: str, row: Dict[str, Any]) -> str:
    """``sha256(prev_hash + canonical(row 去掉 hash))`` —— 追加式账本的**共用**哈希链构造。

    Audit 与 Run Registry 共用同一构造（**不各造一套**）。
    """
    body = {k: v for k, v in row.items() if k != "hash"}
    return hashlib.sha256((prev_hash + _canon(body)).encode("utf-8")).hexdigest()


def _canon(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class AuditLog:
    """独立 append-only 审计流（哈希链）。"""

    def __init__(self, path=None):
        self.path = Path(normalize_path(path or DEFAULT_AUDIT_PATH))

    # ---------------- 写 ----------------
    def record(
        self,
        kind: str,
        run_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
        layer: str = "",
        actor: str = "pes",
        severity: str = "info",
    ) -> Dict[str, Any]:
        """追加一条审计。**永不抛**（审计失败不得打断业务），但会在行内标 ``degraded``。"""
        with _LOCK:
            prev = self._last_hash()
            row = {
                "seq": self._next_seq(),
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "epoch": time.time(),
                "kind": str(kind),
                "run_id": str(run_id or ""),
                "qualified": bool(str(run_id or "").strip()),  # run_id 是资格位
                "layer": str(layer or ""),
                "actor": str(actor or "pes"),
                "severity": str(severity or "info"),
                "payload": payload or {},
                "pid": os.getpid(),
                "prev_hash": prev,
            }
            row["hash"] = hashlib.sha256((prev + _canon({k: v for k, v in row.items() if k != "hash"})).encode("utf-8")).hexdigest()
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            except Exception as e:
                row["degraded"] = "audit write failed: %s" % type(e).__name__
            return row

    def record_for_run(self, kind: str, run_id: str, **kw) -> Dict[str, Any]:
        """**要求 run_id 非空** 的收口写入口（M2 对账专用）。"""
        if not str(run_id or "").strip():
            raise ValueError("审计条目必须带 run_id（缺 run_id 的条目不合格，不计入对账证据）")
        return self.record(kind, run_id=run_id, **kw)

    # ---------------- 读 ----------------
    def tail(self, n: int = 100) -> List[Dict[str, Any]]:
        return self._all()[-int(n):]

    def for_run(self, run_id: str) -> List[Dict[str, Any]]:
        return [r for r in self._all() if r.get("run_id") == str(run_id)]

    def by_kind(self, kind: str) -> List[Dict[str, Any]]:
        return [r for r in self._all() if r.get("kind") == str(kind)]

    def unqualified(self) -> List[Dict[str, Any]]:
        """缺 run_id 的**不合格**条目（不得计入对账证据）。"""
        return [r for r in self._all() if not r.get("qualified")]

    # ---------------- 完整性 ----------------
    def verify_chain(self) -> Dict[str, Any]:
        """校验哈希链。返回 ``{ok, rows, first_bad_seq, detail}``。"""
        rows = self._all()
        prev = _GENESIS
        for r in rows:
            expect = hashlib.sha256(
                (prev + _canon({k: v for k, v in r.items() if k != "hash"})).encode("utf-8")
            ).hexdigest()
            if r.get("prev_hash") != prev or r.get("hash") != expect:
                return {
                    "ok": False,
                    "rows": len(rows),
                    "first_bad_seq": r.get("seq"),
                    "detail": "审计链在 seq=%s 断裂 ⇒ 该行之后不可信" % r.get("seq"),
                }
            prev = r.get("hash", "")
        return {"ok": True, "rows": len(rows), "first_bad_seq": None, "detail": "链完整（%d 条）" % len(rows)}

    def stats(self) -> Dict[str, Any]:
        rows = self._all()
        return {
            "path": self.path.as_posix(),
            "rows": len(rows),
            "qualified": sum(1 for r in rows if r.get("qualified")),
            "unqualified": sum(1 for r in rows if not r.get("qualified")),
            "kinds": sorted({r.get("kind", "") for r in rows}),
            "chain": self.verify_chain()["ok"],
        }

    # ---------------- 内部 ----------------
    def _all(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not self.path.exists():
            return out
        try:
            with open(self.path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        continue  # 坏行跳过，不炸
        except Exception:
            pass
        return out

    def _last_hash(self) -> str:
        rows = self._all()
        return rows[-1].get("hash", _GENESIS) if rows else _GENESIS

    def _next_seq(self) -> int:
        rows = self._all()
        try:
            return int(rows[-1].get("seq", 0)) + 1 if rows else 1
        except Exception:
            return len(rows) + 1


def audit_log(path=None) -> AuditLog:
    """进程内默认审计流（**独立于执行态**）。"""
    global _log
    if path is not None:
        return AuditLog(path)
    if _log is None:
        _log = AuditLog()
    return _log


__all__ = ["DEFAULT_AUDIT_PATH", "GENESIS", "chain_hash", "AuditLog", "audit_log"]