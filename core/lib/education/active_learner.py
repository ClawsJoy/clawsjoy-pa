#!/usr/bin/env python3
"""Active Learner - Active Learner 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""主动学习系统 - LLM 从反馈中学习"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests


class ActiveLearner:
    """让 LLM 主动学习和改进"""

    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = unified_config.get_llm_config().get(
            "fast_model",
            unified_config.get_llm_config().get(
                "fast_model",
                unified_config.get(
                    "llm.fast_model", config_helper.get_llm_model(fast=True)
                ),
            ),
        )
        self.memory_file = Path(f"{config_helper.get_data_root()}/llm_learning.json")
        self.load_memory()

    def load_memory(self):
        """加载学习记忆"""
        if self.memory_file.exists():
            with open(self.memory_file, "r") as f:
                self.memory = json.load(f)
        else:
            self.memory = {
                "lessons": [],  # 学到的教训
                "patterns": [],  # 学到的模式
                "feedback_history": [],  # 反馈历史
                "improvements": [],  # 改进记录
            }

    def save_memory(self):
        """保存学习记忆"""
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    def learn_from_feedback(self, task: str, output: str, feedback: str, score: int):
        """从反馈中学习"""
        lesson = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "output": output[:200],
            "feedback": feedback,
            "score": score,
            "improvement": self._suggest_improvement(feedback),
        }
        self.memory["lessons"].append(lesson)
        self.memory["feedback_history"].append(lesson)

        # 只保留最近 50 条
        if len(self.memory["lessons"]) > 50:
            self.memory["lessons"] = self.memory["lessons"][-50:]

        self.save_memory()
        return lesson

    def _suggest_improvement(self, feedback: str) -> str:
        """根据反馈生成改进建议"""
        if "符号" in feedback or "装饰" in feedback:
            return "不要使用任何装饰符号（#、*、-、|、%、￥等），输出纯文本"
        elif "太少" in feedback or "内容少" in feedback:
            return "增加详细描述，每个要点至少2-3句话"
        elif "格式" in feedback:
            return "使用统一的格式：名称：描述"
        return "保持输出简洁、专业"

    def apply_lessons(self, prompt: str) -> str:
        """应用学到的教训来改进输出"""
        # 提取最近的教训
        recent_lessons = self.memory["lessons"][-5:]

        lessons_text = ""
        for lesson in recent_lessons:
            lessons_text += (
                f"- 问题：{lesson['feedback']}，改进：{lesson['improvement']}\n"
            )

        enhanced_prompt = f"""请根据以下历史教训改进你的输出：

历史教训：
{lessons_text}

当前任务：{prompt}

要求：
1. 不要使用任何装饰符号（#、*、-、|、%、￥等）
2. 输出要详细、有信息量
3. 格式简洁清晰

请输出："""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": enhanced_prompt,
                    "stream": False,
                    "options": {"num_predict": 800},
                },
                timeout=45,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            print(f"生成失败: {e}")

        return ""

    def self_reflect(self, task: str, output: str) -> str:
        """自我反思：LLM 自己评估输出质量"""
        prompt = f"""请评估你刚才的输出质量：

任务：{task}

你的输出：
{output[:500]}

请自我评估：
1. 输出是否有装饰符号？（有/无）
2. 内容是否详细？（1-5分）
3. 格式是否清晰？（1-5分）
4. 如何改进？

输出 JSON 格式：
{{"has_symbols": true/false, "detail_score": 0-5, "format_score": 0-5, "improvement": "改进建议"}}"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=unified_config.get("timeouts.default", 30),
            )
            if resp.status_code == 200:
                response = resp.json().get("response", "")
                import re

                match = re.search(r"\{[^{}]*\}", response)
                if match:
                    return json.loads(match.group())
        except Exception as e:
            pass
        return {"has_symbols": True, "detail_score": 2, "format_score": 2}

    def get_statistics(self) -> Dict:
        """获取学习统计"""
        lessons = self.memory["lessons"]
        if not lessons:
            return {"total_lessons": 0, "avg_score": 0}

        scores = [l.get("score", 0) for l in lessons]
        return {
            "total_lessons": len(lessons),
            "avg_score": sum(scores) / len(scores),
            "recent_feedback": lessons[-3:] if len(lessons) >= 3 else lessons,
        }


if __name__ == "__main__":
    learner = ActiveLearner()

    print("=" * 60)
    print("LLM 主动学习系统")
    print("=" * 60)

    # 模拟学习过程
    print("\n1. 生成内容...")
    result = learner.apply_lessons("列出 ClawsJoy 的所有 Agent")
    print(f"生成结果:\n{result[:300]}")

    print("\n2. 自我反思...")
    reflection = learner.self_reflect("列出 ClawsJoy 的所有 Agent", result)
    print(f"反思结果: {reflection}")

    print("\n3. 学习统计:")
    stats = learner.get_statistics()
    print(f"总教训数: {stats['total_lessons']}")
    print(f"平均分: {stats['avg_score']:.1f}")

    print("\n✅ LLM 正在主动学习！")
