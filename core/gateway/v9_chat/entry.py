"""v9_agent_chat 编排层（P3-B 从主文件下沉，2026-09-12）。

流式契约：生成器仍由 bridge_call.make_stream_response 产出，本层只返回
(生成器, "stream") 或 (dict, "json")，由路由侧包装 —— 不跨层 yield。
"""

import json
import os
import time
from pathlib import Path

from core.gateway.approval import _v9_handle_approvals
from core.gateway.execute_agent_task import _execute_agent_task
from core.gateway.message_assembler import (
    _calc_token_budget,
    _compress_messages,
    _estimate_tokens,
    _hard_truncate_messages,
    _inject_sys_content,
    _tg_estimate,
    _validate_messages,
)
from core.gateway.quota_manager import _check_discuss_token_budget
from core.gateway.session_log import get_session_log as _gsl_dig
from core.gateway.shared_state import _load_v9_execution_policy
from core.gateway.tool_router import _filter_tools_by_mode
from core.gateway.v9_bridge.context_utils import (
    _v9_inject_context,
    _v9_is_resume_utterance,
    _v9_looks_like_new_task,
    _v9_mark_agent_plan,
    _v9_round_checkpoint,
)
from core.gateway.v9_bridge.response_helpers import _goal_info_for_response
from core.gateway.write_gate import _plan_pending, _v9_restore_pending_writes
from core.lib.gateway_helpers import _get_agent_tools, _get_sandbox_base, cleanup_task_context
from core.lib.util import _get_skeletons_by_type

# B2（本地 provider 不依赖 DeepSeek key）：本地 model 走 Ollama 本地 adapter；
# ⛔ 整文件 cp —— 本段为 live 真源之函数/类级定点新增。
_LOCAL_MODEL_ALIASES = ("ollama", "local", "local_vlm", "local_api", "llama.cpp", "lmstudio", "mock")


class _LocalOllamaAdapter:
    """本地 Ollama adapter：与 DeepSeekAdapter.execute_with_tools 同形返回。

    复用 execute_agent_task._ollama_execute_with_tools（不依赖 DEEPSEEK_API_KEY / 外网）。
    model 为本地别名（ollama/local…）时解析 env OLLAMA_MODEL / 内置 qwen 名。
    """

    def __init__(self, model=None):
        _m = str(model or "").strip()
        if not _m or _m.lower() in _LOCAL_MODEL_ALIASES:
            _m = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_0-gpu")
        self.model = _m

    def execute_with_tools(self, messages, tools, user_id=None, temperature=0.7, max_tokens=2000, thinking=False):
        from core.gateway.execute_agent_task import _ollama_execute_with_tools

        return _ollama_execute_with_tools(
            messages=messages, tools=tools, model=self.model, temperature=temperature, max_tokens=max_tokens
        )


def _make_model_adapter(model, api_key):
    """B2：deepseek* ⇒ DeepSeekAdapter；其余（本地）⇒ _LocalOllamaAdapter。"""
    _m = str(model or "").strip().lower()
    if not _m.startswith("deepseek"):
        return _LocalOllamaAdapter(model)
    from core.lib.v8.adapters.deepseek_adapter import DeepSeekAdapter

    return DeepSeekAdapter(api_key=api_key, model=model)


def run_chat_entry(*, data, deps):
    """v9_agent_chat 全量编排：请求解析 → 归档 → 恢复层各块 → 桥接调度。

    契约：返回 (payload, kind)；"json" → 路由 jsonify；"stream" → 路由 Response(swc)。
    依赖注入 deps：bridge_loop_fn / allowed_commands / max_context_tokens /
                   deepseek_key_loaded / resolve_session_id_fn（防循环 import）。
    """
    """代理 DeepSeek API 调用，前端不暴露 Key"""
    global _read_cache, _consecutive_reads, _consecutive_lists, _session_failed, _session_artifacts
    try:
        # P3-B: 归档层归位 core/gateway/v9_chat/archive.py（解析 + TaskContract + 快照恢复）
        from core.gateway.v9_chat.archive import prepare_chat_entry

        _arch = prepare_chat_entry(data=data, resolve_session_id_fn=deps["resolve_session_id_fn"])
        if _arch["short_circuit"] is not None:
            return (_arch["short_circuit"], "json")
        _v9_max_total_tools = _arch["max_total_tools"]
        _sr = _single_run_guard(data, _arch["session_id"])
        if _sr is not None:
            return (_sr, "json")
        # 批191 · #5 补完：本轮开始清空压缩统计（否则「本轮没压缩」会显示**上一轮**的数字 = 假可见）；
        # 压缩一旦发生，由 message_assembler._compress_messages（压缩唯一出口）单源写回。
        try:
            from core.gateway.shared_state import clear_last_compact as _clc0

            _clc0(_arch["session_id"])
        except Exception:
            pass
        messages = _arch["messages"]
        model = _arch["model"]
        user_id = _arch["user_id"]
        session_id = _arch["session_id"]
        _auto_sid = _arch["auto_sid"]
        # P3-B 恢复层块 A：pending 恢复 + 回执分发 + 讨论/确认路由 + 上下文清理
        # 批222·A（老板拍板）：**seed 门前移到回合入口最早安全点** —— 位于 _single_run_guard 之后、
        # recover_session / ROUND / LLM / tool_call **之前**；未通过 ⇒ **短路该回合（零执行）**。
        try:
            # A3（DS 裁 #27 ＝「会话创建时 seed」；三问裁：缩 scope / LIVE 树 / 不硬链接）
            #   会话首入 ⇒ 建沙箱并 seed（实测 ≈21 MB；照字面全 scope 是 2.17 GB / 86,355 files ⇒
            #   与「PA 首用不卡」相悖）。落痕由 seed_sandbox 写；失败 **fail-loud**（返回显式 message）。
            #   回滚：V9_SEED_ON_CREATE=0（不改代码）；源覆盖：V9_SEED_SOURCE=<path>。
            if str(_os_w.environ.get("V9_SEED_ON_CREATE", "1")) != "0":
                try:
                    from core.gateway.seed_on_create import ensure_seeded as _ensure_seeded

                    _sd = _ensure_seeded(str(data.get("user_id") or ""), str(data.get("session_id") or ""))
                    if _sd.get("created"):
                        print(
                            "[SEED_ON_CREATE] 建沙箱并 seed: {}（files={} src_files={} commit={}）".format(
                                _sd.get("sandbox"),
                                (_sd.get("record") or {}).get("file_count"),
                                (_sd.get("record") or {}).get("source_file_count"),
                                (_sd.get("record") or {}).get("commit"),
                            )
                        )
                except Exception as _soc_e:
                    print(f"[SEED_ON_CREATE] seed 失败（fail-loud）: {_soc_e}")
                    return (
                        {
                            "success": False,
                            "status": "seed_failed",
                            "seed_error": True,
                            "message": f"会话 sandbox seed 失败：{str(_soc_e)[:200]}（查 V9_SEED_SOURCE / 磁盘）",
                        },
                        "json",
                    )
            from core.gateway.sandbox_seed import task_entry_gate as _teg

            _g2 = _teg(str(data.get("user_id") or ""), str(data.get("session_id") or ""))
            # 2026-09-20 · DSH 修（缺陷1「写确认回执断」· DS 已认 A1）：
            #   审批回执（approve_*）= **同一 run 的延续**，与 _single_run_guard 的豁免口径一致（见 :346/:364）。
            #   修正前：seed 门跑在「回执分发」（recover_session 内）之前且**无豁免** ⇒ 未 seed 会话里
            #   人拍「仅本次」的回执被短路，载荷 {blocked,status,reason} **无 message/error**
            #   ⇒ 前端 pa.html:2233（2026-09-20 之面 · 今漂）渲染成「确认未生效：未知响应」（**假成交**）。
            #   安全性：回执只对**已存在**的 _pending_writes[session_id] 生效（无 pending ⇒ write_expired），
            #   不会凭空写入；故豁免不放大权限面。
            #   运行期回滚开关：V9_SEED_GATE_EXEMPT_APPROVALS=0 ⇒ 退回旧行为。
            if str(_os_w.environ.get("V9_SEED_GATE_EXEMPT_APPROVALS", "1")) != "0" and any(
                _k_appr in (data or {}) for _k_appr in _APPROVAL_KEYS
            ):
                print("[SEED_GATE] 审批回执豁免（approve_* = 同一 run 的延续）⇒ 不短路，交回执自身逻辑")
                _g2 = {
                    "allowed": True,
                    "status": "approval_exempt",
                    "reason": "approve_* 豁免：回执是同一 run 的延续（DSH A1）",
                }
            if not _g2.get("allowed"):
                print("[SEED_GATE] 回合入口拦下（短路，未进 ROUND）: {}".format(str(_g2.get("reason"))[:140]))
                # 批222·A-2：**blocked 记录必须真落盘**（可独立查询）—— plan 空 + 明确原因。
                _bg_id = ""
                try:
                    import pathlib as _pl2
                    import time as _t2

                    from core.gateway.state_json import update_json as _uj2

                    _uid2 = str(data.get("user_id") or "")
                    _sid2 = str(data.get("session_id") or "")
                    _obj2 = ""
                    try:
                        for _m2 in messages or []:
                            if str(_m2.get("role")) == "user":
                                _obj2 = str(_m2.get("content") or "")[:300]
                        if not _obj2:
                            _obj2 = str(data.get("task") or "")[:300]
                    except Exception:
                        _obj2 = ""
                    _bg_id = f"goal_blocked_{int(_t2.time())}"
                    _gd2 = _pl2.Path("data/projects") / _uid2 / _sid2 / "clawsjoy_dev" / "goals"
                    _gd2.mkdir(parents=True, exist_ok=True)
                    _rec2 = {
                        "goal_id": _bg_id,
                        "objective": _obj2,
                        "status": "blocked",
                        "plan": [],
                        "blocked": True,
                        "blocked_reason": _g2.get("reason"),
                        "seed_status": _g2.get("status"),
                        "sandbox": _g2.get("sandbox"),
                        "started_at": _t2.time(),
                        "updated_at": _t2.time(),
                    }
                    _uj2(_gd2 / (_bg_id + ".json"), lambda _d: (_d.clear(), _d.update(_rec2)))
                    print(f"[SEED_GATE] blocked goal 已落盘: {_bg_id}")
                except Exception as _be:
                    print(f"[SEED_GATE] blocked 记录落盘失败（不阻断返回）: {_be}")
                return (
                    {
                        "success": False,
                        "blocked": True,
                        "status": "blocked",
                        "reason": _g2.get("reason"),
                        "seed_status": _g2.get("status"),
                        "sandbox": _g2.get("sandbox"),
                        "blocked_goal": _bg_id,
                    },
                    "json",
                )
        except Exception as _ge2:
            print(f"[SEED_GATE] 门异常（放行不阻断）：{_ge2}")

        from core.gateway.v9_chat.recovery import recover_session

        _rec = recover_session(
            data=data,
            messages=messages,
            model=model,
            user_id=user_id,
            session_id=session_id,
            restore_pending_fn=_v9_restore_pending_writes,
            handle_approvals_fn=_v9_handle_approvals,
            check_discuss_budget_fn=_check_discuss_token_budget,
            execute_agent_task_fn=_execute_agent_task,
            cleanup_ctx_fn=cleanup_task_context,
        )
        if _rec["short_circuit"] is not None:
            return (_rec["short_circuit"], "json")
        messages = _rec["messages"]
        plan_status = _rec["plan_status"]
        current_plan = _rec["current_plan"]
        import threading as _th

        print(
            f"[V9] thread={_th.current_thread().name}, key_in_environ={'DEEPSEEK_API_KEY' in os.environ}, key_len={len(os.environ.get('DEEPSEEK_API_KEY',''))}"
        )
        # P3-B 恢复层块 B：api_key 校验 + 异步入队 + 复杂度预判 + prompt 组装
        from core.gateway.v9_chat.recovery import build_prompt

        _b = build_prompt(
            data=data,
            messages=messages,
            model=model,
            user_id=user_id,
            session_id=session_id,
            allowed_commands=deps["allowed_commands"],
            deepseek_key_loaded=deps["deepseek_key_loaded"],
            execute_agent_task_fn=_execute_agent_task,
        )
        if _b["short_circuit"] is not None:
            return (_b["short_circuit"], "json")
        messages = _b["messages"]
        api_key = _b["api_key"]
        state_file = _b["state_file"]
        task_id = _b["task_id"]

        # P3-B 恢复层块 C：上下文注入 + 确认检测/继续恢复 + 轮检查点 + 多文件检测
        from core.gateway.v9_chat.recovery import inject_context_and_flags

        _c = inject_context_and_flags(
            messages=messages,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            inject_ctx_fn=_v9_inject_context,
            mark_plan_fn=_v9_mark_agent_plan,
            round_checkpoint_fn=_v9_round_checkpoint,
            looks_like_new_task_fn=_v9_looks_like_new_task,
            gsl_events_fn=lambda sid: _gsl_dig(sid)._events,
        )
        if _c["short_circuit"] is not None:
            return (_c["short_circuit"], "json")
        messages = _c["messages"]

        # P3-B 恢复层块 D：清缓存(R4) + task_progress/历史步骤/artifact + 代码预加载(R5)
        from core.gateway.v9_chat.recovery import preload_code_and_history

        _d = preload_code_and_history(data=data, messages=messages, user_id=user_id, session_id=session_id)
        if _d["short_circuit"] is not None:
            return (_d["short_circuit"], "json")
        messages = _d["messages"]

        # ★ 能力模型主动注入：根据任务类型从 world_model 提取模板
        try:
            _last_msg = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else ""
            _inject = None
            if any(kw in _last_msg for kw in ["创建", "新建", "添加"]) and any(
                kw in _last_msg for kw in ["ui/", "页面", "page"]
            ):
                _inject = _get_skeletons_by_type("ui", user_id, session_id)
            elif any(kw in _last_msg for kw in ["创建", "新建", "添加"]) and any(
                kw in _last_msg for kw in ["services/", "服务", "service"]
            ):
                _inject = _get_skeletons_by_type("services", user_id, session_id)
            elif any(kw in _last_msg for kw in ["创建", "新建", "添加"]) and any(
                kw in _last_msg for kw in ["models/", "模型", "model"]
            ):
                _inject = _get_skeletons_by_type("models", user_id, session_id)
            if _inject:
                _inject_sys_content(messages, f"\n\n【参考模板 — 基于项目中已有文件骨架（与磁盘文件一致）】\n{_inject}")
        except Exception:
            pass

        # 文件外部记忆引导：上下文接近阈值时提示 Agent 写临时文件
        # 构建 tools 定义（提前构建，供 400KB 截断后强制复查 tg_estimate(messages, tools) 使用）
        # P3-B 恢复层块 E：tools 构建/过滤/截断/压缩 + 兜底命令
        from core.gateway.v9_chat.recovery import build_tools_and_trim

        _e = build_tools_and_trim(
            messages=messages,
            tools=[],
            model=model,
            user_id=user_id,
            session_id=session_id,
            # 注: E 块内首行即 tools = get_agent_tools_fn()，入参 tools 会被覆盖(原块内本无此变量)
            state_file=state_file,
            get_agent_tools_fn=_get_agent_tools,
            filter_tools_fn=_filter_tools_by_mode,
            calc_token_budget_fn=_calc_token_budget,
            tg_estimate_fn=_tg_estimate,
            compress_fn=_compress_messages,
            validate_fn=_validate_messages,
            hard_truncate_fn=_hard_truncate_messages,
            estimate_tokens_fn=_estimate_tokens,
            max_context_tokens=deps["max_context_tokens"],
            get_sandbox_base_fn=_get_sandbox_base,
        )
        if _e["short_circuit"] is not None:
            return (_e["short_circuit"], "json")
        messages = _e["messages"]
        tools = _e["tools"]
        # 调模型（B2）：deepseek* ⇒ DeepSeekAdapter；本地 model ⇒ Ollama 本地 adapter
        # （无 DEEPSEEK_API_KEY 时 ⛔ 实例化 DeepSeekAdapter）
        try:
            adapter = _make_model_adapter(model, api_key)
        except Exception as _adp_err:
            print(f"[MODEL_FALLBACK] adapter 创建失败: {_adp_err}")
            adapter = None
        # P3-B 恢复层块 F：thinking 按需判定
        from core.gateway.v9_chat.recovery import prepare_thinking

        _th = prepare_thinking(messages=messages)
        _thinking2 = _th["thinking2"]
        _file_think = _th["file_think"]
        _last_usr_think = _th["last_usr_think"]
        # P3-B: 消息准备归位 bridge_call.prepare_request（消除与 main 内联版重复 R8）
        from core.gateway.v9_chat.bridge_call import prepare_request

        messages = prepare_request(messages=messages, tools=tools, model=model, user_id=user_id, session_id=session_id)
        # #94 桥接模式接入真实工具执行器：LLM 返回 tool_calls → 服务端执行并回传（最多 8 轮）
        # 经 _execute_sandbox_tool（@_with_tool_flow）→ tool_flow 记录 + 配额检查 + 连续失败暂停
        from core.gateway.tool_router import _execute_sandbox_tool as _exec_tool_94

        # #101 桥接工具步骤回传：记录每轮执行的工具摘要，供前端渲染工具使用记录
        _tool_steps = []

        # #101 G1 进度结构化：返回 tool_steps 时附 progress{done,total}（total=bridge 上限 8 轮）
        def _ts_progress():
            return {
                "done": len(_tool_steps),
                "total": _v9_max_total_tools,
                "step_index": len(_tool_steps),
                "total_steps": _v9_max_total_tools,
            }

        # G4 审计复核窗口起点：本 bridge 循环开始时间
        _task_start_ts = time.time()
        # #101 G6 目标跨轮次持久：任务开始时创建/激活 goal（objective=最近用户消息）
        # Goal 驱动多 turn: continue_goal=true 续跑时跳过 objective 覆盖(仅读取现有 goal)
        # P3-B 恢复层块 G：goal/steer/contract 编排 + 清理 + 桥接状态初始化（铁律：整块不可切）
        from core.gateway.v9_chat.recovery import orchestrate_goal

        _g = orchestrate_goal(
            data=data,
            messages=messages,
            user_id=user_id,
            session_id=session_id,
            max_total_tools=_v9_max_total_tools,
            load_policy_fn=_load_v9_execution_policy,
            plan_pending=_plan_pending,
            is_resume_fn=_v9_is_resume_utterance,
        )
        messages = _g["messages"]
        _bridge_exhausted = _g["bridge_exhausted"]
        # P3-B: 桥接调用层归位 core/gateway/v9_chat/bridge_call.py（SSE / 同步两条路径）
        from core.gateway.v9_chat.bridge_call import make_stream_response, run_bridge_sync

        _bc_kwargs = dict(
            bridge_loop_fn=deps["bridge_loop_fn"],
            messages=messages,
            tools=tools,
            user_id=user_id,
            session_id=session_id,
            adapter=adapter,
            thinking2=_thinking2,
            model=model,
            plan_status=plan_status,
            current_plan=current_plan,
            data=data,
            max_total_tools=_v9_max_total_tools,
            goal_info_fn=_goal_info_for_response,
        )
        # 任务2 流式: data.stream=true 时走 SSE（子线程 + 队列实时 yield 进度事件）
        if bool(data.get("stream")):
            from flask import Response as _SR_bc
            from flask import stream_with_context as _swc_bc

            return (_swc_bc(make_stream_response(**_bc_kwargs)), "stream")
        return (run_bridge_sync(**_bc_kwargs), "json")
        # ⚠ 不可达（在上面 return 之后）：F0.2b-final auto-bind 段，历史搬迁遗留，原样保留待确认
        # F0.2b-final auto-bind(2026-09-09): 新任务首轮(无契约)可编译出链式任务 → 建契约并绑定
        # (仅 >=2 节点链, 单节点/闲聊不绑 → 零回归)
        try:
            from core.gateway.task_contract import contract_for_session as _cfs_ab
            from core.gateway.task_contract import first_round_autobind as _fra_ab

            if _cfs_ab(session_id) is None:
                _task_u_ab = ""
                for _m_ab in reversed(messages):
                    if _m_ab.get("role") == "user" and str(_m_ab.get("content") or "").strip():
                        _task_u_ab = str(_m_ab.get("content") or "")
                        break
                if _task_u_ab and not _task_u_ab.startswith("[系统]"):
                    _c_ab, _b_ab = _fra_ab(session_id, "task_" + str(int(time.time())), _task_u_ab)
                    if _b_ab and _c_ab:
                        print("[CONTRACT] 首轮 auto-bind " + str(session_id) + " phase=" + str(_c_ab.get("phase")))
        except Exception as _e_ab:
            print(f"[CONTRACT] auto-bind 异常(忽略): {_e_ab}")

    except Exception as e:
        return ({"success": False, "error": str(e)}, "json")


_APPROVAL_KEYS = ("approve_write", "approve_plan", "approve_browser", "approve_reply")

import os as _os_w  # noqa: E402

_SINGLE_RUN_WINDOW_SEC = int(_os_w.environ.get("V9_SINGLE_RUN_WINDOW_SEC", "120"))


def _single_run_guard(data, session_id):
    """批189 · #6（老板补充）：**后端只允许一个活动 run**（PA = 单线程）。

    规则：
      - 审批回执（approve_*）= **同一 run 的延续** ⇒ 放行；
      - 否则若存在**心跳未超时**的 RUNNING/DETACHED 回合 ⇒ **拒绝**并发第二发（返回载荷）；
      - 环境开关 V9_SINGLE_RUN=0 可整体关闭（回滚用）。
    返回：拒绝载荷（dict）或 None（放行）。
    """
    import os as _os_sr

    if str(_os_sr.environ.get("V9_SINGLE_RUN", "1")) == "0":
        return None
    if _os_sr.environ.get("PYTEST_CURRENT_TEST") and str(_os_sr.environ.get("V9_SINGLE_RUN_FORCE", "0")) != "1":
        # 测试进程内不启用：本守卫读**全局** turns.db，会与既有集成测试（test_v9_stream 等）共享状态而误判 busy；
        # 其**行为**由 tests/unit/test_p189_single_run_guard.py 直接覆盖（5 条）。
        return None
    try:
        if any(k in (data or {}) for k in _APPROVAL_KEYS):
            return None
        from core.gateway import turn_registry as _trg

        # 批189 · ②：守卫改用**更短的活跃窗口**（默认 120s，env V9_SINGLE_RUN_WINDOW_SEC 可调）。
        # 原先沿用 STALE_AFTER_SEC=900s，使「客户端已断开、回合未收尾」的僵尸回合最长阻塞 15 分钟。
        _act = _trg.active_turns(stale_after=_SINGLE_RUN_WINDOW_SEC, limit=5)
        # 同 session 的 DETACHED（客户端已走）⇒ 允许接管并收尾旧回合；同 session RUNNING ⇒ 仍拒。
        _same_det = [a for a in _act if a.get("session_id") == session_id and a.get("status") == "DETACHED"]
        for _a0 in _same_det:
            try:
                _trg.finish_turn(_a0.get("turn_key"), "CANCELLED", "批189：同 session 新任务接管")
            except Exception:
                pass
            print("[SINGLE_RUN] 接管同 session 的 DETACHED 回合: {}".format(_a0.get("turn_key")))
        _act = [a for a in _act if a not in _same_det]
        if _act:
            _a = _act[0]
            print(
                "[SINGLE_RUN] 拒绝并发：已有活动任务 session={} status={}".format(
                    _a.get("session_id"), _a.get("status")
                )
            )
            return {
                "success": False,
                "status": "busy",
                "reason": "已有任务正在执行（PA 单线程，不支持并发）：{}".format(_a.get("session_id")),
                "active": _act,
                "hint": "可在 PA 页点「停止」取消它，或等它结束后再发。",
            }
    except Exception as _e_sr:
        print(f"[SINGLE_RUN] 守卫异常(放行): {_e_sr}")
    return None
