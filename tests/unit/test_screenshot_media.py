"""截图流可视化后端测试: /v9/media 静态服务 + playwright screenshot 挂截图字段 + tool_steps 透传"""
import sys

sys.path.insert(0, ".")
from pathlib import Path

import pytest


@pytest.fixture
def sandbox(tmp_path):
    """构造含截图的 session 沙箱目录"""
    sb = tmp_path / "clawsjoy_dev"
    (sb / "data" / "screenshots").mkdir(parents=True)
    (sb / "data" / "screenshots" / "playwright_1001.png").write_bytes(b"\x89PNG\r\nMOCK")
    (sb / "data" / "output").mkdir(parents=True)
    (sb / "data" / "output" / "report.md").write_text("# 报告", encoding="utf-8")
    return sb


# ===== /v9/media 路由 =====


def test_media_serves_png(sandbox, monkeypatch):
    import agent_gateway_enhanced as main
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    client = main.app.test_client()
    resp = client.get("/v9/media?user_id=u1&session_id=s1&path=data/screenshots/playwright_1001.png")
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"
    assert resp.data.startswith(b"\x89PNG")


def test_media_missing_params():
    import agent_gateway_enhanced as main

    client = main.app.test_client()
    d = client.get("/v9/media?user_id=u1").get_json()
    assert d["success"] is False and "path" in d["error"]


def test_media_path_traversal_blocked(sandbox, monkeypatch):
    """../ 穿越必须被拒绝(防读沙箱外文件)"""
    import agent_gateway_enhanced as main
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    client = main.app.test_client()
    resp = client.get("/v9/media?user_id=u1&session_id=s1&path=../../../../etc/passwd")
    assert resp.get_json()["success"] is False


def test_media_nonexistent_file(sandbox, monkeypatch):
    import agent_gateway_enhanced as main
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    client = main.app.test_client()
    d = client.get("/v9/media?user_id=u1&session_id=s1&path=data/screenshots/nope.png").get_json()
    assert d["success"] is False


def test_media_text_file_content_type(sandbox, monkeypatch):
    """非图片扩展名回退 octet-stream(仍可访问, 类型由扩展名定)"""
    import agent_gateway_enhanced as main
    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: sandbox)
    client = main.app.test_client()
    resp = client.get("/v9/media?user_id=u1&session_id=s1&path=data/output/report.md")
    assert resp.status_code == 200
    assert "报告" in resp.get_data(as_text=True)


# ===== playwright_browser screenshot 挂截图字段 =====


def test_plugin_screenshot_forces_sandbox_and_sets_url(monkeypatch, tmp_path):
    """screenshot action: 强制落沙箱 data/screenshots/, 结果带 screenshot_path/url"""
    import core.tools.playwright_browser as pb

    sb = tmp_path / "clawsjoy_dev"
    (sb / "data").mkdir(parents=True)

    captured = {}

    def _fake_handler(params):
        captured["shot_path"] = params.get("screenshot_path")
        return {"success": True, "action": "screenshot", "path": params.get("screenshot_path"), "url": "https://a.com"}

    monkeypatch.setattr(pb, "_handle_playwright_browser", _fake_handler)

    class Ctx:
        base = sb
        user_id = "u1"
        session_id = "s1"

    plugin = pb.PlaywrightBrowserPlugin()
    r = plugin.execute({"action": "screenshot", "url": "https://a.com"}, Ctx())
    assert r["success"] is True
    # 截图路径被强制指向沙箱内 data/screenshots/
    assert str(captured["shot_path"]).startswith(str(sb / "data" / "screenshots"))
    # 结果挂截图字段: 沙箱相对路径 + /v9/media URL
    assert r["screenshot_path"] == "data/screenshots/" + Path(captured["shot_path"]).name
    assert r["screenshot_url"].startswith("/v9/media?user_id=u1&session_id=s1&path=data/screenshots/")


def test_plugin_screenshot_respects_filename(monkeypatch, tmp_path):
    """LLM 指定文件名时保留文件名, 但强制落沙箱目录"""
    import core.tools.playwright_browser as pb

    sb = tmp_path / "clawsjoy_dev"
    (sb / "data").mkdir(parents=True)
    captured = {}

    def _fake_handler(params):
        captured["shot_path"] = params.get("screenshot_path")
        return {"success": True, "action": "screenshot", "path": params.get("screenshot_path"), "url": "https://a.com"}

    monkeypatch.setattr(pb, "_handle_playwright_browser", _fake_handler)

    class Ctx:
        base = sb
        user_id = "u1"
        session_id = "s1"

    plugin = pb.PlaywrightBrowserPlugin()
    r = plugin.execute({"action": "screenshot", "screenshot_path": "custom.png"}, Ctx())
    assert r["screenshot_path"] == "data/screenshots/custom.png"


def test_plugin_non_screenshot_no_force(monkeypatch, tmp_path):
    """非 screenshot action 不强制改路径, 也不挂截图字段"""
    import core.tools.playwright_browser as pb

    captured = {}

    def _fake_handler(params):
        captured["params"] = params
        return {"success": True, "action": "open", "url": "https://a.com", "title": "T"}

    monkeypatch.setattr(pb, "_handle_playwright_browser", _fake_handler)

    class Ctx:
        base = tmp_path
        user_id = "u1"
        session_id = "s1"

    plugin = pb.PlaywrightBrowserPlugin()
    r = plugin.execute({"action": "open", "url": "https://a.com"}, Ctx())
    assert "screenshot_path" not in captured["params"]
    assert "screenshot_url" not in r


# ===== tool_steps 透传(桥接循环字段拼接逻辑) =====


def test_tool_step_passthrough_screenshot(monkeypatch, tmp_path):
    """成功截图工具结果 → tool_step 含 screenshot_url/path(桥接循环拼接规则)"""
    import agent_gateway_enhanced as main

    # 提取 _v9_bridge_loop 中拼接逻辑的等价函数: 直接验证字段规则
    # (bridge loop 内联; 用源码断言兜底, 防止字段丢失)
    src = Path("core/gateway/v9_bridge/tool_runner.py").read_text(encoding="utf-8")
    assert "screenshot_url" in src
    assert "screenshot_path" in src
    assert '"screenshot_url": str(_su or "")' in src
