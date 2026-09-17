#!/usr/bin/env python3
"""Memory Vector - Memory Vector 模块

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

"""向量记忆模块 - 修复版"""
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import chromadb


class VectorMemory:
    def __init__(self, persist_dir: str = f"{get_data_root()}/vector_kb"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        # #30 修复: 默认库复用 VectorKnowledgeCenter 的 client(同 settings),
        # 避免同路径不同 settings 触发 "An instance of Chroma already exists"
        from core.lib.vector_knowledge_center import vector_knowledge_center as _vkc

        _default_kb = str(Path(f"{get_data_root()}/vector_kb").resolve())
        if str(self.persist_dir.resolve()) == _default_kb:
            self.client = _vkc.get_client()
            # 共享 VKC 的 client: 生命周期归 VKC, 本实例不得关闭它
            self._owns_client = False
        else:
            from chromadb.config import Settings

            # 自定义目录: 与 VKC 相同 settings(allow_reset=True)保持兼容
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir), settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            self._owns_client = True
        self.collection_name = "conversation"
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def close(self) -> None:
        """释放本实例持有的 Chroma 资源。

        Windows 上 hnswlib 会一直持有 <persist_dir>/<uuid>/data_level0.bin 的文件句柄，
        不显式释放就无法删除持久化目录 —— 临时目录清理会抛
        PermissionError [WinError 32]。Linux 允许删除已打开的文件，所以不会暴露该问题。

        仅当 client 由本实例创建时才真正 stop；默认库复用 VectorKnowledgeCenter
        的共享 client，关闭它会破坏整个进程的向量知识中心。
        """
        client = getattr(self, "client", None)
        owns_client = getattr(self, "_owns_client", False)
        self.collection = None
        self.client = None
        if client is None or not owns_client:
            return
        system = getattr(client, "_system", None)
        if system is not None and hasattr(system, "stop"):
            try:
                system.stop()
            except Exception:
                pass
        try:
            from chromadb.api.shared_system_client import SharedSystemClient

            SharedSystemClient.clear_system_cache()
        except Exception:
            pass

    def __enter__(self) -> "VectorMemory":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def add(self, text: str, category: str = "general", metadata: dict = None) -> str:
        """添加向量记忆"""
        doc_id = hashlib.md5(f"{text}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        meta = metadata or {}
        meta["category"] = category
        meta["timestamp"] = datetime.now().isoformat()
        meta["doc_id"] = doc_id

        self.collection.add(ids=[doc_id], documents=[text], metadatas=[meta])
        return doc_id

    def search(self, query: str, n: int = 5, category: str = None, where: dict = None) -> List[Dict]:
        """搜索向量记忆"""
        try:
            where_filter = {}
            if category:
                where_filter["category"] = category
            if where:
                where_filter.update(where)

            results = self.collection.query(
                query_texts=[query],
                n_results=n,
                where=where_filter if where_filter else None,
            )

            items = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    item = {
                        "text": doc,
                        "similarity": (results["distances"][0][i] if results["distances"] else 0),
                        "metadata": (results["metadatas"][0][i] if results["metadatas"] else {}),
                        "id": results["ids"][0][i],
                    }
                    items.append(item)
            return items
        except Exception as e:
            print(f"搜索失败: {e}")
            return []

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_vectors": self.collection.count(),
            "collection_name": self.collection_name,
            "initialized": True,
        }


vector_memory = VectorMemory()
