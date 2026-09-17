# -*- coding: utf-8 -*-
"""observe 功能回归: observe_start/stop 注入+日志+SOP 提炼"""
import importlib.util
import json
import sys

sys.path.insert(0, ".")


def _load_actions():
    spec = importlib.util.spec_from_file_location("agent_actions_obs", "scripts/agent_client/actions.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_observe_constants_present():
    """脚本常量存在且含核心监听器"""
    A = _load_actions()
    assert hasattr(A, "_OBSERVE_START_JS"), "缺 _OBSERVE_START_JS"
    assert hasattr(A, "_OBSERVE_STOP_JS"), "缺 _OBSERVE_STOP_JS"
    for kw in ("addEventListener", "type: 'click'", "type: 'input'", "type: 'api'", "__observe_log"):
        assert kw in A._OBSERVE_START_JS, "脚本缺 " + kw
    assert "__observe_log" in A._OBSERVE_STOP_JS


def test_observe_start_injects_and_stores():
    """observe_start: 注入脚本, 返回 observe_id, 存 _observe 状态"""
    A = _load_actions()

    class FakePage:
        def evaluate(self, expr):
            if expr.startswith("window.__observe_max ="):
                return None
            return {"started": True, "observe_id": "obs_test123"}

    import types

    obj = A.Actions.__new__(A.Actions)
    obj._frame_target = lambda page, frame: page
    obj._observe = None
    r = obj.observe_start(FakePage(), {"frame": 0, "max_actions": 100})
    assert r.get("success") is True, r
    assert r.get("observe_id") == "obs_test123", r
    assert obj._observe and obj._observe["observe_id"] == "obs_test123"


def test_observe_stop_returns_log():
    """observe_stop: 取回日志 JSON, 返回 actions + sop_draft"""
    A = _load_actions()
    log_json = json.dumps(
        [
            {"type": "navigate", "from": "a", "to": "https://creator.douyin.com/upload", "ts": 10},
            {"type": "click", "selector": "input[type=file][accept*='image/']", "text": "", "tag": "INPUT", "ts": 20},
            {"type": "input", "selector": "input[placeholder='添加作品标题']", "value": "AI刷题", "tag": "INPUT", "ts": 30},
            {"type": "click", "selector": "button:has-text('暂存')", "text": "暂存", "tag": "BUTTON", "ts": 40},
            {"type": "api", "method": "POST", "url": "https://creator.douyin.com/draft", "params": "x", "ts": 50},
        ]
    )

    class FakePage:
        def evaluate(self, expr):
            return log_json

    import types

    obj = A.Actions.__new__(A.Actions)
    obj._frame_target = lambda page, frame: page
    obj._observe = {"observe_id": "obs_test123", "start_ts": __import__("time").time() - 3}
    r = obj.observe_stop(FakePage(), {"frame": 0, "observe_id": "obs_test123"})
    assert r.get("success") is True, r
    assert r.get("action_count") == 5, r
    acts = r["actions"]
    assert acts[0]["type"] == "navigate" and acts[1]["type"] == "click", acts
    assert acts[2]["selector"] == "input[placeholder='添加作品标题']", acts
    steps = r["sop_draft"]["steps"]
    assert any("navigate(" in s for s in steps), steps
    assert any("input(input[placeholder" in s for s in steps), steps
    assert obj._observe is None, "observe 状态应清空"


def test_observe_id_mismatch():
    """observe_id 不匹配 → 报错"""
    A = _load_actions()

    class FakePage:
        def evaluate(self, expr):
            return "[]"

    import types

    obj = A.Actions.__new__(A.Actions)
    obj._frame_target = lambda page, frame: page
    obj._observe = {"observe_id": "obs_a", "start_ts": 1}
    r = obj.observe_stop(FakePage(), {"observe_id": "obs_wrong"})
    assert "error" in r, r


def test_observe_stop_no_session():
    """无活跃会话 → 报错"""
    A = _load_actions()
    import types

    obj = A.Actions.__new__(A.Actions)
    obj._frame_target = lambda page, frame: page
    obj._observe = None
    r = obj.observe_stop(None, {})
    assert "error" in r and "observe_start" in r["error"], r
