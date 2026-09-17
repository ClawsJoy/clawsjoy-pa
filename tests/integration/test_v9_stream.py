"""任务2: v9/agent/chat 流式模式（SSE 事件流）+ 非流式 fallback"""
import sys, os, json
sys.path.insert(0, ".")
import pytest

os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-for-stream")


class _FakeAdapter:
    """mock DeepSeekAdapter: 第一轮无工具调用直接完成（验证事件流，不触发真实工具）"""
    def __init__(self, *a, **k):
        pass

    def execute_with_tools(self, **k):
        return {
            "success": True,
            "data": {"choices": [{"message": {"role": "assistant", "content": "任务完成，无需工具调用"}}]},
            "tokens": 5,
        }


@pytest.fixture()
def stream_app(monkeypatch):
    import agent_gateway_enhanced as main
    from core.lib.v8.adapters import deepseek_adapter as dsa
    monkeypatch.setattr(dsa, "DeepSeekAdapter", _FakeAdapter)
    monkeypatch.setattr(main, "app", main.app)  # 保证 test client 用主 app
    main.app.config["TESTING"] = True
    return main.app.test_client()


def _simple_messages():
    return [{"role": "user", "content": "测试流式任务：简单回复即可"}]


def test_stream_mode_emits_sse_events(stream_app):
    """stream=true 时返回 text/event-stream，含 start/progress/done 事件"""
    resp = stream_app.post("/v9/agent/chat", json={
        "user_id": "web_1783219071801",
        "session_id": "session_stream_test_1",
        "model": "deepseek-v4-flash",
        "stream": True,
        "messages": _simple_messages(),
    })
    assert resp.status_code == 200
    ctype = resp.headers.get("Content-Type", "")
    assert "text/event-stream" in ctype, f"应返回 SSE, got {ctype}"
    body = resp.get_data(as_text=True)
    assert "[DONE]" in body, "SSE 应以 [DONE] 结尾"
    events = []
    for line in body.splitlines():
        if line.startswith("data: ") and line[6:].strip() not in ("[DONE]",):
            try:
                events.append(json.loads(line[6:]))
            except Exception:
                pass
    types = [e.get("type") for e in events]
    assert "start" in types, f"缺 start 事件: {types}"
    assert "progress" in types, f"缺 progress 事件: {types}"
    assert "done" in types, f"缺 done 事件: {types}"
    done = next(e for e in events if e.get("type") == "done")
    assert done.get("success") is True, f"done 事件应 success: {done}"
    assert "tool_steps" in done, "done 事件应含 tool_steps"


def test_non_stream_mode_returns_json(stream_app):
    """默认（非流式）仍返回 JSON——fallback 保留"""
    resp = stream_app.post("/v9/agent/chat", json={
        "user_id": "web_1783219071801",
        "session_id": "session_stream_test_2",
        "model": "deepseek-v4-flash",
        "messages": _simple_messages(),
    })
    assert resp.status_code == 200
    ctype = resp.headers.get("Content-Type", "")
    assert "text/event-stream" not in ctype, "非流式不应返回 SSE"
    d = resp.get_json()
    assert d.get("success") is True, f"非流式应成功: {d}"
