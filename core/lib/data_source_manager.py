from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""Data Source Manager - Data Source Manager 模块

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
from core.lib.unified_config import unified_config

"""数据源管理器 - 所有数据入口统一管理"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests


@dataclass
class DataSource:
    name: str
    type: str  # api, file, db, vector, memory
    endpoint: str
    enabled: bool
    last_fetch: str = ""
    last_count: int = 0


class DataSourceManager:
    def collect_all(self) -> Dict:
        """收集所有数据源的数据"""
        results = {}
        for source in self.sources:
            if source.enabled:
                try:
                    data = self.fetch(source.name)
                    results[source.name] = data
                except Exception as e:
                    results[source.name] = {"error": str(e)}
        return results

    """统一管理所有数据源入口"""

    def __init__(self):
        self.sources = []
        self._load_sources()
        self._register_default_sources()

    def _load_sources(self):
        sources_file = Path("config/data_sources.yaml")
        if sources_file.exists():
            import yaml

            with open(sources_file, "r") as f:
                data = unified_config.get("data_source_manager", {})
                for src in data.get("sources", []):
                    self.sources.append(DataSource(**src))

    def _register_default_sources(self):
        """注册默认数据源"""
        defaults = [
            DataSource("skills", "api", "/api/skills", True),
            DataSource("health", "api", "/api/health", True),
            DataSource("agents", "api", "/api/agents/list", True),
            DataSource("memory_vector", "vector", "lib.memory_vector", True),
            DataSource("logs", "file", "logs/", True),
            DataSource(
                "user_data",
                "db",
                unified_config.get("paths.users_dir", f"{get_data_root()}/users/") + "/",
                True,
            ),
            DataSource("knowledge_base", "vector", "lib.agent_knowledge", True),
            DataSource(
                "skill_registry",
                "file",
                f"{get_data_root()}/skill_registry_v2.json",
                True,
            ),
        ]

        existing_names = [s.name for s in self.sources]
        for src in defaults:
            if src.name not in existing_names:
                self.sources.append(src)

    def fetch(self, source_name: str) -> Dict:
        """从指定数据源获取数据"""
        source = next((s for s in self.sources if s.name == source_name), None)
        if not source:
            return {"error": f"数据源不存在: {source_name}"}
        if not source.enabled:
            return {"error": f"数据源已禁用: {source_name}"}
        try:
            if source.type == "api":
                resp = requests.get(
                    f"http://{unified_config.get('services.gateway.host', 'localhost')}:{unified_config.get('services.gateway.port', 5002)}{source.endpoint}",
                    timeout=10,
                )
                data = resp.json() if resp.status_code == 200 else {"error": f"HTTP {resp.status_code}"}
            elif source.type == "file":
                path = Path(source.endpoint)
                if path.exists():
                    if path.suffix == ".json":
                        import json

                        with open(path, "r") as f:
                            data = json.load(f)
                    else:
                        data = {"path": str(path), "size": path.stat().st_size}
                else:
                    data = {"error": "文件不存在"}
            elif source.type == "vector":
                if source.endpoint == "lib.memory_vector":
                    from core.lib.memory_vector import vector_memory

                    data = {"count": vector_memory.collection.count()}
                elif source.endpoint == "lib.agent_knowledge":
                    from core.lib.agent_knowledge import agent_knowledge

                    data = agent_knowledge.get_stats()
                else:
                    data = {"error": "未知向量源"}
            else:
                data = {"error": f"不支持的类型: {source.type}"}

            source.last_fetch = datetime.now().isoformat()
            if isinstance(data, dict) and "total" in data:
                source.last_count = data["total"]
            elif isinstance(data, dict) and "count" in data:
                source.last_count = data["count"]

            return {"success": True, "data": data, "source": source.name}
        except Exception as e:
            return {"success": False, "error": str(e), "source": source.name}

    def fetch_all(self) -> Dict:
        """获取所有数据源数据"""
        results = {}
        for source in self.sources:
            if source.enabled:
                results[source.name] = self.fetch(source.name)
        return results

    def get_status(self) -> Dict:
        """获取所有数据源状态"""
        return {
            "total": len(self.sources),
            "enabled": sum(1 for s in self.sources if s.enabled),
            "sources": [{"name": s.name, "type": s.type, "enabled": s.enabled} for s in self.sources],
        }

    def enable(self, name: str) -> Dict:
        for s in self.sources:
            if s.name == name:
                s.enabled = True
                return {"success": True}
        return {"error": "数据源不存在"}

    def disable(self, name: str) -> Dict:
        for s in self.sources:
            if s.name == name:
                s.enabled = False
                return {"success": True}
        return {"error": "数据源不存在"}


data_source_manager = DataSourceManager()


def check_quality(self, source_name: str, data: Dict) -> Dict:
    """检查数据质量"""
    quality = {"score": 100, "issues": []}

    if source_name == "knowledge_base":
        from core.lib.agent_knowledge import agent_knowledge

        for name, col in agent_knowledge.collections.items():
            if col.count() == 0:
                quality["issues"].append(f"{name} 集合为空")
                quality["score"] -= 20

    elif source_name == "memory_vector":
        if data.get("count", 0) < 100:
            quality["issues"].append(f"向量记忆数量不足: {data.get('count', 0)}")
            quality["score"] -= 30

    elif source_name == "skills":
        if data.get("total", 0) < 100:
            quality["issues"].append(f"技能数量不足: {data.get('total', 0)}")
            quality["score"] -= 30

    quality["quality"] = "good" if quality["score"] >= 80 else "warning" if quality["score"] >= 60 else "poor"
    return quality


def fetch_with_quality(self, source_name: str) -> Dict:
    """获取数据并检查质量"""
    result = self.fetch(source_name)
    if result.get("success") and result.get("data"):
        quality = self.check_quality(source_name, result["data"])
        result["quality"] = quality
    return result

    def check_quality_enhanced(self, source_name: str, data: Dict) -> Dict:
        """增强版质量检查"""
        issues = []
        warnings = []

        if source_name == "skills":
            total = data.get("total", 0)
            if total < 100:
                issues.append(f"技能数量不足: {total} < 100")
            elif total < 130:
                warnings.append(f"技能数量偏低: {total}")

        elif source_name == "memory_vector":
            count = data.get("count", 0)
            if count < 50:
                issues.append(f"向量记忆不足: {count} < 50")

        elif source_name == "knowledge_base":
            from core.lib.agent_knowledge import agent_knowledge

            stats = agent_knowledge.get_stats()
            if stats.get("skills", 0) < 30:
                issues.append(f"知识库技能不足: {stats.get('skills', 0)}")

        return {
            "quality": "good" if not issues else "poor",
            "issues": issues,
            "warnings": warnings,
            "score": max(0, 100 - len(issues) * 20 - len(warnings) * 5),
        }
