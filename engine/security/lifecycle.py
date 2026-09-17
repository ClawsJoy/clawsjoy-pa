"""数据生命周期管理 - 自动清理过期数据"""

import json
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from engine.lib.logger import engine_logger


class DataLifecycleManager:
    """数据生命周期管理器"""

    def __init__(self):
        self.retention_days = 30
        self.running = False
        self.thread = None
        engine_logger.get().info("📊 数据生命周期管理器已初始化")

    def start(self):
        """启动自动清理"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()
        engine_logger.get().info("🔄 数据生命周期管理已启动")

    def stop(self):
        self.running = False

    def _cleanup_loop(self):
        """清理循环"""
        while self.running:
            try:
                self._cleanup_expired_data()
                time.sleep(86400)  # 每天执行一次
            except Exception as e:
                engine_logger.get().error(f"清理失败: {e}")

    def _cleanup_expired_data(self):
        """清理过期数据"""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        cleaned = 0

        # 清理旧日志
        log_dir = Path("logs")
        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                    log_file.unlink()
                    cleaned += 1

        # 清理旧会话
        session_dir = Path("data/sessions")
        if session_dir.exists():
            for session_file in session_dir.glob("*.json"):
                if datetime.fromtimestamp(session_file.stat().st_mtime) < cutoff:
                    session_file.unlink()
                    cleaned += 1

        engine_logger.get().info(f"🧹 清理了 {cleaned} 个过期文件")

    def get_stats(self) -> Dict:
        return {"retention_days": self.retention_days, "running": self.running}


lifecycle_manager = DataLifecycleManager()
