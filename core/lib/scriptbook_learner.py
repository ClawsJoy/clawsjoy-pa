"""话本学习器 - 自动优化对话模板"""

import yaml
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict


class ScriptbookLearner:
    """话本学习器 - 从对话中学习并优化话本"""
    
    def __init__(self, agent_name: str = "chat_agent"):
        self.agent_name = agent_name
        self.scriptbook_path = Path(f"agents/{agent_name}/scriptbook.yaml")
        self.learning_data_path = Path(f"data/learning/scriptbook/{agent_name}.json")
        self.learning_data_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 统计信息
        self._stats = defaultdict(lambda: {"hits": 0, "misses": 0, "feedback": []})
        self._load_stats()
    
    def _load_stats(self):
        """加载统计"""
        if self.learning_data_path.exists():
            try:
                import json
                with open(self.learning_data_path, 'r') as f:
                    data = json.load(f)
                    self._stats.update(data.get("stats", {}))
            except:
                pass
    
    def _save_stats(self):
        """保存统计"""
        import json
        with open(self.learning_data_path, 'w') as f:
            json.dump({
                "stats": dict(self._stats),
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def record_hit(self, intent: str, user_input: str, response: str, 
                   user_satisfied: bool = None):
        """记录话本命中"""
        self._stats[intent]["hits"] += 1
        if user_satisfied is not None:
            self._stats[intent]["feedback"].append({
                "satisfied": user_satisfied,
                "input": user_input[:100],
                "response": response[:100],
                "timestamp": datetime.now().isoformat()
            })
        self._save_stats()
    
    def record_miss(self, user_input: str, llm_response: str):
        """记录话本未命中（需要新增话本）"""
        self._stats["_misses"]["count"] = self._stats["_misses"].get("count", 0) + 1
        if "examples" not in self._stats["_misses"]:
            self._stats["_misses"]["examples"] = []
        self._stats["_misses"]["examples"].append({
            "input": user_input[:100],
            "response": llm_response[:100],
            "timestamp": datetime.now().isoformat()
        })
        # 只保留最近 50 条
        self._stats["_misses"]["examples"] = self._stats["_misses"]["examples"][-50:]
        self._save_stats()
    
    def suggest_new_intents(self) -> List[Dict]:
        """建议新增话本意图"""
        suggestions = []
        misses = self._stats.get("_misses", {})
        examples = misses.get("examples", [])
        
        if len(examples) < 5:
            return suggestions
        
        # 按模式分组
        patterns = defaultdict(list)
        for ex in examples:
            # 简单模式识别
            text = ex["input"].lower()
            if "?" in text or "？" in text:
                patterns["question"].append(ex)
            elif "!" in text or "！" in text:
                patterns["exclamation"].append(ex)
            elif len(text) < 10:
                patterns["short"].append(ex)
            else:
                patterns["long"].append(ex)
        
        # 生成建议
        for pattern_type, items in patterns.items():
            if len(items) >= 3:
                suggestions.append({
                    "type": pattern_type,
                    "examples": [i["input"] for i in items[:5]],
                    "suggested_keywords": self._extract_keywords(items),
                    "confidence": len(items) / len(examples)
                })
        
        return suggestions
    
    def _extract_keywords(self, examples: List[Dict]) -> List[str]:
        """提取关键词"""
        import jieba
        all_words = []
        for ex in examples:
            words = jieba.lcut(ex["input"])
            all_words.extend([w for w in words if len(w) > 1])
        
        # 统计词频
        from collections import Counter
        counter = Counter(all_words)
        return [word for word, count in counter.most_common(5)]
    
    def get_stats(self) -> Dict:
        """获取话本统计"""
        total_hits = sum(s["hits"] for s in self._stats.values() if isinstance(s, dict))
        total_misses = self._stats.get("_misses", {}).get("count", 0)
        
        return {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_rate": total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0,
            "intent_stats": {k: v for k, v in self._stats.items() if k != "_misses"},
            "suggestions": self.suggest_new_intents()
        }


# 全局实例
scriptbook_learner = ScriptbookLearner()
