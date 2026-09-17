# -*- coding: utf-8 -*-
"""2026-09-07: EnvBlockGuard 环境阻塞收敛 + browser DOM 深挖上限
针对: 登录墙(飞书内嵌 sheet 0 行)/302 无限重定向/浏览器不可用时, Agent 换法硬闯
(逐格读 canvas / 反复 extract / 换抓取工具)烧预算 — 需在 ≥3 次环境阻塞后硬收敛。"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.shared_state import browser_unavailable_error, env_block_error


def test_env_block_detected():
    assert env_block_error({"success": False, "error": "浏览器不可用: browser has been closed"})
    assert env_block_error({"success": False, "error": "未读到表格内容: 需登录态(内嵌 sheet 0 行)"})
    assert env_block_error({"success": False, "error": "HTTPError: HTTP 302 infinite redirect"})
    assert env_block_error({"success": True, "error": ""}) == ""
    assert env_block_error({"success": False, "error": "网络超时"}) == ""


def test_bridge_has_envblock_and_dig_cap():
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "ENVBLOCK_STOP" in src
    assert "env_block_error" in src
    assert "DOM_DIG_STOP" in src
    assert 'in ("evaluate", "extract", "scroll")' in src
    assert "禁止继续用替代方式硬闯" in src


def test_shared_state_has_env_markers():
    src = open("core/gateway/shared_state.py", encoding="utf-8").read()
    assert "def env_block_error" in src
    assert '"0 行"' in src or "0 行" in src


def test_steers_via_add_steer_channel():
    """空参/浏览器/环境阻塞/DOM 深挖 steer 走 add_steer 通道(防 derive 抹掉)"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    _TR = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "add_steer as _st_buv" in src or "_st_buv(session_id" in src
    assert "_st_envb(session_id" in src
    assert "_st_dig(session_id" in src
    assert "_ea_steer(session_id" in _TR
    assert "本地 messages.append 会被下轮 derive 重建抹掉" in _TR
