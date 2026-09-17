"""优雅关闭 - 确保资源正确释放"""

import logging
import signal
import sys
import time

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """优雅关闭处理器"""

    def __init__(self):
        self._shutdown_flag = False
        self._shutdown_hooks = []

        # 注册信号处理
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum):
        """处理关闭信号"""
        logger.info(f"收到信号 {signum}，准备优雅关闭...")
        self._shutdown_flag = True

        # 执行所有关闭钩子
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"关闭钩子执行失败: {e}")

        logger.info("优雅关闭完成")
        sys.exit(0)

    def register_hook(self, hook):
        """注册关闭钩子"""
        self._shutdown_hooks.append(hook)

    @property
    def should_shutdown(self) -> bool:
        return self._shutdown_flag


graceful_shutdown = GracefulShutdown()
