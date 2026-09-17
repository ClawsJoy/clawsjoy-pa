# -*- coding: utf-8 -*-
"""browser_local upload 动作回归: schema + 客户端分发 + actions.upload 逻辑"""
import sys

sys.path.insert(0, ".")
import json


def test_schema_has_upload_action():
    """V9 工具层 schema enum 含 upload + kind/files/file 参数"""
    from core.tools.browser_local import BROWSER_LOCAL_SCHEMA

    props = BROWSER_LOCAL_SCHEMA["function"]["parameters"]["properties"]
    enum = props["action"]["enum"]
    assert "upload" in enum, enum
    assert "kind" in props and "files" in props and "file" in props


def test_client_dispatches_upload():
    """agent_client.py 分发链含 upload 分支"""
    src = open("scripts/agent_client/agent_client.py", encoding="utf-8").read()
    assert 'action == "upload"' in src


def test_actions_upload_method():
    """actions.py 含 upload 方法 + video kind 支持"""
    src = open("scripts/agent_client/actions.py", encoding="utf-8").read()
    assert "def upload(self, page, platform, params):" in src
    assert "set_input_files" in src
    assert 'kind == "video"' in src
    assert "video_input" in src  # _pick_upload_input 支持平台 video_input 配置


def test_platforms_bilibili_video_config():
    """platforms.py bilibili publish 含视频上传选择器"""
    src = open("scripts/agent_client/platforms.py", encoding="utf-8").read()
    assert "member.bilibili.com/platform/upload/video/frame" in src
    assert "video_input" in src


def test_browser_profile_lock_detection():
    """browser.py 含 profile 锁检测(防止二次 launch 冲突)"""
    src = open("scripts/agent_client/browser.py", encoding="utf-8").read()
    assert "_profile_locked" in src
    assert "SingletonLock" in src
    assert "禁止再写独立 playwright 脚本" in src


def test_agent_prompt_bans_scripts():
    """agent_system.md 提示 Agent 禁止写独立 playwright 脚本 + 用 upload"""
    src = open("config/prompts/agent_system.md", encoding="utf-8").read()
    assert "upload 动作" in src
    assert "禁止写独立 playwright/python 脚本" in src
