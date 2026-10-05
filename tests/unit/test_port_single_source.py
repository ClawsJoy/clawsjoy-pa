# -*- coding: utf-8 -*-
"""X-12 · 端口／URL 单源闸（该红格 / 该不红格 / 对照的对照）。

判据：真源 = ``config/system/system_unified.yaml`` 的 ``services.gateway.port``；
出口 = ``core/lib/port_config.py``。本测**树无关**（WSL 树与 Windows 树都应过）。

四格：
  该红   —— 出口值必须**跟着真源**（不是某个写死的字面量）
  该不红 —— 显式 ``host`` 参数不得被真源覆盖
  对照   —— 设 ``V9_URL`` ⇒ 必须跟着走（证「取真源」而**不是**「换个常量」）
  陷阱   —— WSL 时代 env（``GATEWAY_PORT`` / ``CLAWSJOY_GATEWAY_PORT``）**不得**被读：
            ``.env`` 一注入就会把 Windows 副本**静默指回 WSL 端口**（错峰失效）
"""
import sys

sys.path.insert(0, ".")

from core.lib import port_config as pc
from core.lib.unified_config import unified_config

SOURCE_KEY = "services.gateway.port"


def test_gateway_port_follows_single_source():
    assert pc.gateway_port() == int(unified_config.get(SOURCE_KEY))


def test_legacy_constant_follows_single_source():
    assert pc.GATEWAY_PORT == int(unified_config.get(SOURCE_KEY))


def test_base_url_shape_matches_single_source():
    assert pc.gateway_base_url() == "http://%s:%d" % (pc.CLIENT_HOST, pc.gateway_port())


def test_base_url_does_not_reuse_bind_host():
    """``services.gateway.host`` 是 0.0.0.0（**绑定**地址），不是可连接的客户端地址。"""
    bind_host = str(unified_config.get("services.gateway.host"))
    if bind_host and bind_host not in ("127.0.0.1", "localhost"):
        assert bind_host not in pc.gateway_base_url()


def test_explicit_host_wins():
    assert pc.gateway_base_url(host="localhost") == "http://localhost:%d" % pc.gateway_port()


def test_v9_url_env_wins(monkeypatch):
    monkeypatch.setenv("V9_URL", "http://127.0.0.1:9999")
    assert pc.gateway_base_url() == "http://127.0.0.1:9999"


def test_wsl_era_env_is_ignored(monkeypatch):
    monkeypatch.setenv("GATEWAY_PORT", "1")
    monkeypatch.setenv("CLAWSJOY_GATEWAY_PORT", "2")
    assert pc.gateway_port() == int(unified_config.get(SOURCE_KEY))
    assert pc.gateway_base_url() == "http://%s:%d" % (pc.CLIENT_HOST, pc.gateway_port())