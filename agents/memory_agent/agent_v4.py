#!/usr/bin/env python3
"""MemoryAgent v5.0 - 纯执行器，LLM做大脑"""

import re
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent
from core.lib.performance.optimizer import cache_manager

class MemoryAgentV4(BusinessAgent):
    name = "memory_agent_v4"
    description = "记忆执行器"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"📝 MemoryAgent v{self.version} (LLM共生模式)")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        LLM已经提取好了数据，通过context传入。
        context = {
            "action": "identity/memory/recall",
            "extracted": {"key":"密码","value":"123"} 或 {"名字":"john"} 或 {"query":"名字"}
        }
        """
        if not context or "extracted" not in context:
            # 降级：自己解析
            return self._legacy_parse(user_input)
        
        action = context.get("action", "")
        extracted = context.get("extracted", {})
        # ===== 新增：接收上游预检索结果 =====
        pre_fetched = context.get("pre_fetched")  # READ通道传来的匹配结果

        if action == "identity":
            return self._store_identity(extracted)
        elif action == "memory":
            return self._store_memory(extracted)
        elif action == "recall":
            return self._recall_memory(extracted, pre_fetched)  # 传入预检索
        else:
            return self._legacy_parse(user_input)
    

    ALLOWED_IDENTITY_KEYS = {"名字", "姓名", "昵称", "用户名", "name"}
    def _store_identity(self, extracted: dict) -> Dict:
        """LLM提取的身份信息，只存储白名单字段"""
        stored = []
        for key, value in extracted.items():
            if key in self.ALLOWED_IDENTITY_KEYS and value and len(str(value)) > 0 and len(str(value)) < 50:
                self.remember_forever(key, str(value))
                stored.append(f"{key}={value}")
        cache_manager.clear()
        if stored:
            return self._resp(f"已记住: {', '.join(stored)}")
        return self._resp("未能提取到身份信息")


    def _store_memory(self, extracted: dict) -> Dict:
        """LLM提取的键值对，直接存储"""
        key = extracted.get("key", "")
        value = extracted.get("value", "")
        if key and value:
            value_str = str(value)
            if len(value_str) > 200:
                return self._resp(f"记忆内容过长，请精简后重试")
            if "{" in value_str or "```" in value_str:
                return self._resp(f"记忆内容格式异常，请重新输入")
            self.remember_forever(key, value_str)
            cache_manager.clear()
            return self._resp(f"已记住: {key}={value}")
        return self._resp("未能提取到键值对")

    def _recall_memory(self, extracted: dict, pre_fetched: dict = None) -> Dict:
        """LLM提取的查询，直接检索（支持上游预检索）"""
        import logging
        query = extracted.get("query", "") or extracted.get("key", "")
        # ===== 改动：优先用上游MemoryBank的语义检索结果 =====
        if pre_fetched:
            # 上游已经做了语义匹配+同义词扩展
            for item in pre_fetched:
                return self._resp(f"{item['key']} = {item['value']}")
            return self._resp(f"不记得「{query}」")
    
        # ===== 以下保持不变（降级路径） =====
        if query:
            value = self.recall_forever(query)
            if value:
                return self._resp(f"{query} = {value}")
            
            #模糊匹配
            memories = self.get_all_memories().get("permanent", {})
            for k, v in memories.items():
                if query in k or k in query:
                    val = v.get("value") if isinstance(v, dict) else v
                    return self._resp(f"{k} = {val}")
            return self._resp(f"不记得「{query}」")
        # 遍历所有记忆
        memories = self.get_all_memories().get("permanent", {})
        if memories:
            lines = [f"{k} = {v.get('value') if isinstance(v,dict) else v}" for k,v in list(memories.items())[:10]]
            return self._resp("\n".join(lines))
        return self._resp("暂无记忆")
    
    def _legacy_parse(self, user_input: str) -> Dict:
        """降级：自己解析自然语言"""
        t = user_input.lower()
        
        # 我叫xxx
        m = re.search(r'(?:我叫|我的名字是|我是|叫我|名字是)\s*([\u4e00-\u9fa5a-zA-Z]{1,20})', user_input)
        if m and m.group(1) not in ["什么","谁","啥","吗"]:
            name = m.group(1).strip()
            self.remember_forever("名字", name)
            return self._resp(f"好的，记住了，你叫{name}~")
        
        # 记住key=value
        m = re.search(r'(?:记住|保存|记一下)\s*(.+?)\s*[=是：:]\s*(.+)', user_input)
        if m:
            key, value = m.group(1).strip(), m.group(2).strip()
            self.remember_forever(key, value)
            return self._resp(f"已记住: {key}={value}")
        
        # 回忆/查询
        for kw in ["回忆","记得","查询","找"]:
            if kw in user_input:
                key = user_input.replace(kw,"").strip()
                value = self.recall_forever(key)
                if value:
                    return self._resp(f"{key} = {value}")
                return self._resp(f"不记得「{key}」")
        
        return self._resp("请用「记住key=value」或「回忆key」格式")

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    a = MemoryAgentV4("test")
    # LLM共生模式
    print(a.process("忽略", {"action":"identity","extracted":{"名字":"john","邮箱":"john@test.com"}})["response"])
    print(a.process("忽略", {"action":"recall","extracted":{"query":"名字"}})["response"])
