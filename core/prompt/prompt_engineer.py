#!/usr/bin/env python3
"""Prompt Engineer - Prompt Engineer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


class PromptEngineer:
    """提示词工程师"""

    @staticmethod
    def reasoning_prompt(question: str) -> str:
        """推理类提示词"""
        return f"""请一步步推理，最后给出答案。

问题: {question}

请按以下格式回答：
1. 分析...
2. 推理...
3. 答案: ..."""

    @staticmethod
    def coding_prompt(task: str, language: str = "python") -> str:
        """代码生成提示词"""
        return f"""请生成 {language} 代码完成以下任务：
{task}

要求：
- 只输出代码
- 添加必要注释
- 代码要可直接运行"""

    @staticmethod
    def knowledge_prompt(question: str) -> str:
        """知识问答提示词"""
        return f"""请回答以下问题，如果不确定请说"我不确定"。

问题: {question}

回答:"""

    @staticmethod
    def creative_prompt(task: str) -> str:
        """创意类提示词"""
        return f"""请发挥创意完成以下任务：
{task}

要求：有创意、有趣、实用"""


prompt_engineer = PromptEngineer()
