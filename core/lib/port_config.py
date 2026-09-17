"""统一端口配置"""

from core.lib.unified_config import unified_config


def get_port(service_name: str, default: int) -> int:
    return unified_config.get(f"services.{service_name}.port", default)


# 预定义端口
GATEWAY_PORT = 5002
USER_PREFERENCE_PORT = 5445
DRIVER_HTTPS_PORT = 5443
DRIVER_PORT = 5013
LLM_PORT = 5012
