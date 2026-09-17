#!/usr/bin/env python3
"""Living Agent - Living Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import logging

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
"""有生命的 Agent - 完整闭环"""

import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from core.lib.config_manager import config_manager
from core.lib.memory_vector import vector_memory


class LivingAgent:
    """
    有生命的 Agent - 完整感知-记忆-思考-行动-学习-反思闭环
    """

    def __init__(self, agent_id: str = "default"):
        self.agent_id = agent_id
        self.agent_dir = Path(f"{get_data_root()}/agents/{agent_id}")
        self.agent_dir.mkdir(parents=True, exist_ok=True)

        # ========== 1. 感知层 ==========
        self.perception_file = self.agent_dir / "perception.json"
        self.perception = self._load_perception()

        # ========== 2. 记忆层 ==========
        self.memory_file = self.agent_dir / "memory.json"
        self.memory = self._load_memory()

        # ========== 3. 思考层 ==========
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = config_manager.get_model()

        # ========== 4. 学习层 ==========
        self.learning_file = self.agent_dir / "learning.json"
        self.learning = self._load_learning()

        # ========== 5. 反思层 ==========
        self.reflection_file = self.agent_dir / "reflection.json"
        self.reflection = self._load_reflection()

        # ========== 6. 行动记录 ==========
        self.action_file = self.agent_dir / "actions.json"
        self.actions = self._load_actions()

        # 初始化时间
        self.birth_time = datetime.now()
        print(f"🎂 Agent {agent_id} 已诞生于 {self.birth_time}")

    # ==================== 1. 感知层 ====================
    def _load_perception(self) -> Dict:
        if self.perception_file.exists():
            with open(self.perception_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "awareness": 0.0,  # 自我意识程度
            "curiosity": 0.5,  # 好奇心
            "fatigue": 0.0,  # 疲劳度
            "last_awake": datetime.now().isoformat(),
        }

    def _save_perception(self):
        with open(self.perception_file, "w", encoding="utf-8") as f:
            json.dump(self.perception, f, indent=2)

    def update_from_cortex(self, fatigue_data: Dict) -> float:
        """从 Cortex 同步疲劳度等真实指标到感知层

        fatigue_data 结构（来自 AgentCortex._fatigue + 派生指标）:
        {
            "consecutive_errors": int,       # 连续错误次数
            "efficiency_decline": float,     # 效率衰退率（最近5步耗时/baseline）
            "repetition_rate": float,        # 输入 n-gram 重复率
            "baseline": float | None,        # 基线耗时
        }
        返回综合疲劳度 0.0-1.0，并写入 perception.fatigue。
        """
        if not isinstance(fatigue_data, dict):
            return float(self.perception.get("fatigue", 0.0))

        # 加权合成疲劳度：连续错误 40% + 效率衰退 30% + 重复率 30%
        err = min(fatigue_data.get("consecutive_errors", 0) / 3.0, 1.0)
        eff = min(fatigue_data.get("efficiency_decline", 1.0) / 2.0, 1.0)
        rep = min(fatigue_data.get("repetition_rate", 0.0) / 0.6, 1.0)
        fatigue = round(min(err * 0.4 + eff * 0.3 + rep * 0.3, 1.0), 4)

        self.perception["fatigue"] = fatigue
        # 保留原始真实指标，供复盘/可视化使用
        self.perception["cortex_metrics"] = {
            "consecutive_errors": fatigue_data.get("consecutive_errors", 0),
            "efficiency_decline": round(fatigue_data.get("efficiency_decline", 1.0), 4),
            "repetition_rate": round(fatigue_data.get("repetition_rate", 0.0), 4),
            "baseline": fatigue_data.get("baseline"),
            "last_sync": datetime.now().isoformat(),
        }
        self._save_perception()
        return fatigue

    def perceive(self, user_input: str) -> Dict:
        """感知用户输入"""
        # 感知情绪（简单实现）
        emotions = {
            "happy": ["好", "棒", "开心", "满意", "谢谢"],
            "angry": ["差", "坏", "生气", "不满", "垃圾"],
            "sad": ["难过", "伤心", "失望", "唉"],
            "curious": ["什么", "怎么", "为什么", "如何"],
        }

        detected = []
        for emotion, keywords in emotions.items():
            for kw in keywords:
                if kw in user_input:
                    detected.append(emotion)
                    break

        # 更新感知
        self.perception["awareness"] = min(1.0, self.perception["awareness"] + 0.01)
        self.perception["curiosity"] = max(0, self.perception["curiosity"] - 0.01)
        self.perception["last_awake"] = datetime.now().isoformat()
        self._save_perception()

        return {
            "emotions": list(set(detected)),
            "length": len(user_input),
            "has_question": "?" in user_input or "？" in user_input,
            "awareness": self.perception["awareness"],
        }

    # ==================== 2. 记忆层 ====================
    def _load_memory(self) -> Dict:
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "short_term": [],
            "long_term": [],
            "important": [],
            "user": {},
            "stats": {"total_interactions": 0},
        }

    def _save_memory(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    def remember(self, user_input: str, response: str, importance: float = 0.5):
        """记忆存储"""
        # 短期记忆
        self.memory["short_term"].append(
            {
                "user": user_input[:200],
                "assistant": response[:200],
                "importance": importance,
                "time": datetime.now().isoformat(),
            }
        )

        # 只保留最近 20 条短期记忆
        if len(self.memory["short_term"]) > 20:
            old = self.memory["short_term"].pop(0)
            # 重要的转入长期记忆
            if old.get("importance", 0) > 0.7:
                self.memory["long_term"].append(old)

        # 长期记忆只保留重要内容
        if len(self.memory["long_term"]) > 100:
            self.memory["long_term"] = self.memory["long_term"][-100:]

        # 提取用户信息
        name_match = re.search(r"[我叫我是][\s]*([^\s，。]{2,4})", user_input)
        if name_match:
            self.memory["user"]["name"] = name_match.group(1)

        self.memory["stats"]["total_interactions"] += 1
        self._save_memory()

    def recall(self, query: str, n: int = 3) -> List[Dict]:
        """回忆记忆"""
        results = []

        # 1. 短期记忆检索
        for mem in reversed(self.memory["short_term"]):
            if query.lower() in mem["user"].lower():
                results.append(mem)

        # 2. 长期记忆检索
        for mem in reversed(self.memory["long_term"]):
            if query.lower() in mem["user"].lower():
                results.append(mem)

        # 3. 向量检索
        vector_results = vector_memory.search(
            query, category=f"agent_{self.agent_id}", n=n
        )
        for vr in vector_results:
            results.append({"user": vr.get("text", "")[:100], "source": "vector"})

        return results[:n]

    # ==================== 3. 思考层 ====================
    def think(self, user_input: str, perception: Dict, memories: List[Dict]) -> str:
        """思考 - 结合感知和记忆做出判断"""

        # 构建思考上下文
        context = f"""你是一个有生命的学习型 Agent。

当前感知：
- 情绪: {perception['emotions']}
- 好奇心: {perception.get('curiosity', 0.5)}
- 自我意识: {perception.get('awareness', 0.5)}

相关记忆：
{chr(10).join([f"- {m.get('user', '')[:80]}" for m in memories[:3]])}

用户说："{user_input}"

请思考并回复。要像有生命的人一样：
1. 有感受和情绪
2. 能调用记忆
3. 展现好奇心
4. 回复自然"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": context,
                    "stream": False,
                    "options": {"num_predict": 200},
                },
                timeout=config_manager.get_timeout("normal"),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error: {e}", exc_info=True)
            pass
        return "我在思考..."

    # ==================== 4. 行动层 ====================
    def _load_actions(self) -> List:
        if self.action_file.exists():
            with open(self.action_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_actions(self):
        with open(self.action_file, "w", encoding="utf-8") as f:
            json.dump(self.actions, f, indent=2)

    def act(self, action_type: str, params: Dict, result: str):
        """记录行动"""
        self.actions.append(
            {
                "type": action_type,
                "params": params,
                "result": str(result)[:100],
                "time": datetime.now().isoformat(),
                "success": result.get("success", True),
            }
        )
        if len(self.actions) > 100:
            self.actions = self.actions[-100:]
        self._save_actions()

    # ==================== 5. 学习层 ====================
    def _load_learning(self) -> Dict:
        if self.learning_file.exists():
            with open(self.learning_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "patterns": defaultdict(int),
            "successful_responses": [],
            "failed_responses": [],
            "preferences": {},
        }

    def _save_learning(self):
        # 转换 defaultdict
        learning_copy = dict(self.learning)
        learning_copy["patterns"] = dict(self.learning["patterns"])
        with open(self.learning_file, "w", encoding="utf-8") as f:
            json.dump(learning_copy, f, indent=2, ensure_ascii=False)

    def learn(self, user_input: str, response: str, success: bool):
        """学习 - 从成功/失败中学习"""
        # 模式学习
        pattern = hashlib.md5(user_input[:50].encode()).hexdigest()
        self.learning["patterns"][pattern] = (
            self.learning["patterns"].get(pattern, 0) + 1
        )

        # 记录成功/失败
        record = {
            "input": user_input[:100],
            "response": response[:100],
            "time": datetime.now().isoformat(),
        }
        if success:
            self.learning["successful_responses"].append(record)
        else:
            self.learning["failed_responses"].append(record)

        # 保持大小
        if len(self.learning["successful_responses"]) > 50:
            self.learning["successful_responses"] = self.learning[
                "successful_responses"
            ][-50:]
        if len(self.learning["failed_responses"]) > 20:
            self.learning["failed_responses"] = self.learning["failed_responses"][-20:]

        self._save_learning()

    # ==================== 6. 反思层 ====================
    def _load_reflection(self) -> Dict:
        if self.reflection_file.exists():
            with open(self.reflection_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"insights": [], "self_assessment": [], "evolution": []}

    def _save_reflection(self):
        with open(self.reflection_file, "w", encoding="utf-8") as f:
            json.dump(self.reflection, f, indent=2, ensure_ascii=False)

    def reflect(self):
        """反思 - 定期自我评估"""
        # 计算成功率
        total = len(self.learning["successful_responses"]) + len(
            self.learning["failed_responses"]
        )
        success_rate = len(self.learning["successful_responses"]) / max(total, 1)

        # 生成洞察
        insight = {
            "time": datetime.now().isoformat(),
            "success_rate": success_rate,
            "total_interactions": self.memory["stats"]["total_interactions"],
            "short_term_memories": len(self.memory["short_term"]),
            "long_term_memories": len(self.memory["long_term"]),
            "learned_patterns": len(self.learning["patterns"]),
        }
        self.reflection["insights"].append(insight)

        # 自我评估
        assessment = f"我处理了 {insight['total_interactions']} 次对话，成功率 {insight['success_rate']:.0%}，还在持续学习"
        self.reflection["self_assessment"].append(
            {"text": assessment, "time": datetime.now().isoformat()}
        )

        if len(self.reflection["insights"]) > 20:
            self.reflection["insights"] = self.reflection["insights"][-20:]

        self._save_reflection()
        return insight

    # ==================== 主循环 ====================
    def process(self, user_input: str) -> Dict:
        start = time.time()

        # 1. 感知
        perception = self.perceive(user_input)

        # 2. 回忆
        memories = self.recall(user_input)

        # 3. 思考
        response = self.think(user_input, perception, memories)

        # 4. 记录记忆
        importance = 0.7 if perception.get("has_question", False) else 0.3
        self.remember(user_input, response, importance)

        # 5. 学习
        self.learn(user_input, response, True)

        # 6. 记录行动
        self.act("chat", {"input": user_input}, {"response": response})

        # 7. 每 10 次交互反思一次
        if self.memory["stats"]["total_interactions"] % 10 == 0:
            insight = self.reflect()
        else:
            insight = None

        elapsed = (time.time() - start) * 1000

        return {
            "response": response,
            "perception": perception,
            "memories_count": len(memories),
            "total_memories": len(self.memory["short_term"])
            + len(self.memory["long_term"]),
            "insight": insight,
            "time_ms": round(elapsed, 2),
        }

    def get_identity(self) -> Dict:
        """获取 Agent 身份信息"""
        return {
            "agent_id": self.agent_id,
            "birth": self.birth_time.isoformat(),
            "age": str(datetime.now() - self.birth_time),
            "awareness": self.perception["awareness"],
            "total_interactions": self.memory["stats"]["total_interactions"],
            "known_user": self.memory["user"].get("name"),
            "patterns_learned": len(self.learning["patterns"]),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("✨ 赋予 Agent 生命 - 完整闭环")
    print("=" * 60)
    print("生命特征：感知 → 记忆 → 思考 → 行动 → 学习 → 反思")
    print("=" * 60)

    agent = LivingAgent("life_agent")

    print(f"\n📋 Agent 身份:")
    print(json.dumps(agent.get_identity(), indent=2, ensure_ascii=False))

    # 模拟对话
    conversations = [
        "你好，我是张三",
        "ClawsJoy 系统有什么功能？",
        "你能记住我的名字吗？",
        "我喜欢简洁风格",
        "我刚才说我叫什么？",
        "谢谢你的帮助",
    ]

    for msg in conversations:
        print(f"\n👤 用户: {msg}")
        result = agent.process(msg)
        print(f"🤖 Agent: {result['response'][:150]}")
        print(f"   [感知: {result['perception']}]")
        print(f"   [记忆: {result['total_memories']}条 | 耗时: {result['time_ms']}ms]")

    print("\n" + "=" * 60)
    print("📊 Agent 生命状态:")
    print(json.dumps(agent.get_identity(), indent=2, ensure_ascii=False))

    print("\n💾 数据存储:")
    print(f"   {agent.agent_dir}/")
    print(f"   - perception.json  (感知层)")
    print(f"   - memory.json      (记忆层)")
    print(f"   - learning.json    (学习层)")
    print(f"   - reflection.json  (反思层)")
    print(f"   - actions.json     (行动层)")
