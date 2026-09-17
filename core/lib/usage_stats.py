"""使用统计 - 匿名收集使用数据用于产品改进"""

import json
import time
from pathlib import Path
from datetime import datetime
from threading import Lock


class UsageStats:
    """使用统计收集器（匿名）"""
    
    def __init__(self, data_dir="data/stats"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.stats = self._load_stats()
    
    def _load_stats(self):
        stats_file = self.data_dir / "usage.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "total_requests": 0,
            "intent_usage": {},
            "daily_stats": [],
            "first_seen": datetime.now().isoformat()
        }
    
    def record(self, intent: str, success: bool, duration_ms: int):
        """记录一次使用"""
        with self.lock:
            self.stats["total_requests"] += 1
            
            if intent not in self.stats["intent_usage"]:
                self.stats["intent_usage"][intent] = 0
            self.stats["intent_usage"][intent] += 1
            
            # 保存
            stats_file = self.data_dir / "usage.json"
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
    
    def get_summary(self) -> dict:
        """获取统计摘要"""
        return {
            "total_requests": self.stats["total_requests"],
            "intent_usage": self.stats["intent_usage"],
            "first_seen": self.stats["first_seen"]
        }
    
    def generate_report(self) -> str:
        """生成使用报告"""
        summary = self.get_summary()
        report = f"""
📊 ClawsJoy 使用报告
==================
总请求数: {summary['total_requests']}
首次使用: {summary['first_seen']}

意图分布:
"""
        for intent, count in summary['intent_usage'].items():
            report += f"  {intent}: {count}次\n"
        
        return report


usage_stats = UsageStats()
