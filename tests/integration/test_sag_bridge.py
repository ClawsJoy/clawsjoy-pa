"""R1 P1a: SAG 注册桥 — register_entity 降级 + query_entities + 四注册点"""
import json
import os
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _reset_sab():
    """每个测试前重置 SAB 懒加载状态（防跨测试污染）"""
    from core.lib import sag_audit_bridge as SAB

    SAB._extractor_loaded = False
    SAB._extractor = None
    yield
    SAB._extractor_loaded = False
    SAB._extractor = None


def test_register_entity_db_unavailable_degrades(monkeypatch):
    """DB 不可用 → register_entity 返回 False 不抛异常（mock _get_extractor 强制 None）"""
    from core.lib import sag_audit_bridge as SAB

    monkeypatch.setattr(SAB, "_get_extractor", lambda: None)
    ok = SAB.register_entity("audit_event", "write_file", "success=True", "sess_x", ["u_x"])
    assert ok is False


def test_query_entities_empty_when_db_unavailable(monkeypatch):
    """DB 不可用 → query_entities 返回 []（mock _get_extractor 强制 None）"""
    from core.lib import sag_audit_bridge as SAB

    monkeypatch.setattr(SAB, "_get_extractor", lambda: None)
    res = SAB.query_entities("audit_event")
    assert res == []


def test_registration_points_syntax():
    """四个注册点均已接入（源码断言）"""
    files = {
        "core/gateway/audit.py": ("audit_event", "register_entity"),
        "core/gateway/goal_state.py": ("goal", "register_entity"),
        "core/gateway/message_assembler.py": ("snapshot", "register_entity"),
    }
    # P3-A: _record_escalation 已归位 audit.py → escalation 注册点随之迁入 audit.py
    _audit_es = open("core/gateway/audit.py", encoding="utf-8").read()
    assert "register_entity" in _audit_es, "audit.py 缺 register_entity(escalation)"
    assert "escalation" in _audit_es, "audit.py 缺 entity_type=escalation"
    for path, (etype, fn) in files.items():
        src = open(path, encoding="utf-8").read()
        assert fn in src, f"{path} 缺少 register_entity"
        assert etype in src, f"{path} 缺少 entity_type={etype}"
