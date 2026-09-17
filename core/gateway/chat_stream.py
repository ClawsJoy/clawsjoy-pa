"""chat_stream 路由 — 从 agent_gateway_enhanced.py 抽取"""


import os
import yaml
import concurrent.futures
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from flask import request, Response, stream_with_context
from core.lib.precision_feed import _precision_feed_cache, _load_asset
from core.gateway.context_validator import audit_agent_output
from core.gateway.quota_manager import _check_discuss_token_budget
from core.gateway.execute_agent_task import _execute_agent_task
from core.context.context_manager import _inject_user_history
from core.gateway.archive import _archive_user_message
from core.lib.v8.ledger import ledger
from core.agents.cortex import agent_cortex

logger = logging.getLogger(__name__)


def chat_stream_handler():
    from flask import Response, stream_with_context
    data = request.json or {}
    message = data.get("message", "")
    user_id = data.get("user_id", "guest")
    logger.info(f"[DEBUG_CHAT_STREAM] plan_status={data.get('plan_status')}, agent_name={data.get('agent_name')}, message前50={data.get('message','')[:50]}")
    # 在 generate() 外面，chat_stream() 里面，定义一个共享的降级函数
    def _fallback_to_ollama(msg, sys_prompt, agent_name):
        """降级到 Ollama 的共享逻辑"""
        import json
        from core.lib.llm_client import llm_client
        
        _model = "qwen2.5:7b-instruct-q4_0-gpu"
        
        for token in llm_client.generate_stream(
            prompt=msg, model=_model, task_type="chat", system_prompt=sys_prompt
        ):
            if not token:
                continue
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            try:
                data_token = json.loads(token)
                if "response" in data_token:
                    token = data_token["response"]
                elif "choices" in data_token:
                    delta = data_token["choices"][0].get("delta", {})
                    token = delta.get("content") or delta.get("reasoning_content") or ""
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
            if token:
                yield f"data: {json.dumps({'chunk': token, 'done': False})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    
    def _denoise_sys_prompt(sys_prompt: str) -> str:
        """降噪把关：过滤 EXPIRED/SKIPPED 任务引用和 _ 开头的脚本文件名引用
        
        保留动态上下文注入机制不变——只过滤噪声，不改变注入逻辑。
        """
        if not sys_prompt:
            return sys_prompt
        
        import re
        from core.gateway.inject_filter import inject_filter
        
        lines = sys_prompt.split('\n')
        filtered = []
        for line in lines:
            # 过滤 EXPIRED/SKIPPED 状态的任务引用
            if re.search(r'(?:\[|\s)(EXPIRED|SKIPPED)(?:\]|\s|$)', line):
                continue
            # 过滤 _ 开头的脚本文件名引用（如 _fix_v2.py, _do_cleanup.py 等）
            if re.search(r'(?:^|[\s/:])_\w+\.py', line):
                continue
            filtered.append(line)
        
        _denoised = '\n'.join(filtered)
        if len(_denoised) != len(sys_prompt):
            logger.info(f"[DENOISE] filtered {len(sys_prompt) - len(_denoised)} chars of noise from _sys_prompt")
        return _denoised


    
    def generate():
        # 编排 Agent 多轮讨论路由
        nonlocal data
        plan_status = data.get("plan_status", "")
        _sys_prompt = None
        # 精准投喂：按 os_precision_feeds.yaml 配置注入数据资产
        feeds_config = _precision_feed_cache
        # 获取当前 Agent 的 position
        _agent_pos = ""
        try:
            from core.lib.v8.roster_engine import roster_engine
            _agent_name = data.get("agent_name", "")
            _member = roster_engine.get("default", _agent_name)
            if _member:
                _agent_pos = _member.get("position", "")
        except Exception:
            pass
        # 精准投喂空数据源去重（避免文件不存在类的 source 重复加载）
        _DYNAMIC_SOURCES = {"os_events", "os_capabilities", "system_hypothesis"}
        EMPTY_SOURCES = set()
        _t0 = time.time()
        # 第一阶段：匹配并收集所有需要加载的任务（保持遍历顺序）
        _load_tasks = []  # [(feed, inj, source)]
        for feed in feeds_config.get("feeds", []):
            if feed.get("status") != "active":
                continue
            # 关键词匹配 OR agent_position 匹配
            _kw_match = any(kw in message for kw in feed.get("keywords", []))
            _pos_match = _agent_pos and _agent_pos in feed.get("agent_positions", [])
            if _kw_match or _pos_match:
                for inj in feed.get("inject", []):
                    source = inj["source"]
                    # 动态数据源（os_events/os_capabilities/system_hypothesis）永不跳过
                    if source in EMPTY_SOURCES and source not in _DYNAMIC_SOURCES:
                        logger.info(f"[PRECISION_FEED] skip already-empty source={source}")
                        continue
                    _load_tasks.append((feed, inj, source))
        # 第二阶段：并行加载所有资产
        _session_id_val = data.get("session_id")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as _executor:
            _futures = []
            for _feed, _inj, _source in _load_tasks:
                _params = dict(_inj.get("params", {}) or {})
                if _source == "sag_dependency_chain" and not _params.get("task_query"):
                    _params["task_query"] = message
                _futures.append(_executor.submit(_load_asset, _source, _params, user_id, _session_id_val, None, message))  # #41-3 变量驱动投喂
            # 第三阶段：按 feed 遍历顺序、source 遍历顺序收集结果并拼接 _sys_prompt
            for _idx, _f in enumerate(_futures):
                feed, inj, source = _load_tasks[_idx]
                try:
                    _feed_data = _f.result()
                except Exception:
                    import traceback
                    logger.warning(f"[PRECISION_FEED] exception for source={source}")
                    traceback.print_exc()
                    continue
                logger.info(f"[PRECISION_FEED] source={source}, data_len={len(_feed_data or '')}")
                if _feed_data:
                    _sys_prompt = (_sys_prompt or "") + f"\n\n## {source}\n{_feed_data[:inj.get('max_chars', 2000)]}"
                else:
                    if source not in _DYNAMIC_SOURCES:
                        logger.warning(f"[PRECISION_FEED] _load_asset returned empty for source={source}")
                        EMPTY_SOURCES.add(source)
        _t1 = time.time()
        logger.info(f"[PRECISION_FEED] parallel load {len(_load_tasks)} sources in {int((_t1 - _t0) * 1000)}ms")
        # 花名册身份：统一拼接
        _agent = data.get("agent_name", "")
        try:
            from core.lib.v8.roster_engine import roster_engine
            _member = roster_engine.get("default", _agent)
            if _member:
                _roster_prompt = _member.get("system_prompt", "")
                if _roster_prompt:
                    _sys_prompt = (_sys_prompt or "") + "\n\n" + _roster_prompt
        except Exception:
            pass
        
        # #166 路牌注入：Agent 自动获取历史对话上下文（JSONL + SAG）
        try:
            _hist_inject = _inject_user_history(data.get("session_id", ""), message)
            if _hist_inject:
                _sys_prompt = (_sys_prompt or "") + "\n\n" + _hist_inject
                logger.info(f"[USER_HISTORY] 已注入历史上下文 {len(_hist_inject)} 字符")
        except Exception as _he:
            logger.info(f"[USER_HISTORY] 注入失败: {_he}")
        if plan_status == "agent_discussion":
            focus = data.get("focus", "")
            agents = data.get("agents")
            from core.lib.v8.agent_discussion import AgentDiscussionEngine
            engine = AgentDiscussionEngine()
            _final_event = None
            for event in engine.discuss(focus=focus, agents=agents, user_id=user_id, session_id=data.get("session_id", "")):
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    _final_event = event
                    break
            # --- 讨论结论入库 ---
            if _final_event:
                _disc_dir = Path("data/v8/discussions")
                _disc_dir.mkdir(parents=True, exist_ok=True)
                _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                _record = {
                    "topic": focus,
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "consensus": _final_event.get("consensus", False),
                    "decision": _final_event.get("decision", ""),
                    "rounds": _final_event.get("rounds", 0),
                    "participants": [a["name"] for a in agents] if agents else [],
                    "status": "pending_breakdown",
                    "history": _final_event.get("history", []),
                }
                _filepath = _disc_dir / f"{_ts}.json"
                with open(_filepath, "w", encoding="utf-8") as _f:
                    json.dump(_record, _f, ensure_ascii=False, indent=2)
                logger.info(f"[DISCUSSION_SAVED] {_filepath}")
            return
        if plan_status == "discussing" and data.get("current_plan"):
            # === 讨论历史条数上限检查 ===
            try:
                _rules_path = Path("config/v8/audit_rules.yaml")
                if _rules_path.exists():
                    with open(_rules_path, encoding="utf-8") as _f:
                        _rules = yaml.safe_load(_f) or {}
                else:
                    _rules = {}
                _max_items = _rules.get("discussion", {}).get("max_history_items", 50)
            except Exception:
                _max_items = 50
            _discussion = data["current_plan"].get("_discussion", [])
            if len(_discussion) > _max_items:
                data["current_plan"]["_discussion"] = _discussion[-_max_items:]
                try:
                    from core.lib.os_event_logger import write_os_event
                    write_os_event(
                        event_type="intercept",
                        operation="truncate",
                        os_action="discussion_history",
                        reason=f"讨论历史超限({len(_discussion)}>{_max_items})，截断保留最近{_max_items}条",
                        command="chat_stream",
                        detail={"original_count": len(_discussion), "max_items": _max_items},
                        session_id=locals().get("session_id", ""),
                        user_id=locals().get("user_id", "")
                    )
                except Exception:
                    pass
            # === Token 预算检查 ===
            try:
                _over, _used, _limit = _check_discuss_token_budget(user_id, data.get("server_id", "default"), "ollama")
                if _over:
                    logger.info(f"[BUDGET] 讨论预算超限: {_used}/{_limit}")
                    yield f"data: {json.dumps({'done': True, 'plan_status': 'confirmed', 'current_plan': data.get('current_plan', {}), 'message': f'今日 Token 预算已超限({_used}/{_limit})，自动确认计划。'})}\n\n"
                    return
            except Exception as _be:
                logger.info(f"[BUDGET] 预算检查异常: {_be}")
            # === /Token 预算检查 ===
            # === 结束历史条数检查 ===
            try:
                from core.lib.v8.task_orchestrator import orchestrator
                discussion = orchestrator.discuss_plan(
                    user_message=message,
                    current_plan=data["current_plan"],
                    user_id=user_id,
                    server_id=data.get("server_id", "default")
                )
                logger.info(f"[CHAT_STREAM] discussion: {discussion}")
                if discussion.get("plan_status") == "confirmed":
                    ledger.record_event(server_id=data.get("server_id", "default"), agent_name="计划经理", position="编排Agent", action="plan_confirmed", summary="计划已确认，V9 异步执行已启动")
                    yield f"data: {json.dumps({'done': True, 'plan_status': 'confirmed', 'current_plan': discussion.get('current_plan', {})})}\n\n"
                    return
                prompt_info = orchestrator.build_discussion_prompt(
                    user_message=message,
                    current_plan=data["current_plan"],
                    user_id=user_id,
                    server_id=data.get("server_id", "default"),
                    agent_name=data.get("agent_name", "编排Agent"))
                import requests as _req
                _headers = {"Authorization": f"Bearer {prompt_info['api_key']}"} if prompt_info.get('api_key') else {}
                _system_content = prompt_info["system_prompt"]
                if _sys_prompt:
                    _system_content = _sys_prompt + "\n\n---\n\n" + _system_content
                _json = {
                    "model": prompt_info["model"],
                    "messages": [
                         {"role": "system", "content": _system_content},
                        {"role": "user", "content": message}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "stream": True,
                    "stream_options": {"include_usage": True}
                }
                _resp = _req.post(prompt_info["endpoint"], headers=_headers, json=_json, timeout=60, stream=True)
                logger.info(f"DeepSeek status: {_resp.status_code}")
                if _resp.status_code == 200:    
                    _full_content = ""
                    for _line in _resp.iter_lines():
                        if _line and _line.startswith(b'data: '):
                            _chunk = _line[6:].decode()
                            logger.info(f"[STREAM] chunk: {_chunk}")
                            if _chunk == '[DONE]':
                                # 从最后一个非 DONE chunk 提取 usage
                                try:
                                    if _last_chunk_data and _last_chunk_data.get("usage"):
                                        _usage = _last_chunk_data["usage"]
                                        _total_tokens = _usage.get("total_tokens", 0)
                                        if _total_tokens > 0:
                                            from core.lib.v8.billing_hook import record_if_roster_member
                                            record_if_roster_member(
                                                server_id=data.get("server_id", "default"),
                                                agent_name=data.get("agent_name", "编排Agent"),
                                                tokens=_total_tokens,
                                                model=prompt_info.get("model", ""),
                                            )
                                            logger.info(f"[BILLING] 记录讨论用量: {_total_tokens} tokens")
                                except Exception as _ue:
                                    logger.info(f"[BILLING] usage recording failed: {_ue}")
                                break
                            try:
                                _chunk_data = json.loads(_chunk)
                                _last_chunk_data = _chunk_data  # 保存最后 chunk 供 usage 提取
                                _delta = _chunk_data["choices"][0].get("delta", {}).get("reasoning_content", "") or _chunk_data["choices"][0].get("delta", {}).get("content", "")
                                _full_content += _delta
                                yield f"data: {json.dumps({'chunk': _delta, 'done': False})}\n\n"
                            except Exception:
                                from core.lib.os_event_logger import write_os_event
                                write_os_event(
                                    event_type="intercept",
                                    operation="read",
                                    os_action="blocked",
                                    reason="stream_parse_failed",
                                    command="chat_stream",
                                    detail={"error": "silent pass"},
                                    session_id=locals().get("session_id", ""),
                                    user_id=locals().get("user_id", "")
                                )
                    try:
                        _result = json.loads(_full_content)
                    except Exception:
                        _result = {"response": _full_content, "plan_updated": False, "plan_status": "discussing"}
                    _result["current_plan"] = _result.get("updated_plan", prompt_info["current_plan"].get("plan", []))
                    _result["current_plan"] = {"plan": _result["current_plan"], "_discussion": prompt_info["current_plan"].get("_discussion", [])}
                    yield f"data: {json.dumps({'done': True, 'plan_status': _result.get('plan_status', 'discussing'), 'current_plan': _result.get('current_plan', {})})}\n\n"
                    
                    # 持久化讨论记录到 SAG
                    try:
                        from core.lib.code_entity_extractor import extractor
                        extractor.upsert_entity({
                            "entity_type": "discussion_log",
                            "entity_name": f"discussion::{user_id}::{int(time.time())}",
                            "signature": json.dumps({
                                "user_message": message,
                                "assistant_response": _full_content[:500],
                                "plan_status": _result.get("plan_status", "discussing")
                            }, ensure_ascii=False),
                            "related_entities": ["orchestration_agent", user_id],
                            "file_path": ""
                        })
                    except Exception:
                        pass
                else:
                    raise Exception(f"DeepSeek API 返回 {_resp.status_code}")    
            except Exception as _e:
                 yield from _fallback_to_ollama(message, _sys_prompt, data.get("agent_name", ""))
                 return    
        elif plan_status == "confirmed" and data.get("current_plan"):
            # 计划确认 → 走 V9 异步执行路径
            _plan = data["current_plan"]
            _plan["user_id"] = user_id
            _task_id = f"task_{int(time.time())}"
            _plan["session_id"] = f"v8_task_{_task_id}"
            import threading as _th2
            _th2.Thread(
                target=_execute_agent_task,
                args=(user_id, _plan["session_id"], [
                    {"role": "system", "content": f"执行已确认的计划：{json.dumps(_plan, ensure_ascii=False)}"}
                ], os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"), _task_id, data.get("sub_task_id")),
                daemon=True
            ).start()
            response_text = json.dumps({
                "status": "executing",
                "task_id": _task_id,
                "message": "计划已确认，V9 异步执行已启动。",
            }, ensure_ascii=False)
        # === 简单任务快速通道 ===
        _SIMPLE_CODE_KEYWORDS = ["\u4fee\u6539", "\u4fee\u590d", "\u521b\u5efa", "\u6dfb\u52a0", "\u5b9e\u73b0", "\u91cd\u6784"]
        _is_codex = "```" in message
        _is_simple = (len(message) < 100 and not any(_kw in message for _kw in _SIMPLE_CODE_KEYWORDS)) or _is_codex
        if _is_simple:
            logger.info(f"[FAST_LANE] \u7b80\u5355\u4efb\u52a1\u5feb\u901f\u901a\u9053\uff1a\u8df3\u8fc7 AgentCortex \u610f\u56fe\u8bc6\u522b\u4e0e\u4e0a\u4e0b\u6587\u68c0\u7d22\uff0c\u76f4\u63a5\u964d\u7ea7\u8c03\u7528 Ollama")
            _sys_prompt = _sys_prompt or ""
            _sys_prompt = f"## \u5f53\u524d\u4efb\u52a1\n{message}\n\n" + _sys_prompt
            _sys_prompt = _denoise_sys_prompt(_sys_prompt)
            # #41 上下文管理：骨架化超长 prompt + 依赖链注入（快速通道）
            _sys_prompt = _skeletonize_sys_prompt(_sys_prompt)
            _dep_chain = _build_dependency_chain(message, user_id, data.get("session_id", ""))
            if _dep_chain:
                _sys_prompt = _sys_prompt + "\n\n" + _dep_chain
            _has_write_file = False
            _full_reply = ""
            for _chunk in _fallback_to_ollama(message, _sys_prompt, data.get("agent_name", "")):
                if _chunk.startswith('data: '):
                    try:
                        _parsed = json.loads(_chunk[6:])
                        if _parsed.get('chunk'):
                            _full_reply += _parsed['chunk']
                    except Exception:
                        pass
                yield _chunk
            # Phase 1 \u5b9e\u65f6\u5ba1\u8ba1\u5c42\uff1aAgent \u8f93\u51fa\u62e6\u622a
            for _warning in audit_agent_output(message, _full_reply):
                ledger.record_event(server_id=data.get("server_id", "default"), agent_name=data.get("agent_name", ""), position=_agent_pos, action="audit_warning", summary=f"\u5ba1\u8ba1\u8b66\u544a: {_warning}")
                yield f"data: {json.dumps({'chunk': _warning, 'done': False})}\n\n"
            ledger.record_event(server_id=data.get("server_id", "default"), agent_name=data.get("agent_name", ""), position=_agent_pos, action="task_complete", summary=f"\u5bf9\u8bdd\u5b8c\u6210(\u5feb\u901f\u901a\u9053): {message[:50]}")
            # #166 用户消息自动入库 SAG + JSONL
            _archive_user_message("user", message, data.get("session_id", ""), data.get("agent_name", ""), data.get("user_id", ""))
            return

        else:
            # AgentCortex 轻量预处理
            try:
                _action, _confidence = agent_cortex._infer_action(message)
                if _action != "chat" and _confidence > 0.5:
                    _extracted = agent_cortex._extract(message, _action)
                    _ctx = agent_cortex._retrieve_context(_action, _extracted, message, user_id)
                    _hypotheses = _ctx.get("system_hypotheses", [])
                    _plans = _ctx.get("plan_discussions", _ctx.get("plan", []))
                    if _hypotheses:
                        _sys_prompt = (_sys_prompt or "") + "\n\n## 系统假设\n" + json.dumps(_hypotheses, ensure_ascii=False, indent=2)
                    if _plans:
                        if isinstance(_plans, list):
                            _plans_str = json.dumps(_plans, ensure_ascii=False, indent=2)
                        else:
                            _plans_str = json.dumps([_plans], ensure_ascii=False, indent=2)
                        _sys_prompt = (_sys_prompt or "") + "\n\n## 计划讨论\n" + _plans_str
            except Exception:
                pass
            # 任务指令放在 _sys_prompt 最前面
            _sys_prompt = f"## 当前任务\n{message}\n\n" + (_sys_prompt or "")
            # 降噪把关：过滤 EXPIRED/SKIPPED 任务引用和 _ 开头的脚本文件名
            _sys_prompt = _denoise_sys_prompt(_sys_prompt)
            # #41 上下文管理：骨架化超长 prompt + 依赖链注入（AgentCortex 分支）
            _sys_prompt = _skeletonize_sys_prompt(_sys_prompt)
            _dep_chain = _build_dependency_chain(message, user_id, data.get("session_id", ""))
            if _dep_chain:
                _sys_prompt = _sys_prompt + "\n\n" + _dep_chain
            # 检查是否有 write_file 调用，无则加 hint
            _has_write_file = False
            _full_reply = ""
            for _chunk in _fallback_to_ollama(message, _sys_prompt, data.get("agent_name", "")):
                if 'write_file' in _chunk:
                    _has_write_file = True
                # 收集完整回复用于审计
                if _chunk.startswith('data: '):
                    try:
                        _parsed = json.loads(_chunk[6:])
                        if _parsed.get('chunk'):
                            _full_reply += _parsed['chunk']
                    except Exception:
                        pass
                if '"done": True' in _chunk or '"done": true' in _chunk:
                    if not _has_write_file:
                        yield f"data: {json.dumps({'chunk': '\U0001f4a1 \u63d0\u793a\uff1a\u5f53\u524d\u8f93\u51fa\u4e3a\u7eaf\u8ba1\u5212\uff0c\u672a\u68c0\u6d4b\u5230 write_file \u8c03\u7528\u3002\u5982\u9700\u6267\u884c\u4fee\u6539\uff0c\u8bf7\u786e\u4fdd\u4f7f\u7528\u5de5\u5177\u5b9e\u9645\u5199\u5165\u6587\u4ef6\u3002', 'done': False})}\n\n"
                yield _chunk
            # Phase 1 实时审计层：Agent 输出拦截
            for _warning in audit_agent_output(message, _full_reply):
                ledger.record_event(server_id=data.get("server_id", "default"), agent_name=data.get("agent_name", ""), position=_agent_pos, action="audit_warning", summary=f"审计警告: {_warning}")
                yield f"data: {json.dumps({'chunk': _warning, 'done': False})}\n\n"
            ledger.record_event(server_id=data.get("server_id", "default"), agent_name=data.get("agent_name", ""), position=_agent_pos, action="task_complete", summary=f"对话完成: {message[:50]}")
            # #166 用户消息自动入库 SAG + JSONL
            _archive_user_message("user", message, data.get("session_id", ""), data.get("agent_name", ""), data.get("user_id", ""))
            return    

         
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


def _skeletonize_sys_prompt(sys_prompt: str, max_chars: int = 6000) -> str:
    """骨架化：按优先级保留 system prompt 内容。"""
    if len(sys_prompt) <= max_chars:
        return sys_prompt
    sections = sys_prompt.split("## ")
    core = sections[0]
    body = sections[1:]
    priority = {"当前任务": 0, "系统假设": 1, "计划讨论": 2}
    sorted_body = sorted(body, key=lambda s: priority.get(s.split("\n")[0].strip(), 99))
    result = core
    for section in sorted_body:
        if len(result) + len(section) + 4 <= max_chars:
            result += "## " + section
        else:
            remaining = max_chars - len(result) - 20
            if remaining > 100:
                result += "## " + section[:remaining] + "\n...[已截断]"
            break
    import logging
    logging.getLogger(__name__).info(f"[SKELETON] {len(sys_prompt)} -> {len(result)} chars")
    return result



def _build_dependency_chain(message: str, user_id: str, session_id: str) -> str:
    """依赖链：从当前任务提取关键词，展开关联的 plan/hypothesis/capability。"""
    import json as _json
    import re as _re
    
    # 提取关键词（简单版：中文2字词+英文3字母词）
    _kw = _re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z_]{3,}', message)
    if not _kw:
        return ""
    
    chain_parts = []
    try:
        import psycopg2
        conn = psycopg2.connect("postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev")
        cur = conn.cursor()
        
        # 查相关 plan
        for kw in _kw[:3]:
            cur.execute(
                "SELECT entity_name, signature FROM code_entities WHERE entity_type='plan_discussion' AND signature ILIKE %s LIMIT 1",
                (f"%{kw}%",)
            )
            row = cur.fetchone()
            if row:
                chain_parts.append(f"相关计划: {row[0][:50]}")
                break
        
        # 查相关 hypothesis
        cur.execute(
            "SELECT entity_name, signature FROM code_entities WHERE entity_type='system_hypothesis' ORDER BY created_at DESC LIMIT 3"
        )
        for row in cur.fetchall():
            sig = row[1] or ""
            if any(kw.lower() in sig.lower() for kw in _kw[:3]):
                chain_parts.append(f"相关假设: {row[0]}")
        
        # #87 依赖链增强：查 code_edges 图边（imports 边），注入相关依赖
        for kw in _kw[:2]:
            cur.execute(
                "SELECT source_name, target_name FROM code_edges "
                "WHERE edge_type='imports' AND (source_name ILIKE %s OR target_name ILIKE %s) LIMIT 5",
                (f"%{kw}%", f"%{kw}%")
            )
            for _row in cur.fetchall():
                chain_parts.append(f"依赖边: {_row[0]} → {_row[1]}")
        
        cur.close()
        conn.close()
    except Exception:
        pass
    
    if chain_parts:
        return "## 依赖链\n" + "\n".join(chain_parts[:5])
    return ""
