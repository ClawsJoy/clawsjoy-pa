# -*- coding: utf-8 -*-
"""BUG-3 回归: 缺省 session 自动分配稳定唯一 id + 双重序列化容错"""
import json
import pathlib
import sys

sys.path.insert(0, ".")
import pytest


def _clean_map(tmp_path, uid):
    mf = pathlib.Path("data/projects") / uid / ".v9_default_session.json"
    if mf.exists():
        mf.unlink()


def test_default_session_assigned_stable_unique(tmp_path, monkeypatch):
    """缺省 session → 自动分配稳定唯一 id(同 user 复用, 非 default)"""
    from agent_gateway_enhanced import _resolve_v9_session_id

    uid = "user_test_ds1"
    _clean_map(None, uid)
    sid1, auto1 = _resolve_v9_session_id(uid, "default")
    assert auto1 is True, "缺省应自动分配"
    assert sid1 != "default", "不应是 default"
    assert sid1.startswith("v9auto_"), sid1
    # 同 user 再次缺省 → 复用同一 id(会话稳定)
    sid2, auto2 = _resolve_v9_session_id(uid, "")
    assert sid2 == sid1, "同 user 缺省应复用同一 id"
    # 显式传入 → 尊重
    sid3, auto3 = _resolve_v9_session_id(uid, "session-explicit-1")
    assert auto3 is False and sid3 == "session-explicit-1"
    _clean_map(None, uid)


def test_default_session_unique_per_user(tmp_path, monkeypatch):
    """不同 user 缺省 → 不同 id(互不串扰)"""
    from agent_gateway_enhanced import _resolve_v9_session_id

    _clean_map(None, "user_test_a")
    _clean_map(None, "user_test_b")
    a1, _ = _resolve_v9_session_id("user_test_a", "default")
    b1, _ = _resolve_v9_session_id("user_test_b", "default")
    assert a1 != b1, "不同 user 应分配不同 id"
    _clean_map(None, "user_test_a")
    _clean_map(None, "user_test_b")


def test_pending_writes_double_serialized_restore(tmp_path, monkeypatch):
    """旧数据 pending_writes 为 str(双重序列化) → 恢复容错不崩溃"""
    import agent_gateway_enhanced as g

    # 模拟旧版: pending_writes 是字符串
    st = {
        "pending_writes": json.dumps(
            {"sess_x": {"id": "c1", "tool": "write_file", "path": "a.md", "content_preview": "X" * 100, "ts": 100}}
        )
    }
    # 走 _persist_pending_writes 的读取逻辑: 构造一个含 str pending 的 state 文件
    uid, sid = "user_pw", "sess_x"
    f = pathlib.Path(f"data/projects/{uid}/{sid}/clawsjoy_dev/.agent_state.json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    import core.gateway.write_gate as _wg

    monkeypatch.setattr(_wg, "_pending_writes", {})
    monkeypatch.setattr(g, "_pending_writes", _wg._pending_writes)
    g._v9_restore_pending_writes(uid, sid)
    assert sid in g._pending_writes, "str pending 应被恢复"
    assert g._pending_writes[sid]["path"] == "a.md"
    # 清理
    import shutil

    shutil.rmtree(pathlib.Path(f"data/projects/{uid}"), ignore_errors=True)
