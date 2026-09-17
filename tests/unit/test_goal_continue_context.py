# -*- coding: utf-8 -*-
"""2026-09-09: 续跑上下文注入 — steer 带目标原文 + 新任务不一致停问"""
import sys

sys.path.insert(0, ".")
import pytest


def test_continue_steer_has_objective():
    src = (
        open("agent_gateway_enhanced.py", encoding="utf-8").read()
        + open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()
    )  # P3-B: G 块已归位
    assert "目标任务原文: " in src
    assert "_gobj[:400]" in src or "_gobj[:60]" in src
    assert "不要自行搜索猜测" in src
    assert "不要重复已完成步骤" in src
