#!/usr/bin/env python3
"""Skill Schema - Skill Schema 模块

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

"""技能注册规范 - 定义原子技能和工作流的标准接口"""
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillType(Enum):
    ATOMIC = "atomic"  # 原子技能：单一功能
    WORKFLOW = "workflow"  # 工作流：组合多个原子技能


class SkillStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"


@dataclass
class SkillManifest:
    """技能清单 - 技能注册的标准格式"""

    name: str  # 技能名称（唯一标识）
    type: SkillType  # 技能类型
    version: str = "1.0.0"  # 版本号
    description: str = ""  # 功能描述
    category: str = "general"  # 分类: text/image/video/audio/network
    author: str = "ClawsJoy"  # 作者
    tags: List[str] = field(default_factory=list)  # 标签

    # 原子技能专用
    input_schema: Dict = field(default_factory=dict)  # 输入参数定义
    output_schema: Dict = field(default_factory=dict)  # 输出格式定义

    # 工作流专用
    steps: List[Dict] = field(default_factory=list)  # 执行步骤
    dependencies: List[str] = field(default_factory=list)  # 依赖的技能

    # 元数据
    created_at: str = ""
    updated_at: str = ""
    status: SkillStatus = SkillStatus.ACTIVE
    success_rate: float = 0.0  # 成功率统计
    execution_count: int = 0  # 执行次数

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type.value,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "author": self.author,
            "tags": self.tags,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "steps": self.steps,
            "dependencies": self.dependencies,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "success_rate": self.success_rate,
            "execution_count": self.execution_count,
        }


class SkillRegistry:
    """统一技能注册中心"""

    def __init__(self, registry_file=f"{get_data_root()}/skill_manifests.json"):
        self.registry_file = Path(registry_file)
        self.manifests: Dict[str, SkillManifest] = {}
        self._load()

    def _load(self):
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                for name, manifest_data in data.items():
                    self.manifests[name] = self._dict_to_manifest(manifest_data)

    def _save(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        data = {name: m.to_dict() for name, m in self.manifests.items()}
        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _dict_to_manifest(self, data: Dict) -> SkillManifest:
        return SkillManifest(
            name=data["name"],
            type=SkillType(data["type"]),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            author=data.get("author", "ClawsJoy"),
            tags=data.get("tags", []),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            steps=data.get("steps", []),
            dependencies=data.get("dependencies", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            status=SkillStatus(data.get("status", "active")),
            success_rate=data.get("success_rate", 0.0),
            execution_count=data.get("execution_count", 0),
        )

    def register_atomic(
        self,
        name: str,
        description: str,
        category: str,
        input_schema: Dict = None,
        output_schema: Dict = None,
        tags: List[str] = None,
    ) -> bool:
        """注册原子技能"""
        import datetime

        manifest = SkillManifest(
            name=name,
            type=SkillType.ATOMIC,
            description=description,
            category=category,
            tags=tags or [],
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            created_at=datetime.datetime.now().isoformat(),
            updated_at=datetime.datetime.now().isoformat(),
        )
        self.manifests[name] = manifest
        self._save()
        print(f"✅ 注册原子技能: {name} [{category}]")
        return True

    def register_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict],
        dependencies: List[str] = None,
        tags: List[str] = None,
    ) -> bool:
        """注册工作流技能"""
        import datetime

        manifest = SkillManifest(
            name=name,
            type=SkillType.WORKFLOW,
            description=description,
            category="workflow",
            tags=tags or [],
            steps=steps,
            dependencies=dependencies or [],
            created_at=datetime.datetime.now().isoformat(),
            updated_at=datetime.datetime.now().isoformat(),
        )
        self.manifests[name] = manifest
        self._save()
        print(f"✅ 注册工作流: {name} ({len(steps)} 步骤)")
        return True

    def get(self, name: str) -> Optional[SkillManifest]:
        return self.manifests.get(name)

    def list_by_type(self, skill_type: SkillType) -> List[str]:
        return [n for n, m in self.manifests.items() if m.type == skill_type]

    def list_by_category(self, category: str) -> List[str]:
        return [n for n, m in self.manifests.items() if m.category == category]

    def update_success_rate(self, name: str, success: bool):
        manifest = self.manifests.get(name)
        if manifest:
            manifest.execution_count += 1
            total = manifest.execution_count
            current_rate = manifest.success_rate
            # 移动平均更新成功率
            manifest.success_rate = (
                current_rate * (total - 1) + (100 if success else 0)
            ) / total
            self._save()

    def get_best_workflow(self, goal: str) -> Optional[str]:
        """根据目标推荐最佳工作流"""
        goal_lower = goal.lower()
        # 关键词匹配
        workflow_keywords = {
            "video_creation": ["视频", "制作", "漫剧"],
            "script_writing": ["脚本", "文案", "写作"],
            "data_analysis": ["分析", "统计", "处理"],
        }

        for workflow, keywords in workflow_keywords.items():
            if any(kw in goal_lower for kw in keywords):
                if workflow in self.manifests:
                    return workflow
        return None


skill_registry = SkillRegistry()
