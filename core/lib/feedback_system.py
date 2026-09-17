#!/usr/bin/env python3
"""Feedback System - Feedback System 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from core.lib.config_helper import get_data_root


class FeedbackSystem:
    """反馈系统 - 两层设计"""

    VERSION = "1.0.0"

    def __init__(self):
        self.feedback_file = Path(f"{get_data_root()}/feedback.json")
        self.satisfaction_file = Path(f"{get_data_root()}/user_satisfaction.json")
        self._init_files()

    def _init_files(self):
        if not self.feedback_file.exists():
            with open(self.feedback_file, "w") as f:
                json.dump({"success": [], "failure": []}, f)
        if not self.satisfaction_file.exists():
            with open(self.satisfaction_file, "w") as f:
                json.dump({}, f)

    def record_success(self, task: str, agent: str, duration: float = 0):
        """记录成功"""
        with open(self.feedback_file, "r") as f:
            data = json.load(f)
        data["success"].append(
            {
                "task": task,
                "agent": agent,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
            }
        )
        data["success"] = data["success"][-1000:]
        with open(self.feedback_file, "w") as f:
            json.dump(data, f, indent=2)

    def record_failure(self, task: str, agent: str, error: str):
        """记录失败"""
        with open(self.feedback_file, "r") as f:
            data = json.load(f)
        data["failure"].append(
            {
                "task": task,
                "agent": agent,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )
        data["failure"] = data["failure"][-1000:]
        with open(self.feedback_file, "w") as f:
            json.dump(data, f, indent=2)

    def update_satisfaction(self, user_id: str, channel_data: Dict):
        """更新用户满意度"""
        with open(self.satisfaction_file, "r") as f:
            data = json.load(f)

        if user_id not in data:
            data[user_id] = {"history": [], "current_score": 70}

        engagement = channel_data.get("engagement_rate", 0.5)
        growth = channel_data.get("growth_rate", 0)
        competitor_compare = channel_data.get("competitor_advantage", 0)

        score = 50 + (engagement * 30) + (growth * 10) + (competitor_compare * 10)
        score = min(100, max(0, score))

        data[user_id]["history"].append(
            {
                "score": score,
                "channel_data": channel_data,
                "timestamp": datetime.now().isoformat(),
            }
        )
        data[user_id]["current_score"] = score
        data[user_id]["history"] = data[user_id]["history"][-30:]

        with open(self.satisfaction_file, "w") as f:
            json.dump(data, f, indent=2)

        return {"user_id": user_id, "satisfaction_score": score}

    def get_stats(self) -> Dict:
        """获取反馈统计"""
        with open(self.feedback_file, "r") as f:
            data = json.load(f)

        total_success = len(data["success"])
        total_failure = len(data["failure"])
        success_rate = (
            total_success / (total_success + total_failure)
            if (total_success + total_failure) > 0
            else 0
        )

        week_ago = datetime.now() - timedelta(days=7)
        recent_success = sum(
            1
            for s in data["success"]
            if datetime.fromisoformat(s["timestamp"]) > week_ago
        )
        recent_failure = sum(
            1
            for f in data["failure"]
            if datetime.fromisoformat(f["timestamp"]) > week_ago
        )

        return {
            "total_success": total_success,
            "total_failure": total_failure,
            "success_rate": round(success_rate, 3),
            "recent_7d": {"success": recent_success, "failure": recent_failure},
            "avg_response_time": (
                sum(s.get("duration", 0) for s in data["success"][-100:]) / 100
                if data["success"]
                else 0
            ),
        }

    def should_trigger_meeting(self, user_id: str = None) -> Dict:
        """检查是否需要触发会议"""
        result = {"should": False, "reason": "", "urgency": "low"}

        stats = self.get_stats()
        success_rate = stats.get("success_rate", 0)

        if success_rate < 0.5:
            result = {
                "should": True,
                "reason": f"成功率过低: {success_rate*100:.0f}%",
                "urgency": "high",
            }
        elif success_rate < 0.7:
            result = {
                "should": True,
                "reason": f"成功率偏低: {success_rate*100:.0f}%",
                "urgency": "medium",
            }

        if user_id:
            with open(self.satisfaction_file, "r") as f:
                sat_data = json.load(f)
            user_sat = sat_data.get(user_id, {})
            current_score = user_sat.get("current_score", 70)

            if current_score < 40:
                result = {
                    "should": True,
                    "reason": f"用户{user_id}满意度极低: {current_score}",
                    "urgency": "high",
                }
            elif current_score < 60:
                result = {
                    "should": True,
                    "reason": f"用户{user_id}满意度偏低: {current_score}",
                    "urgency": "medium",
                }

        recent = stats.get("recent_7d", {})
        failures = recent.get("failure", 0)
        if failures > 10:
            result = {
                "should": True,
                "reason": f"最近7天失败次数: {failures}",
                "urgency": "medium",
            }

        return result

    def get_trigger_summary(self) -> Dict:
        """获取触发摘要"""
        trigger = self.should_trigger_meeting()
        stats = self.get_stats()

        return {
            "trigger": trigger,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }


# 全局实例
feedback_system = FeedbackSystem()
