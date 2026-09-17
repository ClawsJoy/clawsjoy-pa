"""路径管理器 - 统一路径处理"""

import os
from pathlib import Path


class PathManager:
    """统一路径管理"""

    _instance = None
    _root = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_path()
        return cls._instance

    def _init_path(self):
        """初始化路径"""
        # 获取项目根目录
        self._root = Path(__file__).parent.parent.parent.resolve()
        print(f"📁 项目根目录: {self._root}")

    @property
    def root(self) -> Path:
        return self._root

    def get(self, *paths) -> Path:
        """获取绝对路径"""
        return self._root.joinpath(*paths)

    def ensure_dir(self, *paths) -> Path:
        """确保目录存在"""
        path = self.get(*paths)
        path.mkdir(parents=True, exist_ok=True)
        return path


path_manager = PathManager()
