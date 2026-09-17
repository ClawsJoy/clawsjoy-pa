"""审计 API 后端测试: escalations/approvals/tool_flow 路由 + 审批落盘记录"""
import json
import sys

sys.path.insert(0, ".")
from pathlib import Path

import pytest


@pytest.fixture
def audit_sandbox(tmp_path, monkeypatch):
    """构造带 .agent_state.json(escalations) 的沙箱"""
    sb = tmp_path / "clawsjoy_dev"
    sb.mkdir(parents=True)
    st = {
        "escalations": [
            {
                "timestamp": "2026-08-22T07:40:00",
                "tool": "write_file",
                "target": "/etc/hosts",
                "reason": "路径逃逸",
                "action": "blocked",
            },
            {
                "timestamp": "2026-08-22T07:30:00",
                "tool": "execute_command",
                "target": "rm -rf /tmp",
                "reason": "高危命令",
                "action": "blocked",
            },
        ],
    }
    (sb / ".agent_state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return sb


def _client(monkeypatch, sandbox):
    import agent_gateway_enhanced as main
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    return main.app.test_client()


# ===== escalations 路由 =====


def test_escalations_returns_sorted_desc(audit_sandbox, monkeypatch):
    client = _client(monkeypatch, audit_sandbox)
    resp = client.get("/v9/audit/escalations?user_id=u1&session_id=s1")
    d = resp.get_json()
    assert d["success"] is True
    assert len(d["escalations"]) == 2
    # 时间倒序: 较新的在前面
    assert d["escalations"][0]["tool"] == "write_file"
    assert d["escalations"][1]["tool"] == "execute_command"
    assert d["escalations"][0]["reason"] == "路径逃逸"


def test_escalations_missing_session():
    import agent_gateway_enhanced as main

    d = main.app.test_client().get("/v9/audit/escalations?user_id=u1").get_json()
    assert d["success"] is False and "session_id" in d["error"]


def test_escalations_empty_state(tmp_path, monkeypatch):
    """无 .agent_state.json → 空列表(不报错)"""
    sb = tmp_path / "clawsjoy_dev"
    sb.mkdir(parents=True)
    client = _client(monkeypatch, sb)
    d = client.get("/v9/audit/escalations?user_id=u1&session_id=s1").get_json()
    assert d["success"] is True and d["escalations"] == []


# ===== tool_flow 路由 =====


def test_tool_flow_returns_records(audit_sandbox, monkeypatch):
    """read_audit_records(session_id) 过滤 + 时间倒序"""
    client = _client(monkeypatch, audit_sandbox)
    import core.gateway.audit as audit_mod

    monkeypatch.setattr(
        audit_mod,
        "read_audit_records",
        lambda session_id=None, limit=500: [
            {"ts": 100, "ts_iso": "t1", "tool": "read_file", "success": True, "elapsed_ms": 35, "round": 1},
            {"ts": 200, "ts_iso": "t2", "tool": "execute_command", "success": False, "elapsed_ms": 1800, "round": 2},
        ],
    )
    resp = client.get("/v9/audit/tool_flow?session_id=s1")
    d = resp.get_json()
    assert d["success"] is True
    assert len(d["tool_flow"]) == 2
    assert d["tool_flow"][0]["tool"] == "execute_command"  # ts 大者在前(倒序)
    assert d["tool_flow"][0]["success"] is False
    assert d["tool_flow"][1]["tool"] == "read_file"


# ===== approvals 路由 + 落盘 =====


def test_approvals_returns_records(audit_sandbox, monkeypatch):
    client = _client(monkeypatch, audit_sandbox)
    # 预置一条审批记录
    st = json.loads((audit_sandbox / ".agent_state.json").read_text(encoding="utf-8"))
    st["approvals"] = [
        {"timestamp": "2026-08-22T07:42:00", "kind": "write", "action": "approved", "target": "/x.md", "detail": ""}
    ]
    (audit_sandbox / ".agent_state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    d = client.get("/v9/audit/approvals?user_id=u1&session_id=s1").get_json()
    assert d["success"] is True
    assert d["approvals"][0]["kind"] == "write"
    assert d["approvals"][0]["action"] == "approved"


def test_record_approval_appends(tmp_path, monkeypatch):
    """_record_approval 追加到 .agent_state.json approvals(幂等, 不覆盖 escalations)"""
    import agent_gateway_enhanced as main

    sb = tmp_path / "clawsjoy_dev"
    sb.mkdir(parents=True)
    (sb / ".agent_state.json").write_text(
        json.dumps(
            {
                "escalations": [{"timestamp": "t0", "tool": "x", "target": "y", "reason": "z", "action": "blocked"}],
            }
        ),
        encoding="utf-8",
    )
    import agent_gateway_enhanced as m2
    import core.lib.gateway_helpers as gh2

    monkeypatch.setattr(gh2, "_get_sandbox_base", lambda uid, sid: sb)
    m2._record_approval("u1", "s1", "write", "approved", "/data/out/a.md", "tool=write_file")
    f = sb / ".agent_state.json"
    st = json.loads(f.read_text(encoding="utf-8"))
    assert st["approvals"][0]["kind"] == "write"
    assert st["approvals"][0]["action"] == "approved"
    # escalations 保留(不覆盖)
    assert len(st["escalations"]) == 1
