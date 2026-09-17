#!/usr/bin/env python3
"""Developer Api - Developer Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)

"""开发者API - 管理开发者Agent的上架、审核、发布"""
import hashlib
import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from flask import Blueprint, jsonify, request

# 创建蓝图
developer_bp = Blueprint("developer", __name__, url_prefix="/api/developer")


class DeveloperAPI:
    """开发者API管理器"""

    VERSION = "1.0.0"

    def __init__(self):
        self.registry_path = Path("config/developer/registry.yaml")
        self.marketplace_dir = Path(f"{get_data_root()}/marketplace")
        self.pending_dir = Path(f"{get_data_root()}/marketplace/pending")
        self._init_dirs()

    def _init_dirs(self):
        """初始化目录"""
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.marketplace_dir.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> Dict:
        """加载开发者注册表"""
        if self.registry_path.exists():
            with open(self.registry_path, "r") as f:
                return yaml.safe_load(f) or {"developers": {}}
        return {"developers": {}}

    def _save_registry(self, data: Dict):
        """保存开发者注册表"""
        with open(self.registry_path, "w") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, indent=2)

    def sanitize_agent(self, agent_path: Path) -> Dict:
        """脱敏处理 - 清空用户记忆"""
        result = {"cleared": [], "kept": []}

        # 清空记忆文件
        memory_files = [
            "memory.json",
            "preferences.json",
            "habits.json",
            "todos.json",
            "conversations.json",
        ]
        for f in memory_files:
            target = agent_path / f
            if target.exists():
                with open(target, "w") as fp:
                    json.dump(
                        {
                            "sanitized": True,
                            "data": {},
                            "sanitized_at": datetime.now().isoformat(),
                        },
                        fp,
                    )
                result["cleared"].append(f)

        # 清空向量目录
        vector_dir = agent_path / "vectors"
        if vector_dir.exists():
            shutil.rmtree(vector_dir)
            vector_dir.mkdir(parents=True)
            result["cleared"].append("vectors/")

        # 清空用户数据目录
        user_data_dir = agent_path / "user_data"
        if user_data_dir.exists():
            shutil.rmtree(user_data_dir)
            user_data_dir.mkdir(parents=True)
            result["cleared"].append("user_data/")

        # 保留配置和技能
        keep_dirs = ["config", "skills", "workflows", "templates", "prompts"]
        for d in keep_dirs:
            if (agent_path / d).exists():
                result["kept"].append(f"{d}/")

        # 标记已脱敏
        with open(agent_path / ".sanitized", "w") as f:
            f.write(f"version: {self.VERSION}\n")
            f.write(f"sanitized_at: {datetime.now().isoformat()}\n")
            f.write("user_memory_cleared: true\n")

        return result

    def register_developer(self, developer_id: str, name: str, email: str) -> Dict:
        """注册开发者"""
        registry = self._load_registry()

        if developer_id in registry.get("developers", {}):
            return {"success": False, "error": "Developer already exists"}

        registry["developers"][developer_id] = {
            "id": developer_id,
            "name": name,
            "email": email,
            "registered_at": datetime.now().isoformat(),
            "status": "active",
            "agents": {},
            "stats": {"total_uploads": 0, "total_published": 0, "total_downloads": 0},
        }

        registry["statistics"]["total_developers"] = len(registry["developers"])
        self._save_registry(registry)

        return {"success": True, "developer": registry["developers"][developer_id]}

    def upload_agent(
        self, developer_id: str, agent_path: Path, version: str = "1.0.0"
    ) -> Dict:
        """上传Agent（自动脱敏）"""
        registry = self._load_registry()

        # 验证开发者
        if developer_id not in registry.get("developers", {}):
            return {"success": False, "error": "Developer not found"}

        # 读取Agent配置
        config_file = agent_path / "config" / "agent.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
                agent_name = config.get("name", agent_path.name)
                agent_type = config.get("type", "custom")
        else:
            agent_name = agent_path.name
            agent_type = "custom"

        # 脱敏处理
        sanitize_result = self.sanitize_agent(agent_path)

        # 生成包ID
        package_id = hashlib.md5(
            f"{developer_id}_{agent_name}_{datetime.now()}".encode()
        ).hexdigest()[:12]

        # 打包
        package_file = self.pending_dir / f"{package_id}.tar.gz"
        with tarfile.open(package_file, "w:gz") as tar:
            tar.add(agent_path, arcname=f"{agent_name}_{version}")

        # 创建审核记录
        review_record = {
            "package_id": package_id,
            "developer_id": developer_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "version": version,
            "upload_time": datetime.now().isoformat(),
            "status": "pending",
            "sanitized": True,
            "sanitize_result": sanitize_result,
        }

        # 保存审核记录
        with open(self.pending_dir / f"{package_id}.json", "w") as f:
            json.dump(review_record, f, indent=2)

        # 更新开发者统计
        registry["developers"][developer_id]["stats"]["total_uploads"] += 1
        registry["developers"][developer_id]["agents"][agent_name] = {
            "version": version,
            "status": "pending",
            "package_id": package_id,
            "uploaded_at": datetime.now().isoformat(),
        }

        registry["review_queue"].append(package_id)
        self._save_registry(registry)

        return {
            "success": True,
            "package_id": package_id,
            "status": "pending",
            "sanitized": sanitize_result,
        }

    def list_pending(self) -> List[Dict]:
        """列出待审核的Agent（管理员）"""
        pending = []
        for f in self.pending_dir.glob("*.json"):
            with open(f, "r") as fp:
                record = json.load(fp)
                if record.get("status") == "pending":
                    pending.append(record)
        return pending

    def approve_agent(self, package_id: str, reviewer: str = "admin") -> Dict:
        """审核通过（管理员）"""
        pending_file = self.pending_dir / f"{package_id}.json"
        if not pending_file.exists():
            return {"success": False, "error": "Package not found"}

        with open(pending_file, "r") as f:
            record = json.load(f)

        # 移动到正式市场
        record["status"] = "approved"
        record["reviewer"] = reviewer
        record["approved_time"] = datetime.now().isoformat()

        # 创建产品文件
        product_file = self.marketplace_dir / f"{record['agent_name']}.json"
        product_data = {
            "id": record["agent_name"],
            "name": record["agent_name"],
            "type": record.get("agent_type", "agent"),
            "version": record["version"],
            "description": f"Developed by {record['developer_id']}",
            "developer_id": record["developer_id"],
            "package_id": package_id,
            "approved_at": record["approved_time"],
            "price": "free",
            "downloads": 0,
        }

        with open(product_file, "w") as f:
            json.dump(product_data, f, indent=2)

        # 移动包文件
        shutil.move(
            self.pending_dir / f"{package_id}.tar.gz",
            self.marketplace_dir / f"{package_id}.tar.gz",
        )
        shutil.move(pending_file, self.marketplace_dir / f"{package_id}.json")

        # 更新注册表
        registry = self._load_registry()
        dev_id = record["developer_id"]
        if dev_id in registry.get("developers", {}):
            registry["developers"][dev_id]["stats"]["total_published"] += 1
            if record["agent_name"] in registry["developers"][dev_id]["agents"]:
                registry["developers"][dev_id]["agents"][record["agent_name"]][
                    "status"
                ] = "published"

        if package_id in registry.get("review_queue", []):
            registry["review_queue"].remove(package_id)

        registry["statistics"]["total_published_agents"] += 1
        self._save_registry(registry)

        return {"success": True, "message": f"Agent {record['agent_name']} approved"}

    def reject_agent(self, package_id: str, reason: str = "") -> Dict:
        """审核拒绝（管理员）"""
        pending_file = self.pending_dir / f"{package_id}.json"
        if not pending_file.exists():
            return {"success": False, "error": "Package not found"}

        with open(pending_file, "r") as f:
            record = json.load(f)

        record["status"] = "rejected"
        record["reject_reason"] = reason
        record["rejected_time"] = datetime.now().isoformat()

        # 移动回退
        shutil.move(
            self.pending_dir / f"{package_id}.tar.gz",
            self.marketplace_dir / f"rejected_{package_id}.tar.gz",
        )
        shutil.move(pending_file, self.marketplace_dir / f"rejected_{package_id}.json")

        # 更新注册表
        registry = self._load_registry()
        dev_id = record["developer_id"]
        if dev_id in registry.get("developers", {}):
            if record["agent_name"] in registry["developers"][dev_id]["agents"]:
                registry["developers"][dev_id]["agents"][record["agent_name"]][
                    "status"
                ] = "rejected"

        if package_id in registry.get("review_queue", []):
            registry["review_queue"].remove(package_id)

        self._save_registry(registry)

        return {"success": True, "message": f"Agent {record['agent_name']} rejected"}


# 全局实例
developer_api = DeveloperAPI()


# ========== Flask 路由 ==========
def register_developer_routes(app):
    """注册开发者路由到Flask应用"""

    @app.route("/api/developer/register", methods=["POST"])
    def developer_register():
        data = request.get_json() or {}
        result = developer_api.register_developer(
            developer_id=data.get("developer_id"),
            name=data.get("name"),
            email=data.get("email"),
        )
        return jsonify(result)

    @app.route("/api/developer/upload", methods=["POST"])
    def developer_upload():
        data = request.get_json() or {}
        agent_path = Path(data.get("agent_path"))
        if not agent_path.exists():
            return jsonify({"success": False, "error": "Agent path not found"}), 400

        result = developer_api.upload_agent(
            developer_id=data.get("developer_id"),
            agent_path=agent_path,
            version=data.get("version", "1.0.0"),
        )
        return jsonify(result)

    @app.route("/api/admin/pending", methods=["GET"])
    def admin_pending():
        """管理员 - 待审核列表"""
        pending = developer_api.list_pending()
        return jsonify({"success": True, "pending": pending, "count": len(pending)})

    @app.route("/api/admin/approve", methods=["POST"])
    def admin_approve():
        """管理员 - 审核通过"""
        data = request.get_json() or {}
        result = developer_api.approve_agent(
            package_id=data.get("package_id"), reviewer=data.get("reviewer", "admin")
        )
        return jsonify(result)

    @app.route("/api/admin/reject", methods=["POST"])
    def admin_reject():
        """管理员 - 审核拒绝"""
        data = request.get_json() or {}
        result = developer_api.reject_agent(
            package_id=data.get("package_id"), reason=data.get("reason", "")
        )
        return jsonify(result)

    print("✅ 开发者路由已注册")
