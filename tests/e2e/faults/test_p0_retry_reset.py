# -*- coding: utf-8 -*-
"""续跑计数必须每 turn 重置（2026-09-13 修）。

事故：verification_retry_reset 全仓只有定义、**生产代码 0 个调用点** →
VERIFICATION_RETRY_CAP=2 变成「会话级永久耗尽」：前 2 次续跑用掉后，
同一会话后续 turn 再也无法续跑 —— 核验闸门形同失效。
"""
import sys

sys.path.insert(0, ".")
from core.gateway import shared_state as ss


def test_FAULT_reset_is_called_on_new_turn():
    """① 先能失败：新 turn 必须有重置调用点（源码级锁定）。"""
    src = open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()
    assert "verification_retry_reset" in src, "新 turn 未重置续跑计数 → 上限会永久耗尽"


def test_PASS_reset_restores_budget():
    """② 再能通过：重置后又能续跑。"""
    sid = "s_reset"
    ss.verification_retry_reset(sid)
    assert ss.verification_retry_bump(sid) is True
    assert ss.verification_retry_bump(sid) is True
    assert ss.verification_retry_bump(sid) is False  # 上限内用尽
    ss.verification_retry_reset(sid)  # 新 turn 重置
    assert ss.verification_retry_bump(sid) is True
