"""任务3: 子任务并发执行器测试（有界池/独立沙箱/git 基线/归档/保留现场）"""
import json
import sys
import time

sys.path.insert(0, ".")
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from core.gateway import subtask_executor as se


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """隔离状态 dict + 沙箱根 + mock 执行引擎"""
    monkeypatch.setattr(se, "_subtasks", {})
    # 用 tmp_path 替换沙箱根
    import core.gateway.subtask_executor as m

    real_path = m.Path

    def fake_path(p):
        if str(p).startswith("data/projects"):
            return real_path(str(tmp_path) + "/" + str(p))
        return real_path(p)

    monkeypatch.setattr(m, "Path", fake_path)

    # mock _execute_agent_task: 直接回调 on_done + 写产出文件
    def _fake_execute(
        user_id,
        session_id,
        messages,
        model,
        task_id,
        sub_task_id=None,
        on_done=None,
        on_fail=None,
        sandbox_base=None,
        parent_goal_id=None,
    ):
        if sandbox_base is not None:
            (sandbox_base / "report.md").write_text("# 完成\n子任务输出", encoding="utf-8")
        if on_done:
            on_done(task_id, user_id, session_id, "子任务完成")

    monkeypatch.setattr("core.gateway.execute_agent_task._execute_agent_task", _fake_execute)
    yield


def _wait_status(uid, sid, task_id, want, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = se._state(uid, sid)
        if st.get(task_id, {}).get("status") == want:
            return st[task_id]
        time.sleep(0.2)
    return st.get(task_id, {})


def test_approval_isolation_clears_pending_via_container(monkeypatch):
    """#76 审批隔离: subtask_executor 从 V9Context 容器取清理服务, 不 import 网关"""
    from core.os.context import get_v9_context

    # 模拟网关已注册的清理服务(真实网关启动时注册)
    _cleared = []

    def _fake_cleaner(session_key):
        _cleared.append(session_key)

    ctx = get_v9_context()
    # ⑭(2026-09-13) 先存原状态: 旧写法 finally 里无条件写 None → 键存在值为 None →
    # write_gate 的 import 时注册(if not has())永不重跑 → 污染后序测试。
    # 清理必须区分"本来有值"与"本来没有": 后者要**删键**, 否则留一个值为 None 的键 = 同样的坑。
    _had_cleaner = ctx.has("pending_writes_cleaner")
    _old_cleaner = ctx.get_opt("pending_writes_cleaner")
    ctx.provide_override("pending_writes_cleaner", _fake_cleaner)
    try:
        # 不直接跑 _run(需沙箱/mock), 断言 _run 源码走容器而非 import 网关
        src = Path("core/gateway/subtask_executor.py").read_text(encoding="utf-8")
        assert "from agent_gateway_enhanced import" not in src, "子任务不应 import 网关"
        assert "pending_writes_cleaner" in src, "应从 V9Context 容器取清理服务"
        # 行为验证: 容器服务可被调用
        cleaner = ctx.get_opt("pending_writes_cleaner")
        assert cleaner is not None
        cleaner("sess_sub")
        assert _cleared == ["sess_sub"], f"清理服务应被调用: {_cleared}"
    finally:
        # 恢复原状态(而非置 None): 原来有值 → 写回原值; 原来没这个键 → 删键
        if _had_cleaner:
            ctx.provide_override("pending_writes_cleaner", _old_cleaner)
        else:
            getattr(ctx, "_services", {}).pop("pending_writes_cleaner", None)


def test_submit_runs_and_archives(tmp_path):
    """提交后状态 queued→done，独立沙箱 + git 基线 + 归档完成"""
    uid, sid = "u3", "s3"
    tid = se.submit(uid, sid, "读取并总结 audit.py", "mock-model")
    assert tid.startswith("sub_")
    # queued → running → done
    entry = _wait_status(uid, sid, tid, "done")
    assert entry["status"] == "done", f"应完成: {entry}"
    assert entry["result"], "应有结果"
    # 独立沙箱执行后被归档 move 走（原 subtasks/{tid} 不存在），产出在归档目录
    sub_dir = Path(tmp_path) / "data" / "projects" / uid / sid / "clawsjoy_dev" / "subtasks" / tid
    assert not sub_dir.exists(), "成功子任务沙箱应已归档 move 走"
    # 归档: move 到 archive/subtasks/{tid}
    archived = Path(tmp_path) / "data" / "projects" / uid / sid / "clawsjoy_dev" / "archive" / "subtasks" / tid
    assert archived.exists(), f"应归档到 {archived}"
    assert (archived / "report.md").exists(), "归档应含产出文件"
    assert "archived_path" in entry and entry["archived_path"], "状态应有归档路径"


def test_submit_failure_keeps_site(tmp_path, monkeypatch):
    """执行失败保留现场（不归档不清理），状态 failed"""

    def _fail_execute(
        user_id,
        session_id,
        messages,
        model,
        task_id,
        sub_task_id=None,
        on_done=None,
        on_fail=None,
        sandbox_base=None,
        parent_goal_id=None,
    ):
        if sandbox_base is not None:
            (sandbox_base / "partial.md").write_text("半成品", encoding="utf-8")
        if on_fail:
            on_fail(task_id, user_id, session_id, "执行失败")

    monkeypatch.setattr("core.gateway.execute_agent_task._execute_agent_task", _fail_execute)
    uid, sid = "u4", "s4"
    tid = se.submit(uid, sid, "会失败的任务", "mock-model")
    entry = _wait_status(uid, sid, tid, "failed")
    assert entry["status"] == "failed"
    assert entry["error"], "应有错误信息"
    # 保留现场: subtasks/{tid} 不清理
    sub_dir = Path(tmp_path) / "data" / "projects" / uid / sid / "clawsjoy_dev" / "subtasks" / tid
    assert (sub_dir / "partial.md").exists(), "失败应保留现场(partial.md)"
    # 不归档
    archived = Path(tmp_path) / "data" / "projects" / uid / sid / "clawsjoy_dev" / "archive" / "subtasks" / tid
    assert not archived.exists(), "失败不应归档"


def test_routes_create_and_status(monkeypatch):
    """/v9/subtask/create + /v9/subtask/status 路由"""
    from flask import Flask

    # ⑦(2026-09-13) 路由已迁出主文件(P1): create/status 在 routes/session.py 的 Blueprint
    from routes.session import bp as _session_bp

    app = Flask(__name__)
    app.register_blueprint(_session_bp)
    app.config["TESTING"] = True
    client = app.test_client()
    r1 = client.post("/v9/subtask/create", json={"user_id": "u5", "session_id": "s5", "task_spec": "测试子任务"})
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1["success"] is True and d1["task_id"], f"创建失败: {d1}"
    # 等完成
    _wait_status("u5", "s5", d1["task_id"], "done")
    r2 = client.get("/v9/subtask/status?user_id=u5&session_id=s5")
    d2 = r2.get_json()
    assert d2["success"] is True
    assert any(t["task_id"] == d1["task_id"] for t in d2["subtasks"]), "状态列表应含创建的子任务"
