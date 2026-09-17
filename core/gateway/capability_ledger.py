# -*- coding: utf-8 -*-
"""Capability Execution Ledger（2026-09-13）。

**命名根因**：GPT 把「接了但静默跳过」命名为 **capability liveness failure**
—— 一段能力代码有三种状态：没接（0 调用）／接了但抛错被吞（静默跳过）／真跑了。
前两种从外部看**完全一样**（都没留下痕迹），所以必须给「预期要执行的能力」留一条可查记录。

**落点决策：复用 session_log 事件流，不新建表。**
理由：① 已有 turn_id/step_id/时间戳/追加式保证，ledger 最需要的是「可查、可断言」而非高性能聚合；
     ② 新建表要额外处理迁移/并发/清理，而这张 ledger 的第一价值是**让「跳过」可见**；
     ③ 等真需要跨 session 聚合统计时再抽表，那时数据模型也更清楚。

事件形态（type=capability_exec）：
    {capability, expected, result, started_at, finished_at, elapsed_ms, detail}
覆盖（本批先做 2 个，其余按「先有 expected/result 语义」逐条加）：
    verification —— 完成核验（含五步链是否真跑）
    tool_block   —— 护栏拦截（续跑禁写 vault 等）
"""
import time

# 能力名白名单（防拼错导致统计失真）
CAPABILITIES = (
    "verification",
    "tool_block",
    "tool_call",
    "artifact_write",
    "state_transition",
    "notification",
    "intent_classifier",
)  # 批179：意图分类器（fastText）存活率也进 ledger

# 2026-09-13 except 策略分类（与 GPT 的分歧定稿）：
#   两类能力的**失败语义不同**，不能用同一策略 ——
#   STRICT：不可用 = 状态可能不一致，继续跑才危险 → emit_event + raise
#   DEGRADABLE：不可用 = 这次没验成，任务本身没坏 → emit_event + 继续（记 SKIPPED）
#   理由：对 DEGRADABLE 也 raise，会制造**假的失败**（SSE error），
#         而「制造假失败」与「制造假完成」同样有害。
STRICT_CAPABILITIES = ("artifact_write", "state_transition")
DEGRADABLE_CAPABILITIES = ("verification", "notification", "tool_block", "tool_call")


# 批180 · result 取值白名单 + 「存活率」三分类（堵住「result 取值让 rate 虚高」的陷阱）
#   语义：RAN = 真的跑成；FAILED = 跑了但没过（**不算存活**，单列可见，不隐藏）；
#         NOT_RUN = 没跑（本该跑却跳过 / 不适用 / 被护栏拦住）。
#   为什么必须把 FAILED 单列：批179 教训 —— 旧算术是「非 SKIPPED 一律算已执行」，
#   于是「能力根本没跑成」只要被记成 FAIL，rate 就会算成 1.0（**死能力显示成活能力**）。
#   实测依据（批180 先验）：result 的**唯一消费者**就是本文件的 liveness_report（无生产调用点）；
#   生产侧现有取值只有 PASS / FAIL / SKIPPED（response_guard 的 verification 两处 + cortex 的 intent_classifier）
#   ⇒ 收紧算术**不影响**任何生产调用，且 FAIL 仍是合法取值（禁掉它反而会丢信息）。
RESULT_RAN = ("PASS",)
RESULT_FAILED = ("FAIL",)
RESULT_NOT_RUN = ("SKIPPED", "NOT_APPLICABLE", "BLOCKED")
RESULT_VOCAB = RESULT_RAN + RESULT_FAILED + RESULT_NOT_RUN


def check_result(result):
    """result 取值白名单校验（**fail-loud**：防拼错、防「未知值被静默算成已执行」）。"""
    _r = str(result)
    if _r not in RESULT_VOCAB:
        raise ValueError("[CAPABILITY_LEDGER] 非法 result=%r（词表：%s）—— 词表外的取值会让存活率算术失真" % (result, "/".join(RESULT_VOCAB)))
    return _r


def is_strict(capability):
    """该能力的不可用是否应当中断。env V9_CAPABILITY_STRICT=1 时全部视为严格。"""
    import os as _os_cl

    if str(_os_cl.environ.get("V9_CAPABILITY_STRICT", "0")) == "1":
        return True
    return str(capability) in STRICT_CAPABILITIES


def on_capability_error(capability, session_id, exc, detail="", turn_id=None, emit=True):
    """统一的「能力不可用」处置：永远先留痕，再按分类决定是否抛。"""
    payload = finish(
        start(capability, session_id, expected=True, turn_id=turn_id),
        "SKIPPED",
        detail="%s err=%s" % (detail, str(exc)[:150]),
        emit=emit,
    )
    if is_strict(capability):
        raise RuntimeError("[CAPABILITY_STRICT] %s 不可用，按策略中断: %s" % (capability, exc))
    return payload


def start(capability, session_id, expected=True, turn_id=None, step_id=0):
    """登记「一个预期要执行的能力开始了」。契约：返回 handle（dict），交给 finish()。"""
    return {
        "capability": str(capability),
        "expected": bool(expected),
        "session_id": session_id,
        "turn_id": turn_id,
        "step_id": step_id,
        "started_at": time.time(),
    }


def finish(handle, result, detail="", emit=True):
    """收尾并落一条 capability_exec 事件。

    result 建议取值：PASS / FAIL / SKIPPED / NOT_APPLICABLE / BLOCKED。
    **SKIPPED 是这张表存在的理由** —— 它让「本该跑却没跑」变成可查的事实，而不是沉默。
    """
    result = check_result(result)  # 批180：词表校验（fail-loud；词表外取值会让存活率算术失真）
    try:
        h = handle or {}
        _end = time.time()
        payload = {
            "capability": h.get("capability"),
            "expected": h.get("expected", True),
            "result": str(result),
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(h.get("started_at") or _end)),
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_end)),
            "elapsed_ms": int((_end - (h.get("started_at") or _end)) * 1000),
            "detail": str(detail)[:300],
        }
        if emit:
            try:
                from core.gateway.session_log import log_event as _le

                _le(
                    h.get("session_id"),
                    "capability_exec",
                    payload,
                    turn_id=h.get("turn_id"),
                    step_id=h.get("step_id", 0),
                )
            except Exception as _e:
                print(f"[CAPABILITY_LEDGER] 落盘失败(不阻断): {_e}")
        return payload
    except Exception as _e2:
        print(f"[CAPABILITY_LEDGER] finish 异常(不阻断): {_e2}")
        return {}


def record(capability, session_id, result, expected=True, detail="", turn_id=None, step_id=0):
    """一步登记（不需要 start 的场景）。"""
    return finish(start(capability, session_id, expected=expected, turn_id=turn_id, step_id=step_id), result, detail)


def liveness_report(session_id, capabilities=("verification",)):
    """给一个会话算「能力存活率」。

    批180 语义收紧（旧口径：「非 SKIPPED 一律算已执行」）：
      executed = **PASS** 条数（真跑成）        rate = executed / expected
      failed   = FAIL 条数（跑了但没过，**不计入 rate**，单列可见）
      not_run  = SKIPPED / NOT_APPLICABLE / BLOCKED 条数（没跑）
      unknown  = 词表外的历史取值条数（**单列**，不再被静默算成已执行）
      sum_ok   = executed + failed + not_run + unknown == expected（账目自洽）

    契约：返回 {capability: {expected, executed, failed, not_run, skipped, unknown, rate, sum_ok}}。
    """
    out = {}
    try:
        from core.gateway.session_log import get_session_log as _gsl

        rows = [e for e in _gsl(session_id)._events if getattr(e, "type", "") == "capability_exec"]
    except Exception:
        rows = []
    for cap in capabilities:
        rel = [r for r in rows if (r.payload or {}).get("capability") == cap and (r.payload or {}).get("expected")]
        _res = [str((r.payload or {}).get("result")) for r in rel]
        _ran = len([x for x in _res if x in RESULT_RAN])
        _fail = len([x for x in _res if x in RESULT_FAILED])
        _not = len([x for x in _res if x in RESULT_NOT_RUN])
        _unk = len(_res) - _ran - _fail - _not
        out[cap] = {
            "expected": len(rel),
            "executed": _ran,
            "failed": _fail,
            "not_run": _not,
            "skipped": len([x for x in _res if x == "SKIPPED"]),
            "unknown": _unk,
            "rate": (_ran / len(rel)) if rel else None,
            "sum_ok": (_ran + _fail + _not + _unk) == len(rel),
        }
    return out


def record_continuation_cost(session_id, attempt, tokens_total, tools_total, verdict="", failures_n=0, turn_id=None):
    """记录一次续跑的代价（2026-09-13）。

    **只记录，不拦** —— 先拿真实分布再定 retry_token_cap。
    字段：
      attempt      第几次续跑（1-based）
      tokens_total 本 turn 到该时刻累计 token（**绝对值**，相邻两次相减即得增量）
      tools_total  本 turn 到该时刻累计工具数
      verdict      触发续跑的核验结论
      failures_n   失败条数
    落点：session_log 事件流（type=continuation_cost），不新建表 —— 与 ledger 同一决策。
    """
    try:
        from core.gateway.session_log import log_event as _le_cc

        payload = {
            "attempt": int(attempt),
            "tokens_total": int(tokens_total or 0),
            "tools_total": int(tools_total or 0),
            "verdict": str(verdict or ""),
            "failures_n": int(failures_n or 0),
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        _le_cc(session_id, "continuation_cost", payload, turn_id=turn_id, step_id=0)
        return payload
    except Exception as _e_cc:
        print(f"[CONTINUATION_COST] 记录失败(不阻断): {_e_cc}")
        return {}
