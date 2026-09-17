"""动态知识图谱引擎"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.embedding.local_embedding import local_embedding
from engine.lib.logger import engine_logger


class DynamicKnowledgeEngine:
    """动态知识图谱引擎"""

    def __init__(self):
        self.nodes = {}
        self.edges = []
        engine_logger.get().info("🔄 动态知识图谱引擎已初始化")

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self.query(input_data)
        return self.query(str(input_data))

    def add_node(self, node_id: str, node_type: str, properties: Dict = None):
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "type": node_type,
                "properties": properties or {},
            }

    def add_edge(self, source: str, target: str, relation: str, weight: float = 1.0):
        self.edges.append(
            {"source": source, "target": target, "relation": relation, "weight": weight}
        )

    def learn_from_interaction(self, query: str, response: str, success: bool):
        import re

        words = re.findall(r"[\u4e00-\u9fa5a-zA-Z]+", query)
        for w in words[:3]:
            self.add_node(w, "concept", {})
        engine_logger.get().debug(f"   📚 学习: {query[:30]}...")

    def query(self, query_text: str, top_k: int = 5) -> List[Dict]:
        """查询知识图谱"""
        results = []
        for node_id, node in self.nodes.items():
            if query_text.lower() in node_id.lower():
                results.append({"node": node, "similarity": 0.8})
        return results[:top_k]

    def get_stats(self) -> Dict:
        return {"nodes": len(self.nodes), "edges": len(self.edges), "status": "active"}

    def reload(self) -> Dict:
        self.nodes = {}
        self.edges = []
        return {"success": True, "message": "Dynamic knowledge engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "dynamic_knowledge_engine", "status": "healthy"}


dynamic_knowledge_engine = DynamicKnowledgeEngine()
