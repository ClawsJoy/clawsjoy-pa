"""execute_command 工具插件（#238 + 沙箱安全检查）"""

import os
import subprocess
from core.gateway.sandbox_git import _git_status, _sandbox_git_post_exec
from core.gateway.shared_state import _HEREDOC_MARKERS, _policy, _session_write_tracker, _strip_quoted_and_comments, _tracker_setdefault, _load_v9_execution_policy
from core.tools.base import ToolPlugin

# #3 Code Runtime 隔离: 命令输出大小限制(防爆上下文; 截断只影响回传, 不落盘原始输出)
_CMD_STDOUT_LIMIT = 8000
_CMD_STDERR_LIMIT = 4000


def _truncate_cmd_output(text, limit):
    """命令输出超限截断: 保留头尾各半 + [TRUNCATED] 标记(与 P0-1 tool_result 截断同风格)。"""
    text = str(text or "")
    if len(text) <= limit:
        return text
    half = limit // 2
    return (text[:half]
            + f"\n...[TRUNCATED] 原文 {len(text)} 字符, 超限 {limit}, 已截断保留头尾各 {half} 字符\n"
            + text[-half:])


class ExecuteCommandPlugin(ToolPlugin):
    name = "execute_command"
    quota = 10

    def execute(self, args: dict, ctx) -> dict:
        # P2c: messages 从 ctx 取(替代共享单例), 无则空列表
        messages = getattr(ctx, "messages", [])
        base = ctx.base
        user_id = ctx.user_id
        session_id = ctx.session_id
        _normalize_path = ctx.normalize_path
        _check_sandbox_read = ctx.check_sandbox_read
        _SANDBOX_ENV = ctx.sandbox_env

        cmd = args.get("command", "")
        _sb_err = _check_sandbox_read(cmd)
        if _sb_err:
            return {"success": False, "stdout": "", "stderr": _sb_err, "returncode": 1}
        # 2026-09-06 项目级脚本注入: 首次 execute_command 时把项目 scripts/pipelines/ 注入沙箱
        # (确定性流水线脚本跨 session 复用 — 放 vault 需 read→write→exec 三步且反复越权,
        #  注入到沙箱 scripts/pipelines/ 后 Agent 直接 python3 执行)。
        try:
            from pathlib import Path as _P_ip
            _proj_root_ip = Path(os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parents[2])
            _src_pipelines = _proj_root_ip / "scripts" / "pipelines"
            _dst_pipelines = Path(base) / "scripts" / "pipelines"
            if _src_pipelines.is_dir() and not _dst_pipelines.is_dir():
                import shutil as _sh_ip
                _dst_pipelines.parent.mkdir(parents=True, exist_ok=True)
                _sh_ip.copytree(_src_pipelines, _dst_pipelines)
                print("[PIPELINE_INJECT] 项目级脚本注入: %s -> %s (%d 文件)" %
                      (_src_pipelines, _dst_pipelines, len(list(_src_pipelines.glob('*.py')))), flush=True)
        except Exception as _ip_e:
            pass  # 注入失败不阻断命令执行(仅诊断)
        import subprocess
        # P1-2: 工具执行超时从 execution_policy.yaml 读取(默认 30000ms), 不再硬编码 30s
        try:
            _tool_timeout = int(((_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}).get("tool_timeout_ms", 320000) or 320000)
        except Exception:
            _tool_timeout = 320000
        _tool_timeout_s = max(1, _tool_timeout / 1000.0)
        # 路径修正：command 含 clawsjoy_dev/xxx.py 时交由 _normalize_path 规范化，自动修正 cwd 避免双重拼接
        import re as _re_exec
        _exec_cwd = base
        _m_exec = _re_exec.search(r"clawsjoy_dev/[\w./\-]+", cmd)
        if _m_exec:
            try:
                _norm_exec = _normalize_path(_m_exec.group(0), user_id, session_id)
                if len(_norm_exec.parents) >= 2:
                    _exec_cwd = _norm_exec.parents[1]
            except Exception:
                _exec_cwd = base
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=_tool_timeout_s, cwd=str(_exec_cwd), env=_SANDBOX_ENV)
        except subprocess.TimeoutExpired:
            # P1-2: 长时间测试超时引导 — 不要 nohup 后台 + sleep 轮询
            return {"success": False, "stdout": "",
                    "stderr": f"命令执行超时(>{int(_tool_timeout_s)}s)。如需运行长时间测试，请改用 timeout 300 同步等待，不要 nohup 后台 + sleep 轮询。",
                    "returncode": -1}
        _is_heredoc_async = any(m in _strip_quoted_and_comments(cmd) for m in _HEREDOC_MARKERS)
        _sandbox_note_async = None
        if _is_heredoc_async:
            if "subprocess" in cmd or "os.system" in cmd or "popen" in cmd.lower():
                _sandbox_note_async = "heredoc 内 subprocess 可执行任意命令"
            import re as _re_wp
            _before_mtimes = {}
            for _wp in _re_wp.findall(r'open\([\'\"]([^\'\"]+)[\'\"]', cmd):
                if _wp.startswith(('/etc', '/home', '/root', '/var', '/usr', '/bin', '/sbin', '/opt', '/proc', '/sys', '/dev', '/boot')):
                    return {"success": False, "stdout": "", "stderr": "[sandbox] heredoc 内禁止读取系统路径", "returncode": 1}
                _abs = (base / _wp).resolve()
                if _abs.exists():
                    _before_mtimes[str(_abs)] = _abs.stat().st_mtime
            # 刷新目标文件 stat 缓存，消除 mtime 竞态窗口
            _abs_h = None
            for _wp2 in _re_wp.findall(r"""open\(['"]([^'"]+)['"]""", cmd):
                _abs_pre = (base / _wp2).resolve()
                _abs_h = _abs_pre
                if _abs_pre.exists():
                    _abs_pre.stat()
            try:
                _res_h = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=_tool_timeout_s, cwd=str(base), env=_SANDBOX_ENV)
            except subprocess.TimeoutExpired:
                return {"success": False, "stdout": "",
                        "stderr": f"命令执行超时(>{int(_tool_timeout_s)}s)。如需运行长时间测试，请改用 timeout 300 同步等待，不要 nohup 后台 + sleep 轮询。",
                        "returncode": -1}
            if _res_h.returncode == 0:
                import time as _t1; _t1.sleep(0.1)
                _modified = False
                for _wp2 in _re_wp.findall(r'open\([\'\"]([^\'\"]+)[\'\"]', cmd):
                    _abs2 = (base / _wp2).resolve()
                    if _abs2.exists() and str(_abs2) in _before_mtimes:
                        if _abs2.stat().st_mtime > _before_mtimes[str(_abs2)]:
                            _modified = True
                        else:
                            _res_h.stderr += f"\n[系统] {_wp2} 未被修改，请检查写入逻辑"
                if not _modified:
                    _res_h.stderr += "\n[系统] heredoc 执行成功但目标文件未被修改。请检查：1) 是否有 f.write(content) 2) open() 路径是否正确。修正后重试，或改用 write_file。"
                    if _abs_h is not None and _abs_h.exists():
                        try:
                            from core.lib.code_entity_extractor import extractor
                            _ec_h = extractor.extract_and_upsert(str(_abs_h)) or 0
                            if _ec_h > 0:
                                _res_h.stdout += f"\\n[SAG] {_ec_h}个实体已入库"
                        except Exception: pass
            if not _res_h.returncode == 0:
                _fail_h = sum(1 for m in messages[-8:] if m["role"] == "tool" and "heredoc" in str(m.get("content", "")).lower())
                if _fail_h >= _policy["retry"]["failure_analysis_max_loops"]:
                    _res_h.stderr += "\n[系统] 连续 3 次 heredoc 失败，请检查文件路径是否正确（cwd已是clawsjoy_dev/，不要加前缀）"
            if _res_h.returncode == 0:
                _last_usr_h = ""
                for _mu_h in messages:
                    if _mu_h["role"] == "user" and len(_mu_h.get("content", "")) > 10:
                        _last_usr_h = _mu_h["content"]
                        break
                if _last_usr_h:
                    try:
                        import psycopg2
                        from core.lib.code_entity_extractor import extractor
                        _pg = psycopg2.connect(extractor.db_url)
                        _cur = _pg.cursor()
                        _cur.execute("""
                            INSERT INTO code_entities (project_id, entity_type, entity_name, file_path, status)
                            VALUES (%s, 'task', %s, %s, 'pending')
                            ON CONFLICT (project_id, entity_name, file_path) DO UPDATE SET status = 'pending'
                        """, ("default", _last_usr_h[:200], f"/tasks/{session_id}"))
                        _pg.commit()
                        _cur.close()
                        _pg.close()
                    except Exception: pass
            if _res_h.returncode == 0:
                _sandbox_git_post_exec(user_id, session_id, cmd)
                _trk_e = _tracker_setdefault(_session_write_tracker, session_id, lambda: {"write_count": 0, "execute_write_count": 0, "files_written": [], "_seen": set()})
                _trk_e.setdefault("_seen", set())
                _trk_e["execute_write_count"] = _trk_e.get("execute_write_count", 0) + 1
            # #3: heredoc 分支输出截断(在 SAG/系统提示追加之后)
            return {"success": _res_h.returncode == 0,
                    "stdout": _truncate_cmd_output(_res_h.stdout, _CMD_STDOUT_LIMIT),
                    "stderr": _truncate_cmd_output(_res_h.stderr, _CMD_STDERR_LIMIT),
                    "git_status": _git_status(user_id, session_id)}
        # B3(2026-08-30): 读写分文案 — 纯读命令(cat/grep/head/tail/sed -n/awk/find/ls, 无 > 输出重定向)
        # 不应被当成写操作拦截; 2>/dev/null/2>&1 是 stderr 丢弃, 不是输出重定向
        _cmd_stripped = _strip_quoted_and_comments(cmd)
        _first_word = _cmd_stripped.strip().split()[0].lower() if _cmd_stripped.strip().split() else ""
        _read_cmds = ("cat", "grep", "head", "tail", "sed", "awk", "find", "ls", "wc", "echo", "pwd", "df", "du", "file", "stat")
        # 剥离 stderr 重定向后检测输出重定向(2>/dev/null/2>&1 不算写)
        import re as _re_b3
        _cmd_write_detect = _re_b3.sub(r"2>\S+", "", _cmd_stripped)
        _has_out_redirect = any(kw in _cmd_write_detect for kw in (">>", "> ", "tee ", "dd of=", "mkfs", "mount ")) or ">" in _cmd_write_detect
        _is_read_cmd = _first_word in _read_cmds and not _has_out_redirect and not _re_b3.search(r"(?m)^\s*echo[^|]*>", _cmd_stripped)
        _dangerous_async = False if _is_read_cmd else _has_out_redirect
        _hint_exec = None
        if _dangerous_async:
            import re as _re_cmd
            _cmd_paths = _re_cmd.findall(r'[\w_./-]+\.\w+', cmd)
            _resolved_async = []
            for _pa in _cmd_paths:
                try:
                    _abs_async = (base / _pa).resolve()
                    _resolved_async.append(str(_abs_async))
                except Exception:
                    _resolved_async.append(_pa)
            _all_in = all('clawsjoy_dev/' in p for p in _resolved_async) if _resolved_async else False
            if _cmd_paths and not _all_in:
                return {"success": False, "error": "禁止在沙箱外写入文件。"}
            if result.returncode == 0:
                _hint_exec = "文件已写入，请用 read_file 验证内容。"
        # 实体抽取（独立于 _dangerous_async）
        print(f"[TRACE-ASYNC] returncode={result.returncode}, is_heredoc={_is_heredoc_async}, cmd_len={len(cmd)}")
        _stdout = result.stdout
        if result.returncode == 0:
            import re as _re_wp2
            _write_paths2 = _re_wp2.findall(r"open\([\'\"]([^\'\"]+)[\'\"]", cmd)
            print(f"[ENTITY-ASYNC] 匹配到 {len(_write_paths2)} 个路径: {_write_paths2}")
            for _wp2 in _write_paths2:
                _abs_wp2 = (base / _wp2).resolve()
                if _abs_wp2.exists():
                    try:
                        from core.lib.code_entity_extractor import extractor
                        _ec2 = extractor.extract_and_upsert(str(_abs_wp2)) or 0
                        if _ec2 > 0:
                            _stdout += f"\n[SAG] {_ec2}个实体已入库，可用 query_index 检索"
                    except Exception:
                        pass
        if result.returncode == 0:
            _sandbox_git_post_exec(user_id, session_id, cmd)
            _trk_e = _tracker_setdefault(_session_write_tracker, session_id, lambda: {"write_count": 0, "execute_write_count": 0, "files_written": [], "_seen": set()})
            _trk_e.setdefault("_seen", set())
            _trk_e["execute_write_count"] = _trk_e.get("execute_write_count", 0) + 1
        # #3: 普通分支输出截断(SAG 追加之后)
        _return_dict = {"success": True,
                        "stdout": _truncate_cmd_output(_stdout, _CMD_STDOUT_LIMIT),
                        "stderr": _truncate_cmd_output(result.stderr, _CMD_STDERR_LIMIT),
                        "hint": _hint_exec, "git_status": _git_status(user_id, session_id)}
        if _sandbox_note_async:
            _return_dict["_sandbox_note"] = _sandbox_note_async
        return _return_dict
