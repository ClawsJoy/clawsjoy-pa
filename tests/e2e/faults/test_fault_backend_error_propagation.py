# -*- coding: utf-8 -*-
"""故障注入 · 后端错误必须传播到前端（SSE 契约）。纪律：先能失败，再能通过。

背景：readSSE 只认 progress/done，type=error 被静默丢弃 → 老板看到的是
「进度刷了一屏然后什么都不发生」。前端已修；本测试锁**后端**那一侧：
桥接异常必须发出一条明确的 error 事件并以 [DONE] 收尾。
"""
import sys

sys.path.insert(0, ".")
from core.gateway import shared_state as ss
from core.gateway.v9_chat import bridge_call as bc


def _mk(bridge_loop_fn, session_id="s_err"):
    return bc.make_stream_response(
        bridge_loop_fn=bridge_loop_fn,
        messages=[],
        tools=[],
        user_id="u",
        session_id=session_id,
        adapter=None,
        thinking2=False,
        model="m",
        plan_status=None,
        current_plan=None,
        data={},
        max_total_tools=48,
        goal_info_fn=lambda sid: {},
    )


def test_FAULT_bridge_exception_is_reported_not_swallowed(monkeypatch):
    """① 先能失败：桥接抛异常 → 流里必须出现 error 事件（不能静默 [DONE]）。"""
    monkeypatch.setattr(ss, "request_cancel", lambda sid: None)

    def _boom(*a, **k):
        raise RuntimeError("模拟桥接崩溃")

    joined = "".join(_mk(_boom))
    assert '"type": "error"' in joined, joined[:300]
    assert "模拟桥接崩溃" in joined
    assert "[DONE]" in joined


def test_PASS_normal_completion_has_no_error_event(monkeypatch):
    """② 再能通过：正常完成不得出现 error 事件。"""
    monkeypatch.setattr(ss, "request_cancel", lambda sid: None)

    def _ok(*a, **k):
        return ([{"role": "assistant", "content": "done"}], [], False, None, 1, "stop", "ok")

    joined = "".join(_mk(_ok, session_id="s_ok2"))
    assert '"type": "done"' in joined
    assert '"type": "error"' not in joined
    assert "[DONE]" in joined
