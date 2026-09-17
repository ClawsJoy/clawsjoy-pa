#!/usr/bin/env python3
"""Learning Hooks - Learning Hooks 模块

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

"""学习钩子 - 让 Agent 从交互中学习"""

import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class LearningHooks:
    """学习钩子 - 记录交互，让 Agent 成长"""

    def __init__(self):
        self.log_dir = Path(f"{get_data_root()}/learning_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 学习统计
        self.stats = {
            "total_interactions": 0,
            "successful_interactions": 0,
            "failed_interactions": 0,
            "learned_patterns": [],
            "user_preferences": defaultdict(dict),
        }
        self._load_stats()

    def _load_stats(self):
        stats_file = self.log_dir / "learning_stats.json"
        if stats_file.exists():
            with open(stats_file, "r") as f:
                data = json.load(f)
                self.stats.update(data)
                # 恢复 defaultdict
                self.stats["user_preferences"] = defaultdict(
                    dict, self.stats.get("user_preferences", {})
                )

    def _save_stats(self):
        stats_file = self.log_dir / "learning_stats.json"
        # 转换 defaultdict 为普通 dict
        save_data = dict(self.stats)
        save_data["user_preferences"] = dict(save_data["user_preferences"])
        with open(stats_file, "w") as f:
            json.dump(save_data, f, indent=2, default=str)

    # ========== 日志钩子 ==========
    def log_interaction(self, context: Dict) -> Dict:
        """记录用户交互 - 让 Agent 学习"""
        user_id = context.get("user_id", "unknown")
        user_input = context.get("user_input", "")
        response = context.get("response", "")
        success = context.get("success", False)
        duration = context.get("duration", 0)

        # 记录到日志文件
        log_file = self.log_dir / f"{user_id}_{datetime.now().strftime('%Y%m%d')}.jsonl"

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "input": user_input[:200],
            "response": response[:200],
            "success": success,
            "duration": duration,
            "learned": False,
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 更新统计
        self.stats["total_interactions"] += 1
        if success:
            self.stats["successful_interactions"] += 1
        else:
            self.stats["failed_interactions"] += 1

        self._save_stats()

        # 触发学习分析
        context["log_entry"] = log_entry
        return context

    # ========== 学习钩子 ==========
    def learn_from_interaction(self, context: Dict) -> Dict:
        """从交互中学习模式"""
        log_entry = context.get("log_entry", {})
        user_id = log_entry.get("user_id")
        user_input = log_entry.get("input", "")
        success = log_entry.get("success", False)

        # 学习成功模式
        if success:
            pattern = self._extract_pattern(user_input)
            if pattern:
                pattern_entry = {
                    "pattern": pattern,
                    "user_id": user_id,
                    "learned_at": datetime.now().isoformat(),
                    "confidence": 0.7,
                }

                # 避免重复
                if pattern_entry not in self.stats["learned_patterns"]:
                    self.stats["learned_patterns"].append(pattern_entry)
                    print(f"📚 学到新模式: {pattern}")

        # 学习用户偏好
        self._learn_preference(user_id, user_input, success)

        context["learned"] = True
        return context

    def _extract_pattern(self, text: str) -> str:
        """提取问题模式"""
        # 简单模式提取
        keywords = ["帮我", "怎么", "如何", "什么是", "为什么", "能不能"]
        for kw in keywords:
            if kw in text:
                pos = text.find(kw)
                pattern = text[pos : pos + 30]
                return pattern
        return None

    def _learn_preference(self, user_id: str, user_input: str, success: bool):
        """学习用户偏好"""
        # 检测用户偏好
        if "简洁" in user_input or "简单" in user_input:
            self.stats["user_preferences"][user_id]["style"] = "concise"
        elif "详细" in user_input or "具体" in user_input:
            self.stats["user_preferences"][user_id]["style"] = "detailed"

        # 检测用户活跃时间
        hour = datetime.now().hour
        self.stats["user_preferences"][user_id]["active_hour"] = hour

        self._save_stats()

    # ========== 监控钩子 ==========
    def monitor_performance(self, context: Dict) -> Dict:
        """监控性能 - 检测异常"""
        duration = context.get("duration", 0)
        success = context.get("success", False)
        user_id = context.get("user_id", "unknown")

        alerts = []

        # 检测慢响应
        if duration > 5:
            alerts.append(f"⚠️ 响应慢: {duration:.1f}秒")

        # 检测失败率
        user_stats = self._get_user_stats(user_id)
        if user_stats.get("recent_failures", 0) > 3:
            alerts.append(f"⚠️ 用户 {user_id} 失败率较高")

        # 检测学习机会
        if not success and context.get("user_input"):
            alerts.append(f"📚 学习机会: 用户问题未能解决")

        context["alerts"] = alerts
        if alerts:
            print(f"📊 监控: {', '.join(alerts)}")

        return context

    def _get_user_stats(self, user_id: str) -> Dict:
        """获取用户统计"""
        recent_failures = 0
        log_file = self.log_dir / f"{user_id}_{datetime.now().strftime('%Y%m%d')}.jsonl"

        if log_file.exists():
            with open(log_file, "r") as f:
                lines = f.readlines()[-10:]  # 最近10条
                for line in lines:
                    try:
                        entry = json.loads(line)
                        if not entry.get("success", False):
                            recent_failures += 1
                    except Exception as e:
                        pass

        return {"recent_failures": recent_failures}

    # ========== 主动服务钩子 ==========
    def check_proactive_service(self, context: Dict) -> Dict:
        """检查是否需要主动服务"""
        user_id = context.get("user_id", "unknown")
        hour = datetime.now().hour
        preferences = self.stats["user_preferences"].get(user_id, {})

        suggestions = []

        # 根据活跃时间主动问候
        if preferences.get("active_hour") == hour and hour in [8, 9, 22, 23]:
            suggestions.append("早上好！今天有什么可以帮你的？")

        # 根据失败记录主动帮助
        user_stats = self._get_user_stats(user_id)
        if user_stats.get("recent_failures", 0) >= 2:
            suggestions.append("我注意到你刚才遇到了问题，需要我换个方式解释吗？")

        context["suggestions"] = suggestions
        return context


# 全局实例
learning_hooks = LearningHooks()

# 导出钩子函数
log_interaction = learning_hooks.log_interaction
learn_from_interaction = learning_hooks.learn_from_interaction
monitor_performance = learning_hooks.monitor_performance
check_proactive_service = learning_hooks.check_proactive_service
