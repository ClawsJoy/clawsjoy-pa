#!/usr/bin/env python3
"""RosterEngine v8.0 — AI员工花名册管理"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List


class RosterEngine:
    """AI 员工花名册 — 聘用/解雇/权限/预算管理"""

    def __init__(self, data_dir: str = "data/v8"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.roster: Dict[str, dict] = {}  # {server_id: {members}}
        self._cache: Dict[str, dict] = {}  # 内存缓存，加速读取
        self._load_all()

    # ========== 持久化 ==========

    def _file(self, server_id: str) -> Path:
        return self.data_dir / f"roster_{server_id}.json"

    def _load_all(self):
        for f in self.data_dir.glob("roster_*.json"):
            server_id = f.stem.replace("roster_", "")
            try:
                self.roster[server_id] = json.loads(f.read_text())
            except:
                self.roster[server_id] = {"members": {}}
            self._cache[server_id] = self.roster[server_id]

    def _save(self, server_id: str):
        if server_id not in self.roster:
            self.roster[server_id] = {"members": {}}
        self._file(server_id).write_text(
            json.dumps(self.roster[server_id], indent=2, ensure_ascii=False)
        )
        self._cache[server_id] = self.roster[server_id]

    # ========== 生命周期 ==========

    def hire(self, server_id: str, name: str, position_yaml: dict) -> dict:
        """聘用 AI 员工"""
        if server_id not in self.roster:
            self.roster[server_id] = {"members": {}}

        if name in self.roster[server_id]["members"]:
            return {"success": False, "error": f"员工 {name} 已存在"}

        member = {
            "name": name,
            "position": position_yaml.get("position", "未知"),
            "model": position_yaml.get("model", ""),
            "budget": position_yaml.get("budget", 0),
            "spent": 0,
            "status": "active",
            "hired_at": datetime.now().isoformat(),
            "permissions": position_yaml.get("permissions", {}),
            "constraints": position_yaml.get("constraints", []),
            "task_count": 0,
            "success_count": 0,
            "api_key": position_yaml.get("api_key", ""),
            "unit_price": position_yaml.get("unit_price", 0),
        }
        self.roster[server_id]["members"][name] = member
        self._save(server_id)
        # V9 注入：聘用事件
        try:
            from core.lib.code_entity_extractor import extractor
            extractor.insert_agent_action(
                session_id=server_id,
                task_name=f"roster:hire:{name}",
                tool_name="roster_engine",
                result="hire",
                file_type="roster",
                agent_reaction="",
                detail=f"聘用 {name} 为 {member['position']}"
            )
        except:
            pass
        return {"success": True, "member": member}

    def fire(self, server_id: str, name: str) -> dict:
        """解雇 AI 员工"""
        if not self._exists(server_id, name):
            return {"success": False, "error": f"员工 {name} 不存在"}
        member = self.roster[server_id]["members"].pop(name)
        member["status"] = "fired"
        member["fired_at"] = datetime.now().isoformat()
        self._save(server_id)
        # V9 注入：解雇事件
        try:
            from core.lib.code_entity_extractor import extractor
            extractor.insert_agent_action(
                session_id=server_id,
                task_name=f"roster:fire:{name}",
                tool_name="roster_engine",
                result="fire",
                file_type="roster",
                agent_reaction="",
                detail=f"解雇 {name}"
            )
        except:
            pass
        return {"success": True, "member": member}

    def pause(self, server_id: str, name: str) -> dict:
        """暂停"""
        if not self._exists(server_id, name):
            return {"success": False, "error": f"员工 {name} 不存在"}
        self.roster[server_id]["members"][name]["status"] = "paused"
        self._save(server_id)
        return {"success": True}

    def resume(self, server_id: str, name: str) -> dict:
        """恢复"""
        if not self._exists(server_id, name):
            return {"success": False, "error": f"员工 {name} 不存在"}
        self.roster[server_id]["members"][name]["status"] = "active"
        self._save(server_id)
        return {"success": True}

    # ========== 查询 ==========

    def get(self, server_id: str, name: str) -> Optional[dict]:
        # 优先从缓存读取
        server_data = self._cache.get(server_id)
        if server_data is None:
            server_data = self.roster.get(server_id, {"members": {}})
            self._cache[server_id] = server_data
        return server_data["members"].get(name)

    def list(self, server_id: str) -> List[dict]:
        # 优先从缓存读取
        server_data = self._cache.get(server_id)
        if server_data is None:
            server_data = self.roster.get(server_id, {"members": {}})
            self._cache[server_id] = server_data
        return list(server_data["members"].values())

    def list_active(self, server_id: str) -> List[dict]:
        return [m for m in self.list(server_id) if m["status"] == "active"]

    # ========== 权限 & 预算 ==========

    def check_permission(self, server_id: str, name: str, action: str, target: str = "") -> dict:
        """检查权限"""
        member = self.get(server_id, name)
        if not member:
            return {"allowed": False, "reason": "员工不存在"}
        if member["status"] != "active":
            return {"allowed": False, "reason": f"员工状态: {member['status']}"}

        permissions = member.get("permissions", {})
        if action not in permissions:
            return {"allowed": False, "reason": f"未授权操作: {action}"}

        targets = permissions[action]
        if targets == "*":
            return {"allowed": True}

        if isinstance(targets, list):
            if target in targets:
                return {"allowed": True}
            return {"allowed": False, "reason": f"目标 {target} 不在授权列表"}

        return {"allowed": False, "reason": "权限配置异常"}

    def check_budget(self, server_id: str, name: str, estimated_cost: float = 0) -> dict:
        """检查预算"""
        member = self.get(server_id, name)
        if not member:
            return {"allowed": False, "reason": "员工不存在"}
        budget = member.get("budget", 0)
        if budget <= 0:
            return {"allowed": True, "reason": "无预算限制"}
        spent = member.get("spent", 0)
        if spent + estimated_cost > budget:
            return {
                "allowed": False,
                "reason": f"预算不足: 已花费 ${spent:.2f} / ${budget:.2f}",
                "spent": spent,
                "budget": budget,
                "remaining": budget - spent,
            }
        return {
            "allowed": True,
            "spent": spent,
            "budget": budget,
            "remaining": budget - spent - estimated_cost,
        }

    def record_cost(self, server_id: str, name: str, cost: float) -> dict:
        """记录花费"""
        member = self.get(server_id, name)
        if not member:
            return {"success": False, "error": "员工不存在"}
        member["spent"] = member.get("spent", 0) + cost
        member["task_count"] = member.get("task_count", 0) + 1
        member["success_count"] = member.get("success_count", 0) + 1
        self._save(server_id)
        # V9 注入：同步写入 agent_actions
        try:
            from core.lib.code_entity_extractor import extractor
            extractor.insert_agent_action(
                session_id=server_id,
                task_name=f"roster:{name}",
                tool_name=name,
                result="completed",
                file_type="roster",
                agent_reaction="",
                detail=f"花费: {cost:.4f}"
            )
        except:
            pass
        return {
            "success": True,
            "spent": member["spent"],
            "budget": member.get("budget", 0),
            "remaining": max(0, member.get("budget", 0) - member["spent"]),
        }

    def update_permissions(self, server_id: str, name: str, permissions: dict) -> dict:
        """修改权限"""
        if not self._exists(server_id, name):
            return {"success": False, "error": f"员工 {name} 不存在"}
        self.roster[server_id]["members"][name]["permissions"].update(permissions)
        self._save(server_id)
        return {"success": True}

    def update_budget(self, server_id: str, name: str, budget: float) -> dict:
        """修改预算"""
        if not self._exists(server_id, name):
            return {"success": False, "error": f"员工 {name} 不存在"}
        self.roster[server_id]["members"][name]["budget"] = budget
        self._save(server_id)
        return {"success": True}

    # ========== 辅助 ==========

    def _exists(self, server_id: str, name: str) -> bool:
        return (
            server_id in self.roster
            and name in self.roster[server_id].get("members", {})
        )

    def get_stats(self) -> dict:
        """全局统计"""
        total = 0
        active = 0
        for server in self.roster.values():
            for m in server.get("members", {}).values():
                total += 1
                if m["status"] == "active":
                    active += 1
        return {
            "total_servers": len(self.roster),
            "total_members": total,
            "active_members": active,
        }


# ========== 全局单例 ==========
roster_engine = RosterEngine()

# P0: 收编注册到 V9Context 容器(零行为变化 — 容器持有同一实例, 业务代码仍直接 import roster_engine)
try:
    from core.os.context import get_v9_context as _get_v9_ctx_roster
    _get_v9_ctx_roster().provide("roster_engine", roster_engine)
except Exception as _roster_ctx_err:
    print(f"[ROSTER] P0 容器收编失败(不影响运行): {_roster_ctx_err}")
