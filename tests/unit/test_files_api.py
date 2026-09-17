"""文件中心 API 单测: 沙箱文件扫描/排除/排序/过滤 + 路由(content/download)"""
import json
import os
import sys
import time

sys.path.insert(0, ".")
from pathlib import Path

import pytest


@pytest.fixture
def sandbox(tmp_path):
    """构造一个带产出文件的 session 沙箱目录"""
    sb = tmp_path / "clawsjoy_dev"
    (sb / "data" / "output").mkdir(parents=True)
    (sb / ".git").mkdir(parents=True)
    (sb / "goals").mkdir()
    (sb / "data" / "v8").mkdir(parents=True)
    # 产出文件(不同 mtime 用于排序)
    f1 = sb / "data" / "output" / "简报.md"
    f1.write_text("# 今日 AI 简报\n正文", encoding="utf-8")
    os.utime(f1, (time.time() - 300, time.time() - 300))
    f2 = sb / "data" / "output" / "notes.txt"
    f2.write_text("notes", encoding="utf-8")
    os.utime(f2, (time.time() - 100, time.time() - 100))
    f3 = sb / "screenshot_1.png"
    f3.write_bytes(b"\x89PNG")
    os.utime(f3, (time.time() - 50, time.time() - 50))
    # 内部文件(应排除)
    (sb / ".agent_state.json").write_text("{}", encoding="utf-8")
    (sb / "goals" / "goal_x.json").write_text("{}", encoding="utf-8")
    (sb / "data" / "v8" / "internal.json").write_text("{}", encoding="utf-8")
    (sb / ".git" / "config").write_text("", encoding="utf-8")
    return sb


def _scan(sandbox, **kw):
    from core.gateway.file_center import _scan_session_files

    return _scan_session_files(sandbox, **kw)


def test_scan_lists_produced_files(sandbox):
    files = _scan(sandbox)
    names = {f["name"] for f in files}
    assert "简报.md" in names and "notes.txt" in names and "screenshot_1.png" in names
    for f in files:
        assert {"id", "name", "path", "size", "modified_at", "preview_url"} <= set(f.keys()), f


def test_scan_excludes_internal(sandbox):
    files = _scan(sandbox)
    names = {f["name"] for f in files}
    assert ".agent_state.json" not in names
    assert not any(f["path"].startswith("goals/") for f in files)
    assert not any(f["path"].startswith("data/v8/") for f in files)
    assert not any(f["path"].startswith(".git") for f in files)
    assert not any(f["path"].startswith(".") for f in files)


def test_scan_sorted_by_modified_desc(sandbox):
    files = _scan(sandbox)
    mtimes = [f["modified_at"] for f in files]
    assert mtimes == sorted(mtimes, reverse=True), "应按 modified_at 倒序"


def test_scan_limit(sandbox):
    files = _scan(sandbox, limit=2)
    assert len(files) == 2


def test_scan_ext_filter(sandbox):
    files = _scan(sandbox, ext=".md,.txt")
    assert {f["name"] for f in files} == {"简报.md", "notes.txt"}


def test_scan_type_filters(sandbox):
    shots = _scan(sandbox, type_="screenshot")
    assert {f["name"] for f in shots} == {"screenshot_1.png"}
    reports = _scan(sandbox, type_="report")
    assert "简报.md" in {f["name"] for f in reports} and "notes.txt" in {f["name"] for f in reports}


def test_scan_missing_dir(tmp_path):
    assert _scan(tmp_path / "nonexistent") == []


def test_route_list_and_content(sandbox, monkeypatch):
    """GET /v9/files + /v9/files/content 走真实路由"""
    import agent_gateway_enhanced as main
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    client = main.app.test_client()

    resp = client.get("/v9/files?user_id=u1&session_id=s1")
    d = resp.get_json()
    assert d["success"] is True
    assert len(d["files"]) == 3
    md = next(f for f in d["files"] if f["name"] == "简报.md")
    # preview_url 带 user/session 上下文(content 路由需要)
    assert md["preview_url"].startswith("/v9/files/content?user_id=u1&session_id=s1&id=")

    # content 预览(直接用 preview_url)
    c = client.get(md["preview_url"])
    assert c.status_code == 200
    assert "今日 AI 简报" in c.get_data(as_text=True)

    # 缺 session_id → 错误
    bad = client.get("/v9/files?user_id=u1")
    assert bad.get_json()["success"] is False


def test_route_missing_session_returns_error(monkeypatch):
    import agent_gateway_enhanced as main

    client = main.app.test_client()
    d = client.get("/v9/files?user_id=u1").get_json()
    assert d["success"] is False and "session_id" in d["error"]
