#!/usr/bin/env python3
"""Service Registry - Service Registry 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from core.lib.config_helper import get_data_root


class ServiceRegistry:
    """服务注册表"""

    def __init__(self, registry_file: str = None):
        if registry_file is None:
            registry_file = f"{get_data_root()}/service_registry.json"
        self.registry_file = Path(registry_file)
        self.services = self._load()

    def _load(self) -> Dict:
        """加载服务注册表"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, "r") as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
            return {}
        except json.JSONDecodeError as e:
            print(f"⚠️ 服务注册表文件格式错误: {self.registry_file} - {e}")
            return {}
        except Exception as e:
            print(f"⚠️ 加载服务注册表失败: {e}")
            return {}

    def _save(self):
        """保存服务注册表"""
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_file, "w") as f:
                json.dump(self.services, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存服务注册表失败: {e}")

    def register(
        self,
        name: str,
        port: int,
        host: str = "localhost",
        health_path: str = "/api/health",
    ):
        """注册服务"""
        self.services[name] = {
            "name": name,
            "host": host,
            "port": port,
            "health_path": health_path,
            "url": f"http://{host}:{port}",
            "registered_at": datetime.now().isoformat(),
            "status": "active",
        }
        self._save()
        print(f"✅ 服务已注册: {name} -> {self.services[name]['url']}")
        return True

    def unregister(self, name: str):
        """注销服务"""
        if name in self.services:
            del self.services[name]
            self._save()
            print(f"❌ 服务已注销: {name}")

    def get(self, name: str) -> Optional[Dict]:
        """获取服务信息"""
        return self.services.get(name)

    def get_url(self, name: str) -> Optional[str]:
        """获取服务 URL"""
        service = self.get(name)
        return service["url"] if service else None

    def get_port(self, name: str) -> Optional[int]:
        """获取服务端口"""
        service = self.get(name)
        return service.get("port") if service else None

    def list_all(self) -> List[str]:
        """列出所有服务"""
        return list(self.services.keys())

    def health_check(self, name: str) -> bool:
        """健康检查"""
        service = self.get(name)
        if not service:
            return False
        try:
            resp = requests.get(f"{service['url']}{service['health_path']}", timeout=3)
            return resp.status_code == 200
        except requests.RequestException:
            return False
        except Exception:
            return False

    def get_active_services(self) -> List[Dict]:
        """获取所有活跃服务"""
        return [s for s in self.services.values() if s.get("status") == "active"]


# 全局实例
service_registry = ServiceRegistry()
