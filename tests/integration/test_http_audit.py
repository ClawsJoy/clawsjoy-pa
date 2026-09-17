"""H7: HTTP 工具路由（/v9/sandbox/*）G4 全量审计

回归防线：_with_http_tool_flow 必须同时写 tool_flow（SAG）与
tool_audit.jsonl（第三方审计），防止"HTTP 工具调用零审计"回归。
"""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, ".")
import pytest
from flask import Flask

from core.gateway import audit as audit_mod
from core.gateway import sandbox_ops


@pytest.fixture()
def isolated_audit(tmp_path, monkeypatch):
    """把审计写盘路径隔离到临时目录，不污染 data/v8/audit"""
    audit_dir = tmp_path / "audit"
    monkeypatch.setattr(audit_mod, "_AUDIT_DIR", audit_dir)
    monkeypatch.setattr(audit_mod, "_AUDIT_FILE", audit_dir / "tool_audit.jsonl")
    # 停后台批量落盘线程，测试走同步 flush，避免线程间竞态
    monkeypatch.setattr(audit_mod, "_FLUSH_INTERVAL", 9999.0)
    audit_mod._flush_stop.set()
    # 清空全局内存队列，避免前序测试（如 gateway_routes 的 search_files）残留记录混入
    with audit_mod._audit_lock:
        audit_mod._audit_queue = []
    yield audit_mod._AUDIT_FILE
    # 复位后台线程状态，避免污染其他测试
    audit_mod._flush_stop.clear()
    with audit_mod._audit_lock:
        audit_mod._audit_queue = []


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.add_url_rule(
        "/v9/sandbox/read",
        view_func=sandbox_ops.v9_sandbox_read_handler,
        methods=["POST"],
        endpoint="v9_read",
    )
    app.add_url_rule(
        "/v9/sandbox/exec",
        view_func=sandbox_ops.v9_sandbox_exec_handler,
        methods=["POST"],
        endpoint="v9_exec",
    )
    return app


def _read_audit_lines(path):
    if not Path(path).exists():
        return []
    return [l for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def test_http_read_route_writes_audit(app, isolated_audit):
    """HTTP 工具路由调用后必须追加 tool_audit.jsonl 记录（成功/失败均记录）"""
    client = app.test_client()
    resp = client.post(
        "/v9/sandbox/read",
        json={
            "user_id": "web_1783219071801",
            "session_id": "session_1783388196051",
            "path": "core/gateway/shared_state.py",
        },
    )
    assert resp.status_code == 200
    audit_mod.flush_audit()
    lines = _read_audit_lines(isolated_audit)
    assert lines, "HTTP 工具路由未写入任何审计记录"
    recs = [json.loads(l) for l in lines]
    rec = next((r for r in recs if r["tool"] == "read_file"), None)
    assert rec is not None, f"缺少 read_file 审计记录: {recs}"
    assert rec["user_id"] == "web_1783219071801"
    assert rec["session_id"] == "session_1783388196051"
    assert "success" in rec and "elapsed_ms" in rec and "args_hash" in rec


def test_http_exec_route_writes_audit(app, isolated_audit):
    """execute_command HTTP 路由同样写审计"""
    client = app.test_client()
    resp = client.post(
        "/v9/sandbox/exec",
        json={
            "user_id": "web_1783219071801",
            "session_id": "session_1783388196051",
            "command": "echo h7-audit-check",
        },
    )
    assert resp.status_code == 200
    audit_mod.flush_audit()
    lines = _read_audit_lines(isolated_audit)
    assert lines, "execute_command HTTP 路由未写审计"
    recs = [json.loads(l) for l in lines]
    assert any(r["tool"] == "execute_command" for r in recs)
