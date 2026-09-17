"""任务1: /v9/session/clean 会话清理路由"""
import json
import sys

sys.path.insert(0, ".")
from pathlib import Path

import pytest
from flask import Flask

from routes.session import v9_session_clean


@pytest.fixture()
def clean_app(monkeypatch, tmp_path):
    """挂载 clean 路由，隔离 session 状态"""
    app = Flask(__name__)
    app.add_url_rule("/v9/session/clean", view_func=v9_session_clean, methods=["POST"], endpoint="v9_clean")
    return app


def test_clean_route_clears_pending_and_plan(clean_app, tmp_path, monkeypatch):
    """清理后 _pending_writes/_plan_pending 该 session 条目消失，goal 移除"""
    from agent_gateway_enhanced import _pending_writes, _plan_pending
    from core.gateway import goal_state as gs

    sid = "clean_test_session_1"
    _pending_writes[sid] = {"tool": "write_file", "path": "x", "ts": 1.0, "approved": False}
    _plan_pending[sid] = {"ts": 1.0, "approved": False, "plan": "p", "files": [], "intents": 1}
    gs.create_goal("u1", sid, "objective")

    client = clean_app.test_client()
    resp = client.post("/v9/session/clean", json={"user_id": "u1", "session_id": sid})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    # 内存状态清理
    assert sid not in _pending_writes, "pending_writes 未清理"
    assert sid not in _plan_pending, "plan_pending 未清理"
    assert f"u1:{sid}" not in gs._goals, "goal 未清理"
    # 清理后无害（再次调用幂等）
    resp2 = client.post("/v9/session/clean", json={"user_id": "u1", "session_id": sid})
    assert resp2.status_code == 200


def test_clean_clears_runtime_caches(clean_app, monkeypatch):
    """补全: 检索缓存/计数/持久化 pending/subtask 状态清理"""
    from core.gateway import subtask_executor as se
    from core.gateway import tool_router as tr
    from core.gateway.session_cleaner import _clean_session_context
    from core.gateway.shared_state import (
        _consecutive_lists,
        _consecutive_reads,
        _query_cache,
        _retry_cache,
        _search_empty_cache,
    )
    from core.gateway.write_gate import _pending_writes, _plan_pending

    sid = "clean_cache_sess"
    # 填充各状态
    _query_cache[sid] = {"q": "x"}
    _query_cache[sid + "_sub_1"] = {"q": "y"}  # 子任务后缀 key
    _query_cache["other_sess"] = {"q": "z"}  # 其他会话不动
    _search_empty_cache[sid] = 2
    _retry_cache[sid + "_t1"] = {"retry_count": 1}
    _consecutive_reads[sid] = 5
    _consecutive_lists[sid] = 3
    tr._consecutive_failures[sid] = 2
    se._subtasks["u8:" + sid] = {
        "t_done": {"status": "done", "spec": "x"},
        "t_fail": {"status": "failed", "spec": "y"},
        "t_run": {"status": "running", "spec": "z"},
    }
    # 清理
    _clean_session_context("u8", sid)
    # 断言: 该 session 前缀 key 清空, 其他会话保留
    assert sid not in _query_cache, "query_cache 未清"
    assert sid + "_sub_1" not in _query_cache, "子任务后缀 key 未清"
    assert "other_sess" in _query_cache, "其他会话缓存被误清"
    assert sid not in _search_empty_cache
    assert sid + "_t1" not in _retry_cache
    assert sid not in _consecutive_reads
    assert sid not in _consecutive_lists
    assert sid not in tr._consecutive_failures
    # subtask: done/failed 清, running 保留
    st_map = se._subtasks.get("u8:" + sid, {})
    assert "t_done" not in st_map, "done 子任务未清"
    assert "t_fail" not in st_map, "failed 子任务未清"
    assert "t_run" in st_map, "running 子任务被误清"


def test_clean_clears_agent_state_pending_writes(tmp_path, monkeypatch, clean_app):
    """.agent_state.json 的 pending_writes 持久化字段被清除"""
    from core.gateway.session_cleaner import _clean_session_context

    sid = "clean_pw_sess"
    st_file = tmp_path / "data" / "projects" / "u9" / sid / "clawsjoy_dev" / ".agent_state.json"
    st_file.parent.mkdir(parents=True)
    st_file.write_text(json.dumps({"pending_writes": {"pw1": {"path": "x"}}, "other": 1}), encoding="utf-8")
    import core.gateway.session_cleaner as _sc

    real_path = _sc.Path

    def fake_path(p):
        if str(p).startswith("data/projects/u9/"):
            return real_path(str(tmp_path) + "/" + str(p))
        return real_path(p)

    monkeypatch.setattr(_sc, "Path", fake_path)
    _clean_session_context("u9", sid)
    st = json.loads(st_file.read_text(encoding="utf-8"))
    assert "pending_writes" not in st, "agent_state pending_writes 未清"
    assert st.get("other") == 1, "其他字段被误清"


def test_clean_route_snapshot_messages(tmp_path, monkeypatch, clean_app):
    """任务快照 .task_state.json 的 messages 被清空（文件结构保留）"""
    from agent_gateway_enhanced import _pending_writes, _plan_pending

    sid = "clean_test_session_2"
    snap_dir = tmp_path / "data" / "projects" / "u2" / sid / "clawsjoy_dev"
    snap_dir.mkdir(parents=True)
    snap = snap_dir / ".task_state.json"
    snap.write_text(json.dumps({"task_name": "旧任务", "messages": [{"role": "user", "content": "历史"}]}), encoding="utf-8")
    # 用 tmp_path 替换快照路径：monkeypatch Path 构造
    import core.gateway.session_cleaner as _sc

    real_path = _sc.Path

    def fake_path(p):
        if str(p).startswith("data/projects/u2/"):
            return real_path(str(tmp_path) + "/" + str(p))
        return real_path(p)

    monkeypatch.setattr(_sc, "Path", fake_path)
    client = clean_app.test_client()
    resp = client.post("/v9/session/clean", json={"user_id": "u2", "session_id": sid})
    assert resp.status_code == 200
    st = json.loads(snap.read_text(encoding="utf-8"))
    assert st["messages"] == [], "快照 messages 未清空"
    assert st["task_name"] == "", "快照 task_name 未清空"
