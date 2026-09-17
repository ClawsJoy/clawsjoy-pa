"""懒加载管理器 - 按需初始化，避免启动时全部加载"""

import threading
from typing import Any, Callable, Dict, Optional


class LazyLoader:
    """懒加载管理器 - 单例"""

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
        self._registry: Dict[str, Callable] = {}
        self._loaded: Dict[str, Any] = {}
        self._loading: Dict[str, bool] = {}
        print("🔧 懒加载管理器已启动")

    def register(self, name: str, loader: Callable):
        """注册懒加载组件"""
        self._registry[name] = loader

    def get(self, name: str) -> Optional[Any]:
        """获取组件（按需加载）"""
        if name in self._loaded:
            return self._loaded[name]

        if name not in self._registry:
            return None

        if self._loading.get(name):
            return None

        with self._lock:
            self._loading[name] = True
            try:
                component = self._registry[name]()
                self._loaded[name] = component
            finally:
                self._loading[name] = False

        return self._loaded.get(name)

    def is_loaded(self, name: str) -> bool:
        """检查是否已加载"""
        return name in self._loaded

    def reload(self, name: str):
        """重新加载组件"""
        if name in self._loaded:
            del self._loaded[name]
        return self.get(name)


# 全局实例
lazy_loader = LazyLoader()
