#!/usr/bin/env python3
"""DialectAgent v4.3 - 方言学习引擎版"""

import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pathlib import Path
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent
from core.lib.dialect_learning_engine import DialectLearningEngine


class DialectAgentV4(BusinessAgent):
    name = "dialect_agent_v4"
    description = "智慧方言助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.user_id = user_id
        self._learner = DialectLearningEngine(user_id)
        self._mode = "idle"
        print(f"🗣 DialectAgent v{self.version} 启动")
        stats = self._learner.stats()
        v = stats["vocabulary_size"]
        r = stats["reply_templates"]
        print(f"   📚 已学 {v} 方言词 | {r} 回复 | 共 {v + r} 项")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.strip()
        mode = context.get("extracted", {}).get("_mode", "") if context else ""
        if not mode:
            mode = self._mode

        # 模式切换
        if t in ["讲方言", "方言对话", "方言模式"]:
            self._mode = "dialogue"
            return self._resp("🗣 进入方言对话模式！直接跟我说方言，听不懂我会问你~")
        if t in ["方言训练", "教方言", "方言学习"]:
            self._mode = "training"
            return self._resp("📚 进入方言训练模式！格式：食饱未 就是 吃饱了吗")
        if t in ["方言练习", "练方言"]:
            self._mode = "practice"
            return self._resp("✏️ 进入方言练习模式！我说普通话，你来说方言~")
        if t in ["列出方言", "已学方言", "方言列表"]:
            return self._list_dialects()

        # 训练模式
        if self._mode == "training" or mode == "dialect_training":
            # 回复教学：回复 X 说 Y
            reply_match = re.search(r"回复\s+(.+?)\s+说\s+(.+)", t)
            if reply_match:
                trigger = reply_match.group(1).strip()
                reply = reply_match.group(2).strip()
                self._learner.learn_reply(trigger, reply)
                return self._resp(f"✅ 学会啦！当「{trigger}」时，回复「{reply}」~")

            # 动作教学：当我说 X 就 通知/拨打 Y
            action_match = re.search(r"(?:当我说|我说)\s*(.+?)\s*(?:就|要)\s*(通知|拨打|发送|提醒)\s*(.+)", t)
            if action_match:
                trigger = action_match.group(1).strip()
                action_type = action_match.group(2).strip()
                target = action_match.group(3).strip()
                self._learner.learn_action(trigger, action_type, target)
                return self._resp(f"✅ 学会啦！当你说「{trigger}」时，系统会{action_type}{target}")

            # 词汇教学：X 就是 Y
            match = re.search(r"(.+?)\s+(?:就是|意思是|指的是|叫)\s+(.+)", t)
            if match:
                word, meaning = match.group(1).strip(), match.group(2).strip()
                self._learner.learn(word, meaning)
                return self._resp(f"✅ 学会啦！「{word}」就是「{meaning}」~")
            return self._resp("📚 格式：「食饱未 就是 吃饱了吗」")

        # 练习模式
        if self._mode == "practice" or mode == "dialect_practice":
            vocab = self._learner.vocabulary
            if vocab:
                word, info = random.choice(list(vocab.items()))
                standard = info.get("standard", info) if isinstance(info, dict) else info
                return self._resp(f"✏️ 「{standard}」用方言怎么说？")
            return self._resp("📭 还没学任何词，先用「方言训练」教我~")

        # 对话模式
        if self._mode == "dialogue" or mode == "dialect_dialogue":
            # 优先查动作触发器（不需要词库匹配）
            action = self._learner.get_action(t)
            if action:
                action_type = action.get("action", "")
                target = action.get("target", "")
                return self._resp(f"🚨 已触发：{action_type}{target}")

            # 用词库翻译
            result = t
            for word, info in sorted(self._learner.vocabulary.items(), key=lambda x: -len(x[0])):
                std = info.get("standard", info) if isinstance(info, dict) else info
                if word in result:
                    result = result.replace(word, std)

            if result != t:
                # 记录上一轮理解结果（用于上下文拼接）
                self._last_understood = result
                # 路径A：查已学回复模板
                reply_text = self._learner.get_reply(result, self._last_understood)

                # 路径A2：内置模板
                if not reply_text:
                    if "吃" in result and ("吗" in result or "没" in result):
                        reply_text = "吃饱了，谢谢！"
                    elif "你好" in result:
                        reply_text = "你好！我很好，你呢？"
                    elif "谢谢" in result or "多谢" in result:
                        reply_text = "不客气！"
                    elif "再见" in result or "拜拜" in result:
                        reply_text = "再见！"

                # 路径B：LLM 兜底
                if not reply_text:
                    try:
                        from core.lib.llm_client import llm_client

                        reply_text = llm_client.generate(
                            f"用户说：{result}\n请用普通话简短回复（20字以内）：",
                            model="qwen2.5:7b-instruct-q4_0-gpu",
                            max_tokens=50,
                            task_type="dialect_reply",
                            timeout=10,
                        )
                    except Exception:
                        pass

                if reply_text and len(reply_text.strip()) >= 2:
                    dialect_reply = self._learner.express(reply_text)
                    return self._resp(f"🗣 {dialect_reply}")
                return self._resp(f"🗣 理解: {result}")

            # 完全没匹配
            self._learner.unknown_words = [t]
            return self._resp(self._learner.ask_clarification())

        # 引导
        return self._resp("🗣 方言助手：\n  📞 「讲方言」\n  📚 「方言训练」\n  ✏️ 「方言练习」\n  📋 「列出方言」")

    def _list_dialects(self) -> Dict:
        vocab = self._learner.vocabulary
        if not vocab:
            return self._resp("📭 还没学任何方言词")
        lines = ["🗣 已学方言："]
        for word, info in list(vocab.items())[:20]:
            standard = info.get("standard", info) if isinstance(info, dict) else info
            dtype = info.get("dialect_type", "") if isinstance(info, dict) else ""
            lines.append(f"  • {word} → {standard} ({dtype})" if dtype else f"  • {word} → {standard}")
        return self._resp("\n".join(lines))

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = DialectAgentV4("test")
    print(agent.process("方言训练")["response"])
