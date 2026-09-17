#!/usr/bin/env python3
"""Real Learner - Real Learner 模块

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

#!/usr/bin/env python3
"""真正的学习系统 - 非 mock"""

import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class RealLearner:
    """真正的学习器 - 记录真实数据"""

    def __init__(self):
        self.stats_file = Path(f"{get_data_root()}/real_stats.json")
        self.cache_file = Path(f"{get_data_root()}/execution_cache.json")
        self._load()

    def _load(self):
        """加载真实数据"""
        if self.stats_file.exists():
            with open(self.stats_file, "r") as f:
                self.stats = json.load(f)
        else:
            self.stats = {
                "total_requests": 0,
                "avg_response_time": 0,
                "task_counts": defaultdict(int),
                "user_satisfaction": [],
            }

        if self.cache_file.exists():
            with open(self.cache_file, "r") as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

    def _save(self):
        """保存真实数据"""
        # 转换 defaultdict
        stats_copy = dict(self.stats)
        stats_copy["task_counts"] = dict(self.stats["task_counts"])

        with open(self.stats_file, "w") as f:
            json.dump(stats_copy, f, indent=2)

        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def record_request(
        self,
        user_input: str,
        task: str,
        response_time: float,
        success: bool,
        cache_hit: bool = False,
    ):
        """记录真实请求"""
        self.stats["total_requests"] += 1

        # 更新平均响应时间
        old_avg = self.stats["avg_response_time"]
        n = self.stats["total_requests"]
        self.stats["avg_response_time"] = old_avg + (response_time - old_avg) / n

        # 记录任务次数
        self.stats["task_counts"][task] = self.stats["task_counts"].get(task, 0) + 1

        # 记录缓存命中
        if cache_hit:
            self.stats["cache_hit_count"] = self.stats.get("cache_hit_count", 0) + 1

        self._save()

    def cache_result(self, key: str, result: Dict, ttl: int = 3600):
        """缓存执行结果"""
        self.cache[key] = {
            "result": result,
            "cached_at": time.time(),
            "expires_at": time.time() + ttl,
            "hit_count": self.cache.get(key, {}).get("hit_count", 0),
        }
        self._save()

    def get_cached(self, key: str) -> Optional[Dict]:
        """获取缓存结果"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry["expires_at"]:
                entry["hit_count"] = entry.get("hit_count", 0) + 1
                self._save()
                return entry["result"]
            else:
                # 过期删除
                del self.cache[key]
                self._save()
        return None

    def get_stats(self) -> Dict:
        """获取真实统计"""
        cache_hit_rate = self.stats.get("cache_hit_count", 0) / max(
            1, self.stats["total_requests"]
        )

        return {
            "total_requests": self.stats["total_requests"],
            "avg_response_time_ms": round(self.stats["avg_response_time"] * 1000, 2),
            "cache_hit_rate": round(cache_hit_rate * 100, 1),
            "most_used_tasks": sorted(
                self.stats["task_counts"].items(), key=lambda x: x[1], reverse=True
            )[:5],
            "cached_items": len(self.cache),
        }


real_learner = RealLearner()


if __name__ == "__main__":
    print("真正的学习系统")
    print("=" * 40)

    # 模拟真实请求
    for i in range(5):
        real_learner.record_request(
            user_input="列出 Agent",
            task="list_agents",
            response_time=0.5,
            success=True,
            cache_hit=(i > 2),
        )

    # 查看真实统计
    stats = real_learner.get_stats()
    print(f"总请求: {stats['total_requests']}")
    print(f"平均响应: {stats['avg_response_time_ms']}ms")
    print(f"缓存命中率: {stats['cache_hit_rate']}%")
    print(f"最常用任务: {stats['most_used_tasks']}")

    def discover_pattern(self, code: str, context: str) -> Dict:
        """从代码中发现新模式"""
        import re

        patterns = []

        # 检测布局模式
        if "display: flex" in code:
            patterns.append("flex_layout")
        if "display: grid" in code:
            patterns.append("grid_layout")
        if "@keyframes" in code:
            patterns.append("animation")
        if "box-shadow" in code and "0 0" in code:
            patterns.append("glow_effect")

        if patterns:
            # 记录到成功模式
            self.stats["learned_patterns"] = self.stats.get("learned_patterns", [])
            self.stats["learned_patterns"].append(
                {
                    "context": context,
                    "patterns": patterns,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self._save()

        return {
            "discovered": patterns,
            "total": len(self.stats.get("learned_patterns", [])),
        }

    def discover_pattern(self, code: str, context: str) -> Dict:
        """从代码中发现新模式"""
        import re

        patterns = []

        # 检测布局模式
        if "display: flex" in code:
            patterns.append("flex_layout")
        if "display: grid" in code:
            patterns.append("grid_layout")
        if "@keyframes" in code:
            patterns.append("animation")
        if "box-shadow" in code and "0 0" in code:
            patterns.append("glow_effect")

        if patterns:
            # 记录到成功模式
            self.stats["learned_patterns"] = self.stats.get("learned_patterns", [])
            self.stats["learned_patterns"].append(
                {
                    "context": context,
                    "patterns": patterns,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self._save()

        return {
            "discovered": patterns,
            "total": len(self.stats.get("learned_patterns", [])),
        }

    def discover_pattern(self, code: str, context: str) -> Dict:
        """从代码中发现新模式"""
        import re

        patterns = []

        # 检测布局模式
        if "display: flex" in code:
            patterns.append("flex_layout")
        if "display: grid" in code:
            patterns.append("grid_layout")
        if "display: flex" in code and "justify-content: center" in code:
            patterns.append("flex_center")
        if "display: grid" in code and "grid-template-columns" in code:
            patterns.append("grid_responsive")
        if "@keyframes" in code:
            patterns.append("css_animation")
        if "box-shadow" in code and "0 0" in code:
            patterns.append("glow_effect")
        if "transition" in code:
            patterns.append("smooth_transition")
        if "position: absolute" in code:
            patterns.append("absolute_position")
        if "position: fixed" in code:
            patterns.append("fixed_position")

        if patterns:
            # 记录到成功模式
            if "learned_patterns" not in self.stats:
                self.stats["learned_patterns"] = []

            self.stats["learned_patterns"].append(
                {
                    "context": context,
                    "patterns": patterns,
                    "code_preview": code[:200],
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self._save()

        return {
            "discovered": patterns,
            "total": len(self.stats.get("learned_patterns", [])),
        }

    def get_learned_patterns(self) -> List[Dict]:
        """获取已学习的模式"""
        return self.stats.get("learned_patterns", [])

    def discover_pattern(self, code: str, context: str) -> dict:
        """从代码中发现新模式"""
        import re

        patterns = []

        if "display: flex" in code:
            patterns.append("flex_layout")
        if "display: grid" in code:
            patterns.append("grid_layout")
        if "box-shadow" in code:
            patterns.append("glow_effect")
        if "@keyframes" in code:
            patterns.append("animation")
        if "transition" in code:
            patterns.append("transition")

        if patterns:
            if "learned_patterns" not in self.stats:
                self.stats["learned_patterns"] = []

            self.stats["learned_patterns"].append(
                {
                    "context": context,
                    "patterns": patterns,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self._save()

        return {
            "discovered": patterns,
            "total": len(self.stats.get("learned_patterns", [])),
        }
