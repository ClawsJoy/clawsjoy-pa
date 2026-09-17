"""生命体监控 - 系统健康状态"""

from typing import Dict, List
from datetime import datetime


class LifecycleMonitor:
    """ClawsJoy 生命体监控"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.status = {
            "brain": {"name": "决策层", "status": "active", "last_beat": None},
            "nervous": {"name": "编排层", "status": "active", "last_beat": None},
            "limbs": {"name": "执行层", "status": "active", "last_beat": None},
            "senses": {"name": "表达层", "status": "active", "last_beat": None},
            "skin": {"name": "横切层", "status": "active", "last_beat": None},
        }
        self.start_time = datetime.now()
        print("🧬 ClawsJoy 生命体已苏醒")
    
    def heartbeat(self, layer: str):
        """心跳"""
        if layer in self.status:
            self.status[layer]["last_beat"] = datetime.now()
            self.status[layer]["status"] = "active"
    
    def get_status(self) -> Dict:
        """获取生命体征"""
        now = datetime.now()
        for layer, info in self.status.items():
            if info["last_beat"] and (now - info["last_beat"]).seconds > 60:
                info["status"] = "warning"
        
        return {
            "uptime": str(now - self.start_time).split('.')[0],
            "layers": self.status,
            "overall": "alive" if all(s["status"] != "critical" for s in self.status.values()) else "degraded"
        }
    
    def get_vitals(self) -> Dict:
        """获取生命体征简表"""
        return {
            "status": self.get_status()["overall"],
            "uptime": self.get_status()["uptime"],
            "active_layers": [k for k, v in self.status.items() if v["status"] == "active"]
        }


lifecycle_monitor = LifecycleMonitor()
