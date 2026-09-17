# -*- coding: utf-8 -*-
"""V9-PES · **Run Registry（汇总态）** —— PA 独占写、append-only、原子。

对应总任务书 §3.3 状态所有权三层 与 §5 M2；字段集来自
``批225 S1 run registry 最小字段集草案``（18 条最小集，**不扩张**）。

三条硬边界（**不得越**）：

1. **PA 对执行态只读不改** —— :meth:`RunRegistry.update_from_source` 只能把**来源回报的字段值**
   投影进来（``recorded_by="v9"``），**PA 不代填**；
2. **PA 独占写的只有** :meth:`RunRegistry.verify_artifact`（``artifact_verified_by``，字段 15）；
3. **「Registry 是投影，不是新真源」**（批235）—— 事实由来源 Contract 回报，
   **不得为取事实去读来源的生成日志**。

反例（对账硬判据）：**声称完成但 registry 无该 run_id ⇒ 判「未完成」**（不许用 stream complete 充数）。
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.pes.audit import GENESIS, chain_hash
from core.pes.windows import REPO_ROOT, normalize_path

DEFAULT_RUNS_PATH = REPO_ROOT / "data" / "v9" / "pes" / "runs.jsonl"

#: 运行状态机（新增 ``partial_success`` / ``waiting_approval`` 为**显式态**）
RUN_STATES = ("running", "waiting_approval", "blocked", "partial_success", "done", "failed")

#: 只有 PA 能写的字段（汇总态）
PA_OWNED_FIELDS = ("artifact_verified_by",)

#: 执行态字段（PA **只读**；只能由来源回报投影进来）
SOURCE_OWNED_FIELDS = (
    "state", "steps_total", "steps_done", "progress_source", "idempotency_key",
    "attempt_count", "dedup_hits", "done_when", "done_when_status", "constraints",
    "last_error", "failure_memory_written", "workspace", "artifact",
    "started_at", "heartbeat_at", "ended_at",
)

_DEFAULTS: Dict[str, Any] = {
    "run_id": "",
    "session_id": "", "user_id": "", "turn_id": "",
    "state": "",
    "steps_total": 0, "steps_done": 0, "progress_source": "",
    "idempotency_key": "", "attempt_count": 0, "dedup_hits": 0,
    "done_when": "", "done_when_status": "unset",
    "constraints": {}, "last_error": {}, "failure_memory_written": False,
    "workspace": {}, "artifact": {}, "artifact_verified_by": "",
    "started_at": 0, "heartbeat_at": 0, "ended_at": 0,
    "source_ref": {}, "recorded_by": "",
}

_LOCK = threading.RLock()


class RunRegistry:
    """汇总态注册表（append-only JSONL + 哈希链 + 投影）。"""

    def __init__(self, path=None):
        self.path = Path(normalize_path(path or DEFAULT_RUNS_PATH))

    # ---------------- 追加（唯一写路径） ----------------
    def _append(self, kind: str, run_id: str, fields: Dict[str, Any], actor: str = "pa") -> Dict[str, Any]:
        with _LOCK:
            rows = self._raw()
            prev = rows[-1].get("hash", GENESIS) if rows else GENESIS
            row = {
                "seq": (int(rows[-1].get("seq", 0)) + 1) if rows else 1,
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "kind": str(kind),
                "run_id": str(run_id),
                "actor": str(actor),
                "fields": fields or {},
                "prev_hash": prev,
            }
            row["hash"] = chain_hash(prev, row)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return row

    # ---------------- 写：来源回报（PA 不代填） ----------------
    def register_run(self, run_id: str, **fields) -> Dict[str, Any]:
        """新建一次运行的汇总条目（PA 侧登记，``recorded_by`` 记来源标记）。"""
        payload = {k: v for k, v in fields.items() if k in SOURCE_OWNED_FIELDS or k in ("session_id", "user_id", "turn_id", "source_ref")}
        payload.setdefault("started_at", time.time())
        payload.setdefault("state", "running")
        payload.setdefault("recorded_by", "v9")
        self._append("run_registered", run_id, payload)
        return self.get(run_id) or {}

    def update_from_source(self, run_id: str, reported: Dict[str, Any]) -> Dict[str, Any]:
        """把**来源 Contract 回报**的执行态字段投影进来。

        **PA 不代填**：只接受 :data:`SOURCE_OWNED_FIELDS` 内、且带 ``recorded_by`` 的值；
        越界字段**丢弃并留痕**（不静默）。
        """
        clean: Dict[str, Any] = {}
        rejected: List[str] = []
        for k, v in (reported or {}).items():
            if k in PA_OWNED_FIELDS:
                rejected.append(k)
                continue
            if k in SOURCE_OWNED_FIELDS or k in ("session_id", "user_id", "turn_id", "source_ref"):
                clean[k] = v
            else:
                rejected.append(k)
        clean.setdefault("recorded_by", "v9")
        clean["heartbeat_at"] = time.time()
        if "state" in clean and clean["state"] not in RUN_STATES:
            rejected.append("state=%r" % clean["state"])
            clean.pop("state", None)
        self._append("source_reported", run_id, clean, actor=str(reported.get("recorded_by", "v9")))
        if rejected:
            self._append("fields_rejected", run_id, {"rejected": sorted(set(rejected))}, actor="pa")
        return self.get(run_id) or {}

    # ---------------- 写：PA 独占的那一个字段 ----------------
    def verify_artifact(self, run_id: str, by: str, artifact_fact: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """**独立复验**：谁能验、验的是什么（对治「自己说的不算」）。"""
        if not str(by or "").strip():
            raise ValueError("复验必须留下验证者身份（by 不得为空）")
        fields: Dict[str, Any] = {"artifact_verified_by": str(by)}
        if artifact_fact:
            fields["artifact"] = dict(artifact_fact)
        self._append("artifact_verified", run_id, fields, actor="pa")
        try:
            from core.pes.audit import audit_log

            audit_log().record_for_run(
                "registry.artifact_verified", run_id, payload={"by": by}, layer="Run Registry", actor="pa"
            )
        except Exception:
            pass
        return self.get(run_id) or {}

    # ---------------- 读（投影） ----------------
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
                        continue
        except Exception:
            pass
        return out

    def get(self, run_id: str) -> Optional[Dict[str, Any]]:
        rid = str(run_id)
        rows = [r for r in self._raw() if r.get("run_id") == rid]
        if not rows:
            return None
        doc = dict(_DEFAULTS)
        doc["run_id"] = rid
        for r in rows:
            for k, v in (r.get("fields") or {}).items():
                doc[k] = v
        return doc

    def has(self, run_id: str) -> bool:
        return self.get(run_id) is not None

    def list_runs(self) -> List[Dict[str, Any]]:
        ids: List[str] = []
        for r in self._raw():
            rid = r.get("run_id")
            if rid and rid not in ids:
                ids.append(rid)
        return [d for d in (self.get(i) for i in ids) if d]

    def open_runs(self) -> List[Dict[str, Any]]:
        return [d for d in self.list_runs() if d.get("state") in ("running", "waiting_approval")]

    # ---------------- 对账（M2 / S2） ----------------
    def incomplete_claims(self) -> List[Dict[str, Any]]:
        """**声称完成但没有产物事实** 的 run（「假成交」的机械判据）。"""
        bad = []
        for d in self.list_runs():
            art = d.get("artifact") or {}
            if d.get("state") in ("done", "partial_success") and not art.get("exists"):
                bad.append({"run_id": d.get("run_id"), "state": d.get("state"), "reason": "声称完成但无产物事实"})
            if d.get("done_when_status") == "claimed" and d.get("state") == "done":
                bad.append({"run_id": d.get("run_id"), "state": d.get("state"), "reason": "仅 claimed，未经机器验证"})
        return bad

    def reconcile(self, run_id: str, source_fact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """与来源比对：``consistent`` / ``registry_missing`` / ``source_missing``。

        **不一致必须产生可见告警**（页面 + 审计流），不得静默（对账层 §③）。
        """
        mine = self.get(run_id)
        if mine is None:
            out = {"run_id": str(run_id), "result": "registry_missing", "warning": "来源有该 run，但 Registry 无 ⇒ 判未完成"}
        elif source_fact is None:
            out = {"run_id": str(run_id), "result": "source_missing", "warning": "Registry 有该 run，但来源已丢 ⇒ 升级告警"}
        else:
            mism: List[str] = []
            if source_fact.get("state") and source_fact.get("state") != mine.get("state"):
                mism.append("state: registry=%r source=%r" % (mine.get("state"), source_fact.get("state")))
            sf_art = source_fact.get("artifact") or {}
            my_art = mine.get("artifact") or {}
            if sf_art.get("exists") is not None and bool(sf_art.get("exists")) != bool(my_art.get("exists")):
                mism.append("artifact.exists: registry=%r source=%r" % (my_art.get("exists"), sf_art.get("exists")))
            if mism:
                out = {"run_id": str(run_id), "result": "inconsistent", "differences": mism, "warning": "对账不一致 ⇒ 必须可见告警"}
            else:
                out = {"run_id": str(run_id), "result": "consistent", "differences": []}
        if out["result"] != "consistent":
            try:
                from core.pes.audit import audit_log

                audit_log().record_for_run(
                    "registry.reconcile_%s" % out["result"], run_id,
                    payload={"warning": out.get("warning"), "differences": out.get("differences", [])},
                    layer="Run Registry", severity="warn", actor="pa",
                )
            except Exception:
                pass
        return out

    # ---------------- 完整性 ----------------
    def verify_chain(self) -> Dict[str, Any]:
        rows = self._raw()
        prev = GENESIS
        for r in rows:
            if r.get("prev_hash") != prev or r.get("hash") != chain_hash(prev, r):
                return {"ok": False, "rows": len(rows), "first_bad_seq": r.get("seq"),
                        "detail": "Registry 链在 seq=%s 断裂" % r.get("seq")}
            prev = r.get("hash", "")
        return {"ok": True, "rows": len(rows), "first_bad_seq": None, "detail": "链完整（%d 条）" % len(rows)}


__all__ = ["DEFAULT_RUNS_PATH", "RUN_STATES", "PA_OWNED_FIELDS", "SOURCE_OWNED_FIELDS", "RunRegistry"]