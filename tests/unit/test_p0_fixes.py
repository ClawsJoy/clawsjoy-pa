# -*- coding: utf-8 -*-
"""P0 修复回归: #14 重试退避 / #15 TTL 触发点 / #18 token 明细"""
import sys

sys.path.insert(0, ".")
import pytest


def test_retry_backoff():
    """#14: adapter 含重试循环 + 指数退避"""
    src = open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()
    assert "_max_retries = 3" in src, "缺3次重试"
    assert "2 * (2 ** _attempt_rt)" in src, "缺指数退避"
    assert "DS_RETRY" in src, "缺重试日志"


def test_ttl_cleanup_triggers():
    """#15: 审批查询 + restore 路径触发 TTL 清理"""
    # 查询路由在 routes/audit.py
    src = open("routes/audit.py", encoding="utf-8").read()
    assert "def v9_audit_approvals():" in src
    idx = src.find("def v9_audit_approvals():")
    block = src[idx : idx + 400]
    assert "_pending_cleanup()" in block, "审批查询未触发 TTL 清理"
    # restore 仍在主文件
    gw = open("core/gateway/write_gate.py", encoding="utf-8").read()  # P3-A: _v9_restore_pending_writes 已归位
    idx2 = gw.find("def _v9_restore_pending_writes")
    block2 = gw[idx2 : idx2 + 300]
    assert "_pending_cleanup()" in block2, "restore 未触发 TTL 清理"


def test_token_detail_log():
    """#18: adapter 返回 usage_detail + bridge 打印 TOKEN_LOG"""
    adap = open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()
    assert "usage_detail" in adap, "adapter 缺 usage_detail"
    assert "reasoning" in adap and "cache" in adap, "缺 reasoning/cache 明细"
    gw = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    assert "TOKEN_LOG" in gw, "bridge 缺 TOKEN_LOG 打印"
    assert "usage_detail" in gw, "bridge 缺 usage_detail 消费"
