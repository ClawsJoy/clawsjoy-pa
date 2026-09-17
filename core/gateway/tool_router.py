"""工具统一路由 — 从 agent_gateway_enhanced.py 抽取

包含 _execute_sandbox_tool：所有沙箱工具的统一分发入口。
"""

import logging
import subprocess
import time

from core.gateway.path_utils import _normalize_path, _resolve_path
from core.gateway.sandbox_git import _git_status, _sandbox_git_post_write, _sandbox_git_pre_write
from core.gateway.shared_state import (
    _SANDBOX_ENV,
    _code_indexer,
    _consecutive_failures,
    _consecutive_lists,
    _consecutive_reads,
    _js_rollback_count,
    _last_read_fingerprints,
    _paused_breakpoints,
    _policy,
    _query_empty_cache,
    _round,
    _search_empty_cache,
    _task_name_async,
)
from core.lib.gateway_helpers import _get_sandbox_base, recap_checkpoint
from core.lib.precision_feed import _classify_task_type
from core.lib.tool_executor import tool_executor

logger = logging.getLogger(__name__)


def _check_consecutive_failure(result, tool_name, session_id):
    """#86 连续失败自动暂停：失败计数 / 注入提示 / 强制暂停。

    - success=True  → 重置计数
    - 连续失败 >= 5 → 注入系统消息"请停止当前策略，重新审视任务目标"
    - 连续失败 >= 8 → 保存断点 + 返回强制暂停（请老板介入）
    """
    # P3: 并行工具池下多线程递增同一计数, 需互斥(写/读/改一锁完成)
    from core.gateway.shared_state import _get_consecutive_lock

    with _get_consecutive_lock():
        if result.get("success"):
            _consecutive_failures.pop(session_id, None)
            return result
        _consecutive_failures[session_id] = _consecutive_failures.get(session_id, 0) + 1
        _n = _consecutive_failures[session_id]
        if _n >= 8:
            _paused_breakpoints[session_id] = {
                "tool": tool_name,
                "count": _n,
                "at": time.time(),
                "reason": "连续失败8次，任务已暂停",
                "last_error": str(result.get("error", ""))[:200],
            }
            return {
                "success": False,
                "error": "连续失败8次，任务已暂停。请老板介入或换任务。",
                "paused": True,
                "paused_at": time.time(),
            }
        if _n >= 3:
            # 断点2: 连续失败 3 次强制换策略(原 ≥5) — steer 明确"换工具或路径"
            # P0: 提示走 steer 通道(不直接落 user_message 事件, 防破坏投影配对 → DeepSeek 400)
            try:
                from core.gateway.shared_state import add_steer

                add_steer(session_id, "当前工具连续失败，请换一个工具或路径，不要继续重复当前策略")
            except Exception:
                pass
    return result


def _with_tool_flow(func):
    """装饰器：工具执行完成后自动记录流水到 SAG（成功+失败都记录）"""
    import functools as _ft

    @_ft.wraps(func)
    def wrapper(tool_name, args, user_id, session_id, **kwargs):
        import time as _t

        from core.context.context_manager import record_tool_flow
        from core.gateway.audit import audit_tool_call  # G4: 全量审计（独立于 tool_flow）

        _start = _t.time()
        try:
            result = func(tool_name, args, user_id, session_id, **kwargs)
            _elapsed = round((_t.time() - _start) * 1000)
            _summary = result.get("success", False) and "success" or result.get("error", "failed")[:100]
            try:
                record_tool_flow(tool_name, args, f"{_summary} ({_elapsed}ms)", user_id, session_id)
            except Exception:
                pass
            # G4: 全量审计记录（成功/失败都记，第三方视角）
            try:
                audit_tool_call(tool_name, args, result, user_id, session_id, elapsed_ms=_elapsed)
            except Exception:
                pass
            # P2: 写类工具成功后刷新项目结构记忆(读工具不触发, 省开销)
            if result.get("success") and tool_name in (
                "write_file",
                "edit_file",
                "write_large",
                "create_file",
                "execute_command",
            ):
                try:
                    from core.lib.gateway_helpers import _refresh_project_structure

                    _refresh_project_structure(user_id, session_id)
                except Exception:
                    pass
            # #86 连续失败自动暂停：计数/注入/强制暂停
            return _check_consecutive_failure(result, tool_name, session_id)
        except Exception as e:
            _elapsed = round((_t.time() - _start) * 1000)
            try:
                record_tool_flow(tool_name, args, f"exception: {str(e)[:100]} ({_elapsed}ms)", user_id, session_id)
            except Exception:
                pass
            # G4: 异常也审计（失败记录，供复核窗口判断）
            try:
                audit_tool_call(
                    tool_name, args, {"success": False, "error": str(e)[:200]}, user_id, session_id, elapsed_ms=_elapsed
                )
            except Exception:
                pass
            raise

    return wrapper


class _ToolContext:
    def __init__(self, base, resolve_path):
        self.base = base
        self.resolve_path = resolve_path


# ===== P0: 工具注册表(if/elif → 查表分发的第一步) =====
# 注册表存 Plugin 类, 分发处查表; 各工具 ctx 装配仍保留分支(逐字不变, 行为零变化)。
# P1 将装配也注册化(每工具 builder fn), P2 迁入 V9Context scope。
_TOOL_REGISTRY = {}

# ===== #12 工具优先级(数值越大越紧急; 调度器抢占判定尺度) =====
# 读类/查询: 1(最低, 可被打断) | 写类/命令: 2 | 浏览器自动化/网络: 3 | 紧急通道: 4+
_TOOL_PRIORITY = {
    "read_file": 1,
    "list_dir": 1,
    "search_files": 1,
    "query_index": 1,
    "cu_learning": 2,
    "write_file": 2,
    "execute_command": 2,
    "fetch_web": 3,
    "browse_web": 3,
    "playwright_browser": 3,
    "browser_local": 3,
    "browser_hybrid": 3,
    "web_search": 3,
    "table_extract": 3,
    "wps_office": 3,
}


def _tool_priority(tool_name):
    """工具优先级(未注册默认 1)。"""
    return int(_TOOL_PRIORITY.get(tool_name, 1) or 1)


def _register_tools():
    """注册全部沙箱工具插件类(模块加载时调用一次)。"""
    from core.tools.browse_web import BrowseWebPlugin
    from core.tools.browser_hybrid import BrowserHybridPlugin  # 2026-09-04 Computer Use 混合方案
    from core.tools.browser_local import BrowserLocalPlugin
    from core.tools.cu_learning import CuLearningPlugin  # 2026-09-04 学习循环 + SOP 生成器
    from core.tools.execute_command import ExecuteCommandPlugin

    # 网络工具(只读抓取/浏览 + 浏览器自动化): fetch_web 新实现, browse_web/playwright_browser 包装已有 handler
    from core.tools.fetch_web import FetchWebPlugin
    from core.tools.file_center import FileCenterPlugin  # 2026-09-11 PA 独立核验交付物落盘
    from core.tools.file_tools import ListDirPlugin, SearchFilesPlugin
    from core.tools.lingxi import LingxiPlugin  # 2026-09-11 PA 驱动灵犀(WPS-AI)桥
    from core.tools.obsidian_knowledge import ObsidianKnowledgePlugin  # S4 单轨(原 elif 迁 handler)
    from core.tools.pa_audit import PaAuditPlugin  # 2026-09-11 PA 验收(preflight/postcheck)
    from core.tools.playwright_browser import PlaywrightBrowserPlugin
    from core.tools.query_index import QueryIndexPlugin
    from core.tools.read_file import ReadFilePlugin
    from core.tools.table_extract import TableExtractPlugin  # 2026-09-07 确定性表格提取
    from core.tools.web_search import WebSearchPlugin
    from core.tools.wps_office import WpsOfficePlugin  # 2026-09-09 WPS/office 生成入口
    from core.tools.write_file import WriteFilePlugin

    _TOOL_REGISTRY.update(
        {
            "read_file": ReadFilePlugin,
            "write_file": WriteFilePlugin,
            "list_dir": ListDirPlugin,
            "search_files": SearchFilesPlugin,
            "execute_command": ExecuteCommandPlugin,
            "query_index": QueryIndexPlugin,
            "fetch_web": FetchWebPlugin,
            "browse_web": BrowseWebPlugin,
            "playwright_browser": PlaywrightBrowserPlugin,
            "browser_local": BrowserLocalPlugin,
            "browser_hybrid": BrowserHybridPlugin,
            "cu_learning": CuLearningPlugin,
            "obsidian_knowledge": ObsidianKnowledgePlugin,
            "web_search": WebSearchPlugin,
            "table_extract": TableExtractPlugin,
            "wps_office": WpsOfficePlugin,
            "lingxi": LingxiPlugin,
            "pa_audit": PaAuditPlugin,
            "file_center": FileCenterPlugin,
        }
    )
    # P0: 注册表同步进 V9Context 容器(tool_registry 服务)
    try:
        from core.os.context import get_v9_context as _get_v9_ctx_tr

        _get_v9_ctx_tr().provide("tool_registry", _TOOL_REGISTRY)
    except Exception:
        pass  # 容器不可用时注册表仍模块级可用


_register_tools()


@_with_tool_flow
def _execute_sandbox_tool(tool_name, args, user_id, session_id, sandbox_base=None):
    """执行单个沙箱工具

    任务3: sandbox_base 可选覆盖（子任务独立沙箱）
    """
    base = sandbox_base or _get_sandbox_base(user_id, session_id)
    # P2c: messages 从会话事件日志投影(替代共享单例)
    try:
        from core.gateway.session_log import get_session_log

        messages = get_session_log(session_id).derive_messages()
    except Exception:
        messages = []
    try:
        if tool_name == "sandbox_checkpoint":
            import subprocess

            _msg = args.get("message", "Auto checkpoint")
            if not (base / ".git").exists():
                return {"success": False, "error": "沙箱 Git 仓库未初始化"}
            # 批181 · 走唯一出口（只提交本次变更 + 要求仓库根=沙箱）；不提供清单 ⇒ 拒绝提交
            from core.gateway.sandbox_git import safe_git_commit as _sgc

            _st = subprocess.run(
                ["git", "status", "--porcelain"], cwd=str(base), capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace"
            )
            _files = [ln[3:].strip() for ln in (_st.stdout or "").splitlines() if len(ln) > 3 and ln[3:].strip()]
            _ok_t, _det_t = _sgc(base, _files, _msg, require_toplevel=base)
            if not _ok_t:
                return {"success": False, "error": "拒绝提交: %s" % _det_t.get("reason")}
            _r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(base), capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace")
            return {"success": True, "hash": _r.stdout.strip()}
        elif tool_name == "sandbox_rollback":
            import subprocess

            _target = args.get("target", "HEAD~1")
            if not (base / ".git").exists():
                return {"success": False, "error": "沙箱 Git 仓库未初始化"}
            subprocess.run(
                ["git", "reset", "--hard", _target], cwd=str(base), capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace"
            )
            _r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(base), capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace")
            return {"success": True, "current": _r.stdout.strip()}
        # #12 工具优先级抢占: 每工具执行前检查更高优先级请求 → 打断当前低优工具
        try:
            from core.gateway.shared_state import drain_preempt as _dp12

            _cur_prio = _tool_priority(tool_name)
            _preempt = _dp12(session_id, current_priority=_cur_prio, current_tool=tool_name)
            if _preempt:
                _req_prio = _preempt.get("priority", 0)
                print(
                    f"[PREEMPT] 工具 {tool_name}(prio={_cur_prio}) 被更高优先级({_req_prio})抢占: "
                    f"{_preempt.get('reason', '')[:80]} requester={_preempt.get('requester', '')}"
                )
                return {
                    "success": False,
                    "error": f"被更高优先级任务抢占(prio {_req_prio}): {_preempt.get('reason', '')[:120]}",
                    "preempted": True,
                    "preempted_by_priority": _req_prio,
                    "preempted_by": _preempt.get("requester", "boss"),
                }
        except Exception as _pe12:
            print(f"[PREEMPT] 抢占检查失败(不影响执行): {_pe12}")

        # P0: 注册表查名(替代 if/elif 分发链)。未注册工具直接返回未知。
        _plugin_cls = _TOOL_REGISTRY.get(tool_name)
        if _plugin_cls is None:
            return {"success": False, "error": f"未知工具: {tool_name}"}
        if tool_name == "read_file":
            from core.context.context_manager import _get_skeleton_by_path, _is_repeat_read_attempt, _is_stale_read

            _read_ctx = _ToolContext(base, _resolve_path)
            _read_ctx.messages = messages
            _read_ctx.consecutive_reads = _consecutive_reads
            _read_ctx.classify_task_type = _classify_task_type
            _read_ctx.get_skeleton_by_path = _get_skeleton_by_path
            _read_ctx.is_repeat_read_attempt = _is_repeat_read_attempt
            _read_ctx.is_stale_read = _is_stale_read
            _read_ctx.tool_executor = tool_executor
            _read_ctx.user_id = user_id
            _read_ctx.session_id = session_id
            _result_read = _plugin_cls().execute(args, _read_ctx)
            # #106 C1：ctx 内是 dict 引用，插件已直接修改共享 dict，无需回传赋值
            return _result_read
        elif tool_name == "write_file":
            from core.gateway.execute_agent_task import _update_world_model

            _write_ctx = _ToolContext(base, _resolve_path)
            _write_ctx.messages = messages
            _write_ctx.consecutive_reads = _consecutive_reads
            _write_ctx.consecutive_lists = _consecutive_lists
            _write_ctx.last_read_fingerprints = _last_read_fingerprints
            _write_ctx.user_id = user_id
            _write_ctx.session_id = session_id
            _write_ctx.recap_checkpoint = recap_checkpoint
            _write_ctx.task_name_async = _task_name_async
            _write_ctx.round = _round
            _write_ctx.update_world_model = _update_world_model
            _write_ctx.sandbox_git_pre_write = _sandbox_git_pre_write
            _write_ctx.sandbox_git_post_write = _sandbox_git_post_write
            _write_ctx.git_status = _git_status
            _write_ctx.policy = _policy
            _write_ctx.js_rollback_count = _js_rollback_count
            return _plugin_cls().execute(args, _write_ctx)
        elif tool_name == "list_dir":
            return _plugin_cls().execute(args, _ToolContext(base, _resolve_path))
        elif tool_name == "search_files":
            _sf_ctx = _ToolContext(base, _resolve_path)
            _sf_ctx.user_id = user_id
            _sf_ctx.session_id = session_id
            _sf_ctx.search_empty_cache = _search_empty_cache  # P1 检索熔断：连续空结果计数
            return _plugin_cls().execute(args, _sf_ctx)
        elif tool_name == "execute_command":
            from core.gateway.sandbox_ops import _check_sandbox_read

            _exec_ctx = _ToolContext(base, _resolve_path)
            _exec_ctx.user_id = user_id
            _exec_ctx.session_id = session_id
            _exec_ctx.messages = messages  # P2c: 传入当前消息(替代共享单例)
            _exec_ctx.normalize_path = _normalize_path
            _exec_ctx.check_sandbox_read = _check_sandbox_read
            _exec_ctx.sandbox_env = _SANDBOX_ENV
            return _plugin_cls().execute(args, _exec_ctx)
        elif tool_name == "query_index":
            _qi_ctx = _ToolContext(base, _resolve_path)
            _qi_ctx.code_indexer = _code_indexer
            _qi_ctx.messages = messages
            _qi_ctx.user_id = user_id
            _qi_ctx.session_id = session_id
            _qi_ctx.query_empty_cache = _query_empty_cache
            return _plugin_cls().execute(args, _qi_ctx)
        elif tool_name in (
            "fetch_web",
            "browse_web",
            "playwright_browser",
            "browser_local",
            "web_search",
            "table_extract",
            "wps_office",
        ):
            # 网络/浏览器工具: 只读/抓取/浏览/搜索/本地浏览器操作, 无需沙箱文件 ctx; 传最小 ctx(user/session)
            _net_ctx = _ToolContext(base, _resolve_path)
            _net_ctx.user_id = user_id
            _net_ctx.session_id = session_id
            return _plugin_cls().execute(args, _net_ctx)
        else:
            # S1 canary 发现(2026-09-05): 注册插件但无专用 ctx 分支(cu_learning/browser_hybrid 等)
            # 原先落到函数末尾 → 返回 None → bridge/tool_flow wrapper 崩溃(NoneType)。补通用最小 ctx。
            _gen_ctx = _ToolContext(base, _resolve_path)
            _gen_ctx.user_id = user_id
            _gen_ctx.session_id = session_id
            _gen_ctx.messages = messages
            return _plugin_cls().execute(args, _gen_ctx)
        _consecutive_reads[session_id] = 0  # #106 per-session 重置
    except Exception as e:
        return {"success": False, "error": str(e)}


def _truncate_tool_result_content(content: str, limit: int = 2000) -> str:
    """#22/P0-1 + L4(2026-09-05): tool_result 进上下文前按类型策略化。

    - JSON 数组 → 「N 项(前 5 预览)」; 多行条目(列表/日志) → 行计数+首尾行;
    - 其它长内容 → 摘要 + 全文落盘 data/computer_use/out/ 并给 path;
    - 短内容原样。头尾保留避免无标记硬切(LLM 误判残缺重跑)。
    """
    txt = str(content or "")
    if len(txt) <= limit:
        return txt
    stripped = txt.strip()
    if stripped.startswith("["):
        try:
            import json as _j4

            arr = _j4.loads(stripped)
            head5 = ", ".join(str(x)[:40] for x in arr[:5])
            return "共 %d 项(前 5: %s...)[TRUNCATED] 原文 %d 字符" % (len(arr), head5, len(txt))
        except Exception:
            pass
    lines = txt.split("\n")
    if len(lines) > 12 and max(len(l) for l in lines) < 220:
        return "%d 行条目(前 6 + 后 3 行):\n%s\n...\n%s" % (len(lines), "\n".join(lines[:6]), "\n".join(lines[-3:]))
    # 通用长内容: 保留头尾各半 + 标记(基线语义), 保持上下文 ≤ limit
    half = limit // 2
    marker = "\n...[TRUNCATED] 原文 %d 字符, 已截断保留头尾各 %d 字符\n" % (len(txt), half)
    return txt[:half] + marker + txt[-half:]


def _filter_tools_by_mode(tools, session_id, messages=None):
    """按当前模式白名单过滤 tools schema — LLM 根本看不到不可用工具(不再试错)。

    minimal → 只给 minimal 白名单里的工具; full → 全部。
    核心工具(read_file/write_file/execute_command)兜底保留 — 写审批依赖 write_file schema。
    """
    try:
        from core.gateway.quota_manager import get_mode, get_mode_tools
        from core.lib.gateway_helpers import last_user_task_msg

        _hint = last_user_task_msg(messages or [])
        _mode = get_mode(session_id, _hint)
        _allowed = set(get_mode_tools(session_id, _hint))
        if not _allowed:
            return tools
        _filtered = [t for t in (tools or []) if t.get("function", {}).get("name") in _allowed]
        # 核心工具兜底(模式配置意外缺项时写审批/基本操作不受影响)
        for _core in ("write_file", "read_file", "execute_command"):
            if not any(t.get("function", {}).get("name") == _core for t in _filtered):
                _src = next((t for t in (tools or []) if t.get("function", {}).get("name") == _core), None)
                if _src:
                    _filtered.append(_src)
        if len(_filtered) != len(tools or []):
            _removed = sorted(
                {t.get("function", {}).get("name", "") for t in (tools or [])}
                - {t.get("function", {}).get("name", "") for t in _filtered}
            )
            print(f"[TOOLS_FILTER] 模式 {_mode} 隐藏不可用工具: {_removed}")
        return _filtered
    except Exception:
        return tools
