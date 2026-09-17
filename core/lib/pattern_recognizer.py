"""模式识别器 - 从用户行为中自动发现模式"""

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import yaml


class PatternRecognizer:
    """自动识别用户行为模式并生成规则"""

    def __init__(self):
        self.patterns_file = Path("data/learned_patterns.json")
        self.rules_file = Path("config/auto_learned_rules.yaml")
        self._load()

    def _load(self):
        if self.patterns_file.exists():
            with open(self.patterns_file, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {
                "user_sequences": {},  # 用户行为序列
                "frequent_patterns": [],  # 高频模式
                "generated_rules": [],  # 已生成的规则
                "stats": {},
            }

    def _save(self):
        with open(self.patterns_file, "w") as f:
            json.dump(self.data, f, indent=2)

    def record_behavior(self, user_id: str, user_input: str, response: str, agent: str):
        """记录用户行为"""
        now = datetime.now().isoformat()

        # 记录行为序列
        if user_id not in self.data["user_sequences"]:
            self.data["user_sequences"][user_id] = []

        self.data["user_sequences"][user_id].append(
            {
                "input": user_input[:100],
                "response": response[:100],
                "agent": agent,
                "timestamp": now,
            }
        )
        # 保留最近100条
        self.data["user_sequences"][user_id] = self.data["user_sequences"][user_id][
            -100:
        ]

        # 识别模式
        self._detect_patterns(user_id)
        self._save()

    def _detect_patterns(self, user_id: str):
        """检测重复模式"""
        sequences = self.data["user_sequences"].get(user_id, [])
        if len(sequences) < 3:
            return

        # 统计相同问题出现次数
        question_count = defaultdict(int)
        for s in sequences:
            # 提取问题核心（去除名字等变量）
            core_question = self._extract_core(s["input"])
            question_count[core_question] += 1

        # 发现高频问题（>=3次）
        for question, count in question_count.items():
            if count >= 3:
                # 找到对应的回答
                for s in sequences:
                    if self._extract_core(s["input"]) == question:
                        self._generate_rule(question, s["response"], count)
                        break

    def _extract_core(self, text: str) -> str:
        """提取问题核心（去除变量）"""
        # 去除具体名字、数字等变量
        text = re.sub(r"[\u4e00-\u9fa5]{2,4}(?=说|叫|是)", "[NAME]", text)
        text = re.sub(r"\d+", "[NUM]", text)
        text = re.sub(r"[" '"]', "", text)
        return text.strip()

    def _generate_rule(self, question: str, answer: str, frequency: int):
        """生成规则并存入配置"""
        # 检查是否已存在
        for rule in self.data["generated_rules"]:
            if rule.get("question") == question:
                rule["frequency"] = frequency
                rule["last_seen"] = datetime.now().isoformat()
                self._save_rules_to_yaml()
                return

        # 新规则
        rule = {
            "id": len(self.data["generated_rules"]) + 1,
            "question": question,
            "answer": answer,
            "frequency": frequency,
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "enabled": True,
        }
        self.data["generated_rules"].append(rule)

        # 写入 YAML 配置
        self._save_rules_to_yaml()
        print(f"📚 自动生成新规则: {question[:30]}... (出现{frequency}次)")

    def _save_rules_to_yaml(self):
        """将规则保存到 YAML 配置文件"""
        rules_config = {
            "version": "1.0.0",
            "description": "自动学习的规则",
            "learned_at": datetime.now().isoformat(),
            "rules": self.data["generated_rules"],
        }
        with open(self.rules_file, "w") as f:
            yaml.dump(rules_config, f, allow_unicode=True, default_flow_style=False)

        # 触发热重载
        self._trigger_reload()

    def _trigger_reload(self):
        """触发规则热重载"""
        try:
            from core.lib.skill_watcher import skill_watcher

            skill_watcher.reload()
        except Exception as e:
            pass

    def get_stats(self):
        return {
            "total_sequences": sum(
                len(v) for v in self.data["user_sequences"].values()
            ),
            "total_users": len(self.data["user_sequences"]),
            "generated_rules": len(self.data["generated_rules"]),
            "frequent_patterns": len(self.data["frequent_patterns"]),
        }


pattern_recognizer = PatternRecognizer()
