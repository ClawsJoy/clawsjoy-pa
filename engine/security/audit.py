from typing import Any, Dict, List, Optional

"""审计日志 - 操作追踪"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    """审计日志记录器"""

    def __init__(self):
        self.audit_file = Path("data/audit.log")
        self._lock = threading.Lock()
        print("📝 审计日志已初始化")

    def log(
        self,
        action: str,
        user_id: str,
        resource: str = None,
        details: Dict = None,
        result: str = "success",
        ip: str = None,
        user_agent: str = None,
    ) -> Dict:
        """记录审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "details": details or {},
            "result": result,
            "ip": ip,
            "user_agent": user_agent,
        }

        with self._lock:
            with open(self.audit_file, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return entry

    def query(
        self,
        user_id: str = None,
        action: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """查询审计日志"""
        results = []

        if not self.audit_file.exists():
            return results

        with open(self.audit_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if user_id and entry.get("user_id") != user_id:
                        continue
                    if action and entry.get("action") != action:
                        continue
                    if start_time and entry.get("timestamp") < start_time:
                        continue
                    if end_time and entry.get("timestamp") > end_time:
                        continue
                    results.append(entry)
                except Exception as e:
                    continue

        return results[-limit:]

    def get_stats(self) -> Dict:
        """获取统计"""
        count = 0
        if self.audit_file.exists():
            with open(self.audit_file, "r") as f:
                count = sum(1 for _ in f)
        return {"total_logs": count, "status": "active"}


audit_logger = AuditLogger()
