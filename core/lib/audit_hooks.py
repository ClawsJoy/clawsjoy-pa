"""审计钩子实现"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class AuditHooks:
    """审计钩子集合"""
    
    @classmethod
    def log_request_start(cls, user_id: str, message: str, config: Dict = None) -> None:
        """记录请求开始"""
        cls._write_audit_log(user_id, "request_start", {"message": message[:200]})
    
    @classmethod
    def log_request_end(cls, user_id: str, response: str, duration_ms: float, config: Dict = None) -> None:
        """记录请求结束"""
        cls._write_audit_log(user_id, "request_end", {
            "response": response[:200],
            "duration_ms": duration_ms
        })
    
    @classmethod
    def _write_audit_log(cls, user_id: str, action: str, data: Dict):
        """写入审计日志"""
        audit_dir = Path(f"data/users/{user_id}/audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        audit_file = audit_dir / f"{datetime.now().strftime('%Y%m%d')}.json"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            **data
        }
        
        existing = []
        if audit_file.exists():
            try:
                with open(audit_file, 'r') as f:
                    existing = json.load(f)
            except:
                pass
        
        existing.append(entry)
        with open(audit_file, 'w') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)


def log_start(user_id, message, config=None):
    AuditHooks.log_request_start(user_id, message, config)

def log_end(user_id, response, duration_ms, config=None):
    AuditHooks.log_request_end(user_id, response, duration_ms, config)
