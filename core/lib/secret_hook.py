#!/usr/bin/env python3
"""Secret Hook - Secret Hook 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""密钥钩子 - 管理密钥和敏感信息"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from core.lib.unified_config import unified_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SecretHook:
    VERSION = "1.0.0"

    def __init__(self):
        self._load_config()
        self._load_env_vars()

    def _load_config(self):
        config_file = Path("config/driver/secrets.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("secret_hook", {})
        else:
            self.config = {}

        self.sensitive_patterns = self.config.get("sensitive_patterns", [])
        self.log_redaction = self.config.get("log_redaction", {})

    def _load_env_vars(self):
        self.env = {}
        for var in self.config.get("env_vars", []):
            self.env[var] = os.environ.get(var, "")

    def redact_sensitive(self, text: str) -> str:
        if not self.log_redaction.get("enabled", True):
            return text

        result = text
        for pattern_config in self.log_redaction.get("patterns", []):
            pattern = pattern_config.get("pattern", "")
            replace = pattern_config.get("replace", "***")
            if pattern:
                result = re.sub(pattern, replace, result, flags=re.IGNORECASE)

        for pattern in self.sensitive_patterns:
            result = re.sub(
                f"({pattern})[=:]\\S+", r"\1=***", result, flags=re.IGNORECASE
            )

        return result

    def check_message(self, message: Dict) -> Tuple[bool, Optional[Dict]]:
        message_str = str(message)
        redacted = self.redact_sensitive(message_str)
        if redacted != message_str:
            logger.info("消息已脱敏处理")
            return True, {"redacted": True}
        return True, None

    def get_status(self) -> Dict:
        return {
            "version": self.VERSION,
            "redaction_enabled": self.log_redaction.get("enabled", True),
        }


secret_hook = SecretHook()
