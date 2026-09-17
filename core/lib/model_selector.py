#!/usr/bin/env python3
"""智能模型选择器 - 根据任务复杂度选择模型"""

import re


class ModelSelector:
    """模型选择器"""

    # 模型配置
    MODELS = {
        "fast": "qwen2.5:1.5b-instruct",   # 简单任务，< 3s
        "medium": "qwen2.5:7b-instruct-q4_0-gpu",             # 中等任务，3-10s
        "large": "qwen2.5:7b-instruct-q4_0-gpu",              # 复杂任务，10-30s
    }

    def select(self, user_input: str, task_type: str = None) -> str:
        """根据输入选择模型"""
        
        # 如果指定了任务类型
        if task_type:
            return self.MODELS.get(task_type, self.MODELS["medium"])
        
        # 自动检测
        input_len = len(user_input)
        has_code = "```" in user_input
        has_complex = any(kw in user_input for kw in ["分析", "审查", "生成", "优化", "重构"])
        has_code_keywords = any(kw in user_input for kw in ["代码", "函数", "算法", "编程"])
        
        # 复杂任务：代码审查、深度分析
        if has_code and has_complex:
            return self.MODELS["large"]
        
        # 代码生成：中等任务
        if has_code_keywords or has_code:
            return self.MODELS["medium"]
        
        # 简单任务：聊天、推荐
        if input_len < 100 and not has_complex:
            return self.MODELS["fast"]
        
        # 默认
        return self.MODELS["medium"]


# 全局实例
model_selector = ModelSelector()
