#!/usr/bin/env python3
"""Intent Learner - Intent Learner 模块

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
"""意图学习系统 - 理解用户需求 + 从重复任务中学习"""

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class IntentLearner:
    """意图学习器 - 理解用户并学习模式"""

    def __init__(self):
        self.learning_file = Path(f"{get_data_root()}/intent_learning.json")
        self.patterns = defaultdict(int)
        self.user_history = defaultdict(list)
        self._load()

    def _load(self):
        """加载学习数据"""
        if self.learning_file.exists():
            with open(self.learning_file, "r") as f:
                data = json.load(f)
                self.patterns = defaultdict(int, data.get("patterns", {}))
                self.user_history = defaultdict(list, data.get("user_history", {}))

    def _save(self):
        """保存学习数据"""
        with open(self.learning_file, "w") as f:
            json.dump(
                {
                    "patterns": dict(self.patterns),
                    "user_history": dict(self.user_history),
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def get_intent_key(self, user_input: str) -> str:
        """生成意图的哈希键"""
        # 标准化输入
        normalized = user_input.lower().strip()
        # 移除常见停用词
        stopwords = ["的", "了", "吗", "呢", "吧", "请", "帮我"]
        for w in stopwords:
            normalized = normalized.replace(w, "")
        return hashlib.md5(normalized.encode()).hexdigest()[:8]

    def learn(self, user_input: str, task: str, success: bool, result: str = ""):
        """从任务中学习"""
        key = self.get_intent_key(user_input)
        self.patterns[key] = self.patterns.get(key, 0) + 1

        # 记录用户历史
        self.user_history[key].append(
            {
                "input": user_input,
                "task": task,
                "success": success,
                "result": result[:100],
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 只保留最近 10 条
        if len(self.user_history[key]) > 10:
            self.user_history[key] = self.user_history[key][-10:]

        self._save()

    def predict(self, user_input: str) -> Optional[Dict]:
        """预测用户意图（基于历史）"""
        key = self.get_intent_key(user_input)

        if key in self.patterns and self.patterns[key] >= 2:
            # 有过类似请求，返回历史结果
            history = self.user_history.get(key, [])
            if history:
                # 返回最成功的那个
                for h in reversed(history):
                    if h.get("success"):
                        return {
                            "matched": True,
                            "task": h.get("task"),
                            "confidence": min(0.9, self.patterns[key] * 0.1),
                            "history_count": self.patterns[key],
                            "suggestion": h.get("result", ""),
                        }

        return {"matched": False, "confidence": 0}

    def get_stats(self) -> Dict:
        """获取学习统计"""
        return {
            "total_patterns": len(self.patterns),
            "total_interactions": sum(self.patterns.values()),
            "frequent_intents": sorted(
                self.patterns.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }


class SmartIntentHandler:
    """智能意图处理器 - 结合学习和理解"""

    def __init__(self):
        self.learner = IntentLearner()
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = unified_config.get_llm_config().get(
            "fast_model",
            unified_config.get_llm_config().get(
                "fast_model",
                unified_config.get("llm.fast_model", get_llm_model(fast=True)),
            ),
        )

    def understand(self, user_input: str) -> Dict:
        """理解用户意图（学习优先）"""

        # 1. 先查学习历史
        prediction = self.learner.predict(user_input)

        if prediction.get("matched"):
            return {
                "source": "learned",
                "task": prediction.get("task"),
                "confidence": prediction.get("confidence"),
                "history_count": prediction.get("history_count"),
                "suggestion": prediction.get("suggestion"),
            }

        # 2. 没有历史，用 LLM 理解
        return self._llm_understand(user_input)

    def _llm_understand(self, user_input: str) -> Dict:
        """LLM 理解意图"""
        prompt = f"""分析用户意图，返回 JSON：
用户："{user_input}"

可用任务：list_agents, list_skills, generate_chart, unknown

输出格式：{{"task": "任务名", "confidence": 0.0-1.0, "params": {{}}}}"""

        try:
            import requests

            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 200},
                },
                timeout=15,
            )
            if resp.status_code == 200:
                response = resp.json().get("response", "")
                import re

                match = re.search(r"\{[^{}]*\}", response)
                if match:
                    return {"source": "llm", **json.loads(match.group())}
        except Exception as e:
            pass

        return {"source": "default", "task": "unknown", "confidence": 0.3}

    def record_feedback(
        self, user_input: str, task: str, success: bool, result: str = ""
    ):
        """记录反馈用于学习"""
        self.learner.learn(user_input, task, success, result)


intent_handler = SmartIntentHandler()


if __name__ == "__main__":
    print("=" * 60)
    print("意图学习系统测试")
    print("=" * 60)

    # 模拟学习过程
    test_queries = [
        "列出所有 Agent",
        "有哪些 Agent",
        "显示 Agent 列表",
        "Agent 都有谁",
        "生成架构图",
        "帮我画一张蓝图",
    ]

    for q in test_queries[:3]:
        print(f"\n1. 第一次: {q}")
        result = intent_handler.understand(q)
        print(f"   来源: {result.get('source')}")
        print(f"   任务: {result.get('task')}")

        # 模拟成功，记录学习
        intent_handler.record_feedback(
            q, result.get("task", "unknown"), True, "成功执行"
        )

    print("\n" + "=" * 60)
    print("学习后再次查询（相同意图）")
    print("=" * 60)

    # 再次查询相同意图
    result = intent_handler.understand("有哪些 Agent")
    print(f"来源: {result.get('source')}")
    print(f"任务: {result.get('task')}")
    print(f"置信度: {result.get('confidence')}")
    print(f"历史次数: {result.get('history_count')}")

    print("\n" + "=" * 60)
    print("学习统计")
    stats = intent_handler.learner.get_stats()
    print(f"学习模式数: {stats['total_patterns']}")
    print(f"总交互次数: {stats['total_interactions']}")
    print(f"高频意图: {stats['frequent_intents']}")
