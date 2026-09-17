"""跨 session 记忆持久层(用户级, 同一 user_id 的所有 session 共享)。

known_issues:   失败工具调用(连续失败/递归/越权)沉淀的"别踩的坑"
known_patterns: 任务完成后的关键 finding/报告摘要沉淀的"有效做法"
存储:           data/projects/{user_id}/memory/{known_issues|known_patterns}.json
结构:           [{content, ts}]
防膨胀:         上限 20 条 / 相同 content 去重(更新 ts 提前) / 超限按 ts 淘汰最旧
"""
import json
import threading
import time
from pathlib import Path

_MEMORY_ROOT = Path("data/projects")
_LOCK = threading.Lock()
MAX_ENTRIES = 20
CONTENT_LIMIT = 500


def _memory_file(user_id, kind):
    return _MEMORY_ROOT / str(user_id or "default") / "memory" / f"{kind}.json"


def _load_memory(user_id, kind):
    """读取用户级记忆列表(防御损坏)。"""
    try:
        f = _memory_file(user_id, kind)
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [e for e in data if isinstance(e, dict) and e.get("content")]
    except Exception:
        pass
    return []


def _save_memory(user_id, kind, entries):
    try:
        f = _memory_file(user_id, kind)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[MEMORY] 保存失败: {e}")


# 2026-09-07: 记忆卫生 — 系统注入串/诊断会话噪声/原始报错路径不进跨会话记忆。
# 旧实现把 [系统] 阶段指引、diag/dbg/inject_check 等诊断会话的失败、[TOOL_ARGS] 原始
# 报错都沉淀下来 → 每条新任务 round0 都被注入这些失败噪声 → 模型困惑 → 空工具调用。
_JUNK_MEM_MARKERS = (
    "[系统]",
    "[TOOL_ARGS]",
    "[系统拦截",
    "diag_",
    "dbg_",
    "inject_check",
    "repro_",
    "hc2_",
    "s_d_sub",
    "No such file or directory: 'data/projects/",
)


def _is_junk_memory(content):
    return any(_mk in content for _mk in _JUNK_MEM_MARKERS)


def _remember(user_id, kind, content, limit=MAX_ENTRIES):
    content = str(content or "").strip()[:CONTENT_LIMIT]
    if not content or not user_id:
        return None
    if _is_junk_memory(content):
        return None
    with _LOCK:
        entries = _load_memory(user_id, kind)
        # 去重: 相同内容更新 ts 提前(最新引用优先)
        for e in entries:
            if e.get("content") == content:
                e["ts"] = time.time()
                _save_memory(user_id, kind, entries)
                return e
        entry = {"content": content, "ts": time.time()}
        entries.append(entry)
        entries.sort(key=lambda e: e.get("ts", 0), reverse=True)
        if len(entries) > limit:
            entries = entries[:limit]
        _save_memory(user_id, kind, entries)
        return entry


def remember_issue(user_id, issue):
    """沉淀失败经验(known_issues)。"""
    return _remember(user_id, "known_issues", issue)


def remember_pattern(user_id, pattern):
    """沉淀有效模式(known_patterns)。"""
    return _remember(user_id, "known_patterns", pattern)


def get_memory_context(user_id, max_issues=5, max_patterns=5):
    """构建跨 session 注入文本: 「已知问题：...」「已知模式：...」。"""
    try:
        issues = _load_memory(user_id, "known_issues")[:max_issues]
        patterns = _load_memory(user_id, "known_patterns")[:max_patterns]
    except Exception:
        return ""
    parts = []
    if issues:
        parts.append("已知问题：" + "；".join(str(e.get("content", ""))[:120] for e in issues))
    if patterns:
        parts.append("已知模式：" + "；".join(str(e.get("content", ""))[:120] for e in patterns))
    return "\n".join(parts)


def clear_memory(user_id, kind=None):
    """清空记忆(测试/用户重置用)。kind 为空清全部。"""
    for k in ("known_issues", "known_patterns") if kind is None else (kind,):
        try:
            f = _memory_file(user_id, k)
            if f.exists():
                f.unlink()
        except Exception:
            pass


def persist_session_learning_state(*, messages, user_id, session_id, tokens, _task_start_ts, meta_state=None):
    """学习能力：持久化会话状态（S2，从 _v9_bridge_loop 归位，2026-09-12）。

    契约：原地写 .agent_state.json（合并 meta_state 元认知结论 → 修复 S1 结论被覆盖）+ 同步
    VerificationChain/审计完成判定 + 上下文管理器 add_turn。返回最终 state dict。
    """
    try:
        from datetime import datetime

        from core.gateway.completion_guard import _artifact_incomplete_pages
        from core.gateway.context_validator import _check_recent_writes, _classify_task_type, _get_task_done_when
        from core.gateway.execute_agent_task import _task_config
        from core.gateway.sag_feedback import _update_sag_feedback
        from core.gateway.sandbox_git import _has_git_diff
        from core.gateway.shared_state import _session_artifacts
        from core.gateway.state_persist import _persist_state
        from core.lib.code_entity_extractor import TaskStateMachine
        from core.lib.gateway_helpers import _get_sandbox_base

        project_dir = _get_sandbox_base(user_id, session_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        # 沙箱 Git 自动初始化
        _git_dir = project_dir / ".git"
        if not _git_dir.exists():
            import subprocess as _sp

            _sp.run(["git", "init"], cwd=str(project_dir), capture_output=True)
            _sp.run(["git", "config", "user.name", "ClawsJoy Agent"], cwd=str(project_dir), capture_output=True)
            _sp.run(["git", "config", "user.email", "agent@clawsjoy.local"], cwd=str(project_dir), capture_output=True)
            _sp.run(["git", "add", "-A"], cwd=str(project_dir), capture_output=True)
            _sp.run(["git", "commit", "-m", "sandbox init", "--allow-empty"], cwd=str(project_dir), capture_output=True)
        state_file = project_dir / ".agent_state.json"
        state = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())

            except Exception:
                state = {}

        last_user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user_msg = m["content"][:200]
                break

        # 保护：恢复指令（继续/确认/短消息）不覆盖已有任务描述
        _usr_raw = ""
        for _m in reversed(messages):
            if _m["role"] == "user":
                _usr_raw = str(_m.get("content", "")).strip()
                break
        _restore_exact = ("继续", "/continue", "继续执行", "继续任务", "接着做", "继续吧")
        _is_restore = _usr_raw.lower() in _restore_exact or len(_usr_raw) <= 4
        if _is_restore and state.get("last_task"):
            last_user_msg = state["last_task"]

        state["last_task"] = last_user_msg
        state["last_time"] = datetime.now().isoformat()
        state["venv_path"] = ".venv"
        state["project_root"] = "clawsjoy_dev"

        # 自动扫描已安装的包
        venv_lib = project_dir / ".venv" / "lib"
        if venv_lib.exists():
            installed = list(state.get("installed_packages", []))
            for p in venv_lib.rglob("*.dist-info"):
                pkg = p.name.split("-")[0]
                if pkg not in installed:
                    installed.append(pkg)
            state["installed_packages"] = installed[:50]

        # 自动扫描项目结构
        core_dirs = [d.name for d in project_dir.iterdir() if d.is_dir() and not d.name.startswith(".")][:20]
        state["project_structure"] = core_dirs

        # 项目认知固化：首次探索后记录关键配置
        if "project_config" not in state:
            state["project_config"] = {
                "root_dir": "clawsjoy_dev",
                "test_dir": "tests",
                "source_dir": "agents",
                "pytest_params": {
                    "disabled_plugins": ["launch-testing-ros"],
                    "ignore_files": ["tests/test_e2e.py"],
                    "pythonpath": "",
                },
            }

        # 自动记录成功的测试命令
        known_commands = state.get("known_commands", {})
        if not isinstance(known_commands, dict):
            known_commands = {}

        # 提取成功的具体命令
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if tc["function"]["name"] == "execute_command":
                        cmd = json.loads(tc["function"]["arguments"]).get("command", "")
                        if "pytest" in cmd:
                            # 只存命令本身，不存输出
                            known_commands["pytest"] = cmd[:200]
                            break

        state["known_commands"] = known_commands

        # 记录任务执行进度
        task_progress = state.get("task_progress", {})
        task_progress["last_user_message"] = last_user_msg
        task_progress["total_rounds"] = len(messages)
        # #166 防假完成：同步路径也走 VerificationChain 验证闭环
        _vc_sync = None
        _vc_sync_fail = ""
        try:
            from core.lib.verification_chain import run_verification_chain

            try:
                _sync_kw = _task_config.get(
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
            except NameError:
                _sync_kw = [
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
                ]
            # G2: require_write 判定升级 — messages 中出现 write_file 工具调用为强信号，关键词仅作辅助信号
            _has_write_call_sync = False
            for _m_sync in messages:
                if _m_sync.get("role") == "assistant":
                    for _tc_sync in _m_sync.get("tool_calls", []):
                        if _tc_sync.get("function", {}).get("name") == "write_file":
                            _has_write_call_sync = True
                            break
            _has_write_intent_sync = _has_write_call_sync or any(k in last_user_msg for k in _sync_kw)
            try:
                # 批188 · 缺陷2 第三层之一：base_dir 必须走修好的沙箱解析器
                # （PA 线程 user_id=default 时，裸 f-string 会拼出 data/projects/default/... ⇒ 路径不存在 ⇒ 链核验假失败）
                from core.lib.gateway_helpers import _get_sandbox_base as _gsb_vc_sync

                _vc_base_sync = _gsb_vc_sync(user_id, session_id).parent
            except Exception:
                _vc_base_sync = Path("data/projects/" + str(user_id) + "/" + str(session_id))
            _vc_sync = run_verification_chain(
                task_name=last_user_msg[:80],
                session_id=session_id,
                user_id=user_id,
                messages=messages,
                task_goal=last_user_msg,
                base_dir=_vc_base_sync,
                project_root="clawsjoy_dev",
                require_write=bool(_has_write_intent_sync),
                done_when=_get_task_done_when(session_id),
            )
        except Exception as _vc_sync_err:
            print(f"[V9 sync] VerificationChain 调用异常: {_vc_sync_err}")
        # G4 第三方审计复核：VerificationChain 结果 + 审计记录交叉核对（防假完成）
        _audit_cc_sync = None
        try:
            from core.gateway.audit import cross_check_completion

            _audit_cc_sync = cross_check_completion(_vc_sync, session_id, task_start_ts=_task_start_ts, user_id=user_id)
        except Exception as _audit_cc_sync_err:
            print(f"[V9 sync] 审计复核异常(忽略): {_audit_cc_sync_err}")
        if (
            _audit_cc_sync is not None
            and not _audit_cc_sync.get("audit_passed", True)
            and _classify_task_type(messages) != "analysis"
        ):
            # 审计复核未通过 → 与验证失败同等处理：不判完成
            _audit_fail_sync = "；".join(_audit_cc_sync.get("audit_failures", []))[:400]
            _vc_sync_fail = f"审计复核未通过：{_audit_fail_sync}"
            task_progress["last_action"] = "failed"
            task_progress["verification"] = {
                "passed": False,
                "failures": _audit_cc_sync.get("audit_failures", []),
                "audit": True,
            }
            try:
                _fake_log2 = Path("data/fake_completion_log.json")
                _recs2 = []
                if _fake_log2.exists():
                    _recs2 = json.loads(_fake_log2.read_text(encoding="utf-8"))
                if not isinstance(_recs2, list):
                    _recs2 = []
                _recs2.append(
                    {
                        "time": datetime.now().isoformat(),
                        "user_id": user_id,
                        "session_id": session_id,
                        "task": last_user_msg,
                        "failures": _audit_cc_sync.get("audit_failures", []),
                        "verification_passed": False,
                        "audit_cc": True,
                    }
                )
                _fake_log2.parent.mkdir(parents=True, exist_ok=True)
                _fake_log2.write_text(json.dumps(_recs2, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as _fake_log2_err:
                print(f"[V9 sync] 审计假完成日志写入失败: {_fake_log2_err}")
        elif _vc_sync is not None and not _vc_sync.get("passed", False) and _classify_task_type(messages) != "analysis":
            # 验证未通过 → 不判完成
            _vc_sync_fail = "；".join(_vc_sync.get("failures", []))[:500]
            task_progress["last_action"] = "failed"
            task_progress["verification"] = {"passed": False, "failures": _vc_sync.get("failures", [])}
            # 审计记录：宣告完成但验证未通过 → 追加假完成日志
            try:
                _fake_log = Path("data/fake_completion_log.json")
                _records = []
                if _fake_log.exists():
                    _records = json.loads(_fake_log.read_text(encoding="utf-8"))
                if not isinstance(_records, list):
                    _records = []
                _records.append(
                    {
                        "time": datetime.now().isoformat(),
                        "user_id": user_id,
                        "session_id": session_id,
                        "task": last_user_msg,
                        "failures": _vc_sync.get("failures", []),
                        "verification_passed": False,
                    }
                )
                _fake_log.parent.mkdir(parents=True, exist_ok=True)
                _fake_log.write_text(json.dumps(_records, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[V9 sync] 假完成已记录: data/fake_completion_log.json")
            except Exception as _fake_log_err:
                print(f"[V9 sync] 假完成日志写入失败: {_fake_log_err}")
        else:
            # 验证器不可用降级路径：保留基础写入检查（对齐异步 2873-2875）
            _degraded = False
            if (
                _vc_sync is None
                and _has_write_intent_sync
                and _classify_task_type(messages) != "analysis"
                and not _check_recent_writes(messages)
                and not _has_git_diff()
            ):
                _degraded = True
                print("[V9 sync] degraded: 验证器不可用且未检测到 write_file 操作，完成判定降级为基础写入检查")
            task_progress["last_action"] = "completed"
            task_progress["verification"] = {"passed": True, "degraded": _degraded}
            # #101 G6 目标跨轮次持久：任务完成 → goal 置 complete
            try:
                from core.gateway.goal_state import complete_goal

                # 报告: 取最后一条 assistant 最终总结(可空, 兼容旧 goal 无 report)
                _sync_report = ""
                for _m_sr in reversed(messages):
                    if _m_sr.get("role") == "assistant" and str(_m_sr.get("content") or "").strip():
                        _sync_report = str(_m_sr.get("content") or "").strip()[:8000]
                        break
                # 2026-09-08 产物缺页守卫(async)
                try:
                    _ai2_in, _ai2_det = _artifact_incomplete_pages(user_id, session_id, messages)
                except Exception:
                    _ai2_in, _ai2_det = False, ""
                if _ai2_in:
                    from core.gateway.shared_state import add_steer as _st_ai2

                    try:
                        _st_ai2(session_id, "[系统] " + _ai2_det + "; 请一次性原子补写完整后再报告完成。")
                    except Exception:
                        pass
                    print("[ARTIFACT_GUARD] async %s %s" % (session_id, _ai2_det[:80]))
                else:
                    # F0.5: 契约存在 → decide_completion 唯一裁决; 完成后才 propagate complete_goal
                    try:
                        from core.gateway.task_contract import contract_for_session as _cfs_f5
                        from core.gateway.task_contract import contract_should_complete as _csc_f5
                        from core.gateway.task_contract import decide_completion as _dc_f5

                        _c_f5 = _cfs_f5(session_id)
                        if _c_f5 is not None:
                            _c_f5b, _ = _dc_f5(_c_f5, True, str(_sync_report or "")[:200])
                            if _csc_f5(_c_f5b):
                                complete_goal(user_id, session_id, report=_sync_report or None)
                            else:
                                print("[CONTRACT] async 契约未达完成, 跳过 complete_goal")
                        else:
                            complete_goal(user_id, session_id, report=_sync_report or None)
                    except Exception:
                        complete_goal(user_id, session_id, report=_sync_report or None)
            except Exception as _goal_done_err:
                print(f"[GOAL_STATE] 目标完成标记失败: {_goal_done_err}")
            # ===== 自学习评分更新：同步路径 VerificationChain 通过后写入 SAG feedback（#166 闭环）=====
            try:
                _update_sag_feedback(
                    last_user_msg[:80], session_id, user_id, messages, passed=True, verification=_vc_sync
                )
            except Exception as _fb_sync_err:
                print("[SAG_FEEDBACK] sync 调用异常: %s" % _fb_sync_err)
        # 从 messages 提取 write_file 成功的步骤
        extracted_steps = []
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if tc["function"]["name"] == "write_file":
                        args = json.loads(tc["function"]["arguments"])
                        step = {"action": "write_file", "file": args.get("path", "")}
                        if "line" in args:
                            step["line"] = args["line"]
                            step["content"] = args.get("content", "")[:100]
                        extracted_steps.append(step)
        if extracted_steps:
            task_progress["completed_steps"] = extracted_steps

        # 检测 Agent 的最终结论：如果判定"代码已处于目标状态"
        for m in reversed(messages):
            if m["role"] == "assistant" and m.get("content"):
                c = m["content"]
                if "代码已处于目标状态" in c or "未做修改" in c or "已处于目标状态" in c:
                    detail = c.split("\n")[0][:100] if "\n" in c else c[:100]
                    task_progress["completed_steps"] = [
                        {
                            "action": "verified",
                            "status": "already_correct",
                            "detail": detail,
                            "timestamp": datetime.now().isoformat(),
                        }
                    ]
                    break

        state["task_progress"] = task_progress

        # 同步 V8 task_engine 状态
        try:
            from core.lib.v8.task_engine import task_engine

            server_id = "default"
            user_tasks = task_engine.list(server_id)
            for t in user_tasks:
                if t.get("created_by") == user_id and t.get("status") == "running":
                    task_engine.transition(
                        server_id, t["id"], "done", comment=f"任务完成: {task_progress.get('total_rounds', 0)} 轮对话"
                    )
        except Exception:
            pass

        # 自动从失败命令中提取 known_issues
        current_issues = state.get("known_issues", [])
        if not isinstance(current_issues, list):
            current_issues = []
        existing_texts = {i.get("issue", "") for i in current_issues}

        for m in messages:
            if m["role"] == "tool" and m.get("content"):
                content_str = str(m.get("content", ""))
                import re as _re

                # 白名单命令失败
                if "不在白名单" in content_str:
                    match = _re.search(r"'(\w+)' 不在白名单", content_str)
                    if match:
                        cmd = match.group(1)
                        tip = f"{cmd} 命令不可用，用 python 替代"
                        if tip not in existing_texts:
                            current_issues.append({"issue": tip})
                            existing_texts.add(tip)

                # ModuleNotFoundError
                if "ModuleNotFoundError" in content_str:
                    match = _re.search(r"No module named '([^']+)'", content_str)
                    if match:
                        mod = match.group(1)
                        tip = f"缺少模块 {mod}，需 --ignore 跳过相关测试"
                        if tip not in existing_texts:
                            current_issues.append({"issue": tip})
                            existing_texts.add(tip)

                # FileNotFoundError — 路径错误
                if "FileNotFoundError" in content_str:
                    match = _re.search(r"No such file or directory: '([^']+)'", content_str)
                    if match:
                        path = match.group(1)
                        tip = f"路径不存在: {path.split('/')[-1] if '/' in path else path}，检查是否漏了 clawsjoy_dev/ 前缀"
                        if tip not in existing_texts:
                            current_issues.append({"issue": tip})
                            existing_texts.add(tip)

                # pytest 插件冲突
                if "launch_testing" in content_str and "error" in content_str.lower():
                    tip = "pytest 需加 -p no:launch-testing-ros 禁用 ROS 插件"
                    if tip not in existing_texts:
                        current_issues.append({"issue": tip})
                        existing_texts.add(tip)

                # 路径越权
                if "路径越权" in content_str:
                    tip = "路径越权，检查文件路径是否在项目目录内"
                    if tip not in existing_texts:
                        current_issues.append({"issue": tip})
                        existing_texts.add(tip)

        state["known_issues"] = current_issues[-10:]

        # 从 artifacts 自动沉淀经验
        _session_key = f"{user_id}/{session_id}"
        if _session_key in _session_artifacts:
            arts = _session_artifacts[_session_key]
            # 检测重复读取
            hash_counts = {}
            for a in arts:
                if a["type"] == "file_snapshot":
                    h = a["content_hash"]
                    hash_counts[h] = hash_counts.get(h, 0) + 1
            for h, cnt in hash_counts.items():
                if cnt > 2:
                    tip = f"同一文件被读取{cnt}次，可能无效循环"
                    if tip not in existing_texts:
                        current_issues.append({"issue": tip})
                        existing_texts.add(tip)

        # 清理本次 artifacts
        _session_artifacts.pop(_session_key, None)  # 保留最近10条
        # 提炼 known_patterns
        current_patterns = state.get("known_patterns", [])
        if not isinstance(current_patterns, list):
            current_patterns = []

        has_write = any("write_file" in str(m.get("tool_calls", "")) for m in messages if m["role"] == "assistant")
        has_test = any(
            "pytest" in str(m.get("content", "")) and "passed" in str(m.get("content", "")).lower()
            for m in messages
            if m["role"] == "tool"
        )

        if has_write and has_test:
            p = {
                "pattern": "修改源码 -> 写入 -> 测试验证",
                "trigger": "代码修改任务",
                "success": True,
                "timestamp": datetime.now().isoformat(),
            }
            if p["pattern"] not in [x.get("pattern") for x in current_patterns]:
                current_patterns.append(p)

        has_search = any("search=" in str(m.get("tool_calls", "")) for m in messages if m["role"] == "assistant")
        has_lines = any("lines_start" in str(m.get("tool_calls", "")) for m in messages if m["role"] == "assistant")

        if has_search and has_lines:
            p = {
                "pattern": "search定位 -> lines范围读取",
                "trigger": "需要定位代码时",
                "success": True,
                "timestamp": datetime.now().isoformat(),
            }
            if p["pattern"] not in [x.get("pattern") for x in current_patterns]:
                current_patterns.append(p)

        state["known_patterns"] = current_patterns[-5:]

        # 提炼 tool_preferences
        tool_prefs = state.get("tool_preferences", {})
        if not isinstance(tool_prefs, dict):
            tool_prefs = {}
        tool_counts = {}
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    name = tc["function"]["name"]
                    tool_counts[name] = tool_counts.get(name, 0) + 1
        total = sum(tool_counts.values()) or 1
        for name, count in tool_counts.items():
            tool_prefs[name] = round(count / total, 2)
        state["tool_preferences"] = tool_prefs

        # 采集 Agent 行为数据 + 更新任务状态机
        try:
            from core.lib.code_entity_extractor import extractor

            _task_name = ""
            for _m in reversed(messages):
                if _m["role"] == "user":
                    _task_name = _m["content"][:80]
                    break
            _tsm = TaskStateMachine(_task_name or "unknown", session_id, extractor)
            _last_tool_calls = next(
                (
                    m.get("tool_calls", [])
                    for m in reversed(messages)
                    if m.get("role") == "assistant" and m.get("tool_calls")
                ),
                [],
            )
            for _tc in _last_tool_calls:
                _tfn = _tc.get("function", {}).get("name", "unknown")
                _args_str = _tc.get("function", {}).get("arguments", "{}")
                try:
                    _args = json.loads(_args_str) if isinstance(_args_str, str) else _args_str
                except Exception:
                    _args = {}
                _fp = _args.get("path", _args.get("file_path", ""))
                _tsm.record_step(_tfn, _fp, "in_progress")

        except Exception as _e:
            print(f"[AGENT_ACTION] 采集失败: {_e}")

        # 更新 last_task
        for _ml in messages:
            if _ml["role"] == "user":
                state["last_task"] = _ml["content"][:200]
                state["last_time"] = datetime.now().isoformat()
                break

        state.update(meta_state or {})
        _persist_state(state, state_file)
    except Exception as e:
        pass
    # 上下文管理器
    try:
        from core.lib.context_manager import get_context

        ctx = get_context(user_id)
        if not hasattr(ctx, "_last_session_id") or ctx._last_session_id != session_id:
            ctx.clear()
            ctx._last_session_id = session_id
        ctx.add_turn(
            last_user_msg,
            f"tokens={tokens}",
            "agent_workspace",
            {},
            world_model=state.get("world_model"),
            last_task_pattern=state.get("last_task_pattern"),
            intent_model=state.get("intent_model"),
        )
    except Exception:
        pass
    # ===== 学习能力结束 =====
    return locals().get("state", {})
