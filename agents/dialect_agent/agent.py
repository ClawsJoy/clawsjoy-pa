from core.agents.business.business_agent_v2 import BusinessAgentV2
#!/usr/bin/env python3
"""方言智能体 - 增强版"""

import random
import re
from typing import Dict, Optional

from core.agents.business.base_business_agent import BusinessAgent
from core.lib.smart_adapter import smart_adapter


class DialectAgent(BusinessAgentV2):
    name = "dialect_agent"
    description = "方言识别、翻译和转换"
    version = "3.0.0"

    # 方言词库
    DIALECT_WORDS = {
        "粤语": {
            "你好": "你好",
            "谢谢": "唔該",
            "对不起": "對唔住",
            "吃饭": "食飯",
            "多少钱": "幾多錢",
            "不知道": "唔知",
            "可以": "可以",
            "漂亮": "靚",
        },
        "四川话": {
            "你好": "你好噻",
            "谢谢": "谢咯",
            "对不起": "对不住",
            "吃饭": "吃莽莽",
            "多少钱": "好多钱",
            "不知道": "不晓得",
            "可以": "要得",
            "漂亮": "巴适",
        },
        "东北话": {
            "你好": "你干啥呢",
            "谢谢": "谢了嗷",
            "对不起": "对不住了",
            "吃饭": "整点饭",
            "多少钱": "多钱儿",
            "不知道": "不知道啊",
            "可以": "成",
            "漂亮": "带劲",
        },
        "上海话": {
            "你好": "侬好",
            "谢谢": "谢谢侬",
            "对不起": "对勿起",
            "吃饭": "切饭",
            "多少钱": "几钿",
            "不知道": "勿晓得",
            "可以": "好个",
            "漂亮": "灵光",
        },
    }

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.conversion_history = []
        print(f"🗣️ 方言智能体 v3.0 已上线")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - BusinessAgent 要求"""
        return self.process(user_input, context)

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        print(f"[方言] 收到: {user_input}")

        # 1. 方言翻译
        match = re.search(r"用(.{2,4})说(.+)", user_input)
        if match:
            dialect = match.group(1)
            text = match.group(2)
            result = self._translate_to_dialect(text, dialect)
            return {
                "success": True,
                "response": f"🗣️ {dialect}：{result}",
                "dialect": dialect,
                "original": text,
                "translated": result,
                "agent": self.name,
                "user_id": self.user_id,
            }

        # 2. 方言识别
        detected = self._detect_dialect(user_input)
        if detected:
            return {
                "success": True,
                "response": f"🔍 这听起来像{detected}",
                "detected_dialect": detected,
                "agent": self.name,
                "user_id": self.user_id,
            }

        # 3. 方言学习
        if "学习方言" in user_input or "教我说" in user_input:
            return self._teach_dialect(user_input)

        return {
            "success": True,
            "response": "方言功能：用「用粤语说你好」翻译，「这是什么方言」识别",
            "supported_dialects": list(self.DIALECT_WORDS.keys()),
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _translate_to_dialect(self, text: str, dialect: str) -> str:
        """翻译成方言"""
        if dialect not in self.DIALECT_WORDS:
            return f"暂不支持{dialect}，支持：{', '.join(self.DIALECT_WORDS.keys())}"

        words = self.DIALECT_WORDS[dialect]
        result = text
        for std, dial in words.items():
            if std in text:
                result = result.replace(std, dial)

        # 记录学习
        self.conversion_history.append(
            {"dialect": dialect, "original": text, "translated": result}
        )
        return result

    def _detect_dialect(self, text: str) -> Optional[str]:
        """检测方言"""
        for dialect, words in self.DIALECT_WORDS.items():
            for dial_word in words.values():
                if dial_word in text:
                    return dialect
        return None

    def _teach_dialect(self, user_input: str) -> Dict:
        """教方言"""
        match = re.search(r"教我说(.{2,4})(.+)", user_input)
        if match:
            dialect = match.group(1)
            text = match.group(2)
            translated = self._translate_to_dialect(text, dialect)
            return {
                "success": True,
                "response": f"📖 {dialect}中「{text}」说「{translated}」",
                "agent": self.name,
                "user_id": self.user_id,
            }
        return {
            "success": True,
            "response": "说「教我说粤语你好」学习方言",
            "agent": self.name,
            "user_id": self.user_id,
        }
