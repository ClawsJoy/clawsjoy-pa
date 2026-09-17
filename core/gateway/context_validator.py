"""上下文校验模块 — 从 agent_gateway_enhanced.py 抽取"""

import json
import logging
from pathlib import Path

from core.gateway.archive import _archive_asset
from core.gateway.shared_state import _session_write_tracker, _tracker_setdefault

logger = logging.getLogger(__name__)


def _check_recent_writes(messages, session_id=None):
    """检查最近6轮是否有成功的写入操作（工具名+结果双重校验），
    并同步更新会话级写入追踪器 _session_write_tracker（#166）。

    - write_file / write_large 成功 → write_count += 1，文件加入 files_written
    - execute_command 写命令成功 → execute_write_count += 1
    - _tc_id 去重，避免同一工具调用被重复计数
    """
    _session_key = session_id or ("msg:%d" % id(messages))
    _success_markers = ["auto_fixed", "success", "已写入", "写入成功", "ok"]
    for m in messages[-6:]:
        # 检查 assistant 的 tool_calls
        for tc in m.get("tool_calls", []):
            _name = tc.get("function", {}).get("name", "")
            if _name in ("write_file", "write_large"):
                # 还需要找到对应的 tool result 确认成功
                _tc_id = tc.get("id", "")
                for _rm in messages[-6:]:
                    if _rm.get("role") == "tool" and _rm.get("tool_call_id") == _tc_id:
                        _result = str(_rm.get("content", "")).lower()
                        if any(_mk in _result for _mk in _success_markers):
                            # 会话级追踪：write_count += 1，文件加入 files_written
                            _trk = _tracker_setdefault(
                                _session_write_tracker,
                                _session_key,
                                lambda: {
                                    "write_count": 0,
                                    "execute_write_count": 0,
                                    "files_written": [],
                                    "_seen": set(),
                                },
                            )
                            # #96 修复：execute_command/sandbox_write 可能用 {} 初始化 tracker（缺 _seen/write_count 键）→ KeyError
                            _trk.setdefault("_seen", set())
                            _trk.setdefault("write_count", 0)
                            if _tc_id not in _trk["_seen"]:
                                _trk["_seen"].add(_tc_id)
                                _trk["write_count"] += 1
                                try:
                                    _args = tc.get("function", {}).get("arguments", "")
                                    _parsed = _args if isinstance(_args, dict) else json.loads(_args or "{}")
                                    _fp = str(_parsed.get("path", ""))
                                    if _fp and _fp not in _trk["files_written"]:
                                        _trk["files_written"].append(_fp)
                                except Exception:
                                    pass
                            return True
            elif _name == "execute_command":
                # execute_command 区分读写：
                #   读命令（_classify_command == read）→ 调用即视为有效执行
                #   写命令 → tool result 含成功标记才算有效执行
                _cmd = ""
                try:
                    _args = tc.get("function", {}).get("arguments", "")
                    _parsed = _args if isinstance(_args, dict) else json.loads(_args or "{}")
                    _cmd = str(_parsed.get("command", ""))
                except Exception:
                    _cmd = ""
                from core.gateway.sandbox_ops import _classify_command

                _is_write_cmd = _classify_command(_cmd) == "write"
                _tc_id = tc.get("id", "")
                for _rm in messages[-6:]:
                    if _rm.get("role") == "tool" and _rm.get("tool_call_id") == _tc_id:
                        _result = str(_rm.get("content", "")).lower()
                        if any(_mk in _result for _mk in _success_markers):
                            # 会话级追踪：execute_command 写操作成功 → execute_write_count += 1
                            if _is_write_cmd:
                                _trk = _tracker_setdefault(
                                    _session_write_tracker,
                                    _session_key,
                                    lambda: {
                                        "write_count": 0,
                                        "execute_write_count": 0,
                                        "files_written": [],
                                        "_seen": set(),
                                    },
                                )
                                # #96 修复：旧 tracker 可能缺 _seen/execute_write_count 键 → KeyError
                                _trk.setdefault("_seen", set())
                                _trk.setdefault("execute_write_count", 0)
                                if _tc_id not in _trk["_seen"]:
                                    _trk["_seen"].add(_tc_id)
                                    _trk["execute_write_count"] += 1
                            return True
    return False


def _planning_output_valid(messages, session_id=None):
    """统一判定计划任务输出是否有效：优先落盘校验，落盘失败/文件缺失兜底原文本判定
    (#169 方案A：先 _archive_asset("plan", ...) 落盘 data/plans/{session_id}/plan_*.json，
     再读最新 plan_*.json 校验；落盘失败或文件缺失 -> 原文本关键词判定)
    """
    if not messages:
        return False
    _plan_kws = ("plan", "计划", "规划", "安排")
    _neg_kws = ("没有计划", "无计划", "no plan")
    # ===== #169 方案A：计划落盘优先校验 =====
    if session_id:
        try:
            _plan_content = ""
            for _m in reversed(messages):
                if _m.get("role") == "assistant":
                    _plan_content = str(_m.get("content", "") or "")
                    break
            if not _plan_content:
                _plan_content = "\n".join(
                    f"[{_m.get('role', '')}] {str(_m.get('content', ''))[:300]}"
                    for _m in messages[-10:]
                    if _m.get("content")
                )
            _plan_title = (_plan_content.splitlines()[0] if _plan_content.splitlines() else "计划输出")[:120]
            _archived_path = _archive_asset("plan", session_id, _plan_title, _plan_content[:4000], messages)
        except Exception as _arch_err:
            print(f"[PLAN_VALID] 计划落盘失败，走兜底文本判定: {_arch_err}")
            _archived_path = ""
        if _archived_path:
            try:
                _plans_dir = Path(f"data/plans/{session_id}")
                _plan_files = sorted(
                    _plans_dir.glob("plan_*.json"),
                    key=lambda _p: _p.stat().st_mtime,
                    reverse=True,
                )
                if _plan_files:
                    _latest_plan = json.loads(_plan_files[0].read_text(encoding="utf-8"))
                    _p_content = str(_latest_plan.get("content", "") or "")
                    _p_low = _p_content.lower()
                    # 否定排除：明确表示没有计划 -> 无效
                    if any(_kw in _p_low for _kw in _neg_kws):
                        return False
                    # 结构校验：steps 非空 或 内容含计划关键词 -> 有效
                    if _latest_plan.get("steps"):
                        return True
                    if any(_kw in _p_low for _kw in _plan_kws):
                        return True
            except Exception as _read_err:
                print(f"[PLAN_VALID] 读取最新 plan json 失败，走兜底文本判定: {_read_err}")
    # ===== 兜底：原文本判定（最近6轮 assistant 消息含计划关键词） =====
    for _m in messages[-6:]:
        if _m.get("role") == "assistant":
            _content = str(_m.get("content", "") or "")
            _low = _content.lower()
            # 1) 否定排除：明确表示没有计划 -> 无效
            if any(_kw in _low for _kw in _neg_kws):
                return False
            # 2) 结构标记：>=2 个以 数字+点号 或 -/* 开头的行 -> 强通过
            _struct_lines = 0
            for _line in _content.splitlines():
                _s = _line.strip()
                if (
                    (_s and _s[0].isdigit() and len(_s) > 1 and _s[1] == ".")
                    or _s.startswith("- ")
                    or _s.startswith("* ")
                ):
                    _struct_lines += 1
            if _struct_lines >= 2:
                return True
            if any(_kw in _low for _kw in _plan_kws):
                return True
    return False


def _should_inject_hint(messages, hint_msg):
    """全局去重：最近 6 条消息中已有 2 次相同提示则不再注入"""
    if not hint_msg:
        return False
    _hint_marker = "[系统]"
    _recent_hint_count = sum(
        1
        for m in messages[-6:]
        if m.get("role") in ["system", "assistant"] and _hint_marker in str(m.get("content", ""))
    )
    return _recent_hint_count < 2


def _is_plan_message(content: str) -> bool:
    if not content:
        return False
    import re

    _steps = re.findall(r"(?:^|\n)\s*\d+[\.\)]\s", content)
    if len(_steps) < 2:
        return False
    _has_target = bool(re.search(r"(?:修改|创建|删除|添加|新建|写入)\s*(?:文件|目录|路由|页面|组件)?\s*[：:]?\s*[\w_/\-\.]+", content))
    _has_path = bool(re.search(r"[\w_]+/[\w_]+\.\w+", content))
    if not (_has_target or _has_path):
        return False
    _action_steps = re.findall(
        r"\d+[\.\)]\s.*(?:修改|创建|删除|添加|新建|写入|在|用|通过|从|调用|实现|add|create|delete|modify|write|build|implement|update|remove)",
        content,
    )
    if re.search(r"[✅✓]|已完成|执行结果|任务完成|修改完成", content):
        return False
    return len(_action_steps) >= 2


def audit_agent_output(user_message: str, agent_reply: str, skip_evidence: bool = False) -> list:
    """Phase 1 实时审计层：Agent 输出拦截
    规则A：无关脚本检测
    规则B：超范围文件修改检测

    任务3 v8: skip_evidence=True 时跳过规则C(证据条款)——子任务写入已由
    VerificationChain + git 钩子 + 审计复核三重确认, 规则C 对子任务 LLM
    简短回复误报(日志噪音); 共享任务(代码修改)保持证据条款防线。
    """
    import re

    warnings = []
    # 规则A：检测 Agent 回复中是否包含 _*.py 脚本名
    _scripts = re.findall(r"(?<![a-zA-Z])_\w+\.py", agent_reply)
    if _scripts:
        for _s in sorted(set(_scripts)):
            warnings.append(f"[审计] \u26a0\ufe0f 检测到执行了无关脚本：{_s}")
    # 规则B：如果用户指令指定了修改范围，检查实际修改的文件
    _scope = re.search(r"只(?:改|修改|允许)(?:\s+)(\S+\.\w+)", user_message)
    if _scope:
        _allowed = _scope.group(1)
        _found = re.findall(
            r"(?:修改|写入|创建|write_file|编辑)(?:\s*(?:文件|了))?\s*[`\"\']?([\w./-]+\.\w+)[`\"\']?", agent_reply
        )
        _extra = [f for f in _found if f != _allowed and _allowed not in f]
        if _extra:
            warnings.append(f"[审计] \u26a0\ufe0f 修改了指令外的文件：" + ", ".join(sorted(set(_extra))))
    # 规则C：证据条款检测（只对修改类任务触发，只读/计划类不检测；子任务 skip_evidence 跳过）
    if skip_evidence:
        return warnings
    _modify_kw = re.search(r"(?:修改|写入|创建|编辑|write_file|增加|添加|替换|重构|新增|修正)", user_message)
    _readonly_kw = re.search(r"(?:只读|只输出|计划|讨论|分析|报告|查询|列出|查看)", user_message)
    if _modify_kw and not _readonly_kw:
        _ev_path = bool(re.search(r"[\w./-]+\.(?:py|md|json|yaml|yml|toml|ini|txt|sh|js|ts|html|css)\b", agent_reply))
        _ev_line = bool(
            re.search(r"(?:第\s*\d+\s*行|line\s*\d+|L\d{1,6}|[\w./-]+\.\w+:\s*\d{1,6}\b)", agent_reply, re.IGNORECASE)
        )
        _ev_diff = bool(re.search(r"(?:diff|改前|改后|原内容|新内容|->|→)", agent_reply))
        _ev_hit = sum([_ev_path, _ev_line, _ev_diff])
        if _ev_hit < 2:
            _ev_missing = []
            if not _ev_path:
                _ev_missing.append("文件路径")
            if not _ev_line:
                _ev_missing.append("行号")
            if not _ev_diff:
                _ev_missing.append("diff摘要")
            warnings.append(f"[审计] \u26a0\ufe0f 证据条款检测未通过：三要素仅命中{_ev_hit}/3，缺失：" + "、".join(_ev_missing))

    if warnings:
        logger.info(f"[AUDIT] {'; '.join(warnings)}")
    return warnings


def _get_task_done_when(session_id: str) -> str:
    """从 .agent_state.json 读取 plan_data，提取 done_when 供 VerificationChain Step5 断言（#166）。

    仅传 session_id，通过 glob 定位 {user_id}/{session_id}/clawsjoy_dev/.agent_state.json；
    缺失、无 plan_data 或读取异常时返回空串（run_verification_chain 的 done_when 默认空，可安全跳过）。
    """
    try:
        import json
        from pathlib import Path

        _state_file = None
        for _root in ("data/projects", "."):
            _base = Path(_root)
            if not _base.exists():
                continue
            for _f in _base.rglob(".agent_state.json"):
                if session_id and session_id in str(_f):
                    _state_file = _f
                    break
            if _state_file is not None:
                break
        if _state_file is None:
            return ""
        _data = json.loads(_state_file.read_text(encoding="utf-8"))
        _plan_data = _data.get("plan_data")
        if _plan_data is None and isinstance(_data.get("task_progress"), dict):
            _plan_data = _data["task_progress"].get("plan_data")
        if isinstance(_plan_data, str):
            _plan_data = json.loads(_plan_data)
        if isinstance(_plan_data, dict):
            _dw = _plan_data.get("done_when")
            if _dw:
                return str(_dw)
        return ""
    except Exception:
        return ""


def _classify_task_type(messages):
    """从用户消息中提取任务类型（S4 依赖，从 agent_gateway_enhanced 归位）。"""
    from core.lib.gateway_helpers import last_user_task_msg

    _last_usr = last_user_task_msg(messages)
    _write_kw = ["修改", "创建", "添加", "修复", "实现", "完善", "写入", "重构", "解决", "优化", "更新", "调整", "落盘", "改", "统一"]
    # analysis 类型不要求写入（假完成误判修复）
    _analysis_kw = ["只读", "分析", "排查", "检查", "报告", "统计"]
    _discuss_kw = ["讨论", "商量", "你们讨论"]
    _plan_kw = ["计划", "规划", "安排"]
    # audit 类型：检查/排查类 + 列表结构（编号或项目符号），优先级在 analysis 之前
    _audit_kw = ["检查", "排查", "审计", "验证", "确认"]
    _has_list = any(
        _l.strip()
        and (_l.strip()[0] in "-*•" or (len(_l.strip()) >= 2 and _l.strip()[0].isdigit() and _l.strip()[1] in ".、)）"))
        for _l in _last_usr.splitlines()
    )
    if any(kw in _last_usr for kw in _write_kw):
        return "code_modify"
    elif "交付" in _last_usr or "生成" in _last_usr:
        return "delivery"
    elif any(kw in _last_usr for kw in _audit_kw) and _has_list:
        return "audit"
    elif any(kw in _last_usr for kw in _analysis_kw):
        return "analysis"
    elif any(kw in _last_usr for kw in _discuss_kw):
        return "discussion"
    elif any(kw in _last_usr for kw in _plan_kw):
        return "planning"
    return "general"


def _is_readonly_task(user_prompt: str) -> bool:
    """检测是否为只读任务，避免在核查/分析时注入写入催促（S4 依赖，归位）。"""
    readonly_keywords = ["只读", "核查", "检查", "分析", "盘点", "核实", "建议", "排查", "报告", "统计"]
    write_intent_kw = ["修复", "修改", "解决", "优化", "重构", "更新", "改", "创建", "实现", "编写", "补充", "完善", "新增", "添加", "写入"]
    if any(kw in user_prompt for kw in write_intent_kw):
        return False  # 含写意图动作词（如"检查并修复"）不算只读任务
    return any(kw in user_prompt for kw in readonly_keywords)


def _v9_detect_ask(_bmsg):
    """H1 最小门控验证: 检测 Agent 是否输出【ask】结构化提问。返回 ask dict 或 None。"""
    # #101 G3 ask 式提问通道：Agent 输出【ask】结构化提问 → 返回 options 供前端选择
    _ask_text = ""
    _ask_match = None
    _ask_content = str(_bmsg.get("content") or "")
    if "【ask】" in _ask_content or "【ASK】" in _ask_content:
        import re as _re_ask

        _ask_match = _re_ask.search(r"【ask】", _ask_content, _re_ask.IGNORECASE)
        if _ask_match:
            _ask_seg = _ask_content[_ask_match.end() :].strip()
            # 问题 = ask 标记后到第一个选项行之间
            _ask_lines = [ln.strip() for ln in _ask_seg.splitlines() if ln.strip()]
            _ask_question = ""
            _ask_options = []
            for _ln in _ask_lines:
                _opt = _re_ask.match(r"^(?:选项|Option)\s*[A-Za-z0-9]+\s*[：:]\s*(.+)$", _ln, _re_ask.IGNORECASE)
                if _opt:
                    _ask_options.append(_opt.group(1).strip())
                elif not _ask_options:
                    _ask_question = (_ask_question + " " + _ln).strip()
            if _ask_options:
                _ask_text = _ask_question or _ask_seg[:200]
                print(f"[ASK_GATE] Agent 提问: {_ask_text[:80]} / {len(_ask_options)} 选项")
                return {"question": _ask_text, "options": _ask_options}
    return None
