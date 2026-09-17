# -*- coding: utf-8 -*-
"""Windows 客户端改造回归: browser channel/user_data_dir"""
import importlib.util
import sys

sys.path.insert(0, ".")


def _load_browser_module():
    spec = importlib.util.spec_from_file_location("agent_browser_mod", "scripts/agent_client/browser.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_pw_factory(captured):
    """构造 FakePW: 捕获 launch_persistent_context 参数"""

    class FakeCtx:
        def add_cookies(self, ck):
            pass

    class FakeChromium:
        @staticmethod
        def launch_persistent_context(ud, **kw):
            captured["ud"] = ud
            captured["kw"] = kw
            return FakeCtx()

    class FakePW:
        def start(self):
            return self

        chromium = FakeChromium

    return FakePW


def test_resolve_user_data_dir_default(tmp_path):
    B = _load_browser_module()
    b = B.BrowserSession(str(tmp_path))
    assert b._resolve_user_data_dir() == str(tmp_path / "default")


def test_resolve_user_data_dir_explicit(tmp_path):
    B = _load_browser_module()
    custom = tmp_path / "my_chrome_data"
    b = B.BrowserSession(str(tmp_path), user_data_dir=str(custom))
    assert b._resolve_user_data_dir() == str(custom)
    assert (tmp_path / "default").exists() is False


def test_channel_and_ud_passed_to_launch(tmp_path, monkeypatch):
    import playwright.sync_api as P

    captured = {}
    monkeypatch.setattr(P, "sync_playwright", lambda: _fake_pw_factory(captured)())
    B = _load_browser_module()
    b = B.BrowserSession(str(tmp_path), channel="chrome", user_data_dir=str(tmp_path / "win_data"))
    b._inject_cookies = lambda: None
    b._profile_locked = lambda: False
    b.start()
    assert captured["ud"] == str(tmp_path / "win_data")
    assert captured["kw"].get("channel") == "chrome"


def test_no_channel_uses_default(tmp_path, monkeypatch):
    import playwright.sync_api as P

    captured = {}
    monkeypatch.setattr(P, "sync_playwright", lambda: _fake_pw_factory(captured)())
    B = _load_browser_module()
    b = B.BrowserSession(str(tmp_path))
    b._inject_cookies = lambda: None
    b._profile_locked = lambda: False
    b.start()
    assert "channel" not in captured["kw"]
    assert captured["ud"] == str(tmp_path / "default")
