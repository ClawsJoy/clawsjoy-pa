# core/lib/json_serializer.py
#!/usr/bin/env python3
"""LLM 友好的序列化器"""

import json
from typing import Dict, Any
from core.lib.json_standard import StandardJSON


class LLMFriendlySerializer:
    """
    LLM 友好的序列化器
    
    特点:
    1. 简单任务输出纯扁平 JSON
    2. 复杂任务才输出嵌套
    3. 支持流式输出
    """
    
    def serialize(self, obj: StandardJSON) -> str:
        """序列化为 JSON 字符串"""
        
        # 简单任务：直接输出核心字段
        if obj.is_simple():
            return self._serialize_simple(obj)
        
        # 复杂任务：输出完整结构
        return self._serialize_complex(obj)
    
    def _serialize_simple(self, obj: StandardJSON) -> str:
        """简单任务 - 最少字段，纯扁平"""
        core = {
            "version": obj.version,
            "action": obj.action,
            "target": obj.target,
            "keywords": obj.keywords[:3],  # 只保留前3个
            "raw_input": obj.raw_input[:100]  # 截断长文本
        }
        
        # 只有非空才加
        if obj.user_id:
            core["user_id"] = obj.user_id
        if obj.params:
            core["params"] = obj.params
        
        return json.dumps(core, ensure_ascii=False)
    
    def _serialize_complex(self, obj: StandardJSON) -> str:
        """复杂任务 - 完整结构"""
        return json.dumps(obj.to_dict(), ensure_ascii=False)
    
    def stream_serialize(self, obj: StandardJSON):
        """流式序列化 - 用于实时输出"""
        
        # 先输出核心字段
        yield '{"action": "' + obj.action + '", '
        yield '"target": "' + obj.target + '", '
        
        if obj.keywords:
            yield '"keywords": ' + json.dumps(obj.keywords) + ', '
        
        # 复杂部分最后输出
        if obj.workflow:
            yield '"workflow": ' + json.dumps(obj.workflow.to_dict()) + ', '
        
        if obj.condition:
            yield '"condition": ' + json.dumps(obj.condition.to_dict()) + ', '
        
        # 结束
        yield '"status": "pending"}'
    
    def compress_for_llm(self, obj: StandardJSON) -> str:
        """压缩格式 - 最小化 Token"""
        
        # 单字母映射
        mapping = {
            "action": "a",
            "target": "t", 
            "keywords": "k",
            "raw_input": "r",
            "user_id": "u"
        }
        
        compressed = {}
        for key, short in mapping.items():
            value = getattr(obj, key, None)
            if value:
                compressed[short] = value
        
        return json.dumps(compressed, ensure_ascii=False, separators=(',', ':'))
