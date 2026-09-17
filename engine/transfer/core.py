"""迁移学习引擎 - 跨领域知识迁移"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.embedding.local_embedding import local_embedding
from engine.lib.logger import engine_logger


class TransferEngine:
    """迁移学习引擎"""

    def __init__(self):
        self.knowledge_base = defaultdict(dict)
        self.similarity_threshold = 0.6
        self.knowledge_file = Path("data/transfer_knowledge.json")
        self._load()
        engine_logger.get().info("🔄 迁移学习引擎已初始化")

    def _load(self):
        if self.knowledge_file.exists():
            with open(self.knowledge_file, "r") as f:
                data = json.load(f)
                self.knowledge_base.update(data.get("knowledge", {}))

    def _save(self):
        with open(self.knowledge_file, "w") as f:
            json.dump(
                {
                    "knowledge": dict(self.knowledge_base),
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def transfer(
        self, source_domain: str, target_domain: str, source_knowledge: Dict
    ) -> Dict:
        """知识迁移"""
        similarity = self._compute_similarity(source_domain, target_domain)

        if similarity < self.similarity_threshold:
            return {
                "similarity": similarity,
                "transferred": False,
                "transferred_count": 0,
            }

        transferred = {}
        for key, value in source_knowledge.items():
            adapted_key = self._adapt_key(key, source_domain, target_domain)
            transferred[adapted_key] = value
            self.knowledge_base[target_domain][adapted_key] = value

        self._save()
        engine_logger.get().info(
            f"   📤 迁移: {source_domain} -> {target_domain}, {len(transferred)}项"
        )

        return {
            "similarity": similarity,
            "transferred_count": len(transferred),
            "transferred": transferred,
        }

    def _compute_similarity(self, domain1: str, domain2: str) -> float:
        """计算领域相似度"""
        return local_embedding.similarity(domain1, domain2)

    def _adapt_key(self, key: str, source: str, target: str) -> str:
        """适配键名"""
        mappings = {
            "python": ["code", "programming"],
            "javascript": ["code", "web"],
            "weather": ["climate", "temperature"],
        }
        for k, v_list in mappings.items():
            if k in source:
                for v in v_list:
                    if v in target:
                        return key
        return key

    def get_knowledge(self, domain: str) -> Dict:
        """获取领域知识"""
        return dict(self.knowledge_base.get(domain, {}))

    def add_knowledge(self, domain: str, key: str, value: Any):
        """添加知识"""
        self.knowledge_base[domain][key] = value
        self._save()

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, dict):
            action = input_data.get("action", "transfer")
            if action == "transfer":
                return self.transfer(
                    input_data.get("source_domain", ""),
                    input_data.get("target_domain", ""),
                    input_data.get("source_knowledge", {}),
                )
            elif action == "add":
                return self.add_knowledge(
                    input_data.get("domain", ""),
                    input_data.get("key", ""),
                    input_data.get("value", ""),
                )
        return self.get_stats()

    def get_stats(self) -> Dict:
        return {
            "domains": len(self.knowledge_base),
            "total_knowledge": sum(len(v) for v in self.knowledge_base.values()),
        }


transfer_engine = TransferEngine()
