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
        # Windows(2026-09-17): 中文 GBK 控制台编码不了日志里的 emoji(🎯🔗📝…),
        # StreamHandler 会在 emit 时 UnicodeEncodeError(且只在真控制台暴露)。
        _stream = sys.stdout
        _reconfigure = getattr(_stream, "reconfigure", None)
        if _reconfigure is not None:
            try:
                _reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        console = logging.StreamHandler(_stream)
        console.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console.setFormatter(formatter)
        self.logger.addHandler(console)

        # 文件输出
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        # Windows(2026-09-17): FileHandler 不带 encoding 时按 locale(cp936) 打开,
        # 写 emoji 直接 UnicodeEncodeError → 日志丢行 + 刷 "--- Logging error ---"。
        file_handler = logging.FileHandler(log_dir / "engine.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def get(self, name: str = None) -> logging.Logger:
        if name:
            return self.logger.getChild(name)
        return self.logger


engine_logger = EngineLogger()
