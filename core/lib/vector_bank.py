#!/usr/bin/env python3
"""
向量记忆银行 - 语义检索
存：文本→向量→存
检：查询→向量→找最相似的
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class VectorBank:
    """向量记忆银行 - 语义存储和检索"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.dir = Path(f"data/users/{user_id}")
        self.dir.mkdir(parents=True, exist_ok=True)
        
        # 存储：{key: {vector, content, timestamp}}
        self._store: Dict[str, dict] = {}
        self._dirty = False
        self._load()
    
    def _load(self):
        f = self.dir / "vectors.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                self._store = {k: {**v, "vector": np.array(v["vector"])} for k, v in data.items()}
            except Exception:
                pass
    
    def _save(self):
        if not self._dirty:
            return
        data = {k: {**v, "vector": v["vector"].tolist()} for k, v in self._store.items()}
        (self.dir / "vectors.json").write_text(json.dumps(data, ensure_ascii=False))
        self._dirty = False
    
    # ========== 向量化 ==========
    
    def _embed(self, text: str) -> np.ndarray:
        """文本→向量（用Ollama embedding模型）"""
        try:
            import requests
            resp = requests.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text[:500]},
                timeout=10
            )
            if resp.status_code == 200:
                return np.array(resp.json()["embedding"])
        except Exception:
            pass
        
        # 降级：用hash做伪向量（保证至少能跑）
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        return np.frombuffer(h[:128], dtype=np.float32)
    
    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        """余弦相似度，维度不匹配时返回0"""
        try:
            if a.shape != b.shape:
                return 0.0
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
        except Exception:
            return 0.0
    
    # ========== 存 ==========
    
    def remember(self, what: str, query_form: str, content: str):
        """
        存入记忆
        what: 存储桶名
        query_form: 用户可能用什么话问到这条记忆（用于生成检索向量）
        content: 实际存储的内容
        """
        key = f"{what}:{query_form[:60]}"
        vector = self._embed(query_form)
        
        self._store[key] = {
            "vector": vector,
            "content": content,
            "bucket": what,
            "query_form": query_form[:200],
            "timestamp": datetime.now().isoformat(),
        }
        self._dirty = True
        
        # 每10条保存一次
        if len(self._store) % 10 == 0:
            self._save()
    
    # ========== 检 ==========
    
    def recall(self, query: str, bucket: str = None, limit: int = 5) -> List[dict]:
        """
        语义检索
        query: 用户当前说的话
        bucket: 限定存储桶（None=所有桶）
        limit: 返回数量
        """
        if not self._store:
            return []
        
        query_vec = self._embed(query)
        
        scored = []
        for key, entry in self._store.items():
            if bucket and entry.get("bucket") != bucket:
                continue
            score = self._cosine(query_vec, entry["vector"])
            scored.append((score, entry))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]
    
    # ========== 注入 ==========
    
    def inject(self, user_input: str) -> str:
        """检索相关记忆，拼接成prompt片段"""
        results = self.recall(user_input, limit=5)
        if not results:
            return ""
        
        lines = []
        for r in results:
            content = r.get("content", "")[:200]
            # 解析JSON内容为自然语言
            try:
                import json
                data = json.loads(content)
                if "extracted" in data:
                    for k, v in data["extracted"].items():
                        lines.append(f"- 用户{k}是{v}")
                elif "input" in data:
                    lines.append(f"- 用户说过: {data['input']}")
                else:
                    lines.append(f"- {content}")
            except:
                lines.append(f"- {content}")
        
        return ("之前聊天的内容：\n" + "\n".join(lines)) if lines else "" 
    
    def flush(self):
        self._save()
    
    def stats(self) -> dict:
        return {
            "total": len(self._store),
            "buckets": list(set(e.get("bucket", "?") for e in self._store.values())),
        }


_banks: Dict[str, VectorBank] = {}

def get_vector_bank(user_id: str = "default") -> VectorBank:
    if user_id not in _banks:
        _banks[user_id] = VectorBank(user_id)
    return _banks[user_id]
