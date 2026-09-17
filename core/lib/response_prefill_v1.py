#!/usr/bin/env python3
"""Response Prefill V1 - Response Prefill V1 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""响应预填充 v1.0.0 - 强制模型从指定 token 开始生成"""

from typing import Any, Dict, Optional


class ResponsePrefill:
    """响应预填充 - 稳定模型输出"""

    VERSION = "1.0.0"

    # 预设的预填充模板
    PREFILL_TEMPLATES = {
        "json": "{\n",
        "code": "```\n",
        "answer": "好的，",
        "explain": "基于分析，",
        "summarize": "总结如下：",
        "list": "- ",
    }

    @classmethod
    def get_prefill(cls, output_type: str = "answer") -> str:
        """获取预填充文本"""
        return cls.PREFILL_TEMPLATES.get(output_type, "")

    @classmethod
    def build_prompt(
        cls, user_input: str, output_type: str = "json", context: Optional[str] = None
    ) -> str:
        """构建带预填充的提示词"""
        prefill = cls.get_prefill(output_type)

        prompt = f"""{context or ""}

用户: {user_input}

助手: {prefill}"""
        return prompt

    @classmethod
    def extract_complete_response(cls, raw_response: str, prefill: str) -> str:
        """提取完整响应"""
        if raw_response.startswith(prefill):
            return raw_response
        return prefill + raw_response


# 高级预填充：针对不同模型
class ModelSpecificPrefill:
    """模型特定的预填充策略"""

    # Qwen 系列
    QWEN_PREFILL = "好的，我来"

    # GLM 系列 (需要强制 think 标签)
    GLM_PREFILL = "<think>"

    # 通用
    DEFAULT_PREFILL = ""

    @classmethod
    def for_model(cls, model_name: str) -> str:
        model_lower = model_name.lower()
        if "qwen" in model_lower:
            return cls.QWEN_PREFILL
        elif "glm" in model_lower:
            return cls.GLM_PREFILL
        else:
            return cls.DEFAULT_PREFILL


if __name__ == "__main__":
    print(f"响应预填充 v{ResponsePrefill.VERSION}")

    # 测试
    prompt = ResponsePrefill.build_prompt("生成一张图片", output_type="json")
    print(f"构建的提示词:\n{prompt}")

    print(f"\n模型特定预填充:")
    print(
        f"  Qwen: '{ModelSpecificPrefill.for_model(unified_config.get('llm.default_model', 'qwen2.5:7b'))}'"
    )
    print(f"  GLM:  '{ModelSpecificPrefill.for_model('glm-4.7-flash')}'")
