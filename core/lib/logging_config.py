"""统一日志配置"""

import logging
import json
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(log_level=logging.INFO, json_format=True):
    """设置统一日志"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # 根日志配置
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 控制台 handler
    console_handler = logging.StreamHandler()
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    root_logger.addHandler(console_handler)
    
    # 文件 handler
    file_handler = logging.FileHandler(logs_dir / "clawsjoy.log", encoding='utf-8')
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # 错误日志单独文件
    error_handler = logging.FileHandler(logs_dir / "error.log", encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
    
    return root_logger


# 全局日志实例
logger = setup_logging()
