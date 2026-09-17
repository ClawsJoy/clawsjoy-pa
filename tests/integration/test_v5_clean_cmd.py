"""/clean 指令：V5 入口拦截（方案A 后端兜底）"""
import sys

sys.path.insert(0, ".")
import pytest
from flask import Flask

from core.gateway.v5_execute import v5_execute_handler


@pytest.fixture()
def v5_app(monkeypatch):
    app = Flask(__name__)
    app.add_url_rule("/v5/execute", view_func=v5_execute_handler, methods=["POST"], endpoint="v5_exec")
    app.config["TESTING"] = True
    # mock _clean_session_context（避免真实清理副作用）
    import core.gateway.session_cleaner as _sc

    calls = {"count": 0}

    def _fake_clean(uid, sid):
        calls["count"] += 1
        calls["uid"], calls["sid"] = uid, sid

    monkeypatch.setattr(_sc, "_clean_session_context", _fake_clean)
    monkeypatch.setattr("core.gateway.session_cleaner._clean_session_context", _fake_clean)
    return app, calls


def test_v5_clean_command_intercepted(v5_app):
    """/clean 被 V5 拦截返回 cleaned，不路由 Agent"""
    app, calls = v5_app
    client = app.test_client()
    resp = client.post("/v5/execute", json={"user_id": "u9", "session_id": "s9", "message": "/clean"})
    d = resp.get_json()
    assert d.get("cleaned") is True, f"应返回 cleaned: {d}"
    assert calls["count"] >= 1, "应调用清理函数"
    assert calls.get("uid") == "u9"
    assert calls.get("sid") == "s9"


def test_v5_clean_variants(v5_app):
    """/clear /clearsession 同样拦截"""
    app, calls = v5_app
    client = app.test_client()
    for cmd in ("/clear", "/clearsession", " /clean "):
        calls["count"] = 0
        resp = client.post("/v5/execute", json={"user_id": "u9", "session_id": "s9", "message": cmd})
        d = resp.get_json()
        assert d.get("cleaned") is True, f"{cmd} 应拦截: {d}"


def test_v5_normal_message_not_intercepted(v5_app, monkeypatch):
    """普通消息不拦截，继续正常流程"""
    app, calls = v5_app
    client = app.test_client()
    # 普通消息会走到后续逻辑（可能失败于 LLM 无 key 等），只要不是 cleaned 即可
    resp = client.post("/v5/execute", json={"user_id": "u9", "session_id": "s9", "message": "你好，介绍一下自己"})
    d = resp.get_json() or {}
    assert d.get("cleaned") is not True, "普通消息不应被当作 /clean"
