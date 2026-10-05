"""v9_sandbox_write 路由 — 从 agent_gateway_enhanced.py 抽取"""

from core.lib.gateway_helpers import _get_sandbox_base, _unified_preprocess
from core.gateway.path_utils import _resolve_path, _normalize_path
from core.gateway.sag_feedback import _record_path_pattern
from core.gateway.sandbox_git import _git_status, _sandbox_git_post_write, _sandbox_git_pre_write
from core.gateway.shared_state import _consecutive_reads, _read_cache, _last_read_fingerprints, _js_rollback_count, _search_file_cache, _session_artifacts, _session_write_tracker, _content_hashes, _tracker_setdefault
from core.lib.paths import runtime_tmp_path
from core.gateway import _proc as _proc  # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import request, jsonify

logger = logging.getLogger(__name__)


def _missing(_key):
    """必填缺失 ⇒ 400 ＋ 定位（PM-011 N11：同一键 ⛔ 不许两套码；形制 `<路由>: 缺 <键>`）。"""
    _rule = request.url_rule
    return jsonify({"success": False, "error": "%s: 缺 %s" % ((_rule.rule if _rule is not None else "?").lstrip("/"), _key)}), 400

def v9_sandbox_write_handler():
    data = _unified_preprocess(request.json or {})
    user_id = data.get("user_id", "default")
    session_id = data.get("session_id", "default")
    filepath = data.get("path", "")
    base = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev")
    if ".git" in str(filepath).split("/"):
        raise ValueError("禁止操作 .git 目录")
    if not filepath:
        return _missing("path")
    target = _normalize_path(filepath, user_id, session_id)
    content = data.get("content", "")
    _stash_ref = _sandbox_git_pre_write(user_id, session_id)
    line = data.get("line", 0)  # 按行修改：指定行号
    lines_start = int(data.get("lines_start", 0) or 0)
    lines_end = int(data.get("lines_end", 0) or 0)
    # 修复模型双重转义：\n → 换行，\" → 引号
    content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
    # 长内容自动走临时文件通道，避开 JSON 转义问题
    if len(content) > 2000:
        import tempfile as _tmp, os as _os
        _tf = _tmp.NamedTemporaryFile(mode="w", suffix=".tmp", delete=False, encoding="utf-8")
        try:
            _tf.write(content)
            _tf.close()
            with open(_tf.name, "r", encoding="utf-8") as _rf:
                content = _rf.read()
        finally:
            _os.unlink(_tf.name)

    if not filepath:
        return _missing("path")
    
    # 通用路径补全：如果路径不以 clawsjoy_dev/ 开头且不存在，尝试加前缀
    if not target.exists() and not str(filepath).startswith("clawsjoy_dev/"):
        _corrected = base / filepath
        if _corrected.exists():
            target = _corrected
    if not str(target.resolve()).startswith(str(base.resolve())):
        return jsonify({"success": False, "error": "路径越权", "_project_prefix": "clawsjoy_dev/", "hint": "工具返回的路径已包含 clawsjoy_dev/ 前缀，请直接使用，不要拼接。"})

    _record_path_pattern(data.get('path', ''), str(target.relative_to(base)) if str(target).startswith(str(base)) else str(target), user_id, session_id)
    
    try:
        # 按行修改模式：支持单行和多行替换
        if lines_start > 0 and lines_end > 0 and lines_end >= lines_start:
            # 显式区间替换：用 content 替换 lines_start 到 lines_end 的行
            original = target.read_text(encoding="utf-8") if target.exists() else ""
            original_lines = original.split('\n')
            # 硬约束：>500 行文件禁止区间替换（与 line 分支硬约束一致）
            if len(original_lines) > 500:
                return jsonify({"success": False, "error": f"大文件保护：文件 {len(original_lines)} 行超过 500 行，禁止区间替换，请使用完整写入模式 (line=0)", "_project_prefix": "clawsjoy_dev/"})
            if lines_end <= len(original_lines):
                content_lines = (content or "").split('\n')
                original_lines[lines_start - 1:lines_end] = content_lines
                target.write_text('\n'.join(original_lines), encoding='utf-8')
                _consecutive_reads[session_id] = 0  # #106 per-session 重置
                _read_cache.pop(str(target.resolve()), None)
                try:
                    from core.gateway.shared_state import _invalidate_read_content_cache as _inv_r2
                    _inv_r2(session_id, str(target.resolve()))
                except Exception:
                    pass
                # #11 P1(2026-08-29): 并发锁保护 — clear 与并行读工具竞态防护
                try:
                    from core.gateway.shared_state import _get_consecutive_lock
                    with _get_consecutive_lock():
                        _last_read_fingerprints.clear()
                except Exception:
                    _last_read_fingerprints.clear()
                _js_rollback_count.pop(str(target), None)
                # 清除文件列表缓存，确保 list_dir/search_files 能立即看到新文件
                for _k in list(_search_file_cache.keys()):
                    if _k.startswith(session_id + ":"):
                        del _search_file_cache[_k]
                _trk_w = _tracker_setdefault(_session_write_tracker, session_id, lambda: {"write_count": 0, "execute_write_count": 0, "files_written": [], "_seen": set()})
                _trk_w.setdefault("_seen", set())
                _trk_w["write_count"] = _trk_w.get("write_count", 0) + 1
                return jsonify({"success": True, "path": str(target), "lines_start": lines_start, "lines_end": lines_end, "mode": "line_range_replace", "git_status": _git_status(user_id, session_id)})
            else:
                return jsonify({"success": False, "error": f"区间 {lines_start}-{lines_end} 超出文件范围 (1-{len(original_lines)})"})
        elif line > 0 and content:
            original = target.read_text(encoding="utf-8") if target.exists() else ""
            original_lines = original.split('\n')
            # 硬约束：>200 行文件禁止 line 参数 → 自动降级为全量替换
            if len(original_lines) > 500:
                line = 0  # 自动降级为全量替换
            if line <= len(original_lines):
                content_lines = content.split('\n')
                if len(content_lines) > 1:
                    # 多行替换：替换从 line 开始的 len(content_lines) 行
                    end_line = line - 1 + len(content_lines)
                    if end_line <= len(original_lines):
                        original_lines[line - 1:end_line] = content_lines
                    else:
                        original_lines[line - 1:] = content_lines
                else:
                    # 单行替换
                    original_lines[line - 1] = content
                target.write_text('\n'.join(original_lines), encoding='utf-8')
                _consecutive_reads[session_id] = 0  # #106 per-session 重置
                _read_cache.pop(str(target.resolve()), None)
                try:
                    from core.gateway.shared_state import _invalidate_read_content_cache as _inv_r2
                    _inv_r2(session_id, str(target.resolve()))
                except Exception:
                    pass
                # #11 P1(2026-08-29): 并发锁保护 — clear 与并行读工具竞态防护
                try:
                    from core.gateway.shared_state import _get_consecutive_lock
                    with _get_consecutive_lock():
                        _last_read_fingerprints.clear()
                except Exception:
                    _last_read_fingerprints.clear()
                _js_rollback_count.pop(str(target), None)
                # JS 文件写入后语法校验，失败则回滚
                if str(target).endswith('.js'):
                    import subprocess as _sp
                    _result = _proc.run_hidden(['node', '-c', str(target)], capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
                    if _result.returncode != 0:
                        target.write_text('\n'.join(original_lines), encoding='utf-8')
                        _key = str(target)
                        _js_rollback_count[_key] = _js_rollback_count.get(_key, 0) + 1
                        _count = _js_rollback_count[_key]
                        _err = _result.stderr[:200]
                        if _count >= 2:
                            return jsonify({"success": False, "error": f"write_file 已连续 {_count} 次导致 JS 语法错误并被回滚: {_err}", "hint": "write_file line 已被系统禁用。必须改用 python3 heredoc 完整写入该文件，不要再使用 write_file。", "line_mode_disabled": True})
                        else:
                            return jsonify({"success": False, "error": f"写入导致 JS 语法错误，已自动回滚: {_err}", "hint": "请改用 python3 heredoc 完整写入该文件，避免使用 write_file line 逐行修改。"})
                # 清除文件列表缓存，确保 list_dir/search_files 能立即看到新文件
                for _k in list(_search_file_cache.keys()):
                    if _k.startswith(session_id + ":"):
                        del _search_file_cache[_k]
                _trk_w = _tracker_setdefault(_session_write_tracker, session_id, lambda: {"write_count": 0, "execute_write_count": 0, "files_written": [], "_seen": set()})
                _trk_w.setdefault("_seen", set())
                _trk_w["write_count"] = _trk_w.get("write_count", 0) + 1
                return jsonify({"success": True, "path": str(target), "line": line, "mode": "line_replace", "git_status": _git_status(user_id, session_id)})
            else:
                return jsonify({"success": False, "error": f"行号 {line} 超出文件范围 (1-{len(original_lines)})"})
        
        # 完整写入模式
        if not content.strip():
            return jsonify({"success": False, "error": "content 为空，写入失败。请检查内容是否正确。"})
        if target.exists():
            original = target.read_text(encoding="utf-8")
            _orig_lines = original.split(chr(10))
            _new_lines = content.split(chr(10))
            # 保护：content 行数远少于原文件，可能丢失内容
            if len(_new_lines) < len(_orig_lines) - 5 and any(l1.strip() == l2.strip() for l1 in _new_lines for l2 in _orig_lines if l1.strip()):
                _example_line = _orig_lines[-1] if _orig_lines else "新行内容"
                return jsonify({
                    "success": False,
                    "error": f"完整写入模式下 content 只有 {len(_new_lines)} 行，原文件有 {len(_orig_lines)} 行。请改用 line 参数修改单行。",
                    "hint": f"write_file(path='{str(target)}', line=N, content='{_example_line.strip()[:80]}')"
                })
            backup = target.with_suffix(target.suffix + '.bak')
            backup.write_text(original, encoding="utf-8")
        # #98 修复：write_file 自动创建父目录（此前父目录缺失直接 ENOENT，agent 被迫绕 heredoc）
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        # 记录 artifact
        import hashlib as _hl
        _old_hash = _content_hashes.get(str(target), "")
        _new_hash = _hl.md5(content.encode()).hexdigest()
        _content_hashes[str(target)] = _new_hash
        _session_key = f"{user_id}/{session_id}"
        _artifact = {
            "id": f"write_{_session_key}_{_new_hash[:8]}",
            "type": "file_modification",
            "file": str(target.relative_to(Path(f"data/projects/{user_id}/{session_id}"))),
            "content_hash": _new_hash,
            "old_hash": _old_hash,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        if _session_key not in _session_artifacts:
            _session_artifacts[_session_key] = []
        _session_artifacts[_session_key].append(_artifact)
        _read_cache.pop(str(target.resolve()), None)
        try:
            from core.gateway.shared_state import _invalidate_read_content_cache as _inv_r2
            _inv_r2(session_id, str(target.resolve()))
        except Exception:
            pass
        _consecutive_reads[session_id] = 0  # #106 per-session 重置
        _last_read_fingerprints.clear()
        _js_rollback_count.pop(str(target), None)
        from core.gateway.execute_agent_task import _update_world_model
        _update_world_model(str(target), content, user_id, session_id)
        # SAG 全文缓存：write_file 成功后自动入库
        try:
            from core.lib.code_entity_extractor import extractor
            extractor.upsert_entity({
                "entity_type": "code_fulltext",
                "entity_name": str(target),
                "file_path": str(target),
                "signature": content[:5000]
            })
        except Exception:
            pass
        try:
            _sandbox_git_post_write(user_id, session_id, filepath, _stash_ref)
        except Exception as _git_e:
            return jsonify({"success": False, "error": str(_git_e)})
        from core.lib.code_entity_extractor import extractor; extractor._sync_code_edges(filepath, "", [])
        # 清除文件列表缓存，确保 list_dir/search_files 能立即看到新文件
        for _k in list(_search_file_cache.keys()):
            if _k.startswith(session_id + ":"):
                del _search_file_cache[_k]
        _trk_w = _tracker_setdefault(_session_write_tracker, session_id, lambda: {"write_count": 0, "execute_write_count": 0, "files_written": [], "_seen": set()})
        _trk_w.setdefault("_seen", set())
        _trk_w["write_count"] = _trk_w.get("write_count", 0) + 1
        return jsonify({"success": True, "path": str(target), "mode": "full_write", "git_status": _git_status(user_id, session_id)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})



def v9_sandbox_write_large_handler():
    """长内容写入——三层自动修复 + 降级信号"""
    import logging as _log
    data = request.json or {}
    user_id = data.get("user_id", "default")
    session_id = data.get("session_id", "default")
    filepath = data.get("path", "")
    raw = data.get("raw_arguments", "")
    content = ""
    auto_fixed = True
    fix_method = "json_parse"
    # ★ 主动 base64 通道：长内容网关直接写入，不返回给 Agent
    _pre_content = None
    try:
        _pre_args = json.loads(raw)
        _pre_content = _pre_args.get("content", "")
    except Exception:
        pass
    if not _pre_content:
        import re as _re4
        _match = _re4.search(r'"content"\s*:\s*"', raw)
        if _match:
            _start = _match.end()
            _end = _start
            while _end < len(raw):
                if raw[_end] == '"' and (_end == 0 or raw[_end-1] != '\\'):
                    _after = raw[_end+1:_end+10].lstrip()
                    if _after.startswith(',') or _after.startswith('}'):
                        break
                _end += 1
            if _end > _start:
                _pre_content = raw[_start:_end]
                _pre_content = _pre_content.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
    _is_doc = False
    try:
        import re as _re_doc
        _path_match = _re_doc.search(r'"path"\s*:\s*"([^"]+)"', raw)
        if _path_match:
            _fp = _path_match.group(1)
            _is_doc = _fp.endswith((".md", ".tsx", ".ts", ".txt", ".json", ".js", ".jsx"))
    except Exception:
        pass
    if _is_doc and _pre_content and len(_pre_content) > 2000:
        pass  # 不拒绝，写入但后续标记 truncated
    _threshold = 2000 if _is_doc else 3000
    if _pre_content and (_pre_content.count('\n') > 100 or len(_pre_content) > _threshold):
        try:
            _base = _get_sandbox_base(user_id, session_id)
            _base.mkdir(parents=True, exist_ok=True)
            _target = _resolve_path(_base, filepath)
            _target.parent.mkdir(parents=True, exist_ok=True)
            _target.write_text(_pre_content, encoding='utf-8')
            _actual = _target.read_text(encoding='utf-8')
            _ec_af = _update_world_model(str(_target), _pre_content, user_id, session_id) or 0
            _truncated = len(_actual) != len(_pre_content)
            _hint_af = f"[SAG] {_ec_af}个实体已入库" if _ec_af > 0 else ""
            return jsonify({
                "success": True,
                "auto_fixed": not _truncated,
                "hint": _hint_af,
                "fix_method": "direct_write",
                "path": str(_target),
                "size": len(_actual),
                "expected": len(_pre_content),
                "truncated": _truncated,
                "hint": "长内容已写入，请用 read_file 验证内容完整性。" if not _truncated else "写入不完整，请用 python3 heredoc 重新写入。"
            })
        except Exception as _e:
            _log.getLogger('werkzeug').exception(f'[DIRECT_WRITE_FAIL]')
            pass

    # 第一层：json.loads 直接解析
    try:
        args = json.loads(raw)
        content = args.get("content", "")
    except Exception:
        # 第二层：字符串修复 + json.loads 重试
        try:
            fixed = raw
            if fixed.count('"') % 2 != 0:
                fixed += '"'
            fixed = fixed.replace('\n', '\\n').replace('\r', '\\r')
            args = json.loads(fixed)
            content = args.get("content", "")
            fix_method = "string_fix"
        except Exception:
            # 第三层：正则提取 content + 反转义
            import re as _re
            match = _re.search(r'"content"\s*:\s*"', raw)
            if match:
                start = match.end()
                end_match = _re.search(r'"\s*}\s*$|"\s*,\s*"line"', raw[start:])
                if end_match:
                    content = raw[start:start + end_match.start()]
                    content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
                    fix_method = "regex_extract"
            # 第四层：正则盲区兜底 —— 逐字符扫描找 content 闭合引号
            if not content:
                start_marker = '"content": "'
                start_idx = raw.find(start_marker)
                if start_idx != -1:
                    start_idx += len(start_marker)
                    # 逐字符扫描：找第一个后面紧跟 , 或 } 的未转义引号
                    end_idx = start_idx
                    i = start_idx
                    while i < len(raw):
                        if raw[i] == '"' and (i == 0 or raw[i-1] != '\\'):
                            after = raw[i+1:i+10].lstrip()
                            if after.startswith(',') or after.startswith('}'):
                                end_idx = i
                                break
                        i += 1
                    if end_idx > start_idx:
                        content = raw[start_idx:end_idx]
                        content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
                        fix_method = "string_fallback"
                        content = raw[start_idx:end_idx]
                        content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
                        fix_method = "string_fallback"
    
    if not content:
        auto_fixed = False
    
    base = _get_sandbox_base(user_id, session_id)
    base.mkdir(parents=True, exist_ok=True)
    # 路径自动补全：command 中的路径缺少 clawsjoy_dev/ 前缀时，注入前缀
    _cmd = data.get("command", "")
    if "clawsjoy_dev/" not in _cmd and "/" in _cmd:
        _hint = f"cd clawsjoy_dev && {_cmd}"
        # 不修改原命令，在提示中标注
    target = _resolve_path(base, filepath)
    
    # #98 修复：write_file 自动创建父目录（此前父目录缺失直接 ENOENT，agent 被迫绕 heredoc）
    if content:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    
    import base64 as _b64
    content_b64 = None
    hint_msg = None
    if not auto_fixed:
        content_b64 = _b64.b64encode(raw.encode()).decode()
        hint_msg = (
    "[系统指令] 唯一可用的写入方式是执行以下命令，立即复制执行：\n"
    f"python3 << 'PYEOF'\n"
    "import base64\n"
    f"content = base64.b64decode('{content_b64}').decode()\n"
    f"with open('{filepath}', 'w') as f:\n"
    "    f.write(content)\n"
    "PYEOF"
)
    from core.lib.code_entity_extractor import extractor; extractor._sync_code_edges(filepath, "", [])
    return jsonify({
        "success": True,
        "auto_fixed": auto_fixed,
        "fix_method": fix_method if auto_fixed else None,
        "hint": hint_msg,
        "content_b64": content_b64,

    })

def v9_sandbox_write_begin_handler():
    """返回临时文件路径"""
    import uuid as _uuid
    data = request.json or {}
    _temp_name = f"agent_write_{_uuid.uuid4().hex[:12]}.py"
    _temp_str = runtime_tmp_path("clawsjoy_temp", _temp_name)
    _temp_path = Path(_temp_str)
    _temp_path.parent.mkdir(parents=True, exist_ok=True)
    return jsonify({"success": True, "temp_path": _temp_str})

def v9_sandbox_write_finalize_handler():
    """将临时文件移动到目标路径"""
    data = request.json or {}
    user_id = data.get("user_id", "default")
    session_id = data.get("session_id", "default")
    target_path = data.get("path", "")
    temp_path = data.get("temp_path", "")
    if not target_path:
        return _missing("path")
    if not temp_path:
        return _missing("temp_path")
    _temp = Path(temp_path)
    if not _temp.exists():
        return jsonify({"success": False, "error": f"临时文件不存在: {temp_path}"})
    base = _get_sandbox_base(user_id, session_id)
    target = _resolve_path(base, target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _temp.rename(target)
    _content = target.read_text(encoding='utf-8')
    _update_world_model(str(target), _content, user_id, session_id)
    import json as _j2
    _st = _j2.loads(Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json").read_text(encoding="utf-8")) if Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json").exists() else {}
    _ec_wf = _st.get("_last_entity_count", 0)
    _hint_wf = f"[SAG] {_ec_wf}个实体已入库" if _ec_wf > 0 else ""
    return jsonify({"success": True, "path": str(target), "size": len(_content), "hint": _hint_wf})



def register_write_routes(app):
    app.add_url_rule("/v9/sandbox/write_large", view_func=v9_sandbox_write_large_handler, methods=["POST"])
    app.add_url_rule("/v9/sandbox/write_begin", view_func=v9_sandbox_write_begin_handler, methods=["POST"])
    app.add_url_rule("/v9/sandbox/write_finalize", view_func=v9_sandbox_write_finalize_handler, methods=["POST"])
    app.add_url_rule("/v9/sandbox/write", view_func=v9_sandbox_write_handler, methods=["POST"])
