# core/lib/input_validator.py
"""输入验证模块"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class ValidationResult:
    """验证结果"""

    valid: bool
    errors: List[str] = field(default_factory=list)
    sanitized_value: Any = None


class InputValidator:
    """输入验证器"""

    # 安全配置
    MAX_MESSAGE_LENGTH = 10000
    MAX_PROMPT_LENGTH = 5000
    MAX_CODE_LENGTH = 50000
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB

    # 危险模式
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/?",  # 删除命令
        r"\|.*sh\b",  # 管道执行shell
        r"`.*`",  # 反引号执行
        r"\$\(.*\)",  # 美元符号执行
        r"eval\s*\(",  # eval函数
        r"exec\s*\(",  # exec函数
        r"__import__\s*\(",  # 动态导入
        r"os\.system\s*\(",  # 系统调用
        r"subprocess\.",  # 子进程调用
        r"<script.*?>.*?</script>",  # XSS脚本
        r"javascript:",  # JavaScript协议
    ]

    # 允许的语言
    ALLOWED_LANGUAGES = ["python", "javascript", "java", "go", "rust", "cpp", "c"]

    @classmethod
    def validate_message(cls, message: str) -> ValidationResult:
        """验证用户消息"""
        errors = []

        # 空消息检查
        if not message or not message.strip():
            errors.append("消息不能为空")
            return ValidationResult(False, errors, "")

        # 长度检查
        if len(message) > cls.MAX_MESSAGE_LENGTH:
            errors.append(f"消息过长，最大 {cls.MAX_MESSAGE_LENGTH} 字符")
            message = message[: cls.MAX_MESSAGE_LENGTH]

        # 危险内容检查
        sanitized = cls._sanitize_dangerous_content(message)
        if sanitized != message:
            errors.append("检测到潜在危险内容，已自动过滤")
            message = sanitized

        return ValidationResult(len(errors) == 0, errors, message)

    @classmethod
    def validate_code_request(
        cls, prompt: str, language: str = None
    ) -> ValidationResult:
        """验证代码生成请求"""
        errors = []

        # 语言验证
        if language and language not in cls.ALLOWED_LANGUAGES:
            errors.append(f"不支持的语言: {language}，支持: {cls.ALLOWED_LANGUAGES}")
            language = "python"  # 默认使用Python

        # 提示词验证
        msg_result = cls.validate_message(prompt)
        if not msg_result.valid:
            errors.extend(msg_result.errors)
            prompt = msg_result.sanitized_value

        # 代码特定安全检查
        dangerous_keywords = ["hack", "crack", "exploit", "malware", "virus"]
        prompt_lower = prompt.lower()
        for keyword in dangerous_keywords:
            if keyword in prompt_lower:
                errors.append(f"检测到敏感关键词: {keyword}")
                prompt = prompt.replace(keyword, "[FILTERED]")

        return ValidationResult(
            len(errors) == 0, errors, {"prompt": prompt, "language": language}
        )

    @classmethod
    def validate_image_prompt(cls, prompt: str) -> ValidationResult:
        """验证图像生成提示词"""
        errors = []

        # 空提示词检查
        if not prompt or not prompt.strip():
            errors.append("图像描述不能为空")
            prompt = "美丽的风景"  # 默认提示词

        # 长度检查
        if len(prompt) > cls.MAX_PROMPT_LENGTH:
            errors.append(f"提示词过长，最大 {cls.MAX_PROMPT_LENGTH} 字符")
            prompt = prompt[: cls.MAX_PROMPT_LENGTH]

        # 过滤不当内容（简化版）
        inappropriate = ["nudity", "porn", "gore", "violence"]
        prompt_lower = prompt.lower()
        for word in inappropriate:
            if word in prompt_lower:
                errors.append(f"检测到不当内容: {word}")
                prompt = prompt.replace(word, "[FILTERED]")

        return ValidationResult(len(errors) == 0, errors, prompt)

    @classmethod
    def _sanitize_dangerous_content(cls, text: str) -> str:
        """清理危险内容"""
        sanitized = text
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
        return sanitized


# 全局验证器实例
input_validator = InputValidator()
