"""Integration tests for video_studio download and error handling"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from unittest.mock import patch, MagicMock
from flask import Flask


class TestDownloadErrorHandling:
    """下载与错误处理集成测试"""

    def test_download_nonexistent_task(self):
        """测试下载不存在的任务"""
        app = Flask(__name__)
        from web.api.video_studio_api import video_studio_bp
        app.register_blueprint(video_studio_bp)
        app.config["TESTING"] = True
        client = app.test_client()

        resp = client.get("/api/video-studio/download/task-999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False
        assert "导出任务不存在" in data["error"]

    def test_get_nonexistent_timeline(self):
        """测试获取不存在项目的时间线"""
        app = Flask(__name__)
        from web.api.video_studio_api import video_studio_bp
        app.register_blueprint(video_studio_bp)
        app.config["TESTING"] = True
        client = app.test_client()

        resp = client.get("/api/video-studio/timeline/proj-999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False

    def test_delete_nonexistent_project(self):
        """测试删除不存在的项目"""
        app = Flask(__name__)
        from web.api.video_studio_api import video_studio_bp
        app.register_blueprint(video_studio_bp)
        app.config["TESTING"] = True
        client = app.test_client()

        resp = client.delete("/api/video-studio/projects/proj-999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False

    def test_update_nonexistent_timeline(self):
        """测试更新不存在项目的时间线"""
        app = Flask(__name__)
        from web.api.video_studio_api import video_studio_bp
        app.register_blueprint(video_studio_bp)
        app.config["TESTING"] = True
        client = app.test_client()

        resp = client.put("/api/video-studio/timeline/proj-999", json={"timeline": {}})
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False

    def test_blueprint_routes_exist(self):
        """验证 Blueprint 所有路由已注册"""
        app = Flask(__name__)
        from web.api.video_studio_api import video_studio_bp
        app.register_blueprint(video_studio_bp)

        rules = [r.rule for r in app.url_map.iter_rules()
                 if '/api/video-studio' in r.rule]
        expected_endpoints = [
            "/api/video-studio/import",
            "/api/video-studio/export",
            "/api/video-studio/projects",
            "/api/video-studio/projects/<project_id>",
            "/api/video-studio/timeline/<project_id>",
            "/api/video-studio/download/<task_id>",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in rules, f"Missing route: {endpoint}"
        print(f"   所有 {len(expected_endpoints)} 个路由已注册")


if __name__ == "__main__":
    t = TestDownloadErrorHandling()

    tests = [
        ("test_download_nonexistent_task",
         lambda: t.test_download_nonexistent_task()),
        ("test_get_nonexistent_timeline",
         lambda: t.test_get_nonexistent_timeline()),
        ("test_delete_nonexistent_project",
         lambda: t.test_delete_nonexistent_project()),
        ("test_update_nonexistent_timeline",
         lambda: t.test_update_nonexistent_timeline()),
        ("test_blueprint_routes_exist",
         lambda: t.test_blueprint_routes_exist()),
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
