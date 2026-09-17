#!/usr/bin/env python3
"""模型路由器 - 根据任务选最优模型"""

class ModelRouter:
    """模型路由 - 简单任务用小模型，复杂任务用大模型"""
    
    # 可用模型配置
    MODELS = {
        "fast": "qwen2:1.5b-instruct",    # 追问、闲聊、简单翻译
        "balanced": "qwen2.5:7b-instruct-q4_0-gpu",          # 日常使用
        "powerful": "qwen2.5:7b-instruct-q4_0-gpu",          # 复杂推理、代码生成
        "ultra": "qwen2.5:7b-instruct-q4_0-gpu",            # 需要大模型时
    }
    
    @classmethod
    def route(cls, action: str, task_type: str = "default") -> str:
        """根据action选择合适的模型"""
        # 轻量任务：用小模型
        if action in ("greeting", "clarify"):
            return cls.MODELS["fast"]
        
        # 推理任务：用大模型
        if action in ("code", "analyze", "brainstorm", "write"):
            return cls.MODELS["powerful"]
        
        # 翻译、计算：中等模型
        if action in ("translate", "calculate"):
            return cls.MODELS["balanced"]
        
        # 默认
        return cls.MODELS["balanced"]
    
    @classmethod
    def list_models(cls) -> dict:
        return cls.MODELS


model_router = ModelRouter()
