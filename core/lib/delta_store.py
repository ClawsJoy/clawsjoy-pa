#!/usr/bin/env python3
"""
增量存储引擎 - 追加不覆盖，时间加权检索
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class DeltaStore:
    """增量存储 - 只追加，不覆盖"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.root = Path(f"data/users/{user_id}")
        self.root.mkdir(parents=True, exist_ok=True)
        
        # 当前活跃的文件句柄
        self._writers: Dict[str, object] = {}
        
        # 内存向量索引（最近1000条热数据）
        self._hot_vectors: List[dict] = []
    
    # ========== 追加 ==========
    
    def append(self, bucket: str, entry: dict):
        """
        追加一条记录
        bucket: profile/memory/history/creative/任意LLM建议的新桶
        entry: 2.5层JSON标准格式的条目
        """
        # 确保必填字段
        entry.setdefault("timestamp", datetime.now().isoformat())
        entry.setdefault("version", "2.5")
        
        # 追加到JSONL文件
        f = self._get_writer(bucket)
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        f.flush()
        
        # 更新热向量索引
        if "vector" in entry:
            self._hot_vectors.append(entry)
            if len(self._hot_vectors) > 1000:
                self._hot_vectors = self._hot_vectors[-500:]
    
    def _get_writer(self, bucket: str):
        if bucket not in self._writers:
            f = open(self.root / f"{bucket}.jsonl", 'a')
            self._writers[bucket] = f
        return self._writers[bucket]
    
    # ========== 检索（时间加权） ==========
    
    def query(self, query_vec: np.ndarray, bucket: str = None, 
              limit: int = 5, time_decay: float = 0.95) -> List[dict]:
        """
        语义检索 + 时间加权
        time_decay: 每过1小时权重乘以0.95
        """
        scored = []
        now = datetime.now()
        
        # 1. 从热向量索引检索
        for entry in self._hot_vectors:
            if bucket and entry.get("bucket") != bucket:
                continue
            if "vector" not in entry:
                continue
            
            # 语义相似度
            sim = float(np.dot(query_vec, entry["vector"]) / 
                       (np.linalg.norm(query_vec) * np.linalg.norm(entry["vector"]) + 1e-8))
            
            # 时间权重
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
                hours = max(0, (now - ts).total_seconds() / 3600)
                time_weight = time_decay ** hours
            except Exception:
                time_weight = 0.5
            
            final_score = sim * 0.7 + time_weight * 0.3
            scored.append((final_score, entry))
        
        # 2. 从冷存储检索（最近修改的文件）
        if len(scored) < limit:
            cold = self._scan_cold(query_vec, bucket, limit)
            scored.extend(cold)
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]
    
    def _scan_cold(self, query_vec: np.ndarray, bucket: str, limit: int) -> List[tuple]:
        """扫描JSONL文件中的冷数据"""
        results = []
        pattern = f"{bucket}.jsonl" if bucket else "*.jsonl"
        
        for f in sorted(self.root.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            for line in self._read_tail(f, 100):
                try:
                    entry = json.loads(line)
                    if "vector" not in entry:
                        continue
                    sim = float(np.dot(query_vec, entry["vector"]) /
                               (np.linalg.norm(query_vec) * np.linalg.norm(entry["vector"]) + 1e-8))
                    results.append((sim, entry))
                except Exception:
                    pass
        
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:limit]
    
    # ========== 增量schema扩展 ==========
    
    def extend_schema(self, bucket: str, fields: List[str]):
        """LLM建议新字段，系统扩展schema（不迁移旧数据）"""
        schema_file = self.root / "_schema.json"
        schema = {}
        if schema_file.exists():
            schema = json.loads(schema_file.read_text())
        
        if bucket not in schema:
            schema[bucket] = {"fields": [], "created": datetime.now().isoformat()}
        
        for f in fields:
            if f not in schema[bucket]["fields"]:
                schema[bucket]["fields"].append(f)
        
        schema[bucket]["updated"] = datetime.now().isoformat()
        schema_file.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
        
        return {"bucket": bucket, "new_fields": fields, "total_fields": len(schema[bucket]["fields"])}
    
    def get_schema(self) -> dict:
        schema_file = self.root / "_schema.json"
        if schema_file.exists():
            return json.loads(schema_file.read_text())
        return {}
    
    # ========== 辅助 ==========
    
    def _read_tail(self, filepath: Path, n: int) -> list:
        try:
            lines = filepath.read_text().strip().split('\n')
            return lines[-n:]
        except Exception:
            return []
    
    def flush(self):
        for f in self._writers.values():
            f.flush()
    
    def stats(self) -> dict:
        buckets = {}
        for f in self.root.glob("*.jsonl"):
            lines = len(f.read_text().strip().split('\n')) if f.read_text().strip() else 0
            buckets[f.stem] = lines
        
        return {
            "buckets": buckets,
            "total_entries": sum(buckets.values()),
            "hot_vectors": len(self._hot_vectors),
            "schema": self.get_schema(),
        }


_stores: Dict[str, DeltaStore] = {}

def get_store(user_id: str = "default") -> DeltaStore:
    if user_id not in _stores:
        _stores[user_id] = DeltaStore(user_id)
    return _stores[user_id]
