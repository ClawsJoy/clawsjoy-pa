#!/usr/bin/env python3
"""Service Registry V2 - Service Registry V2 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

from core.lib.config_helper import get_data_root


class ServiceRegistryV2:
    """增强版服务注册中心"""

    def __init__(
        self,
        registry_file=f"{get_data_root()}/service_registry.json",
        heartbeat_interval=30,
    ):
        self.registry_file = Path(registry_file)
        self.heartbeat_interval = heartbeat_interval
        self.services = self._load()
        self._start_heartbeat_checker()

    def _load(self):
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                return json.load(f)
        return {}

    def _save(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, "w") as f:
            json.dump(self.services, f, indent=2)

    def _start_heartbeat_checker(self):
        """启动心跳检查线程"""

        def checker():
            while True:
                time.sleep(self.heartbeat_interval)
                self._check_heartbeats()

        thread = threading.Thread(target=checker, daemon=True)
        thread.start()

    def _check_heartbeats(self):
        """检查所有服务的心跳"""
        now = datetime.now().isoformat()
        to_remove = []

        for name, service in self.services.items():
            if service.get("status") != "active":
                continue

            last_heartbeat = service.get("last_heartbeat")
            if last_heartbeat:
                last_time = datetime.fromisoformat(last_heartbeat)
                if datetime.now() - last_time > timedelta(
                    seconds=self.heartbeat_interval * 2
                ):
                    service["status"] = "inactive"
                    service["last_error"] = f"心跳超时: {last_heartbeat}"
                    print(f"⚠️ 服务 {name} 心跳超时，标记为 inactive")
                    self._save()

        return to_remove

    def register(
        self,
        name: str,
        port: int,
        host: str = unified_config.get("services.gateway.host", "localhost"),
        version: str = "1.0.0",
        health_path: str = "/health",
        metadata: Dict = None,
    ):
        """注册服务"""
        self.services[name] = {
            "name": name,
            "host": host,
            "port": port,
            "version": version,
            "health_path": health_path,
            "url": f"http://{host}:{port}",
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "status": "active",
            "metadata": metadata or {},
            "health_check_count": 0,
            "fail_count": 0,
        }
        self._save()
        print(f"✅ 服务已注册: {name} v{version} -> {self.services[name]['url']}")
        return True

    def heartbeat(self, name: str):
        """发送心跳"""
        if name in self.services:
            self.services[name]["last_heartbeat"] = datetime.now().isoformat()
            self.services[name]["status"] = "active"
            self._save()
            return True
        return False

    def unregister(self, name: str):
        """注销服务"""
        if name in self.services:
            del self.services[name]
            self._save()
            print(f"❌ 服务已注销: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[Dict]:
        """获取服务信息"""
        return self.services.get(name)

    def get_url(self, name: str) -> Optional[str]:
        service = self.get(name)
        return service["url"] if service else None

    def get_active(self) -> List[Dict]:
        """获取活跃服务"""
        return [s for s in self.services.values() if s.get("status") == "active"]

    def list_all(self) -> List[str]:
        return list(self.services.keys())

    def list_active(self) -> List[str]:
        return [s["name"] for s in self.get_active()]

    def health_check(self, name: str) -> bool:
        """健康检查"""
        service = self.get(name)
        if not service:
            return False
        try:
            url = f"{service['url']}{service['health_path']}"
            resp = requests.get(url, timeout=5)
            is_healthy = resp.status_code == 200
            service["health_check_count"] = service.get("health_check_count", 0) + 1
            if is_healthy:
                service["status"] = "active"
                service["last_heartbeat"] = datetime.now().isoformat()
            else:
                service["fail_count"] = service.get("fail_count", 0) + 1
                if service["fail_count"] > 3:
                    service["status"] = "unhealthy"
            self._save()
            return is_healthy
        except Exception as e:
            service["fail_count"] = service.get("fail_count", 0) + 1
            if service["fail_count"] > 3:
                service["status"] = "unhealthy"
            self._save()
            return False

    def get_stats(self) -> Dict:
        """获取统计信息"""
        active = len([s for s in self.services.values() if s.get("status") == "active"])
        inactive = len(
            [s for s in self.services.values() if s.get("status") != "active"]
        )
        return {
            "total": len(self.services),
            "active": active,
            "inactive": inactive,
            "services": self.services,
        }

    def list_services(self):
        """列出所有服务"""
        return list(self.services.keys())


service_registry = ServiceRegistryV2()
