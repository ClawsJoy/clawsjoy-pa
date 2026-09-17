"""链接抓全文后端测试: /v9/fetch(复用 fetch_web 护栏) + /v9/files/save(存沙箱 data/reports)"""
import json
import sys

sys.path.insert(0, ".")
from pathlib import Path

import pytest


def _client(monkeypatch, sandbox):
    import agent_gateway_enhanced as main
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    return main.app.test_client()


# ===== /v9/fetch =====


def test_fetch_returns_content(monkeypatch):
    """GET /v9/fetch?url= → 正文/标题/URL(FetchWebPlugin 真实护栏)"""
    import agent_gateway_enhanced as main
    import core.tools.fetch_web as fw

    monkeypatch.setattr(
        fw.FetchWebPlugin,
        "execute",
        lambda self, args, ctx: {
            "success": True,
            "url": "https://example.com/news/x",
            "content": "正文内容 abc",
            "truncated": False,
            "length": 6,
        },
    )
    client = main.app.test_client()
    d = client.get("/v9/fetch?url=https://example.com/news/x").get_json()
    assert d["success"] is True
    assert d["content"] == "正文内容 abc"
    assert d["title"]  # 从 URL 推断标题
    assert d["url"] == "https://example.com/news/x"


def test_fetch_missing_url():
    import agent_gateway_enhanced as main

    d = main.app.test_client().get("/v9/fetch").get_json()
    assert d["success"] is False and "url" in d["error"]


def test_fetch_failure_propagates(monkeypatch):
    """抓取失败(SSRF/超时等) → success=false + error 透传"""
    import agent_gateway_enhanced as main
    import core.tools.fetch_web as fw

    monkeypatch.setattr(
        fw.FetchWebPlugin,
        "execute",
        lambda self, args, ctx: {
            "success": False,
            "error": "localhost/内网地址不允许访问",
        },
    )
    d = main.app.test_client().get("/v9/fetch?url=http://127.0.0.1:8080").get_json()
    assert d["success"] is False
    assert "内网" in d["error"]


# ===== /v9/files/save =====


def test_save_creates_md_in_reports(tmp_path, monkeypatch):
    """POST /v9/files/save → 沙箱 data/reports/{filename}.md + 返回文件记录"""
    sb = tmp_path / "clawsjoy_dev"
    sb.mkdir(parents=True)
    client = _client(monkeypatch, sb)
    r = client.post(
        "/v9/files/save",
        json={
            "user_id": "u1",
            "session_id": "s1",
            "filename": "DeepSeek 新闻",
            "content": "# 正文\n内容",
        },
    )
    d = r.get_json()
    assert d["success"] is True
    assert d["file"]["name"] == "DeepSeek 新闻.md"
    assert d["file"]["path"] == "data/reports/DeepSeek 新闻.md"
    f = sb / "data" / "reports" / "DeepSeek 新闻.md"
    assert f.exists()
    assert "正文" in f.read_text(encoding="utf-8")


def test_save_forces_md_suffix(tmp_path, monkeypatch):
    """无 .md 后缀自动补; 已有 .md 不重复"""
    sb = tmp_path / "clawsjoy_dev"
    sb.mkdir(parents=True)
    client = _client(monkeypatch, sb)
    r1 = client.post("/v9/files/save", json={"user_id": "u1", "session_id": "s1", "filename": "a.txt", "content": "x"})
    assert r1.get_json()["file"]["name"] == "a.md"
    r2 = client.post("/v9/files/save", json={"user_id": "u1", "session_id": "s1", "filename": "b.md", "content": "x"})
    assert r2.get_json()["file"]["name"] == "b.md"


def test_save_blocks_path_traversal(tmp_path, monkeypatch):
    """filename 含 ../ 只取 basename(防穿越)"""
    sb = tmp_path / "clawsjoy_dev"
    sb.mkdir(parents=True)
    client = _client(monkeypatch, sb)
    r = client.post(
        "/v9/files/save",
        json={
            "user_id": "u1",
            "session_id": "s1",
            "filename": "../../etc/passwd",
            "content": "x",
        },
    )
    d = r.get_json()
    assert d["success"] is True
    assert d["file"]["name"] == "passwd.md"
    assert ".." not in d["file"]["path"]


def test_save_missing_params(tmp_path, monkeypatch):
    sb = tmp_path / "clawsjoy_dev"
    sb.mkdir(parents=True)
    client = _client(monkeypatch, sb)
    d1 = client.post("/v9/files/save", json={"user_id": "u1", "filename": "x", "content": "y"}).get_json()
    assert d1["success"] is False and "session_id" in d1["error"]
    d2 = client.post("/v9/files/save", json={"user_id": "u1", "session_id": "s1", "content": "y"}).get_json()
    assert d2["success"] is False and "filename" in d2["error"]


def test_save_content_over_limit(tmp_path, monkeypatch):
    """>200KB 内容拒绝"""
    sb = tmp_path / "clawsjoy_dev"
    sb.mkdir(parents=True)
    client = _client(monkeypatch, sb)
    d = client.post(
        "/v9/files/save",
        json={
            "user_id": "u1",
            "session_id": "s1",
            "filename": "big",
            "content": "x" * (201 * 1024),
        },
    ).get_json()
    assert d["success"] is False and "超限" in d["error"]
