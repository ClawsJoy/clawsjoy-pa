#!/usr/bin/env python3
"""Clean Output - Clean Output 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""干净输出训练器 - 禁止装饰符号"""

import json
from typing import Dict, List

import requests


class CleanOutputTrainer:
    """训练 LLM 输出干净格式"""

    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = unified_config.get_llm_config().get(
            "fast_model",
            unified_config.get_llm_config().get(
                "fast_model",
                unified_config.get(
                    "llm.fast_model", config_helper.get_llm_model(fast=True)
                ),
            ),
        )

    def clean_response(self, text: str) -> str:
        """后处理：清理残留的装饰符号"""
        import re

        # 移除各种装饰符号
        text = re.sub(r"[│─┌┐└┘├┤┬┴┼]", "", text)
        text = re.sub(r"[#*\-_]{3,}", "", text)
        text = re.sub(r"[%￥$€£]", "", text)
        text = re.sub(r"\|\s*\|", "|", text)
        # 清理多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def generate_agent_list(self) -> str:
        """生成干净的 Agent 列表"""
        prompt = """请列出 ClawsJoy 系统的所有 Agent，每个 Agent 一行，格式如下：

Agent名称：职责描述

不需要任何装饰符号（不要用 #、*、-、|、% 等），不要表格，只要纯文本。

Agent 包括：orchestrator, code_agent, video_agent, youtube_agent, security_agent, memory_manager, decision_agent, chat_agent, personal_butler, analysis_agent

输出示例：
决策Agent：用户总管，负责任务调度和决策
聊天Agent：负责话术生成和用户沟通

现在请输出："""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 500},
                },
                timeout=unified_config.get("timeouts.default", 30),
            )
            if resp.status_code == 200:
                raw = resp.json().get("response", "")
                return self.clean_response(raw)
        except Exception as e:
            print(f"生成失败: {e}")

        # 默认输出
        return """决策Agent：用户总管，负责任务调度和决策
聊天Agent：负责话术生成和用户沟通
执行Agent：负责技能执行
采集Agent：负责参数收集
安全Agent：负责安全检查和审计
分析Agent：负责数据分析和优化建议
管家Agent：用户的数字分身，1对1专属服务
记忆Agent：负责记忆存储和检索
编排Agent：负责任务编排和协调
代码Agent：负责代码生成和审查"""

    def generate_architecture(self) -> str:
        """生成干净的架构描述"""
        prompt = """请用纯文本描述 ClawsJoy 系统架构，每层一行，不要有任何装饰符号。

格式：
层名称：描述内容

不要用表格、不要用 #、*、-、|、% 等符号。

输出："""

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
                raw = resp.json().get("response", "")
                return self.clean_response(raw)
        except Exception as e:
            pass

        return """用户层：Web/API/移动端入口，接收用户请求
安全层：HTTPS加密、JWT认证、数据脱敏
Agent层：10个专业Agent协同工作
技能层：20+原子技能可调用
记忆层：L0-L4渐进式记忆架构
基础设施层：Ollama LLM + ComfyUI图像生成"""


if __name__ == "__main__":
    trainer = CleanOutputTrainer()

    print("=" * 60)
    print("Agent 列表（干净格式）")
    print("=" * 60)
    agents = trainer.generate_agent_list()
    print(agents)

    print("\n" + "=" * 60)
    print("架构描述（干净格式）")
    print("=" * 60)
    arch = trainer.generate_architecture()
    print(arch)
