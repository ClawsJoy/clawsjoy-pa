"""统一端口配置 —— 端口／URL 的**唯一出口**（X-12）。

真源：``config/system/system_unified.yaml`` 的 ``services.gateway.port``
（Windows 副本 = 5102；Windows 侧 5002 不可绑，实测 ``WinError 10013``。
WSL 侧 = 5002；两树**错峰**）。调用点**不得复述**数值，一律经
``gateway_port()`` / ``gateway_base_url()`` 取。

三条口径（DS 2026-09-20 裁 · 标"DS 代理拍板·待追认"）
----------------------------------------------------
1. **绑定地址 != 连接地址**：``services.gateway.host``（0.0.0.0）只作**绑定**，
   不得作连接目标 ⇒ 出口用 ``CLIENT_HOST``。
2. **本模块有意不读** ``GATEWAY_PORT`` / ``CLAWSJOY_GATEWAY_PORT`` —— 它们是
   WSL 时代的真源，**注入无效**。⇒ 后人**不得**"补上 env 支持"：那是**反向改**
   （一注入就把本副本静默指回 WSL 端口 ⇒ 错峰失效）。
3. **未配 ⇒ 拒启（fail-loud）**：端口未配置时**不回落字面量**，直接抛
   ``PortUnconfigured``。回落常量 = 静默错（有人改了常量、没人知道 —— L-14/L-61 族）。
"""

import os

from core.lib.unified_config import unified_config

SOURCE_KEY = "services.gateway.port"

# 客户端默认主机 —— 见口径 1（**有意不复用** services.gateway.host）
CLIENT_HOST = "127.0.0.1"

# 非网关的预定义端口（与 X-12 无关，原样保留）
USER_PREFERENCE_PORT = 5445
DRIVER_HTTPS_PORT = 5443
DRIVER_PORT = 5013
LLM_PORT = 5012


class PortUnconfigured(RuntimeError):
    """端口未配置 ⇒ 拒启（fail-loud，**不回落字面量**）。"""


def get_port(service_name: str, default: int = None) -> int:
    value = unified_config.get("services.%s.port" % service_name)
    if value is None or value == "":
        if default is None:
            raise PortUnconfigured("services.%s.port 未配置 ⇒ 拒启（不回落字面量）" % service_name)
        return int(default)
    return int(value)


def gateway_port() -> int:
    """网关端口 = 真源 ``services.gateway.port``（未配 ⇒ 拒启）。"""
    return get_port("gateway")


def gateway_base_url(host: str = None) -> str:
    """网关基址（无尾斜杠）。优先级：env ``V9_URL`` > 真源端口 + ``CLIENT_HOST``。"""
    env = os.environ.get("V9_URL")
    if env:
        return env.rstrip("/")
    return "http://%s:%d" % (host or CLIENT_HOST, gateway_port())


def __getattr__(name):
    """``GATEWAY_PORT``（兼容旧名）—— **惰性**求值（PEP 562）。

    为什么惰性：真源未配时要**在用到时**拒启（fail-loud），而不是 import 时就炸；
    同时不给"预置一个常量值"留位置 —— 那个常量正是本模块要消灭的形状。
    """
    if name == "GATEWAY_PORT":
        return gateway_port()
    raise AttributeError("module %r has no attribute %r" % (__name__, name))