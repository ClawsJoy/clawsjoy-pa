# -*- coding: utf-8 -*-
"""V9-PES · **Execution Contract 层** —— 在既有 P0-负三（``core.gateway.task_contract``）
**上补字段**，**不新造第二套契约**（总任务书 术语修正 ②，硬纪律）。

本模块**只做三件事**：

1. :func:`upgrade` —— 把既有契约（无新字段）**就地升级**为带 v1 字段集的契约，幂等、向后兼容；
2. :func:`verdict` —— **单一完成裁决**：把「agent 自报」与「机器验过」在数据上分开，
   并强制 **没有产物事实 ⇒ 永不 ``done``**（对治「假成交」）；
3. :func:`progress` —— **分子分母同源**判定（M2 判据④）：声明值与回报值不同源 ⇒ **标红，不取平均**。

补字段清单来自 ``批225 S1 run registry 最小字段集草案``，每条标注它对应的缺口：

| 字段 | 缺口 |
|---|---|
| ``done_when`` / ``done_when_status`` | Q6：业务完成判据在 v9 主链缺位 / 自报 vs 机验无法分离 |
| ``steps_total`` / ``steps_done`` / ``progress_source`` | Q5：分母造假（废除 ``len(plan or []) or 1`` 兜底） |
| ``idempotency_key`` / ``attempt_count`` / ``dedup_hits`` | Q1：幂等键缺 |
| ``constraints`` | Q4：约束不落 state ⇒ 跨轮不继承 |
| ``last_error`` / ``failure_memory_written`` | Q2：失败不写记忆 |
| ``workspace`` | W1 接线 / P0-4 判据②：工作副本与 seed 门凭证 |
| ``artifact`` / ``artifact_verified_by`` | P0-4 判据②③：产物**事实** + **谁验的** |
| ``source_ref`` / ``recorded_by`` | 状态所有权三层的可审计位 |
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

#: 新增（补）字段的默认值 —— ``upgrade`` 用它做幂等填充
CONTRACT_DEFAULTS: Dict[str, Any] = {
    # --- done_when（Q6）---
    "done_when": "",
    "done_when_status": "unset",          # unset | claimed | verified
    # --- 进度（Q5）---
    "steps_total": 0,
    "steps_done": 0,
    "progress_source": "declared",        # declared | reported
    # --- 幂等（Q1）---
    "idempotency_key": "",
    "attempt_count": 0,
    "dedup_hits": 0,
    # --- 约束（Q4）---
    "constraints": {"quota": "", "mode": "work", "risk_level": "R1", "approval_required": False},
    # --- 失败（Q2）---
    "last_error": {},
    "failure_memory_written": False,
    # --- 工作副本 / seed 门（W1）---
    "workspace": {"sandbox_dir": "", "seed_manifest_hash": "", "seed_status": ""},
    # --- 产物事实（P0-4 判据②③）---
    "artifact": {"path": "", "sha256": "", "bytes": 0, "exists": False, "kind": ""},
    "artifact_verified_by": "",
    # --- 来源与写者（状态所有权）---
    "source_ref": {"session_id": "", "workspace": "", "project": ""},
    "recorded_by": "v9",
}

#: ``done_when_status`` 合法取值（``claimed`` **不得**当完成依据）
DONE_WHEN_STATES = ("unset", "claimed", "verified")

#: **执行态**字段（唯一写者 = 执行链 v9）
EXECUTION_FIELDS = (
    "done_when", "done_when_status", "steps_total", "steps_done", "progress_source",
    "idempotency_key", "attempt_count", "dedup_hits", "constraints", "last_error",
    "failure_memory_written", "workspace", "artifact", "source_ref", "recorded_by",
)

#: **汇总态**字段（PA 独占写，append-only）—— PA 对执行态只读不改
SUMMARY_FIELDS = ("artifact_verified_by",)

ALL_FIELDS = EXECUTION_FIELDS + SUMMARY_FIELDS


def upgrade(contract: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """把既有契约（可能无新字段）**就地补齐**为 v1 字段集。

    幂等：已有值的字段**不覆盖**；``None``（无契约）→ 返回 ``{}``；
    空字典 ``{}`` 视作「一份还没填的契约」，**补齐为整份默认字段**
    （否则 ``new_run_fields`` 这类「从零起契约」的调用会直接 KeyError）。
    **不新造契约**：返回的就是同一份契约对象（浅拷贝），既有字段全部保留。
    """
    if contract is None:
        return {}
    c = dict(contract)
    for k, default in CONTRACT_DEFAULTS.items():
        if k not in c or c[k] is None:
            c[k] = dict(default) if isinstance(default, dict) else default
        elif isinstance(default, dict) and isinstance(c.get(k), dict):
            merged = dict(default)
            merged.update({kk: vv for kk, vv in c[k].items() if vv not in (None, "")})
            c[k] = merged
    if c.get("done_when_status") not in DONE_WHEN_STATES:
        c["done_when_status"] = "unset"
    return c


def new_contract(task_id: str, objective: str = "", nodes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """建契约：**复用既有** ``core.gateway.task_contract.new_contract``，**仅补字段**。"""
    from core.gateway.task_contract import new_contract as _existing_new

    base = _existing_new(task_id, objective=objective, nodes=nodes or [])
    c = upgrade(base)
    c["task_id"] = task_id
    c["objective"] = objective
    return c


# ============================== 完成裁决 ==============================
def verdict(contract: Optional[Dict[str, Any]], artifact_fact: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """**单一完成裁决**（M2 判据①②）。

    ``artifact_fact``：**独立取得**的产物事实（不由 agent 自报），形如
    ``{"path": ..., "exists": True, "sha256": ..., "bytes": ...}``。

    规则（写死，**不可协商**）：
      · ``done_when_status == "claimed"`` ⇒ **不构成完成**（agent 自报不算）；
      · 无产物事实（``artifact.exists`` 为假）⇒ **永不 done**（假成交红线）；
      · ``done_when_status == "verified"`` 且产物存在 ⇒ ``done``；
      · 其余 ⇒ ``not_done``，并给出**可读**的下一条动作。
    """
    if not contract:
        return {"state": "not_done", "reason": "no_contract", "message": "没有契约，无法裁决完成。", "next_action": "先建契约"}
    c = upgrade(contract)
    fact = artifact_fact if artifact_fact is not None else c.get("artifact") or {}
    exists = bool(fact.get("exists"))
    dws = c.get("done_when_status")
    claimed_only = dws == "claimed"

    if not exists:
        return {
            "state": "not_done",
            "reason": "no_artifact_fact",
            "message": "声称完成的依据不足：**没有产物事实**（文件不存在或未独立验证）。",
            "next_action": "生成产物并落盘，再由独立进程复核；或明确报告卡在哪里。",
        }
    if claimed_only:
        return {
            "state": "not_done",
            "reason": "claimed_only",
            "message": "agent 自报完成（claimed），**未经机器验证**，不得作为完成依据。",
            "next_action": "由独立验证者写入 artifact_verified_by 并把 done_when_status 置 verified。",
        }
    if dws == "verified":
        return {
            "state": "done",
            "reason": "verified",
            "message": "产物存在且已独立验证。",
            "next_action": "",
            "verified_by": c.get("artifact_verified_by", ""),
        }
    return {
        "state": "not_done",
        "reason": "done_when_unset",
        "message": "业务完成判据（done_when）尚未设置或未验证。",
        "next_action": "补 done_when 文本并跑验证。",
    }


def record_artifact(
    contract: Dict[str, Any], path: str, kind: str = "", verified_by: str = ""
) -> Dict[str, Any]:
    """把**产物事实**写进契约（``exists`` 由**磁盘实况**决定，不由调用方声称）。"""
    from pathlib import Path

    c = upgrade(contract)
    p = Path(str(path))
    fact = {"path": str(path), "kind": str(kind or ""), "exists": False, "sha256": "", "bytes": 0}
    try:
        if p.is_file():
            data = p.read_bytes()
            fact["exists"] = True
            fact["bytes"] = len(data)
            fact["sha256"] = hashlib.sha256(data).hexdigest()
    except Exception:
        fact["exists"] = False
    c["artifact"] = fact
    if verified_by:
        c["artifact_verified_by"] = str(verified_by)
        c["done_when_status"] = "verified"
    if fact["exists"]:
        c["recorded_by"] = "v9"
    return c


def mark_claimed(contract: Dict[str, Any], done_when: str = "") -> Dict[str, Any]:
    """agent 自报完成 ⇒ 只置 ``claimed``（**永不动 ``verified``**）。"""
    c = upgrade(contract)
    if done_when:
        c["done_when"] = str(done_when)
    if c.get("done_when_status") != "verified":
        c["done_when_status"] = "claimed"
    return c


# ============================== 进度（分子分母同源） ==============================
def progress(contract: Optional[Dict[str, Any]], reported_done: Optional[int] = None) -> Dict[str, Any]:
    """进度判定（M2 判据④：**分子分母同源**）。

    分母**必须来自声明**（``steps_total`` 由 plan 显式给出）；
    **禁止** ``len(plan or []) or 1`` 这类兜底推定。
    声明值与回报值**不同源**时 **标红（``mismatch=True``）**，**不取平均、不静默择一**。
    """
    c = upgrade(contract)
    total = int(c.get("steps_total") or 0)
    done = int(c.get("steps_done") or 0)
    out = {
        "total": total,
        "done": done,
        "source": c.get("progress_source", "declared"),
        "mismatch": False,
        "message": "",
    }
    if total <= 0:
        out["mismatch"] = True
        out["message"] = "分母未声明（steps_total<=0）⇒ 不显示百分比（宁可不显示，不做假仪表盘）。"
        return out
    if reported_done is not None and int(reported_done) != done:
        out["mismatch"] = True
        out["reported_done"] = int(reported_done)
        out["message"] = "声明步数(%d) 与回报步数(%d) 不同源 ⇒ 标红，不取平均。" % (done, int(reported_done))
        return out
    out["percent"] = round(100.0 * done / total, 1)
    return out


# ============================== 幂等 ==============================
def idempotency_key(run_id: str, task_digest: str) -> str:
    """``sha256(run_id + task_digest)`` —— 重复投递识别键（Q1）。"""
    return hashlib.sha256(("%s|%s" % (run_id, task_digest)).encode("utf-8")).hexdigest()


def digest_task(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def new_run_fields(run_id: str, task_text: str, steps_total: int, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """一次运行的**新增字段初值**（执行态；写者 = v9）。"""
    c = upgrade({})
    c.update(
        {
            "idempotency_key": idempotency_key(run_id, digest_task(task_text)),
            "steps_total": int(steps_total or 0),
            "steps_done": 0,
            "progress_source": "declared",
            "constraints": dict(constraints or c["constraints"]),
            "recorded_by": "v9",
            "created_at": time.time(),
        }
    )
    return c


def validate(contract: Optional[Dict[str, Any]]) -> List[str]:
    """字段级校验（返回问题清单，空 = 合规）。"""
    problems: List[str] = []
    if not contract:
        return ["契约为空"]
    c = upgrade(contract)
    for k in ALL_FIELDS:
        if k not in c:
            problems.append("缺字段 %s" % k)
    if c.get("done_when_status") not in DONE_WHEN_STATES:
        problems.append("done_when_status 非法：%r" % c.get("done_when_status"))
    if c.get("recorded_by") not in ("v9", "pa"):
        problems.append("recorded_by 非法：%r" % c.get("recorded_by"))
    if not isinstance(c.get("artifact"), dict):
        problems.append("artifact 必须是对象")
    if int(c.get("steps_total") or 0) < 0:
        problems.append("steps_total 不得为负")
    return problems


def ownership_of(field: str) -> str:
    """字段的**写权归属**（状态所有权三层）—— ``execution`` 或 ``summary``。"""
    if field in SUMMARY_FIELDS:
        return "summary"
    if field in EXECUTION_FIELDS:
        return "execution"
    return "unknown"


__all__ = [
    "CONTRACT_DEFAULTS",
    "DONE_WHEN_STATES",
    "EXECUTION_FIELDS",
    "SUMMARY_FIELDS",
    "ALL_FIELDS",
    "upgrade",
    "new_contract",
    "verdict",
    "record_artifact",
    "mark_claimed",
    "progress",
    "idempotency_key",
    "digest_task",
    "new_run_fields",
    "validate",
    "ownership_of",
]
