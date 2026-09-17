#!/usr/bin/env python3
"""ButlerAgent v5.0 - 私人管家"""

import re
from datetime import datetime
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class ButlerAgentV4(BusinessAgent):
    name = "butler_agent_v4"
    description = "智慧私人管家"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._todos = []
        self._history = []
        self._max_history = 10
        print(f"👤 ButlerAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input

        # 名字学习
        m = re.search(r'(?:叫我|我叫|可以叫我|称呼我|以后叫我)\s*([^\s，,。.!！?？]+)', t)
        if m and m.group(1) not in ["什么", "啥", "谁"]:
            self.remember_forever("user_name", m.group(1))
            return self._resp(f"好的主人，以后就叫您{m.group(1)}~ 😊")

        # 查询名字
        if any(kw in t for kw in ["我叫什么", "我的名字", "我是谁"]):
            name = self.recall_forever("user_name")
            return self._resp(f"您叫{name}呀~ 😊" if name else "我还不知道您的名字呢，可以告诉我吗？")

        # 添加待办
        if any(kw in t for kw in ["添加待办", "记一下", "提醒我"]):
            task = re.sub(r'(添加待办|记一下|提醒我)', '', t).strip()
            if task:
                self._todos.append({"task": task, "completed": False, "created_at": datetime.now().isoformat()})
                return self._resp(f"✅ 已添加待办：{task}")
            return self._resp("请告诉我需要添加什么待办事项")

        # 查看待办
        if any(kw in t for kw in ["查看待办", "我的待办", "待办列表"]):
            pending = [td for td in self._todos if not td.get("completed")]
            if pending:
                lines = ["📋 待办事项："] + [f"  {i}. {td['task']}" for i, td in enumerate(pending, 1)]
                return self._resp("\n".join(lines))
            return self._resp("🎉 所有待办都已完成！")

        # 完成待办
        if any(kw in t for kw in ["完成待办", "已完成", "搞定"]):
            m = re.search(r'(\d+)', t)
            if m:
                idx = int(m.group(1)) - 1
                pending = [td for td in self._todos if not td.get("completed")]
                if 0 <= idx < len(pending):
                    pending[idx]["completed"] = True
                    return self._resp(f"✅ 已完成：{pending[idx]['task']}")
            return self._resp("请提供待办编号。例如：完成待办 1")

        # 清空对话
        if any(kw in t for kw in ["清空对话", "清空历史", "重置对话"]):
            self._history = []
            return self._resp("✅ 已清空对话历史")

        # 情感回应
        if "开心" in t or "高兴" in t:
            return self._resp("很高兴您心情不错！有什么需要我帮忙的吗？😊")
        if "谢谢" in t or "感谢" in t:
            return self._resp("不客气！很高兴能帮到您")
        if "难过" in t or "伤心" in t:
            return self._resp("很抱歉听到这个消息...希望您能好起来")

        # 默认对话
        prompt = f"你是私人管家，简短友好回复：{t}"
        response = self._call_llm(prompt, task_type="chat")
        self._update_history(t, response or "您好！我是您的私人管家，有什么可以帮您的吗？")
        return self._resp(response or "您好！我是您的私人管家，有什么可以帮您的吗？")

    def _update_history(self, user_input: str, response: str):
        self._history.append({"user": user_input[:200], "assistant": response[:200], "timestamp": datetime.now().isoformat()})
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = ButlerAgentV4("test")
    print(agent.process("我叫王小明")["response"])
