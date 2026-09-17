"""Integration tests for video_studio timeline and export workflow"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from unittest.mock import patch, MagicMock
from flask import Flask


class TestTimelineExportWorkflow:
    """时间线与导出工作流集成测试"""

    @patch("web.api.video_studio_api.Path.exists")
    @patch("web.api.video_studio_api.subprocess.run")
    def test_full_export_workflow(self, mock_run, mock_exists):
        """测试完整导出工作流：创建项目->导入视频->导出"""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        mock_exists.return_value = True

        app = Flask(__name__)
        from web.api.video_studio_api import video_studio_bp
        app.register_blueprint(video_studio_bp)
        app.config["TESTING"] = True
        client = app.test_client()

        # Step 1: Create project
        resp = client.post("/api/video-studio/projects", json={
            "name": "导出测试项目",
            "duration": 30.0,
        })
        assert resp.status_code == 201
        project = resp.get_json()["project"]
        project_id = project["id"]
        assert project["name"] == "导出测试项目"

        # Step 2: Get project timeline
        resp = client.get(f"/api/video-studio/timeline/{project_id}")
        assert resp.status_code == 200
        timeline = resp.get_json()["timeline"]
        assert timeline["duration"] == 30.0

        # Step 3: Export video
        resp = client.post("/api/video-studio/export", json={
            "project_id": project_id,
            "format": "mp4",
            "resolution": "1280x720",
            "bitrate": "2M",
            "fps": 24,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["task_id"].startswith("task-")
        assert data["status"] == "completed"

    def test_export_invalid_format(self):
        """测试使用无效格式导出"""
        app = Flask(__name__)
        from web.api.video_studio_api import video_studio_bp
        app.register_blueprint(video_studio_bp)
        app.config["TESTING"] = True
        client = app.test_client()

        resp = client.post("/api/video-studio/export", json={
            "project_id": "proj-001",
            "format": "avi",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False
        assert "不支持的格式" in data["error"]

    def test_export_invalid_resolution(self):
        """测试使用无效分辨率导出"""
        app = Flask(__name__)
        from web.api.video_studio_api import video_studio_bp
        app.register_blueprint(video_studio_bp)
        app.config["TESTING"] = True
        client = app.test_client()

        resp = client.post("/api/video-studio/export", json={
            "project_id": "proj-001",
            "resolution": "invalid",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False
        assert "无效的分辨率" in data["error"]


if __name__ == "__main__":
    t = TestTimelineExportWorkflow()

    app = Flask(__name__)
    from web.api.video_studio_api import video_studio_bp
    app.register_blueprint(video_studio_bp)
    app.config["TESTING"] = True

    tests = [
        ("test_full_export_workflow",
         lambda: t.test_full_export_workflow()),
        ("test_export_invalid_format",
         lambda: t.test_export_invalid_format()),
        ("test_export_invalid_resolution",
         lambda: t.test_export_invalid_resolution()),
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
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败")
    sys.exit(0 if failed == 0 else 1)
