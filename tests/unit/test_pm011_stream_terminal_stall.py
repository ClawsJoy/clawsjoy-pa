# -*- coding: utf-8 -*-
"""PM-011 主件 · 流式终态保证（停滞 ⇒ 必发 error + [DONE]）。

PM 判据（2026-09-30）：「**任何流式响应必须在有限时间内给出终态 done 或 error**」。
现场（09-30 05:42，session=pa_mu6fxm7z）：worker 进工具阶段后零日志、零进度、零终态；
turns.db 里该 turn 直到 900s 心跳超时扫描才被判 STALE ⇒ **沉默 15 分钟没有任何终态**，
前端只能一直心跳（「疑似卡住」）。

本文件钉死四件（含反例门 —— 承 SOP 规则 5「反例优先」）：
  T1 停滞 ⇒ **必发** type=error（stage=turn_stall）+ [DONE] + 置取消标志；
  T2 **反例门**：把阈值设为 0（禁用本机制）⇒ 同一输入**不得**出现终态
     —— 证明 T1 是靠本机制通过的，不是靠别的路径（本判据有齿）；
  T3 「不该说时不说」：阈值很大 ⇒ 静默期内不得误收口（防把合法长任务判红）；
  T4 进度事件刷新停滞基线：一条 progress 之后的 5s 静默**不得**被判停滞
     —— 若基线停在 turn 起点，同一输入会被误判（这是本改动最大的风险面）。
"""
import sys
import threading
import time

sys.path.insert(0, ".")
from core.gateway import shared_state as ss
from core.gateway.v9_chat import bridge_call as bc


def _policy(timeout_ms, stall_ms):
    return lambda: {"execution_budget": {"turn_timeout_ms": timeout_ms, "turn_stall_ms": stall_ms}}


def _mk(session_id, bridge_loop_fn):
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


def _hung(*a, **k):
    time.sleep(30)  # 模拟 worker 卡在工具阶段（永不给进度、永不给终态）


def _take(gen, n):
    out = []
    for chunk in gen:
        out.append(chunk)
        if len(out) >= n:
            break
    return out


def _wire(monkeypatch, calls, stall_ms, tmp_path=None):
    # ⛔ 不让本门往**生产台账** data\v9\turns.db 写行 —— 那份台账是 PM/DS 的取证面，
    #    测试往里写行会污染读数（自陈：加此隔离前，本门在生产台账里留了 4 行）。
    if tmp_path is not None:
        from core.gateway import turn_registry as _tr

        monkeypatch.setattr(_tr, "DB_PATH", str(tmp_path / "turns.db"))
    monkeypatch.delenv("V9_TURN_STALL_MS", raising=False)
    monkeypatch.setattr(ss, "_load_v9_execution_policy", _policy(1500000, stall_ms))
    monkeypatch.setattr(ss, "request_cancel", lambda sid: calls.__setitem__("cancel", calls["cancel"] + 1))


def test_t1_stall_emits_terminal_error(monkeypatch, tmp_path):
    """停滞 ⇒ 必须发出 machine-readable 终态（error + [DONE]），并置取消标志。"""
    calls = {"cancel": 0}
    _wire(monkeypatch, calls, 1, tmp_path)  # 阈值 1ms ⇒ 首个 5s 静默周期即应判停滞
    out = list(_mk("s_pm011_stall", _hung))
    joined = "".join(out)
    assert '"type": "error"' in joined, joined[:400]
    assert '"stage": "turn_stall"' in joined, joined[:400]
    assert '"stall": true' in joined
    assert "silent_s" in joined
    assert "[DONE]" in joined, "终态之后必须关流"
    assert joined.index('"stage": "turn_stall"') < joined.index("[DONE]")
    assert calls["cancel"] >= 1, "停滞必须置取消标志（后台 worker 才会在下个检查点退出）"


def test_t2_反例门_机制禁用则无终态(monkeypatch, tmp_path):
    """反例门：turn_stall_ms=0（禁用本机制）⇒ 同一输入**不得**出现终态。

    若本测试失败（出现终态）⇒ 说明终态另有来源 ⇒ T1 的判据无齿、须重判。
    """
    calls = {"cancel": 0}
    _wire(monkeypatch, calls, 0, tmp_path)
    gen = _mk("s_pm011_stall_off", _hung)
    out = _take(gen, 2)
    gen.close()
    joined = "".join(out)
    assert '"type": "start"' in joined
    assert '"type": "error"' not in joined, "机制已禁用却仍出 error ⇒ 判据打在别处（无齿）: " + joined[:300]
    assert "[DONE]" not in joined, "机制已禁用却仍关流 ⇒ 判据打在别处（无齿）: " + joined[:300]


def test_t3_big_threshold_does_not_fire_early(monkeypatch, tmp_path):
    """不该说时不说：阈值很大 ⇒ 静默期内不得误收口（防把合法长任务判红）。"""
    calls = {"cancel": 0}
    _wire(monkeypatch, calls, 600000, tmp_path)
    gen = _mk("s_pm011_stall_big", _hung)
    out = _take(gen, 2)
    gen.close()
    joined = "".join(out)
    assert '"type": "error"' not in joined, joined[:300]
    # 不断言 cancel==0：gen.close() 本身＝客户端断开语义，必置取消（既有行为，与本机制无关）。
    # 本测试只问「停滞分支有没有走」—— 由事件面回答（无 stage=turn_stall）。


def test_t4_progress_event_resets_stall_baseline(monkeypatch, tmp_path):
    """进度事件刷新停滞基线：一条 progress 之后的 5s 静默不得被判停滞。

    时序（阈值 6000ms）：t≈0 start ／ t≈4s worker 推一条 progress ／
    t≈9s 生成器首次超时 —— 此刻「距最近进度」≈5s（< 6s）⇒ 只能发心跳。
    若基线停在 turn 起点，此刻读数≈9s（> 6s）⇒ 会误判停滞 ⇒ 本测试判红。
    """
    calls = {"cancel": 0}
    _wire(monkeypatch, calls, 6000, tmp_path)

    def _one_progress_then_hang(messages, tools, user_id, session_id, adapter, thinking2, model,
                                plan_status, current_plan, data, on_round=None):
        time.sleep(4.0)
        on_round(0, [], "工具阶段开始")
        time.sleep(30)

    gen = _mk("s_pm011_stall_prog", _one_progress_then_hang)
    out = _take(gen, 3)
    gen.close()
    joined = "".join(out)
    assert joined.count('"type": "progress"') == 1, "应恰好收到 worker 那一条 progress: " + joined[:400]
    assert '"type": "heartbeat"' in joined, "5s 静默（< 阈值）应发心跳: " + joined[:400]
    assert '"stage": "turn_stall"' not in joined, "有近期进度却判停滞 ⇒ 基线未刷新: " + joined[:400]