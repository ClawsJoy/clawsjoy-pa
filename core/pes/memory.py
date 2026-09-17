# -*- coding: utf-8 -*-
"""V9-PES · **Memory 层** —— 偏好 / 结论 / 上下文来源。

对应总任务书工程版 v1 §3.1（五层的第五层：Memory）与 §3.3（状态所有权第三层：
**上下文来源 —— 每条资产带 session_id / workspace / project**）。

设计纪律（与 Audit 层同构，**不另造一套**）：

1. **append-only JSONL + 哈希链**：只追加，不修改既有行；``forget`` 写的是
   **墓碑（tombstone）**，原记录**保留** —— 「忘掉」本身也必须留痕、可审计；
2. **哈希链共用** :func:`core.pes.audit.chain_hash`（``run_registry`` 亦同）；
3. **上下文来源三元组是资格位**：缺 ``session_id`` / ``workspace`` / ``project``
   任一者，记录标 ``qualified=False``，**不得作为跨会话恢复依据**
   （与 Audit 把 ``run_id`` 当资格位同构）；
4. **追加式账本不走** :class:`~core.pes.state_integrity.StateFile` 的
   「全文 sha256」判据 —— 两类东西的完整性保证方式不同（见
   :func:`core.pes.state_integrity.scan_state_dir` 的说明）。

零第三方依赖。
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.pes.audit import GENESIS, chain_hash
from core.pes.windows import REPO_ROOT, normalize_path

DEFAULT_MEMORY_PATH = REPO_ROOT / "data" / "v9" / "pes" / "memory.jsonl"

#: 三类记录（总任务书 §3.1 Memory：偏好 / 结论 / 上下文来源）
RECORD_KINDS = ("preference", "conclusion", "context")

#: 操作类型：``remember``（记）/ ``forget``（忘，写墓碑）
OPS = ("remember", "forget")

#: 上下文来源三元组（状态所有权第三层）
SOURCE_TRIPLE = ("session_id", "workspace", "project")

_LOCK = threading.RLock()
_mem: Optional["MemoryLog"] = None


def _jsonable(value: Any) -> Any:
    """把任意值收敛成可 JSON 往返的形态（不可序列化的部分转 str，**不抛**）。"""
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return str(value)


def _norm_source(source_ref: Optional[Dict[str, Any]]) -> Dict[str, str]:
    src = dict(source_ref or {})
    return {k: str(src.get(k) or "") for k in SOURCE_TRIPLE}


def _source_complete(src: Dict[str, str]) -> bool:
    return all(str(src.get(k) or "").strip() for k in SOURCE_TRIPLE)


def _record_id(row: Dict[str, Any]) -> str:
    body = {k: row.get(k) for k in ("seq", "ts", "op", "kind", "key", "value", "source_ref", "run_id", "target")}
    blob = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class MemoryLog:
    """个人记忆的 **append-only 账本**（偏好 / 结论 / 上下文来源）。

    **唯一写路径**是 :meth:`_append`：它负责 seq、哈希链与落盘。
    读侧一律走 :meth:`live`（当前有效记忆，墓碑已摘除）或 :meth:`rows`（全量原始行）。
    """

    def __init__(self, path=None):
        self.path = Path(normalize_path(path or DEFAULT_MEMORY_PATH))

    # ---------------- 写 ----------------
    def remember(
        self,
        kind: str,
        key: str,
        value: Any,
        source_ref: Optional[Dict[str, Any]] = None,
        run_id: str = "",
        tags: Optional[List[str]] = None,
        actor: str = "pa",
        note: str = "",
    ) -> Dict[str, Any]:
        """记一条记忆。``kind`` 必须是 :data:`RECORD_KINDS` 之一（**fail-closed**）。"""
        k = str(kind or "").strip()
        if k not in RECORD_KINDS:
            raise ValueError("记录类型必须是 %s 之一（收到 %r）" % ("/".join(RECORD_KINDS), kind))
        src = _norm_source(source_ref)
        return self._append(
            {
                "op": "remember",
                "kind": k,
                "key": str(key or ""),
                "value": _jsonable(value),
                "tags": [str(t) for t in (tags or [])],
                "source_ref": src,
                "run_id": str(run_id or ""),
                "qualified": bool(_source_complete(src)),
                "actor": str(actor or "pa"),
                "note": str(note or ""),
            }
        )

    def forget(self, record_id: str, reason: str = "", actor: str = "boss") -> Dict[str, Any]:
        """**可审计地忘掉**：追加一条墓碑，原记录保留（append-only 不被破坏）。"""
        rid = str(record_id or "").strip()
        if not rid:
            raise ValueError("forget 必须给出 record_id（不允许无目标地清空记忆）")
        return self._append(
            {
                "op": "forget",
                "kind": "",
                "key": "",
                "value": None,
                "tags": [],
                "target": rid,
                "source_ref": {},
                "run_id": "",
                # 墓碑本身是一次**操作**而非记忆，不需要上下文来源三元组；
                # 它是否合格由链完整性与 target 是否指向真实记录决定。
                "qualified": True,
                "actor": str(actor or "boss"),
                "note": str(reason or ""),
            }
        )

    def _append(self, row: Dict[str, Any]) -> Dict[str, Any]:
        with _LOCK:
            rows = self._raw()
            prev = rows[-1].get("hash", GENESIS) if rows else GENESIS
            full: Dict[str, Any] = {
                "seq": (int(rows[-1].get("seq", 0)) + 1) if rows else 1,
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "epoch": time.time(),
            }
            full.update(row)
            full["record_id"] = _record_id(full)
            full["prev_hash"] = prev
            full["hash"] = chain_hash(prev, full)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="") as f:
                f.write(json.dumps(full, ensure_ascii=False) + "\n")
            return full

    # ---------------- 读 ----------------
    def _raw(self) -> List[Dict[str, Any]]:
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

    def rows(self) -> List[Dict[str, Any]]:
        """全部原始行（**含墓碑**）—— 审计视图。"""
        return self._raw()

    def live(self) -> Dict[str, Dict[str, Any]]:
        """当前**有效**记忆（``record_id`` → 行）；墓碑已摘除，原行仍留在 :meth:`rows`。"""
        live: Dict[str, Dict[str, Any]] = {}
        for r in self._raw():
            op = r.get("op")
            if op == "remember":
                live[str(r.get("record_id"))] = r
            elif op == "forget":
                live.pop(str(r.get("target")), None)
        return live

    def recall(
        self,
        kind: Optional[str] = None,
        key: Optional[str] = None,
        project: Optional[str] = None,
        session_id: Optional[str] = None,
        workspace: Optional[str] = None,
        include_unqualified: bool = False,
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        """按条件取当前有效记忆，**新的在前**。

        默认**排除** ``qualified=False``（缺上下文来源三元组）的记录 ——
        它们不得作为跨会话恢复依据。
        """
        out: List[Dict[str, Any]] = []
        for r in self.live().values():
            if kind is not None and r.get("kind") != str(kind):
                continue
            if key is not None and r.get("key") != str(key):
                continue
            src = r.get("source_ref") or {}
            if project is not None and src.get("project") != str(project):
                continue
            if session_id is not None and src.get("session_id") != str(session_id):
                continue
            if workspace is not None and src.get("workspace") != str(workspace):
                continue
            if not include_unqualified and not r.get("qualified"):
                continue
            out.append(r)
        out.sort(key=lambda r: int(r.get("seq", 0)), reverse=True)
        if limit and int(limit) > 0:
            out = out[: int(limit)]
        return out

    def context_bundle(self, session_id: str = "", project: str = "", workspace: str = "") -> Dict[str, Any]:
        """跨会话恢复的**最小件**：偏好 + 结论 + 来源三元组（不靠人复述）。"""

        def _match(r: Dict[str, Any]) -> bool:
            src = r.get("source_ref") or {}
            if session_id and src.get("session_id") != str(session_id):
                return False
            if project and src.get("project") != str(project):
                return False
            if workspace and src.get("workspace") != str(workspace):
                return False
            return True

        rows = [r for r in self.live().values() if r.get("qualified") and _match(r)]
        rows.sort(key=lambda r: int(r.get("seq", 0)), reverse=True)
        return {
            "preferences": {r["key"]: r["value"] for r in rows if r.get("kind") == "preference" and r.get("key")},
            "conclusions": [
                {"key": r.get("key"), "value": r.get("value"), "run_id": r.get("run_id"), "ts": r.get("ts")}
                for r in rows
                if r.get("kind") == "conclusion"
            ],
            "sources": [r.get("source_ref") for r in rows if r.get("kind") == "context"],
            "count": len(rows),
        }

    def unqualified(self) -> List[Dict[str, Any]]:
        """缺上下文来源三元组的记录（**不得作为跨会话恢复依据**）。"""
        return [r for r in self._raw() if r.get("op") == "remember" and not r.get("qualified")]

    def verify_chain(self) -> Dict[str, Any]:
        """校验哈希链。返回 ``{ok, rows, first_bad_seq, detail}``。"""
        rows = self._raw()
        prev = GENESIS
        for r in rows:
            if r.get("prev_hash") != prev or r.get("hash") != chain_hash(prev, r):
                return {
                    "ok": False,
                    "rows": len(rows),
                    "first_bad_seq": r.get("seq"),
                    "detail": "记忆链在 seq=%s 断裂 ⇒ 该行之后不可信" % r.get("seq"),
                }
            prev = r.get("hash", "")
        return {"ok": True, "rows": len(rows), "first_bad_seq": None, "detail": "链完整（%d 条）" % len(rows)}

    def stats(self) -> Dict[str, Any]:
        rows = self._raw()
        live = self.live()
        return {
            "path": self.path.as_posix(),
            "rows": len(rows),
            "live": len(live),
            "tombstones": sum(1 for r in rows if r.get("op") == "forget"),
            "unqualified": len(self.unqualified()),
            "kinds": sorted({r.get("kind", "") for r in live.values() if r.get("kind")}),
            "projects": sorted(
                {
                    (r.get("source_ref") or {}).get("project", "")
                    for r in live.values()
                    if (r.get("source_ref") or {}).get("project")
                }
            ),
            "chain": self.verify_chain()["ok"],
        }


def memory_log(path=None) -> MemoryLog:
    """进程内默认记忆账本（传 ``path`` 则返回独立实例，便于测试隔离）。"""
    global _mem
    if path is not None:
        return MemoryLog(path)
    if _mem is None:
        _mem = MemoryLog()
    return _mem


__all__ = [
    "DEFAULT_MEMORY_PATH",
    "RECORD_KINDS",
    "OPS",
    "SOURCE_TRIPLE",
    "MemoryLog",
    "memory_log",
]
