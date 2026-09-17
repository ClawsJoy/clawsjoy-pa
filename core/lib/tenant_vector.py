"""多租户向量隔离 - 独立集合方案"""

from core.lib.vector_knowledge_center import vector_knowledge_center


class TenantVector:
    """租户向量隔离管理器"""

    def __init__(self):
        self._collections = {}

    def _get_collection_name(self, tenant_id: str, collection_type: str) -> str:
        return f"{tenant_id}_{collection_type}"

    def get_or_create(self, tenant_id: str, collection_type: str):
        """获取或创建租户专属集合"""
        name = self._get_collection_name(tenant_id, collection_type)
        if name not in self._collections:
            self._collections[name] = vector_knowledge_center._get_or_create_collection(
                name
            )
        return self._collections[name]

    def store_memory(
        self, tenant_id: str, user_id: str, content: str, metadata: dict = None
    ):
        """存储租户记忆"""
        collection = self.get_or_create(tenant_id, "memories")
        import hashlib
        import time

        doc_id = hashlib.md5(
            f"{tenant_id}_{user_id}_{content}_{time.time()}".encode()
        ).hexdigest()[:16]
        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas={"user_id": user_id, "content": content, **(metadata or {})},
        )

    def recall_memories(self, tenant_id: str, user_id: str, query: str, top_k: int = 3):
        """召回租户记忆"""
        collection = self.get_or_create(tenant_id, "memories")
        results = collection.query(query_texts=[query], n_results=top_k)
        if not results or not results.get("metadatas"):
            return []
        return [
            m.get("content", "")
            for m in results["metadatas"][0]
            if m.get("user_id") == user_id
        ]


tenant_vector = TenantVector()
