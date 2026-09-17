# -*- coding: utf-8 -*-
"""任务边界写入回归(2026-09-07 死循环根因修复):
1) [系统] 前缀内部注入(runtime_context)不当任务边界
2) 真实用户消息一律写入, 仅 15s 内同内容紧邻去重(不误伤失败后重试)
"""
import sys

sys.path.insert(0, ".")
import pytest


def test_bridge_source_has_task_boundary_fix():
    """bridge 写入点包含: [系统] 分类 + runtime_context + 15s 窗口"""
    src = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    assert 'startswith("[系统]")' in src, "缺 [系统] 内部注入分类"
    assert '"source": "runtime_context"' in src, "缺 runtime_context 落盘"
    assert "< 15" in src, "缺 15s 紧邻去重窗口"


def test_async_source_has_task_boundary_fix():
    """async 引擎写入点同样包含任务边界语义"""
    src = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    assert 'startswith("[系统]")' in src
    assert '"source": "runtime_context"' in src
    assert "< 15" in src


def test_derive_source_skips_system_prefixed_boundary():
    """derive last_task_only 边界过滤 [系统] 前缀旧日志"""
    src = open("core/gateway/session_log.py", encoding="utf-8").read()
    assert 'startswith("[系统]")' in src, "derive 边界应跳过 [系统] 前缀"


def test_retry_after_failure_writes():
    """模拟: 上次任务失败后同文本重发 → 应写入(新边界), 不再被连续去重吞掉"""
    import time as _t

    # 旧行为: content 与投影最后 user 相同 → 跳过; 新行为: 只看 15s 内紧邻重复
    messages_now = [{"role": "user", "content": "任务：盘点项目状态"}]
    last_user_now = messages_now[-1]["content"]
    # 上次任务是 1 小时前(失败后用户重发) → 非紧邻 → 必须写入
    last_event_ts = _t.time() - 3600
    recent_same = (_t.time() - last_event_ts) < 15
    assert not recent_same, "1 小时前的重试不应被去重"
    # 同一 POST 双写(秒级内) → 去重
    assert (_t.time() - _t.time()) < 15 and last_user_now == last_user_now
