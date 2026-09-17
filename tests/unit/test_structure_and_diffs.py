"""P2 结构记忆刷新 + P3 文件 diff 历史"""
import json
import os
import sys
import time

sys.path.insert(0, ".")
from pathlib import Path

import pytest


@pytest.fixture
def sandbox(tmp_path):
    sb = tmp_path / "clawsjoy_dev"
    (sb / "data" / "output").mkdir(parents=True)
    (sb / "core").mkdir()
    (sb / "goals").mkdir()
    (sb / ".git").mkdir()
    (sb / "data" / "diffs").mkdir(parents=True)
    (sb / "data" / "output" / "简报.md").write_text("v1", encoding="utf-8")
    (sb / "core" / "app.py").write_text("x", encoding="utf-8")
    (sb / "config.yaml").write_text("x", encoding="utf-8")
    # diff 历史
    (sb / "data" / "diffs" / "20260819_100000_简报.md.diff").write_text("diff v1", encoding="utf-8")
    (sb / "data" / "diffs" / "20260819_110000_简报.md.diff").write_text("diff v2", encoding="utf-8")
    return sb


def test_refresh_project_structure(sandbox, monkeypatch):
    """结构记忆: 扫描沙箱根, 排除隐藏/goals; 更新 ContextManager"""
    import core.lib.context_manager as cm
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    captured = {}

    class _FakeCtx:
        def update_project_structure(self, struct):
            captured["struct"] = struct
            return struct

    monkeypatch.setattr(cm, "get_context", lambda uid="default": _FakeCtx())

    gh._refresh_project_structure("u1", "s1")
    s = captured["struct"]
    assert "data" in s["dirs"] and "core" in s["dirs"]
    assert "goals" not in s["dirs"] and ".git" not in s["dirs"]
    assert "config.yaml" in s["files"]


def test_files_list_excludes_diffs(sandbox, monkeypatch):
    """文件列表排除 data/diffs(内部 diff 产物)"""
    from core.gateway.file_center import _scan_session_files

    files = _scan_session_files(sandbox)
    assert not any(f["path"].startswith("data/diffs") for f in files)
    assert "简报.md" in {f["name"] for f in files}


def test_diffs_route(sandbox, monkeypatch):
    """GET /v9/files/diffs: 按 basename 匹配, 时间倒序"""
    import agent_gateway_enhanced as main
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    client = main.app.test_client()
    d = client.get("/v9/files/diffs?user_id=u1&session_id=s1&path=data/output/简报.md").get_json()
    assert d["success"] is True
    assert len(d["diffs"]) == 2
    # 时间倒序: 110000 在前
    assert d["diffs"][0]["diff"] == "diff v2"
    assert d["diffs"][1]["diff"] == "diff v1"
    # 不匹配的文件名 → 空
    d2 = client.get("/v9/files/diffs?user_id=u1&session_id=s1&path=other.txt").get_json()
    assert d2["success"] is True and d2["diffs"] == []
    # 缺 path → 错误
    d3 = client.get("/v9/files/diffs?user_id=u1&session_id=s1").get_json()
    assert d3["success"] is False
