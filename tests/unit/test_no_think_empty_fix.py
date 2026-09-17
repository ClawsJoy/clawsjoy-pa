# -*- coding: utf-8 -*-
"""封面类简单任务空回复修复: reasoning-only 残留 → 简单生成任务/空回复重试强制关 thinking"""
import sys

sys.path.insert(0, ".")

_SRC = open("agent_gateway_enhanced.py", encoding="utf-8").read()


def test_no_think_wired():
    """flag 初始化 + 简单生成类启发式 + 空回复重试强制关 + 调用点使用"""
    _LOOP = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    assert "_no_think = False" in _LOOP
    assert "简单生成类任务, 关闭 thinking" in _LOOP, "启发式应存在"
    assert "_gen_kw = (" in _LOOP and "_think_kw = (" in _LOOP, "关键词组应存在"
    assert "封面" in _LOOP.split("_gen_kw = (")[1].split(")")[0], "生成类应含封面"
    _RG = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    assert "no_think = True  # (2026-09-05) 空回复重试强制关 thinking" in _RG
    _LC = open("core/gateway/v9_bridge/llm_call.py", encoding="utf-8").read()
    assert "thinking=(thinking2 and not no_think)" in _LC, "主 LLM 调用点应使用 no-think 门控"
    assert "thinking=(_thinking2 and not _no_think)" in _SRC, "输出防截断重试也应门控"


def test_no_think_heuristic_logic():
    """启发式: 封面任务(无分析词)→关; 分析/修复任务→不关"""
    gen = ("封面", "生成", "写稿", "绘图", "出图", "海报")
    think = ("分析", "评估", "设计", "排查", "修复", "架构", "方案", "复盘")

    def judge(text):
        return any(k in text for k in gen) and not any(k in text for k in think)

    assert judge("生成一张 900x383 封面并落盘") is True
    assert judge("设计封面风格方案") is False  # 含设计/方案
    assert judge("排查封面生成失败的原因") is False  # 排查类
    assert judge("分析近期 token 消耗并出报告") is False
