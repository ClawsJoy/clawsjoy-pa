#!/usr/bin/env python3
"""Prompt工厂 - 系统唯一逻辑"""

class PromptFactory:
    @staticmethod
    def route(user_input: str, context: str = "", capabilities: str = "") -> str:
        return f"""根据用户输入选择合适的Agent。

{context}
{capabilities}

用户输入: {user_input}

输出JSON:
{{"action":"agent名","agents":["agent名"],"extracted":{{"字段":"值"}},"confidence":0.X,"intent_desc":"描述","is_complex":false,"suggest_new_category":""}}

只输出JSON:"""

    @staticmethod
    def polish(system_output: str, user_intent: str = "") -> str:
        return f"""把系统输出翻译成自然语言。

系统输出: {system_output[:1000]}
用户意图: {user_intent}

要求: 像朋友聊天一样自然，信息完整，不要加前缀。
直接输出:"""

prompt_factory = PromptFactory()
