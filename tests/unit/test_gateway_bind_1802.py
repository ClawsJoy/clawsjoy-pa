# -*- coding: utf-8 -*-
u"""pm_1802 §三 之齿：网关监听之**绑形**默认唯本机（`127.0.0.1`）＋ 显式开关 `CJ_PA_BIND`。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_gateway_bind_1802.py -q

判据：
  ⒜ **默认**（⛔ env）⇒ `127.0.0.1`（旧病：硬编 `0.0.0.0` ⇒ 局网可达）。
  ⒝ **显式开关**：`CJ_PA_BIND` 非空 ⇒ **逐字**取之（有意跨机者自担 · 承 pm_1802 §三）。
  ⒞ **空 ／ 空白** ⇒ 回落默认（⛔ 以空串当「全绑」）。
  ⒟ **一处定形**：`_serve_http` 之 `host` 唯经 `_bind_host()`（源内 ⛔ `host="0.0.0.0"`）。
  ⒠ **真绑之证**：以 `_serve_http` 起一临时 app（自有之口 · ⛔ 撞 `5102`）⇒ 本机可连。
  ⒡ **⛔ 有意不读 `services.gateway.host`**：该键属**连接**方（`core/lib/port_config.py:10`
     逐字立口径「绑定地址 != 连接地址」）⇒ 源内 ⛔ 引之（改其值 ＝ 静默改连接目标）。
"""
from __future__ import annotations

import io
import socket
import sys
import threading
import time
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.gateway import boot as B  # noqa: E402


def test_bind_default_is_loopback(monkeypatch):
    u"""⒜：⛔ env ⇒ 默认唯本机。"""
    monkeypatch.delenv("CJ_PA_BIND", raising=False)
    assert B._bind_host() == "127.0.0.1"


def test_bind_env_override_is_verbatim(monkeypatch):
    u"""⒝：显式开关 ⇒ 逐字取（⛔ 白名单 · ⛔ 归一）。"""
    monkeypatch.setenv("CJ_PA_BIND", "0.0.0.0")
    assert B._bind_host() == "0.0.0.0"
    monkeypatch.setenv("CJ_PA_BIND", "192.168.3.11")
    assert B._bind_host() == "192.168.3.11"


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_bind_blank_falls_back(monkeypatch, blank):
    u"""⒞：空 ／ 空白 ⇒ 回落默认（⛔ 空串 ＝ 全绑）。"""
    monkeypatch.setenv("CJ_PA_BIND", blank)
    assert B._bind_host() == "127.0.0.1"


def test_serve_http_uses_single_source():
    u"""⒟ ＋ ⒡：源内锚（一处定形 ∧ ⛔ 引 `services.gateway.host`）。"""
    src = io.open(B.__file__, encoding="utf-8").read()
    assert 'host="0.0.0.0"' not in src, u"⛔ 硬编全绑（旧病）"
    assert "_host = _bind_host()" in src and "host=_host" in src
    # ⛔ **读**该键（唯注内可提其名 ⇒ 名同义不同之警戒）
    _hits = [ln for ln in src.splitlines() if "services.gateway.host" in ln]
    assert _hits and all(ln.lstrip().startswith("#") for ln in _hits), _hits
    assert 'unified_config.get("services.gateway.host"' not in src


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_serve_http_really_binds(monkeypatch):
    u"""⒠：真起一临时 app（同 `_serve_http` 之路 · 自有之口）⇒ 本机可连。"""
    monkeypatch.delenv("CJ_PA_BIND", raising=False)
    port = _free_port()
    app = Flask("bindtest")

    @app.route("/ping")
    def _ping():
        return "pong"

    threading.Thread(target=B._serve_http, args=(app, port), daemon=True).start()
    ok = False
    for _ in range(160):
        s = socket.socket()
        s.settimeout(0.5)
        try:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                ok = True
                break
        finally:
            s.close()
        time.sleep(0.05)
    assert ok, u"`_serve_http` 未在 127.0.0.1:%d 起" % port
