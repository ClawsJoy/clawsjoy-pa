#!/usr/bin/env python3
"""Llm Guide V4 - Llm Guide V4 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""LLM 稳定指引 v4.0.0 - 确保 LLM 输出稳定"""

import json
import logging
from typing import Any, Dict, Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LLMGuide:
    """LLM 指引器 - 确保输出稳定"""

    VERSION = "4.0.0"

    OUTPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["execute", "compose", "query", "learn"],
            },
            "skills": {"type": "array", "items": {"type": "string"}},
            "params": {"type": "object"},
            "reasoning": {"type": "string"},
        },
        "required": ["action", "reasoning"],
    }

    def get_stable_prompt(self, user_input: str, context: Dict = None) -> str:
        """生成稳定的提示词"""
        context = context or {}

        prompt = f"""You are ClawsJoy, a reliable AI assistant.

## Rules
1. Always respond with valid JSON only
2. No markdown, no explanations outside JSON
3. Follow the schema strictly

## Schema
{json.dumps(self.OUTPUT_SCHEMA, indent=2)}

## Context
{json.dumps(context, indent=2)}

## User Input
{user_input}

## Your Response (JSON only):"""

        return prompt

    def parse_response(self, response: str) -> Optional[Dict]:
        """解析 LLM 响应"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None

    def validate_response(self, response: Dict) -> bool:
        """验证响应格式"""
        required = self.OUTPUT_SCHEMA.get("required", [])
        for field in required:
            if field not in response:
                return False
        return True

    def get_schema(self) -> Dict:
        """获取输出格式 schema"""
        return self.OUTPUT_SCHEMA


llm_guide = LLMGuide()


if __name__ == "__main__":
    print(f"LLM 指引器 v{llm_guide.VERSION}")
    prompt = llm_guide.get_stable_prompt("生成一张香港风景图片")
    print(f"生成的提示词长度: {len(prompt)}")
    print(f"Schema: {list(llm_guide.get_schema()['properties'].keys())}")
