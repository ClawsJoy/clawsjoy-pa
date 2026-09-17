# -*- coding: utf-8 -*-
"""#24 compaction 0.8 回归: 阈值触发/动态keep/压缩后降token"""
import sys

sys.path.insert(0, ".")
import pytest


def test_compaction_threshold_config():
    import yaml

    cfg = yaml.safe_load(open("config/v9/execution_policy.yaml", encoding="utf-8"))
    # R2(2026-08-30): 0.8→0.6 更早压缩(原阈值过高 → 上下文堆积到近预算才压 → token 爆炸)
    assert cfg["execution_budget"].get("compaction_threshold") == 0.6


def test_no_300000_skip():
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "> 300000" not in src, "仍含 >300000 跳过压缩 bug"
    assert "compaction_threshold" in src, "缺 compaction_threshold 读取"


def test_compaction_trigger_logic():
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "_ratio_24" in src and "_threshold_24 = _budget_round * _ratio_24" in src, "缺阈值计算"
    assert "_keep_24 = max(min(int(_target_24 / _avg_24), 8), 4)" in src, "缺动态 keep"
    budget = 61536
    threshold = budget * 0.6
    assert 36000 < threshold < 38000, f"threshold={threshold}"


def test_compaction_reduces_tokens():
    """压缩后 token 大幅下降(模拟长上下文 8.5万场景)"""
    import tempfile

    from core.gateway.message_assembler import _compress_messages, _finalize_messages, _tg_estimate

    msgs = [{"role": "system", "content": "你是ClawsJoy助手, 任务: 完成报告"}]
    msgs.append({"role": "user", "content": "任务开始"})
    for i in range(100):
        msgs.append({"role": "assistant", "content": f"第{i}步执行"})
        msgs.append({"role": "tool", "content": f"结果{i}: " + "x" * 500})
    est_before = _tg_estimate(msgs, [])
    with tempfile.TemporaryDirectory() as td:
        compressed = _compress_messages(msgs, "user_c24", "sess_c24", keep=6)
        compressed = _finalize_messages(compressed)
        est_after = _tg_estimate(compressed, [])
    print(f"est_before={est_before} est_after={est_after}")
    assert est_before > 1000, f"测试消息应够长: {est_before}"
    assert est_after < est_before / 5, f"压缩不足: {est_before} → {est_after}"
    # 85万场景: 压缩应使 85万 → <10万(这里用比例证明压缩能力)
    assert est_after < 5000, f"压缩后应很小: {est_after}"
