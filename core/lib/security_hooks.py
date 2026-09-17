#!/usr/bin/env python3
"""Security Hooks - Security Hooks 模块

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
from core.lib.unified_config import unified_config

"""统一安全钩子 - 加密、脱敏、验证"""

import base64
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet


class SecurityHooks:
    """统一安全钩子"""

    def __init__(self):
        self.key_file = Path(f"{get_data_root()}/keys/user_master.key")
        self._init_key()

    def _init_key(self):
        """初始化主密钥"""
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(self.key)
        self.cipher = Fernet(self.key)

    # ========== 数据脱敏 ==========
    def redact_sensitive(self, context: Dict) -> Dict:
        """脱敏敏感数据"""
        data = context.get("data", {})

        # 脱敏模式
        patterns = [
            (r"(api[_-]?key|apikey|token|secret)[=:]\s*\S+", r"\1=***"),
            (r"(password|passwd|pwd)[=:]\s*\S+", r"\1=***"),
            (r"(bearer|authorization)[=:]\s*\S+", r"\1=***"),
        ]

        for pattern, replacement in patterns:
            if isinstance(data, dict):
                for key in list(data.keys()):
                    if re.search(r"api|key|token|secret|password", key, re.I):
                        data[key] = "***"
            elif isinstance(data, str):
                data = re.sub(pattern, replacement, data, flags=re.I)

        context["data"] = data
        return context

    # ========== 加密/解密 ==========
    def encrypt_sensitive(self, context: Dict) -> Dict:
        """加密敏感数据"""
        data = context.get("data", {})
        sensitive_fields = context.get(
            "sensitive_fields",
            ["preferences", "habits", "todos", "patterns", "credentials"],
        )

        for field in sensitive_fields:
            if field in data and data[field]:
                try:
                    json_str = json.dumps(data[field], ensure_ascii=False, default=str)
                    encrypted = self.cipher.encrypt(json_str.encode())
                    data[f"{field}_encrypted"] = base64.b64encode(encrypted).decode()
                    # 可选：删除原字段
                    # del data[field]
                except Exception as e:
                    print(f"⚠️ 加密失败 {field}: {e}")

        context["data"] = data
        return context

    def decrypt_sensitive(self, context: Dict) -> Dict:
        """解密敏感数据"""
        data = context.get("data", {})
        encrypted_fields = [k for k in data.keys() if k.endswith("_encrypted")]

        for enc_field in encrypted_fields:
            original_field = enc_field.replace("_encrypted", "")
            try:
                encrypted = base64.b64decode(data[enc_field])
                decrypted = self.cipher.decrypt(encrypted)
                data[original_field] = json.loads(decrypted.decode())
            except Exception as e:
                print(f"⚠️ 解密失败 {enc_field}: {e}")

        context["data"] = data
        return context

    # ========== 数据验证 ==========
    def validate_data(self, context: Dict) -> Dict:
        """验证数据完整性"""
        data = context.get("data", {})
        errors = []

        # 基本验证规则
        if isinstance(data, dict):
            # 检查必要字段
            if "user_id" not in data and "user_id" in context:
                data["user_id"] = context["user_id"]

            # 检查数据大小
            data_size = len(json.dumps(data, default=str))
            if data_size > 10 * 1024 * 1024:  # 10MB
                errors.append("数据过大")

        context["data"] = data
        context["validation_errors"] = errors
        return context

    # ========== 准备/清理 ==========
    def prepare_encryption(self, context: Dict) -> Dict:
        """准备加密（预处理）"""
        context["sensitive_fields"] = ["preferences", "habits", "todos", "patterns"]
        return context

    def cleanup_after_decrypt(self, context: Dict) -> Dict:
        """解密后清理"""
        # 移除临时加密字段
        data = context.get("data", {})
        temp_fields = [k for k in data.keys() if k.startswith("_temp_")]
        for field in temp_fields:
            del data[field]
        context["data"] = data
        return context

    # 全局实例

    @staticmethod
    def sanitize_input(text: str) -> tuple:
        """输入清洗和验证"""
        if not text or not isinstance(text, str):
            return False, ""

        import re

        # 允许：中文、英文、数字、常用标点
        cleaned = re.sub(
            r"[^\u4e00-\u9fa5a-zA-Z0-9\s\.\,\!\?\-\:\;\"\'\(\)\[\]\{\}]", "", text
        )

        if not cleaned.strip():
            return False, ""

        if len(cleaned) > 5000:
            cleaned = cleaned[:5000]

        return True, cleaned

    @staticmethod
    def check_dangerous_patterns(text: str) -> tuple:
        """检查危险模式

        Args:
            text: 用户输入文本

        Returns:
            (is_safe, error_message) 元组
        """
        if not text or not isinstance(text, str):
            return True, ""

        # 定义危险模式
        dangerous_patterns = [
            (r"(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE)\s+", "SQL注入风险"),
            (r"<script|<iframe|javascript:|onclick=|onload=", "XSS攻击风险"),
            (r"rm\s+-rf|del\s+/|format\s+|shutdown", "系统命令风险"),
            (r"__import__|eval\(|exec\(|compile\(", "代码注入风险"),
            (r"\.\./|\.\.\\|/etc/passwd|C:\\Windows", "路径遍历风险"),
        ]

        import re

        text_lower = text.lower()

        for pattern, error_msg in dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return False, f"检测到危险操作: {error_msg}"

        return True, ""

    @staticmethod
    def check_rate_limit(user_id: str, config: dict = None) -> tuple:
        """检查频率限制

        Args:
            user_id: 用户ID
            config: 配置参数

        Returns:
            (is_allowed, error_message) 元组
        """
        import time
        from collections import defaultdict

        # 简单的内存限流
        if not hasattr(SecurityHooks, "_rate_limit_cache"):
            SecurityHooks._rate_limit_cache = defaultdict(list)

        cache = SecurityHooks._rate_limit_cache
        now = time.time()
        window = 60  # 60秒窗口
        max_requests = config.get("max_requests_per_minute", 30) if config else 30

        # 清理过期记录
        cache[user_id] = [t for t in cache[user_id] if now - t < window]

        # 检查限制
        if len(cache[user_id]) >= max_requests:
            wait_time = int(window - (now - cache[user_id][0]))
            return False, f"请求过于频繁，请等待 {wait_time} 秒后重试"

        # 记录本次请求
        cache[user_id].append(now)

        return True, ""
