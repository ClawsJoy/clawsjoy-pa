#!/usr/bin/env python3
"""Sandbox Scheduler - Sandbox Scheduler 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

import docker


class SandboxScheduler:
    """沙箱调度器 - 负责创建、管理、销毁容器实例"""

    VERSION = "1.0.0"

    def __init__(self):
        self.docker_client = None
        self.instances: Dict[str, Dict] = {}
        self.images_registry: Dict[str, Dict] = {}
        self._init_docker()
        self._load_registry()

    def _init_docker(self):
        """初始化Docker客户端"""
        try:
            self.docker_client = docker.from_env()
            print("✅ Docker 连接成功，沙箱模式可用")
        except Exception as e:
            print(f"⚠️ Docker 不可用，沙箱模式将受限: {e}")
            self.docker_client = None

    def _load_registry(self):
        """加载Agent镜像注册表"""
        registry_file = Path("config/sandbox_registry.yaml")
        if registry_file.exists():
            with open(registry_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.images_registry = data.get("images", {})
        else:
            # 默认注册表
            self.images_registry = {
                "code_reviewer": {
                    "name": "代码审查Agent",
                    "image": "clawsjoy/agent-code-reviewer:latest",
                    "port": 8080,
                    "resources": {"cpu": 0.5, "memory": "512m"},
                    "status": "active",
                },
                "chat_assistant": {
                    "name": "聊天助手",
                    "image": "clawsjoy/agent-chat:latest",
                    "port": 8080,
                    "resources": {"cpu": 0.5, "memory": "256m"},
                    "status": "active",
                },
            }

    def create_instance(self, agent_id: str, user_id: str) -> Dict:
        """为用户创建Agent沙箱实例"""
        if agent_id not in self.images_registry:
            return {"success": False, "error": f"Agent {agent_id} not found"}

        if not self.docker_client:
            return {"success": False, "error": "Docker not available"}

        image_config = self.images_registry[agent_id]
        instance_id = f"{user_id}_{agent_id}_{uuid.uuid4().hex[:8]}"
        container_name = f"clawsjoy-sandbox-{instance_id}"

        try:
            # 创建容器
            container = self.docker_client.containers.run(
                image=image_config["image"],
                name=container_name,
                detach=True,
                mem_limit=image_config.get("resources", {}).get("memory", "512m"),
                nano_cpus=int(
                    float(image_config.get("resources", {}).get("cpu", 0.5)) * 1e9
                ),
                environment={"USER_ID": user_id, "AGENT_ID": agent_id},
                remove=True,
            )

            # 获取容器端口
            container.reload()
            port = image_config["port"]
            host_port = container.attrs["NetworkSettings"]["Ports"][f"{port}/tcp"][0][
                "HostPort"
            ]

            instance_info = {
                "instance_id": instance_id,
                "container_id": container.id,
                "container_name": container_name,
                "user_id": user_id,
                "agent_id": agent_id,
                "endpoint": f"http://{unified_config.get("services.sandbox.host", "localhost")}:{host_port}",
                "created_at": datetime.now().isoformat(),
                "status": "running",
            }

            self.instances[instance_id] = instance_info
            return {"success": True, "instance": instance_info}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def destroy_instance(self, instance_id: str) -> Dict:
        """销毁沙箱实例"""
        if instance_id not in self.instances:
            return {"success": False, "error": "Instance not found"}

        instance = self.instances[instance_id]

        try:
            if self.docker_client:
                container = self.docker_client.containers.get(instance["container_id"])
                container.stop()
                container.remove()

            del self.instances[instance_id]
            return {"success": True, "message": "Instance destroyed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_instance(self, user_id: str, agent_id: str) -> Optional[Dict]:
        """获取用户的Agent实例"""
        for instance in self.instances.values():
            if instance["user_id"] == user_id and instance["agent_id"] == agent_id:
                if instance["status"] == "running":
                    return instance

        # 没有实例，创建新的
        result = self.create_instance(agent_id, user_id)
        if result["success"]:
            return result["instance"]
        return None

    async def proxy_request(
        self, user_id: str, agent_id: str, path: str, data: Dict
    ) -> Dict:
        """代理请求到沙箱实例"""
        instance = self.get_instance(user_id, agent_id)
        if not instance:
            return {"success": False, "error": "Cannot create instance"}

        try:
            import httpx

            async with httpx.AsyncClient(
                timeout=config_helper.get_timeout("default")
            ) as client:
                response = await client.post(f"{instance['endpoint']}{path}", json=data)
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}


sandbox_scheduler = SandboxScheduler()
