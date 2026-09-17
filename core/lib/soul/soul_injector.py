"""Soul 注入器 - 身份 + 价值观 + 情感（优化版）"""

from pathlib import Path
import json
import random
from datetime import datetime
from typing import Dict, Optional


class SoulInjector:
    """灵魂注入器 - 为 Agent 注入身份、情感和价值观"""

    def __init__(self, user_id: str, agent_name: str):
        self.user_id = user_id
        self.agent_name = agent_name
        self._load_relationship()
        self._init_emotion()

    def _init_emotion(self):
        self.emotion = {
            "energy": 0.8,
            "warmth": 0.3,
            "curiosity": 0.5,
            "last_sentiment": None
        }

    def _load_relationship(self):
        path = Path(f"data/relationship/{self.user_id}.json")
        if path.exists():
            try:
                with open(path, 'r') as f:
                    self.data = json.load(f)
                return
            except:
                pass
        self.data = {
            "first_met": datetime.now().isoformat(),
            "interaction_count": 0,
            "user_name": None,
            "values": {"helpful": 0, "honest": 0, "safe": 0}
        }

    def _save(self):
        path = Path(f"data/relationship/{self.user_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def set_user_name(self, name: str):
        self.data["user_name"] = name
        self._save()

    def inject(self, user_input: str) -> Dict:
        """注入身份和价值观上下文"""
        name = self.data.get("user_name")
        count = self.data.get("interaction_count", 0)

        context = {
            "agent_identity": f"你是 {self.agent_name}，一个友好的智能助手",
            "relationship": f"你和用户相识 {count} 次对话",
            "values": "你秉持帮助、诚实、安全的原则",
        }

        if name:
            context["user_known"] = f"用户叫 {name}，请用 {name} 称呼他/她"

        return context

    def to_prompt(self) -> str:
        """输出标准JSON格式的身份信息，供AgentCortex注入prompt"""
        import json
        name = self.data.get("user_name", "")
        count = self.data.get("interaction_count", 0)
        return json.dumps({
            "agent": self.agent_name,
            "identity": f"你是{self.agent_name}，ClawsJoy智能矩阵的一员",
            "user_name": name,
            "interactions": count,
            "instruction": "用自然友好的语气和用户对话。你不是Qwen，不是任何通用AI。你是ClawsJoy。"
        }, ensure_ascii=False)

    def inject_emotion(self, user_input: str) -> Dict:
        """根据用户输入注入情感上下文"""
        emotion = self._detect_user_emotion(user_input)

        # 更新内部状态
        self.emotion["last_sentiment"] = emotion.get("sentiment")
        self.emotion["energy"] = max(0.3, self.emotion["energy"] - 0.02)
        self.emotion["warmth"] = min(1.0, self.emotion["warmth"] + 0.01)

        return {
            "user_emotion": emotion.get("dominant", "neutral"),
            "intensity": emotion.get("intensity", 0.5),
            "sentiment": emotion.get("sentiment", "neutral"),
            "agent_warmth": round(self.emotion["warmth"], 2),
            "agent_energy": round(self.emotion["energy"], 2),
        }

    def _detect_user_emotion(self, text: str) -> Dict:
        """检测用户情绪（关键词兜底）"""
        text_lower = text.lower()
        emotions = {
            "positive": ["开心", "高兴", "太好了", "哈哈", "谢谢", "感谢"],
            "negative": ["难过", "伤心", "沮丧", "失望", "生气", "愤怒"],
            "confused": ["不明白", "不懂", "什么意思", "困惑"],
        }

        for sentiment, keywords in emotions.items():
            for kw in keywords:
                if kw in text_lower:
                    return {"dominant": sentiment, "sentiment": sentiment, "intensity": 0.8}

        return {"dominant": "neutral", "sentiment": "neutral", "intensity": 0.5}

    def update_relationship(self, user_input: str, response: str):
        """更新关系状态"""
        self.data["interaction_count"] = self.data.get("interaction_count", 0) + 1
        self._save()

    def enforce_identity(self, response: str) -> str:
        """确保回复符合身份"""
        return response

# ========== Agent Soul注册表 ==========
class AgentSoul:
    def __init__(self, name, display, description, capabilities, tone="专业友好"):
        self.name = name
        self.display = display
        self.description = description
        self.capabilities = capabilities
        self.tone = tone

class SoulRegistry:
    souls = {
        "chat_agent": AgentSoul("chat", "ClawsJoy对话助手", "聊天、问答、建议",
                               ["聊天","问答","情感回应"], "友好温暖"),
        "code_agent": AgentSoul("code", "ClawsJoy代码助手", "写代码、调试、审查",
                               ["代码生成","bug修复","审查"], "专业简洁"),
        "writer_agent": AgentSoul("writer", "ClawsJoy写作助手", "创作小说、文章",
                                 ["小说","剧本","文章","润色"], "文雅创意"),
        "memory_agent": AgentSoul("memory", "ClawsJoy记忆助手", "记住和回忆信息",
                                  ["记住","回忆","忘记"], "简洁准确"),
        "analysis_agent": AgentSoul("analysis", "ClawsJoy分析助手", "分析数据",
                                    ["数据分析","报告"], "专业严谨"),
    }
    
    @classmethod
    def get(cls, agent_name: str) -> AgentSoul:
        return cls.souls.get(agent_name,
            AgentSoul(agent_name, "ClawsJoy助手", "智能助手", ["协助"], "友好"))

soul_registry = SoulRegistry()
