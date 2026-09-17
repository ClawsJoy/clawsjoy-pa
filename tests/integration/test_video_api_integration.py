"""Integration tests for video_studio_api import endpoint"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import json
from unittest.mock import patch, MagicMock
from io import BytesIO

import pytest
from flask import Flask


@pytest.fixture
def app():
    """创建测试用 Flask 应用"""
    app = Flask(__name__)
    from web.api.video_studio_api import video_studio_bp
    app.register_blueprint(video_studio_bp)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestVideoImportAPI:
    """视频导入 API 集成测试"""

    def test_import_with_json(self, client):
        """测试通过 JSON 导入视频"""
        response = client.post(
            "/api/video-studio/import",
            json={"title": "测试视频", "duration": "30.0", "project_id": "proj-001"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["video_id"].startswith("vid-")
        assert data["filename"] == "untitled.mp4"
        assert data["metadata"]["title"] == "测试视频"

    def test_import_without_file(self, client):
        """测试不传文件的导入"""
        response = client.post(
            "/api/video-studio/import",
            json={"title": "无文件导入"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True

    def test_import_invalid_method(self, client):
        """测试使用 GET 方法"""
        response = client.get("/api/video-studio/import")
        assert response.status_code == 405  # Method Not Allowed


class TestVideoProjectsAPI:
    """项目 API 集成测试"""

    def test_list_projects(self, client):
        """测试获取项目列表"""
        response = client.get("/api/video-studio/projects")
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert "projects" in data
        # Should have at least the default project
        assert len(data["projects"]) >= 1

    def test_get_project_detail(self, client):
        """测试获取项目详情"""
        response = client.get("/api/video-studio/projects/proj-001")
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["project"]["id"] == "proj-001"

    def test_get_nonexistent_project(self, client):
        """测试获取不存在的项目"""
        response = client.get("/api/video-studio/projects/proj-999")
        assert response.status_code == 404
        data = response.get_json()
        assert data["ok"] is False

    def test_create_project(self, client):
        """测试创建新项目"""
        response = client.post(
            "/api/video-studio/projects",
            json={"name": "新项目", "duration": 60.0},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["ok"] is True
        assert data["project"]["name"] == "新项目"
        assert data["project"]["id"] != "proj-001"

    def test_delete_project(self, client):
        """测试删除项目"""
        # First create
        resp = client.post("/api/video-studio/projects", json={"name": "待删除"})
        proj_id = resp.get_json()["project"]["id"]

        # Then delete
        resp = client.delete(f"/api/video-studio/projects/{proj_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

        # Verify deleted
        resp = client.get(f"/api/video-studio/projects/{proj_id}")
        assert resp.status_code == 404


class TestVideoTimelineAPI:
    """时间线 API 集成测试"""

    def test_get_timeline(self, client):
        """测试获取项目时间线"""
        response = client.get("/api/video-studio/timeline/proj-001")
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert "timeline" in data
        assert len(data["timeline"]["tracks"]) == 2

    def test_update_timeline(self, client):
        """测试更新时间线"""
        new_timeline = {
            "duration": 60.0,
            "tracks": [
                {"id": "t1", "type": "video", "clips": [
                    {"id": "c1", "video_id": "vid-001", "file_path": "/tmp/test.mp4",
                     "start": 0.0, "end": 10.0}
                ]},
                {"id": "t2", "type": "audio", "clips": []},
            ],
        }
        response = client.put(
            "/api/video-studio/timeline/proj-001",
            json={"timeline": new_timeline},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["timeline"]["duration"] == 60.0
        assert len(data["timeline"]["tracks"][0]["clips"]) == 1

    def test_export_video_missing_project(self, client):
        """测试导出不存在的项目"""
        response = client.post(
            "/api/video-studio/export",
            json={"project_id": "proj-999"},
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data["ok"] is False


if __name__ == "__main__":
    import sys
    # Run tests manually
    app = Flask(__name__)
    from web.api.video_studio_api import video_studio_bp
    app.register_blueprint(video_studio_bp)
    app.config["TESTING"] = True
    client = app.test_client()

    tests = [
        ("VideoImportAPI.test_import_with_json",
         lambda: TestVideoImportAPI().test_import_with_json(client)),
        ("VideoImportAPI.test_import_without_file",
         lambda: TestVideoImportAPI().test_import_without_file(client)),
        ("VideoImportAPI.test_import_invalid_method",
         lambda: TestVideoImportAPI().test_import_invalid_method(client)),
        ("VideoProjectsAPI.test_list_projects",
         lambda: TestVideoProjectsAPI().test_list_projects(client)),
        ("VideoProjectsAPI.test_get_project_detail",
         lambda: TestVideoProjectsAPI().test_get_project_detail(client)),
        ("VideoProjectsAPI.test_get_nonexistent_project",
         lambda: TestVideoProjectsAPI().test_get_nonexistent_project(client)),
        ("VideoProjectsAPI.test_create_project",
         lambda: TestVideoProjectsAPI().test_create_project(client)),
        ("VideoProjectsAPI.test_delete_project",
         lambda: TestVideoProjectsAPI().test_delete_project(client)),
        ("VideoTimelineAPI.test_get_timeline",
         lambda: TestVideoTimelineAPI().test_get_timeline(client)),
        ("VideoTimelineAPI.test_update_timeline",
         lambda: TestVideoTimelineAPI().test_update_timeline(client)),
        ("VideoTimelineAPI.test_export_video_missing_project",
         lambda: TestVideoTimelineAPI().test_export_video_missing_project(client)),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败")
    sys.exit(0 if failed == 0 else 1)
