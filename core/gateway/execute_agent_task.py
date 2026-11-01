"""_execute_agent_task — V9 后台任务执行主循环"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from core.gateway.archive import _archive_asset
from core.gateway.context_validator import (
    _check_recent_writes,
    _get_task_done_when,
    _planning_output_valid,
    audit_agent_output,
)
from core.gateway.message_assembler import _calc_token_budget, _estimate_tokens, _finalize_messages, _tg_estimate
from core.gateway.path_utils import _extract_tool_path, _resolve_main_repo, _resolve_path
from core.gateway.quota_manager import get_mode_tools
from core.gateway.sag_feedback import _build_code_edges, _update_sag_edge_learning, _update_sag_feedback

logger = logging.getLogger(__name__)
from core.gateway.sandbox_git import _auto_merge_to_main, _has_git_diff
from core.gateway import _proc as _proc  # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）
from core.gateway.shared_state import (
    _auto_merge_cooldown,
    _guard_log,
    _recursion_tracker,
    _session_tool_tracker,
    _tracker_setdefault,
)
from core.gateway.state_persist import _persist_retrieval_cache, _safe_serialize_state
from core.lib.gateway_helpers import _get_sandbox_base, cleanup_task_context
from core.lib.precision_feed import _classify_task_type
from core.lib.v8.ledger import ledger
from core.lib.v8.roster_engine import roster_engine

# 任务配置默认值（_task_config.get(key, default) 兼容，避免未定义引用）
_task_config = {}

# ===== 结构化错误分类(借鉴 Harness LlmError/errorChain: 错误带 code 而非纯文本) =====
_ERROR_CODES = ("LLM_API", "NETWORK", "TOOL_EXEC", "TOOL_ARGS", "TIMEOUT", "UNKNOWN")


def _struct_error(code, message, detail=None):
    """统一结构化错误: {"code", "message", "detail"}——供 preserve_error_context / 外部消费"""
    return {"code": code, "message": str(message)[:300], "detail": detail}


def _classify_exception(e, default="UNKNOWN"):
    """异常 -> 错误分类 code(按异常类型/消息特征)"""
    _n = type(e).__name__
    _s = str(e).lower()
    if (
        _n in ("ConnectionError", "TimeoutError", "ConnectionResetError", "NewConnectionError", "MaxRetryError")
        or "network" in _s
        or "connection" in _s
        or "unreachable" in _s
    ):
        return "NETWORK"
    if "api" in _s or "key" in _s or "balance" in _s or "quota" in _s or "429" in _s or "api error" in _s:
        return "LLM_API"
    if "json" in _s or "parse" in _s or "decode" in _s:
        return "TOOL_ARGS"
    return default


# 任务3 v9: 全局 LLM 并发信号量(最多 2 个同时调 DeepSeek)——
# v3-v6 实测子任务并发调 LLM 反复 Errno 101 网络错误(被限流);
# Semaphore 阻塞式 acquire, 排队等待的子任务不报错
_LLM_SEMAPHORE = threading.Semaphore(2)


def _ollama_execute_with_tools(messages, tools, model="qwen2.5:7b-instruct-q4_0-gpu", temperature=0.7, max_tokens=2000, cancel_event=None):
    """V9 Ollama 降级：本地 function calling（无 DEEPSEEK_API_KEY 时走此路径，不依赖外网）。

    - 普通路径：ollama /api/chat with tools，返回格式对齐 DeepSeek
    - cancel_event 不为空：走 stream=True，边读边检查取消；置位即 close 连接，
      让 RunService 的 running 取消能在秒级收口（不改 runs 对外状态语义）。
    """
    import requests as _rq

    _base = {"model": model, "messages": messages, "tools": tools, "temperature": temperature, "stream": False}
    if max_tokens:
        _base["options"] = {"num_predict": max_tokens}
    if cancel_event is None:
        try:
            _resp = _rq.post("http://127.0.0.1:11434/api/chat", json=_base, timeout=(10, 120))
            if _resp.status_code == 200:
                _data = _resp.json()
                _msg = _data.get("message", {}) or {}
                _tc = _msg.get("tool_calls") or []
                for _c in _tc:
                    _fn = _c.get("function", {})
                    if isinstance(_fn.get("arguments"), dict):
                        _fn["arguments"] = json.dumps(_fn["arguments"], ensure_ascii=False)
                    _c.setdefault("type", "function")
                _usage = (_data.get("prompt_eval_count") or 0) + (_data.get("eval_count") or 0)
                return {
                    "success": True,
                    "data": {"choices": [{"message": _msg, "finish_reason": "tool_calls" if _tc else "stop"}]},
                    "tokens": _usage,
                }
            return {"success": False, "error": f"Ollama 错误: {_resp.status_code} - {_resp.text[:300]}"}
        except Exception as _e:
            return {"success": False, "error": f"Ollama 调用失败: {_e}"}

    _body = dict(_base)
    _body["stream"] = True
    _resp = None
    try:
        _resp = _rq.post("http://127.0.0.1:11434/api/chat", json=_body, timeout=(10, 120), stream=True)
        if _resp.status_code != 200:
            return {"success": False, "error": f"Ollama 错误: {_resp.status_code} - {_resp.text[:300]}"}
        _parts = []
        _tool_calls = []
        _usage = 0
        for _line in _resp.iter_lines():
            if cancel_event.is_set():
                try:
                    _resp.close()
                except Exception:
                    pass
                return {"success": False, "cancelled": True, "error": "cancelled by user"}
            if not _line:
                continue
            try:
                _j = json.loads(_line.decode("utf-8") if isinstance(_line, bytes) else _line)
            except Exception:
                continue
            _m = _j.get("message") or {}
            _chunk = _m.get("content") or ""
            if _chunk:
                _parts.append(str(_chunk))
            for _c in (_m.get("tool_calls") or []):
                _fn = _c.get("function", {})
                if isinstance(_fn.get("arguments"), dict):
                    _fn["arguments"] = json.dumps(_fn["arguments"], ensure_ascii=False)
                _c.setdefault("type", "function")
                _tool_calls.append(_c)
            _usage = (_j.get("prompt_eval_count") or 0) + (_j.get("eval_count") or 0) or _usage
            if _j.get("done"):
                break
        if cancel_event.is_set():
            try:
                _resp.close()
            except Exception:
                pass
            return {"success": False, "cancelled": True, "error": "cancelled by user"}
        _msg = {"role": "assistant", "content": "".join(_parts)}
        if _tool_calls:
            _msg["tool_calls"] = _tool_calls
        return {
            "success": True,
            "data": {"choices": [{"message": _msg, "finish_reason": "tool_calls" if _tool_calls else "stop"}]},
            "tokens": _usage,
        }
    except Exception as _e:
        if cancel_event.is_set():
            return {"success": False, "cancelled": True, "error": "cancelled by user"}
        return {"success": False, "error": f"Ollama 调用失败: {_e}"}
    finally:
        try:
            if _resp is not None:
                _resp.close()
        except Exception:
            pass


def _notify_done_impl(on_done, task_id, user_id, session_id, sub_task_id, output=""):
    """#31 长线任务完成回调（H1 从 _execute_agent_task 提级为模块函数）"""
    if on_done:
        try:
            on_done(task_id, user_id, session_id, output)
        except Exception as _cb_e:
            logger.info(f"[sub:{sub_task_id}] [V9 async] on_done 回调失败(忽略): {_cb_e}")


def _notify_fail_impl(on_fail, task_id, user_id, session_id, sub_task_id, reason=""):
    """#31 长线任务失败回调（H1 从 _execute_agent_task 提级为模块函数）
    P3: reason 支持结构化 dict {code, message}; 回调只接受 str 时自动降级为 '[CODE] message' 文本。
    判定依据: 回调最后一个参数的类型注解——dict/Dict/Optional[dict] 视为结构化消费方, 无注解/str 视为文本消费方。
    """
    if not on_fail:
        return
    try:
        import inspect as _insp

        _payload = reason
        try:
            _params = list(_insp.signature(on_fail).parameters.values())
            if _params:
                _ann = _params[-1].annotation
                _accepts_str = _ann is _insp.Parameter.empty or _ann in (str, "str")
                if _accepts_str:
                    _payload = _notify_fail_to_text(reason)
        except (ValueError, TypeError):
            _payload = _notify_fail_to_text(reason)  # 签名不可解析 → 保守降级
        on_fail(task_id, user_id, session_id, _payload)
    except Exception as _cb_e:
        logger.info(f"[sub:{sub_task_id}] [V9 async] on_fail 回调失败(忽略): {_cb_e}")


def _notify_fail_to_text(reason) -> str:
    """结构化 dict -> '[CODE] message' 文本(兼容只接受 str 的回调)"""
    if isinstance(reason, dict):
        _code = reason.get("code", "")
        _msg = reason.get("message", "")
        return f"[{_code}] {_msg}" if _code else str(_msg or "")
    return str(reason)


def _run_filter_net_learning(user_id, session_id, messages, content):
    """#81 过滤网自学习：统计本次会话 tool_calls 特征并更新 core/lib/filter_net.json"""
    import json as _json
    import time as _t

    from core.lib.os_event_logger import write_os_event as _write_event

    _fnet_path = Path("core/lib/filter_net.json")
    _fnet = {
        "version": 1,
        "rules": [],
        "stats": {
            "sessions": 0,
            "learned_at": None,
            "last_session_id": None,
            "total_queries": 0,
            "successful_retrievals": 0,
            "empty_retrievals": 0,
        },
    }

    # ===== 加载现有 filter_net.json =====
    if _fnet_path.exists():
        try:
            _loaded = _json.loads(_fnet_path.read_text(encoding="utf-8"))
            if isinstance(_loaded, dict):
                _fnet = _loaded
        except Exception:
            # 加载失败用默认结构，不阻断自学习
            pass

    # ===== 提取本次会话 tool_calls 特征 =====
    _rules = _fnet.setdefault("rules", [])
    _rule_map = {}
    for _r in _rules:
        _rule_map[(_r.get("tool", ""), _r.get("pattern", ""))] = _r

    _assistant_blocks = [m for m in messages if m.get("role") == "assistant"]
    _calls = []
    for _i, _m in enumerate(_assistant_blocks):
        _tool_calls = _m.get("tool_calls") or []
        for _tc in _tool_calls:
            _fn = _tc.get("function") or {}
            _name = _fn.get("name") or ""
            _args = {}
            try:
                _args = _json.loads(_fn.get("arguments") or "{}")
            except Exception:
                _args = {}

            _pattern = ""
            for _k in ("path", "file", "query", "search"):
                if _args.get(_k):
                    _pattern = str(_args[_k])[:120]
                    break
            if not _pattern:
                _pattern = "<none>"

            _failed = False
            _tc_id = _tc.get("id") or ""
            for _jm in _assistant_blocks[_i + 1 :]:
                _jcontent = (_jm.get("content") or "").lower()
                if (
                    _tc_id
                    and _tc_id in _jcontent
                    and any(_kw in _jcontent for _kw in ("error", "失败", "拒绝", "denied", "invalid"))
                ):
                    _failed = True
                    break

            _calls.append((_name, _pattern, _failed))

    # ===== 修复点 1：无 tool_calls 也写入基础统计 =====
    # 不再提前 return None，继续更新 stats

    _stats = _fnet.setdefault("stats", {})
    _stats["sessions"] = int(_stats.get("sessions", 0) or 0) + 1
    _stats["learned_at"] = _t.strftime("%Y-%m-%d %H:%M:%S")
    _stats["last_session_id"] = session_id

    # ===== 修复点 3：从内存缓存回填计数 =====
    try:
        _qcache = globals().get("_query_cache", {}) or {}
        _ecache = globals().get("_search_empty_cache", {}) or {}

        _total_q = 0
        _success_q = 0
        for _sid, _sess_cache in _qcache.items():
            if not isinstance(_sess_cache, dict):
                continue
            for _qsig, _entry in _sess_cache.items():
                if not isinstance(_entry, dict):
                    continue
                _total_q += int(_entry.get("count", 0) or 0)
                # 有结果且未被阻断的检索视为成功
                if _entry.get("last_result") and not _entry.get("blocked"):
                    _success_q += 1

        _empty_q = sum(int(v) for v in _ecache.values() if isinstance(v, (int, float)))

        _stats["total_queries"] = _total_q
        _stats["successful_retrievals"] = _success_q
        _stats["empty_retrievals"] = _empty_q
    except Exception as _e_q:
        logger.info(f"[FILTER_NET] 回填缓存计数失败: {_e_q}")

    # ===== 更新规则权重 =====
    _updated = []
    for _name, _pattern, _failed in _calls:
        _key = (_name, _pattern)
        _r = _rule_map.get(_key)
        if _r is None:
            _r = {"tool": _name, "pattern": _pattern, "used_count": 0, "ignored_count": 0, "weight": 0.0}
            _rules.append(_r)
            _rule_map[_key] = _r

        _r["used_count"] = int(_r.get("used_count", 0) or 0) + 1
        if _failed:
            _r["ignored_count"] = int(_r.get("ignored_count", 0) or 0) + 1

        _used = _r["used_count"]
        _ignored = _r["ignored_count"]
        _r["weight"] = round(_ignored / _used if _used else 0.0, 3)

        _updated.append("%s/%s used=%d ignored=%d w=%.3f" % (_name, _pattern, _used, _ignored, _r["weight"]))

    # ===== 修复点 2：写入异常打印 + os_event =====
    try:
        _fnet_path.parent.mkdir(parents=True, exist_ok=True)
        _fnet_path.write_text(_json.dumps(_fnet, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as _e_w:
        logger.info(f"[FILTER_NET] 写入失败: {_e_w}")
        try:
            _write_event(
                event_type="filter_net_error",
                operation="write",
                os_action="error",
                os_context=str(_e_w),
                user_id=user_id,
                session_id=session_id,
            )
        except Exception:
            pass
        return None

    # ===== 返回摘要 =====
    if _updated:
        return "; ".join(_updated[-10:])
    return f"sessions={_stats['sessions']} (no tool_calls)"


# 注：_update_sag_edge_learning 使用 core/gateway/sag_feedback.py 的正确实现（#81），
# 本地曾有一个签名不匹配的僵尸嵌套函数遮蔽它（H1 提级时暴露，已删除）


def _audit_cross_check_save(messages, session_id, sub_task_id=None, dw=None, dw_res=None):
    """G4 审计复核: done_when 通过后、标记 done 前，用审计记录交叉核对。返回 True=通过/False=拒绝。"""
    try:
        from core.gateway.audit import read_audit_records, verify_completion_report

        _audit_rep = {}
        # 1) write_file 声称：messages 中出现 write_file 调用即声称成功
        for _m_ar in messages:
            if _m_ar.get("role") == "assistant" and _m_ar.get("tool_calls"):
                for _tc_ar in _m_ar["tool_calls"]:
                    _fn_ar = (_tc_ar.get("function") or {}).get("name", "")
                    if _fn_ar in ("write_file", "write_large"):
                        _audit_rep["write"] = {"tool": ["write_file", "write_large"], "claimed": True}
                        break
                if "write" in _audit_rep:
                    break
        # 2) 语法检查声称：execute_command 含 py_compile
        for _m_ar in messages:
            if _m_ar.get("role") == "assistant" and _m_ar.get("tool_calls"):
                for _tc_ar in _m_ar["tool_calls"]:
                    _fn_ar = (_tc_ar.get("function") or {}).get("name", "")
                    if _fn_ar != "execute_command":
                        continue
                    try:
                        _cmd_ar = json.loads(_tc_ar["function"].get("arguments", "{}")).get("command", "")
                        if "py_compile" in _cmd_ar:
                            _audit_rep["compile"] = {"tool": ["execute_command"], "claimed": True}
                    except Exception:
                        pass
                if "compile" in _audit_rep:
                    break
        # 3) done_when 声称：断言通过（_dw 非空且 _dw_res.passed；无断言时 _dw_res 未赋值，安全跳过）
        _dw_ok = False
        try:
            _dw_ok = bool(_dw and _dw_res.get("passed"))
        except (NameError, AttributeError):
            _dw_ok = False
        if _dw_ok:
            _audit_rep["done_when"] = {"tool": ["execute_command"], "claimed": True}
        if _audit_rep:
            _audit_recs = read_audit_records(session_id=session_id)
            _audit_res = verify_completion_report(_audit_rep, _audit_recs)
            if not _audit_res["passed"]:
                logger.info(
                    f"[sub:{sub_task_id}] [SAVE_STATE] 审计复核未通过，拒绝标记 done: {'；'.join(_audit_res['failures'])[:300]}"
                )
                return False
    except Exception as _audit_e:
        logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 审计复核异常(忽略): {_audit_e}")
    return True


def _validate_task_completion(messages, session_id, sub_task_id=None):
    """H1 提取: 任务类型副作用校验(标记 done 前检查是否真正写入)。返回 True=可标记/False=拒绝。"""
    if True:
        _task_type = _classify_task_type(messages)
        # #192 增强：不管工具类型，git diff 检测到实际文件变更即视为有效写入
        _has_write = _has_git_diff()
        if _task_type == "code_modify" and not _has_write:
            logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 拒绝虚假完成：代码修改任务但无写入操作")
            return False
        elif _task_type == "delivery" and not _has_write:
            logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 拒绝虚假完成：交付任务但无写入操作")
            return False
        elif _task_type == "discussion":
            # 结构化优先：tool result 中 consensus=True → 通过
            _has_consensus = False
            for _m in messages[-6:]:
                if _m.get("role") == "tool":
                    _res = _m.get("result")
                    if isinstance(_res, str):
                        try:
                            _res = json.loads(_res)
                        except Exception:
                            _res = None
                    if isinstance(_res, dict) and _res.get("consensus") is True:
                        _has_consensus = True
                        break
            # 兜底：JSON 片段 / 共识文本
            if not _has_consensus:
                _last_ctx = str(messages[-6:])
                _has_consensus = '"consensus": true' in _last_ctx or "✅ 已达成共识" in _last_ctx or "达成共识" in _last_ctx
            if not _has_consensus:
                logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 拒绝虚假完成：讨论任务但未达成共识")
                return False
        elif _task_type == "planning":
            if not _planning_output_valid(messages, session_id):
                logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 拒绝虚假完成：计划任务但无计划输出")
                return False
        elif _task_type == "analysis":
            if not _has_write:
                logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 拒绝虚假完成：分析任务但无文件产出（需写入 report.md 或 BRIEF.md）")
                return False
        elif _task_type == "general":
            if not _has_write:
                logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 拒绝虚假完成：通用任务但无写入操作")
                return False
    return True


def _execute_agent_task(
    user_id,
    session_id,
    messages,
    model,
    task_id,
    sub_task_id=None,
    on_done=None,
    on_fail=None,
    sandbox_base=None,
    parent_goal_id=None,
):
    """后台执行 Agent 任务，循环处理 tool_calls 直到完成

    on_done(task_id, user_id, session_id, output) / on_fail(task_id, user_id, session_id, reason)
    为长线任务循环回调（#31）：完成后驱动任务队列自动取下一个。
    任务3: sandbox_base 可选覆盖（子任务独立沙箱）
    #4: parent_goal_id 可选 — 子任务继承父 goal, turn_end 关联父 goal(子会话查无时回退 get_goal_by_id)
    """
    import json as _json

    _sb_task3 = sandbox_base or _get_sandbox_base(user_id, session_id)
    # 重复工具提醒: 新任务开始重置计数(agent_id = sub_task_id or task_id)
    try:
        from core.gateway.repeat_tool_reminder import reset as _rtr_reset

        _rtr_reset(sub_task_id or task_id)
    except Exception:
        pass
    from core.lib.context_manager import ContextManager
    from core.lib.gateway_helpers import preserve_error_context, recap_checkpoint
    from core.lib.v8.adapters.deepseek_adapter import DeepSeekAdapter

    # #31 长线任务回调 helper（异常不影响主线程结果）— H1 提级为模块函数
    def _notify_done(output=""):
        _notify_done_impl(on_done, task_id, user_id, session_id, sub_task_id, output)

    def _notify_fail(reason=""):
        _notify_fail_impl(on_fail, task_id, user_id, session_id, sub_task_id, reason)

    _sid = f"{session_id}_{sub_task_id}" if sub_task_id else session_id
    # ===== no_context 修复(2026-09-11): 主任务启动即生成 BRIEF.md(续跑权威上下文) =====
    # 【A2 结案 2026-09-13 批72】本块与 core/gateway/resume_context.py 的
    #   ensure_resumable_context() **职责不同，刻意不合并**（老板批70 拍板 A2）。
    #   逐条比对（批70）确认 helper 是**超集**，4 处行为差异：
    #     ① 适用条件：本块仅主任务；helper 不分主次
    #     ② 任务文本来源：本块取最后一条 user 消息；helper 走四级兜底链
    #     ③ 本块**不写** last_task 到 .agent_state.json；helper 写
    #     ④ BRIEF 生成条件：本块 load() is None 才生成（=下方注释「已存在则不重写」）；
    #        helper 在「任务已换」时会**重生成**
    #   ⇒ 事件型（本块，保守不动已有 BRIEF）与启动型（helper，保证可续跑）是分工，
    #     不是重复。**合并会同时改变这三件事，故保留两处。**
    #   关联体检项 42：重复实现判定后若两者职责不同 → 保留，不合并（理由是分工不是技术）。
    # 仅主任务(sub_task_id 为空); 已存在则不重写(保留「继续」时的执行进度)。
    if not sub_task_id:
        try:
            _last_task_msg = ""
            for _m in messages or []:
                if isinstance(_m, dict) and _m.get("role") == "user":
                    _last_task_msg = str(_m.get("content", "") or "")
            if _last_task_msg:
                from core.lib.brief_manager import get_brief_manager

                _bm = get_brief_manager(user_id, session_id)
                if _bm.load() is None:
                    _bm.generate(_last_task_msg)
        except Exception as _bg_err:
            logger.info(f"[sub:{sub_task_id}] [BRIEF] 主任务 BRIEF.md 生成失败(忽略): {_bg_err}")
    # F0.2b async: waiting_user 契约短路(暂停, 不跑执行循环)
    try:
        from core.gateway.task_contract import waiting_user_payload as _wup_a

        _wu_a = _wup_a(_sid)
        if _wu_a:
            print(f"[CONTRACT] async {_sid} waiting_user 短路: {str(_wu_a.get('question'))[:60]}")
            _save_status = Path(f"data/projects/{user_id}/{_sid}/.task_state.json")
            try:
                import json as _j_a

                _save_status.parent.mkdir(parents=True, exist_ok=True)
                _save_status.write_text(
                    _j_a.dumps({"status": "waiting_user", "question": _wu_a.get("question", ""), "task_id": task_id}),
                    encoding="utf-8",
                )
            except Exception:
                pass
            if on_done:
                try:
                    on_done({"status": "waiting_user", "question": _wu_a.get("question", "")})
                except Exception:
                    pass
            return
    except Exception as _e_a:
        print(f"[CONTRACT] async 接线异常(忽略): {_e_a}")

    state_file = Path(f"data/projects/{user_id}/{_sid}/.task_state.json")

    # P2: 失败路径统一写入 agent_actions 审计表(tool_name=failed, result={code,message})
    def _record_failure_action(code, message, detail_note=""):
        """失败记录: 进入 SAG 审计表 agent_actions(借鉴 Harness 失败可审计性)"""
        try:
            from core.lib.code_entity_extractor import extractor as _fail_extractor

            _fail_extractor.insert_agent_action(
                session_id=_sid,
                task_name=_task_name_async or task_id,
                tool_name="failed",
                result=_json.dumps({"code": code, "message": str(message)[:300]}, ensure_ascii=False),
                file_type="task_failure",
                agent_reaction="",
                detail=f"step={_round} {detail_note}".strip(),
            )
        except Exception as _fail_rec_err:
            logger.info(f"[sub:{sub_task_id}] [FAIL_REC] agent_actions 写入失败(忽略): {_fail_rec_err}")

    def _save_state(status, content=None, tokens=0):
        # 副作用校验：标记 done 前检查是否真正执行了写入操作
        if not _validate_task_completion(messages, session_id, sub_task_id):
            return
        # done_when 断言：未满足则拒绝标记 done
        _dw_res = (
            None  # 修复: 无 done_when 配置时 _dw_res 未赋值, 下方 _audit_cross_check_save 引用会 UnboundLocalError（子任务 session 实测暴露）
        )
        try:
            from core.lib.verification_chain import _check_done_when

            _dw = _get_task_done_when(session_id)
            if _dw:
                _dw_res = _check_done_when(_dw, _sb_task3)
                if not _dw_res["passed"]:
                    logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 拒绝完成：done_when 未满足 → {_dw_res['detail']}")
                    return
        except Exception as _dw_e:
            logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] done_when 检查异常: {_dw_e}")
        if not _audit_cross_check_save(messages, session_id, sub_task_id, _dw, _dw_res):
            return
        _save_data = {"status": status, "content": content, "tokens": tokens, "updated": datetime.now().isoformat()}
        _last_usr = ""
        for _m in messages:
            if _m["role"] == "user":
                _last_usr = _m["content"]
        if _last_usr:
            _save_data["last_task"] = _last_usr[:200]
            _save_data["last_task_status"] = status  # "done" 或 "paused"
            _save_data["last_task_at"] = time.time()
        state_file.parent.mkdir(parents=True, exist_ok=True)  # V9 修复：首次执行时目录可能不存在
        state_file.write_text(_safe_serialize_state(_save_data), encoding="utf-8")
        # ===== BRIEF.md 执行进度同步：步骤完成/失败/暂停 → update_progress =====
        try:
            from core.lib.brief_manager import get_brief_manager

            _step_name = sub_task_id if sub_task_id else "主任务"
            get_brief_manager(user_id, session_id).update_progress(
                step=_step_name, status=status, summary=(content or "")[:120]
            )
        except Exception as _bp_err:
            logger.info(f"[sub:{sub_task_id}] [BRIEF_PROGRESS] update_progress 失败: {_bp_err}")
        # ===== 子任务完成 → 写主 .agent_state.json 的 subtasks 标记 =====
        if sub_task_id and status == "done":
            try:
                import fcntl as _fcntl  # #192 并发修复：主 .agent_state.json 加文件锁

                _main_agent_state = Path(f"data/projects/{user_id}/{session_id}/.agent_state.json")
                _main_agent_state.parent.mkdir(parents=True, exist_ok=True)
                _main_agent_data = {}
                # fcntl.flock 排它锁：多子线程并发写回主 state 时串行化，避免覆盖/半写
                with open(_main_agent_state, "a+", encoding="utf-8") as _main_f:
                    _fcntl.flock(_main_f.fileno(), _fcntl.LOCK_EX)
                    try:
                        _main_f.seek(0)
                        _main_raw = _main_f.read()
                        if _main_raw.strip():
                            _main_agent_data = _json.loads(_main_raw)
                    except Exception:
                        _main_agent_data = {}
                    # 任务3 v7: subtasks 字段可能是 str(旧数据/异常结构), 非 dict 时重置避免 item assignment 报错
                    _subtasks_map = _main_agent_data.get("subtasks")
                    if not isinstance(_subtasks_map, dict):
                        _subtasks_map = {}
                        _main_agent_data["subtasks"] = _subtasks_map
                    # 任务3 v9: 保留已有 depth(委托深度预算持久化——submit 时写入, done 时 merge 不覆盖)
                    _sub_existing = _subtasks_map.get(sub_task_id) or {}
                    _subtasks_map[sub_task_id] = {
                        **_sub_existing,
                        "status": "done",
                        "updated": datetime.now().isoformat(),
                    }
                    _main_f.seek(0)
                    _main_f.truncate()
                    _main_f.write(_safe_serialize_state(_main_agent_data))
                    _main_f.flush()
                    _fcntl.flock(_main_f.fileno(), _fcntl.LOCK_UN)
                logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 子任务 {sub_task_id} 完成 → 主 .agent_state.json subtasks 已标记")
            except Exception as _sub_mark_e:
                logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] 子任务 subtasks 标记写入失败: {_sub_mark_e}")
        # ===== Git 提交：.agent_state.json 状态文件 =====
        try:
            import subprocess as _sub

            _agent_dir = _sb_task3
            if not (_agent_dir / ".git").exists():
                logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] Git 仓库不存在（未找到 .git 目录），跳过提交")
            else:
                _proc.run_hidden(
                    ["git", "-C", str(_agent_dir), "add", ".agent_state.json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                _diff_res = _proc.run_hidden(
                    ["git", "-C", str(_agent_dir), "diff", "--cached"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if not _diff_res.stdout.strip():
                    logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] Git diff 为空，可能文件路径错误，请检查")
                else:
                    _commit_msg = f"state: {status}"
                    _proc.run_hidden(
                        ["git", "-C", str(_agent_dir), "commit", "-m", _commit_msg],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] Git 已提交: {_commit_msg}")
        except Exception as _git_err:
            logger.info(f"[sub:{sub_task_id}] [SAVE_STATE] Git 提交异常: {_git_err}")

        # ===== 自学习失败反馈(A): 任务失败 → SAG 负反馈 + 边缘降权(补审计断链 4b/4c) =====
        # 成功侧已有 _update_sag_feedback(passed=True) + _update_sag_edge_learning(done 分支);
        # 失败侧之前无任何 feedback → 负反馈 weight-0.05 / 失败 known_issues 沉淀
        if status == "failed":
            try:
                _update_sag_feedback(
                    _last_usr[:80] if _last_usr else "task_failed", session_id, user_id, messages, passed=False
                )
            except Exception as _fb_fail_e:
                logger.info(f"[sub:{sub_task_id}] [SAG_FEEDBACK] failed 反馈异常: {_fb_fail_e}")
            try:
                _update_sag_edge_learning("save_state_failed", session_id, user_id, messages)
            except Exception as _edge_fail_e:
                logger.info(f"[sub:{sub_task_id}] [SAG_EDGE] failed 边缘学习异常: {_edge_fail_e}")
            # 失败沉淀 known_issues(用户级, 供后续会话注入)
            try:
                from core.gateway.memory import remember_issue as _mem_issue_f

                _mem_issue_f(user_id, f"任务失败: {(content or _last_usr or '')[:160]}")
            except Exception:
                pass

        # ===== #145 数字资产自动文件化：_save_state("done") 时归档当前任务的 messages 摘要 =====
        if status == "done":
            _persist_retrieval_cache()  # #192 检索缓存落盘（任务完成）
            try:
                _done_kind = "report"
                _done_task_type = _classify_task_type(messages)
                if _done_task_type == "planning":
                    _done_kind = "plan"
                _done_title = (_last_usr or content or "任务完成")[:120]
                _done_content = content or ""
                if not _done_content:
                    _done_content = "\n".join(
                        f"[{_m.get('role','')}] {str(_m.get('content',''))[:300]}"
                        for _m in messages[-10:]
                        if _m.get("content")
                    )
                _archived_done = _archive_asset(_done_kind, session_id, _done_title, _done_content[:4000], messages)
                if _archived_done:
                    logger.info(f"[sub:{sub_task_id}] [AUTO_ARCHIVE] _save_state(done) 归档 -> {_archived_done}")
                # summary_{timestamp}.jsonl 追加式日志：当前任务 messages 逐条摘要
                _sum_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                _sum_dir = Path(f"data/plans/{session_id}")
                _sum_dir.mkdir(parents=True, exist_ok=True)
                _sum_file = _sum_dir / f"summary_{_sum_ts}.jsonl"
                _sum_lines = []
                for _m_sum in messages:
                    _rec_sum = {
                        "role": _m_sum.get("role", ""),
                        "content": str(_m_sum.get("content", "") or "")[:1000],
                        "ts": datetime.now().isoformat(),
                    }
                    if _m_sum.get("tool_calls"):
                        _rec_sum["tool_calls"] = [
                            str(_tc.get("function", {}).get("name", "")) for _tc in _m_sum["tool_calls"]
                        ]
                    _sum_lines.append(json.dumps(_rec_sum, ensure_ascii=False))
                with open(_sum_file, "a", encoding="utf-8") as _sf_sum:
                    _sf_sum.write("\n".join(_sum_lines) + "\n")
                logger.info(
                    f"[sub:{sub_task_id}] [AUTO_ARCHIVE] _save_state(done) 摘要日志 -> {_sum_file} ({len(_sum_lines)} 行)"
                )
                # 同时调 store_step_summary 入库 SAG
                try:
                    from core.lib.code_entity_extractor import extractor as _sum_extractor

                    _sum_extractor.store_step_summary(
                        task_name=f"summary_{session_id}_{_sum_ts}",
                        step_number=1,
                        summary_json={
                            "kind": "summary",
                            "session_id": session_id,
                            "lines": len(_sum_lines),
                            "file": str(_sum_file),
                            "source": "save_state_done",
                            "ts": datetime.now().isoformat(),
                        },
                    )
                    logger.info(f"[sub:{sub_task_id}] [AUTO_ARCHIVE] 摘要已入库 SAG: summary_{session_id}_{_sum_ts}")
                except Exception as _sum_e:
                    logger.info(f"[sub:{sub_task_id}] [AUTO_ARCHIVE] 摘要 SAG 入库失败: {_sum_e}")
            except Exception as _e_done_ar:
                logger.info(f"[sub:{sub_task_id}] [AUTO_ARCHIVE] _save_state(done) 归档失败: {_e_done_ar}")
            # ===== 边缘学习：任务完成后更新 SAG code_edges 评分（#81 过滤网自学习闭环）=====
            try:
                # H1 修复：改用 sag_feedback._update_sag_edge_learning（正确 #81 实现，原被本地僵尸嵌套函数遮蔽）
                _edge_updated = _update_sag_edge_learning(
                    task_name="save_state_done",
                    session_id=session_id,
                    user_id=user_id,
                    messages=messages,
                )
                logger.info(f"[sub:{sub_task_id}] [SAG_EDGE] _save_state(done) 边缘学习更新={_edge_updated}")
            except Exception as _edge_done_e:
                logger.info(f"[sub:{sub_task_id}] [SAG_EDGE] _save_state(done) 边缘学习失败: {_edge_done_e}")
            # ===== 主动压缩：total_rounds 为 10 的倍数 或 tokens > 50000 时压缩旧轮次 =====
            try:
                _total_rounds = _round + 1  # _round 为 0-based 循环变量，+1 得到 total_rounds
                _tokens_before = _estimate_tokens(messages)
                if _total_rounds % 10 == 0 or _tokens_before > 50000:
                    _recap_compress = recap_checkpoint(_task_name_async, _total_rounds)
                    if _recap_compress:
                        # 保留 system 头 + 最近 4 条消息，中间旧轮次替换为压缩摘要
                        _head_comp = []
                        for _m_comp in messages:
                            if _m_comp.get("role") == "system":
                                _head_comp.append(_m_comp)
                            else:
                                break
                        _tail_comp = messages[-4:] if len(messages) > 4 else messages[:]
                        # 修复：tail 首条为 tool 时找回配对 assistant
                        if _tail_comp and _tail_comp[0].get("role") == "tool":
                            _tc_id = _tail_comp[0].get("tool_call_id")
                            _matched = None
                            for _m in messages:
                                if _m.get("role") == "assistant" and _m.get("tool_calls"):
                                    if any(
                                        isinstance(_tc, dict) and _tc.get("id") == _tc_id for _tc in _m["tool_calls"]
                                    ):
                                        _matched = _m
                                        break
                            if _matched is None:
                                _tail_comp.pop(0)
                            elif _matched not in _tail_comp:
                                _tail_comp.insert(0, _matched)
                        _summary_comp = {
                            "role": "system",
                            "content": f"[AUTO_COMPRESS] 旧轮次已压缩为摘要：\n{_recap_compress[:2000]}",
                        }
                        messages[:] = _head_comp + [_summary_comp] + _tail_comp
                        # 唯一出口: 配对修复 + tool_calls 结构规范化
                        messages[:] = _finalize_messages(messages)
                        _tokens_after = _estimate_tokens(messages)
                        _guard_log(
                            "AUTO_COMPRESS",
                            f"[AUTO_COMPRESS] 压缩完成，tokens: {_tokens_before} → {_tokens_after}",
                            "auto_compress.log",
                        )
            except Exception as _e_compress:
                _guard_log("AUTO_COMPRESS", f"[AUTO_COMPRESS] 压缩失败: {_e_compress}", "auto_compress.log")
            # ===== #166 强制验证检查：修改类任务必须有 py_compile / read_file 验证记录 =====
            try:
                _verify_task_type = _classify_task_type(messages)
                if _verify_task_type == "code_modify":
                    _verify_text = " ".join(
                        str(_m.get("content", ""))
                        + " "
                        + " ".join(str(_tc.get("function", {}).get("name", "")) for _tc in (_m.get("tool_calls") or []))
                        for _m in messages
                    )
                    if "py_compile" not in _verify_text and "read_file" not in _verify_text:
                        logger.info(
                            f"[sub:{sub_task_id}] [VERIFY_MISSING] 修改类任务缺少验证记录（py_compile/read_file）：task={task_id}, type={_verify_task_type}"
                        )
            except Exception as _e_verify:
                logger.info(f"[sub:{sub_task_id}] [VERIFY_MISSING] 强制验证检查异常: {_e_verify}")
            # ===== #167 副本自动合并正本：AUTO_ARCHIVE 之后触发 =====
            try:
                _main_repo = _resolve_main_repo(user_id, session_id)
                if _main_repo is None:
                    logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] 未定位正本仓库，跳过合并")
                else:
                    _now_merge = time.time()
                    _merge_key = f"{user_id}:{session_id}"
                    _last_merge = _auto_merge_cooldown.get(_merge_key, 0)
                    if _now_merge - _last_merge < 120:
                        logger.info(
                            f"[sub:{sub_task_id}] [AUTO_MERGE] 冷却期内（{int(_now_merge - _last_merge)}s/300s），跳过合并"
                        )
                    elif not _check_recent_task_progress_completed(session_id):
                        logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] task_progress 最近 3 条未全部 completed，跳过合并")
                    else:
                        # 从 task_progress.completed_steps 收集变更文件列表
                        _merge_files = []
                        _sb_dir = _main_repo / "data" / "projects" / str(user_id) / str(session_id) / "clawsjoy_dev"
                        # ===== #192 AUTO_MERGE 并发保护：读取主 .task_state.json 前加 fcntl 共享锁 =====
                        import fcntl

                        _merge_lock_fd = None
                        try:
                            _merge_lock_path = (
                                _main_repo / "data" / "projects" / str(user_id) / str(session_id) / ".task_state.json"
                            )
                            if _merge_lock_path.exists():
                                _merge_lock_fd = open(str(_merge_lock_path), "r", encoding="utf-8")
                                fcntl.flock(_merge_lock_fd, fcntl.LOCK_SH)
                        except Exception as _e_lock:
                            logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] 加共享锁失败（继续无锁执行）: {_e_lock}")
                            _merge_lock_fd = None

                        for _tp_path in (
                            _sb_dir / ".agent_state.json",
                            _main_repo / "data" / "projects" / str(user_id) / str(session_id) / ".task_state.json",
                        ):
                            try:
                                if _tp_path.exists():
                                    _tp_state = json.loads(_tp_path.read_text(encoding="utf-8"))
                                    _tp_obj = _tp_state.get("task_progress") or {}
                                    if isinstance(_tp_obj, str):
                                        try:
                                            _tp_obj = json.loads(_tp_obj)
                                        except Exception:
                                            _tp_obj = {}
                                    for _step in (
                                        (_tp_obj.get("completed_steps") or []) if isinstance(_tp_obj, dict) else []
                                    ):
                                        if not isinstance(_step, dict):
                                            continue
                                        _f = _step.get("file") or _step.get("file_path") or ""
                                        if isinstance(_f, str):
                                            _f = _f.strip().lstrip("/")
                                            # 网关路径可能带 clawsjoy_dev/ 前缀，剥离
                                            if _f.startswith("clawsjoy_dev/"):
                                                _f = _f[len("clawsjoy_dev/") :]
                                        if _f and _f not in _merge_files:
                                            _merge_files.append(_f)
                            except Exception:
                                pass
                        # 强制追加 agent_gateway_enhanced.py
                        if "agent_gateway_enhanced.py" not in _merge_files:
                            _merge_files.append("agent_gateway_enhanced.py")
                        # py_compile 检查（仅变更的 .py）
                        _merge_py = [f for f in _merge_files if str(f).endswith(".py")]
                        _compile_fail = _py_compile_files(_merge_py, _sb_dir)
                        if _compile_fail:
                            logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] py_compile 失败，跳过合并: {_compile_fail}")
                        else:
                            _merge_res = _auto_merge_to_main(user_id, session_id, _merge_files)
                            _auto_merge_cooldown[_merge_key] = time.time()
                            logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] 触发完成: {_merge_res}")
                            # 合并完成，释放共享锁
                            if _merge_lock_fd is not None:
                                try:
                                    fcntl.flock(_merge_lock_fd, fcntl.LOCK_UN)
                                    _merge_lock_fd.close()
                                except Exception as _e_unlock:
                                    logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] 释放锁异常: {_e_unlock}")
                            # #192 子线程完成后清理孤儿目录 data/projects/{user_id}/{session_id}_{sub_task_id}
                            if sub_task_id:
                                _orphan_dir = Path("data/projects") / str(user_id) / f"{session_id}_{sub_task_id}"
                                try:
                                    if _orphan_dir.exists():
                                        import shutil

                                        shutil.rmtree(_orphan_dir, ignore_errors=True)
                                        logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] 子线程孤儿目录已清理: {_orphan_dir}")
                                except Exception as _e_orphan:
                                    logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] 清理孤儿目录异常: {_e_orphan}")
            except Exception as _e_merge:
                logger.info(f"[sub:{sub_task_id}] [AUTO_MERGE] 自动合并异常: {_e_merge}")
        # ===== #81 过滤网自学习：任务完成时基于本次会话 tool_calls 更新过滤网 =====
        try:
            _learned = _run_filter_net_learning(user_id, session_id, messages, content)
            if _learned:
                logger.info(f"[sub:{sub_task_id}] [FILTER_NET] #81 自学习完成: {_learned}")
        except Exception as _e_learn:
            logger.info(f"[sub:{sub_task_id}] [FILTER_NET] #81 自学习异常: {_e_learn}")

    _task_name_async = ""
    for _m in messages:
        if _m["role"] == "user":
            _task_name_async = _m["content"][:80]
            break
    # 2026-09-06 诊断: dump async 入口原始 messages 结构到 logger(定位 400 触发源)
    try:
        _adbg_summ = "; ".join(
            "%s(rc=%s tc=%d %s)"
            % (
                m.get("role"),
                "Y" if "reasoning_content" in m else "N",
                len(m.get("tool_calls") or []),
                str(m.get("content") or "")[:40],
            )
            for m in messages
        )
        logger.info(
            f"[sub:{sub_task_id}] [REQ_DUMP] n={len(messages)} task={_task_name_async[:50]} :: {_adbg_summ[:1500]}"
        )
    except Exception:
        pass
    messages = cleanup_task_context(messages, _task_name_async, user_id, session_id)
    # 2026-09-06: async 路径同样剥离前端带来的 assistant reasoning_content(同步路径在
    # v9_agent_chat 已做 RC_STRIP, async 提交绕过该入口) — DeepSeek thinking 只接受
    # tool_calls 轮 reasoning, 纯文本旧收尾 reasoning 带入新任务 → 400。
    try:
        _rc_strip_n = 0
        for _m_rc2 in messages:
            if _m_rc2.get("role") == "assistant" and _m_rc2.get("reasoning_content") is not None:
                _m_rc2.pop("reasoning_content", None)
                _rc_strip_n += 1
        if _rc_strip_n:
            logger.info(f"[sub:{sub_task_id}] [RC_STRIP] async 入口剥离 {_rc_strip_n} 条 reasoning_content")
    except Exception:
        pass
    _agent_name_task = ""
    # 精准投喂：收缩为 LoopContextManager().inject_precision_only 调用
    try:
        _agent_pos = ""
        try:
            _state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
            if _state_file.exists():
                _state_data = json.loads(_state_file.read_text(encoding="utf-8"))
                _agent_name_task = _state_data.get("agent_name", "")
                if _agent_name_task:
                    _member_task = roster_engine.get("default", _agent_name_task)
                    if _member_task:
                        _agent_pos = _member_task.get("position", "")
        except Exception:
            pass
        from core.lib.v8.loop_context_manager import LoopContextManager

        _feed_text = LoopContextManager().inject_precision_only(
            task_name=_task_name_async,
            step_number=1,
            user_id=user_id,
            session_id=session_id,
            position=_agent_pos,
        )
        if _feed_text:
            messages.insert(0, {"role": "system", "content": _feed_text})
    except Exception:
        pass

    import threading as _th

    logger.info(
        f"[sub:{sub_task_id}] [V9] thread={_th.current_thread().name}, key_in_environ={'DEEPSEEK_API_KEY' in os.environ}, key_len={len(os.environ.get('DEEPSEEK_API_KEY',''))}"
    )
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        logger.info(f"[sub:{sub_task_id}] [V9] DeepSeek API Key 未配置，降级到 Ollama")
        # 不 return，继续执行，模型自动降级

    try:
        _task_start = time.time()
        _MAX_TASK_SECONDS = 600  # V9 修复：任务级超时保护（工具循环+LLM），超时强制结束防卡死
        _all_tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "strict": True,
                    "description": "读取文件内容。搜索代码内容时用 search 参数，如 read_file(path='xxx.py', search='关键词')",
                    "parameters": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "path": {"type": "string"},
                            "function": {"type": "string"},
                            "search": {"type": "string"},
                            "lines_start": {"type": "integer"},
                            "lines_end": {"type": "integer"},
                            "verify_line": {"type": "integer"},
                            "verify_expected": {"type": "string"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "strict": True,
                    "description": "写入文件",
                    "parameters": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                            "line": {"type": "integer", "description": "按行修改：指定行号"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "strict": True,
                    "description": "列出目录",
                    "parameters": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_files",
                    "strict": True,
                    "description": "只搜索文件名，不搜代码内容。搜代码用 read_file 的 search 参数",
                    "parameters": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"query": {"type": "string"}, "path": {"type": "string"}},
                        "required": ["query", "path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "strict": True,
                    "description": "执行命令",
                    "parameters": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_index",
                    "strict": True,
                    "description": "SAG 代码实体索引查询。连续 3 次空结果会熔断，熔断后改用 read_file 的 search 参数",
                    "parameters": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            },
        ]
        # P1-1 工具预设模式：按模式过滤 Agent 可见的工具列表（minimal 只暴露核心 3 工具）
        # 取真实用户任务(跳过 [系统] 注入上下文, 防快照/steer 误分类模式)
        from core.lib.gateway_helpers import last_user_task_msg

        _task_hint = last_user_task_msg(messages)
        _mode_tools = get_mode_tools(session_id, _task_hint)
        tools = [t for t in _all_tools if t["function"]["name"] in _mode_tools]
        # V9 修复：无 DEEPSEEK_API_KEY 时降级 Ollama 本地工具模式（原降级是空壳，仍调 DeepSeek 外网）
        _use_ollama_v9 = not api_key
        adapter = DeepSeekAdapter(api_key=api_key, model=model) if not _use_ollama_v9 else None
        # #6 maxSteps 硬限制: max_rounds 从 execution_policy.yaml 读取(默认 30), 超限 _save_state("timeout") 强制终止
        try:
            from core.gateway.shared_state import _load_v9_execution_policy

            _exec_budget = (_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}
            max_rounds = int(_exec_budget.get("max_steps", 30) or 30)
        except Exception:
            max_rounds = 30  # fallback 默认值
        _heartbeat_minutes = int(os.getenv("CLAWSJOY_HEARTBEAT_MINUTES", "5"))
        _last_heartbeat = time.time()
        _task_name_heartbeat = _task_name_async or "unknown"
        total_tokens = 0

        # 前置检测：文件是否已满足任务需求（Agent 循环之前）
        _last_user_msg = ""
        for _m in reversed(messages):
            if _m["role"] == "user":
                _last_user_msg = _m["content"]
                break
        if _last_user_msg:
            import re as _re_pre

            _write_kw = ["添加", "创建", "修改", "新增", "加入", "实现", "编写", "补充"]
            _has_write = any(kw in _last_user_msg for kw in _write_kw)
            if _has_write:
                _target_match = _re_pre.search(r"[\w_]+/[\w_]+\.\w+", _last_user_msg)
                if _target_match:
                    _target_file = _target_match.group(0)
                    _base = _sb_task3
                    _disk_paths = [
                        _base / _target_file,
                        _base / _target_file,
                    ]
                    _found = None
                    for _dp in _disk_paths:
                        if _dp.exists():
                            _found = _dp
                            break
                    if not _found:
                        import glob as _glob

                        _fname = _target_file.split("/")[-1]
                        _candidates = _glob.glob(str(_base / "**" / _fname), recursive=True)
                        for _c in _candidates:
                            _cp = Path(_c)
                            if _cp.exists() and "resume-optimizer" in str(_cp):
                                _found = _cp
                                break
                        if not _found:
                            for _c in _candidates:
                                _cp = Path(_c)
                                if _cp.exists():
                                    _found = _cp
                                    break
                    if _found:
                        try:
                            import ast as _ast_pre

                            _content = _found.read_text(encoding="utf-8")
                            if _found.suffix == ".py":
                                _ast_pre.parse(_content)
                            # 前置检测防误判：计划文本（执行计划/修改计划/步骤列表等）不作为"文件已包含功能"依据
                            _plan_prefixes = ("执行计划", "修改计划", "任务计划", "实施计划", "开发路线", "步骤列表", "实施步骤")
                            _is_plan_text = _last_user_msg.strip().startswith(_plan_prefixes) or any(
                                _pp in _last_user_msg[:40] for _pp in _plan_prefixes
                            )
                            _kw_raw = _re_pre.sub(r"[^一-鿿a-zA-Z0-9]", " ", _last_user_msg if not _is_plan_text else "")
                            _kw = _re_pre.findall(r"[一-鿿]{2,}|[a-zA-Z_]{3,}", _kw_raw)
                            _noise = {"resume", "optimizer", "analysis_page", "py", "markdown", "文件", "点击后将", "分析结果导出为"}
                            _action_pre = {
                                "添加",
                                "创建",
                                "修改",
                                "删除",
                                "新增",
                                "加入",
                                "实现",
                                "编写",
                                "补充",
                                "完善",
                                "点击",
                                "中添加",
                                "点击后",
                                "分析结果导出",
                                "点击后将分析结果导出为",
                            }
                            _kw = [
                                k
                                for k in _kw
                                if k.lower() not in _noise
                                and k not in _action_pre
                                and not (k.isascii() and k.isalpha())
                            ]
                            _matched_pre = sum(1 for k in _kw if k.lower() in _content.lower())
                            if _kw and _matched_pre >= max(2, len(_kw) * 0.5):
                                # 关键词匹配仅作提示，不作为完成依据；必须由主循环执行真实写入
                                logger.info(
                                    f"[sub:{sub_task_id}] [V9 async] 前置检测提示：文件已包含任务关键词（{', '.join(_kw[:5])}），仍需实际写入以完成任务"
                                )
                        except (SyntaxError, UnicodeDecodeError):
                            pass
        _ctx_mgr = ContextManager()
        _round = 0  # 初始化轮次计数器，用于异常处理
        # P2b 修复: 确保用户消息写入日志(2026-09-07 与 bridge 对齐 — 任务边界语义)
        # 原「content 不在全量投影就写」会吞同文本重试 / 把 [系统] 注入写成任务边界 → 死循环。
        # 现: 只写最后一条真实 user; "[系统]" 前缀记 runtime_context; 15s 内同内容防双写。
        try:
            import time as _t_um

            from core.gateway.session_log import EV_USER_MESSAGE as _EV_UM_E
            from core.gateway.session_log import get_session_log

            _slog = get_session_log(_sid)
            _last_um = None
            for _m_in in reversed(messages):
                if _m_in.get("role") == "user" and _m_in.get("content"):
                    _last_um = _m_in
                    break
            if _last_um is not None:
                _utxt_e = str(_last_um.get("content", ""))
                if _utxt_e.startswith("[系统]"):
                    _slog.append("user_message", {"role": "system", "content": _utxt_e, "source": "runtime_context"})
                else:
                    _recent_same_e = False
                    _now_e = _t_um.time()
                    for _ev_e in reversed(_slog.events()):
                        if _ev_e.type == _EV_UM_E and _ev_e.payload.get("source") == "user_input":
                            if _ev_e.payload.get("content") == _utxt_e and (_now_e - float(_ev_e.ts or 0)) < 15:
                                _recent_same_e = True
                            break
                    if not _recent_same_e:
                        _slog.append("user_message", {"role": "user", "content": _utxt_e, "source": "user_input"})
        except Exception:
            pass
        # P2b 切换读取: 每轮从事件日志重建 messages(derive_messages 唯一入口, 替代内存累积)。
        # 2026-09-06: last_task_only=True 与同步路径(v9_agent_chat bridge)对齐 —
        # async 原用全量投影, 跨任务旧事件(含 thinking reasoning)会带入本轮 → DeepSeek 400
        # reasoning_content must be passed back。
        try:
            from core.gateway.session_log import get_session_log

            messages = get_session_log(_sid).derive_messages(last_task_only=True)
        except Exception:
            pass
        # 唯一出口: derive 重建会丢 reasoning_content(tool_calls assistant 必须带该字段) — 重建后立即 finalize
        try:
            from core.gateway.message_assembler import _finalize_messages

            messages = _finalize_messages(messages)
        except Exception:
            pass
        # Turn 协议 Step2: turn_start
        try:
            from core.gateway.session_log import log_event as _log_exec_turn

            _exec_turn_id = int(time.time())
            from core.gateway.session_log import EV_TURN_START as _EV_TS

            _log_exec_turn(
                _sid,
                _EV_TS,
                {
                    "turn_id": _exec_turn_id,
                    "task_name": str((messages[0].get("content") if messages else ""))[:80],
                    "path": "execute_agent_task",
                },
            )
        except Exception:
            _exec_turn_id = 0

        def _write_exec_turn_end(_reason, _detail, _rounds=0):
            # P1: turn_end 关联 goal — 事件带 goal_id + progress delta(exec 路径按轮数推进)
            # #4: 子任务继承 — 子会话查无 goal 时回退 get_goal_by_id(parent_goal_id), 关联父 goal
            _goal_info_e = {}
            try:
                from core.gateway.goal_state import (
                    complete_goal,
                    get_goal_by_id,
                    get_goal_by_session_id,
                    update_goal_progress,
                )

                _g_e = get_goal_by_session_id(_sid)
                if _g_e is None and parent_goal_id:
                    _g_e = get_goal_by_id(parent_goal_id)
                if _g_e:
                    _g_uid = _g_e.get("user_id") or ""
                    _g_sid = _g_e.get("session_id") or _sid
                    _p_e = _g_e.get("progress") or {}
                    _prev_e = int(_p_e.get("done", 0) or 0)
                    _total_e = int(_p_e.get("total", 1) or 1)
                    _delta_e = _rounds if _reason != "completed" else max(_total_e - _prev_e, 0)
                    update_goal_progress(
                        _g_uid,
                        _g_sid,
                        done=_prev_e + _delta_e,
                        step=f"exec_turn{_exec_turn_id} rounds{_rounds}",
                        turn_id=_exec_turn_id,
                    )
                    if _reason == "completed" and _g_e.get("status") in ("active", "paused"):
                        complete_goal(_g_uid, _g_sid)
                    _goal_info_e = {
                        "goal_id": _g_e.get("goal_id"),
                        "progress_delta": {
                            "done": _delta_e,
                            "total": _total_e,
                            "pct": int(round((_prev_e + _delta_e) * 100 / _total_e)),
                        },
                    }
            except Exception:
                pass
            try:
                from core.gateway.session_log import EV_TURN_END as _EV_TE2
                from core.gateway.session_log import log_event as _log_ete

                _log_ete(
                    _sid,
                    _EV_TE2,
                    {
                        "turn_id": _exec_turn_id,
                        "reason": _reason,
                        "reason_detail": _detail,
                        "rounds": _rounds,
                        **_goal_info_e,
                    },
                )
            except Exception:
                pass
            # Step3 审计接入: exec 路径 turn reason 写入 ledger timeline
            try:
                from core.lib.v8.ledger import ledger

                ledger.record_event(
                    server_id=_sid,
                    agent_name="V9",
                    position="execute_agent_task",
                    action=f"turn_end:{_reason}",
                    summary=f"turn_id={_exec_turn_id} {_detail} rounds={_rounds}"[:300],
                )
            except Exception:
                pass
            # #8 审计告警: exec 路径 turn reason=error/blocked/cancelled → 通知老板
            if _reason in ("error", "blocked", "cancelled"):
                try:
                    from core.gateway.sandbox_util import notify_boss

                    notify_boss(
                        event_type="turn_end",
                        message=f"V9 子任务回合异常: {_reason} — {str(_detail)[:80]}",
                        detail=f"turn_id={_exec_turn_id} rounds={_rounds} session={_sid}",
                        level="error" if _reason == "error" else "warn",
                    )
                except Exception:
                    pass

        for _round in range(max_rounds):
            # P4 steer 全量迁移: exec 路径每轮消费 steer 通道(与 bridge_loop 同构,
            # 注入为 user 消息 → derive_messages 重建时保留, LLM 可见)
            try:
                from core.gateway.shared_state import drain_steer

                # P4: 消费两个键 — 子任务注入走 _sid, 工具层(tool_router)以父 session_id 写 steer
                _exec_steer = drain_steer(_sid) + (drain_steer(session_id) if _sid != session_id else [])
                if _exec_steer:
                    for _es in _exec_steer:
                        logger.info(f"[sub:{sub_task_id}] [STEER_INJECT] {str(_es)[:80]}")
                    messages = messages + [{"role": "user", "content": str(_s)[:500]} for _s in _exec_steer]
            except Exception:
                pass
            # #1 协作取消: exec 路径同构(每轮检查, 不硬杀)
            try:
                from core.gateway.shared_state import is_cancel_requested

                if is_cancel_requested(_sid):
                    logger.info(f"[sub:{sub_task_id}] [V9 CANCEL] 协作取消, 退出")
                    _write_exec_turn_end("cancelled", "协作取消(用户停止)", _round)
                    break
            except Exception:
                pass
            if time.time() - _task_start > _MAX_TASK_SECONDS:
                logger.info(f"[sub:{sub_task_id}] [V9 TIMEOUT] 任务执行超过 {_MAX_TASK_SECONDS}s，强制结束")
                break
            # 注意力聚焦：每 20 轮检查最近操作模式
            if _round > 0 and _round % 20 == 0:
                _recent_actions = []
                for _m in messages[-10:]:
                    for _tc in _m.get("tool_calls", []):
                        _recent_actions.append(_tc.get("function", {}).get("name", ""))
                if len(set(_recent_actions)) <= 2 and len(_recent_actions) >= 8:
                    # P4 steer 全量迁移: 纠偏指令走 steer 通道(本轮起点已消费, 下轮注入)
                    try:
                        from core.gateway.shared_state import add_steer

                        add_steer(
                            _sid,
                            f"[注意力检查] 最近 10 轮只用了 {len(set(_recent_actions))} 种工具。请重新审视全局目标，确认当前步骤是否偏离任务方向。必要时使用 read_file(function='函数名') 直接定位目标。",
                        )
                    except Exception:
                        messages.append(
                            {
                                "role": "system",
                                "content": f"[注意力检查] 最近 10 轮只用了 {len(set(_recent_actions))} 种工具。请重新审视全局目标，确认当前步骤是否偏离任务方向。必要时使用 read_file(function='函数名') 直接定位目标。",
                            }
                        )
            # 心跳检查：每 N 分钟保存 checkpoint
            if time.time() - _last_heartbeat > _heartbeat_minutes * 60:
                try:
                    from core.lib.progress_manager import ProgressManager

                    _pm = ProgressManager(user_id, _sid)
                    _pm.save_checkpoint(
                        _task_name_heartbeat,
                        [],
                        _round,
                        [],
                        str(messages[-1].get("content", ""))[:200] if messages else "",
                    )
                    _last_heartbeat = time.time()
                except Exception:
                    from core.lib.os_event_logger import write_os_event

                    write_os_event(
                        event_type="intercept",
                        operation="write",
                        os_action="blocked",
                        reason="checkpoint_lost",
                        command="save_checkpoint",
                        detail={"error": "silent pass"},
                        session_id=locals().get("session_id", ""),
                        task_id=locals().get("task_id", ""),
                    )
            _thinking = len(_file_matches_hard) >= 2 if "_file_matches_hard" in dir() else False
            # 呼吸模式：每步执行前注入复述
            _recap_text = recap_checkpoint(_task_name_async, _round)
            if _recap_text:
                messages.append({"role": "system", "content": _recap_text})
            # [TOKEN_GUARD] V9 API 调用前 Token 硬截断（复用 core/lib/llm_client.py _tg_estimate 逻辑）
            _tg_before = _tg_estimate(messages, tools)
            if _tg_before > _calc_token_budget(model, tools) * 0.9:
                _tg_sys = [m for m in messages if m.get("role") == "system"][:2]
                _tg_tail = messages[-4:]
                _tg_summary = {"role": "system", "content": "【上下文摘要】中间消息已被强制截断，保留前 2 条 system 与最近 4 条消息。"}
                messages = _tg_sys + [_tg_summary] + _tg_tail
                if _tg_estimate(messages, tools) > _calc_token_budget(model, tools):
                    for _m in messages:
                        if _m.get("role") == "system" and len(str(_m.get("content", "") or "")) > 5000:
                            _m["content"] = str(_m["content"])[:5000]
                _guard_log(
                    "TOKEN_GUARD",
                    f"[TOKEN_GUARD] 强制截断：{_tg_before} → {_tg_estimate(messages, tools)}",
                    "token_guard.log",
                )
            # P2c: 保留极简补记(守卫注入需写日志才能被 derive_messages 重建, 否则丢失)
            try:
                from core.gateway.session_log import get_session_log

                _slog = get_session_log(_sid)
                _projected = _slog.derive_messages()
                _proj_count = len(_projected)
                if len(messages) > _proj_count:
                    for _m_extra in messages[_proj_count:]:
                        if _m_extra.get("role") in ("system", "user", "tool"):
                            _slog.append(
                                "user_message" if _m_extra.get("role") in ("system", "user") else "tool_result",
                                {
                                    "role": _m_extra.get("role"),
                                    "content": str(_m_extra.get("content", "")),
                                    "call_id": _m_extra.get("tool_call_id", ""),
                                    "source": "guard",
                                },
                            )
            except Exception:
                pass
            # 唯一出口: 配对修复 + tool_calls 结构规范化(根治 thinking 400, 与 bridge_loop 同构)
            messages = _finalize_messages(messages)
            # 2026-09-06: 发送前最终剥离纯文本 assistant 的 reasoning_content(双保险,
            # 与 adapter.keep_last_reasoning 一致) — derive 异常/事件空时 messages 可能
            # 仍是前端带 reasoning 的原始消息, 直接发 DeepSeek → 400。
            try:
                _rc_final = 0
                for _m_rf in messages:
                    if (
                        _m_rf.get("role") == "assistant"
                        and not _m_rf.get("tool_calls")
                        and _m_rf.get("reasoning_content") is not None
                    ):
                        _m_rf.pop("reasoning_content", None)
                        _rc_final += 1
                if _rc_final:
                    logger.info(f"[sub:{sub_task_id}] [RC_FINAL] 发送前剥离 {_rc_final} 条纯文本 reasoning_content")
            except Exception:
                pass
            # 任务3 v9: LLM 调用限流(信号量 max 2, 阻塞排队) + 失败指数退避重试(1s->2s->4s, 最多 3 次)
            # Turn 协议 Step2: step_start(每轮 LLM 调用前)
            try:
                from core.gateway.session_log import EV_STEP_START as _EV_SS
                from core.gateway.session_log import log_event as _log_es

                _log_es(
                    _sid,
                    _EV_SS,
                    {"turn_id": _exec_turn_id, "step_id": _round + 1, "round": _round},
                    turn_id=_exec_turn_id,
                    step_id=_round + 1,
                )
            except Exception:
                pass
            _llm_retries = 0
            _llm_delay = 1.0
            resp = {"success": False, "error": "init"}
            while _llm_retries < 3:
                try:
                    if _use_ollama_v9:
                        with _LLM_SEMAPHORE:
                            resp = _ollama_execute_with_tools(
                                messages,
                                tools,
                                model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_0-gpu"),
                                max_tokens=8000 if _thinking else 2000,
                            )
                    else:
                        with _LLM_SEMAPHORE:
                            resp = adapter.execute_with_tools(
                                messages=messages,
                                tools=tools,
                                user_id=user_id,
                                temperature=0.7,
                                max_tokens=8000 if _thinking else 2000,
                                thinking=_thinking,
                            )
                except Exception as _llm_e:
                    resp = {"success": False, "error": str(_llm_e)[:200]}
                if resp.get("success"):
                    break
                _llm_retries += 1
                if _llm_retries < 3:
                    logger.info(
                        f"[sub:{sub_task_id}] [LLM_RETRY] 第{_llm_retries}次重试, 退避{int(_llm_delay)}s: {(resp.get('error') or '')[:80]}"
                    )
                    time.sleep(_llm_delay)
                    _llm_delay *= 2

            if not resp.get("success"):
                # P1 结构化错误: LLM API 失败透传 code(LLM_API)
                _api_err = resp.get("error", "API错误")
                preserve_error_context(
                    {"error": _struct_error("LLM_API", _api_err), "round": _round, "step": "api_call"},
                    _task_name_async,
                    _round,
                )
                _write_exec_turn_end("error", f"[LLM_API] {_api_err}", _round)
                _save_state("failed", f"[LLM_API] {_api_err}")
                _notify_fail({"code": "LLM_API", "message": _api_err})  # #31 P3: 结构化回调(按 code 决策)
                _record_failure_action("LLM_API", f"[LLM_API] {_api_err}", detail_note=f"round={_round} step=api_call")
                return

            data_resp = resp["data"]
            msg = data_resp.get("choices", [{}])[0].get("message", {})
            total_tokens += resp.get("tokens", 0)
            # [AUDIT] 实时审计 Agent 输出（模块级 audit_agent_output）
            _last_user_msg = ""
            for _m in reversed(messages):
                if _m.get("role") == "user":
                    _last_user_msg = str(_m.get("content", ""))
                    break
            audit_agent_output(
                _last_user_msg, msg.get("content", ""), skip_evidence=bool(sub_task_id)
            )  # 子任务跳过规则C(证据条款)

            if not msg.get("tool_calls"):
                # 方案确认检测：Agent 在等待用户确认方案，不结束任务
                _content = msg.get("content", "")
                _confirmation_keywords = _task_config.get("confirmation_keywords", ["是否确认", "请确认", "按此计划", "确认后执行"])
                _scheme_indicators = ["```", "修改计划", "文件列表", "###", "| 文件 |", "实施步骤"]
                _has_confirmation = any(kw in _content for kw in _confirmation_keywords)
                _has_scheme = any(ind in _content for ind in _scheme_indicators)
                if _has_confirmation and _has_scheme:
                    continue  # 不结束任务，保留上下文等待用户输入
                # P0.5: 交付物检查 — 用户要求修改文件但未写入，不判定完成
                _last_user_msg = ""
                for _m in reversed(messages):
                    if _m["role"] == "user":
                        _last_user_msg = _m["content"]
                        break
                _write_keywords = _task_config.get(
                    "write_keywords",
                    [
                        "创建",
                        "修改",
                        "完善",
                        "写入",
                        "新增",
                        "添加",
                        "生成",
                        "实现",
                        "编写",
                        "补充",
                        "新建",
                        "修复",
                        "解决",
                        "优化",
                        "重构",
                        "更新",
                        "改",
                    ],
                )
                # G2: require_write 判定升级 — messages 中出现 write_file 工具调用为强信号，关键词仅作辅助信号
                _has_write_call = False
                for _m in messages:
                    if _m.get("role") == "assistant":
                        for _tc in _m.get("tool_calls", []):
                            if _tc.get("function", {}).get("name") == "write_file":
                                _has_write_call = True
                                break
                _has_write_intent = _has_write_call or any(kw in _last_user_msg for kw in _write_keywords)
                if _has_write_intent:
                    # P0-2/P0-3: 真实写入校验 — 空口验证词（已完成/验证通过等）不构成完成依据，
                    # 必须以 write_file/write_large/execute_command 调用记录为准；无写入则强制继续执行
                    if not _check_recent_writes(messages) and _classify_task_type(messages) != "analysis":
                        import re as _re6

                        _target_hint = "目标文件"
                        _path_match = _re6.search(r"[\w_]+/[\w_]+\.\w+", _last_user_msg)
                        if _path_match:
                            _target_hint = _path_match.group(0)
                        # P4 steer 全量迁移: 纠偏指令走 steer 通道(下轮起点消费注入)
                        try:
                            from core.gateway.shared_state import add_steer

                            add_steer(
                                _sid,
                                f"[系统] 检测到任务未执行：用户要求修改 {_target_hint}，但未检测到 write_file 操作。唯一可用操作：write_file(path='{_target_hint}', content='完整文件内容')。禁止继续读取文件。请立即写入。",
                            )
                        except Exception:
                            messages.append(
                                {
                                    "role": "system",
                                    "content": f"[系统] 检测到任务未执行：用户要求修改 {_target_hint}，但未检测到 write_file 操作。唯一可用操作：write_file(path='{_target_hint}', content='完整文件内容')。禁止继续读取文件。请立即写入。",
                                }
                            )
                        continue
                    # 系统主动检测（读取内容）：关键词匹配仅作提示，不作完成依据
                    _target_hint = ""
                    import re as _re6b

                    _path_match = _re6b.search(r"[\w_]+/[\w_]+\.\w+", _last_user_msg)
                    if _path_match:
                        _target_hint = _path_match.group(0)
                    _consecutive_reads_on_target = 0
                    _last_read_content = ""
                    _recent_calls = []
                    for _m in messages[-10:]:
                        if _m["role"] == "assistant":
                            for _tc in _m.get("tool_calls", []):
                                _tc_name = _tc.get("function", {}).get("name", "")
                                _recent_calls.append(_tc_name)
                                if _tc_name == "read_file" and _target_hint:
                                    try:
                                        _tc_args = json.loads(_tc["function"]["arguments"])
                                        _tc_path = _tc_args.get("path", "")
                                        if _tc_path == _target_hint or _tc_path.endswith("/" + _target_hint):
                                            _consecutive_reads_on_target += 1
                                    except Exception:
                                        pass
                    if _consecutive_reads_on_target >= 3:
                        _recent_5 = _recent_calls[-5:]
                        _write_in_recent = any(c in ("write_file", "write_large", "execute_command") for c in _recent_5)
                        if not _write_in_recent:
                            for _m in reversed(messages):
                                if _m["role"] == "tool" and isinstance(_m.get("content"), str):
                                    _tool_content = _m["content"]
                                    if _tool_content and len(_tool_content) > len(_last_read_content):
                                        _last_read_content = _tool_content
                            if _last_read_content:
                                import re as _re7

                                _task_keywords = _re7.findall(r"[一-鿿]{2,4}|[a-zA-Z_]{3,}", _last_user_msg)
                                _action_words = {"添加", "创建", "修改", "删除", "新增", "加入", "实现", "编写", "补充", "完善"}
                                _noise_words = {"resume", "optimizer", "ui", "analysis_page", "py", "markdown", "文件"}
                                _task_keywords = [
                                    k
                                    for k in _task_keywords
                                    if k.lower() not in _noise_words and k not in _action_words
                                ]
                                _matched_count = sum(
                                    1 for k in _task_keywords[:5] if k.lower() in _last_read_content.lower()
                                )
                                _matched = _matched_count >= 2 and (
                                    len(_task_keywords[:5]) == 0 or _matched_count >= len(_task_keywords[:5]) * 0.6
                                )
                                if _matched and _task_keywords:
                                    # 仅作提示，不判完成：关键词匹配不能证明功能已实现
                                    logger.info(
                                        f"[sub:{sub_task_id}] [V9 async] 系统检测提示：读取内容含任务关键词（{', '.join(_task_keywords[:5])}），仍需实际写入以完成任务"
                                    )
                # ===== 任务完成：必须先通过 VerificationChain 五步验证闭环（#166 防假完成）=====
                _vc = None
                _last_usr_sync_hint = ""
                for _m_sync in reversed(messages):
                    if _m_sync["role"] == "user":
                        _last_usr_sync_hint = str(_m_sync["content"])[:300]
                        break
                try:
                    from core.lib.verification_chain import run_verification_chain

                    _vc = run_verification_chain(
                        task_name=_task_name_async,
                        session_id=session_id,
                        user_id=user_id,
                        messages=messages,
                        task_goal=_last_usr_sync_hint,
                        # 任务3 修复: 子任务(独立沙箱)时验证链 base_dir/project_root 指向
                        # subtasks/{task_id}/（此前查共享沙箱根, 子任务文件找不到 -> step1_write
                        # 永不通过 -> 审计复核强制继续 -> 死循环到 100 轮）
                        base_dir=_sb_task3.parent
                        if sandbox_base is not None
                        else Path(f"data/projects/{user_id}/{session_id}"),
                        project_root=_sb_task3.name if sandbox_base is not None else "clawsjoy_dev",
                        require_write=bool(_has_write_intent),
                        done_when=_get_task_done_when(session_id),
                    )
                except Exception as _vc_err:
                    logger.info(f"[sub:{sub_task_id}] [V9 async] VerificationChain 调用异常: {_vc_err}")
                # G4 第三方审计复核：VerificationChain 通过后，用审计记录交叉核对防假完成
                _audit_cc = None
                try:
                    from core.gateway.audit import cross_check_completion

                    _audit_cc = cross_check_completion(_vc, session_id, task_start_ts=_task_start, user_id=user_id)
                except Exception as _audit_cc_err:
                    logger.info(f"[sub:{sub_task_id}] [V9 async] 审计复核异常(忽略): {_audit_cc_err}")
                if (
                    _audit_cc is not None
                    and not _audit_cc.get("audit_passed", True)
                    and _classify_task_type(messages) != "analysis"
                ):
                    # 审计复核未通过 → 与验证失败同等处理：强制继续
                    _audit_fail_text = "；".join(_audit_cc.get("audit_failures", []))[:400]
                    messages.append(
                        {"role": "system", "content": f"[系统] 审计复核未通过：{_audit_fail_text}。禁止宣告完成，必须继续实际写入并修复问题。"}
                    )
                    _save_state("running", f"审计复核未通过，强制继续：{_audit_fail_text}", total_tokens)
                    logger.info(f"[sub:{sub_task_id}] [V9 async] 审计复核未通过，强制继续: {_audit_fail_text}")
                    continue
                if _vc is not None and not _vc.get("passed", False) and _classify_task_type(messages) != "analysis":
                    # 验证未通过 → 不判完成，强制继续执行
                    _vc_fail_text = "；".join(_vc.get("failures", []))[:500]
                    messages.append(
                        {
                            "role": "system",
                            "content": f"[系统] 任务完成验证未通过：{_vc_fail_text}。禁止宣告完成，必须继续实际写入并修复问题。当前唯一目标是完成写入与验证。",
                        }
                    )
                    _save_state("running", f"验证未通过，强制继续：{_vc_fail_text}", total_tokens)
                    logger.info(f"[sub:{sub_task_id}] [V9 async] 验证未通过，强制继续: {_vc_fail_text}")
                    continue
                # 验证通过（或验证器不可用时的降级路径：仍保留基础写入检查）
                _last_usr_sync = ""
                for _m_sync in messages:
                    if _m_sync["role"] == "user":
                        _last_usr_sync = _m_sync["content"]
                if _vc is None and _has_write_intent and _classify_task_type(messages) != "analysis":
                    # ===== 降级路径升级（子任务3）：write_file + git diff 变更 + py_compile 通过 =====
                    _deg_ok = _check_recent_writes(messages)
                    _deg_hint = []
                    if not _deg_ok:
                        _deg_hint.append("未检测到 write_file 操作")
                    else:
                        try:
                            import subprocess as _sp_deg

                            _agent_dir_deg = _sb_task3
                            _diff_deg = _proc.run_hidden(
                                ["git", "-C", str(_agent_dir_deg), "diff", "--name-only"],
                                capture_output=True,
                                text=True,
                                timeout=10, encoding="utf-8", errors="replace"
                            )
                            _changed_py_deg = [
                                ln.strip() for ln in _diff_deg.stdout.splitlines() if ln.strip().endswith(".py")
                            ]
                            if _diff_deg.returncode != 0 or not _changed_py_deg:
                                _deg_ok = False
                                _deg_hint.append("git diff 无变更")
                            else:
                                _compile_fail_deg = _py_compile_files(_changed_py_deg, _agent_dir_deg)
                                if _compile_fail_deg:
                                    _deg_ok = False
                                    _deg_hint.append("py_compile 失败: " + "；".join(_compile_fail_deg)[:200])
                        except Exception as _deg_err:
                            _deg_ok = False
                            _deg_hint.append("降级检查异常: %s" % _deg_err)
                    if not _deg_ok:
                        messages.append(
                            {"role": "system", "content": "[系统] 检测到任务未完成：" + "；".join(_deg_hint)[:300] + "。请立即写入并通过验证。"}
                        )
                        continue
                # ===== 自学习评分更新：VerificationChain 通过后写入 SAG feedback（#166 闭环）=====
                try:
                    _update_sag_feedback(_task_name_async, session_id, user_id, messages, passed=True, verification=_vc)
                except Exception as _fb_async_err:
                    logger.info("[sub:%s] [SAG_FEEDBACK] async 调用异常: %s" % (sub_task_id, _fb_async_err))
                # 呼吸模式：每步执行完成后压缩上下文（done 之前，#192）
                try:
                    # #192 并发修复：子线程独立沙箱传 sub_task_id，写入专属快照
                    try:
                        _ctx_mgr.compress_and_store(sub_task_id=sub_task_id)
                    except TypeError:
                        _ctx_mgr.compress_and_store()
                except Exception as _ctx_done_err:
                    logger.info(f"[sub:{sub_task_id}] [V9 async] 完成前压缩失败: {_ctx_done_err}")
                _write_exec_turn_end("completed", "assistant 有内容且无待执行 tool_calls", _round)
                _save_state("done", msg.get("content", ""), total_tokens)
                _notify_done(msg.get("content", ""))  # #31 长线任务：完成回调驱动队列
                _sync_save = {}
                if _last_usr_sync:
                    _sync_save["last_task"] = _last_usr_sync[:200]
                if _vc is not None:
                    _sync_save["verification"] = {
                        "passed": True,
                        "steps": {k: v.get("passed") for k, v in _vc.get("steps", {}).items()},
                    }
                state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
                try:
                    _existing = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
                except Exception:
                    _existing = {}
                _existing.update(_sync_save)
                state_file.write_text(json.dumps(_existing, ensure_ascii=False, indent=2), encoding="utf-8")
                ledger.record_event(
                    server_id="default",
                    agent_name=_agent_name_task,
                    position=_agent_pos,
                    action="task_complete",
                    summary=f"任务完成: {task_id}",
                )
                return

            # 执行工具调用
            # 源头限流：write_file 参数截断（只保留 path + 内容前 1000 字符 + 总行数）
            _tc_for_history = []
            for _tc in msg["tool_calls"]:
                _tc_fn = (_tc.get("function") or {}).get("name", "")
                if _tc_fn != "write_file":
                    _tc_for_history.append(_tc)
                    continue
                _tc_copy = _json.loads(_json.dumps(_tc))
                try:
                    _tc_args = _json.loads(_tc_copy["function"]["arguments"])
                except json.JSONDecodeError:
                    _tc_for_history.append(_tc_copy)
                    continue
                _tc_content = _tc_args.get("content")
                if isinstance(_tc_content, str) and len(_tc_content) > 1000:
                    _tc_total_lines = _tc_content.count("\n") + 1
                    _tc_args["content"] = (
                        _tc_content[:1000] + f"\n...[write_file 内容截断: 原文 {_tc_total_lines} 行 / {len(_tc_content)} 字符]"
                    )
                    _tc_copy["function"]["arguments"] = _json.dumps(_tc_args, ensure_ascii=False)
                _tc_for_history.append(_tc_copy)
            _assistant_msg = {"role": "assistant", "content": msg.get("content", ""), "tool_calls": _tc_for_history}
            # 2026-09-06 修复: tool_calls assistant 必须带 reasoning_content 键(值可空串) —
            # 原 if truthy 才加, round 返回 reasoning 为空串/None 时键缺失 → 该消息若经
            # derive 异常回退(内存 messages 直发) → DeepSeek 400 "reasoning_content must be
            # passed back"(实测: 无键 400, 空串键 200)。_normalize_tool_calls 会把 None 转空串。
            _assistant_msg["reasoning_content"] = msg.get("reasoning_content")
            messages.append(_assistant_msg)
            # P2a 事件溯源双写: assistant_message(不改变现有 messages 行为)
            try:
                from core.gateway.session_log import log_event

                log_event(
                    _sid,
                    "assistant_message",
                    {
                        "content": msg.get("content", ""),
                        "tool_calls": _tc_for_history,
                        "reasoning_content": msg.get("reasoning_content")
                        if isinstance(msg.get("reasoning_content"), str)
                        else "",
                    },
                    turn_id=_round,
                    step_id=0,
                )
            except Exception:
                pass

            # 推送中间过程到状态文件
            if msg.get("content"):
                _save_state("running", msg["content"], total_tokens)
            for tc in msg["tool_calls"]:
                try:
                    args = _json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    # 尝试修复非法 JSON：补闭合引号、转义换行符
                    fixed = tc["function"]["arguments"]
                    if fixed.count('"') % 2 != 0:
                        fixed += '"'
                    fixed = fixed.replace("\n", "\\n").replace("\r", "\\r")
                    try:
                        args = _json.loads(fixed)
                    except json.JSONDecodeError:
                        _save_state("failed", f"工具参数 JSON 解析失败: {tc['function']['name']}")
                        _notify_fail(
                            {"code": "TOOL_ARGS", "message": f"工具参数 JSON 解析失败: {tc['function']['name']}"}
                        )  # #31 P3
                        _record_failure_action(
                            "TOOL_ARGS",
                            f"工具参数 JSON 解析失败: {tc['function']['name']}",
                            detail_note=f"round={_round} step=args_parse",
                        )
                        return
                _tc_tool = tc["function"]["name"]  # 重复提醒已由 ReminderGuard(post 观察)接管
                # P1 S6: 统一 guard 入口(本路径一律免审批 — 现状无锚点A/B 内联) — pre 检测
                from core.gateway.guards.runner import run_pre_guards

                _scope_key = f"{session_id}_{sub_task_id}" if sub_task_id else f"{session_id}_agent_exec"
                _guard_deny = run_pre_guards(
                    {
                        "tool": _tc_tool,
                        "args": args,
                        "user_id": user_id,
                        "session_id": session_id,
                        "sandbox_base": str(_sb_task3),
                        "messages": messages,
                        "task_id": task_id,
                        "agent_id": sub_task_id or task_id,
                        # ⭐ PM 2026-10-04（承 技总 958 §二.⒝ · 老板「批」）：子任务之标识入载荷
                        #   ⇒ `ApprovalGuard` 据此早返（免审批）∧ 锚点B 不读 ⇒ 越权仍拒
                        "sub_task_id": sub_task_id,
                    },
                    scope_key=_scope_key,
                )
                if _guard_deny is not None:
                    # 状态机透传: paused(递归) 由本路径处理; 其他 deny 拒绝执行
                    _g_status = _guard_deny.get("status", "default")
                    if _g_status == "paused":
                        _pause_recursion(
                            task_id,
                            _tc_tool,
                            str(_guard_deny.get("recursion_path", "")),
                            _guard_deny.get("recursion_reason", "递归暂停"),
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": "[系统] " + _guard_deny.get("recursion_reason", "") + "。任务已暂停，等待老板决定。",
                            }
                        )
                        _save_state("paused", _guard_deny.get("recursion_reason", ""), total_tokens)
                        return
                    if _g_status == "forbidden":
                        # 拦截后引导替代路径(与 bridge_loop 一致): 明确告知沙箱内临时目录 data/tmp/
                        _deny_reason = str(_guard_deny.get("reason", "操作被拒绝"))
                        _deny_hint = (
                            "。请改用沙箱内相对路径（clawsjoy_dev/ 内，如 data/tmp/ 做临时文件、"
                            "data/reports/ 做报告），不要使用 /tmp、/home、/etc 等系统路径或绝对路径。"
                        )
                        messages.append(
                            {"role": "tool", "tool_call_id": tc.get("id", ""), "content": _deny_reason + _deny_hint}
                        )
                        continue
                    if _g_status == "write_pending":
                        # ⭐ PM 2026-10-04（承 技总 957 §三 ⒜）：待审 ⛔ 当「硬失败」
                        #   子任务路无人工审批面 ⇒ 落「待审」态并返回，由上层按 status 处置
                        _wp_reason = str(_guard_deny.get("reason", "写入待审批（未提供 reason）"))
                        messages.append(
                            {"role": "user",
                             "content": "[系统] " + _wp_reason + "。本步为**待审批** ⇒ 本任务停于该步（⛔ 当失败）。"}
                        )
                        _save_state("pending", _wp_reason, total_tokens)
                        _notify_fail({"code": "WRITE_PENDING", "message": _wp_reason})
                        return
                    _save_state("failed", _guard_deny.get("reason", "工具调用被拒绝"))
                    _notify_fail({"code": "GUARD_DENY", "message": _guard_deny.get("reason", "工具调用被拒绝")})
                    return
                try:
                    logger.info(
                        f"[sub:{sub_task_id}] [V9 async] 执行工具: {tc['function']['name']}, args={str(args)[:100]}"
                    )
                    # ---- 递归检测 ----
                    _rec_tool = tc["function"]["name"]
                    _rec_path = _extract_tool_path(args, _rec_tool)
                    _rec_status, _rec_msg = check_recursion(task_id, _rec_tool, _rec_path)
                    if _rec_status == "pause":
                        _pause_recursion(task_id, _rec_tool, _rec_path, _rec_msg)
                        messages.append({"role": "user", "content": "[系统] " + _rec_msg + "。任务已暂停，等待老板决定。"})
                        _save_state("paused", _rec_msg, total_tokens)
                        return
                    # 工具追踪：调用前检查连续同工具
                    _tool_trk_pre = _tracker_setdefault(
                        _session_tool_tracker,
                        session_id,
                        lambda: {"calls": [], "stats": {}, "consecutive": {}, "last_tool": ""},
                    )
                    _prev_tool = _tool_trk_pre.get("last_tool", "")
                    _consec = _tool_trk_pre.setdefault("consecutive", {})
                    if _prev_tool == _rec_tool:
                        _consec[_rec_tool] = _consec.get(_rec_tool, 0) + 1
                    else:
                        _consec[_rec_tool] = 1
                        _tool_trk_pre["last_tool"] = _rec_tool
                    if _consec.get(_rec_tool, 0) >= 3:
                        # P4 steer 全量迁移: 纠偏指令走 steer 通道(下轮起点消费注入)
                        try:
                            from core.gateway.shared_state import add_steer

                            add_steer(_sid, f"[系统] {_rec_tool} 已连续使用 {_consec[_rec_tool]} 次，请考虑切换工具")
                        except Exception:
                            messages.append(
                                {"role": "system", "content": f"[系统] {_rec_tool} 已连续使用 {_consec[_rec_tool]} 次，请考虑切换工具"}
                            )

                    # P2c: _shared_msgs 同步已删(工具层经 ctx.messages 拿当前消息)
                    # P2a 事件溯源双写: tool_call(工具执行前)
                    try:
                        from core.gateway.session_log import log_event

                        log_event(
                            _sid,
                            "tool_call",
                            {"name": _rec_tool, "arguments": args, "call_id": tc.get("id", "")},
                            turn_id=_round,
                            step_id=0,
                        )
                    except Exception:
                        pass
                    tool_result = _execute_sandbox_tool(_rec_tool, args, user_id, session_id, sandbox_base=_sb_task3)
                    # P2a 事件溯源双写: tool_result(工具返回后)
                    try:
                        from core.gateway.session_log import log_event

                        log_event(
                            _sid,
                            "tool_result",
                            {
                                "name": _rec_tool,
                                "call_id": tc.get("id", ""),
                                "content": str(tool_result)[:2000],
                                "success": bool(tool_result.get("success")) if isinstance(tool_result, dict) else False,
                            },
                            turn_id=_round,
                            step_id=0,
                        )
                    except Exception:
                        pass
                    # P2b: 回同步 hack 已删 — 工具层注入消息由下一轮 derive_messages 重建(日志含工具结果)
                    logger.info(f"[sub:{sub_task_id}] [V9 async] 工具返回: {str(tool_result)[:100]}")
                    # 工具追踪：调用后更新 stats
                    _tool_trk = _tracker_setdefault(
                        _session_tool_tracker,
                        session_id,
                        lambda: {"calls": [], "stats": {}, "consecutive": {}, "last_tool": ""},
                    )
                    _tool_name = _rec_tool
                    _tool_st = _tool_trk.setdefault("stats", {}).setdefault(
                        _tool_name, {"count": 0, "success_count": 0, "fail_count": 0, "empty_count": 0}
                    )
                    _tool_st["count"] += 1
                    _success_flag = bool(tool_result.get("success")) if isinstance(tool_result, dict) else False
                    if _success_flag:
                        _tool_st["success_count"] += 1
                    else:
                        _tool_st["fail_count"] += 1
                    _out_val = str(tool_result.get("stdout", "")) if isinstance(tool_result, dict) else ""
                    if not _out_val.strip():
                        _tool_st["empty_count"] += 1
                    _tool_trk["calls"].append({"tool": _tool_name, "success": _success_flag})
                    if len(_tool_trk["calls"]) > 50:
                        _tool_trk["calls"] = _tool_trk["calls"][-50:]
                    _tool_trk["last_tool"] = _tool_name
                    # ===== #202 SAG 索引刷新：write_file 成功后自动重抽实体，行号与磁盘一致 =====
                    # 记录工具调用到 tracker
                    try:
                        _trk_t = _tracker_setdefault(
                            _session_tool_tracker, session_id, lambda: {"calls": [], "stats": {}}
                        )
                        _trk_t["calls"].append(
                            {
                                "tool": _rec_tool,
                                "path": args.get("path", args.get("command", "")),
                                "success": isinstance(tool_result, dict) and tool_result.get("success", False),
                                "time": time.time(),
                            }
                        )
                        if len(_trk_t["calls"]) > 50:
                            _trk_t["calls"] = _trk_t["calls"][-50:]
                        _st = _trk_t["stats"].setdefault(_rec_tool, {"count": 0, "success": 0, "fail": 0})
                        _st["count"] += 1
                        if isinstance(tool_result, dict) and tool_result.get("success"):
                            _st["success"] += 1
                        else:
                            _st["fail"] += 1
                    except Exception:
                        pass
                    # 外置存储 tool 结果
                    from core.lib.code_entity_extractor import extractor

                    _result_ref = ""
                    try:
                        _result_dir = Path(f"data/sag/tool_results/{session_id}")
                        _result_dir.mkdir(parents=True, exist_ok=True)
                        _result_file = _result_dir / f"{tc.get('id', 'unknown')}.json"
                        with open(_result_file, "w", encoding="utf-8") as _rf:
                            json.dump(tool_result, _rf, ensure_ascii=False, default=str)
                        _result_ref = f"sag://tool_results/{session_id}/{tc.get('id', 'unknown')}.json"
                    except Exception as _e_store:
                        logger.info(f"[TOOL_STORE] 外置存储失败: {_e_store}")
                        _result_ref = ""
                    if _rec_tool == "write_file" and isinstance(tool_result, dict) and tool_result.get("success"):
                        try:
                            from core.lib.code_entity_extractor import extractor

                            _sag_base = _sb_task3
                            _sag_target = _resolve_path(_sag_base, args.get("path", ""))
                            if _sag_target.exists():
                                _sag_content = _sag_target.read_text(encoding="utf-8")
                                _sag_rel = str(_sag_target)
                                _pivot = _sag_rel.find("clawsjoy_dev/")
                                if _pivot >= 0:
                                    _sag_rel = _sag_rel[_pivot:]
                                extractor.extract_and_upsert(_sag_rel, _sag_content, "default")
                                logger.info(f"[sub:{sub_task_id}] [SAG_REFRESH] write_file 后刷新索引: {_sag_rel}")
                        except Exception as _sag_err:
                            logger.info(f"[sub:{sub_task_id}] [SAG_REFRESH] 刷新失败: {_sag_err}")
                    # 截断 tool_result 中的 content 字段，防止 messages 膨胀
                    if isinstance(tool_result, dict) and "content" in tool_result:
                        c = tool_result["content"]
                        if isinstance(c, str) and len(c) > 2000:
                            tool_result["content"] = c[:2000] + f"\n... (内容已截断，共 {len(c)} 字符)"
                    _preview = str(tool_result)[:200]
                    _content_ref = _result_ref or str(tool_result)[:2000]
                    messages.append(
                        {"role": "tool", "tool_call_id": tc["id"], "content": f"[预览] {_preview}\n[全文] {_content_ref}"}
                    )
                    # P1 S6: 统一 guard 入口 - post 观察(reminder 注入 + 审计 + 失败计数)
                    from core.gateway.guards.runner import run_post_guards

                    _post_payload = {
                        "tool": _tc_tool,
                        "args": args,
                        "user_id": user_id,
                        "session_id": session_id,
                        "result": tool_result,
                        "agent_id": sub_task_id or task_id,
                    }
                    run_post_guards(_post_payload, scope_key=_scope_key)
                    _gr = _post_payload.get("guard_results", {})
                    _reminder_txt = _gr.get("reminder")
                    if _reminder_txt:
                        # P4 steer 全量迁移: guard reminder 走 steer 通道(下轮注入, 不直接拼 system)
                        try:
                            from core.gateway.shared_state import add_steer

                            add_steer(_sid, str(_reminder_txt))
                        except Exception:
                            messages.append({"role": "system", "content": _reminder_txt})
                    _pause_txt = _gr.get("error") if _gr.get("paused") else None
                    if _pause_txt:
                        _save_state("paused", _pause_txt, total_tokens)
                        messages.append({"role": "user", "content": "[系统] " + _pause_txt})
                        return
                    if _rec_status == "warn":
                        # P4 steer 全量迁移: recursion warn 走 steer 通道(下轮注入)
                        try:
                            from core.gateway.shared_state import add_steer

                            add_steer(_sid, "[系统] " + _rec_msg)
                        except Exception:
                            messages.append({"role": "system", "content": "[系统] " + _rec_msg})
                except Exception as _tool_err:
                    # P2: TOOL_EXEC 前缀 + 工具名 + 结构化 context(错误分类一致, 工具失败可审计)
                    _tool_err_msg = f"[TOOL_EXEC] 工具 {_tc_tool} 执行失败: {_tool_err}"
                    logger.info(f"[sub:{sub_task_id}] [V9 async] 工具执行失败: {_tool_err}")
                    preserve_error_context(
                        {
                            "error": _struct_error(
                                "TOOL_EXEC", f"工具 {_tc_tool} 执行失败", {"tool": _tc_tool, "error": str(_tool_err)[:200]}
                            ),
                            "round": _round,
                            "step": "tool_exec",
                        },
                        _task_name_async,
                        _round,
                    )
                    _save_state("failed", _tool_err_msg)
                    _notify_fail({"code": "TOOL_EXEC", "message": f"工具 {_tc_tool} 执行失败: {_tool_err}"})  # #31 P3: 结构化回调
                    _record_failure_action("TOOL_EXEC", _tool_err_msg, detail_note=f"tool={_tc_tool}")
                    return

            _save_state("running", None, total_tokens)
            # 呼吸模式：每步完成后压缩上下文
            # #192 并发修复：子线程独立沙箱传 sub_task_id，写入专属快照
            try:
                _ctx_mgr.compress_and_store(sub_task_id=sub_task_id)
            except TypeError:
                _ctx_mgr.compress_and_store()
            # #83 疲劳度检查：连续无进展步数告警（不干扰主流程）
            try:
                _fatigue_msg = _ctx_mgr.check_fatigue()
                if _fatigue_msg:
                    logger.info(f"[sub:{sub_task_id}] [V9 async] {_fatigue_msg}")
                    # P4 steer 全量迁移: 疲劳度告警走 steer 通道(下轮注入)
                    try:
                        from core.gateway.shared_state import add_steer

                        add_steer(_sid, "[系统] " + _fatigue_msg)
                    except Exception:
                        messages.append({"role": "system", "content": "[系统] " + _fatigue_msg})
            except Exception as _fatigue_err:
                logger.info(f"[sub:{sub_task_id}] [V9 async] 疲劳度检查失败(忽略): {_fatigue_err}")
            # Turn 协议 Step2: step_end(每轮工具执行后)
            try:
                from core.gateway.session_log import EV_STEP_END as _EV_SE
                from core.gateway.session_log import log_event as _log_ese

                _log_ese(
                    _sid,
                    _EV_SE,
                    {"turn_id": _exec_turn_id, "step_id": _round + 1},
                    turn_id=_exec_turn_id,
                    step_id=_round + 1,
                )
            except Exception:
                pass
            _round += 1

        from core.gateway.turn_protocol import _compute_turn_reason as _ctr_exec

        _reason_e, _detail_e = _ctr_exec(
            round_exhausted=True,
            bridge_exhausted=True,
            content=str((_assistant_content if "_assistant_content" in dir() else "") or ""),
        )
        _write_exec_turn_end(_reason_e, _detail_e, _round)
        _save_state("timeout", "[TIMEOUT] 超过最大轮次", total_tokens)
        _notify_fail({"code": "TIMEOUT", "message": "超过最大轮次"})  # #31 P3: 结构化回调(按 code 决策)
    except Exception as e:
        # P1 结构化错误: 异常分类 -> code 前缀文本(归档兼容) + 结构化 dict(context)
        _err_code = _classify_exception(e)
        _err_msg = str(e)[:300]
        preserve_error_context(
            {"error": _struct_error(_err_code, _err_msg), "round": _round, "step": "outer_except"},
            _task_name_async,
            _round,
        )
        _save_state("failed", f"[{_err_code}] {_err_msg}")
        _notify_fail({"code": _err_code, "message": _err_msg})  # #31 P3: 结构化回调
        _record_failure_action(_err_code, _err_msg, detail_note=f"round={_round} step=outer_except")


# ===== 分层消息存储（#234 消息架构重构）=====
from core.gateway.message_assembler import _finalize_messages

# system_hypothesis 查询缓存（进程内存，30 秒 TTL）
from core.gateway.tool_router import _execute_sandbox_tool

logger = logging.getLogger(__name__)


def _update_world_model(filepath, content, user_id="default", session_id="default"):
    """write_file 成功后更新模块依赖图"""
    import re as _re3

    global _last_read_fingerprints  # 借用全局变量声明位置
    _state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
    _state = json.loads(_state_file.read_text(encoding="utf-8")) if _state_file.exists() else {}
    _wm = _state.get("world_model")
    if isinstance(_wm, str):
        try:
            _state["world_model"] = json.loads(_wm)
        except Exception:
            _state["world_model"] = {"modules": {}, "last_updated": ""}
    if "world_model" not in _state or not isinstance(_state.get("world_model"), dict):
        _state["world_model"] = {"modules": {}, "last_updated": ""}

    _modules = _state["world_model"].get("modules", {})
    if not isinstance(_modules, dict):
        _modules = {}
        _state["world_model"]["modules"] = _modules
    _skel = None
    if filepath.endswith(".py"):
        _lines = content.split("\n")
        if "ui/" in filepath:
            _skel_lines = []
            for _i, _l in enumerate(_lines):
                _stripped = _l.strip()
                if _stripped.startswith("#") and ("\u2500" in _l or "===" in _l):
                    _skel_lines.append(_l)
                elif any(kw in _l for kw in ["st.", "import streamlit", "def render", "def _"]):
                    _skel_lines.append(_l)
                elif "st.columns" in _l:
                    _skel_lines.append(_l)
                elif _i > 0 and any(
                    kw in _lines[_i - 1] for kw in ["st.", "st.columns", "import streamlit", "def render", "def _"]
                ):
                    _skel_lines.append(_l)
            _skel = "\n".join(_skel_lines)[:4000]
        elif "services/" in filepath:
            _skel_lines = []
            for _i, _l in enumerate(_lines):
                _stripped = _l.strip()
                if _stripped.startswith("def ") or _stripped.startswith("class "):
                    _skel_lines.append(_l)
                elif any(
                    kw in _l
                    for kw in [
                        "import ",
                        "from ",
                        "API",
                        "PRICING",
                        "MODEL",
                        "DEFAULT",
                        "BASE_URL",
                        "TIMEOUT",
                        "MAX_",
                        "MIN_",
                    ]
                ):
                    _skel_lines.append(_l)
                elif _stripped.startswith("@"):
                    _skel_lines.append(_l)
                elif _i > 0 and _lines[_i - 1].strip().startswith("def "):
                    if _stripped.startswith('"""') or _stripped.startswith("'''"):
                        _skel_lines.append(_l)
                    elif _stripped.startswith("#") and any(
                        kw in _stripped
                        for kw in ("\u529f\u80fd", "\u4f5c\u7528", "\u8bf4\u660e", "\u53c2\u6570", "\u8fd4\u56de")
                    ):
                        _skel_lines.append(_l)
                elif _stripped.startswith("#") and ("\u2500" in _l or "===" in _l):
                    _skel_lines.append(_l)
            _skel = "\n".join(_skel_lines)[:3000]
        elif "models/" in filepath:
            _skel_lines = [
                l
                for l in _lines
                if any(
                    kw in l
                    for kw in [
                        "@dataclass",
                        "class ",
                        "def ",
                        "from dataclasses",
                        "from typing",
                        "field",
                        "Optional",
                        ":",
                        "=",
                    ]
                )
            ]
            _skel = "\n".join(_skel_lines)[:3000]
    # 过滤网基准纯净：非 .py 文件不入 world_model.modules（避免 html/md/env 污染）
    if not filepath.endswith(".py"):
        _state["world_model"]["last_updated"] = datetime.now().isoformat()
        # 批221 修（DS-206-3 指认：原为非原子直写）⇒ 统一原子出口
        from core.gateway.state_json import update_json as _uj_eat
        _uj_eat(_state_file, lambda _d: _d.update({"world_model": _state.get("world_model")}))
        return
    _modules[filepath] = {
        "lines": len(content.split("\n")),
        "imports": _re3.findall(r"^(?:from|import)\s+(\S+)", content, _re3.MULTILINE),
        "classes": _re3.findall(r"^class\s+(\w+)", content, _re3.MULTILINE),
        "functions": _re3.findall(r"^def\s+(\w+)", content, _re3.MULTILINE),
        "status": "complete",
        "skeleton": _skel,
    }
    # 图化：由线性 modules dict 重建 code_edges 图边，写入 world_model（与 DB code_edges 表同构）
    _state["world_model"]["code_edges"] = _build_code_edges(_modules)
    # 路径校验：文件是否在项目目录树下
    _proj_root = _state.get("project_root", "clawsjoy_dev")
    if not filepath.startswith(_proj_root + "/"):
        # path_mismatch 的文件不加入 world_model，避免跨项目污染
        _state["world_model"]["last_updated"] = datetime.now().isoformat()
        # 批221 修（DS-206-3 指认：原为非原子直写）⇒ 统一原子出口
        from core.gateway.state_json import update_json as _uj_eat
        _uj_eat(_state_file, lambda _d: _d.update({"world_model": _state.get("world_model")}))
        return
    _state["world_model"]["last_updated"] = datetime.now().isoformat()
    _state_file.write_text(_safe_serialize_state(_state), encoding="utf-8")

    # 代码实体自动抽取入库，返回实体数量
    _entity_count = 0
    try:
        from core.lib.code_entity_extractor import extractor

        _entity_count = extractor.extract_and_upsert(filepath, content) or 0
    except Exception:
        _entity_count = -1
    _state["_last_entity_count"] = _entity_count
    _last_usr_wm = ""
    for _mu_wm in messages:
        if _mu_wm["role"] == "user" and len(_mu_wm.get("content", "")) > 10:
            _last_usr_wm = _mu_wm["content"]
    _state["_last_task"] = _last_usr_wm[:500] if _last_usr_wm else ""
    # 双写 PostgreSQL code_entities
    if _last_usr_wm:
        try:
            import psycopg2

            _pg = psycopg2.connect("postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev")
            _cur = _pg.cursor()
            _cur.execute(
                """
                INSERT INTO code_entities (project_id, entity_type, entity_name, file_path, status, related_entities)
                VALUES (%s, 'task', %s, %s, 'pending', %s)
                ON CONFLICT (project_id, entity_name, file_path) DO UPDATE SET status = 'pending'
            """,
                ("default", _last_usr_wm[:200], f"/tasks/{session_id}", [filepath] if filepath else []),
            )
            _pg.commit()
            _cur.close()
            _pg.close()
        except Exception:
            pass
    _state_file.write_text(_safe_serialize_state(_state), encoding="utf-8")


# ===== 从 agent_gateway_enhanced.py 迁移的帮助函数 =====


def _check_recent_task_progress_completed(session_id=None):
    """查 DB task_progress 最近 3 条是否全部 completed"""
    try:
        import psycopg2

        from core.lib.code_entity_extractor import extractor

        conn = psycopg2.connect(extractor.db_url)
        cur = conn.cursor()
        cur.execute(
            "SELECT status FROM task_progress WHERE session_id=%s ORDER BY started_at DESC LIMIT 3", (session_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if len(rows) < 3:
            logger.info(f"[AUTO_MERGE] task_progress 最近记录 {len(rows)} 条 < 3，跳过合并")
            return False
        _ok = all(r[0] == "completed" for r in rows)
        logger.info(f"[AUTO_MERGE] 最近 3 条 task_progress: {[r[0] for r in rows]} -> {'全部完成' if _ok else '未全部完成'}")
        return _ok
    except Exception as e:
        logger.info(f"[AUTO_MERGE] task_progress 查询失败: {e}")
        return False


def _py_compile_files(py_files, base_dir):
    """只编译变更的 .py 文件，返回失败列表"""
    import py_compile as _pc

    _fail = []
    for _f in py_files or []:
        if not _f or not str(_f).endswith(".py"):
            continue
        _rel = str(_f).lstrip("/")
        _p = Path(base_dir) / _rel
        if not _p.exists():
            _fail.append(f"{_rel}:不存在")
            continue
        try:
            _pc.compile(str(_p), doraise=True)
        except Exception as _e:
            _fail.append(f"{_rel}:{_e}")
    return _fail


def check_recursion(task_id, tool_name, file_path):
    """检测同一 (tool, path) 的连续重复操作。返回 ("ok", None) | ("warn", msg) | ("pause", reason)"""
    import time as _time

    entry = _recursion_tracker.setdefault(
        task_id, {"pattern": None, "count": 0, "first_seen": None, "breakpoint": None}
    )
    pattern = (tool_name, file_path)
    now = _time.time()
    if entry["pattern"] == pattern:
        entry["count"] += 1
    else:
        entry["pattern"] = pattern
        entry["count"] = 1
        entry["first_seen"] = now
    n = entry["count"]
    # 阈值取 execution_policy.yaml recursion.auto_pause_threshold(默认 5); 与 bridge 路径一致
    try:
        from core.gateway.shared_state import _load_v9_execution_policy as _lv9p

        _threshold = int(((_lv9p() or {}).get("recursion", {}) or {}).get("auto_pause_threshold", 5) or 5)
    except Exception:
        _threshold = 5
    if n >= _threshold:
        reason = "检测到对同一路径 %r 的 %s 重复操作已达 %d 次，疑似陷入递归循环" % (file_path, tool_name, n)
        return ("pause", reason)
    if n >= max(2, _threshold // 2):
        return ("warn", "检测到重复操作（%s %r 第 %d 次），请换一种方式，避免陷入循环" % (tool_name, file_path, n))
    return ("ok", None)


def _pause_recursion(task_id, tool_name, file_path, reason):
    """保存递归断点并打印 [RECURSION] 日志，返回断点 dict"""
    import time as _time

    bp = {"tool": tool_name, "path": file_path, "paused_at": _time.time(), "reason": reason}
    entry = _recursion_tracker.setdefault(task_id, {})
    entry["breakpoint"] = bp
    _guard_log("RECURSION", "[RECURSION] task=%s 递归触发暂停: %s" % (task_id, reason), "recursion.log")
    return bp
