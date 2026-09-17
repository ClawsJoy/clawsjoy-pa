"""增强健康检查 - 检查各组件状态"""

import sqlite3
from pathlib import Path
from typing import Any, Dict

import psutil


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self._component_status = {}

    def check_database(self) -> Dict[str, Any]:
        """检查数据库健康"""
        db_files = list(Path("data").glob("*.db"))
        db_status = {
            "total": len(db_files),
            "size_kb": sum(f.stat().st_size for f in db_files) / 1024,
            "status": "healthy",
        }

        # 检查写入权限
        test_db = Path("data/test_write.db")
        try:
            conn = sqlite3.connect(test_db)
            conn.execute("CREATE TABLE test (id int)")
            conn.close()
            test_db.unlink()
            db_status["writeable"] = True
        except Exception as e:
            db_status["writeable"] = False
            db_status["status"] = "degraded"
            db_status["error"] = str(e)

        return db_status

    def check_memory(self) -> Dict[str, Any]:
        """检查内存健康"""
        mem = psutil.virtual_memory()
        status = "healthy"
        if mem.percent > 90:
            status = "critical"
        elif mem.percent > 75:
            status = "warning"

        return {
            "total_gb": mem.total / 1024**3,
            "available_gb": mem.available / 1024**3,
            "percent": mem.percent,
            "status": status,
        }

    def check_disk(self) -> Dict[str, Any]:
        """检查磁盘健康"""
        disk = psutil.disk_usage("/")
        status = "healthy"
        if disk.percent > 90:
            status = "critical"
        elif disk.percent > 75:
            status = "warning"

        return {
            "total_gb": disk.total / 1024**3,
            "free_gb": disk.free / 1024**3,
            "percent": disk.percent,
            "status": status,
        }

    def check_llm(self) -> Dict[str, Any]:
        """检查 LLM 服务健康"""
        import requests

        from core.lib.unified_config import unified_config

        llm_url = unified_config.get("llm.endpoint", "http://localhost:11434")
        try:
            resp = requests.get(f"{llm_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return {"status": "healthy", "endpoint": llm_url}
            else:
                return {
                    "status": "degraded",
                    "endpoint": llm_url,
                    "code": resp.status_code,
                }
        except Exception as e:
            return {"status": "unhealthy", "endpoint": llm_url, "error": str(e)}

    def check_all(self) -> Dict[str, Any]:
        """全面健康检查"""
        return {
            "database": self.check_database(),
            "memory": self.check_memory(),
            "disk": self.check_disk(),
            "llm": self.check_llm(),
            "timestamp": __import__("time").time(),
        }


health_checker = HealthChecker()
