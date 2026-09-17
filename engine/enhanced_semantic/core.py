"""增强语义理解引擎"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.semantic.enhanced import enhanced_semantic


class EnhancedSemanticEngine:
    """增强语义理解引擎"""

    def __init__(self):
        self._engine = enhanced_semantic

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self._process_string(input_data, **kwargs)
        return self._process_dict(input_data, **kwargs)

    def _process_string(self, text: str, **kwargs) -> Dict:
        """处理字符串"""
        user_id = kwargs.get("user_id", "default")
        history = kwargs.get("history", [])
        return self._engine.understand_with_context(text, user_id, history)

    def _process_dict(self, data: dict, **kwargs) -> Dict:
        """处理字典"""
        text = data.get("text", "")
        user_id = data.get("user_id", "default")
        history = data.get("history", [])
        return self._engine.understand_with_context(text, user_id, history)

    def get_stats(self) -> Dict:
        return self._engine.get_stats()

    def reload(self) -> Dict:
        return {"success": True, "message": "Enhanced semantic engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "enhanced_semantic_engine", "status": "healthy"}


enhanced_semantic_engine = EnhancedSemanticEngine()
