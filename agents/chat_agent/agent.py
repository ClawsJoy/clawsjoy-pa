from core.agents.business.business_agent import BusinessAgent

#!/usr/bin/env python3
"""ChatAgent v3.0 - 通用对话智能体"""

import random
import re
from datetime import datetime
from typing import Dict, Optional

from core.agents.business.base_business_agent import BusinessAgent
from core.lib.smart_adapter import smart_adapter


class ChatAgent(BusinessAgent):
    """通用对话智能体"""

    name = "chat_agent"
    description = "通用对话助手"
    version = "3.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.user_name = None
        print(f"💬 ChatAgent v3.0 已上线")

    # 实现抽象方法 process（SmartAgent 要求）
    def _execute_business(self, user_input: str, context: Dict = None) -> Dict:
        """核心业务逻辑（BusinessAgent 要求）"""

        # 1. 原子技能
        atomic_result = self._check_atomic_skill(user_input)
        if atomic_result:
            return {"success": True, "response": atomic_result, "skill_type": "atomic"}

        # 2. 话本匹配
        intent = self._match_intent(user_input)
        if intent:
            template = self._get_template(intent)
            if template:
                return {"success": True, "response": template, "intent": intent}

        # 3. 名字提取
        name = self._extract_name(user_input)
        if name:
            self.user_name = name
            self.remember_forever("user_name", name)

        # 查询名字
        if any(
            q in user_input
            for q in [
                "我叫什么",
                "我的名字",
                "我叫啥",
                "我是谁",
                "叫什么名字",
                "名字是什么",
            ]
        ):
            user_name = self.recall_forever("user_name")
            if user_name:
                return {
                    "success": True,
                    "response": f"你的名字是{user_name}。",
                    "agent": self.name,
                }
            else:
                return {
                    "success": True,
                    "response": "我还不知道你的名字，请告诉我（比如：我叫张三）。",
                    "agent": self.name,
                }

        # 查询职业
        if any(
            q in user_input
            for q in [
                "做什么工作",
                "什么职业",
                "我的工作",
                "我是做什么的",
                "职业是什么",
            ]
        ):
            user_job = self.recall_forever("user_job")
            if user_job:
                return {
                    "success": True,
                    "response": f"你的职业是{user_job}。",
                    "agent": self.name,
                }
            else:
                return {
                    "success": True,
                    "response": "我还不知道你的职业，请告诉我。",
                    "agent": self.name,
                }

            return {"success": True, "response": f"你好，{name}！很高兴认识你！"}

        # 4. LLM 兜底
        response = self._llm_chat(user_input)
        return {"success": True, "response": response, "source": "llm"}

    def _check_atomic_skill(self, user_input: str) -> Optional[str]:
        """原子技能"""
        u = user_input.lower()

        m = re.search(r"([\u4e00-\u9fa5]{2,3})天气", user_input)
        if m:
            city = m.group(1)
            weathers = ["晴 ☀️", "多云 ⛅", "阴 ☁️", "小雨 🌧️", "雪 ❄️"]
            return f"📍 {city}天气：{random.choice(weathers)}"

        m = re.search(r"用(.{2,3})说(.+)", user_input)
        if m:
            return f"🗣️ {m.group(1)}：{m.group(2)}"

        m = re.search(r"(\d+)\s*([\+\-\*/])\s*(\d+)", user_input)
        if m:
            try:
                a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
                result = eval(f"{a}{op}{b}")
                return f"{a}{op}{b} = {result}"
            except Exception:
                pass

        if any(w in u for w in ["时间", "几点", "日期"]):
            now = datetime.now()
            return f"📅 {now.strftime('%Y年%m月%d日 %H:%M:%S')}"

        if "随机" in u:
            return f"🎲 随机数：{random.randint(1, 100)}"

        return None

    def _match_intent(self, user_input: str) -> Optional[str]:
        """话本匹配"""
        if "你是谁" in user_input:
            return "identity"
        if "ClawsJoy" in user_input:
            return "about"
        if "你好" in user_input:
            return "greeting"
        if "谢谢" in user_input:
            return "thanks"
        if "再见" in user_input:
            return "farewell"
        if "能做什么" in user_input:
            return "capabilities"
        return None

    def _get_template(self, intent: str) -> Optional[str]:
        """获取话本模板"""
        templates = {
            "identity": "我是 ClawsJoy 助手，您的智能助手！🎉",
            "about": "ClawsJoy 是一个智能体操作系统！🎯",
            "greeting": f"您好{'，' + self.user_name if self.user_name else ''}！很高兴为您服务！✨",
            "thanks": "不客气！很高兴能帮到您！😊",
            "farewell": "再见！欢迎随时回来！👋",
            "capabilities": "我可以帮您查天气、翻译方言、计算、回答问题、生成代码。",
        }
        return templates.get(intent)

    def _extract_name(self, user_input: str) -> Optional[str]:
        """提取名字"""
        patterns = [r"我叫[\s]*([^\s，。！？]{2,4})", r"我是[\s]*([^\s，。！？]{2,4})"]
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                return match.group(1)
        return None

    def _llm_chat(self, user_input: str) -> str:
        """LLM 聊天"""
        prompt = f"用户说：{user_input}\n请友好、简洁地回复。"
        try:
            return smart_adapter.generate(prompt, auto_select=True)
        except Exception:
            return f"收到：{user_input[:50]}..."

    def handle(self, user_input: str, context: dict = None) -> dict:
        """统一入口 - 系统规范"""
        return self._execute_business(user_input, context)


# 全局实例
chat_agent = ChatAgent()
