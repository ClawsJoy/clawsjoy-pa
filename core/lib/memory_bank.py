#!/usr/bin/env python3
"""记忆银行 v3.0 - 双引用模式：直接读写 permanent_memory 文件"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class MemoryBank:
    """与 BaseAgent.remember_forever 共享同一个 permanent_memory 文件"""

    def __init__(self, user_id: str = "default", agent_name: str = "memory_agent_v4"):
        self.user_id = user_id
        self.agent_name = agent_name
        
        # 与 BaseAgent._get_memory_file 相同的路径计算
        memory_key = hashlib.md5(
            f"{user_id}_{agent_name}".encode()
        ).hexdigest()[:16]
        self.file = Path("data/permanent_memory") / f"{memory_key}.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)

        # 同义词映射
        self.synonyms = {
            "名字": ["名字", "姓名", "名称", "称呼", "name"],
            "密码": ["密码", "口令", "password", "pwd"],
            "地址": ["地址", "住址", "位置", "address"],
            "年龄": ["年龄", "年纪", "岁数", "age"],
            "职业": ["职业", "工作", "职位", "job"],
            "语言": ["语言", "编程语言", "language"],
            "城市": ["城市", "城市名", "所在城市", "city"],
            "爱好": ["爱好", "喜好", "兴趣", "喜欢", "hobby"],
            "食物": ["食物", "吃的", "爱吃", "饮食", "food"],
        }
        self._norm_key: Dict[str, str] = {}
        for canonical, aliases in self.synonyms.items():
            for alias in aliases:
                self._norm_key[alias.lower()] = canonical

    def _read(self) -> Dict:
        """读取完整的 permanent_memory dict"""
        if self.file.exists():
            try:
                return json.loads(self.file.read_text())
            except:
                pass
        return {}

    def _write(self, data: Dict):
        """写入完整的 permanent_memory dict"""
        self.file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def remember(self, what: str, content: str):
        """保留旧接口"""
        self.upsert(what, content)

    def upsert(self, key: str, value: str):
        """同key覆盖，直接操作 permanent_memory 文件"""
        data = self._read()
        norm_key = self._normalize_key(key)
        
        data[norm_key] = {
            "value": value,
            "importance": 5,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name,
        }
        self._write(data)

    def recall(self, query: str, limit: int = 10) -> str:
        """保留旧接口"""
        results = self.semantic_search(query, limit)
        return "\n".join([r["content"] for r in results])

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """在 permanent_memory dict 中做同义词搜索"""
        data = self._read()
        expanded_terms = self._expand_query(query)
        results = []

        for key, info in data.items():
            value = info.get("value", "") if isinstance(info, dict) else info
            content = f"{key}: {value}"

            if any(term.lower() in content.lower() for term in expanded_terms):
                results.append({
                    "key": key,
                    "value": str(value),
                    "content": content,
                    "time": info.get("timestamp", "") if isinstance(info, dict) else "",
                    "score": self._match_score(query, content),
                })
                if len(results) >= limit:
                    break

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]

    def _normalize_key(self, key: str) -> str:
        return self._norm_key.get(key.lower(), key)

    def _expand_query(self, query: str) -> List[str]:
        for canonical, aliases in self.synonyms.items():
            if any(alias in query.lower() for alias in aliases):
                return aliases
        return [query]

    def _match_score(self, query: str, content: str) -> float:
        key = content.split(":")[0].strip()
        if query.lower() == key.lower():
            return 1.0
        if query.lower() in content.lower():
            return 0.8
        if any(char in content for char in query):
            return 0.5
        return 0.3

    def inject(self, user_input: str) -> str:
        results = self.semantic_search(user_input, limit=3)
        if results:
            lines = [r["content"] for r in results]
            return f"【相关记忆】\n" + "\n".join(lines)
        return ""


# ===== 单例管理 =====
_banks: Dict[str, MemoryBank] = {}

def get_bank(user_id: str = "default", agent_name: str = "memory_agent_v4") -> MemoryBank:
    cache_key = f"{user_id}:{agent_name}"
    if cache_key not in _banks:
        _banks[cache_key] = MemoryBank(user_id, agent_name)
    return _banks[cache_key]
