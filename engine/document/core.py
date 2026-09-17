from engine.lib.logger import engine_logger

"""文档管理引擎"""

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class DocumentEngine:
    """文档管理引擎"""

    def __init__(self):
        self.documents = {}
        self._init_components()
        self._load_documents()
        engine_logger.get().info("📄 文档管理引擎已初始化")

    def _init_components(self):
        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center

            self._vector_center = vector_knowledge_center
        except Exception as e:
            self._vector_center = None

    def _load_documents(self):
        doc_dirs = [Path("docs"), Path("data/knowledge"), Path("knowledge")]
        for doc_dir in doc_dirs:
            if not doc_dir.exists():
                continue
            for file_path in doc_dir.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    doc_id = str(file_path)
                    if doc_id not in self.documents:
                        self.documents[doc_id] = {
                            "id": doc_id,
                            "name": file_path.name,
                            "path": str(file_path),
                            "type": file_path.suffix[1:] if file_path.suffix else "txt",
                            "size": file_path.stat().st_size,
                            "modified": datetime.fromtimestamp(
                                file_path.stat().st_mtime
                            ).isoformat(),
                        }
        engine_logger.get().info("   ✅ 加载 {len(self.documents)} 个文档")

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if isinstance(input_data, str):
            return self.search(input_data, kwargs.get("top_k", 5))
        return self.search(str(input_data))

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        results = []
        query_lower = query.lower()
        for doc_id, doc in self.documents.items():
            if query_lower in doc["name"].lower():
                doc["score"] = 10
                results.append(doc)
        return sorted(results, key=lambda x: -x.get("score", 0))[:top_k]

    def health_check(self) -> Dict:
        """健康检查"""
        return {
            "name": self.__class__.__name__,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
        }

    def get_stats(self) -> Dict:
        return {"total_documents": len(self.documents), "status": "active"}

    def reload(self) -> Dict:
        self.documents = {}
        self._load_documents()
        return {"success": True, "message": f"Reloaded {len(self.documents)} documents"}


document_engine = DocumentEngine()
