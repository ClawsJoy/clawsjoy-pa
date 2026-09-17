# -*- coding: utf-8 -*-
"""turn 收口与中断语义回归（2026-09-13 bug #4 + #7）。

#4：`_stream_gen` 里 `_evq.get(timeout=30)` 超时只发心跳、**无限循环** —— 桥接线程挂死后
    流永远心跳，前端一直 Thinking，只能重启网关（实测挂死 10 分钟无日志）。
    现在加 turn 级硬时限：超时 → request_cancel + 一条明确的 error 事件 + [DONE]。
#7：此前没有 GeneratorExit 处理 —— 客户端断开后后台线程照跑（实测仍跑 35s），
    而另一条路径下 turn 又会直接中止，四种中断归宿不一致。
    现在统一：**流未正常收尾就关闭 = 取消该 turn**。
"""
import json
import sys
import time

sys.path.insert(0, ".")
from core.gateway import shared_state as ss
from core.gateway.v9_chat import bridge_call as bc


def _events(gen, n=None):
    out = []
    for chunk in gen:
        out.append(chunk)
        if n and len(out) >= n:
            break
    return out


def _fake_policy(ms):
    return lambda: {"execution_budget": {"turn_timeout_ms": ms}}


def test_turn_timeout_emits_error_and_cancels(monkeypatch):
    """turn 超时：必须发出明确 error 事件 + [DONE]，并置取消标志（不能无限心跳）。"""
    called = {"cancel": 0}
    monkeypatch.setattr(ss, "_load_v9_execution_policy", _fake_policy(1))
    monkeypatch.setattr(ss, "request_cancel", lambda sid: called.__setitem__("cancel", called["cancel"] + 1))

    def _never_returns(*a, **k):
        time.sleep(30)  # 模拟桥接线程挂死

    gen = bc.make_stream_response(
        bridge_loop_fn=_never_returns,
        messages=[],
        tools=[],
        user_id="u",
        session_id="s_to",
        adapter=None,
        thinking2=False,
        model="m",
        plan_status=None,
        current_plan=None,
        data={},
        max_total_tools=48,
        goal_info_fn=lambda sid: {},
    )
    out = _events(gen)
    joined = "".join(out)
    assert '"type": "error"' in joined or '"type": "error"' in joined, joined[:400]
    assert "超时" in joined
    assert "[DONE]" in joined
    assert called["cancel"] >= 1, "超时必须置取消标志"


def test_client_disconnect_cancels_turn(monkeypatch):
    """客户端断开（生成器被提前关闭）→ 统一语义为取消。"""
    called = {"cancel": 0}
    monkeypatch.setattr(ss, "_load_v9_execution_policy", _fake_policy(0))
    monkeypatch.setattr(ss, "request_cancel", lambda sid: called.__setitem__("cancel", called["cancel"] + 1))

    def _never_returns(*a, **k):
        time.sleep(30)

    gen = bc.make_stream_response(
        bridge_loop_fn=_never_returns,
        messages=[],
        tools=[],
        user_id="u",
        session_id="s_dc",
        adapter=None,
        thinking2=False,
        model="m",
        plan_status=None,
        current_plan=None,
        data={},
        max_total_tools=48,
        goal_info_fn=lambda sid: {},
    )
    first = next(gen)  # 消费第一条(start)后模拟客户端断开
    assert "start" in first
    gen.close()
    time.sleep(0.2)
    assert called["cancel"] >= 1, "断开必须等价于取消"


def test_normal_completion_does_not_cancel(monkeypatch):
    """不回归：正常收尾（走到 [DONE]）不得误发取消。"""
    called = {"cancel": 0}
    monkeypatch.setattr(ss, "_load_v9_execution_policy", _fake_policy(60000))
    monkeypatch.setattr(ss, "request_cancel", lambda sid: called.__setitem__("cancel", called["cancel"] + 1))

    def _fast_loop(*a, **k):
        # 桥接循环返回值即 result_slot["out"]（run_bridge_async 负责赋值）
        return ([{"role": "assistant", "content": "done"}], [], False, None, 1, "stop", "ok")

    gen = bc.make_stream_response(
        bridge_loop_fn=_fast_loop,
        messages=[],
        tools=[],
        user_id="u",
        session_id="s_ok",
        adapter=None,
        thinking2=False,
        model="m",
        plan_status=None,
        current_plan=None,
        data={},
        max_total_tools=48,
        goal_info_fn=lambda sid: {},
    )
    joined = "".join(gen)
    assert "[DONE]" in joined
    assert called["cancel"] == 0, "正常收尾不应取消"
