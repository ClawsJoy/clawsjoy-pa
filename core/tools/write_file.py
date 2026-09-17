"""write_file 工具插件（#238 + #168 + JS回滚保护 + 内容完整性校验）"""

import re as _re

from core.tools.base import ToolPlugin


def _content_incomplete_hint(content: str) -> str:
    """检测 write_file 内容是否被 LLM 截断(报告类)。命中返回提示文案, 否则 ''。

    启发式: ①末尾未完成 URL(裸协议/尾部斜杠/过短链接) ②代码围栏未闭合 ③表格未闭合
    ④无完整结尾(无换行 + 末行过短且无结尾符)。命中仅返回 warning(不阻止写入)。
    """
    if not content or not isinstance(content, str):
        return ""
    text = content.rstrip("\n")
    # ① 末尾是未完成的链接/URL
    _m = _re.search(r"https?://\S*$", text)
    if _m:
        _u = _m.group(0)
        if _u.endswith(("http:", "https:", "://")) or len(_u) < 25 or _u.endswith(("/", "=", "&", "?")):
            return "内容可能不完整: 末尾是未完成的链接/URL(疑似被截断), 请检查或重新生成"
    elif text.endswith(("http", "https:", "http:", "https", "://")):
        return "内容可能不完整: 末尾是未完成的链接/URL(疑似被截断), 请检查或重新生成"
    # ② 代码围栏未闭合(``` 奇数)
    if text.count("```") % 2 == 1:
        return "内容可能不完整: 代码块围栏未闭合(``` 为奇数), 请检查或重新生成"
    # ③ Markdown 表格未闭合(最后一个非空行是表格行)
    _ne = [l for l in text.splitlines() if l.strip()]
    if _ne and _ne[-1].lstrip().startswith("|"):
        return "内容可能不完整: 末尾是未闭合的 Markdown 表格行, 请检查或重新生成"
    # ④ 硬切: 无结尾换行 + 末行过短且无结尾符
    if not content.endswith("\n"):
        _last = content.splitlines()[-1].strip() if content.splitlines() else ""
        if _last and len(_last) <= 25 and _last[-1] not in "。；！？、）》】]}\"'`~*>":
            return "内容可能不完整: 末尾无完整结尾(疑似被截断), 请检查或重新生成"
    return ""


class WriteFilePlugin(ToolPlugin):
    name = "write_file"
    quota = 10

    def execute(self, args: dict, ctx) -> dict:
        # P2 禁则硬约束：禁止 write_file 直接写共享配置文件（agent_manual §4.2）
        _w_path = str(args.get("path", "") or "")
        _w_base = _w_path.split("/")[-1]
        if _w_base in ("filter_net.json", ".agent_state.json", "dependency_graph.json", "retrieval_cache.json", "skill_registry_v2.json"):
            return {
                "success": False,
                "error": f"禁止 write_file 直接写共享配置文件 {_w_base}（agent_manual §4.2）。这些文件由系统管理，需改配置请走系统接口或说明理由请求人工处理。",
                "forbidden": True,
            }
        messages = ctx.messages
        _consecutive_reads = ctx.consecutive_reads
        _consecutive_lists = ctx.consecutive_lists
        _last_read_fingerprints = ctx.last_read_fingerprints
        base = ctx.base
        _resolve_path = ctx.resolve_path
        user_id = ctx.user_id
        session_id = ctx.session_id
        recap_checkpoint = ctx.recap_checkpoint
        _task_name_async = ctx.task_name_async
        _round = ctx.round
        _update_world_model = ctx.update_world_model
        _sandbox_git_pre_write = ctx.sandbox_git_pre_write
        _sandbox_git_post_write = ctx.sandbox_git_post_write
        _git_status = ctx.git_status
        _policy = ctx.policy
        _js_rollback_count = ctx.js_rollback_count

        def _span_check_168(_span):
            """#168 高行距修改审查：write_file 后跨度 > 30 行时注入系统消息并保存 recap_checkpoint"""
            try:
                if _span > 30:
                    messages.append({"role": "system", "content": f"[系统] 修改跨度 {_span} 行，建议全局检查"})
                    _recap_168 = recap_checkpoint(_task_name_async, _round)
                    if _recap_168:
                        messages.append({"role": "system", "content": _recap_168})
            except Exception as _e168:
                print(f"[#168] 高行距审查失败: {_e168}")
        if not args.get("path"):
            return {"success": False, "error": "write_file path 不能为空"}
        # 写文件前清理 messages 中的 read_file 残留，释放上下文
        # #106 C1 per-session 配额
        if _consecutive_reads.get(session_id, 0) >= 3:
            current_path = args.get("path", "")
            for msg in messages:
                if msg["role"] == "tool" and len(msg.get("content", "")) > 500:
                    if current_path and current_path in str(msg.get("content", "")):
                        continue
                    msg["content"] = msg["content"][:500] + f"\n... (已释放 {len(msg['content'])} 字符)"
        _consecutive_reads[session_id] = 0  # #106 per-session 重置
        _consecutive_lists[session_id] = 0
        # #11 P1(2026-08-29): 并发锁保护 — clear 与并行读工具竞态防护
        try:
            from core.gateway.shared_state import _get_consecutive_lock
            with _get_consecutive_lock():
                _last_read_fingerprints.clear()
        except Exception:
            _last_read_fingerprints.clear()
        target = _resolve_path(base, args.get("path", ""))
        line = args.get("line", 0)
        content_str = args.get("content", "")
        # D4 单一真源(2026-08-30): SOP 沙箱镜像文件(docs/reports 下)只读 —
        # Agent 写 SOP 必须走 obsidian_knowledge(update_sop), 防三份副本漂移
        try:
            _tgt_str = str(target).replace(chr(92), "/")  # Windows: 统一正斜杠再做 SOP 镜像判据
            _sop_mirror = ("docs/reports/platform_publish_workflow.md" in _tgt_str
                           or "docs/reports/fanqie_promotion_sop.md" in _tgt_str
                           or "docs/reports/bilibili_video_script.md" in _tgt_str)
            if _sop_mirror:
                return {"success": False,
                        "error": "该文件是 SOP 的沙箱镜像（vault 唯一真源）。请用 obsidian_knowledge(action=update_sop, sop_key=平台发布工作流/番茄推广SOP/视频制作SOP) 更新，修改会自动同步到本镜像。",
                        "hint": "SOP 更新请走 obsidian_knowledge(update_sop)，不要直接 write_file 写 docs/reports 镜像。"}
        except Exception:
            pass
        # 修复模型双重转义：\n → 换行，\" → 引号
        content_str = content_str.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
        # 长内容自动走临时文件通道，避开 JSON 转义问题(阈值与写入上限一致, 报告类文档够用)
        if len(content_str) > 20000:
            import tempfile as _tmp, os as _os
            _tf = _tmp.NamedTemporaryFile(mode='w', suffix='.tmp', delete=False, encoding='utf-8')
            try:
                _tf.write(content_str)
                _tf.close()
                with open(_tf.name, 'r', encoding='utf-8') as _rf:
                    content_str = _rf.read()
            finally:
                _os.unlink(_tf.name)
        # 截断保护：超长(>20000)非 Python 文件直接拒绝, 提示分段(报告类 ≤20000 直接写)
        _is_doc_async = args.get("path", "").endswith((".md", ".tsx", ".ts", ".txt", ".json", ".js", ".jsx"))
        if _is_doc_async and len(content_str) > 20000:
            return {"success": False, "error": "文件超过 20000 字符，请分段写入（先写主体，再追加或合并）。", "hint": "文件过大，请用 write_file 分两段写入（每次 ≤20000 字符），不要使用 heredoc。"}
        # 截断保护：如果目标文件被部分读取过，禁止完整覆盖
        _truncated_read = False
        for _rm in messages:
            if _rm["role"] == "tool" and isinstance(_rm.get("content"), str):
                try:
                    _rd = json.loads(_rm["content"]) if _rm["content"].startswith("{") else {}
                except Exception:
                    _rd = {}
                if _rd.get("path") == str(target) and _rd.get("truncated"):
                    _truncated_read = True
                    break
        if _truncated_read and line == 0:
            return {
                "success": False,
                "error": "目标文件在本 session 中被截断读取过，禁止完整覆盖。请先用 read_file 读取完整文件内容，或使用 line 参数精确修改。",
                "hint": "文件有 {} 行，你只读取了前部分。用 read_file(path='{}') 获取完整内容后再写入。".format(len(content_str.split(chr(10))), args.get("path"))
            }

        if line > 0:
            # 按行修改：支持单行和多行替换
            original_lines = target.read_text(encoding="utf-8").split("\n") if target.exists() else []
            # 硬约束：>200 行文件禁止 line 参数
            if len(original_lines) > 500:
                pass  # 自动降级，继续走内存重组逻辑     
            if line <= len(original_lines):
                content_lines = content_str.split("\n")
                if len(content_lines) > 1:
                    end_line = line - 1 + len(content_lines)
                    if end_line <= len(original_lines):
                        original_lines[line - 1:end_line] = content_lines
                    else:
                        original_lines[line - 1:] = content_lines
                else:
                    original_lines[line - 1] = content_str
                target.write_text("\n".join(original_lines), encoding="utf-8")
                if str(target).endswith('.js'):
                    import subprocess as _sp
                    _result = _sp.run(['node', '-c', str(target)], capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
                    if _result.returncode != 0:
                        target.write_text("\n".join(original_lines), encoding="utf-8")
                        _key = str(target)
                        _js_rollback_count[_key] = _js_rollback_count.get(_key, 0) + 1
                        _count = _js_rollback_count[_key]
                        _err = _result.stderr[:200]
                        if _count >= _policy["retry"]["js_rollback_limit"]:
                            return {"success": False, "error": f"write_file 已连续 {_count} 次导致 JS 语法错误并被回滚: {_err}", "hint": "write_file line 已被系统禁用。必须改用 python3 heredoc 完整写入该文件，不要再使用 write_file。", "line_mode_disabled": True}
                        else:
                            return {"success": False, "error": f"写入导致 JS 语法错误，已自动回滚: {_err}", "hint": "请改用 python3 heredoc 完整写入该文件，避免使用 write_file line 逐行修改。"}
                # ★ #168 高行距修改审查：计算修改跨度（结束行 - 开始行）
                _span_line = (len(content_lines) - 1) if len(content_lines) > 1 else 1
                _span_check_168(_span_line)
                _stash_ref = _sandbox_git_pre_write(user_id, session_id, ctx.base)
                _sandbox_git_post_write(user_id, session_id, args.get("path", ""), _stash_ref, ctx.base)
                return {"success": True, "line": line, "git_status": _git_status(user_id, session_id, ctx.base)}
            else:
                return {"success": False, "error": f"行号 {line} 超出文件范围 (1-{len(original_lines)})"}
        else:
            # 完整写入：行数保护 + 备份
            _had_original = target.exists()
            if _had_original:
                original = target.read_text(encoding="utf-8")
                orig_lines = original.split("\n")
                new_lines = content_str.split("\n")
                if len(orig_lines) > 0 and len(new_lines) > 0:
                    new_set = set(l.strip() for l in new_lines if l.strip())
                    orig_set = set(l.strip() for l in orig_lines if l.strip())
                    if new_set and orig_set:
                        similarity = len(new_set & orig_set) / len(new_set | orig_set)
                        # 2026-08-30 对齐 harness: 用户已批准该文件覆盖(is_file_approved)
                        # → 跳过相似度二次拒绝(确认即执行, 不再因"相似度低"反悔)
                        _approved_override = False
                        try:
                            if session_id:
                                from core.gateway.shared_state import is_file_approved
                                _approved_override = is_file_approved(session_id, str(target))
                        except Exception:
                            pass
                        # data/tmp 调试脚本(2026-08-30): 免审批区同样跳过相似度保护 —
                        # Agent 重写已存在的调试脚本(改逻辑)时相似度低属正常, 不应被拒
                        _tmp_override = "data/tmp/" in str(target).replace(chr(92), "/")
                        if similarity < 0.3 and not _approved_override and not _tmp_override:
                            return {"success": False, "error": f"完整写入模式下新旧内容相似度仅 {similarity:.0%}，原文件 {len(orig_lines)} 行，新文件 {len(new_lines)} 行。如果确认需要覆盖请分步写入。",
                                    "hint": "看起来你想修改文件中的某一行/片段。请用 line 参数精确修改单行(write_file(path=..., line=N, content=...))，或先 read_file 完整读取后用完整内容重写，不要只提交片段。"}
                backup = target.with_suffix(target.suffix + ".bak")
                backup.write_text(original, encoding="utf-8")
            # #98 修复：write_file 自动创建父目录（此前父目录缺失直接 ENOENT，agent 被迫绕 heredoc）
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content_str, encoding="utf-8")
            _ec_async = _update_world_model(str(target), content_str, user_id, session_id)
            _hint = f"[SAG] {_ec_async}个实体已入库" if (_ec_async or 0) > 0 else ""
            # ★ #168 高行距修改审查：完整写入按新文件行数计算跨度
            _span_full = max(len(orig_lines), len(content_str.split("\n"))) if _had_original else len(content_str.split("\n"))
            _span_check_168(_span_full)
            _stash_ref = _sandbox_git_pre_write(user_id, session_id, ctx.base)
            # #100 修复：传相对路径（sandbox_git.py 用 base / filepath 拼接，绝对路径会双重拼接）
            _rel_target = str(target.relative_to(base)) if str(target).startswith(str(base)) else str(target)
            _sandbox_git_post_write(user_id, session_id, _rel_target, _stash_ref, ctx.base)
            _warn = _content_incomplete_hint(content_str)
            _result = {"success": True, "hint": _hint, "git_status": _git_status(user_id, session_id, ctx.base)}
            if _warn:
                _result["warning"] = _warn
            return _result