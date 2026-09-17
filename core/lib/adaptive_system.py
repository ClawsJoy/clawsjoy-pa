#!/usr/bin/env python3
"""Adaptive System - Adaptive System 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""自适应系统 - 配置驱动 + LLM 动态理解"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml


class AdaptiveSystem:
    """自适应系统 - 不硬编码任何业务逻辑"""

    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = unified_config.get_llm_config().get(
            "fast_model",
            unified_config.get_llm_config().get(
                "fast_model",
                unified_config.get("llm.fast_model", get_llm_model(fast=True)),
            ),
        )
        self.load_configs()

    def load_configs(self):
        """加载所有配置"""
        self.configs = {}
        config_dir = Path("PROJECT_ROOT/config/driver")

        for yaml_file in config_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                self.configs[yaml_file.stem] = unified_config.get("adaptive_system", {})

        # 加载 Agent 配置
        agents_file = Path("PROJECT_ROOT/config/agents.yaml")
        if agents_file.exists():
            with open(agents_file, "r", encoding="utf-8") as f:
                self.configs["agents"] = unified_config.get("adaptive_system", {})

        print(f"✅ 已加载 {len(self.configs)} 个配置模块")

    def get_config(self, key: str, default=None):
        """获取配置值"""
        parts = key.split(".")
        value = self.configs
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default
        return value

    def understand_user(self, user_input: str) -> Dict:
        """让 LLM 理解用户意图（不硬编码规则）"""
        # 获取可用能力描述
        agents_desc = self.get_config("agents.agents", {})
        skills_desc = self.get_config("skills", {})

        prompt = f"""你是一个智能助手，需要理解用户意图。

可用能力：
- Agent: {list(agents_desc.keys())[:5]}
- 技能: 动态发现

用户说："{user_input}"

请分析并返回 JSON：
{{
  "intent": "用户想做什么（一句话）",
  "type": "query|generate|action|unknown",
  "target": "目标对象（Agent名/技能名/未知）",
  "params": {{"key": "提取的参数"}},
  "confidence": 0.0-1.0
}}

只返回 JSON。"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 300},
                },
                timeout=unified_config.get("timeouts.default", 30),
            )
            if resp.status_code == 200:
                response = resp.json().get("response", "")
                import re

                match = re.search(r"\{[^{}]*\}", response)
                if match:
                    return json.loads(match.group())
        except Exception as e:
            print(f"理解失败: {e}")

        return {"intent": user_input, "type": "unknown", "confidence": 0.3}

    def execute(self, user_input: str) -> Dict:
        """执行用户请求（动态路由）"""

        # 1. LLM 理解用户意图
        understanding = self.understand_user(user_input)

        # 2. 根据理解动态路由
        intent_type = understanding.get("type", "unknown")
        target = understanding.get("target", "")

        # 3. 查找匹配的能力
        if intent_type == "generate":
            # 调用生成类技能
            return self._call_generator(user_input, understanding)
        elif intent_type == "query":
            # 调用查询类能力
            return self._call_query(user_input, understanding)
        else:
            # 默认响应
            return {
                "success": True,
                "response": f"收到：{user_input}\n理解：{understanding.get('intent', '')}",
                "understanding": understanding,
            }

    def _call_generator(self, user_input: str, understanding: Dict) -> Dict:
        """动态调用生成器"""
        # 这里可以根据理解动态选择生成方式
        from core.lib.education.retrieval_generator import RetrievalGenerator

        rg = RetrievalGenerator()
        svg = rg.generate_svg_content()

        filename = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
        file_path = Path("PROJECT_ROOT/output") / filename
        file_path.write_text(svg, encoding="utf-8")

        return {
            "success": True,
            "file_path": str(file_path),
            "message": f"已生成 {filename}",
            "understanding": understanding,
        }

    def _call_query(self, user_input: str, understanding: Dict) -> Dict:
        """动态查询"""
        target = understanding.get("target", "").lower()

        if "agent" in target or "agent" in user_input.lower():
            agents = self.get_config("agents.agents", {})
            response = "\n".join(
                [f"{k}: {v.get('name', k)}" for k, v in agents.items()]
            )
            return {
                "success": True,
                "response": response,
                "understanding": understanding,
            }

        return {
            "success": True,
            "response": "请提供更具体的信息",
            "understanding": understanding,
        }


if __name__ == "__main__":
    system = AdaptiveSystem()

    print("=" * 60)
    print("自适应系统测试")
    print("=" * 60)

    test_inputs = [
        "ClawsJoy 有哪些 Agent？",
        "生成一张系统架构图",
        "我要做一张发展蓝图",
    ]

    for inp in test_inputs:
        print(f"\n用户: {inp}")
        result = system.execute(inp)
        print(f"结果: {result.get('response', result.get('message', ''))[:100]}")
        print(f"理解: {result.get('understanding', {})}")
