"""R1 P1b: query_index entity_type 统一检索入口"""
import sys
sys.path.insert(0, ".")
import pytest


def test_entity_type_route_to_sag(monkeypatch):
    """带 entity_type → 走 SAG 检索分支（mock query_entities）"""
    from core.tools.query_index import QueryIndexPlugin
    import core.lib.sag_audit_bridge as SAB
    captured = {}
    def fake_query(entity_type=None, query=None, limit=50, project_id="default"):
        captured["entity_type"] = entity_type
        captured["query"] = query
        captured["limit"] = limit
        return [{
            "entity_type": entity_type, "entity_name": "write_file",
            "signature": "success=True", "file_path": "sess_x",
            "related_entities": ["u_x"],
        }]
    monkeypatch.setattr(SAB, "query_entities", fake_query)
    plugin = QueryIndexPlugin()
    class Ctx:
        code_indexer = None
        messages = []
        user_id = "u"
        session_id = "s"
        query_empty_cache = {}
    res = plugin.execute({"query": "审计", "entity_type": "audit_event"}, Ctx())
    assert res.get("source") == "sag"
    assert captured["entity_type"] == "audit_event"
    assert captured["query"] == "审计"
    assert captured["limit"] == 20
    assert res["results"][0]["entity_name"] == "write_file"


def test_entity_type_empty_results(monkeypatch):
    """SAG 无结果 → source=sag + results=[]（不误报失败）"""
    from core.tools.query_index import QueryIndexPlugin
    import core.lib.sag_audit_bridge as SAB
    monkeypatch.setattr(SAB, "query_entities", lambda **kw: [])
    plugin = QueryIndexPlugin()
    class Ctx:
        code_indexer = None
        messages = []
        user_id = "u"
        session_id = "s"
        query_empty_cache = {}
    res = plugin.execute({"query": "不存在", "entity_type": "goal"}, Ctx())
    assert res.get("success") is True
    assert res.get("results") == []
    assert res.get("source") == "sag"


def test_no_entity_type_falls_back_to_code():
    """无 entity_type → 走原代码索引逻辑（不破坏现状）"""
    from core.tools.query_index import QueryIndexPlugin
    plugin = QueryIndexPlugin()
    class Ctx:
        code_indexer = None
        messages = []
        user_id = "u"
        session_id = "s"
        query_empty_cache = {}
    res = plugin.execute({"query": "xxx"}, Ctx())
    assert res.get("success") is False
    assert "代码索引" in res.get("error", "")
