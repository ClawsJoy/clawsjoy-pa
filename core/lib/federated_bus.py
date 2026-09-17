# core/lib/federated_bus.py
"""联邦消息总线 - 类级别共享，所有Agent实例可见"""

import json
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class FederatedBus:
    """联邦消息总线 - 进程内Agent间通信"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._topics: Dict[str, List[Dict]] = defaultdict(list)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._storage_dir = Path("data/federated")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    # ========== 发布/订阅 ==========

    def publish(self, topic: str, data: Dict, publisher: str = "unknown"):
        """发布消息"""
        message = {
            **data,
            "published_at": datetime.now().isoformat(),
            "publisher": publisher,
        }

        # 内存存储
        self._topics[topic].append(message)
        if len(self._topics[topic]) > 500:
            self._topics[topic] = self._topics[topic][-500:]

        # 通知订阅者
        for callback in self._subscribers.get(topic, []):
            try:
                callback(message)
            except Exception as e:
                print(f"[FederatedBus] 通知失败: {e}")

    def subscribe(self, topic: str, callback: Callable):
        """订阅主题"""
        if callback not in self._subscribers[topic]:
            self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable):
        """取消订阅"""
        if callback in self._subscribers.get(topic, []):
            self._subscribers[topic].remove(callback)

    # ========== 知识存取 ==========

    def put_knowledge(self, key: str, value: Any, source: str,
                      privacy: float = 0.5, tags: List[str] = None):
        """存入知识"""
        entry = {
            "key": key,
            "value": value,
            "source": source,
            "privacy": privacy,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat(),
        }

        # 按key存储（覆盖旧值或追加）
        existing = self._get_knowledge_file(key)
        entries = []
        if existing:
            entries = existing if isinstance(existing, list) else [existing]
        entries.append(entry)
        if len(entries) > 50:
            entries = entries[-50:]

        self._save_knowledge_file(key, entries)

        # 发布事件
        self.publish("knowledge.updated", {
            "key": key, "source": source, "tags": tags
        }, publisher=source)

        return True

    def get_knowledge(self, key: str) -> Optional[Any]:
        """获取知识"""
        entries = self._get_knowledge_file(key)
        if entries and isinstance(entries, list):
            return entries[-1].get("value")
        elif entries:
            return entries.get("value")
        return None

    def query_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索知识（按key和tags模糊匹配）"""
        results = []
        query_lower = query.lower()

        for file in self._storage_dir.glob("*.json"):
            try:
                entries = json.loads(file.read_text())
                if not isinstance(entries, list):
                    entries = [entries]
                for entry in entries:
                    key = entry.get("key", "")
                    tags = " ".join(entry.get("tags", []))
                    value_str = str(entry.get("value", ""))[:200]
                    if (query_lower in key.lower() or
                        query_lower in tags.lower() or
                        query_lower in value_str.lower()):
                        results.append(entry)
            except Exception:
                pass

        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict:
        """获取统计"""
        knowledge_files = list(self._storage_dir.glob("*.json"))
        total_entries = 0
        sources = set()
        for f in knowledge_files:
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    total_entries += len(data)
                    for e in data:
                        sources.add(e.get("source", "unknown"))
                else:
                    total_entries += 1
            except Exception:
                pass

        return {
            "knowledge_files": len(knowledge_files),
            "total_entries": total_entries,
            "sources": list(sources),
            "topics": {k: len(v) for k, v in self._topics.items()},
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
        }

    def clear(self):
        """清空（谨慎使用）"""
        self._topics.clear()
        self._subscribers.clear()

    # ========== 持久化 ==========

    def _get_knowledge_file(self, key: str) -> Optional[Any]:
        """读取知识文件"""
        import hashlib
        safe_name = hashlib.md5(key.encode()).hexdigest()[:16]
        file = self._storage_dir / f"{safe_name}.json"
        if file.exists():
            try:
                return json.loads(file.read_text())
            except Exception:
                pass
        return None

    def _save_knowledge_file(self, key: str, entries: List[Dict]):
        """保存知识文件"""
        import hashlib
        safe_name = hashlib.md5(key.encode()).hexdigest()[:16]
        file = self._storage_dir / f"{safe_name}.json"
        try:
            file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"[FederatedBus] 保存失败: {e}")

    def _load(self):
        """启动时扫描已有知识"""
        pass  # 延迟加载，用到时再读


# 全局单例
federated_bus = FederatedBus()
