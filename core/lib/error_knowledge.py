#!/usr/bin/env python3
"""Error Knowledge - Error Knowledge 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""错误知识库 v1.0.02 - 配置驱动版"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.lib.config_loader import config


class ErrorKnowledge:
    VERSION = "1.0.02"

    def __init__(self):
        self.root = Path("PROJECT_ROOT")
        self.error_file = self.root / "data" / "error_learning.json"
        self.max_retry = config.get("thresholds.max_retry_same_error", 3)
        self.skip_enabled = config.get("optimization.skip_on_repeated_failure", True)

    def _load_errors(self) -> List[Dict]:
        if self.error_file.exists():
            try:
                with open(self.error_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("learned_errors", [])
            except Exception as e:
                return []
        return []

    def _save_errors(self, errors: List[Dict]):
        with open(self.error_file, "w", encoding="utf-8") as f:
            json.dump({"learned_errors": errors}, f, indent=2, ensure_ascii=False)

    def query(self, task_name: str) -> Optional[Dict]:
        for err in self._load_errors():
            if err.get("task") == task_name:
                return err
        return None

    def add(self, task_name: str, error_msg: str, skill: str = "") -> Dict:
        errors = self._load_errors()
        for err in errors:
            if err.get("task") == task_name:
                err["retry_count"] = err.get("retry_count", 0) + 1
                err["last_seen"] = datetime.now().isoformat()
                self._save_errors(errors)
                return err

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
        if not self.skip_enabled:
            return False, "disabled"
        error = self.query(task_name)
        if error and error.get("retry_count", 0) >= self.max_retry:
            return True, f"重复失败 {error['retry_count']} 次"
        return False, ""

    def get_stats(self) -> Dict:
        errors = self._load_errors()
        return {"total_errors": len(errors), "max_retry": self.max_retry}


error_knowledge = ErrorKnowledge()
