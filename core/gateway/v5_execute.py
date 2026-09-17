"""v5_execute 路由 — 从 agent_gateway_enhanced.py 抽取"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from flask import jsonify, request

from core.agents.cortex import agent_cortex
from core.gateway.execute_agent_task import _execute_agent_task
from core.gateway.quota_manager import _check_discuss_token_budget
from core.lib.gateway_helpers import cleanup_task_context
from core.lib.v8.ledger import ledger

logger = logging.getLogger(__name__)


def v5_execute_handler():
    """统一执行入口 - 所有Agent调用走这里"""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "无效JSON"}), 400

    raw_input = data.get("raw_input") or data.get("message") or ""
    if not raw_input:
        return jsonify({"response": "请输入消息内容", "success": False, "error": "消息不能为空"}), 200

    user_id = data.get("user_id", "guest")

    # /clean 会话清理指令（方案A: V5 入口兜底拦截，不发给 Agent）
    _cmd_clean = raw_input.strip().lower()
    if _cmd_clean in ("/clean", "/clear", "/clearsession"):
        try:
            # 函数内延迟 import（H2 防线允许；运行时已加载完成，无环）
            from core.gateway.session_cleaner import _clean_session_context

            _clean_session_context(user_id, data.get("session_id") or user_id)
        except Exception as _ce:
            print(f"[V5_CLEAN] 清理异常(忽略): {_ce}")
        return jsonify({"response": "✅ 会话已清理", "success": True, "cleaned": True})
    session_id = data.get("session_id")
    channel_id = data.get("channel_id", "")

    # 大请求体日志（变量定义之后）
    import sys

    _req_size = len(str(data))
    if _req_size > 200 * 1024:
        print(f"[V5_REQ_SIZE] 大请求体: {_req_size//1024}KB, user={user_id}, msg前50={raw_input[:50]}")

    # ✅ 修复：一次性构建 context，包含 channel_id
    context = {}
    if session_id:
        context["session_id"] = session_id
    if channel_id:
        context["channel_id"] = channel_id
    context = context if context else None
    # ========== @ 提及路由 ==========
    print(f"[V5] {user_id} | {raw_input[:100]}")

    plan_status = data.get("plan_status", "")
    current_plan = data.get("current_plan")

    # ========== 任务边界检测 ==========
    _task_state_file = Path(f"data/projects/{user_id}/{session_id}/.current_plan_task.json")
    _task_state = {}
    if _task_state_file.exists():
        try:
            _task_state = json.loads(_task_state_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"读取任务状态文件失败: {e}")
    current_task_id = _task_state.get("task_id", "")

    _new_task_kw = ["帮我", "开始", "规划", "做一个", "设计"]
    _continue_kw = ["改成", "换成", "不要", "换一个", "调整"]
    _confirm_kw = ["确认", "按此执行", "按计划执行", "开始执行", "好的", "行", "OK", "就按这个", "没问题", "可以开始"]

    if any(kw in raw_input for kw in _confirm_kw) and current_task_id:
        current_task_id = current_task_id.replace("::discussing", "") + "::confirmed"
        try:
            from core.lib.code_entity_extractor import extractor

            extractor.upsert_entity(
                {
                    "entity_type": "plan_discussion",
                    "entity_name": current_task_id,
                    "file_path": f"/tasks/{current_task_id}",
                    "signature": json.dumps({"status": "confirmed", "confirmed_at": time.time()}, ensure_ascii=False),
                }
            )
        except Exception as e:
            logger.warning(f"计划确认状态写入失败: {e}")
    elif any(kw in raw_input for kw in _new_task_kw) and "@计划经理" in raw_input:
        if current_task_id and "::confirmed" not in current_task_id and "::timeout" not in current_task_id:
            current_task_id = current_task_id.replace("::discussing", "") + "::timeout"
        current_task_id = f"plan_{user_id}_{int(time.time())}::discussing"
    elif any(kw in raw_input for kw in _continue_kw) and current_task_id:
        pass
    elif "@计划经理" not in raw_input:
        pass
    else:
        if not current_task_id:
            current_task_id = f"plan_{user_id}_{int(time.time())}::discussing"

    _task_state = {"task_id": current_task_id, "updated_at": time.time()}
    _task_state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(_task_state_file, "w", encoding="utf-8") as f:
        json.dump(_task_state, f)
    # ========== /任务边界检测 ==========

    if plan_status == "agent_discussion":
        focus = data.get("focus", "")
        agents = data.get("agents")
        from core.lib.v8.agent_discussion import AgentDiscussionEngine

        engine = AgentDiscussionEngine()
        final_event = {}
        for event in engine.discuss(focus=focus, agents=agents, user_id=user_id, session_id=data.get("session_id", "")):
            if event["type"] == "done":
                final_event = event
                break
        # --- 讨论结论入库 ---
        if final_event:
            _disc_dir = Path("data/v8/discussions")
            _disc_dir.mkdir(parents=True, exist_ok=True)
            _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            _record = {
                "topic": focus,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "consensus": final_event.get("consensus", False),
                "decision": final_event.get("decision", ""),
                "rounds": final_event.get("rounds", 0),
                "participants": [a["name"] for a in agents] if agents else [],
                "status": "pending_breakdown",
                "history": final_event.get("history", []),
            }
            _filepath = _disc_dir / f"{_ts}.json"
            with open(_filepath, "w", encoding="utf-8") as _f:
                json.dump(_record, _f, ensure_ascii=False, indent=2)
            print(f"[DISCUSSION_SAVED] {_filepath}")
        return jsonify(final_event)
    if plan_status == "discussing" and current_plan:
        _over, _used, _limit = _check_discuss_token_budget(user_id, data.get("server_id", "default"), "ollama")
        if _over:
            print(f"[BUDGET] 讨论预算超限: {_used}/{_limit}")
            return jsonify(
                {
                    "plan_status": "confirmed",
                    "message": f"今日 Token 预算已超限({_used}/{_limit})，自动确认计划。",
                    "current_plan": current_plan,
                }
            )
        from core.lib.v8.task_orchestrator import orchestrator

        result = orchestrator.discuss_plan(raw_input, current_plan, user_id, data.get("server_id", "default"))
        result["agent_name"] = "编排Agent"
        return jsonify(result)  # P0 修复：漏 return 导致讨论结果被丢弃、走 chat_agent

    if plan_status == "confirmed" and current_plan:
        import threading as _th_v5

        from core.lib.v8.task_orchestrator import orchestrator

        _plan = current_plan
        _plan["user_id"] = user_id
        _task_id = f"task_{int(time.time())}"
        _plan["session_id"] = f"v8_task_{_task_id}"
        _th_v5.Thread(
            target=_execute_agent_task,
            args=(
                user_id,
                _plan["session_id"],
                [{"role": "system", "content": f"执行已确认的计划：{json.dumps(_plan, ensure_ascii=False)}"}],
                os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
                _task_id,
                data.get("sub_task_id"),
            ),
            daemon=True,
        ).start()
        ledger.record_event(
            server_id=data.get("server_id", "default"),
            agent_name="计划经理",
            position="编排Agent",
            action="plan_confirmed",
            summary="计划已确认，V9 异步执行已启动",
        )
        return jsonify(
            {"status": "executing", "task_id": _task_id, "message": "计划已确认，V9 异步执行已启动。", "agent_name": "编排Agent"}
        )

    # @ 提及检测
    import re as _re_at

    _at_match = _re_at.match(r"@(\S+)", raw_input.strip())
    if _at_match:
        _at_name = _at_match.group(1).rstrip(",.，。!！?？:：")
        from core.lib.v8.roster_engine import roster_engine

        _member = roster_engine.get("default", _at_name)
        if not _member:
            # P1-1 岗位名兼容：@编排Agent → 匹配岗位=编排Agent 的成员（如"计划经理"）
            try:
                _member = next(
                    (m for m in roster_engine.list_active("default") if m.get("position") == _at_name),
                    None,
                )
            except Exception:
                _member = None
        if _member:
            _mapping = _member.get("agent_mapping", "")
            if _mapping == "orchestration_agent":
                from core.lib.v8.task_orchestrator import orchestrator

                _task_msg = raw_input.replace(f"@{_at_match.group(1)}", "").strip()
                result = orchestrator.plan(_task_msg, user_id, channel_id)
                result["agent_name"] = _at_name
                result["plan_status"] = "discussing"
                return jsonify(result)
            elif _mapping == "planner_agent":
                from core.agents.builtin.planner_agent import PlannerAgent

                _task_msg = raw_input.replace(f"@{_at_match.group(1)}", "").strip()
                _planner = PlannerAgent(user_id=user_id)
                dag = _planner.plan(_task_msg, {"channel_id": channel_id, "session_id": session_id})
                return jsonify(
                    {
                        "success": True,
                        "response": f"规划师已生成 DAG 任务图：{dag.get('name', '通用任务')}（来源 {dag.get('_meta', {}).get('source', 'none')}），共 {len(dag.get('nodes', []))} 个节点。",
                        "agent_name": _at_name,
                        "dag": dag,
                        "plan_status": "discussing",
                    }
                )
            elif _mapping == "metacognitive_agent":
                from core.lib.metacognition import Metacognition

                meta = Metacognition(f"agent_{user_id}")
                stats = meta.get_stats()
                return jsonify(
                    {
                        "success": True,
                        "response": f"元认知统计\n总反思: {stats.get('total_reflections', 0)}\n平均质量: {stats.get('avg_quality_recent', 0)}\n有用率: {stats.get('helpful_rate', 0)}",
                        "agent_name": _at_name,
                    }
                )
            else:
                result = agent_cortex.process(raw_input, user_id, context)
                return jsonify(result)
        else:
            return jsonify({"success": True, "response": f"❌ @{_at_name} 不在花名册中。请在右侧花名册面板中聘用该员工。", "agent_name": "系统"})
    # ========== @ 提及路由结束 ==========

    # ========== P1-2 写意图自动转计划（方案 A）==========
    # 普通消息含写入关键词 + 文件路径 → 自动转 plan() 讨论（无需 @计划经理）
    # 复用 quota_manager._WRITE_KEYWORDS；误触发由 #86 连续失败暂停兜底
    try:
        from core.gateway.quota_manager import _WRITE_KEYWORDS

        _has_file_path = _re_at.search(
            r"[\w\-./\\]+\.(?:py|md|txt|json|yaml|yml|toml|ini|sh|js|ts|html|css|csv|sql)", raw_input
        )
        if _has_file_path and any(_kw in raw_input for _kw in _WRITE_KEYWORDS):
            from core.lib.v8.task_orchestrator import orchestrator as _orch_p12

            _auto_plan = {
                "plan": [],
                "_discussion": [{"role": "user", "content": raw_input}],
                "user_id": user_id,
                "session_id": session_id or f"session_{user_id}",
            }
            _p12_result = _orch_p12.discuss_plan(raw_input, _auto_plan, user_id, data.get("server_id", "default"))
            _p12_result["agent_name"] = "编排Agent"
            _p12_result["auto_plan"] = True
            print(f"[P1-2] 写意图自动转计划: {raw_input[:80]}")
            return jsonify(_p12_result)
    except Exception:
        pass
    # ========== /P1-2 写意图自动转计划 ==========

    # V9 注入：频道上下文清理
    try:
        _ctx_msgs = [{"role": "user", "content": raw_input}]
        _ctx_msgs = cleanup_task_context(_ctx_msgs, raw_input[:80], user_id, data.get("server_id", "default"))
    except Exception:
        from core.lib.os_event_logger import write_os_event

        write_os_event(
            event_type="intercept",
            operation="write",
            os_action="blocked",
            reason="state_persist_failed",
            command="cleanup_task_context",
            detail={"error": "silent pass"},
            session_id=locals().get("session_id", ""),
        )
    # ========== 长线任务检测 — 启动 LongLoopStateMachine ==========
    _long_loop_kw = ["长线任务", "自动执行", "long_loop"]
    _use_long_loop = data.get("use_long_loop", False) or any(kw in raw_input for kw in _long_loop_kw)
    if _use_long_loop:
        import threading as _th_ll

        from core.lib.v8.long_loop_state_machine import LongLoopStateMachine
        from core.lib.v8.task_orchestrator import orchestrator

        _task_id_ll = f"long_loop_{int(time.time())}"
        _ll_sm = LongLoopStateMachine(
            task_id=_task_id_ll,
            session_id=session_id or f"session_{user_id}",
            user_id=user_id,
            orchestrator=orchestrator,
        )
        _th_ll.Thread(target=_ll_sm.run, args=(raw_input, user_id), daemon=True).start()
        return jsonify(
            {"status": "long_loop_started", "task_id": _task_id_ll, "message": "长线任务已启动，异步执行中。", "agent_name": "长线状态机"}
        )

    # 无 @ 提及 → 限制只走通用对话
    _restricted_context = context.copy() if context else {}
    _restricted_context["force_agent"] = "chat_agent"
    result = agent_cortex.process(raw_input, user_id, _restricted_context)

    # v8 记账钩子
    try:
        from core.lib.v8.billing_hook import record_if_roster_member

        server_id = data.get("server_id", "default")
        agent_name = result.get("agents_used", [""])[0] if result.get("agents_used") else ""
        tokens = result.get("tokens", 0)
        model = result.get("model", "")
        if agent_name and tokens:
            record_if_roster_member(server_id, agent_name, tokens, model)
    except Exception:
        from core.lib.os_event_logger import write_os_event

        write_os_event(
            event_type="intercept",
            operation="write",
            os_action="blocked",
            reason="billing_lost",
            command="record_if_roster_member",
            detail={"error": "silent pass"},
            agent_name=locals().get("agent_name", ""),
            server_id=locals().get("server_id", ""),
        )

    # 逐条发送 YouTube 搜索结果到 Discord
    videos = result.get("videos", [])
    if videos and channel_id:
        import requests as _r

        for i, v in enumerate(videos):
            msg = f"**{v['title']}**\n{v['channel']} | {v['url']}"
            try:
                r = _r.post(
                    "http://localhost:5002/v8/discord/notify",
                    json={"channel_id": channel_id, "message": msg, "username": "YouTube"},
                    timeout=5,
                )
            except Exception:
                pass

    # 发送 proactive 建议到 Discord
    proactive = result.get("proactive", "")
    if proactive and channel_id:
        try:
            import requests as _r

            _r.post(
                "http://localhost:5002/v8/discord/notify",
                json={"channel_id": channel_id, "message": proactive, "username": "ClawsJoy"},
                timeout=5,
            )
        except Exception:
            pass

    # 契约对齐: 从 agents_used 提取 agent 字段, 并确保 response/success 存在
    if result.get("agents_used"):
        result.setdefault("agent", result["agents_used"][0])
    if "response" not in result:
        result["response"] = result.get("reply") or result.get("content") or ""
    result.setdefault("success", True)
    return jsonify(result)
