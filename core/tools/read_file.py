"""read_file 工具插件（#213 + #238）

依赖全局状态通过 ctx 注入：
- ctx.messages: 消息历史
- ctx.consecutive_reads: 读取计数
- ctx.classify_task_type: 任务类型分类
- ctx.get_skeleton_by_path: 世界模型骨架查询
- ctx.is_repeat_read_attempt: 重复读取检测
- ctx.is_stale_read: 缓存过期检测
- ctx.tool_executor: 底层文件工具执行器
"""

from core.tools.base import ToolPlugin


class ReadFilePlugin(ToolPlugin):
    name = "read_file"
    quota = 10

    def execute(self, args: dict, ctx) -> dict:
        # 从 ctx 解包依赖
        messages = ctx.messages
        _consecutive_reads = ctx.consecutive_reads
        _classify_task_type = ctx.classify_task_type
        _get_skeleton_by_path = ctx.get_skeleton_by_path
        _is_repeat_read_attempt = ctx.is_repeat_read_attempt
        _is_stale_read = ctx.is_stale_read
        tool_executor = ctx.tool_executor
        base = ctx.base
        _resolve_path = ctx.resolve_path
        user_id = ctx.user_id
        session_id = ctx.session_id
        if self.name == "read_file":
            path = args.get("path", "")
            target = _resolve_path(base, path)
            # P0 沙箱路径映射: 只读回退项目根(命中标记 source=project_root; 桥接路径与 HTTP 同规)
            _read_source = "sandbox"
            if target is not None and not target.exists():
                try:
                    from core.lib.gateway_helpers import _resolve_project_root_read
                    _fb = _resolve_project_root_read(str(path), target, ctx.user_id, ctx.session_id)
                    if _fb is not None and _fb.exists():
                        target = _fb
                        _read_source = "project_root"
                except Exception:
                    pass
            func_name = args.get("function", "")
            if func_name and target and target.suffix == ".py":
                try:
                    import ast
                    content = target.read_text(encoding="utf-8")
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                            lines = content.split("\n")
                            start = node.lineno - 1
                            end = node.end_lineno if hasattr(node, 'end_lineno') else start + len(lines) - 1
                            func_content = "\n".join(lines[start:end])
                            return {
                                "success": True,
                                "function": func_name,
                                "start_line": node.lineno,
                                "end_line": node.end_lineno if hasattr(node, 'end_lineno') else start + 1,
                                "content": func_content,
                                "hint": f"函数 {func_name} 在 {path} 第 {node.lineno} 行"
                            }
                except Exception:
                    pass  # AST 解析失败，走正常 read_file 流程
            # P1: 前置拦截 — 查世界模型骨架
            _rel_path = str(target) if target else path
            _skeleton = _get_skeleton_by_path(_rel_path, user_id, session_id)
            _is_repeat = _is_repeat_read_attempt(messages, path)
            if _skeleton and not _is_repeat:
                return {
                    "success": True,
                    "cached": False,
                    "content": _skeleton,
                    "status_hint": "world_model_skeleton",
                    "hint": (
                        "以上是世界模型中的文件骨架（与磁盘文件一致）。"
                        "如果骨架信息足够完成当前任务，请直接 write_file，不需要 read_file。"
                        "如需查看完整文件内容，请再次调用 read_file。"
                    )
                }
            # P0-1: 读取硬限制
            import re as _re_limit
            _last_usr_msg = ""
            for _lm in messages:
                if _lm["role"] == "user":
                    _last_usr_msg = _lm["content"]
            _write_kw_limit = ['创建', '修改', '添加', '新增', '写入', '实现', '编写', '补充']
            _is_write_task = any(kw in _last_usr_msg for kw in _write_kw_limit)
            _max_reads = 5 if _is_write_task else 10
            # #106 C1 per-session 配额
            _cur_reads_plugin = _consecutive_reads.get(session_id, 0)
            _has_written = any(
                tc.get("function", {}).get("name") in ("write_file", "write_large", "execute_command")
                for m in messages if m["role"] == "assistant"
                for tc in m.get("tool_calls", [])
            )
            # P1 检索熔断降级：熔断前"还剩 N 次"预警（≥max-1 且未写入时）
            if _cur_reads_plugin >= _max_reads - 1 and _cur_reads_plugin < _max_reads and not _has_written and _classify_task_type(messages) != "analysis":
                result = tool_executor.execute("file_tools", {"action": "read", "path": str(target)})
                _consecutive_reads[session_id] = _consecutive_reads.get(session_id, 0) + 1
                if isinstance(result, dict):
                    result["hint"] = (
                        f"读取次数 {_consecutive_reads[session_id]}/{_max_reads}，还剩 {_max_reads - _consecutive_reads[session_id]} 次；"
                        "请尽快 write_file 写入，避免熔断。"
                    )
                return result
            if _cur_reads_plugin >= _max_reads and _classify_task_type(messages) != "analysis" and not _has_written:
                return {
                    "success": False,
                    "error": f"读取上限已达 {_max_reads} 个文件，请立即使用 write_file 写入文件。",
                    "hint": "读取配额已用完，请立即使用 write_file 或 execute_command 写入文件。"
                }
            result = tool_executor.execute("file_tools", {"action": "read", "path": str(target)})
            _consecutive_reads[session_id] = _consecutive_reads.get(session_id, 0) + 1  # #106 per-session
            from_cache = isinstance(result, dict) and result.get("cached", False)
            _fp_path = str(target) if target else ""
            if _is_stale_read(_fp_path, None, None, from_cache) and _classify_task_type(messages) != "analysis":
                if isinstance(result, dict):
                    result["success"] = False
                    result["error"] = "read_file 暂时不可用（同一位置连续 5 次缓存命中，无新信息）"
                    result["hint"] = "读取内容无变化，请立即使用 write_file 或 execute_command 写入文件，不要继续读取。"
            if isinstance(result, dict):
                result["source"] = _read_source   # P0: project_root=回退命中
            # R2(2026-08-30 架构根治): read_file 内容缓存幂等 —
            # 同 session 重复读同一路径且内容未变 → 返回 cached 标记(不再重复全量注入上下文)。
            # 文件变更(sandbox_write 写成功后 _invalidate_read_content_cache)即失效。
            try:
                import hashlib as _hl2
                _r2_fp = str(target) if target else path
                _r2_content = str(result.get("content") or result.get("stdout") or "")
                if _r2_content:
                    _r2_hash = _hl2.md5(_r2_content.encode("utf-8", "ignore")).hexdigest()
                    _r2_key = f"r2:{_r2_fp}"
                    from core.gateway.shared_state import _read_content_cache as _r2_cache
                    _r2_sess = _r2_cache.setdefault(session_id, {})
                    if _r2_sess.get(_r2_key) == _r2_hash:
                        result["cached"] = True
                        result["cached_hint"] = ("内容与上次读取一致(已缓存)。请直接基于已读取的内容推进任务，不要重复读取同一文件。")
                        # 幂等: 不再全量返回内容 — 给简短摘要, 避免重复信息膨胀上下文
                        _r2_short = _r2_content[:200]
                        result["content"] = f"[已读缓存] {path} 内容与上次读取一致({len(_r2_content)} 字符)。{_r2_short}"
                    else:
                        _r2_sess[_r2_key] = _r2_hash
            except Exception:
                pass
            return result
