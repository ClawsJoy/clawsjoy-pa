# -*- coding: utf-8 -*-
"""X-18 方向 3 最小硬化（**改行为批**）：显式接管必须在日志里**可见**。

判据来源：``core/pes/windows.py::BROWSER_ISOLATION`` 的 ``user_profile_reuse=explicit_only``
—— 复用日常 profile 只允许「**显式接管**」，且必须**看得见**（不许静默接管）。

本文件只测**宣告层**（不联网、不启真浏览器）：``BrowserSession`` 的构造只建目录；
``start()`` 用**假 playwright** 顶替，故不下载、不启动 Chrome。
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path

import pytest

AGENT_CLIENT = Path(__file__).resolve().parents[2] / "scripts" / "agent_client"
LOGGER = "agent_client.browser"


@pytest.fixture()
def browser_mod():
    spec = importlib.util.spec_from_file_location("x18_agent_client_browser", AGENT_CLIENT / "browser.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _msgs(caplog):
    return [(r.levelname, r.getMessage()) for r in caplog.records]


def test_显式接管打_warning_且带实际路径(browser_mod, caplog, tmp_path):
    taken = tmp_path / "taken_profile"
    s = browser_mod.BrowserSession(profile_root=str(tmp_path), user_data_dir=str(taken))
    with caplog.at_level(logging.INFO, logger=LOGGER):
        s._announce_profile(s._resolve_user_data_dir())
    msgs = _msgs(caplog)
    assert any(lv == "WARNING" for lv, _ in msgs), msgs
    assert any("接管" in m and str(taken) in m for _, m in msgs), msgs


def test_专用实例只打_info_不打_warning(browser_mod, caplog, tmp_path):
    s = browser_mod.BrowserSession(profile_root=str(tmp_path))
    with caplog.at_level(logging.INFO, logger=LOGGER):
        s._announce_profile(s._resolve_user_data_dir())
    msgs = _msgs(caplog)
    assert not [m for lv, m in msgs if lv == "WARNING"], msgs
    assert any("专用实例" in m for _, m in msgs), msgs


def test_start_真路径上也会宣告(browser_mod, caplog, tmp_path, monkeypatch):
    """接线判据（端到端·假 playwright）：``start()`` 必须真的走到宣告，否则警告只在纸上。"""
    fake_api = types.ModuleType("playwright.sync_api")

    class _Chromium:
        def launch_persistent_context(self, ud, **kw):
            return object()

    class _PW:
        chromium = _Chromium()

        def start(self):
            return self

    fake_api.sync_playwright = lambda: _PW()
    fake_root = types.ModuleType("playwright")
    fake_root.sync_api = fake_api
    monkeypatch.setitem(sys.modules, "playwright", fake_root)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_api)
    monkeypatch.setattr(browser_mod.BrowserSession, "_inject_cookies", lambda self: None, raising=True)

    taken = tmp_path / "taken_profile"
    s = browser_mod.BrowserSession(profile_root=str(tmp_path), user_data_dir=str(taken))
    with caplog.at_level(logging.INFO, logger=LOGGER):
        s.start()
    msgs = _msgs(caplog)
    assert any(lv == "WARNING" and "接管" in m and str(taken) in m for lv, m in msgs), msgs