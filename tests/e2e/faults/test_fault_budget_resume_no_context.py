# -*- coding: utf-8 -*-
"""故障注入 #15：预算耗尽 → 老板回「继续」→ 任务链必须接上（不得 no_context）2026-09-13。

事故（**第三次同型**：修好的东西在主路径上接不上）：
  1) no_context 唯一产生点 core/gateway/v9_chat/recovery.py:306 —— 老板回「继续」时它只查
     BRIEF.md 与 .agent_state.json 的 last_task 两个源，两个都空就当场短路报 no_context，
     **同一次 HTTP 请求自带的 messages 历史（web/pa.html:680-685 每次回传 30 条 · 2026-09-13 之面 · 今漂）、
     goal 目标原文、session_log 事件流一律不看**。
  2) BRIEF.md 只在 core/gateway/execute_agent_task.py:415-427 生成；PA 走
     POST /v9/agent/chat（web/pa.html:684 · 2026-09-13 之面 · 今漂）→ 桥接循环，**从不调用该函数** → 主路径 0 生成
     （与「verification_chain 主路径 0 调用」同型）。
  3) last_task 只有 core/gateway/memory.py:173 与
     core/gateway/v9_bridge/response_builder.py:250 两个写入点；预算耗尽轮在
     agent_gateway_enhanced.py:479-481 被 _budget_limit_guard 早退（response_guard.py:44），
     **两个写入点全被跳过** → 那一句「回复「继续」可完成剩余落盘」是空头支票。
  4) 即使恢复层把 BRIEF/任务原文注入 messages，core/gateway/v9_bridge/round_start.py:16
     轮首 derive 重建会把内存里刚注入的 system 消息整段丢掉 → 第一次 LLM 调用前就没了；
     而 derive(last_task_only=True) 的边界还会落在「继续」这条事件上，把任务原文整段切掉。

纪律：**先能失败，再能通过**。四条 FAULT 断言在修复前全红；最后一条端到端断言
「模型实际收到的 messages 里有任务原文」，测的是调用点，不是实现细节 —— 不 mock 被测逻辑
（只用假 adapter 顶掉外部 LLM 调用）。
"""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

# 沙箱里可能同时有多个 pytest 进程（多个 agent 并行跑回归）—— UID/sid 带 pid，
# 否则两个进程用同一份 data/projects/{UID}/{sid}，对方的 fixture 会删掉自己的现场（实测 flaky）。
_PID = os.getpid()
UID = f"fault_rc_u{_PID}"
TASK = "帮我把 @DS Chat 线程里的回复抓下来，整理成 data/reports/ds_chat.md 报告"
_RESUME_MARK = "[上下文恢复]"


def _sandbox(sid):
    return Path(f"data/projects/{UID}/{sid}/clawsjoy_dev")


def _state(sid):
    _f = _sandbox(sid) / ".agent_state.json"
    return json.loads(_f.read_text(encoding="utf-8")) if _f.exists() else {}


class _BudgetBustAdapter:
    """假 LLM：第 1 轮回一句话但把 token 直接打爆预算 → 下一行 _budget_limit_guard 早退。"""

    model = "fake-budget-bust"

    def __init__(self):
        self.calls = 0

    def execute_with_tools(
        self, messages=None, tools=None, user_id=None, temperature=None, max_tokens=None, thinking=None, **kw
    ):
        self.calls += 1
        if self.calls == 1:
            return {
                "success": True,
                "tokens": 999999999,
                "data": {
                    "choices": [{"message": {"role": "assistant", "content": "先抓一下"}, "finish_reason": "tool_calls"}]
                },
            }
        return {
            "success": True,
            "tokens": 0,
            "data": {"choices": [{"message": {"role": "assistant", "content": "预算不足收尾"}}]},
        }


class _CaptureAdapter:
    """假 LLM：把**实际收到**的 messages 留证。"""

    model = "fake-capture"

    def __init__(self):
        self.seen = []

    def execute_with_tools(
        self, messages=None, tools=None, user_id=None, temperature=None, max_tokens=None, thinking=None, **kw
    ):
        self.seen = list(messages or [])
        return {
            "success": True,
            "tokens": 0,
            "data": {"choices": [{"message": {"role": "assistant", "content": "接着做完了"}, "finish_reason": "stop"}]},
        }


@pytest.fixture
def sess(request, monkeypatch):
    """独立 session（唯一 sid）+ 用完清干净：沙箱目录 / session_log / 新增产物。"""
    sid = ("fault_rc_" + request.node.name.replace("test_", ""))[:40] + f"_{_PID}"
    import core.gateway.session_log as sl

    sl._logs.pop(sid, None)
    # BRIEF.md 有两个副本(data/plans/{sid} + 沙箱), 两侧都要清 —— 只清沙箱会让
    # BriefManager.load() 命中上一轮残留的 master_brief, 测试就不隔离了。
    shutil.rmtree(Path(f"data/projects/{UID}"), ignore_errors=True)
    shutil.rmtree(Path(f"data/plans/{sid}"), ignore_errors=True)
    _sandbox(sid).mkdir(parents=True, exist_ok=True)
    _reports_dir = Path("data/verification_reports")
    _pre_reports = set(_reports_dir.glob("*.json")) if _reports_dir.exists() else set()
    yield sid
    shutil.rmtree(Path(f"data/projects/{UID}"), ignore_errors=True)
    shutil.rmtree(Path(f"data/plans/{sid}"), ignore_errors=True)
    for _f in Path("data/session_logs").glob(f"{sid}*.jsonl"):
        try:
            _f.unlink()
        except Exception:
            pass
    for _f in Path("data/v8/user_messages").glob(f"{sid}*.jsonl"):
        try:
            _f.unlink()
        except Exception:
            pass
    if _reports_dir.exists():
        for _f in set(_reports_dir.glob("*.json")) - _pre_reports:
            try:
                _f.unlink()
            except Exception:
                pass
    sl._logs.pop(sid, None)


def _inject(sid, messages):
    """走真实恢复层块 C（inject_context_and_flags），不 mock 任何被测逻辑。"""
    from core.gateway.v9_bridge.context_utils import (
        _v9_inject_context,
        _v9_looks_like_new_task,
        _v9_mark_agent_plan,
        _v9_round_checkpoint,
    )
    from core.gateway.v9_chat import recovery as R

    return R.inject_context_and_flags(
        messages=messages,
        user_id=UID,
        session_id=sid,
        task_id="t_resume",
        inject_ctx_fn=_v9_inject_context,
        mark_plan_fn=_v9_mark_agent_plan,
        round_checkpoint_fn=_v9_round_checkpoint,
        looks_like_new_task_fn=_v9_looks_like_new_task,
        gsl_events_fn=lambda s: [],
    )


def _run_bridge(sid, messages, adapter):
    """走真实桥接循环（agent_gateway_enhanced._v9_bridge_loop）。"""
    import agent_gateway_enhanced as gw

    return gw._v9_bridge_loop(messages, [], UID, sid, adapter, False, "deepseek-v4-flash", None, None, {})


# ================= FAULT ①：预算耗尽轮必须落盘可续跑上下文 =================


def test_FAULT_budget_exhausted_turn_must_persist_resume_context(sess):
    """① 先能失败：预算耗尽轮结束时，.agent_state.json 必须有 last_task、BRIEF.md 必须存在。

    修复前：_budget_limit_guard 在 agent_gateway_enhanced.py:479-481 早退，
    跳过 core/gateway/memory.py 之 persist_session_learning_state() / response_builder.py:250 两个唯一写入点 → 现场只剩 goal 字段。
    """
    out = _run_bridge(
        sess, [{"role": "system", "content": "SYS"}, {"role": "user", "content": TASK}], _BudgetBustAdapter()
    )
    assert out[3] is not None and out[3].get("status") == "token_water", f"该轮本应走预算收尾（注入生效前提），实际 final_resp={out[3]}"
    assert _state(sess).get("last_task") == TASK[:200], "预算耗尽轮没落 last_task → 老板回「继续」必然无上下文（第三次同型事故现场）"
    assert (_sandbox(sess) / "BRIEF.md").exists(), "主路径(PA→/v9/agent/chat)从没生成 BRIEF.md"


# ================= FAULT ②：事故现场（只有 goal 字段）回「继续」不得 no_context =================


def test_FAULT_continue_with_goal_only_state_must_not_no_context(sess):
    """② 先能失败：现场只剩 goal 字段时（正是事故现场），「继续」不得报 no_context。

    goal 字段由 goal_state._persist_goal → _save_state(goal_state.py:100-102) 写，
    所以 .agent_state.json 存在但没有 last_task → 走的是"兜底源也空"分支。
    """
    (_sandbox(sess) / ".agent_state.json").write_text(
        json.dumps({"goal": {"goal_id": "g1", "objective": TASK, "status": "active"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert not (_sandbox(sess) / "BRIEF.md").exists()
    _res = _inject(
        sess,
        [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": TASK},
            {"role": "assistant", "content": "已开始"},
            {"role": "user", "content": "继续"},
        ],
    )
    assert _res["short_circuit"] is None, f"仍报 no_context（任务链断）: {_res['short_circuit']}"
    _joined = "\n".join(str(m.get("content") or "") for m in _res["messages"])
    assert TASK[:20] in _joined, "恢复出来的上下文里没有任务原文"


# ================= FAULT ③：「继续」不得成为 derive 的任务边界 =================


def test_FAULT_continue_must_not_cut_task_out_of_projection(sess):
    """③ 先能失败：derive_messages(last_task_only=True) 的边界不能落在「继续」上。

    修复前：边界 = 最近一条 user_input 事件 = "继续" → 投影从"继续"开始，
    **真实任务原文被整段切掉**（session_log.py:154-163）。
    """
    from core.gateway.session_log import SessionLog

    _log = SessionLog(sess)
    _log.append("user_message", {"role": "user", "content": TASK, "source": "user_input"})
    _log.append("assistant_message", {"role": "assistant", "content": "已列计划"})
    _log.append("user_message", {"role": "user", "content": "继续", "source": "user_input"})
    _proj = _log.derive_messages(last_task_only=True)
    _texts = [str(m.get("content") or "") for m in _proj]
    assert any(TASK[:20] in t for t in _texts), f"任务原文被 derive 边界切掉（续跑必丢上下文）: {_texts}"


# ================= FAULT ④：轮首 derive 重建不得冲掉注入的续跑上下文 =================


def test_FAULT_injected_resume_context_must_survive_round_rebuild(sess):
    """④ 先能失败：恢复层注入的续跑上下文必须在 rebuild_context（round_start.py:16）后仍在。

    修复前：注入只改内存、不写 session_log 事件 → 轮首 derive 重建直接丢掉
    → 第一次 LLM 调用前就没了（注入形同虚设）。
    """
    from core.gateway.v9_bridge.round_start import rebuild_context

    _msgs = [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "继续"},
        {"role": "system", "content": f"{_RESUME_MARK} 任务说明书（BRIEF.md）：\n> {TASK}"},
    ]
    _out = rebuild_context(
        messages=_msgs, tools=[], user_id=UID, session_id=sess, model="deepseek-v4-flash", is_7b_fallback=False
    )
    assert any(_RESUME_MARK in str(m.get("content") or "") for m in _out), "轮首 derive 重建把注入的续跑上下文冲掉了（本次「续跑不丢上下文」修复失效）"


# ================= PASS：端到端「预算耗尽 → 继续」任务链接上 =================


def test_PASS_budget_exhaust_then_continue_reaches_model_with_task(sess):
    """端到端：真调用点跑两轮（桥接循环 + 恢复层），断言**模型实际收到**任务原文。"""
    _run_bridge(sess, [{"role": "system", "content": "SYS"}, {"role": "user", "content": TASK}], _BudgetBustAdapter())
    assert _state(sess).get("last_task"), "第 1 轮(预算耗尽)没留下可续跑上下文"

    _res = _inject(sess, [{"role": "system", "content": "SYS"}, {"role": "user", "content": "继续"}])
    assert _res["short_circuit"] is None, f"「继续」被短路: {_res['short_circuit']}"

    _cap = _CaptureAdapter()
    _run_bridge(sess, _res["messages"], _cap)
    _joined = "\n".join(str(m.get("content") or "") for m in _cap.seen)
    assert TASK[:20] in _joined, "模型实际收到的 messages 里没有任务原文 → 续跑丢上下文"
    assert _RESUME_MARK in _joined, "续跑上下文标记没进到模型输入"


def test_PASS_new_task_does_not_clobber_last_task(sess):
    """不回归：纯「继续」不得把 last_task 冲成"继续"（core/gateway/memory.py 之 persist_session_learning_state() 之保护段 · 今 :173-181 —— 只挡了一半情况）。"""
    from core.gateway.resume_context import ensure_resumable_context

    ensure_resumable_context(user_id=UID, session_id=sess, messages=[{"role": "user", "content": TASK}])
    r2 = ensure_resumable_context(user_id=UID, session_id=sess, messages=[{"role": "user", "content": "继续"}])
    assert _state(sess).get("last_task") == TASK[:200], "「继续」把任务原文冲掉了"
    assert r2["task"] == TASK, f"续跑未回填任务原文: {r2}"
