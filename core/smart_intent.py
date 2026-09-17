#!/usr/bin/env python3
"""LLM 驱动的意图识别 - 无硬编码"""

import json
import re
import requests
from typing import Dict

class SmartIntent:
    """智能意图识别"""
    
    def __init__(self):
        self.llm_url = "http://localhost:5012/chat"
    
    def detect(self, message: str) -> Dict:
        """使用 LLM 识别意图"""
        prompt = f"""分析用户意图，返回 JSON 格式。

用户消息: {message}

请判断属于以下哪类：
- translate: 翻译
- calculate: 数学计算
- code: 代码相关
- long_task: 多步骤任务
- chat: 普通对话

只返回 JSON: {{"intent": "类型", "confidence": 0.0-1.0, "reason": "原因"}}"""
        
        try:
            resp = requests.post(self.llm_url, json={"message": prompt}, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                response = result.get("response", "")
                # 提取 JSON
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    return json.loads(match.group())
        except Exception as e:
            pass
        
        return {"intent": "chat", "confidence": 0.5, "reason": "fallback"}

smart_intent = SmartIntent()
