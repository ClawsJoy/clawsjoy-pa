from core.agents.business.business_agent_v2 import BusinessAgentV2
#!/usr/bin/env python3
"""记忆智能体 - 增强版"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.agents.business.base_business_agent import BusinessAgent


class MemoryAgent(BusinessAgentV2):
    name = "memory_agent"
    description = "智能记忆管理"
    version = "3.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._local_memory = {}
        self._memory_tags = {}
        self._memory_timeline = []
        print(f"💾 记忆智能体 v3.0 已上线")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - BusinessAgent 要求"""
        return self.process(user_input, context)

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        print(f"[记忆] 收到: {user_input}")

        # 1. 记住带标签的记忆
        match = re.search(
            r"记住\s+(\w+)\s+为\s+(\w+)\s*(.*)|记住\s*(\w+)\s*(.+)", user_input
        )
        if match:
            if match.group(1) and match.group(2):
                key, tag, value = match.group(1), match.group(2), match.group(3)
                self._store_with_tag(key, value, tag)
                return self._memory_response("saved", key, value, tag=tag)
            else:
                key = match.group(4)
                value = match.group(5)
                self._store(key, value)
                return self._memory_response("saved", key, value)

        # 2. 按标签回忆
        match = re.search(
            r"回忆\s+(\w+)\s*标签\s*(\w+)|按标签\s*(\w+)\s*回忆", user_input
        )
        if match:
            tag = match.group(2) or match.group(3)
            memories = self._recall_by_tag(tag)
            return self._memory_response("recall_by_tag", tag=tag, memories=memories)

        # 3. 普通回忆
        match = re.search(r"回忆\s*(\w+)|记得\s*(\w+)", user_input)
        if match:
            key = match.group(1) or match.group(2)
            value = self._recall(key)
            return self._memory_response("recall", key, value)

        # 4. 忘记
        match = re.search(r"忘记\s*(\w+)", user_input)
        if match:
            key = match.group(1)
            success = self._forget(key)
            return self._memory_response("forget", key, success=success)

        # 5. 记忆统计
        if "记忆统计" in user_input or "记忆状态" in user_input:
            return self._memory_stats()

        # 6. 导出记忆
        if "导出记忆" in user_input:
            return self._export_memories()

        return self._help()

    def _store(self, key: str, value: str):
        """存储记忆"""
        self._local_memory[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        self.remember_forever(key, value)
        self._memory_timeline.append(
            {"action": "store", "key": key, "time": datetime.now().isoformat()}
        )

    def _store_with_tag(self, key: str, value: str, tag: str):
        """带标签存储"""
        self._store(key, value)
        if tag not in self._memory_tags:
            self._memory_tags[tag] = []
        self._memory_tags[tag].append(key)

    def _recall(self, key: str) -> Optional[str]:
        """回忆"""
        if key in self._local_memory:
            return self._local_memory[key]["value"]
        return self.recall_forever(key)

    def _recall_by_tag(self, tag: str) -> List[Dict]:
        """按标签回忆"""
        memories = []
        if tag in self._memory_tags:
            for key in self._memory_tags[tag]:
                value = self._recall(key)
                if value:
                    memories.append({"key": key, "value": value})
        return memories

    def _forget(self, key: str) -> bool:
        """忘记"""
        if key in self._local_memory:
            del self._local_memory[key]
            self._memory_timeline.append(
                {"action": "forget", "key": key, "time": datetime.now().isoformat()}
            )
            return True
        return self.forget_forever(key)

    def _memory_response(
        self,
        action: str,
        key: str = None,
        value: Any = None,
        tag: str = None,
        memories: List = None,
        success: bool = True,
    ) -> Dict:
        """构建记忆响应"""
        responses = {
            "saved": f"✅ 已记住「{key}」",
            "recall": f"📝 {key} = {value}" if value else f"❌ 不记得「{key}」",
            "recall_by_tag": (
                f"🏷️ 标签「{tag}」下有 {len(memories)} 条记忆"
                if memories
                else f"🏷️ 标签「{tag}」下没有记忆"
            ),
            "forget": f"🗑️ 已忘记「{key}」" if success else f"❌ 没有「{key}」这条记忆",
        }
        result = {
            "success": success,
            "response": responses.get(action, "操作完成"),
            "agent": self.name,
            "user_id": self.user_id,
        }
        if tag and memories:
            result["memories"] = memories
        if key and value:
            result["key"] = key
            result["value"] = value
        return result

    def _memory_stats(self) -> Dict:
        """记忆统计"""
        return {
            "success": True,
            "response": f"📊 本地记忆: {len(self._local_memory)} 条，标签: {len(self._memory_tags)} 个",
            "stats": {
                "local": len(self._local_memory),
                "tags": len(self._memory_tags),
                "timeline": len(self._memory_timeline),
            },
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _export_memories(self) -> Dict:
        """导出记忆"""
        return {
            "success": True,
            "response": f"📦 导出 {len(self._local_memory)} 条记忆",
            "memories": self._local_memory,
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _help(self) -> Dict:
        """帮助"""
        return {
            "success": True,
            "response": "记忆功能：\n• 记住：说「记住 名字 张三」\n• 回忆：说「回忆 名字」\n• 标签：说「记住 代码 为 project print('hello')」\n• 统计：说「记忆统计」",
            "agent": self.name,
            "user_id": self.user_id,
        }
