# -*- coding: utf-8 -*-
"""B 块(2026-09-13) 续跑上下文：让「预算耗尽 → 回复继续」这条链真的接得上。

事故（第三次同型：修复已存在但**主路径接不上**）：
1) 唯一 no_context 产生点 = core/gateway/v9_chat/recovery.py:306。
   老板回「继续」时它只查两个源（BRIEF.md / .agent_state.json 的 last_task），
   两个都空就当场短路报 no_context —— **同一次 HTTP 请求自带的 messages 历史、
   goal 目标原文、session_log 事件流一律不看**（web/pa.html:680-685 每次回传最近 30 条）。
2) BRIEF.md 只在 core/gateway/execute_agent_task.py:415-427 生成。PA 走的是
   POST /v9/agent/chat（web/pa.html:684）→ 桥接循环，**从不调用该函数**
   → 主路径 0 生成（与「verification_chain 主路径 0 调用」同型）。
3) last_task 全仓只有两个写入点：core/gateway/memory.py:173
   (persist_session_learning_state) 与 core/gateway/v9_bridge/response_builder.py:250
   (build_bridge_response)。而预算耗尽轮在 agent_gateway_enhanced.py:479-481
   被 _budget_limit_guard 早退（response_guard.py:44）——**两个写入点全被跳过**，
   .agent_state.json 里只剩 goal_state 写的 goal 字段（goal_state.py:100-102）。
   文件存在 → 下一轮走的是「last_task 兜底分支」而不是「文件不存在分支」，
   于是兜底源也是空 → no_context。

本模块的做法：把「任务一开始就落一份可续跑上下文」做成**唯一 choke point**，
由 agent_gateway_enhanced._v9_bridge_loop 在进入轮循环前调用一次 —— 之后任何退出
路径（预算耗尽 / 取消 / 工具上限 / 异常 / 正常结束）都已经先落盘过了。

两条铁律：
  A. 纯续跑话语（"继续"）绝不当任务原文，也绝不去覆盖已有 last_task
     （否则任务原文会被冲成"继续"，memory.py:168-171 的防覆盖只挡了一半情况）；
  B. 只在真的拿到任务文本时才写文件 —— 不写空文件（否则会把"文件不存在"
     的语义改成"文件存在但没内容"，反而把兜底分支引向 no_context）。
"""
import json
import time
from pathlib import Path

# 纯续跑话语（小写比较）。**窄名单**：只收「无信息量、只表示接着做」的整句，
# 不用 len<=4 这类宽判据（否则"重启服务"这种真任务会被误判成续跑）。
RESUME_UTTERANCES = (
    "继续",
    "/continue",
    "continue",
    "继续任务",
    "继续执行",
    "继续做",
    "继续吧",
    "接着做",
    "接着",
    "go on",
    "resume",
    "继续。",
    "继续！",
)


def _state_path(user_id, session_id):
    return Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")


def _read_json(path):
    try:
        if path.exists():
            _t = path.read_text(encoding="utf-8")
            if _t.strip():
                _d = json.loads(_t)
                if isinstance(_d, dict):
                    return _d
    except Exception:
        pass
    return {}


def is_resume_utterance(text):
    """整句就是"接着做"（无任务信息量）→ True。"""
    _t = str(text or "").strip().lower().rstrip("。！!~～. ")
    return bool(_t) and _t in RESUME_UTTERANCES


def last_real_task_text(messages):
    """messages 里最近一条**真实任务**文本：跳过 [系统] 注入 与 纯续跑话语。"""
    for _m in reversed(messages or []):
        if not isinstance(_m, dict) or _m.get("role") != "user":
            continue
        _c = str(_m.get("content") or "").strip()
        if not _c or _c.startswith("[系统]") or is_resume_utterance(_c):
            continue
        return _c
    return ""


def goal_objective(user_id, session_id):
    """goal 目标原文：.agent_state.json 的 goal 字段 → goals/{id}.json（权威层）。"""
    _g = _read_json(_state_path(user_id, session_id)).get("goal") or {}
    if isinstance(_g, dict):
        _o = str(_g.get("objective") or "").strip()
        if _o:
            return _o
    try:
        from core.gateway.goal_state import get_goal_by_session_id

        _g2 = get_goal_by_session_id(session_id) or {}
        return str(_g2.get("objective") or "").strip()
    except Exception:
        return ""


def brief_text(user_id, session_id):
    try:
        from core.lib.brief_manager import get_brief_manager

        return str(get_brief_manager(user_id, session_id).inject() or "").strip()
    except Exception:
        return ""


def resolve_task_text(*, messages, user_id, session_id):
    """续跑上下文兜底链。返回 (文本, 来源标记)；取不到 → ("", "")。

    顺序（先近后远）：state.last_task → BRIEF.md → goal.objective → 请求体 messages 历史。
    最后一项是**永不失败**的源：PA 前端每次都把最近 30 条会话回传（web/pa.html:680）。
    """
    _st = _read_json(_state_path(user_id, session_id))
    _lt = str(_st.get("last_task") or "").strip()
    if _lt and not is_resume_utterance(_lt):
        return _lt, "state.last_task"
    _brief = brief_text(user_id, session_id)
    if _brief:
        return _brief, "BRIEF.md"
    _goal = goal_objective(user_id, session_id)
    if _goal and not is_resume_utterance(_goal):
        return _goal, "goal.objective"
    _task = last_real_task_text(messages)
    if _task:
        return _task, "request.messages"
    return "", ""


def ensure_resumable_context(*, user_id, session_id, messages):
    """任务开始即落一份可续跑上下文（幂等）。返回诊断 dict（调用方只记日志）。

    【A2 结案 2026-09-13 批72】与 core/gateway/execute_agent_task.py:415-427 的
    BRIEF 生成块**职责不同，刻意不合并**（老板批70 拍板 A2）。
    本函数是**启动型**：任务一开始就保证「可续跑上下文」存在（连 last_task 一起落）；
    那一块是**事件型**：主任务启动时补一份 BRIEF，且「已存在则不重写」以保留继续时的进度。
    两者行为差异共 4 处（适用条件/文本来源/是否落 last_task/BRIEF 重生成条件），
    合并会同时改变这三件事 ⇒ 保留两处。关联体检项 42。

    落两样：
      1) .agent_state.json 的 last_task —— recovery.py:300 的兜底源；
      2) BRIEF.md（不存在、或任务已换时才生成）—— recovery.py:292 的权威源。
    """
    _out = {"written": False, "task": "", "source": "", "brief_written": False}
    try:
        _path = _state_path(user_id, session_id)
        _state = _read_json(_path)
        _task = last_real_task_text(messages)
        _src = "request.messages" if _task else ""
        if not _task:
            _task, _src = resolve_task_text(messages=messages, user_id=user_id, session_id=session_id)
        _out["task"] = _task[:200]
        _out["source"] = _src
        # 1) last_task：只在有真实任务文本时写（铁律 B），且续跑话语不覆盖（铁律 A）
        if _task:
            _state["last_task"] = _task[:200]
            _state["last_task_at"] = time.time()
            # 批221 修（DS-206-3 指认：原为非原子直写 ⇒ 多写者交错 ⇒ Extra data 损坏）
            from core.gateway.state_json import update_json as _uj_rc
            _uj_rc(_path, lambda _d: (_d.clear(), _d.update(_state)))
            _out["written"] = True
        # 2) BRIEF.md：不存在 → 生成；存在但描述的是**别的任务** → 重生成（防跨任务串味）；
        #    纯续跑轮（_task 来自 state/goal，不是本请求的真实任务）不动它。
        try:
            from core.lib.brief_manager import get_brief_manager

            _bm = get_brief_manager(user_id, session_id)
            _cur = _bm.load()
            if _task and (_cur is None or (_src == "request.messages" and _task[:40] not in _cur[:1200])):
                _bm.generate(_task)
                _out["brief_written"] = True
        except Exception as _be:
            _out["brief_error"] = str(_be)[:200]
    except Exception as _e:
        _out["error"] = str(_e)[:200]
    return _out
