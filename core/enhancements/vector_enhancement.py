from core.lib.vector_knowledge_center import vector_knowledge_center
"""向量检索增强 - 可选插件，需要时可启用"""

import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

class VectorMemoryEnhancement:
    """向量记忆增强（可选）"""
    
    def __init__(self, persist_dir="data/vector_kb"):
        self.enabled = False
        try:
            self.client = vector_knowledge_center.client
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            self.enabled = True
            print("✅ 向量记忆增强已启用")
        except Exception as e:
            print(f"⚠️ 向量记忆增强不可用: {e}")
    
    def search(self, query: str, user_id: str, top_k: int = 5):
        if not self.enabled:
            return []
        # 实现语义搜索
        pass

# 
# vector_enhancement = VectorMemoryEnhancement()
