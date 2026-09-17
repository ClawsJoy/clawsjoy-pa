"""任务: 子任务委托深度预算(借鉴 Harness delegationDepth)

- depth = 父深度 + 1; maxDepth 默认 3; 第 4 层拒绝(SubtaskDepthError)
- depth 持久化到 .agent_state.json(重启不丢)
"""
import json
import sys
import time

sys.path.insert(0, ".")
from pathlib import Path

import pytest

from core.gateway import subtask_executor as se


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """隔离 _subtasks + 沙箱根(避免污染/落盘真实路径)"""
    monkeypatch.setattr(se, "_subtasks", {})
    import core.gateway.subtask_executor as m

    real_path = m.Path

    def fake_path(p):
        if str(p).startswith("data/projects"):
            return real_path(str(tmp_path) + "/" + str(p))
        return real_path(p)

    monkeypatch.setattr(m, "Path", fake_path)

    # mock 执行引擎(避免 submit 后真实 LLM 调用拖慢测试)
    def _fake_execute(*a, **k):
        return None

    monkeypatch.setattr("core.gateway.execute_agent_task._execute_agent_task", _fake_execute)
    yield


def test_resolve_depth_parent_plus_one():
    """子任务深度 = 父深度 + 1"""
    assert se.resolve_depth(0) == 1
    assert se.resolve_depth(2) == 3
    assert se.resolve_depth(None) == 1
    assert se.resolve_depth("2") == 3


def test_depth_within_limit_submits():
    """depth 0-3 正常提交, entry 记录 depth"""
    for d in (0, 1, 2, 3):
        tid = se.submit("u_d", "s_d", "任务", depth=d)
        entry = se._state("u_d", "s_d")[tid]
        assert entry["depth"] == d, f"depth {d} 应记录: {entry}"


def test_depth_exceeds_limit_raises():
    """depth 4(第 4 层) 超 maxDepth 3 抛 SubtaskDepthError"""
    with pytest.raises(se.SubtaskDepthError) as ei:
        se.submit("u_d", "s_d", "任务", depth=4)
    assert "subtask depth 4 exceeds maxDepth 3" in str(ei.value)
    assert "子任务委派深度超限" in str(ei.value)


def test_custom_max_depth():
    """自定义 max_depth 覆盖默认 3"""
    se.submit("u_d", "s_d", "任务", depth=5, max_depth=5)  # 不抛
    with pytest.raises(se.SubtaskDepthError):
        se.submit("u_d", "s_d", "任务", depth=6, max_depth=5)


def test_depth_persisted_to_agent_state(tmp_path):
    """depth 随 .agent_state.json subtasks 落盘(重启不丢)"""
    tid = se.submit("u_p", "s_p", "持久化任务", depth=2)
    st_file = Path(tmp_path) / "data" / "projects" / "u_p" / "s_p" / ".agent_state.json"
    assert st_file.exists(), "应落盘 .agent_state.json"
    st = json.loads(st_file.read_text(encoding="utf-8"))
    subs = st.get("subtasks", {})
    assert tid in subs, f"subtasks 应含 {tid}: {list(subs.keys())}"
    assert subs[tid]["depth"] == 2, f"depth 应持久化: {subs[tid]}"
    assert subs[tid]["status"] == "queued"


def test_route_rejects_depth_exceeded():
    """/v9/subtask/create depth=4 返回结构化错误 SUBTASK_DEPTH_EXCEEDED"""
    from flask import Flask

    # ⑥(2026-09-13) 路由已迁出主文件(P1): /v9/subtask/create 在 routes/session.py 的 Blueprint
    from routes.session import bp as _session_bp

    app = Flask(__name__)
    app.register_blueprint(_session_bp)
    app.config["TESTING"] = True
    client = app.test_client()
    r = client.post(
        "/v9/subtask/create",
        json={
            "user_id": "u_r",
            "session_id": "s_r",
            "task_spec": "深层任务",
            "depth": 4,
        },
    )
    d = r.get_json()
    assert d["success"] is False
    assert d["error_code"] == "SUBTASK_DEPTH_EXCEEDED"
    assert d["max_depth"] == 3
    assert "子任务委派深度超限" in d["error"]
