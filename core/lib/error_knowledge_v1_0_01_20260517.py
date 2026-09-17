#!/usr/bin/env python3
"""Error Knowledge V1 0 01 20260517 - Error Knowledge V1 0 01 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""错误知识库 - 配置驱动版"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.lib.config_driver import config_driver


class ErrorKnowledge:
    """错误知识库"""

    VERSION = "1.0.02"

    def __init__(self):
        self.root = Path("PROJECT_ROOT")
        self.error_file = self.root / "data" / "error_learning.json"
        # 从配置读取阈值
        self.max_retry = config_driver.get("thresholds.max_retry_same_error", 3)
        self.skip_enabled = config_driver.get(
            "optimization.skip_on_repeated_failure", True
        )

    def _load_errors(self) -> List[Dict]:
        """加载错误列表"""
        if self.error_file.exists():
            try:
                with open(self.error_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("learned_errors", [])
            except Exception as e:
                return []
        return []

    def _save_errors(self, errors: List[Dict]):
        """保存错误列表"""
        with open(self.error_file, "w", encoding="utf-8") as f:
            json.dump({"learned_errors": errors}, f, indent=2, ensure_ascii=False)

    def query(self, task_name: str) -> Optional[Dict]:
        """查询错误"""
        for err in self._load_errors():
            if err.get("task") == task_name:
                return err
        return None

    def add(self, task_name: str, error_msg: str, skill: str = "") -> Dict:
        """添加错误"""
        errors = self._load_errors()

        # 查找已存在的错误
        for err in errors:
            if err.get("task") == task_name:
                err["retry_count"] = err.get("retry_count", 0) + 1
                err["last_seen"] = datetime.now().isoformat()
                self._save_errors(errors)
                return err

        # 新增错误
        new_error = {
            "task": task_name,
            "error": error_msg[:200],
            "skill": skill,
            "retry_count": 1,
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        }
        errors.append(new_error)
        self._save_errors(errors)
        return new_error

    def should_skip(self, task_name: str) -> Tuple[bool, str]:
        """判断是否应该跳过任务"""
        if not self.skip_enabled:
            return False, "跳过功能已禁用"

        error = self.query(task_name)
        if error:
            retries = error.get("retry_count", 0)
            if retries >= self.max_retry:
                return True, f"重复失败 {retries} 次 (阈值: {self.max_retry})"

        return False, ""

    def get_stats(self) -> Dict:
        """获取统计信息"""
        errors = self._load_errors()
        return {
            "total_errors": len(errors),
            "max_retry": self.max_retry,
            "skip_enabled": self.skip_enabled,
        }


# 全局实例
error_knowledge = ErrorKnowledge()


if __name__ == "__main__":
    print(f"错误知识库 v{error_knowledge.VERSION}")
    print(f"统计: {error_knowledge.get_stats()}")
