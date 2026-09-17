#!/usr/bin/env python3
"""Tool Loop Guard V1 - Tool Loop Guard V1 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""工具循环防护 v1.0.0 - 防止模型重复调用不存在的工具"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ToolLoopGuard:
    """工具循环防护"""

    VERSION = "1.0.0"

    def __init__(self):
        self.unknown_tool_calls: Dict[str, List[datetime]] = defaultdict(list)
        self.unknown_tool_threshold = 10  # 同一工具最多调用次数
        self.time_window = timedelta(minutes=5)  # 时间窗口
        self.blocked_tools: Dict[str, datetime] = {}
        self.block_duration = timedelta(minutes=10)  # 封禁时长

    def record_unknown_tool(self, tool_name: str) -> Tuple[bool, str]:
        """记录未知工具调用，返回 (是否应中断, 消息)"""
        now = datetime.now()

        # 清理过期记录
        self._cleanup_expired(now)

        # 检查是否已被封禁
        if tool_name in self.blocked_tools:
            blocked_until = self.blocked_tools[tool_name]
            if now < blocked_until:
                remaining = (blocked_until - now).seconds
                return (
                    True,
                    f"Tool '{tool_name}' is blocked for {remaining}s (too many unknown calls)",
                )
            else:
                del self.blocked_tools[tool_name]

        # 记录调用
        self.unknown_tool_calls[tool_name].append(now)
        call_count = len(self.unknown_tool_calls[tool_name])

        # 检查阈值
        if call_count >= self.unknown_tool_threshold:
            self.blocked_tools[tool_name] = now + self.block_duration
            logger.warning(
                f"Tool '{tool_name}' blocked for {self.block_duration.seconds}s (called {call_count} times)"
            )
            return (
                True,
                f"Tool '{tool_name}' blocked (exceeded {self.unknown_tool_threshold} unknown calls)",
            )

        # 警告
        if call_count >= self.unknown_tool_threshold / 2:
            remaining = self.unknown_tool_threshold - call_count
            return (
                False,
                f"Warning: Tool '{tool_name}' unknown, {remaining} more attempts before blocking",
            )

        return False, f"Tool '{tool_name}' not found"

    def _cleanup_expired(self, now: datetime):
        """清理过期的调用记录"""
        for tool_name, calls in list(self.unknown_tool_calls.items()):
            # 保留时间窗口内的调用
            valid_calls = [c for c in calls if now - c < self.time_window]
            if valid_calls:
                self.unknown_tool_calls[tool_name] = valid_calls
            else:
                del self.unknown_tool_calls[tool_name]

    def is_tool_available(self, tool_name: str, available_tools: List[str]) -> bool:
        """检查工具是否可用"""
        if tool_name in self.blocked_tools:
            return False
        return tool_name in available_tools

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "version": self.VERSION,
            "blocked_tools": dict(self.blocked_tools),
            "unknown_calls": {k: len(v) for k, v in self.unknown_tool_calls.items()},
            "threshold": self.unknown_tool_threshold,
            "time_window_seconds": self.time_window.seconds,
            "block_duration_seconds": self.block_duration.seconds,
        }

    def reset(self):
        """重置所有状态"""
        self.unknown_tool_calls.clear()
        self.blocked_tools.clear()
        logger.info("Tool loop guard reset")


tool_loop_guard = ToolLoopGuard()


if __name__ == "__main__":
    print(f"工具循环防护 v{tool_loop_guard.VERSION}")

    # 测试
    print("\n测试未知工具调用:")
    for i in range(12):
        should_stop, msg = tool_loop_guard.record_unknown_tool("nonexistent_tool")
        print(f"  {i+1}: {msg}")
        if should_stop:
            break

    print(f"\n状态: {tool_loop_guard.get_status()}")
