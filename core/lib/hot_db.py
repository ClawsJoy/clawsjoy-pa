#!/usr/bin/env python3
"""Hot Db - Hot Db 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

"""热点信息数据库 - 替代旧关键词库"""
import json
from datetime import datetime
from pathlib import Path


class HotDB:
    def __init__(self, db_path=f"{get_data_root()}/hot_db/hot_signals.json"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if self.db_path.exists():
            with open(self.db_path, "r") as f:
                return json.load(f)
        return {"signals": [], "topics": {}, "last_updated": None}

    def _save(self):
        with open(self.db_path, "w") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def add_signal(self, keyword, source, 热度=0, context=""):
        """添加热点信号"""
        signal = {
            "keyword": keyword,
            "source": source,
            "热度": 热度,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }
        self.data["signals"].append(signal)
        self._save()
        return True

    def get_hot_keywords(self, limit=10):
        """获取热点关键词（按热度排序）"""
        sorted_signals = sorted(
            self.data["signals"], key=lambda x: x.get("热度", 0), reverse=True
        )
        return sorted_signals[:limit]

    def get_by_topic(self, topic):
        """按话题获取相关热点"""
        return [s for s in self.data["signals"] if topic in s["keyword"]]


hot_db = HotDB()

if __name__ == "__main__":
    # 测试
    hot_db.add_signal("高才通续签", "入境处新闻", 热度=85)
    hot_db.add_signal("优才计划改革", "TVB新闻", 热度=70)
    print("热点:", hot_db.get_hot_keywords())
