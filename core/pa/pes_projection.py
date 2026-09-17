# -*- coding: utf-8 -*-
"""V9-PES · M2-A **只读投影层**（可见性闭环 · Step 1）。

对应设计稿：``codex/2026-09-17-v9pes-m2a-visibility-closure-design.md`` §4.2 / §6 Step 1。

把**已存在**的读侧事实（Run Registry 汇总态 + P0-负三 契约）投影成**一张只读视图**，
供 PA 页面渲染三张卡。它**不是**新真源，也**不是** writer。

三条机械保证（设计稿 §4.2，全部可被 ``tests/pes/test_m2a_projection.py`` 铉死）:

* **P1 未知即未知**：未取到的字段**显式置 ``None``**（前端渲染「未核验 / 未记录」）；
  **禁止默认值填充** —— 本模块不用 ``or 0`` / ``or ""`` / ``or []`` / ``bool()`` 做**兜底**。
* **P2 派生态一律后端算**：百分比、是否存在、下一步动作，全部在**这里**算完；
  前端只做字符串化，**不允许自己推导**（否则就是「假仪表盘」与「假撤销」）。
* **P3 投影层无写权**：只 import 读接口（``RunRegistry.list_runs/verify_chain``、
  ``core.gateway.task_contract.load``、``core.pes.contract.verdict/progress``）；
  **不 import 任何写函数**（``_append`` / ``register_run`` / ``update_from_source`` /
  ``verify_artifact`` / ``record_artifact`` / ``mark_claimed`` / ``HoldQueue.hold`` / ``reduce``），
  **不对文件系统做任何写**。本模块**不提供任何 writer**。

**实如标注（Step 1 范围内故意留 ``None`` 的字段，属 Step 3 逐卡接线）**:

|字段|为什么这里没有|
|---|---|
|``blocked.layer`` / ``blocked.blocked_action`` / ``blocked.evidence_ref``|需读 audit 流 / ``goal_blocked_*.json``，属 Step 3 阻断卡接线|
|``blocked.unblock_hint``|需 ``Authorizer.explain()``，属 Step 3|
|``approval``|审批实源（``write_gate._pending_writes``）是 **session 级**，与 run **无共同键** ⇒ **不臆造关联**，恒 ``None``；审批卡本身也排 Step 3 最后|

**边界**：本模块不调 ``contract.reduce()``、不投任何事件、不调 ``RunRegistry.reconcile()``（它会写审计流）。
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.gateway.task_contract import load as _load_p0_contract
from core.pes import contract as pes_contract
from core.pes.run_registry import DEFAULT_RUNS_PATH, RunRegistry

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _k(d: Any, key: str) -> Any:
    """**P1**：取不到就是 ``None``——不兜底、不造值。"""
    if not isinstance(d, dict):
        return None
    return d.get(key)


def _blank(v: Any) -> Any:
    """把「**已知的空哨兵**」（``""``）译成 ``None``。

    这不是补默认值，是把「没有签署者」这个**已知事实**翻译成「未记录」的统一形式，
    以便前端只有**一条**渲染规则（``None`` → 「未核验 / 未记录」）。
    """
    if v is None or v == "":
        return None
    return v


def _ts(v: Any) -> Any:
    """时间戳：``0``（Registry 的「未记录」哨兵）译成 ``None``。"""
    if not v:
        return None
    return v


def _load_contract(run_id: str, contracts_dir: Any = None) -> Optional[Dict[str, Any]]:
    """只读取契约（P0-负三的唯一真相文件）。

    ``contracts_dir`` 仅供测试/多环境**注入**；默认走既有读接口 :func:`task_contract.load`。
    """
    if not run_id:
        return None
    if contracts_dir is None:
        return _load_p0_contract(run_id)
    p = Path(contracts_dir) / (str(run_id) + ".json")
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _progress_view(contract: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """**P2** 进度：分母必须来自契约**声明**；无契约 ⇒ 分子分母均未知。"""
    if not contract:
        return {"total": None, "done": None, "source": None, "mismatch": True,
                "message": "无契约 ⇒ 无进度依据（不显示百分比）。"}
    return pes_contract.progress(contract)


def _artifact_view(row: Any, contract: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """产物事实：优先读**契约**（``record_artifact()`` 的落点＝磁盘实况），
    契约缺失时回落到**注册表行**的来源回报；两边都取不到 ⇒ 全 ``None``。
    """
    c_art = _k(contract, "artifact")
    r_art = _k(row, "artifact")
    src = c_art if (isinstance(c_art, dict) and c_art) else r_art
    return {
        "path": _blank(_k(src, "path")),
        "exists": _k(src, "exists"),
        "sha256": _blank(_k(src, "sha256")),
        "bytes": _k(src, "bytes"),
        "verified_by": _blank(_k(row, "artifact_verified_by")),
        "done_when_status": _blank(_k(row, "done_when_status")),
    }


def _blocked_view(row: Any, run_id: str) -> Optional[Dict[str, Any]]:
    """阻断卡骨架：只读注册表行；未接线字段显式 ``None``（见模块 docstring）。"""
    if _k(row, "state") != "blocked":
        return None
    err = _k(row, "last_error")
    at = _ts(_k(row, "heartbeat_at"))
    if at is None:
        at = _ts(_k(row, "ended_at"))
    return {
        "block_id": str(run_id),
        "blocked_at": at,
        "layer": _blank(_k(err, "layer")),
        "reason": _blank(_k(err, "message")),
        "blocked_action": _blank(_k(err, "tool")),
        "evidence_ref": None,
        "unblock_hint": None,
        "state_map_key": "blocked",
    }


def _project_run(row: Any, degradations: List[Dict[str, Any]], contracts_dir: Any) -> Dict[str, Any]:
    run_id = str(_k(row, "run_id") or "")
    contract = _load_contract(run_id, contracts_dir)
    if contract is None:
        degradations.append({
            "code": "contract_missing", "run_id": run_id,
            "message": "该 run 无契约 ⇒ 完成裁决为 ``no_contract``（不代填）",
        })
    c_art = _k(contract, "artifact")
    r_art = _k(row, "artifact")
    if isinstance(c_art, dict) and isinstance(r_art, dict) and c_art and r_art:
        # 这里的 bool() 是**比较**（判两边是否一致），不是兜底填值 —— P1 禁的是后者。
        if bool(_k(c_art, "exists")) != bool(_k(r_art, "exists")):
            degradations.append({
                "code": "artifact_source_mismatch", "run_id": run_id,
                "message": "契约 artifact.exists=%r 与注册表回报 artifact.exists=%r 不一致 ⇒ 列为降级信号（本模块**不**调 reconcile，避免写审计流）"
                           % (_k(c_art, "exists"), _k(r_art, "exists")),
            })
    return {
        "run_id": run_id,
        "state": _blank(_k(row, "state")),
        "steps_total": _k(row, "steps_total"),
        "steps_done": _k(row, "steps_done"),
        "progress": _progress_view(contract),
        "artifact": _artifact_view(row, contract),
        "verdict": pes_contract.verdict(contract, None),
        "blocked": _blocked_view(row, run_id),
        "approval": None,
    }


def project_runs(session_id: Optional[str] = None, user_id: Optional[str] = None,
                 limit: int = DEFAULT_LIMIT, runs_path: Any = None,
                 contracts_dir: Any = None) -> Dict[str, Any]:
    """**只读**投影：设计稿 §6 Step 1 的返回形状。

    空库 / 无落盘 ⇒ ``runs: []`` + ``degradations``，**不抛异常、不 500**。
    """
    degradations: List[Dict[str, Any]] = []
    reg = RunRegistry(runs_path or DEFAULT_RUNS_PATH)
    if not reg.path.exists():
        degradations.append({
            "code": "registry_file_missing",
            "message": "Run Registry 尚无落盘（%s）⇒ 无任何 run 可投影；这不是错误。" % reg.path,
        })
    else:
        chain = reg.verify_chain()
        if not chain.get("ok"):
            degradations.append({"code": "registry_chain_broken",
                                 "message": chain.get("detail") or "Registry 哈希链断裂"})

    rows = reg.list_runs()
    if session_id:
        rows = [r for r in rows if _k(r, "session_id") == session_id]
    if user_id:
        rows = [r for r in rows if _k(r, "user_id") == user_id]
    rows = sorted(rows, key=lambda r: _ts(_k(r, "started_at")) or 0, reverse=True)

    try:
        cap = int(limit)
    except Exception:
        cap = DEFAULT_LIMIT
    cap = max(1, min(cap, MAX_LIMIT))
    if len(rows) > cap:
        degradations.append({
            "code": "limit_truncated",
            "message": "匹配 %d 条 > limit %d ⇒ 只返回最近的 %d 条" % (len(rows), cap, cap),
        })
        rows = rows[:cap]

    return {
        "success": True,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "runs": [_project_run(r, degradations, contracts_dir) for r in rows],
        "degradations": degradations,
    }


__all__ = ["DEFAULT_LIMIT", "MAX_LIMIT", "project_runs"]
