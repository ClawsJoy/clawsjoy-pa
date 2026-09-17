"""联邦学习 - Agent 间知识共享"""

import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict


class FederatedLearning:
    """联邦学习管理器 - Agent 间共享知识"""
    
    def __init__(self):
        self._knowledge_base: Dict[str, Dict] = {}
        self._agent_knowledge: Dict[str, List[Dict]] = defaultdict(list)
        self._peer_agents: List[str] = []
        self._lock = threading.Lock()
        self._load()
        print("🤝 联邦学习模块已启动")
    
    def _get_path(self) -> Path:
        return Path("data/federated/knowledge.json")
    
    def _load(self):
        path = self._get_path()
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self._knowledge_base = data.get("knowledge", {})
                    self._agent_knowledge = defaultdict(list, data.get("agent_knowledge", {}))
            except:
                pass
    
    def _save(self):
        path = self._get_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump({
                "knowledge": self._knowledge_base,
                "agent_knowledge": dict(self._agent_knowledge),
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def share(self, from_agent: str, knowledge: Dict, confidence: float = 0.8):
        """分享知识"""
        with self._lock:
            for key, value in knowledge.items():
                if key not in self._knowledge_base:
                    self._knowledge_base[key] = {
                        "value": value,
                        "sources": {from_agent: confidence},
                        "avg_confidence": confidence,
                        "shared_at": datetime.now().isoformat()
                    }
                else:
                    self._knowledge_base[key]["sources"][from_agent] = confidence
                    avg = sum(self._knowledge_base[key]["sources"].values()) / len(self._knowledge_base[key]["sources"])
                    self._knowledge_base[key]["avg_confidence"] = avg
            
            self._agent_knowledge[from_agent].append({
                "knowledge": knowledge,
                "confidence": confidence,
                "shared_at": datetime.now().isoformat()
            })
            self._save()
            print(f"📤 [{from_agent}] 分享了 {len(knowledge)} 条知识")
    
    def query(self, agent_name: str, query: str, top_k: int = 5) -> List[Dict]:
        """查询知识"""
        results = []
        query_lower = query.lower()
        
        for key, data in self._knowledge_base.items():
            key_lower = key.lower()
            if query_lower in key_lower or key_lower in query_lower:
                results.append({
                    "key": key,
                    "value": data["value"],
                    "confidence": data["avg_confidence"],
                    "sources": list(data["sources"].keys())
                })
        
        results.sort(key=lambda x: x["confidence"], reverse=True)
        print(f"🔍 [{agent_name}] 查询 '{query[:30]}' 找到 {len(results)} 条")
        return results[:top_k]
    
    def get_agent_stats(self, agent_name: str) -> Dict:
        """获取 Agent 统计"""
        knowledge = self._agent_knowledge.get(agent_name, [])
        return {
            "agent": agent_name,
            "shared_count": len(knowledge),
            "total_knowledge": len(self._knowledge_base),
            "peers": self._peer_agents
        }


federated_learning = FederatedLearning()
