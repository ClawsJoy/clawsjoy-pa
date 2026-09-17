"""环境变量加载器 - 安全配置管理"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional


class EnvLoader:
    """环境变量加载器"""
    
    _instance = None
    _loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        """加载环境变量"""
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            print("✅ 已加载 .env 配置")
        else:
            print("⚠️ .env 不存在，使用默认配置")
        self._loaded = True
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量"""
        return os.getenv(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数环境变量"""
        try:
            return int(os.getenv(key, default))
        except ValueError:
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔环境变量"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')


env = EnvLoader()
