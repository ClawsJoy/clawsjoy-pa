#!/usr/bin/env python3
"""Agent 自我评估与进化 - 2.5 层 JSON 标准"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class AgentSelfEvaluator:
    """Agent 自我评估器 - 支持自我优化和进化"""

    VERSION = "2.5"

    def __init__(self, agent_name: str = "default"):
        self.agent_name = agent_name
        self.eval_dir = Path(f"data/agent_evaluations/{agent_name}")
        self.eval_dir.mkdir(parents=True, exist_ok=True)
        self._load_history()

    def _load_history(self):
        """加载评估历史"""
        self.history_file = self.eval_dir / "history.json"
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
            except:
                self.history = {"evaluations": [], "stats": {"total": 0, "avg_score": 0}}
        else:
            self.history = {"evaluations": [], "stats": {"total": 0, "avg_score": 0}}

    def _save_history(self):
        """保存评估历史"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def evaluate(self, user_input: str, response: str, context: Dict = None) -> Dict:
        """
        评估响应质量 - 2.5 层 JSON

        Args:
            user_input: 用户输入
            response: Agent 响应
            context: 上下文信息

        Returns:
            2.5 层 JSON 评估结果
        """
        context = context or {}

        # 计算评分
        scores = self._calculate_scores(user_input, response, context)

        # 综合评分
        overall = sum(scores.values()) / len(scores) if scores else 0.5

        # 生成改进建议
        suggestions = self._generate_suggestions(scores, overall)

        # 记录评估
        evaluation = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name,
            "user_input": user_input[:200],
            "response": response[:200],
            "scores": scores,
            "overall": overall,
            "suggestions": suggestions,
            "context": context
        }

        self.history["evaluations"].append(evaluation)
        self.history["stats"]["total"] += 1
        self.history["stats"]["avg_score"] = (
            (self.history["stats"]["avg_score"] * (self.history["stats"]["total"] - 1) + overall)
            / self.history["stats"]["total"]
        )
        self._save_history()

        return {
            "version": self.VERSION,
            "success": True,
            "scores": scores,
            "overall": overall,
            "suggestions": suggestions,
            "evaluation_id": len(self.history["evaluations"]) - 1,
            "status": "completed"
        }

    def _calculate_scores(self, user_input: str, response: str, context: Dict) -> Dict:
        """计算各项评分 (0-1)"""
        scores = {}

        # 1. 相关性 - 响应是否包含用户输入的关键词
        relevance = 0.0
        keywords = user_input.split()[:5]
        if keywords:
            matched = sum(1 for kw in keywords if kw in response)
            relevance = min(matched / len(keywords), 1.0)
        scores["relevance"] = max(relevance, 0.3)

        # 2. 完整性 - 响应长度是否合理
        response_len = len(response)
        if response_len > 50:
            scores["completeness"] = min(response_len / 200, 1.0)
        else:
            scores["completeness"] = 0.3

        # 3. 有帮助性 - 是否包含建议或解决方案
        helpful_keywords = ["建议", "推荐", "可以", "应该", "帮助", "解决", "说明", "解释"]
        helpful_score = sum(1 for kw in helpful_keywords if kw in response) / len(helpful_keywords)
        scores["helpfulness"] = min(helpful_score + 0.3, 1.0)

        # 4. 清晰度 - 是否有标点和段落
        clarity = 0.3
        if "。" in response or "." in response:
            clarity += 0.3
        if "，" in response or "," in response:
            clarity += 0.2
        if response.count("\n") > 0:
            clarity += 0.2
        scores["clarity"] = min(clarity, 1.0)

        # 5. 情感匹配 - 是否匹配用户情感
        scores["emotion_match"] = 0.7  # 默认中等偏高

        return scores

    def _generate_suggestions(self, scores: Dict, overall: float) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if overall < 0.5:
            suggestions.append("整体响应质量偏低，建议优化 Prompt 和上下文理解")

        if scores.get("relevance", 0) < 0.4:
            suggestions.append("响应相关性不足，建议增加关键词匹配和语义理解")

        if scores.get("completeness", 0) < 0.4:
            suggestions.append("响应不够完整，建议提供更详细的回答")

        if scores.get("helpfulness", 0) < 0.4:
            suggestions.append("响应不够有帮助，建议增加主动建议和解决方案")

        if scores.get("clarity", 0) < 0.4:
            suggestions.append("响应不够清晰，建议使用分段和标点符号")

        return suggestions

    def get_stats(self) -> Dict:
        """获取评估统计 - 2.5 层 JSON"""
        return {
            "version": self.VERSION,
            "agent": self.agent_name,
            "total_evaluations": self.history["stats"]["total"],
            "avg_score": round(self.history["stats"]["avg_score"], 3),
            "last_evaluation": self.history["evaluations"][-1]["timestamp"] if self.history["evaluations"] else None
        }

    def get_improvement_suggestions(self) -> List[str]:
        """获取改进建议汇总"""
        all_suggestions = []
        for eval_data in self.history["evaluations"][-10:]:  # 最近10条
            all_suggestions.extend(eval_data.get("suggestions", []))

        # 去重并计数
        suggestion_counts = {}
        for s in all_suggestions:
            suggestion_counts[s] = suggestion_counts.get(s, 0) + 1

        # 按频率排序
        sorted_suggestions = sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)
        return [s[0] for s in sorted_suggestions[:5]]

    def reset(self) -> Dict:
        """重置评估历史 - 2.5 层 JSON"""
        self.history = {"evaluations": [], "stats": {"total": 0, "avg_score": 0}}
        self._save_history()
        return {
            "version": self.VERSION,
            "success": True,
            "message": f"Agent {self.agent_name} 评估历史已重置"
        }

# 全局实例
agent_self_evaluator = AgentSelfEvaluator("default")
