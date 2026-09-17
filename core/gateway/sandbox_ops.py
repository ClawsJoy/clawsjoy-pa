"""沙箱操作模块 — 合并 sandbox_read/search/edit/query_index/exec"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path

from flask import jsonify, request

from core.context.context_manager import _get_skeleton_by_path, _is_repeat_read_attempt_v2, _is_stale_read
from core.gateway.path_utils import _format_path_for_agent, _normalize_path
from core.gateway.quota_manager import _check_discuss_token_budget
from core.gateway.sag_feedback import _record_path_pattern
from core.gateway.sandbox_git import _git_status, _sandbox_git_post_exec
from core.gateway.shared_state import (
    _HEREDOC_MARKERS,
    _SAFE_EXEC_CMDS,
    _SANDBOX_ENV,
    ALLOWED_COMMANDS,
    _code_indexers,
    _consecutive_lists,
    _consecutive_reads,
    _intercept_cache,
    _load_v9_execution_policy,
    _query_cache,
    _read_cache,
    _resolve_v9_session_id,
    _retry_cache,
    _search_empty_cache,
    _search_empty_task,
    _search_file_cache,
    _session_failed,
    _session_git_tracker,
    _tracker_setdefault,
)
from core.lib.gateway_helpers import (
    _get_sandbox_base,
    _resolve_project_root_read,
    _unified_preprocess,
    cleanup_task_context,
)
from core.lib.sandbox_tools import _generate_project_tree
from core.lib.tool_executor import tool_executor
from core.lib.v8.ledger import ledger

logger = logging.getLogger(__name__)


def _get_v9_read_quota(task_hint: str = "") -> int:
    """P1-2 读取配额动态化：按任务类型动态调整读取上限。

    - 分析/盘点类任务 → 30 次（需大范围阅读）
    - 排查/定位类任务 → 20 次（需多文件比对定位问题）
    - 写入类任务/默认 → 10 次（写完即止，避免过度探索）
    复用 _classify_task_type + quota_manager._ANALYSIS_KEYWORDS 判定任务类型。
    """
    _hint = str(task_hint or "")
    from core.gateway.quota_manager import _ANALYSIS_KEYWORDS
    from core.lib.precision_feed import _classify_task_type

    _type = _classify_task_type(_hint)
    if _type == "troubleshooting":
        return 20
    if _type == "analysis":
        return 30
    # 兜底：quota_manager._ANALYSIS_KEYWORDS（含"盘点"等 _classify_task_type 未覆盖词）→ 30
    if any(_kw in _hint for _kw in _ANALYSIS_KEYWORDS):
        return 30
    return 10


def _with_http_tool_flow(tool_name: str):
    """#88 过滤网完整接入：HTTP 工具路由（v9_sandbox_* handler）统一记录 tool_flow。

    Agent 侧工具调用已由 _execute_sandbox_tool 上的 @_with_tool_flow 覆盖；
    独立 HTTP 路由（/v9/sandbox/*）直接执行工具，这里统一补记录，保证每个工具调用都入 SAG。
    """

    def deco(func):
        def wrapper(*args, **kwargs):
            import time as _t88

            from core.context.context_manager import record_tool_flow
            from core.gateway.audit import audit_tool_call  # G4: HTTP 工具路由同样全量审计

            _start = _t88.time()
            _data = request.json or {}
            _uid = _data.get("user_id", "guest")
            _sid = _data.get("session_id", "default")
            try:
                _resp = func(*args, **kwargs)
                _elapsed = round((_t88.time() - _start) * 1000)
                try:
                    _body = _resp.get_json() if hasattr(_resp, "get_json") else {}
                    _ok = bool(_body.get("success"))
                    if _ok:
                        _summary = f"success ({_elapsed}ms)"
                    else:
                        _summary = f"{str(_body.get('error', 'failed'))[:100]} ({_elapsed}ms)"
                    record_tool_flow(tool_name, _data, _summary, _uid, _sid)
                    audit_tool_call(tool_name, _data, _body, _uid, _sid, elapsed_ms=_elapsed)
                except Exception:
                    pass
                return _resp
            except Exception as _e:
                _elapsed = round((_t88.time() - _start) * 1000)
                try:
                    record_tool_flow(tool_name, _data, f"exception: {str(_e)[:100]} ({_elapsed}ms)", _uid, _sid)
                    audit_tool_call(
                        tool_name, _data, {"success": False, "error": str(_e)[:200]}, _uid, _sid, elapsed_ms=_elapsed
                    )
                except Exception:
                    pass
                raise

        return wrapper

    return deco


@_with_http_tool_flow("read_file")
def v9_sandbox_read_handler():
    data = request.json or {}
    user_id = data.get("user_id", "default")
    session_id = data.get("session_id", "default")
    filepath = data.get("path", "")
    # #106 C1 并发修复：per-session 配额
    _sess_rd = _consecutive_reads.get(session_id, 0)
    _sess_ls = _consecutive_lists.get(session_id, 0)
    # 新任务检测：同步重置 list 配额
    if _sess_rd == 0:
        _consecutive_lists[session_id] = 0
        _sess_ls = 0
    if not filepath:
        return jsonify({"success": False, "error": "path 必填"})
    base = _get_sandbox_base(user_id, session_id)
    base.mkdir(parents=True, exist_ok=True)
    target = _normalize_path(filepath, user_id, session_id)
    # #213 read_file 目录参数校验：path 指向目录且带 search 参数时，返回明确提示
    _search_param = data.get("search", "")
    if target.is_dir() and _search_param:
        return jsonify(
            {
                "success": False,
                "error": f"path 指向目录（{filepath}），不是具体文件。",
                "hint": "请指定具体文件路径，或去掉 search 参数用 list_dir 查看目录内容。",
                "_project_prefix": "clawsjoy_dev/",
            }
        )
    # 路径自动补全：command 中的路径缺少 clawsjoy_dev/ 前缀时，注入前缀
    _cmd = data.get("command", "")
    if "clawsjoy_dev/" not in _cmd and "/" in _cmd:
        _hint = f"cd clawsjoy_dev && {_cmd}"
    # 路径自动补全：ui/、services/、models/ 开头且不在项目子目录下时，自动补全
    _path_str = str(target)
    if not any(d in _path_str for d in ["youtube-autopilot/", "exam-prep/"]) and _path_str.startswith(
        ("ui/", "services/", "models/")
    ):
        # 从 world_model 获取项目根目录
        _state_file = base / ".agent_state.json"
        _proj_root = "youtube-autopilot"
        if _state_file.exists():
            try:
                _state = json.loads(_state_file.read_text())
                _wm = _state.get("world_model", {})
                _proj_root = _wm.get("project_root", "youtube-autopilot")
            except Exception:
                pass
        target = base / _proj_root / filepath
    # 通用路径补全：如果路径不以 clawsjoy_dev/ 开头且不存在，尝试加前缀
    if not target.exists() and not str(filepath).startswith("clawsjoy_dev/"):
        _corrected = base / filepath
        if _corrected.exists():
            target = _corrected
    # P0 沙箱路径映射: 只读回退 — 沙箱内不存在 → 回退项目根(只读白名单, 命中标记 source=project_root)
    _read_source = "sandbox"
    if not target.exists():
        from core.lib.gateway_helpers import _resolve_project_root_read

        _fb = _resolve_project_root_read(filepath, target, user_id, session_id)
        if _fb is not None and _fb.exists():
            target = _fb
            _read_source = "project_root"
    # 越权检测适配: 项目根回退是只读白名单, 不算越权; 其余仍须在沙箱内
    if _read_source != "project_root" and not str(target.resolve()).startswith(str(base.resolve())):
        from core.lib.gateway_helpers import should_auto_correct

        if should_auto_correct(session_id, "path_escape"):
            return jsonify({"success": False, "hint": "路径越权，请检查路径前缀"})

        return jsonify(
            {
                "success": False,
                "error": "路径越权",
                "_project_prefix": "clawsjoy_dev/",
                "hint": "工具返回的路径已包含 clawsjoy_dev/ 前缀，请直接使用，不要拼接。",
            }
        )

    # #213: read_file 目录参数校验：path 指向目录时禁止带 search 读取
    if os.path.isdir(target) and data.get("search"):
        return jsonify({"success": False, "error": "path 指向目录，请指定具体文件路径，或去掉 search 参数"}), 400

    _record_path_pattern(
        data.get("path", ""),
        str(target.relative_to(base)) if str(target).startswith(str(base)) else str(target),
        user_id,
        session_id,
    )

    # artifact 采集
    _session_key = f"{user_id}/{session_id}"
    _start_time = __import__("time").time()

    # P1: 前置拦截 — 查世界模型骨架（v9_sandbox_read 路由）
    _rel_path = str(target) if target else filepath
    _skeleton = _get_skeleton_by_path(_rel_path, user_id, session_id)
    _is_repeat = _is_repeat_read_attempt_v2(filepath, user_id, session_id)
    if _skeleton and not _is_repeat and not data.get("function"):
        return jsonify(
            {
                "success": True,
                "cached": False,
                "content": _skeleton,
                "status_hint": "world_model_skeleton",
                "hint": "以上是世界模型中的文件骨架（与磁盘文件一致）。如果骨架信息足够完成当前任务，请直接 write_file，不需要 read_file。如需查看完整文件内容，请再次调用 read_file。",
            }
        )

    # P0-1: 读取硬限制（v9_sandbox_read 路由）— P1-2 按任务类型动态配额
    _task_hint_v9 = str(data.get("_last_user_msg", "") or "")
    if not _task_hint_v9:
        try:
            # P2c: 从会话事件日志投影取 last user msg(替代共享单例; 跳过 [系统] 注入上下文)
            from core.gateway.session_log import get_session_log
            from core.lib.gateway_helpers import last_user_task_msg

            _msgs_v9 = get_session_log(session_id).derive_messages()
            _task_hint_v9 = last_user_task_msg(_msgs_v9)
        except Exception:
            _task_hint_v9 = ""
    _max_reads_v9 = _get_v9_read_quota(_task_hint_v9)
    # #106 C1 并发修复：per-session 配额判断
    _cur_reads_v9 = _consecutive_reads.get(session_id, 0)
    if _cur_reads_v9 >= _max_reads_v9 and not data.get("skip_quota") and not data.get("function"):
        return jsonify(
            {
                "success": False,
                "error": f"读取上限已达 {_max_reads_v9} 个文件，请立即使用 write_file 写入文件。",
                "hint": "如需详细内容请用 query_index。",
                "content": _get_skeleton_by_path(_rel_path, user_id, session_id) or "",
                "status_hint": "world_model_skeleton_fallback",
            }
        )

    # #143 放行条件：params 含 search 参数或来自 query_index 时直接放行
    # 在 #143 拦截判断之前：search 模式（read_file 带 search 关键词）与 query_index 查询不触发大文件碎片化读取拦截
    _is_search_mode_v9 = (
        bool(data.get("search") or data.get("function"))
        or data.get("query_index") is True
        or data.get("tool_name") == "query_index"
        or data.get("source") == "query_index"
    )
    if not _is_search_mode_v9:
        # #143: 大文件碎片化读取拦截（v9_sandbox_read 路由）
        # P0-1 硬限制之后、实际读取文件内容之前：文件 > 500 行且未指定 lines_start/lines_end 时禁止读取
        _lines_start_v9 = int(data.get("lines_start", 0) or 0)
        _lines_end_v9 = int(data.get("lines_end", 0) or 0)
        if _lines_start_v9 <= 0 or _lines_end_v9 <= 0:
            _large_line_count_v9 = 0
            try:
                with open(target, "r", encoding="utf-8", errors="replace") as _lf:
                    for _line_v9 in _lf:
                        _large_line_count_v9 += 1
                        if _large_line_count_v9 > 1000:
                            break
            except Exception:
                _large_line_count_v9 = 0
            if _large_line_count_v9 > 1000:
                return jsonify(
                    {
                        "success": False,
                        "error": "文件共 %d 行（>1000），禁止碎片化读取（#143）。请使用 lines_start/lines_end 指定区间读取，例如：read_file(path, lines_start=1, lines_end=500) 读取第 1-500 行。"
                        % _large_line_count_v9,
                        "hint": "大文件必须带 lines_start/lines_end 参数分区间读取，例如：read_file(path, lines_start=1, lines_end=500) 读取第 1-500 行；或用 query_index 查询结构，或基于 world_model 骨架直接 write_file。",
                        "path": str(target),
                        "lines": _large_line_count_v9,
                        "status_hint": "large_file_blocked",
                    }
                )

    # 先获取文件内容（缓存或磁盘）
    cache_key = str(target.resolve())
    content_str = _read_cache.get(cache_key)
    from_cache = content_str is not None

    # 幽灵缓存防护：文件已删除但缓存未清理时，清除缓存重新读取
    if from_cache and not target.exists():
        _read_cache.pop(cache_key, None)
        try:
            from core.gateway.shared_state import _invalidate_read_content_cache as _inv_r2b

            _inv_r2b(session_id)
        except Exception:
            pass
        content_str = None
        from_cache = False

    if not from_cache:
        if not target.exists():
            return jsonify({"success": False, "error": f"文件不存在: {filepath}"})
        result = tool_executor.execute("file_tools", {"action": "read", "path": str(target)})
        if result.get("success"):
            content_str = result.get("content", "")
            _read_cache[cache_key] = content_str
        else:
            return jsonify(result)

    lines = content_str.split("\n")
    total_lines = len(lines)

    # search 参数
    search = data.get("search", "")
    if search:
        matched = [f"{i+1:4d}|{l}" for i, l in enumerate(lines) if search.lower() in l.lower()]
        if matched:
            return jsonify(
                {
                    "success": True,
                    "content": "\n".join(matched[:200]),
                    "path": str(target),
                    "lines": total_lines,
                    "matched": len(matched),
                    "cached": from_cache,
                    "source": _read_source,
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "content": f"全文搜索完成，未找到 '{search}'。文件共 {total_lines} 行。",
                    "path": str(target),
                    "lines": total_lines,
                    "matched": 0,
                    "cached": from_cache,
                }
            )

    # function 参数：按函数名定位（AST 解析）
    function = data.get("function", "")
    if function:
        import ast

        try:
            tree = ast.parse(content_str)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
                    start = node.lineno
                    end = node.end_lineno or (start + len(node.body) + 1)
                    result_lines = lines[start - 1 : end]
                    return jsonify(
                        {
                            "success": True,
                            "function": function,
                            "start_line": start,
                            "end_line": end,
                            "content": "".join(result_lines),
                            "path": str(target),
                            "mode": "function",
                            "cached": from_cache,
                        }
                    )
            return jsonify({"success": False, "error": f"函数 {function} 未找到", "path": str(target)})
        except SyntaxError:
            return jsonify({"success": False, "error": f"文件语法错误，无法解析函数 {function}", "path": str(target)})
    # lines_start / lines_end 参数
    line_start = int(data.get("lines_start", 0) or 0)
    line_end = int(data.get("lines_end", 0) or 0)
    if line_start > 0 and line_end > 0:
        # 超大范围自动截断：范围超过 500 行时只保留最后 500 行
        line_end = min(line_end, total_lines)
        if line_end - line_start + 1 > 500:
            line_start = max(1, line_end - 500 + 1)
        selected = lines[line_start - 1 : line_end]
        numbered = "\n".join([f"{i+1:4d}|{l}" for i, l in enumerate(selected, start=line_start - 1)])
        return jsonify(
            {
                "success": True,
                "content": numbered,
                "path": str(target),
                "lines": total_lines,
                "range": f"{line_start}-{line_end}",
                "mode": "range",
                "cached": from_cache,
                "source": _read_source,
            }
        )

    # verify 参数：快速验证指定行是否匹配预期
    verify_line = int(data.get("verify_line", 0) or 0)
    verify_expected = data.get("verify_expected", "")
    if verify_line > 0 and verify_expected:
        if verify_line <= total_lines:
            actual = lines[verify_line - 1].rstrip()
            expected = verify_expected.rstrip()
            match = actual == expected
            return jsonify(
                {
                    "success": True,
                    "verify": {"line": verify_line, "match": match, "actual": actual, "expected": expected},
                    "path": str(target),
                    "total_lines": total_lines,
                    "hint": "代码已就绪，直接验证" if match else "代码与预期不符，请修改后重新验证",
                }
            )
        else:
            return jsonify({"success": False, "error": f"行号 {verify_line} 超出文件范围 (1-{total_lines})"})

    # 全文带行号
    # 超大文件自动截断：文件超过 2000 行且未指定范围时，只读取最后 500 行
    if total_lines > 2000 and line_start <= 0 and line_end <= 0:
        _tail_start_v9 = total_lines - 500 + 1
        numbered = "\n".join(
            [f"{i+1:4d}|{l}" for i, l in enumerate(lines[_tail_start_v9 - 1 :], start=_tail_start_v9 - 1)]
        )
    else:
        numbered = "\n".join([f"{i+1:4d}|{l}" for i, l in enumerate(lines)])

    # status_hint: 在 content 顶部插入提示，打断逐段读取
    # status_hint: [临时关闭 - 经验注入隔离测试]
    filepath_str = str(target)
    # 规则1: 测试文件 → 提示直接验证
    # 2026-09-13 修子串误伤：原 "test_" in filepath_str 会把 contest_a.md 等也算测试文件。
    # 改为**基名前后缀**判定（同行本来就有 endswith 的正确做法，只是前半段漏了）。
    import os as _os_tt

    _bn_tt = _os_tt.path.basename(filepath_str)
    if _bn_tt.startswith("test_") or _bn_tt.endswith("_test.py"):
        if any("def test_" in l for l in lines):
            numbered = "[系统提示] 此文件包含测试用例定义，建议使用 python3 heredoc 验证而非逐行审查。\n\n" + numbered

    # 规则2: 源码文件包含目标方法 → 提示方法已就绪（配置化规则）
    METHOD_HINTS = [
        {
            "method": "def _calculate",
            "keywords": ["expression", "result", "return"],
            "hint": "此文件的 _calculate 方法已包含表达式返回格式，建议直接验证而非逐行审查。",
        },
    ]
    for rule in METHOD_HINTS:
        if any(rule["method"] in l for l in lines):
            if all(any(kw in l for l in lines) for kw in rule["keywords"]):
                numbered = f"[系统提示] {rule['hint']}\\n\\n" + numbered
                break
    # 斜率检测：同一位置连续 5 次缓存命中 → 无效循环
    # #106 C1 并发修复：per-session 计数
    _consecutive_reads[session_id] = _consecutive_reads.get(session_id, 0) + 1
    _cur_rd = _consecutive_reads[session_id]
    _line_start = line_start if "line_start" in dir() else None
    _line_end = line_end if "line_end" in dir() else None
    if _is_stale_read(str(target), _line_start, _line_end, from_cache):
        return jsonify(
            {
                "success": False,
                "error": "read_file 暂时不可用（同一位置连续 5 次缓存命中，无新信息）",
                "hint": "读取内容无变化，请立即使用 write_file 或 execute_command 写入文件，不要继续读取。",
                "_consecutive_reads": _cur_rd,
            }
        )

    _truncated = len(numbered.split("\n")) < total_lines if total_lines > 0 else False
    return jsonify(
        {
            "success": True,
            "content": numbered,
            "path": str(target),
            "lines": total_lines,
            "mode": "full",
            "cached": from_cache,
            "truncated": _truncated,
            "source": _read_source,  # P0 沙箱路径映射: project_root=回退命中
        }
    )

    return jsonify(result)


@_with_http_tool_flow("search_files")
def v9_sandbox_search_handler():
    data = _unified_preprocess(request.json or {})
    user_id = data.get("user_id", "default")
    session_id = data.get("session_id", "default")
    # #192 空结果熔断：新任务开始（task_id 变化）时重置计数
    _task_id = data.get("task_id", "")
    if _task_id and _search_empty_task.get(session_id) != _task_id:
        _search_empty_task[session_id] = _task_id
        _search_empty_cache[session_id] = 0
    query = data.get("query", "")
    # 防死循环保护①：search_files 语义校验 —— 检测搜索词是否含函数名特征
    _q = str(query).strip()
    _func_like = (
        _q.startswith("_")
        or any(_kw in _q for _kw in ("def ", "def(", "class ", "class("))
        or (len(_q) > 10 and all(_c.isalpha() or _c == "_" for _c in _q))
    )
    if _func_like:
        return jsonify(
            {
                "success": False,
                "error": "search_files 只搜索文件名，搜索代码内容请用 read_file(path, ...)",
                "_project_prefix": "clawsjoy_dev/",
            }
        )
    dirpath = data.get("path") or "."
    base = _get_sandbox_base(user_id, session_id)
    base.mkdir(parents=True, exist_ok=True)
    # 文件列表缓存：30 秒内同一 session+dirpath 复用扫描结果
    key = f"{session_id}:{dirpath}"
    if key in _search_file_cache and time.time() - _search_file_cache[key]["ts"] < 30:
        files = _search_file_cache[key]["files"]
    else:
        # 性能优化：替代 rglob 全量递归 —— 排除大目录、限制遍历深度、超时保护、文件数上限
        _excluded_dirs = {".venv", ".git", "node_modules", "__pycache__", "data", "logs"}
        _max_depth = 5
        _max_files = 5000
        _deadline = time.time() + 3.0
        files = []
        _base_depth = len(base.parts)
        for _root, _dirs, _names in os.walk(base):
            # 1. 排除大目录（原地修改 _dirs 阻止下钻）
            _dirs[:] = [d for d in _dirs if d not in _excluded_dirs]
            # 2. 限制遍历深度：超过 max_depth 不再下钻
            if len(Path(_root).parts) - _base_depth >= _max_depth:
                _dirs[:] = []
            # 3. 超时保护 + 4. 文件数上限：达到即返回已有结果
            _entries = [str(Path(_root) / d) for d in _dirs] + [str(Path(_root) / n) for n in _names]
            for _e in _entries:
                if len(files) >= _max_files or time.time() > _deadline:
                    break
                files.append(_e)
            if len(files) >= _max_files or time.time() > _deadline:
                break
        _search_file_cache[key] = {"files": files, "ts": time.time()}
    # 路径自动补全：command 中的路径缺少 clawsjoy_dev/ 前缀时，注入前缀
    _cmd = data.get("command", "")
    if "clawsjoy_dev/" not in _cmd and "/" in _cmd:
        _hint = f"cd clawsjoy_dev && {_cmd}"
    target = _normalize_path(dirpath, user_id, session_id)
    # 通用路径补全：如果路径不以 clawsjoy_dev/ 开头且不存在，尝试加前缀
    if not target.exists() and not str(dirpath).startswith("clawsjoy_dev/"):
        _corrected = base / dirpath
        if _corrected.exists():
            target = _corrected
    # P0 沙箱路径映射: 只读回退 — 沙箱内不存在 → 回退项目根(只读白名单, source=project_root)
    _read_source = "sandbox"
    if not target.exists():
        from core.lib.gateway_helpers import _resolve_project_root_read

        _fb = _resolve_project_root_read(dirpath, target, user_id, session_id)
        if _fb is not None and _fb.exists():
            target = _fb
            _read_source = "project_root"
    # 越权检测适配: 项目根回退是只读白名单, 不算越权
    if _read_source != "project_root" and not str(target.resolve()).startswith(str(base.resolve())):
        return jsonify(
            {
                "success": False,
                "error": "路径越权",
                "_project_prefix": "clawsjoy_dev/",
                "hint": "工具返回的路径已包含 clawsjoy_dev/ 前缀，请直接使用，不要拼接。",
            }
        )

    _record_path_pattern(
        data.get("path", ""),
        str(target.relative_to(base)) if str(target).startswith(str(base)) else str(target),
        user_id,
        session_id,
    )
    if key in _search_file_cache and time.time() - _search_file_cache[key]["ts"] < 30:
        files = _search_file_cache[key]["files"]
        result = {"files": [f for f in files if query in str(f)], "dirs": []}
    else:
        result = tool_executor.execute("search_tools", {"query": query, "path": str(target)})
        _search_file_cache[key] = {"files": result.get("files", []), "ts": time.time()}
    result["_project_prefix"] = "clawsjoy_dev/"
    result["source"] = _read_source
    # 统一 files/results 列表路径格式，确保每个路径都带 clawsjoy_dev/ 前缀
    for _key in ("files", "results"):
        if isinstance(result.get(_key), list):
            result[_key] = [_format_path_for_agent(str(p)) for p in result[_key]]
    # #192 空结果熔断：连续 3 次空结果 → 熔断提示；非空结果重置计数
    _empty_hit = not (result.get("files") or result.get("results") or result.get("dirs"))
    if _empty_hit:
        _search_empty_cache[session_id] = _search_empty_cache.get(session_id, 0) + 1
        if _search_empty_cache[session_id] >= 3:
            result["_hint"] = "连续空结果，建议用 list_dir 或 read_file"
    else:
        _search_empty_cache[session_id] = 0
    return jsonify(result)


@_with_http_tool_flow("write_file")
def v9_sandbox_edit_handler():
    data = request.json or {}
    user_id = data.get("user_id", "default")
    session_id = data.get("session_id", "default")
    filepath = data.get("path", "")
    prompt = data.get("prompt", "")  # 要修改的内容前文
    suffix = data.get("suffix", "")  # 要修改的内容后文

    if not filepath:
        return jsonify({"success": False, "error": "path 必填"})

    base = _get_sandbox_base(user_id, session_id)
    base.mkdir(parents=True, exist_ok=True)
    # 路径自动补全：command 中的路径缺少 clawsjoy_dev/ 前缀时，注入前缀
    _cmd = data.get("command", "")
    if "clawsjoy_dev/" not in _cmd and "/" in _cmd:
        _hint = f"cd clawsjoy_dev && {_cmd}"
    target = _normalize_path(filepath, user_id, session_id)
    # 通用路径补全：如果路径不以 clawsjoy_dev/ 开头且不存在，尝试加前缀
    if not target.exists() and not str(filepath).startswith("clawsjoy_dev/"):
        _corrected = base / filepath
        if _corrected.exists():
            target = _corrected
    if not str(target.resolve()).startswith(str(base.resolve())):
        return jsonify(
            {
                "success": False,
                "error": "路径越权",
                "_project_prefix": "clawsjoy_dev/",
                "hint": "工具返回的路径已包含 clawsjoy_dev/ 前缀，请直接使用，不要拼接。",
            }
        )

    _record_path_pattern(
        data.get("path", ""),
        str(target.relative_to(base)) if str(target).startswith(str(base)) else str(target),
        user_id,
        session_id,
    )

    if not target.exists():
        return jsonify(
            {
                "success": False,
                "error": "文件不存在",
                "_project_prefix": "clawsjoy_dev/",
                "hint": "工具返回的路径已包含 clawsjoy_dev/ 前缀，请直接使用，不要拼接。",
            }
        )

    # 编排 Agent 多轮讨论路由
    plan_status = data.get("plan_status", "")
    current_plan = data.get("current_plan")
    if plan_status == "discussing" and current_plan:
        _agent_name = data.get("agent_name", "")
        _model = ""
        try:
            from core.lib.v8.roster_engine import roster_engine

            _member = roster_engine.get("default", _agent_name)
            if _member:
                _model = _member.get("model", "")
        except Exception:
            pass
        if _model and _model.startswith("deepseek"):
            import os as _os

            if not _os.getenv("DEEPSEEK_API_KEY"):
                _model = "ollama"
        _over, _used, _limit = _check_discuss_token_budget(user_id, data.get("server_id", "default"), _model)
        if _over:
            logger.info(f"[BUDGET] 讨论预算超限: {_used}/{_limit}")
            return jsonify(
                {
                    "plan_status": "confirmed",
                    "message": f"今日 Token 预算已超限({_used}/{_limit})，自动确认计划。",
                    "current_plan": current_plan,
                }
            )
        from core.lib.v8.task_orchestrator import orchestrator

        result = orchestrator.discuss_plan(
            user_message=messages[-1]["content"] if messages else "",
            current_plan=current_plan,
            user_id=user_id,
            server_id="default",
        )
        return jsonify(result)
    if plan_status == "confirmed" and current_plan:
        from core.gateway.execute_agent_task import _execute_agent_task

        # #31 长线任务循环：定位任务队列当前任务（running 优先/首个 pending），无队列回退随机 task_id
        _q_task = None
        try:
            from core.lib.v8.task_orchestrator import orchestrator as _orch31

            _q_task = _orch31.get_current_queue_task(user_id, session_id, current_plan)
        except Exception:
            _q_task = None
        _task_id = _q_task["id"] if _q_task else f"task_{int(time.time())}"
        _plan = current_plan
        _plan["user_id"] = user_id
        _plan["session_id"] = session_id
        if _q_task:
            # #31 队列驱动：orchestrator 统一入口（标记 _v9_mode + done/fail 回调自动取下一个）
            from core.lib.v8.task_orchestrator import orchestrator as _orch31b

            _orch31b.run_v9_queue_task(_q_task, user_id, session_id, current_plan, data.get("sub_task_id"))
        else:
            import threading as _th_plan

            _th_plan.Thread(
                target=_execute_agent_task,
                args=(
                    user_id,
                    session_id,
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
        return jsonify({"status": "executing", "task_id": _task_id, "message": "计划已确认，V9 异步执行已启动。"})

    # 统一上下文清理
    _task_name_async = ""
    for _m in messages:
        if _m["role"] == "user":
            _task_name_async = _m["content"][:80]
            break
    messages = cleanup_task_context(messages, _task_name_async, user_id, session_id)
    import threading as _th

    logger.info(
        f"[V9] thread={_th.current_thread().name}, key_in_environ={'DEEPSEEK_API_KEY' in os.environ}, key_len={len(os.environ.get('DEEPSEEK_API_KEY',''))}"
    )
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return jsonify({"success": False, "error": "未配置 API Key"})

    try:
        import requests as _r

        resp = _r.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
                "prompt": prompt,
                "suffix": suffix,
                "max_tokens": 2048,
            },
            timeout=120,
            proxies={"http": None, "https": None},
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["text"]
            # 将 FIM 结果插入到文件中
            original = target.read_text()
            # 备份原文件
            backup = target.with_suffix(target.suffix + ".bak")
            backup.write_text(original)

            # FIM 精准替换：找到 prompt 和 suffix 在原文件中的位置，只替换中间部分
            original = target.read_text()

            # 在原文件中定位 prompt 和 suffix
            # 模糊匹配：忽略每行前导空白
            def _fuzzy_find(text, pattern):
                text_lines = [l.strip() for l in text.split("\n")]
                pattern_lines = [l.strip() for l in pattern.strip().split("\n") if l.strip()]
                if not pattern_lines:
                    return -1
                for i in range(len(text_lines) - len(pattern_lines) + 1):
                    if all(text_lines[i + j] == pattern_lines[j] for j in range(len(pattern_lines))):
                        return i
                return -1

            prompt_line = _fuzzy_find(original, prompt)
            suffix_line = _fuzzy_find(original, suffix)

            if prompt_line >= 0 and suffix_line >= 0:
                start = sum(len(l) + 1 for l in original.split("\n")[:prompt_line])
                end = sum(len(l) + 1 for l in original.split("\n")[: suffix_line + 1])
                final = original[:start] + prompt + "\n" + content + "\n" + suffix + original[end:]
                target.write_text(final)
                return jsonify({"success": True, "content": content, "path": str(target)})
            else:
                return jsonify(
                    {
                        "success": False,
                        "error": "FIM match failed. Use write_file with full content.",
                        "hint": "write_file(path, full_content)",
                    }
                )
        logger.info(f"API 400 响应: {resp.text[:500]}")
        with open("logs/api_errors.log", "a") as f:
            f.write(f"{resp.text[:500]}\n")
        return jsonify({"success": False, "error": f"API错误: {resp.status_code}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 前端分别显示 — DeepSeek 余额 + GLM 余额 + 总花费(示例🔵 ¥98.50  🟣 ¥45.00  💰 ¥12.35)


@_with_http_tool_flow("query_index")
def v9_sandbox_query_index_handler():
    """查询代码索引"""
    global _code_indexers
    import re as _re
    from pathlib import Path as _Path

    data = request.json or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"success": False, "error": "query 必填"})
    _uid = data.get("user_id", "default")
    _sid = data.get("session_id", "default")
    # ===== #210 session 级失败锁定：入口检查 =====
    import time as _time_fail

    if False:
        return jsonify(
            {
                "success": False,
                "error": {
                    "message": "任务已失败，请老板介入",
                    "alternative": "请老板介入处理，或重置会话失败状态后重试",
                    "reason": "会话已触发失败锁定（#210），query_index 熔断拒绝服务",
                },
            }
        )
    _cache_key = f"{_uid}/{_sid}"
    # ===== #192 检索次数控制：会话级缓存 _query_cache = {} =====
    # 格式 {session_id: {query_sig: {count, last_result, ts}}}
    # query_sig = hash(工具, 文件, 行号范围, 结果摘要)
    # 第1次：放行并缓存；第2次：不执行查询，从缓存精准投喂 + 提示"已查过"；第3次：禁止，注入"通道关闭，请用 read_file"
    global _query_cache
    import hashlib as _hashlib
    import time as _time

    _tool = "query_index"
    _file_m = _re.search(r"([\w_]+\.py|[\w_]+_agent)", query)
    _file_part = _file_m.group(1) if _file_m else ""
    _line_m = _re.search(r"(\d+)\s*[-~]\s*(\d+)", query)
    _line_part = f"{_line_m.group(1)}-{_line_m.group(2)}" if _line_m else ""
    _kw_list = sorted(set(_re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", query.lower())))
    _summary_part = " ".join(_kw_list)
    _query_sig = _hashlib.md5(f"{_tool}|{_file_part}|{_line_part}|{_summary_part}".encode("utf-8")).hexdigest()
    _session_cache = _query_cache.setdefault(_sid, {})
    _entry = _session_cache.get(_query_sig, {"count": 0, "last_result": None, "ts": 0.0})
    _entry["count"] += 1
    _entry["ts"] = _time.time()
    _session_cache[_query_sig] = _entry
    _retry_key = _sid
    if False:
        # 第3次：自动重新注入机制 —— 清空缓存重开通道 → retry_count++ → ≤3 返回原任务+提示，>3 返回失败；新 task_id 重置 retry_count
        _task_id = data.get("task_id", "")
        _retry_entry = _retry_cache.get(_retry_key, {"task_id": _task_id, "retry_count": 0})
        if _task_id and _retry_entry.get("task_id") != _task_id:
            # 新 task_id 重置 retry_count
            _retry_entry = {"task_id": _task_id, "retry_count": 0}
        _retry_entry["retry_count"] += 1
        _retry_cache[_retry_key] = _retry_entry
        if _retry_entry["retry_count"] <= 3:
            # 清空缓存重开通道，返回原任务 + 提示（自动重新注入）
            _session_cache.pop(_query_sig, None)
            return jsonify(
                {
                    "success": True,
                    "query": query,
                    "retry": True,
                    "retry_count": _retry_entry["retry_count"],
                    "hint": "自动重新注入：已清空缓存重开通道，请重新发起检索（retry_count=%d/3）" % _retry_entry["retry_count"],
                    "keyword_results": [],
                    "sag_results": [],
                }
            )
        # >3 返回失败
        _fail_path = Path(f"data/tasks/{_sid}/FAILED.md")
        _fail_path.parent.mkdir(parents=True, exist_ok=True)
        # ===== #192 完整失败报告模板 =====
        # 已尝试方案：从 _entry/_retry_entry 提取（retry_count、hint）
        _last_agent_reply = ""
        _msgs = data.get("messages") or []
        if _msgs and isinstance(_msgs[-1], dict):
            _last_agent_reply = _msgs[-1].get("content") or _msgs[-1].get("text") or str(_msgs[-1])
        elif _msgs:
            _last_agent_reply = str(_msgs[-1])
        _fail_content = (
            f"# 任务失败报告\n"
            f"- task_id: {_sid}\n"
            f"- 失败时间: {time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
            f"- 失败步骤: query_index 检索（会话 {_sid}，第 {_entry.get('count')} 次查询触发失败通道）\n"
            f"- 错误信息: 检索循环3次重试耗尽\n"
            f"- 已尝试方案: retry_count={_retry_entry.get('retry_count')}，hint={_retry_entry.get('hint', '自动重新注入：已清空缓存重开通道，请重新发起检索')}\n"
            f"- 错误上下文: {_last_agent_reply or '（无 messages 记录）'}\n"
            f"- 建议下一步: 老板人工介入，检查 query 语法或拆分检索目标\n"
        )
        # ===== #210 session 级失败锁定：失败通道触发，写报告 + notify_boss 只执行一次 =====
        if _sid not in _session_failed:
            import time as _time_fail2

            _session_failed[_sid] = _time_fail2.time()
            _fail_path.write_text(_fail_content, encoding="utf-8")
            logger.info(f"[FAILURE_CHANNEL] 失败报告已写入 {_fail_path}")
            # ===== #192 失败通道：失败报告写入后通知老板 =====
            notify_boss(
                f"任务失败：{_sid} | 原因：检索循环3次重试耗尽 | 失败报告：{_fail_path}",
                level="error",
                extra={"task_id": _sid, "reason": "检索循环3次重试耗尽", "report_path": str(_fail_path)},
            )
        return jsonify({"success": False, "error": "任务失败：检索循环3次重试耗尽。失败报告已生成，请老板介入。", "failure_report": str(_fail_path)})
    if _entry["count"] == 2 and _entry.get("last_result"):
        # 第2次：不执行查询，从缓存精准投喂 + 提示"已查过"
        _cached = _entry["last_result"]
        return jsonify(
            {
                "success": True,
                "query": query,
                "cached": True,
                "hint": "query_index 已连续返回不相关结果。如果是搜索变量名（_write_kw、_READ_CMDS 等），这些是函数内局部变量，不在 SAG 索引中。请用：read_file('agent_gateway_enhanced.py', search='关键词') 进行文件内容搜索。",
                "keyword_results": _cached.get("keyword_results", []),
                "sag_results": _cached.get("sag_results"),
            }
        )
    _sandbox_base = _Path(f"data/projects/{_uid}/{_sid}")
    _project_dir = _sandbox_base if (_sandbox_base).exists() else _sandbox_base
    if _cache_key not in _code_indexers:
        from core.lib.code_indexer import CodeIndexer

        _code_indexers[_cache_key] = CodeIndexer(project_root=str(_project_dir))
        if not _code_indexers[_cache_key]._keyword_index:
            _code_indexers[_cache_key]._load()
    _code_indexer = _code_indexers[_cache_key]
    if not _code_indexer._keyword_index or len(_code_indexer._keyword_index) < len(_code_indexer._file_hashes):
        # 索引文件为空，自动触发扫描
        _py_files = [f for f in _project_dir.rglob("*.py") if ".venv" not in f.parts and "site-packages" not in f.parts]
        _py_files = [
            f for f in _py_files if "test_" not in f.name and "/tests/" not in str(f) and not f.name.endswith(".bak")
        ]
        for _pf in _py_files:  # #195 全量扫描，移除 [:200] 截断
            try:
                _code_indexer.index_file(str(_pf.relative_to(_project_dir)))
            except Exception:
                pass
        _code_indexer._save()
    if not _code_indexer._keyword_index:
        return jsonify({"success": False, "error": "代码索引尚未初始化，且未找到可索引的 Python 文件。"})
    # 快速路径：查询包含文件路径关键词时，直接用 AST 解析
    import re as _re
    import warnings

    warnings.filterwarnings("ignore", category=SyntaxWarning)
    file_match = _re.search(r"([\w_]+\.py|[\w_]+_agent)", query)
    if file_match:
        target = file_match.group(1)
        matches = []
        for fpath in _code_indexer._keyword_index:
            if target in fpath:
                # 优先源码文件，排除测试和备份
                priority = 0
                is_test = "test_" in fpath or "/tests/" in fpath or fpath.endswith(".bak")
                is_source = "/agents/" in fpath and not is_test
                if is_source:
                    priority = 2
                elif is_test:
                    priority = 0
                else:
                    priority = 1
                matches.append((priority, fpath))
        if matches:
            matches.sort(key=lambda x: x[0], reverse=True)
            best = matches[0][1]
            blocks = _code_indexer.parse_file(best)
            _entry["last_result"] = {
                "keyword_results": [
                    {"file": "clawsjoy_dev/" + best, "keywords": [], "match_score": 1, "blocks": blocks}
                ],
                "sag_results": None,
            }
            _entry["ts"] = _time.time()
            _session_cache[_query_sig] = _entry
            return jsonify(
                {
                    "success": True,
                    "query": query,
                    "file": "clawsjoy_dev/" + best,
                    "blocks": blocks,
                    "mode": "ast_direct",
                }
            )

    results = []
    query_lower = query.lower()
    for filepath, keywords in _code_indexer._keyword_index.items():
        match_score = 0
        for kw in keywords:
            if kw.lower() in query_lower or query_lower in kw.lower():
                match_score += 1
        if match_score > 0:
            blocks = _code_indexer.parse_file(filepath)
            results.append(
                {
                    "file": "clawsjoy_dev/" + filepath,
                    "keywords": keywords,
                    "match_score": match_score,
                    "blocks": blocks[:20],
                }
            )
    results.sort(key=lambda x: x["match_score"], reverse=True)

    # 检索去重：基于 Jaccard 相似度合并内容高度重复的文件（如备份/副本），
    # 保留 match_score 更高（排序靠前）的代表结果，避免同一代码多副本重复返回
    _dedup_results = []
    _sim_threshold = 0.7
    for _r in results:
        _dup = False
        _r_text = " ".join(_r.get("keywords", []))
        for _kept in _dedup_results:
            _kept_text = " ".join(_kept.get("keywords", []))
            if _text_similarity(_r_text, _kept_text) >= _sim_threshold:
                _dup = True
                break
        if not _dup:
            _dedup_results.append(_r)
    results = _dedup_results

    # 统一路径格式：返回给 Agent 前每个 result 的 file 字段走 _format_path_for_agent
    for _r in results:
        _r["file"] = _format_path_for_agent(_r.get("file", ""))
    # ===== 追加 code_entities 函数级实体检索（entity_name/signature ILIKE 关键词）=====
    # 返回函数级实体：name + line + file，合并进 keyword_results 按匹配度排序
    try:
        from core.lib.code_entity_extractor import searcher as _ce_searcher

        _ce_conn = _ce_searcher._pool.getconn()
        try:
            _ce_cur = _ce_conn.cursor()
            # 拆分关键词：英文单词 + 中文片段，逐词 ILIKE 匹配提升召回
            _ce_terms = []
            for _m in _re.findall(r"[\w\u4e00-\u9fff]+", query):
                _t = _m.strip()
                if len(_t) >= 2:
                    _ce_terms.append(_t)
            if not _ce_terms:
                _ce_terms = [query.strip()]
            _ce_hits = {}
            for _term in _ce_terms:
                _ce_cur.execute(
                    "SELECT entity_name, line_number, file_path FROM code_entities "
                    "WHERE project_id IN (%s, 'default') "
                    "AND entity_type IN ('function', 'method') "
                    "AND (entity_name ILIKE %s OR signature ILIKE %s) "
                    "ORDER BY entity_name LIMIT 50",
                    (_uid, f"%{_term}%", f"%{_term}%"),
                )
                for _row in _ce_cur.fetchall():
                    _ce_name, _ce_line, _ce_fpath = _row[0], _row[1], _row[2]
                    _ce_key = (_ce_name, _ce_line, _ce_fpath)
                    _ce_hits[_ce_key] = _ce_hits.get(_ce_key, 0) + 1
            _ce_cur.close()
            # 合并到 results：同一文件累积 match_score，追加 code_entities 实体列表
            for (_ce_name, _ce_line, _ce_fpath), _score in _ce_hits.items():
                _ce_file = _format_path_for_agent(_ce_fpath or "")
                if not _ce_file:
                    continue
                _target = None
                for _r in results:
                    if _r.get("file") == _ce_file:
                        _target = _r
                        break
                if _target is None:
                    _target = {"file": _ce_file, "keywords": [], "match_score": 0, "blocks": [], "code_entities": []}
                    results.append(_target)
                _target["match_score"] += _score
                _target.setdefault("code_entities", []).append({"name": _ce_name, "line": _ce_line, "file": _ce_file})
        finally:
            _ce_searcher._pool.putconn(_ce_conn)
    except Exception:
        pass
    # 合并两类结果后统一按匹配度排序
    results.sort(key=lambda x: x["match_score"], reverse=True)

    # SAG 超边并行查询（不等关键词失败，每次都查）
    _sag_result = None
    try:
        from core.lib.code_entity_extractor import searcher

        _sag_result = searcher.search_with_hyperedges(query)
    except Exception:
        pass
    # #192 缓存本次检索结果，供第 2 次精准投喂
    _entry["last_result"] = {
        "keyword_results": results[:10],
        "sag_results": _sag_result if _sag_result and _sag_result.get("primary") else None,
    }
    _entry["ts"] = _time.time()
    _session_cache[_query_sig] = _entry
    return jsonify(
        {
            "success": True,
            "query": query,
            "keyword_results": results[:10],
            "sag_results": _sag_result if _sag_result and _sag_result.get("primary") else None,
        }
    )


@_with_http_tool_flow("execute_command")
def v9_sandbox_exec_handler():
    import json as _json
    import logging as _log

    data = _unified_preprocess(request.json or {})
    if not data.get("command"):
        return jsonify({"success": False, "error": "缺少 command 参数"}), 400
    user_id = data.get("user_id", "default")
    session_id = data.get("session_id", "default")
    command = data.get("command", "")
    # P2 禁则硬约束：禁止执行 _*.py 临时/测试脚本（agent_manual §4.1，对齐桥接路径 tool_router）
    # 修复: 只拦"执行临时脚本"(python/bash/node + 临时名 + 脚本后缀), 读/引用临时文件不拦
    import re as _re_forbid

    _tmp_run_h = _re_forbid.search(
        r"(?:^|[\s;&|])(?:python3?|bash|sh|node)\s+[^\s;&|]*(?:_tmp_|_gate_|_vfy|vfy_|_fix)[^\s;&|]*\.(?:py|js|sh)\b",
        command,
    )
    if _tmp_run_h:
        return jsonify(
            {
                "success": False,
                "error": "禁止执行含「临时/测试脚本名」的脚本（_*.py 禁则，见 agent_manual §4.1）。请检查是否误用了测试文件。",
                "forbidden": True,
            }
        )

    # 剥离以 # 开头的注释行（含前导空白），避免注释内容误触发沙箱拦截
    def _strip_comment_lines(_c):
        return "\n".join(_l for _l in _c.split("\n") if not _l.strip().startswith("#"))

    _cmd_no_comments = _strip_comment_lines(command)
    # 修复 #152：heredoc 内容跳过命令黑名单
    import re as _re_heredoc

    _heredoc_match = _re_heredoc.search(r"<<\s*['\"]?(\w+)['\"]?", command)
    if _heredoc_match:
        # 架构根治(2026-08-30): heredoc 写项目文件硬禁止(与 _SYS_ESCAPE_PATTERNS 对齐, 防 API 直连绕过工具路径检查)
        try:
            from core.gateway.security import _detect_sys_escape as _esc_hd

            _esc_hit_hd = _esc_hd(_cmd_no_comments)
            if _esc_hit_hd:
                return jsonify(
                    {
                        "success": False,
                        "error": "高危命令被拦截: %s。heredoc 写项目文件禁止, 请使用 write_file(带审批与保护)。" % _esc_hit_hd[1],
                        "forbidden": True,
                    }
                )
        except Exception:
            pass
        # 安全拦截：heredoc 命令含 /home/ 绝对路径或 ../ 目录跳转时禁止执行
        _has_sandbox_rel = _re_heredoc.search(r"clawsjoy_dev/|data/projects/", command)
        # 读操作不拦: 仅当含写操作(open w/a/write/shutil)且 /home/ 或 ../ 才禁止
        _writes_he = _re_heredoc.search(
            r"open\([^)]*[\"'](?:w|a|r\+|w\+|a\+)[\"']|\bwrite\(|shutil\.(?:copy|move|rmtree)", _cmd_no_comments
        )
        if (("/home/" in _cmd_no_comments and not _has_sandbox_rel) or "../" in _cmd_no_comments) and _writes_he:
            return jsonify({"success": False, "error": "禁止在 heredoc 命令中写绝对路径(/home/)或目录跳转(../)。请在沙箱内执行命令。"})
        import subprocess as _sp_heredoc

        # 修复 heredoc 路径双重拼接：cwd 统一为 sandbox_base（不再拼 clawsjoy_dev，避免 base/clawsjoy_dev 双重拼接）
        sandbox_base = _get_sandbox_base(user_id, session_id)
        # 双重拼接检测：路径含 clawsjoy_dev/clawsjoy_dev 时报错提示
        if "clawsjoy_dev/clawsjoy_dev" in command:
            return jsonify(
                {
                    "success": False,
                    "error": "路径双重拼接：检测到 clawsjoy_dev/clawsjoy_dev。请使用相对 sandbox_base 的路径（如 clawsjoy_dev/xxx 或 ./xxx）。",
                }
            )
        # strip Agent 传入路径的已知前缀（clawsjoy_dev/、data/projects、./），归一为相对 sandbox_base 路径
        _cmd_fixed = _re_heredoc.sub(r"data/projects/[^\"'\s]+/", "", command)
        _cmd_fixed = _re_heredoc.sub(r"(?<![A-Za-z0-9_])\./", "", _cmd_fixed)
        _cmd_fixed = _re_heredoc.sub(r"(?<![A-Za-z0-9_])clawsjoy_dev/", "", _cmd_fixed)
        result = _sp_heredoc.run(
            _cmd_fixed, shell=True, capture_output=True, text=True, timeout=300, cwd=str(sandbox_base), env=_SANDBOX_ENV
        )
        return jsonify(
            {
                "success": result.returncode == 0,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
                "returncode": result.returncode,
            }
        )
    # 快速通道：python3 -c / python -c 内联 Python 同样跳过白名单检查
    _inline_py_match = _re_heredoc.match(r"^(?:python3?)\s+-c\b", command)
    if _inline_py_match:
        # 安全拦截：python3 -c 内联命令 写操作(/home/ 或 ../ + 写模式) 才禁止 — 读操作不拦
        _writes_py = _re_heredoc.search(
            r"open\([^)]*[\"'](?:w|a|r\+|w\+|a\+)[\"']|\bwrite\(|shutil\.(?:copy|move|rmtree)", _cmd_no_comments
        )
        if ("/home/" in _cmd_no_comments or "../" in _cmd_no_comments) and _writes_py:
            return jsonify({"success": False, "error": "禁止在 python3 -c 命令中写绝对路径(/home/)或目录跳转(../)。请在沙箱内执行命令。"})
        import subprocess as _sp_inline

        # cwd 统一为 sandbox_base（与 heredoc 分支一致，避免 base/clawsjoy_dev 双重拼接）
        sandbox_base = _get_sandbox_base(user_id, session_id)
        result = _sp_inline.run(
            command, shell=True, capture_output=True, text=True, timeout=300, cwd=str(sandbox_base), env=_SANDBOX_ENV
        )
        return jsonify(
            {
                "success": result.returncode == 0,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
                "returncode": result.returncode,
            }
        )
    _cmd_to_check = _cmd_no_comments
    # 继续走白名单检查（非 heredoc 命令）...

    # 沙箱安全：拦截正本 Git 操作、绝对路径、目录跳转（仅检查 PYEOF 之前部分）
    import re as _re_sandbox

    if _re_sandbox.search(r"(git.*/home/|git.*clawsjoy_v5|^/|\.\./)", _cmd_to_check):
        return jsonify(
            {
                "success": False,
                "error": "禁止操作正本仓库或使用绝对路径/目录跳转。沙箱内 Git 已自动配置，请使用 sandbox_checkpoint 或 sandbox_rollback API。",
            }
        )
    import logging as _log

    _log.getLogger("werkzeug").info(f'[EXEC_DEBUG] all keys: {list(data.keys())}, has_raw: {"raw_arguments" in data}')
    # 修复 #141：拆分管道符和 &&，逐个检查子命令
    import re as _re_sandbox
    import shlex

    _sub_commands = _cmd_to_check.replace("&&", "|").split("|")
    _all_safe = True
    for _sub in _sub_commands:
        try:
            _parts = shlex.split(_sub.strip())
        except ValueError:
            _all_safe = False
            break
        if not _parts:
            continue
        _cmd_name = _parts[0]
        if _cmd_name not in ALLOWED_COMMANDS and _cmd_name not in _SAFE_EXEC_CMDS:
            _all_safe = False
            break
        for _arg in _parts[1:]:
            if _arg.startswith("/") or ".." in _arg:
                _all_safe = False
                break
        if not _all_safe:
            break

    if not _all_safe:
        return jsonify(
            {"success": False, "error": "命令不在白名单或包含危险路径。沙箱内 Git 已自动配置，请使用 sandbox_checkpoint 或 sandbox_rollback API。"}
        )
    # P1: 如果前端传了 raw_arguments 但 command 为空，网关自己解析
    if not command and data.get("raw_arguments"):
        try:
            _args = _json.loads(data["raw_arguments"])
            command = _args.get("command", "")
        except Exception as _e:
            _log.getLogger("werkzeug").info(
                f'[EXEC_DEBUG] raw_arguments解析失败: {_e}, raw前200字符: {data["raw_arguments"][:200]}'
            )
            # 正则兜底：从损坏的 raw_arguments 中提取 command（匹配任意 heredoc 标记）
            import re as _re_exec

            _cmd_match = _re_exec.search(
                r'"command"\s*:\s*"(.+?)<<\s*\'(\w+)\'', data["raw_arguments"], _re_exec.DOTALL
            )
            if _cmd_match:
                command = _cmd_match.group(1).rstrip() + f"'{_cmd_match.group(2)}'"
                command = command.replace("\\n", "\n").replace('\\"', '"').replace("\\t", "\t")

    cmd_name = command.split()[0] if command else ""
    if not command or not cmd_name:
        logger.info(f"[HEREDOC-DETECT] command为空或cmd_name为空: cmd_name={cmd_name}, cmd[:150]={command[:150]}")
        _log.getLogger("werkzeug").info(
            f"[EXEC_DEBUG] command为空或cmd_name为空: command={repr(command[:200])}, raw_keys={list(data.keys())}"
        )
    # 读文件命令走缓存
    import re as _re

    cat_match = _re.search(r"""(?:cat|head|tail)\s+["']?([^"'\s|;]+)["']?""", command)
    py_match = _re.search(r"""open\(["']([^"']+)["']""", command)
    file_to_read = None
    if cat_match:
        file_to_read = cat_match.group(1)
    elif py_match:
        file_to_read = py_match.group(1)
    if file_to_read:
        base = _get_sandbox_base(user_id, session_id)
        # 补全路径
        if not file_to_read.startswith("clawsjoy_dev/") and not file_to_read.startswith("/"):
            file_to_read = "clawsjoy_dev/" + file_to_read
        target = base / file_to_read
        cache_key = str(target.resolve())
        if cache_key in _read_cache:
            return jsonify({"success": True, "stdout": _read_cache[cache_key], "stderr": "", "cached": True})

    read_cmds = ["cat", "head", "tail", "grep"]
    # 如果是读文件命令，提示用 read_file
    if cmd_name in read_cmds:
        # 负面缓存：120 秒内同 session 同命令不重复拦截，自动纠正
        _cache_key = f"{session_id}:{cmd_name}:read_cmd_block"
        _now = __import__("time").time()
        if _cache_key in _intercept_cache:
            if _now - _intercept_cache[_cache_key] < 120:
                return jsonify({"success": False, "hint": "read_file(path='clawsjoy_dev/xxx.py', search='关键词')"})
        _intercept_cache[_cache_key] = _now
        return jsonify(
            {
                "success": False,
                "error": f"不要用 {cmd_name} 或其他命令读文件。read_file 是唯一的读文件方式，它支持行号、行范围、关键词搜索。你需要的所有读文件功能都在 read_file 里。",
                "hint": "read_file(path='clawsjoy_dev/xxx.py', search='关键词')",
            }
        )

    if cmd_name not in ALLOWED_COMMANDS and cmd_name not in _SAFE_EXEC_CMDS:
        from core.lib.gateway_helpers import should_auto_correct

        if should_auto_correct(session_id, "unknown_command"):
            return jsonify({"success": False, "hint": "命令不在白名单，请使用替代方案"})
        return jsonify({"success": False, "error": f"命令 '{cmd_name}' 不在白名单"})

    base = _get_sandbox_base(user_id, session_id)
    base.mkdir(parents=True, exist_ok=True)
    # 路径自动补全：command 中的路径缺少 clawsjoy_dev/ 前缀时，注入前缀
    _cmd = data.get("command", "")
    if "clawsjoy_dev/" not in _cmd and "/" in _cmd:
        _hint = f"cd clawsjoy_dev && {_cmd}"
        # 不修改原命令，在提示中标注

    # 检测文件写入操作，清除对应缓存
    import re as _re2

    write_match = _re2.search(r"""(?:write|open\(.*['"]w['"]\))["']?([^"'\s|;]+)["']?""", command)
    if write_match:
        written_file = write_match.group(1)
        if not written_file.startswith("clawsjoy_dev/") and not written_file.startswith("/"):
            written_file = "clawsjoy_dev/" + written_file
        target = base / written_file
        _read_cache.pop(str(target.resolve()), None)
        try:
            from core.gateway.shared_state import _invalidate_read_content_cache as _inv_r2c

            _inv_r2c(session_id)
        except Exception:
            pass

    try:
        import subprocess

        # raw_arguments fallback: JSON 解析失败时直接从原始文本提取 command
        _raw_args = data.get("raw_arguments", "") or request.get_data(as_text=True)
        if _raw_args and not data.get("command"):
            try:
                _parsed = json.loads(_raw_args)
                data["command"] = _parsed.get("command", "")
            except Exception:
                import re as _re_raw

                _cmd_match = _re_raw.search(r'"command"\s*:\s*"(.+?)' + "'PYEOF'" + r'",', _raw_args, _re_raw.DOTALL)
                if _cmd_match:
                    _cmd_val = _cmd_match.group(1).rstrip("\n") + "\nPYEOF"
                    _cmd_val = _cmd_val.replace("\\n", "\n").replace('\\"', '"').replace("\\t", "\t")
                    data["command"] = _cmd_val
                    command = _cmd_val
        # 沙箱写入保护：拒绝修改沙箱外的文件
        import re as _re_plan

        _dangerous = False
        _is_heredoc = any(m in _strip_quoted_and_comments(command) for m in _HEREDOC_MARKERS)
        _sandbox_note_sync = None
        if _is_heredoc and ("subprocess" in command or "os.system" in command or "popen" in command.lower()):
            _sandbox_note_sync = "heredoc 内 subprocess 可执行任意命令"
        if _is_heredoc:
            import re as _re_wp

            _before_mtimes = {}
            for _wp in _re_wp.findall(r"open\([\'\"]([^\'\"]+)[\'\"]", command):
                _abs = (base / _wp).resolve()
                if not _abs.exists() and "/" not in _wp:
                    for _f in Path(base).rglob(_wp):
                        if _f.is_file():
                            _abs = _f
                            break
                if _abs.exists():
                    _before_mtimes[str(_abs)] = _abs.stat().st_mtime
            _res_h2 = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30, cwd=str(base), env=_SANDBOX_ENV
            )
            if _res_h2.returncode == 0:
                import time as _t2

                _t2.sleep(0.1)
                _modified = False
                for _wp2 in _re_wp.findall(r"open\([\'\"]([^\'\"]+)[\'\"]", command):
                    _abs2 = (base / _wp2).resolve()
                    if not _abs2.exists() and "/" not in _wp2:
                        for _f2 in Path(base).rglob(_wp2):
                            if _f2.is_file():
                                _abs2 = _f2
                                break
                    if _abs2.exists() and str(_abs2) in _before_mtimes:
                        if _abs2.stat().st_mtime > _before_mtimes[str(_abs2)]:
                            _modified = True
                        else:
                            _res_h2.stderr += f"\n[系统] {_wp2} 未被修改，请检查写入逻辑"
                if not _modified:
                    _res_h2.stderr += "\n[系统] heredoc 执行成功但目标文件未被修改。请检查：1) 是否有 f.write(content) 2) open() 路径是否正确。修正后重试，或改用 write_file。"
                import re as _re_h2

                for _p2 in _re_h2.findall(r"open\([\'\"]([^\'\"]+)[\'\"]", command):
                    _abs_h2 = (base / _p2).resolve()
                    if not _abs_h2.exists() and "/" not in _p2:
                        for _f3 in Path(base).rglob(_p2):
                            if _f3.is_file():
                                _abs_h2 = _f3
                                break
                    if _abs_h2.exists():
                        try:
                            from core.lib.code_entity_extractor import extractor

                            _ec_h2 = extractor.extract_and_upsert(str(_abs_h2)) or 0
                            if _ec_h2 > 0:
                                _res_h2.stdout += f"\n[SAG] {_ec_h2}个实体已入库"
                        except Exception:
                            pass
            if not _res_h2.returncode == 0:
                _fail_h2 = sum(
                    1
                    for m in (messages if "messages" in dir() else [])[-8:]
                    if isinstance(m, dict)
                    and m.get("role") == "tool"
                    and "heredoc" in str(m.get("content", "")).lower()
                )
                if _fail_h2 >= 3:
                    _res_h2.stderr += "\n[系统] 连续 3 次 heredoc 失败，请改用 write_file"
            if _res_h2.returncode == 0:
                _last_usr_h2 = ""
                for _mu_h2 in messages if "messages" in dir() else []:
                    if _mu_h2["role"] == "user" and len(_mu_h2.get("content", "")) > 10:
                        _last_usr_h2 = _mu_h2["content"]
                        break
                if _last_usr_h2:
                    try:
                        import psycopg2

                        _pg = psycopg2.connect("postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev")
                        _cur = _pg.cursor()
                        _cur.execute(
                            "INSERT INTO code_entities (project_id, entity_type, entity_name, file_path, status) VALUES (%s, 'task', %s, %s, 'pending') ON CONFLICT (project_id, entity_name, file_path) DO UPDATE SET status = 'pending'",
                            ("default", _last_usr_h2[:200], f"/tasks/{session_id}"),
                        )
                        _pg.commit()
                        _cur.close()
                        _pg.close()
                    except Exception:
                        pass
            _result = {
                "success": _res_h2.returncode == 0,
                "stdout": _res_h2.stdout[:2000],
                "stderr": _res_h2.stderr[:1000],
                "returncode": _res_h2.returncode,
            }
            if _sandbox_note_sync:
                _result["_sandbox_note"] = _sandbox_note_sync
            return jsonify(_result)

        # 读命令直通：跳过沙箱检查
        if _classify_command(command) == "read":
            _sb_err = _check_sandbox_read(command)
            if _sb_err:
                return jsonify({"success": False, "stdout": "", "stderr": _sb_err, "returncode": 1})
            result = subprocess.run(
                command, shell=True, cwd=str(base), env=_SANDBOX_ENV, capture_output=True, text=True, timeout=30
            )
            _resp = {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode,
            }
            if result.returncode != 0 and result.stderr and "No such file or directory" in result.stderr:
                result.stderr += "\n[hint] 工具返回的路径已包含 clawsjoy_dev/ 前缀，请直接使用，不要拼接。"
            return jsonify(_resp)

        for _kw in (">", ">>", "tee ", "dd of=", "mkfs", "mount "):
            if _kw in command and not (_kw == ">" and "2>&1" in command):
                _dangerous = True
                break
        if _dangerous:
            _cmd_paths = _re_plan.findall(r"[\w_./-]+\.\w+", command)
            _resolved_paths = []
            for _p in _cmd_paths:
                try:
                    _abs = (base / _p).resolve()
                    _resolved_paths.append(str(_abs))
                except Exception:
                    _resolved_paths.append(_p)
            _all_in_sandbox = all("clawsjoy_dev/" in p for p in _resolved_paths) if _resolved_paths else False
            if _cmd_paths and not _all_in_sandbox:
                from core.lib.gateway_helpers import should_auto_correct

                if should_auto_correct(session_id, "sandbox_write"):
                    return jsonify({"success": False, "hint": "请在沙箱内写入文件"})

                return jsonify({"success": False, "error": "禁止在沙箱外写入文件。所有修改操作必须在项目目录内进行。"})

        result = subprocess.run(
            command, shell=True, cwd=str(base), env=_SANDBOX_ENV, capture_output=True, text=True, timeout=30
        )
        _hint = None
        if result.returncode != 0 and result.stderr and "No such file or directory" in result.stderr:
            result.stderr += "\n[hint] 工具返回的路径已包含 clawsjoy_dev/ 前缀，请直接使用，不要拼接。"
            import re as _re_path_hint

            _missing = _re_path_hint.findall(r"'([^']+)'", result.stderr)
            for _fp in _missing:
                if not _fp.startswith("clawsjoy_dev/"):
                    _full = base / _fp
                    if _full.exists():
                        _hint = f"路径缺少 clawsjoy_dev/ 前缀，正确路径: clawsjoy_dev/{_fp}"
                        break
        _resp = {
            "success": result.returncode == 0,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:1000],
            "returncode": result.returncode,
        }
        if _hint:
            _resp["hint"] = _hint
        if result.returncode == 0:
            # 写入成功后自动抽取实体（不依赖 _dangerous 检测）
            # heredoc 写入后自动抽取实体
            import re as _re_wp

            _sandbox_git_post_exec(user_id, session_id, command)
            _write_paths = _re_wp.findall(r"open\([\'\"]([^\'\"]+)[\'\"]", command)
            logger.info(f"[ENTITY] 正则匹配到 {len(_write_paths)} 个路径: {_write_paths}")
            for _wp in _write_paths:
                _abs_wp = (base / _wp).resolve() if _wp.startswith("clawsjoy_dev/") else (base / _wp).resolve()
                if not _abs_wp.exists() and "/" not in _wp:
                    for _found in Path(base).rglob(_wp):
                        if _found.is_file():
                            _abs_wp = _found
                            break
                if _abs_wp.exists():
                    try:
                        from core.lib.code_entity_extractor import extractor

                        _ec = extractor.extract_and_upsert(str(_abs_wp), _abs_wp.read_text()) or 0
                    except Exception:
                        _ec = 0
        _ec = _ec if "_ec" in dir() else 0
        if _ec > 0:
            _resp["stdout"] = _resp.get("stdout", "") + f"\n[SAG] {_ec}个实体已入库，可用 query_index 检索"
        _resp["git_status"] = _git_status(user_id, session_id)
        return jsonify(_resp)
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "命令超时 (30s)"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 显式 re-export 下划线工具函数（import * 不导出 _x 开头的名字）
from core.gateway.sandbox_util import *
from core.gateway.sandbox_util import (
    _check_sandbox_read,
    _classify_command,
    _strip_quoted_and_comments,
    _text_similarity,
    notify_boss,
)

# ===== 从 agent_gateway_enhanced 归位：checkpoint / rollback / list =====


def v9_sandbox_checkpoint_handler():
    import subprocess

    data = request.json or {}
    user_id = data.get("user_id", "default")
    session_id, _auto_sid = _resolve_v9_session_id(user_id, data.get("session_id", "default"))
    message = data.get("message", "Auto checkpoint")
    base = _get_sandbox_base(user_id, session_id)
    if not (base / ".git").exists():
        return jsonify({"success": False, "error": "沙箱 Git 仓库未初始化"})
    try:
        # 批181 · 走唯一出口（只提交本次变更 + 要求仓库根=沙箱）
        from core.gateway.sandbox_git import safe_git_commit as _sgc2

        _st2 = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(base), capture_output=True, text=True, timeout=10
        )
        _files2 = [ln[3:].strip() for ln in (_st2.stdout or "").splitlines() if len(ln) > 3 and ln[3:].strip()]
        _ok2, _det2 = _sgc2(base, _files2, message, require_toplevel=base)
        if not _ok2:
            return jsonify({"success": False, "error": "拒绝提交: %s" % _det2.get("reason")})
        # git commit 成功后生成纯净变更 .patch 文件供用户审核
        patches_dir = base / "data" / "patches"
        patches_dir.mkdir(parents=True, exist_ok=True)
        r_patch = subprocess.run(
            ["git", "format-patch", "HEAD~1", "-o", str(patches_dir)],
            cwd=str(base),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r_patch.returncode != 0:
            return jsonify({"success": False, "error": r_patch.stderr.strip() or "git format-patch 失败"})
        r_hash = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(base), capture_output=True, text=True, timeout=5)
        patch_files = sorted(patches_dir.glob("*.patch")) if patches_dir.exists() else []
        return jsonify(
            {
                "success": True,
                "hash": r_hash.stdout.strip(),
                "diff": "完成",
                "patches": [p.name for p in patch_files],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def v9_sandbox_rollback_handler():
    import subprocess

    data = request.json or {}
    user_id = data.get("user_id", "default")
    session_id, _auto_sid = _resolve_v9_session_id(user_id, data.get("session_id", "default"))
    target = data.get("target", "HEAD~1")
    base = _get_sandbox_base(user_id, session_id)
    if not (base / ".git").exists():
        return jsonify({"success": False, "error": "沙箱 Git 仓库未初始化"})
    try:
        subprocess.run(["git", "reset", "--hard", target], cwd=str(base), capture_output=True, text=True, timeout=10)
        r_hash = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(base), capture_output=True, text=True, timeout=5)
        _trk = _tracker_setdefault(
            _session_git_tracker,
            session_id,
            lambda: {
                "commit_count": 0,
                "committed_files": set(),
                "file_commit_history": {},
                "rollback_count": 0,
                "last_action": "",
                "last_commit": "",
            },
        )
        _trk["rollback_count"] = _trk.get("rollback_count", 0) + 1
        _trk["last_action"] = "rollback"
        return jsonify({"success": True, "current": r_hash.stdout.strip()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def v9_sandbox_list_handler():
    import traceback

    data = _unified_preprocess(request.json or {})
    _sid_list, _auto_sid = _resolve_v9_session_id(data.get("user_id", "default"), data.get("session_id", "default"))
    # #106 C1 并发修复：per-session 配额（原模块级整数多线程串扰）
    _sess_reads = _consecutive_reads.get(_sid_list, 0)
    _sess_lists = _consecutive_lists.get(_sid_list, 0)
    # 新任务检测：如果 reads 为 0，说明是新任务，重置 list 配额
    if _sess_reads == 0:
        _consecutive_lists[_sid_list] = 0
        _sess_lists = 0
    _sess_lists += 1
    _consecutive_lists[_sid_list] = _sess_lists
    _max_lists_v9 = max(1, int((_load_v9_execution_policy().get("read_policy", {}) or {}).get("max_list_dir", 3)))
    if _sess_lists > _max_lists_v9 and not data.get("skip_quota"):
        return jsonify(
            {
                "success": False,
                "error": f"list_dir 配额已达 {_max_lists_v9} 次。请参考上下文中已注入的项目树获取目录结构。",
                "hint": "如需查找文件请用 search_files。",
                "content": _generate_project_tree(data.get("user_id", "default"), data.get("session_id", "default"))
                or "",
                "status_hint": "project_tree_fallback",
            }
        )
    user_id = data.get("user_id", "default")
    session_id, _auto_sid = _resolve_v9_session_id(user_id, data.get("session_id", "default"))
    dirpath = data.get("path") or "."
    recursive = data.get("recursive", False)
    base = _get_sandbox_base(user_id, session_id)
    base.mkdir(parents=True, exist_ok=True)
    # 路径自动补全：command 中的路径缺少 clawsjoy_dev/ 前缀时，注入前缀
    _cmd = data.get("command", "")
    if "clawsjoy_dev/" not in _cmd and "/" in _cmd:
        _hint = f"cd clawsjoy_dev && {_cmd}"
    target = _normalize_path(dirpath, user_id, session_id)
    # 通用路径补全：如果路径不以 clawsjoy_dev/ 开头且不存在，尝试加前缀
    if not target.exists() and not str(dirpath).startswith("clawsjoy_dev/"):
        _corrected = base / dirpath
        if _corrected.exists():
            target = _corrected
    # P0 沙箱路径映射: 只读回退 — 沙箱内不存在 → 回退项目根(只读白名单, source=project_root)
    _read_source = "sandbox"
    if not target.exists():
        _fb = _resolve_project_root_read(dirpath, target, user_id, session_id)
        if _fb is not None and _fb.exists():
            target = _fb
            _read_source = "project_root"
    # 越权检测适配: 项目根回退是只读白名单, 不算越权
    if _read_source != "project_root" and not str(target.resolve()).startswith(str(base.resolve())):
        return jsonify(
            {
                "success": False,
                "error": "路径越权",
                "_project_prefix": "clawsjoy_dev/",
                "hint": "工具返回的路径已包含 clawsjoy_dev/ 前缀，请直接使用，不要拼接。",
            }
        )

    _record_path_pattern(
        data.get("path", ""),
        str(target.relative_to(base)) if str(target).startswith(str(base)) else str(target),
        user_id,
        session_id,
    )
    if not target.exists():
        return jsonify(
            {
                "success": True,
                "files": [],
                "dirs": [],
                "path": str(target),
                "hint": "目录不存在，路径已包含 clawsjoy_dev/ 前缀，请直接使用",
                "_project_prefix": "clawsjoy_dev/",
                "source": _read_source,
            }
        )
    if recursive:
        files = [str(p.relative_to(base)) for p in target.rglob("*") if p.is_file()][:50]
        dirs = [p.name for p in target.rglob("*") if p.is_dir()]
    else:
        files = [p.name for p in target.iterdir() if p.is_file()][:20]
        dirs = [p.name for p in target.iterdir() if p.is_dir()]
    # dirs/files 返回相对路径（相对于沙箱工作目录），不加 clawsjoy_dev/ 前缀，避免前端拼接双重前缀
    files = list(files)
    dirs = list(dirs)
    return jsonify({"success": True, "files": files, "dirs": dirs, "path": str(target), "source": _read_source})
