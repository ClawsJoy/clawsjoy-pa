"""网关路由测试

覆盖:
- GET  /health               健康检查
- POST /v9/sandbox/list      沙箱目录列表
- POST /v9/sandbox/search    沙箱内容搜索
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_gateway_enhanced import app


def _client():
    app.config["TESTING"] = True
    return app.test_client()


def test_health():
    """GET /health 应返回 200 且 status 为 healthy/starting"""
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] in ("healthy", "starting")
    assert data["version"] == "6.0.0"
    assert "startup" in data
    assert "hardware" in data


def test_v9_sandbox_list():
    """POST /v9/sandbox/list 应返回 200 且 success 为 True"""
    client = _client()
    resp = client.post(
        "/v9/sandbox/list",
        json={
            "user_id": "test_user",
            "session_id": "test_session",
            "path": ".",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    # 搜索 API 返回文件列表结构（dirs/files/_project_prefix），非 success 包装
    assert isinstance(data, dict)
    assert "dirs" in data or "files" in data


def test_v9_sandbox_search():
    """POST /v9/sandbox/search 应返回 200 且 success 为 True"""
    client = _client()
    resp = client.post(
        "/v9/sandbox/search",
        json={
            "user_id": "test_user",
            "session_id": "test_session",
            "query": "conftest",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    # 搜索 API 返回文件列表结构（dirs/files/_project_prefix），非 success 包装
    assert isinstance(data, dict)
    assert "_project_prefix" in data
