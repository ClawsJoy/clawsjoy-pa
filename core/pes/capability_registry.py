# -*- coding: utf-8 -*-
"""V9-PES · **Capability Registry 层** —— 能力清单 + 门禁 + 风险等级。

对应总任务书工程版 v1 §3.1 与 §5 M3：
「① 工具/技能/**风险等级**/门禁 ② **新能力注册即受管** ③ 权限分级器与 Registry 联动」。

**唯一安全性质（fail-closed）**：**未注册的能力一律拒绝**。
这意味着「新写一个工具忘了配权限」不会变成**默认放行**，而是**默认拒绝** ——
这是本层存在的全部理由。

风险等级（沿用 ``主权控制面设计_20260913`` §4.4 的分级与撤销窗口）：

| 级 | 语义 | 例子 | 撤销窗口 |
|---|---|---|---|
| **R0** | 只读 | 读文件、读页面 | 无 |
| **R1** | 本地写 | 写文件、跑脚本 | 0（执行前可撤） |
| **R2** | 对外可逆 | 发邮件、发消息 | 30–120s |
| **R3** | 不可逆 | 发布 / 付款 / 删除 / 清空 | 300–900s |

本注册表**自身走 State Integrity 唯一出口**（dogfooding：连权限配置都不许裸写 JSON）。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.pes.windows import REPO_ROOT

#: 风险等级 → 门禁要求（撤销窗口/是否需审批）
RISK_LEVELS: Dict[str, Dict[str, Any]] = {
    "R0": {"label": "只读", "approval_required": False, "window_s": 0, "examples": "读文件/读页面/检索"},
    "R1": {"label": "本地写", "approval_required": False, "window_s": 0, "examples": "写文件/跑脚本/改代码"},
    "R2": {"label": "对外可逆", "approval_required": True, "window_s": 120, "examples": "发邮件/发消息/外部 API 调用"},
    "R3": {"label": "不可逆", "approval_required": True, "window_s": 900, "examples": "发布/付款/删除/清空"},
}

DEFAULT_REGISTRY_PATH = REPO_ROOT / "data" / "v9" / "pes" / "capabilities.json"

#: 内置种子能力（**新能力必须显式注册**才可用）
_SEED_CAPS: List[Dict[str, Any]] = [
    {"name": "read_file", "kind": "tool", "risk_level": "R0", "description": "读文件"},
    {"name": "list_dir", "kind": "tool", "risk_level": "R0", "description": "列目录"},
    {"name": "fetch_web", "kind": "tool", "risk_level": "R0", "description": "读网页"},
    {"name": "screenshot", "kind": "tool", "risk_level": "R0", "description": "截屏"},
    {"name": "write_file", "kind": "tool", "risk_level": "R1", "description": "写文件"},
    {"name": "execute_command", "kind": "tool", "risk_level": "R1", "description": "执行命令"},
    {"name": "git_commit", "kind": "tool", "risk_level": "R1", "description": "沙箱内提交"},
    {"name": "browser_click", "kind": "action", "risk_level": "R1", "description": "点击页面元素"},
    {"name": "send_message", "kind": "action", "risk_level": "R2", "description": "对外发消息"},
    {"name": "publish", "kind": "action", "risk_level": "R3", "description": "对外发布"},
    {"name": "git_push", "kind": "action", "risk_level": "R3", "description": "推远程"},
    {"name": "delete", "kind": "action", "risk_level": "R3", "description": "删除"},
]


class CapabilityRegistry:
    """能力注册表（持久化走 State Integrity 唯一出口）。"""

    def __init__(self, path=None, state_store=None):
        self.path = str(path or DEFAULT_REGISTRY_PATH)
        self._store = state_store

    def _store_obj(self):
        if self._store is None:
            from core.pes.state_integrity import StateFile

            self._store = StateFile(self.path, writer="pes.capability_registry", seed_keys=())
        return self._store

    # ---------------- 读 ----------------
    def _caps(self) -> Dict[str, Dict[str, Any]]:
        d = self._store_obj().read().data or {}
        caps = d.get("capabilities")
        if not isinstance(caps, dict):
            caps = {}
        return caps

    def ensure_seeded(self) -> int:
        """种下内置能力（幂等）。返回新增条数。"""
        added = {"n": 0}

        def _mut(d):
            caps = d.setdefault("capabilities", {})
            for c in _SEED_CAPS:
                if c["name"] not in caps:
                    caps[c["name"]] = _norm(c)
                    added["n"] += 1

        self._store_obj().update_runtime(_mut, writer="pes.capability_registry", reason="ensure_seeded")
        return added["n"]

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._caps().get(str(name))

    def require(self, name: str) -> Dict[str, Any]:
        """**fail-closed**：未注册 ⇒ 抛错（调用方不得自行兜底放行）。"""
        c = self.get(name)
        if c is None:
            raise PermissionError(
                "能力 `%s` 未在 Capability Registry 注册 ⇒ 拒绝执行（未注册即拒绝）。"
                "如需使用，请先 register() 并声明风险等级与门禁。" % name
            )
        return c

    def is_registered(self, name: str) -> bool:
        return self.get(name) is not None

    def list(self) -> List[Dict[str, Any]]:
        return sorted(self._caps().values(), key=lambda x: (x.get("risk_level", ""), x.get("name", "")))

    def by_risk(self, level: str) -> List[Dict[str, Any]]:
        return [c for c in self.list() if c.get("risk_level") == str(level).upper()]

    # ---------------- 写 ----------------
    def register(
        self,
        name: str,
        kind: str = "tool",
        risk_level: str = "R3",
        description: str = "",
        gates: Optional[List[str]] = None,
        requires_grant: bool = True,
        owner_layer: str = "",
    ) -> Dict[str, Any]:
        """注册一个能力 —— **注册即受管**。

        默认值取**最保守**：``risk_level="R3"``、``requires_grant=True``
        （忘填参数时得到的是最严的门，不是最松的门）。
        """
        lvl = str(risk_level or "R3").upper()
        if lvl not in RISK_LEVELS:
            raise ValueError("风险等级必须是 %s 之一（收到 %r）" % ("/".join(RISK_LEVELS), risk_level))
        rec = _norm(
            {
                "name": str(name),
                "kind": str(kind or "tool"),
                "risk_level": lvl,
                "description": str(description or ""),
                "gates": list(gates or ([] if not RISK_LEVELS[lvl]["approval_required"] else ["boss_approval"])),
                "requires_grant": bool(requires_grant),
                "owner_layer": str(owner_layer or ""),
                "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        def _mut(d):
            d.setdefault("capabilities", {})[rec["name"]] = rec

        self._store_obj().update_runtime(_mut, writer="pes.capability_registry", reason="register:%s" % name)
        try:
            from core.pes.audit import audit_log

            audit_log().record(
                "capability.registered",
                payload={"name": rec["name"], "risk_level": lvl, "gates": rec["gates"]},
                layer="Capability Registry",
                actor="pes",
            )
        except Exception:
            pass
        return rec

    def unregister(self, name: str) -> bool:
        gone = {"n": 0}

        def _mut(d):
            caps = d.setdefault("capabilities", {})
            if str(name) in caps:
                caps.pop(str(name))
                gone["n"] += 1

        self._store_obj().update_runtime(_mut, writer="pes.capability_registry", reason="unregister:%s" % name)
        return gone["n"] > 0

    # ---------------- 门禁 ----------------
    def gate_for(self, name: str) -> Dict[str, Any]:
        """该能力的门禁要求（**未注册 ⇒ 拒绝**，不返回宽松默认值）。"""
        c = self.require(name)
        lvl = c.get("risk_level", "R3")
        spec = RISK_LEVELS.get(lvl, RISK_LEVELS["R3"])
        return {
            "name": c["name"],
            "risk_level": lvl,
            "risk_label": spec["label"],
            "approval_required": bool(spec["approval_required"]),
            "window_s": int(spec["window_s"]),
            "requires_grant": bool(c.get("requires_grant", True)),
            "gates": list(c.get("gates") or []),
        }


def _norm(rec: Dict[str, Any]) -> Dict[str, Any]:
    lvl = str(rec.get("risk_level") or "R3").upper()
    spec = RISK_LEVELS.get(lvl, RISK_LEVELS["R3"])
    out = dict(rec)
    out["risk_level"] = lvl
    out["risk_label"] = spec["label"]
    out["approval_required"] = bool(spec["approval_required"])
    out["window_s"] = int(spec["window_s"])
    out.setdefault("gates", [])
    out.setdefault("requires_grant", True)
    return out


__all__ = ["RISK_LEVELS", "DEFAULT_REGISTRY_PATH", "CapabilityRegistry"]
