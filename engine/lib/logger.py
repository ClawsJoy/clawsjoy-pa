"""统一日志框架"""

import logging
import sys
from datetime import datetime
from pathlib import Path


class EngineLogger:
    """统一日志管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        self.logger = logging.getLogger("ClawsJoy")
        self.logger.propagate = False
        self.logger.setLevel(logging.INFO)

        # 控制台输出
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console.setFormatter(formatter)
        self.logger.addHandler(console)

        # 文件输出
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "engine.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def get(self, name: str = None) -> logging.Logger:
        if name:
            return self.logger.getChild(name)
        return self.logger


engine_logger = EngineLogger()
