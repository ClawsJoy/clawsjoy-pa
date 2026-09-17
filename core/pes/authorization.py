# -*- coding: utf-8 -*-
"""V9-PES · **权限模型** —— 两套授权 + 转换层（总任务书第四章「权限模型」）。

> **两套授权 + 转换层：老板级（人对 PA）/ agent 级（PA 对执行体）；==不可合并==**
> 风险分层 + 涉密/外发/花钱逐次确认。

| 授权 | 谁给谁 | 存哪 | 语义 |
|---|---|---|---|
| **老板级** | 老板 → PA | :class:`BossGrantStore` | 权限档：``只读`` / ``标准`` / ``高(需确认)``（**沿用既有 ``core/pa/permission.py`` 三档口径，不另发明刻度**） |
| **agent 级** | PA → 执行体 | :class:`AgentGrantStore` | 按**能力 + 作用域**授权，带 TTL，可撤 |

转换层 :func:`decide` 把两套授权 + 能力风险等级**合成为唯一裁决**：

```
未注册能力                  → deny     (fail-closed)
命中撤销表(denies)          → deny     (撤销 **优先于** 授权)
老板级=只读 且 风险>R0       → deny
风险 R3                     → ask      (不可逆，逐次确认)
风险 R2                     → ask      (对外可逆，逐次确认)
风险 R1                     → 有 agent 授权 ⇒ allow；无 ⇒ ask
风险 R0                     → allow
```

**「不可合并」的产品含义**：两套授权**各自独立判定**，**任一拒绝即拒绝**；
不得因为「老板级给了高」就跳过 agent 级，也不得因为「agent 级有授权」就升老板级。

零第三方依赖。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.pes.windows import REPO_ROOT, normalize_path

#: 老板级三档（**沿用 ``core/pa/permission.py`` 的既有取值**）
BOSS_LEVELS = ("只读", "标准", "高(需确认)")
DEFAULT_BOSS_LEVEL = "标准"

DEFAULT_BOSS_PATH = REPO_ROOT / "data" / "v9" / "pes" / "boss_grant.json"
DEFAULT_AGENT_PATH = REPO_ROOT / "data" / "v9" / "pes" / "agent_grants.json"
DEFAULT_HOLD_PATH = REPO_ROOT / "data" / "v9" / "pes" / "holds.json"

#: 决策三值
ALLOW, ASK, DENY = "allow", "ask", "deny"


def _store(path, writer, seed_keys=()):
    from core.pes.state_integrity import StateFile

    return StateFile(path, writer=writer, seed_keys=seed_keys)


def _audit(kind: str, payload: Dict[str, Any], run_id: str = "") -> None:
    try:
        from core.pes.audit import audit_log

        audit_log().record(kind, run_id=run_id, payload=payload, layer="Authorization")
    except Exception:
        pass


# ============================== 老板级（人对 PA） ==============================
class BossGrantStore:
    """老板级权限档。**只能被老板在场路径写入**（PA agent 直写被硬拒 —— 沿既有主权约束）。"""

    def __init__(self, path=None):
        self.path = str(path or DEFAULT_BOSS_PATH)
        self._s = _store(self.path, "pes.boss_grant")

    def get(self) -> str:
        d = self._s.read().data or {}
        lvl = d.get("level", DEFAULT_BOSS_LEVEL)
        return lvl if lvl in BOSS_LEVELS else DEFAULT_BOSS_LEVEL

    def set(self, level: str, by: str = "boss") -> Dict[str, Any]:
        if level not in BOSS_LEVELS:
            return {"ok": False, "error": "权限档必须是 %s（收到 %r）" % ("/".join(BOSS_LEVELS), level)}
        self._s.update_runtime(
            lambda d: d.update({"level": level, "updated": time.strftime("%Y-%m-%d %H:%M:%S"), "updated_by": str(by)}),
            writer="pes.boss_grant",
            reason="set_level",
        )
        _audit("auth.boss_level_set", {"level": level, "by": by})
        return {"ok": True, "level": level}


# ============================== agent 级（PA 对执行体） ==============================
class AgentGrantStore:
    """agent 级授权：按**能力 + 作用域**授予，带 TTL，可撤。

    **撤销（denies）优先于授权** —— 对治 ``主权控制面设计_20260913`` §4.2 记录的缺口
    （旧 ``endpoint_guard.revoke()`` 只 pop 内存授权，撤完再 approve 就恢复，缺「持续拒绝」语义）。
    """

    def __init__(self, path=None):
        self.path = str(path or DEFAULT_AGENT_PATH)
        self._s = _store(self.path, "pes.agent_grants")

    def _d(self) -> Dict[str, Any]:
        d = self._s.read().data or {}
        d.setdefault("grants", {})
        d.setdefault("denies", {})
        return d

    def grant(self, capability: str, scope: str = "*", ttl_s: int = 0, by: str = "pa") -> Dict[str, Any]:
        key = _key(capability, scope)
        rec = {
            "capability": str(capability),
            "scope": str(scope or "*"),
            "by": str(by),
            "created_at": time.time(),
            "expires_at": (time.time() + int(ttl_s)) if int(ttl_s or 0) > 0 else 0,
        }

        def _mut(d):
            d.setdefault("grants", {})[key] = rec
            d.setdefault("denies", {}).pop(key, None)  # 重新授权即解除同键撤销

        self._s.update_runtime(_mut, writer="pes.agent_grants", reason="grant:%s" % key)
        _audit("auth.agent_granted", {"capability": capability, "scope": scope, "ttl_s": ttl_s})
        return rec

    def revoke(self, capability: str, scope: str = "*", reason: str = "") -> Dict[str, Any]:
        """撤销 ⇒ 写入 **denies**（持续拒绝），**不是**只删授权。"""
        key = _key(capability, scope)

        def _mut(d):
            d.setdefault("grants", {}).pop(key, None)
            d.setdefault("denies", {})[key] = {
                "capability": str(capability),
                "scope": str(scope or "*"),
                "reason": str(reason or ""),
                "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

        self._s.update_runtime(_mut, writer="pes.agent_grants", reason="revoke:%s" % key)
        _audit("auth.agent_revoked", {"capability": capability, "scope": scope, "reason": reason})
        return {"ok": True, "key": key}

    def is_denied(self, capability: str, scope: str = "*") -> Optional[Dict[str, Any]]:
        d = self._d()
        for k in (_key(capability, scope), _key(capability, "*")):
            hit = d.get("denies", {}).get(k)
            if hit:
                return hit
        return None

    def is_granted(self, capability: str, scope: str = "*") -> bool:
        if self.is_denied(capability, scope):
            return False
        d = self._d()
        now = time.time()
        for k in (_key(capability, scope), _key(capability, "*")):
            g = d.get("grants", {}).get(k)
            if not g:
                continue
            exp = float(g.get("expires_at") or 0)
            if exp and exp < now:
                continue  # 过期
            return True
        return False

    def list(self) -> Dict[str, Any]:
        d = self._d()
        return {"grants": list(d.get("grants", {}).values()), "denies": list(d.get("denies", {}).values())}


def _key(capability: str, scope: str) -> str:
    return "%s@%s" % (str(capability), str(scope or "*"))


# ============================== 撤销窗口（延迟执行队列） ==============================
class HoldQueue:
    """撤销窗口 = **延迟执行队列**（不阻塞倒计时）。

    进窗（``hold``）→ 窗口内 ``revoke`` ⇒ 摘除并记 revoked；到期 ``release`` ⇒ 放行。
    **窗口必须对用户可见** —— :meth:`visibility` 给前端「还有 N 秒可撤」。
    """

    def __init__(self, path=None):
        self.path = str(path or DEFAULT_HOLD_PATH)
        self._s = _store(self.path, "pes.holds")

    def hold(self, action_id: str, capability: str, window_s: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = time.time()
        rec = {
            "action_id": str(action_id),
            "capability": str(capability),
            "window_s": int(window_s),
            "due_ts": now + int(window_s),
            "state": "external-pending",
            "payload_ref": payload or {},
            "created_at": now,
        }
        def _mut(d):
            d.setdefault("holds", {})[rec["action_id"]] = rec

        self._s.update_runtime(_mut, writer="pes.holds", reason="hold")
        _audit("auth.hold_created", {"action_id": action_id, "capability": capability, "window_s": window_s})
        return rec

    def revoke(self, action_id: str, reason: str = "老板撤销") -> bool:
        hit = {"ok": False}

        def _mut(d):
            r = d.setdefault("holds", {}).get(str(action_id))
            if r and r.get("state") == "external-pending":
                r["state"] = "revoked"
                r["revoked_at"] = time.time()
                r["reason"] = reason
                hit["ok"] = True

        self._s.update_runtime(_mut, writer="pes.holds", reason="revoke")
        if hit["ok"]:
            _audit("auth.hold_revoked", {"action_id": action_id, "reason": reason})
        return hit["ok"]

    def due(self) -> List[Dict[str, Any]]:
        """窗口到期且未被撤销的条目（可放行）。"""
        d = self._s.read().data or {}
        now = time.time()
        return [r for r in d.get("holds", {}).values() if r.get("state") == "external-pending" and r.get("due_ts", 0) <= now]

    def release(self, action_id: str) -> bool:
        hit = {"ok": False}

        def _mut(d):
            r = d.setdefault("holds", {}).get(str(action_id))
            if r and r.get("state") == "external-pending":
                r["state"] = "external-final"
                r["released_at"] = time.time()
                hit["ok"] = True

        self._s.update_runtime(_mut, writer="pes.holds", reason="release")
        if hit["ok"]:
            _audit("auth.hold_released", {"action_id": action_id})
        return hit["ok"]

    def visibility(self, action_id: str) -> Dict[str, Any]:
        """给前端：**「已发出，还有 N 秒可以撤回」**（不展示 = 用户学不会信任）。"""
        d = self._s.read().data or {}
        r = d.get("holds", {}).get(str(action_id))
        if not r:
            return {"show": False}
        left = max(0, int(r.get("due_ts", 0) - time.time()))
        return {
            "show": True,
            "action_id": r.get("action_id"),
            "state": r.get("state"),
            "seconds_left": left,
            "message": ("已发出，还有 %d 秒可以撤回" % left) if r.get("state") == "external-pending" else "",
        }


# ============================== 转换层 ==============================
class Authorizer:
    """**两套授权 + 转换层**的唯一裁决入口。"""

    def __init__(self, registry=None, boss=None, agent=None, holds=None):
        self.registry = registry
        self.boss = boss or BossGrantStore()
        self.agent = agent or AgentGrantStore()
        self.holds = holds or HoldQueue()

    def _registry(self):
        if self.registry is None:
            from core.pes.capability_registry import CapabilityRegistry

            self.registry = CapabilityRegistry()
            try:
                self.registry.ensure_seeded()
            except Exception:
                pass
        return self.registry

    def decide(
        self,
        capability: str,
        scope: str = "*",
        boss_level: Optional[str] = None,
        run_id: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """合成唯一裁决。**fail-closed**：任何不确定 ⇒ ``ask`` 或 ``deny``，绝不放行。"""
        reg = self._registry()
        level = boss_level or self.boss.get()
        if level not in BOSS_LEVELS:
            level = DEFAULT_BOSS_LEVEL

        base = {
            "capability": str(capability),
            "scope": str(scope or "*"),
            "boss_level": level,
            "run_id": str(run_id or ""),
            "extra": extra or {},
        }

        # ① 未注册能力 ⇒ 拒绝（fail-closed）
        if not reg.is_registered(capability):
            out = dict(base, decision=DENY, reason="unregistered_capability",
                       message="能力 `%s` 未注册 ⇒ 拒绝（未注册即拒绝）。" % capability,
                       risk_level="", window_s=0, requires_approval=True)
            _audit("auth.deny", out, run_id=run_id)
            return out

        gate = reg.gate_for(capability)
        risk = gate["risk_level"]
        out = dict(base, risk_level=risk, risk_label=gate["risk_label"],
                   window_s=gate["window_s"], requires_approval=gate["approval_required"])

        # ② 撤销优先于授权
        denied = self.agent.is_denied(capability, scope)
        if denied:
            out.update(decision=DENY, reason="revoked",
                       message="该能力/作用域已被撤销（持续拒绝）：%s" % (denied.get("reason") or "无原因"))
            _audit("auth.deny", out, run_id=run_id)
            return out

        # ③ 老板级只读 ⇒ 只能 R0
        if level == "只读" and risk != "R0":
            out.update(decision=DENY, reason="boss_readonly",
                       message="老板级权限为「只读」，`%s` 属于 %s（%s），不予执行。"
                               "如需执行，请把权限档调到「标准」或「高(需确认)」。"
                               % (capability, risk, gate["risk_label"]))
            _audit("auth.deny", out, run_id=run_id)
            return out

        # ④ 风险分层
        if risk == "R0":
            out.update(decision=ALLOW, reason="readonly", message="只读能力，放行。")
        elif risk in ("R2", "R3"):
            out.update(
                decision=ASK,
                reason="risk_%s_requires_confirmation" % risk,
                message="`%s` 属于 %s（%s），按规矩**逐次确认**：需要老板点头。"
                        % (capability, risk, gate["risk_label"]),
            )
            if gate["window_s"]:
                out["reversible_window_s"] = gate["window_s"]
                out["visibility_hint"] = "执行后将进入 %d 秒撤销窗口，界面须展示「还有 N 秒可撤回」。" % gate["window_s"]
        else:  # R1
            if not gate["requires_grant"] or self.agent.is_granted(capability, scope):
                out.update(decision=ALLOW, reason="local_write_granted", message="本地写且已有 agent 级授权，放行。")
            else:
                out.update(
                    decision=ASK,
                    reason="local_write_needs_grant",
                    message="`%s` 是本地写，但**没有 agent 级授权**：需先授权（或本次明确确认）。" % capability,
                )

        _audit("auth.%s" % out["decision"], out, run_id=run_id)
        return out

    def explain(self, capability: str, scope: str = "*") -> Dict[str, Any]:
        """**可解释的拒绝**：给出「为什么」+「你可以怎么办」（对治「假拒绝」）。"""
        d = self.decide(capability, scope)
        d["why"] = d.get("message", "")
        d["how_to_fix"] = _how_to_fix(d)
        return d


def _how_to_fix(d: Dict[str, Any]) -> str:
    if d.get("decision") == ALLOW:
        return "无需操作。"
    r = d.get("reason", "")
    if r == "unregistered_capability":
        return "先注册该能力并声明风险等级（CapabilityRegistry.register），再申请授权。"
    if r == "revoked":
        return "该能力/作用域处于撤销态。如确需恢复，请老板在权限页重新授权（撤销优先于授权）。"
    if r == "boss_readonly":
        return "把老板级权限档从「只读」调到「标准」或「高(需确认)」。"
    if r == "local_write_needs_grant":
        return "在权限页给该能力/作用域授予 agent 级权限；或本次明确确认一次。"
    if str(r).startswith("risk_R"):
        return "本次明确确认一次即可（对外/不可逆动作逐次确认，不做长期免问）。"
    return "请提供更多信息，或改用只读方式完成。"


__all__ = [
    "BOSS_LEVELS",
    "DEFAULT_BOSS_LEVEL",
    "ALLOW",
    "ASK",
    "DENY",
    "BossGrantStore",
    "AgentGrantStore",
    "HoldQueue",
    "Authorizer",
]