"""R1 P1a: SAG 注册桥 — register_entity 降级 + query_entities + 四注册点
+ 注销入口（unregister_entity ／ unregister_stale · pm_1951 §二.1 之裁⒝）"""
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


# --------------------------------------------------------------------------- 注销入口
# 承 pm_1951 §二.1（裁：桥加「注销入口」＝一处定形 ⇒ 调用者 ⛔ 自撰 SQL）。


def test_unregister_entity_db_unavailable_degrades(monkeypatch):
    """DB 不可用 → unregister_entity 返回 False 不抛异常。"""
    from core.lib import sag_audit_bridge as SAB

    monkeypatch.setattr(SAB, "_get_extractor", lambda: None)
    assert SAB.unregister_entity("vault_doc", "a.md", "vault/a.md") is False


def test_unregister_stale_db_unavailable_degrades(monkeypatch):
    """DB 不可用 → unregister_stale 返回 -1（降级照实 · ⛔ 静默）。"""
    from core.lib import sag_audit_bridge as SAB

    monkeypatch.setattr(SAB, "_get_extractor", lambda: None)
    assert SAB.unregister_stale("vault_判据", "k#%", ["a#0"]) == -1


def test_unregister_stale_rejects_bad_args(monkeypatch):
    """入参之守：空 file_path_like ⇒ 拒 ／ keep_names=None ⇒ 拒（**皆 ⛔ 触库**）。"""
    from core.lib import sag_audit_bridge as SAB

    monkeypatch.setattr(SAB, "_exec_delete", lambda sql, params: pytest.fail("⛔ 不应触库"))
    assert SAB.unregister_stale("t", "", ["a#0"]) == -1
    assert SAB.unregister_stale("t", None, ["a#0"]) == -1
    assert SAB.unregister_stale("t", "k#%", None) == -1


def test_unregister_stale_sql_shape(monkeypatch):
    """keep 非空 ⇒ 带 `NOT IN`；keep **空表合法**（件结成空）⇒ ⛔ 带（免 `NOT IN ()` 之语法错）。"""
    from core.lib import sag_audit_bridge as SAB

    seen = []

    def _cap(sql, params):
        seen.append((sql, params))
        return 3

    monkeypatch.setattr(SAB, "_exec_delete", _cap)
    assert SAB.unregister_stale("vault_判据", "k#%", ["a#0", "a#1"]) == 3
    sql, params = seen[-1]
    assert "NOT IN" in sql and params[3] == ("a#0", "a#1")
    assert len(params) == 4

    assert SAB.unregister_stale("vault_判据", "k#%", []) == 3
    sql, params = seen[-1]
    assert "NOT IN" not in sql, "空表 ⛔ 得拼 NOT IN（Postgres `NOT IN ()` 为语法错）"
    assert len(params) == 3


def test_unregister_entity_key_matches_register(monkeypatch):
    """注销之键与 register_entity 同（`UNIQUE(project_id, entity_name, file_path)`）。"""
    from core.lib import sag_audit_bridge as SAB

    seen = []
    monkeypatch.setattr(SAB, "_exec_delete",
                        lambda sql, params: (seen.append((sql, params)), 1)[1])
    assert SAB.unregister_entity("vault_doc", "a.md", "vault/a.md") is True
    sql, params = seen[-1]
    for col in ("project_id", "entity_type", "entity_name", "file_path"):
        assert col in sql, col
    assert params == ("default", "vault_doc", "a.md", "vault/a.md")


def test_delete_code_entities_single_place():
    """⭐ 一处定形：全仓「删 `code_entities`」之 SQL **唯** `core/lib/sag_audit_bridge.py`。

    ⚠ 断言之字面须**拆写**（`"DELETE" + " FROM ..."`）—— 合写即自破（本齿扫 `tests/**`）。
    """
    import glob

    lit = "DELETE" + " FROM code_entities"
    hits = []
    for base in ("core", "scripts", "tools", "tests"):
        for path in glob.glob(os.path.join(base, "**", "*.py"), recursive=True):
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if lit in text:
                hits.append(path.replace(os.sep, "/"))
    assert hits == ["core/lib/sag_audit_bridge.py"], hits
