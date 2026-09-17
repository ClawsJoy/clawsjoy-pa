"""规则引擎 - 系统知识容器，多数据源聚合，只读兜底"""

from pathlib import Path
from typing import Dict, Tuple

import yaml

from engine.semantic.engines.base import BaseEngine


class RuleEngine(BaseEngine):
    """规则引擎 - 聚合系统所有知识作为兜底"""

    def __init__(self):
        self._name = "rule"
        self._priority = 4
        self._rules = {}
        self._build()

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def _build(self):
        """启动时从所有数据源构建规则"""
        self._load_from_intents()
        self._load_from_agent_caps()
        self._load_from_skills_dir()
        self._load_from_agents_dir()
        self._load_from_scriptbooks()
        self._load_core_fallback()
        self._print_stats()

    def _load_from_intents(self):
        try:
            from core.lib.unified_config import unified_config

            intents = unified_config.get("keywords.intents", {})
            for intent, config in intents.items():
                self._rules[intent] = config.get("keywords", [])
        except Exception as e:
            pass

    def _load_from_agent_caps(self):
        try:
            from core.lib.unified_config import unified_config

            caps = unified_config.get("keywords.agent_capabilities", {})
            for agent, config in caps.items():
                intent = agent.replace("_agent", "").replace("_skill", "")
                keywords = config.get("capable_of", [])
                if intent in self._rules:
                    self._rules[intent].extend(keywords)
                else:
                    self._rules[intent] = keywords
        except Exception as e:
            pass

    def _load_from_skills_dir(self):
        skills_dir = Path("skills")
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                    if skill_dir.name not in self._rules:
                        self._rules[skill_dir.name] = [skill_dir.name]

    def _load_from_agents_dir(self):
        agents_dir = Path("agents")
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if agent_dir.is_dir() and not agent_dir.name.startswith("_"):
                    intent = agent_dir.name.replace("_agent", "")
                    if intent not in self._rules:
                        self._rules[intent] = [intent, agent_dir.name]

    def _load_from_scriptbooks(self):
        for scriptbook in Path("agents").glob("*/scriptbook.yaml"):
            if scriptbook.exists():
                try:
                    with open(scriptbook) as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            for name, content in data.items():
                                if isinstance(content, dict):
                                    triggers = content.get("triggers", [])
                                    if triggers:
                                        intent = name.replace("_script", "")
                                        if intent in self._rules:
                                            self._rules[intent].extend(triggers)
                                        else:
                                            self._rules[intent] = triggers
                except Exception as e:
                    pass

    def _load_core_fallback(self):
        core = {
            "code": ["写代码", "编程", "python", "java"],
            "weather": ["天气", "气温", "温度", "预报"],
            "translate": ["翻译", "译成", "translate"],
            "calculate": [
                "加",
                "减",
                "乘",
                "除",
                "计算",
                "帮我算",
                "算一下",
                "求值",
                "运算",
                "等于多少",
            ],
            "calculate_division": ["除以", "除", "求商", "求值", "计算除法"],
            "greeting": ["你好", "您好", "hi", "hello"],
        }
        for intent, keywords in core.items():
            if intent not in self._rules:
                self._rules[intent] = keywords
            else:
                # 追加关键词到已有意图
                for kw in keywords:
                    if kw not in self._rules[intent]:
                        self._rules[intent].append(kw)

    def _print_stats(self):
        total = sum(len(k) for k in self._rules.values())
        print(f"\n📋 规则引擎:")
        print(f"  ├─ 意图数: {len(self._rules)}")
        print(f"  └─ 关键词数: {total}")

    def understand(self, text: str) -> Tuple[str, float, Dict]:
        best_intent = None
        best_keyword = ""
        best_len = 0

        for intent, keywords in self._rules.items():
            for kw in keywords:
                if kw in text and len(kw) > best_len:
                    best_intent = intent
                    best_keyword = kw
                    best_len = len(kw)

        if best_intent:
            return best_intent, 0.4, {"source": "rule", "matched": best_keyword}
        return "unknown", 0.0, {"source": "rule"}

    def get_stats(self) -> Dict:
        total = sum(len(k) for k in self._rules.values())
        return {
            "name": self.name,
            "priority": self.priority,
            "intents": len(self._rules),
            "keywords": total,
            "readonly": True,
        }

    def sync(self) -> Dict:
        self._rules = {}
        self._build()
        return self.get_stats()

    def get_capabilities(self) -> Dict:
        return self.get_stats()


rule_engine = RuleEngine()
