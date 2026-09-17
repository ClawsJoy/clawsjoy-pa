#!/usr/bin/env python3
"""Self Learning Coordinator - Self Learning Coordinator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

# 只导入确实存在的模块
from agents.chat_agent.agent import chat_agent
from core.agents.builtin.personal_butler_v2 import PersonalButlerV2
from core.lib.skill_loader_v3 import skill_loader
from core.lib.skill_registry_v6 import SkillRegistryV6 as SkillRegistryV2

# 尝试导入可选模块
try:
    from core.lib.memory_manager import MemoryManager

    HAS_MEMORY_MANAGER = True
except ImportError:
    HAS_MEMORY_MANAGER = False
    print("⚠️ memory_manager 未找到，将使用基础记忆")

try:
    from core.lib.vector_retriever import VectorRetriever

    HAS_VECTOR_RETRIEVER = True
except ImportError:
    HAS_VECTOR_RETRIEVER = False
    print("⚠️ vector_retriever 未找到，将跳过向量检索")


class SelfLearningCoordinator:
    """自我学习协调器 - 利用你现有的所有能力"""

    def __init__(self):
        # 使用你现有的模块
        self.chat_agent = chat_agent
        self.butler = PersonalButlerV2(user_id="self_learner")
        self.skill_registry = SkillRegistryV2()

        # 学习数据存储（利用你现有的 memory 目录）
        self.memory_dir = Path("memory/long_term")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.knowledge_dir = Path("knowledge")

        # 学习统计
        self.stats = {
            "total_learnings": 0,
            "successful_learnings": 0,
            "failed_learnings": 0,
            "by_scenario": {},
        }

        self._load_stats()

    def _load_stats(self):
        stats_file = self.memory_dir / "learning_stats.json"
        if stats_file.exists():
            try:
                with open(stats_file) as f:
                    self.stats = json.load(f)
            except Exception as e:
                pass

    def _save_stats(self):
        stats_file = self.memory_dir / "learning_stats.json"
        with open(stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

    def learn_from_scenario(self, scenario: Dict) -> Dict:
        """从单个场景学习"""
        scenario_type = scenario.get("type", "unknown")
        user_input = scenario.get("input", "")
        expected_outcome = scenario.get("expected", "")

        start_time = time.time()

        try:
            # 使用你的 chat_agent 处理
            result = self.chat_agent.process(user_input)

            response = result.get("response", "")
            success = result.get("success", False)

            # 记录到 personal_butler 的记忆中
            try:
                self.butler._load_data()
                self.butler.memory["history"].append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "user_input": user_input,
                        "response": response,
                        "success": success,
                    }
                )
                self.butler._save_data()
            except Exception as e:
                print(f"⚠️ 保存到 butler 失败: {e}")

            # 如果成功，存入长期记忆
            if success:
                self._store_success_case(user_input, response, scenario_type)

            # 更新统计
            self.stats["total_learnings"] += 1
            if success:
                self.stats["successful_learnings"] += 1
            else:
                self.stats["failed_learnings"] += 1

            scenario_stat = self.stats["by_scenario"].get(
                scenario_type, {"total": 0, "success": 0}
            )
            scenario_stat["total"] += 1
            if success:
                scenario_stat["success"] += 1
            self.stats["by_scenario"][scenario_type] = scenario_stat

            self._save_stats()

            return {
                "success": success,
                "response": response[:100] + "..." if len(response) > 100 else response,
                "scenario": scenario_type,
                "duration": time.time() - start_time,
            }

        except Exception as e:
            self.stats["failed_learnings"] += 1
            self._save_stats()
            return {"success": False, "error": str(e), "scenario": scenario_type}

    def _store_success_case(self, user_input: str, response: str, scenario_type: str):
        """存储成功案例到长期记忆"""
        memory_file = self.memory_dir / f"success_{int(time.time())}.json"
        with open(memory_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "scenario": scenario_type,
                    "user_input": user_input,
                    "response": response[:500],
                    "tags": ["learned", scenario_type],
                },
                f,
                indent=2,
            )

        # 同时更新 personal_butler 的学习模式
        try:
            self.butler.patterns["learned"].append(
                {
                    "pattern": user_input[:100],
                    "response": response[:200],
                    "confidence": 0.7,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            self.butler._save_data()
        except Exception as e:
            print(f"⚠️ 更新 patterns 失败: {e}")

        print(f"📚 已学习: {user_input[:50]}...")

    def run_batch(self, scenarios: List[Dict]) -> Dict:
        """批量学习"""
        results = []
        total = len(scenarios)
        for i, scenario in enumerate(scenarios):
            print(
                f"📖 学习进度: {i+1}/{total} - {scenario.get('type', 'unknown')}: {scenario.get('input', '')[:40]}..."
            )
            result = self.learn_from_scenario(scenario)
            results.append(result)
            time.sleep(0.3)  # 避免过载

        success_count = sum(1 for r in results if r["success"])
        success_rate = success_count / len(results) if results else 0

        return {
            "total": len(results),
            "success_count": success_count,
            "success_rate": success_rate,
            "results": results,
        }


# 场景生成器 - 基于现有技能
class ScenarioGenerator:
    """基于现有技能生成学习场景"""

    def __init__(self):
        self.skill_loader = skill_loader
        self.skills = self.skill_loader.list_all()

        # 场景模板
        self.templates = {
            "greeting": [
                "你好",
                "早上好",
                "晚上好",
                "你好吗",
                "很高兴认识你",
                "今天怎么样",
            ],
            "skill_query": [
                "有哪些{}技能？",
                "帮我找{}相关的功能",
                "{}怎么用？",
                "有没有{}的功能",
            ],
            "skill_execute": ["帮我{}", "执行{}", "请{}", "{}"],
            "info_query": [
                "现在几点了？",
                "今天星期几？",
                "系统状态怎么样？",
                "有多少个技能可以用？",
            ],
        }

    def generate(self, count: int = 10) -> List[Dict]:
        """生成学习场景"""
        scenarios = []

        # 基于真实技能生成场景
        for i in range(count):
            # 随机选择技能
            if self.skills and random.random() > 0.3:
                skill_name = random.choice(self.skills)
            else:
                skill_name = "add"

            scenario_type = random.choice(list(self.templates.keys()))
            template = random.choice(self.templates[scenario_type])

            if "{}" in template:
                user_input = template.format(skill_name)
            else:
                user_input = template

            scenarios.append(
                {
                    "type": scenario_type,
                    "input": user_input,
                    "expected": (
                        f"成功调用{skill_name}"
                        if scenario_type == "skill_execute"
                        else "正常回复"
                    ),
                }
            )

        return scenarios
