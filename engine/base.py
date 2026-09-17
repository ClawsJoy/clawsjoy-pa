"""原子引擎基类 - 统一接口规范"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)


class AtomicEngine(ABC):
    """原子引擎基类 - 所有引擎必须继承"""

    def __init__(self):
        self.name = self.__class__.__name__
        self.created_at = datetime.now().isoformat()
        self._initialized = True

    @abstractmethod
    def process(self, input_data: Any, **kwargs) -> Any:
        """核心处理方法 - 必须实现"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict:
        """获取统计信息 - 必须实现"""
        pass

    def reload(self) -> Dict:
        """热重载配置 - 可选实现"""
        return {"success": True, "message": "Reload not implemented"}

    def health_check(self) -> Dict:
        """健康检查"""
        return {
            "name": self.name,
            "status": "healthy" if self._initialized else "unhealthy",
            "created_at": self.created_at,
        }

    @property
    def info(self) -> Dict:
        """引擎信息"""
        return {
            "name": self.name,
            "type": self.__class__.__bases__[0].__name__,
            "initialized": self._initialized,
        }
