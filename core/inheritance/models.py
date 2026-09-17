#!/usr/bin/env python3
"""Models - Models 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Experience:
    """经验单元 - 可传承的最小单位"""

    type: str  # pattern, rule, strategy, wisdom
    content: Dict  # 经验内容
    id: str = ""  # 唯一标识
    confidence: float = 0.5  # 置信度 0-1
    source: str = "learning"  # learning, manual, inherited, community
    source_id: Optional[str] = None  # 来源标识
    parent_id: Optional[str] = None  # 继承自哪个经验
    version: int = 1  # 版本号

    # 统计数据
    use_count: int = 0  # 使用次数
    success_count: int = 0  # 成功次数
    fail_count: int = 0  # 失败次数

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: Optional[str] = None

    # 标签
    tags: List[str] = field(default_factory=list)
    scope: str = "private"  # private, shared, public

    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = self._generate_id()

    def _generate_id(self) -> str:
        """生成经验ID"""
        raw = (
            f"{self.type}_{json.dumps(self.content, sort_keys=True)}_{self.created_at}"
        )
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.use_count == 0:
            return 0.0
        return self.success_count / self.use_count

    def to_dict(self) -> Dict:
        """序列化"""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "source_id": self.source_id,
            "parent_id": self.parent_id,
            "version": self.version,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_used": self.last_used,
            "tags": self.tags,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Experience":
        """反序列化"""
        return cls(
            type=data.get("type", ""),
            content=data.get("content", {}),
            id=data.get("id", ""),
            confidence=data.get("confidence", 0.5),
            source=data.get("source", "learning"),
            source_id=data.get("source_id"),
            parent_id=data.get("parent_id"),
            version=data.get("version", 1),
            use_count=data.get("use_count", 0),
            success_count=data.get("success_count", 0),
            fail_count=data.get("fail_count", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            last_used=data.get("last_used"),
            tags=data.get("tags", []),
            scope=data.get("scope", "private"),
        )


@dataclass
class ExperienceChain:
    """经验传承链 - 记录经验的演化历史"""

    root_id: str  # 根经验ID
    chain: List[str] = field(default_factory=list)  # 传承链 [id1, id2, ...]

    def add_link(self, id: str):
        """添加传承链接"""
        self.chain.append(id)

    def get_depth(self) -> int:
        """传承深度"""
        return len(self.chain)

    def to_dict(self) -> Dict:
        return {"root_id": self.root_id, "chain": self.chain, "depth": self.get_depth()}


@dataclass
class KnowledgeNode:
    """知识图谱节点"""

    id: str
    name: str
    type: str  # concept, fact, relation, rule
    content: Dict
    properties: Dict = field(default_factory=dict)
    relations: List[Dict] = field(default_factory=list)  # [{target, type, weight}]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "content": self.content,
            "properties": self.properties,
            "relations": self.relations,
        }
