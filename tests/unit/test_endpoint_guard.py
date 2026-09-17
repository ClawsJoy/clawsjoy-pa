# -*- coding: utf-8 -*-
"""端点强制门测试（2026-09-10）

事故驱动: 批量探测路由时对每个路径盲发 POST {}, 其中 POST /kv/clear 清空了
灵犀插件配置库 8 条。本测试锁死"再来一次也拦得住"。
"""
import sys

sys.path.insert(0, ".")
import pytest
from flask import Flask

from core.pa import endpoint_guard as G
from core.pa.gateway_routes import register_pa_routes


# ---- 分级 ----
@pytest.mark.parametrize(
    "method,path,level",
    [
        ("GET", "/kv/all", "read"),
        ("GET", "/mcp/status", "read"),
        ("POST", "/doc-snapshot", "read"),
        ("POST", "/kv/batch", "write"),
        ("POST", "/mcp/register", "write"),
        ("POST", "/kv/clear", "destructive"),
        ("POST", "/doc-restore", "destructive"),
        ("POST", "/totally/unknown", "unknown"),
    ],
)
def test_classify(method, path, level):
    assert G.classify(method, path) == level


# ---- MCP 桥工具分级 (2026-09-13, C 块) ----
# /mcp/call 是灵犀桥唯一执行入口, 风险由 body.name(工具名) 决定, 不由路径决定。
@pytest.mark.parametrize(
    "tool,level",
    [
        ("wpp_get_presentation_info", "read"),
        ("wpp_export_slide_as_image", "read"),
        ("wpp_export_pdf", "read"),
        ("wpp_list_slides", "read"),
        ("wpp_render_html_template", "write"),
        ("wpp_save", "write"),
        ("wpp_save_as", "write"),
        ("wpp_delete_slide", "destructive"),
        ("wpp_delete_shape", "destructive"),
        ("smash_everything", "unknown"),
    ],
)
def test_classify_mcp_tool(tool, level):
    assert G.classify("POST", "/mcp/call", {"name": tool}) == level


def test_mcp_export_allowed_through_gate():
    """C 块正题: 导出缩略图必须能过门 —— 否则 PA 只能绕过门直连 3890"""
    allowed, level, _ = G.check("POST", "/mcp/call", "u", {"name": "wpp_export_slide_as_image"})
    assert allowed is True and level == "read"


def test_mcp_delete_slide_blocked_without_approval():
    """同一个端点, 换个工具名就该被拦 —— 分级看的是工具, 不是路径"""
    allowed, level, reason = G.check("POST", "/mcp/call", "u", {"name": "wpp_delete_slide"})
    assert allowed is False and level == "destructive" and "授权" in reason
    # 在场授权后放行, 且授权按**工具名**隔离(授了 delete_slide 不等于能 undo_full_deck_batch)
    G.approve_destructive("u_c", "/mcp/call#wpp_delete_slide", ttl_s=600, note="test")
    try:
        assert G.check("POST", "/mcp/call", "u_c", {"name": "wpp_delete_slide"})[0] is True
        assert G.check("POST", "/mcp/call", "u_c", {"name": "wpp_undo_full_deck_batch"})[0] is False
    finally:
        G.revoke("u_c")


def test_mcp_unknown_tool_default_deny():
    """未登记工具名仍走"拒绝是默认值", 门没被 /mcp/call 这条路径整体放开"""
    allowed, level, _ = G.check("POST", "/mcp/call", "u", {"name": "no_such_tool"})
    assert allowed is False and level == "unknown"
    # 不带 body 的盲发同样拒绝(事故复现路径)
    assert G.check("POST", "/mcp/call", "u", None)[0] is False


# ---- 核心契约: 事故复现必须被拦 ----
def test_kv_clear_blocked_without_approval():
    """事故原样重放: POST /kv/clear 无授权 -> 必须拒绝"""
    allowed, level, reason = G.check("POST", "/kv/clear", "u")
    assert allowed is False
    assert level == "destructive"
    assert "授权" in reason


def test_unknown_post_default_deny():
    """今天真正的坑: 对未知端点盲发 POST。现在默认拒绝。"""
    allowed, level, _ = G.check("POST", "/some/unregistered/path", "u")
    assert allowed is False and level == "unknown"


def test_unknown_get_allowed():
    """只读探测仍然放行 —— 不能因为加固就把能力发现也堵死"""
    allowed, _, _ = G.check("GET", "/some/unregistered/path", "u")
    assert allowed is True


def test_destructive_allowed_after_presence_approval():
    G.approve_destructive("u2", "/kv/clear", ttl_s=600, note="test")
    try:
        assert G.check("POST", "/kv/clear", "u2")[0] is True
        # 授权按端点隔离: 授了 /kv/clear 不等于能 /doc-restore
        assert G.check("POST", "/doc-restore", "u2")[0] is False
    finally:
        G.revoke("u2")


def test_approval_expires():
    G.approve_destructive("u3", "/kv/clear", ttl_s=-1)
    try:
        assert G.check("POST", "/kv/clear", "u3")[0] is False
    finally:
        G.revoke("u3")


# ---- 路由层: 门必须无法绕过 ----
@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    register_pa_routes(app)
    return app.test_client()


def test_route_blocks_destructive(client):
    """走 HTTP 也一样拦 —— PA 不允许直连 3890"""
    r = client.post("/v9/pa/proxy", json={"user_id": "u9", "method": "POST", "path": "/kv/clear"})
    assert r.status_code == 403
    d = r.get_json()
    assert d["ok"] is False and d["blocked_by"] == "endpoint_guard"


def test_route_blocks_unknown_post(client):
    r = client.post("/v9/pa/proxy", json={"user_id": "u9", "method": "POST", "path": "/anything/new"})
    assert r.status_code == 403


def test_route_requires_path(client):
    r = client.post("/v9/pa/proxy", json={"user_id": "u9"})
    assert r.status_code == 400


def test_gate_and_approve_roundtrip(client):
    assert client.get("/v9/pa/proxy/gate?user_id=u9").get_json()["approved"] is False
    client.post("/v9/pa/proxy/approve", json={"user_id": "u9", "path": "/kv/clear", "ttl_s": 300})
    assert client.get("/v9/pa/proxy/gate?user_id=u9").get_json()["approved"] is True
    client.post("/v9/pa/proxy/approve", json={"user_id": "u9", "revoke": True})
    assert client.get("/v9/pa/proxy/gate?user_id=u9").get_json()["approved"] is False
