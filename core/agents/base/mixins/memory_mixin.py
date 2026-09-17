#!/usr/bin/env python3
"""记忆系统 Mixin - 修复版"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryMixin:
    """记忆系统混入类"""

    def _init_memory_dir(self):
        """初始化记忆目录"""
        from pathlib import Path

        from core.lib.config_helper import get_data_root

        # 确保有 user_id 和 name 属性
        user_id = getattr(self, "user_id", "default")
        agent_name = getattr(self, "name", "unknown")

        self.memory_dir = Path(get_data_root()) / "agents" / agent_name / user_id
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 初始化记忆字典
        self._memory = {}

    def _load_memory(self):
        """加载记忆"""
        if not hasattr(self, "memory_dir"):
            self._init_memory_dir()

        memory_file = self.memory_dir / "memory.json"
        if memory_file.exists():
            try:
                with open(memory_file, "r") as f:
                    self._memory = json.load(f)
            except Exception:
                self._memory = {}
        else:
            self._memory = {}

    def _save_memory(self):
        """保存记忆"""
        if not hasattr(self, "memory_dir"):
            return
        memory_file = self.memory_dir / "memory.json"
        with open(memory_file, "w") as f:
            json.dump(self._memory, f, indent=2)

    def remember(self, key: str, value: Any):
        """记住信息"""
        if not hasattr(self, "_memory"):
            self._load_memory()
        self._memory[key] = value
        self._save_memory()

    def recall(self, key: str = None) -> Any:
        """回忆信息"""
        if not hasattr(self, "_memory"):
            self._load_memory()
        if key:
            return self._memory.get(key)
        return self._memory.copy()

    def forget(self, key: str):
        """忘记信息"""
        if not hasattr(self, "_memory"):
            self._load_memory()
        if key in self._memory:
            del self._memory[key]
            self._save_memory()

    def clear_memory(self):
        """清空记忆"""
        self._memory = {}
        self._save_memory()

    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        return {
            "total_items": len(getattr(self, "_memory", {})),
            "memory_dir": str(getattr(self, "memory_dir", "unknown")),
        }
