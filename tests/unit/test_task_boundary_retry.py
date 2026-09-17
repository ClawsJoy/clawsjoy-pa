# -*- coding: utf-8 -*-
"""任务边界隔离(2026-09-07): 内部注入不当边界 + 重试推进边界"""
import sys
import time as _t

sys.path.insert(0, ".")
from pathlib import Path

import pytest

from core.gateway.session_log import EV_ASSISTANT_MESSAGE, EV_TOOL_RESULT, EV_USER_MESSAGE, SessionLog


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    import core.gateway.session_log as sl

    monkeypatch.setattr(sl, "_logs", {})
    _dir = Path("data/session_logs")
    if _dir.exists():
        for _f in _dir.glob("*.jsonl"):
            try:
                _f.unlink()
            except Exception:
                pass
    yield tmp_path
    if _dir.exists():
        for _f in _dir.glob("*.jsonl"):
            try:
                _f.unlink()
            except Exception:
                pass


def _append_user(log, content, source="user_input", role="user", ts=None):
    """落盘 user_message 事件(可指定 ts 模拟时间)"""
    ev = log.append("user_message", {"role": role, "content": content, "source": source})
    if ts is not None:
        ev.ts = ts
    return ev


def test_derive_boundary_skips_system_prefixed_user_input(tmp_path):
    """旧日志: 注入消息曾以 user_input 落盘 — 边界应跳过它, 投影真实任务"""
    log = SessionLog("u_br1", base_dir=tmp_path)
    _append_user(log, "真实任务：做抖音调研", source="user_input", role="user")
    _append_user(log, "[系统] 继续执行当前目标，请基于已有进度继续", source="user_input", role="user")
    _append_user(log, "[系统] 当前运行环境快照：沙箱", source="runtime_context", role="system")
    # 旧实现会把边界落在 "[系统] 继续执行..." 上(真实任务被切掉)
    proj = log.derive_messages(last_task_only=True)
    roles = [m["role"] for m in proj]
    texts = [str(m.get("content") or "") for m in proj]
    assert "真实任务：做抖音调研" in texts, "真实任务文本必须在投影内(边界不能落在注入消息上)"
    assert roles == ["user", "user", "system"], f"投影角色序列错误: {roles}"


def test_last_real_user_is_boundary_when_system_injected_after(tmp_path):
    """新写入: 注入记 runtime_context; 边界 = 最近真实用户任务"""
    log = SessionLog("u_br2", base_dir=tmp_path)
    _append_user(log, "旧任务A", source="user_input", role="user")
    _append_user(log, "[系统] 继续执行", source="runtime_context", role="system")
    _append_user(log, "新任务B", source="user_input", role="user")
    proj = log.derive_messages(last_task_only=True)
    texts = [str(m.get("content") or "") for m in proj]
    assert "新任务B" in texts
    assert "旧任务A" not in texts, "旧任务不应投影(边界在新任务B)"


def test_same_text_retry_advances_boundary(tmp_path):
    """失败后同文本重试: 两次 user_input 都写入 → 边界推进到第二次"""
    log = SessionLog("u_br3", base_dir=tmp_path)
    _append_user(log, "任务：制作视频", source="user_input", role="user", ts=_t.time() - 600)
    # 模拟旧失败尾事件
    log.append("assistant_message", {"role": "assistant", "content": ""})
    _append_user(log, "任务：制作视频", source="user_input", role="user", ts=_t.time())
    proj = log.derive_messages(last_task_only=True)
    # 边界应落在第二次提交: 投影不含第一次提交之前的旧失败尾
    texts = [str(m.get("content") or "") for m in proj]
    assert len(texts) == 1 and "任务：制作视频" in texts, f"重试未形成干净新边界: {texts}"


def test_goal_continue_visible_but_not_boundary(tmp_path):
    """goal 续跑消息模型可见(投影内含), 但不推进任务边界"""
    log = SessionLog("u_br4", base_dir=tmp_path)
    _append_user(log, "任务：按草稿制作视频", source="user_input", role="user")
    log.append("assistant_message", {"role": "assistant", "content": "已配音", "tool_calls": None})
    _append_user(log, "[系统] 继续执行当前目标，请基于已有进度继续", source="runtime_context", role="system")
    proj = log.derive_messages(last_task_only=True)
    texts = [str(m.get("content") or "") for m in proj]
    assert "任务：按草稿制作视频" in texts, "真实任务必须在(续跑不得切掉任务)"
    assert any("继续执行当前目标" in t for t in texts), "续跑指令仍应对模型可见"
