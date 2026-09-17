#!/usr/bin/env python3
"""ChatAgent v7.0 - 只做聊天，不再自己检索上下文"""

from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent
from core.lib.llm_client import llm_client


class ChatAgentV4(BusinessAgent):
    """兜底Agent：使用Cortex传入的上下文，只做聊天"""
    name = "chat_agent_v4"
    description = "智能对话助手"
    version = "7.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"💬 ChatAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        使用Cortex传入的上下文，只做聊天
        context 包含:
            - action: Cortex识别的动作
            - extracted: 提取的字段
            - context: Cortex检索好的上下文 (包含 _retrieved, _short_term, _mid_term, _long_term, 补全)
        """
        if not context:
            context = {}

        # 从 context 获取信息
        action = context.get("action", "chat")
        extracted = context.get("extracted", {})
        ctx_data = context.get("context", {})

        # 构建上下文字符串（使用 Cortex 已经检索好的）
        context_parts = []

        # 系统补全
        if ctx_data.get("补全"):
            import json
            context_parts.append(f"【系统补全】{json.dumps(ctx_data['补全'], ensure_ascii=False)}")

        # 最近对话
        if ctx_data.get("_short_term"):
            context_parts.append(f"【最近对话】{ctx_data['_short_term'][:200]}")

        # 存储信息
        if ctx_data.get("_mid_term"):
            context_parts.append(f"【存储信息】{ctx_data['_mid_term'][:200]}")

        # 语义检索
        if ctx_data.get("_long_term"):
            context_parts.append(f"【语义检索】{ctx_data['_long_term'][:200]}")

        # 完整的检索结果
        if ctx_data.get("_retrieved"):
            context_parts.append(ctx_data["_retrieved"])

        context_text = "\n".join(context_parts) if context_parts else ""

        # 构建LLM prompt
        prompt = f"""你是ClawsJoy本地AI矩阵系统。有23个Agent。能力:写代码/分析数据/创作/翻译/记忆/管理文件。你不是通用语言模型。

{context_text}

用户: {user_input}
回复:"""

        try:
            resp = llm_client.generate(
                prompt,
                model="qwen2.5:7b-instruct-q4_0-gpu",
                max_tokens=200,
                temperature=0.3,
                task_type="chat",
                timeout=10
            )
            if resp and len(resp.strip()) > 2:
                return self._resp(resp.strip())
        except Exception as e:
            pass

        # 降级回复
        if action == "greeting":
            return self._resp("你好！我是ClawsJoy，有什么可以帮你的吗？")
        elif action == "recall":
            return self._resp("让我查一下...")
        else:
            return self._resp("你好！我是ClawsJoy，有什么可以帮你的吗？")

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}
