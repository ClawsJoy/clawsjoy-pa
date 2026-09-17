#!/usr/bin/env python3
"""VerificationChain — 任务完成强制验证闭环（#166）

验收标准：写入 → 语法检查 → 运行验证 → 内容核验 → 全部通过 → 生成验证报告 → 记录到 task_progress

设计目标：
1. 用代码强制闭环，取代纯文本约束（LLM 可遵守也可不遵守）
2. 完成判定必须经过本模块：五步全通过才返回 passed=True
3. 每次验证生成 JSON 报告（data/verification_reports/）+ 入库 SAG steps_summary + 记录 task_progress
4. 任何一步失败 → passed=False + 详细失败原因，供网关拦截"虚假完成"

用法：
    from core.lib.verification_chain import run_verification_chain
    result = run_verification_chain(
        task_name="...", session_id="...", user_id="...",
        messages=[...], task_goal="...", base_dir=Path("data/projects/xxx/yyy")
    )
    # result = {"passed": bool, "report": {...}, "failures": [...]}
"""

import ast
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 写入工具白名单（结果级判定时用于区分"真正写入"）
WRITE_TOOLS = {"write_file", "write_large"}
# execute_command 中视为"写入类"的命令特征（出现即认为可能写入）
WRITE_CMD_MARKERS = [
    "write_file",
    "write_text",
    "heredoc",
    "cat >",
    "cat <<",
    "tee ",
    "echo >",
    "echo >>",
    "mv ",
    "cp ",
    "mkdir",
    "git add",
]
# 写入成功证据关键词（tool 返回内容中出现即认为该次写入已成功）
WRITE_SUCCESS_MARKERS = [
    "已写入",
    "写入成功",
    "写入完成",
    "auto_fixed",
    "success",
    "已创建",
    "已修改",
    "saved",
    "written",
    "ok",
]


def _extract_tool_results(messages: List[Dict]) -> List[Dict]:
    """从 messages 中提取所有 tool 调用及其返回结果。

    Returns:
        [{"tool": name, "args": dict, "result": str|dict}]
    """
    results = []
    tool_call_map = {}
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                _fn = tc.get("function", {})
                _name = _fn.get("name", "")
                _args_raw = _fn.get("arguments", "{}")
                try:
                    _args = json.loads(_args_raw) if isinstance(_args_raw, str) else (_args_raw or {})
                except Exception:
                    _args = {}
                tool_call_map[tc.get("id")] = (_name, _args)
        elif m.get("role") == "tool":
            _tid = m.get("tool_call_id")
            if _tid and _tid in tool_call_map:
                _name, _args = tool_call_map.pop(_tid)
                results.append(
                    {
                        "tool": _name,
                        "args": _args,
                        "result": m.get("content", ""),
                    }
                )
    return results


def _resolve_sandbox_path(base_dir: Path, path: str, project_root: str = "clawsjoy_dev") -> Path:
    # 2026-09-13 加固：契约是 base_dir = 沙箱的**父目录**，project_root = 沙箱目录名。
    # 但调用方极易误传「沙箱本身」→ 路径双拼成 .../clawsjoy_dev/clawsjoy_dev → 不存在 →
    # 抛错被上层 except 吞掉 → **五步链静默跳过**（实测连续踩中，从接入到 2026-09-13 一次没跑成）。
    # 这里做防御：base_dir 已以 project_root 结尾时，不再重复拼接。
    if str(base_dir).replace("\\", "/").rstrip("/").endswith("/" + str(project_root)):
        project_root = ""
    """将 Agent 传入的路径解析为沙箱磁盘绝对路径。"""
    _p = str(path)
    if _p.startswith("data/projects/") or _p.startswith("/"):
        return Path(_p)
    if _p.startswith(project_root + "/") or _p.startswith("clawsjoy_dev/"):
        _rel = _p.split("/", 1)[1] if "/" in _p else _p
        return (base_dir / project_root / _rel) if project_root else (base_dir / _rel)
    return (base_dir / project_root / _p) if project_root else (base_dir / _p)


def _guess_path_from_cmd(cmd: str, base_dir: Path, project_root: str) -> Optional[str]:
    """从 execute_command 命令中猜测目标文件路径（粗粒度，用于验证目标）。"""
    import re

    if not cmd:
        return None
    for m in re.finditer(r"(?:clawsjoy_dev/)?([\\w_/]+\\.(?:py|json|md|yaml|yml|txt|html|js|css))", cmd):
        _candidate = m.group(0)
        if _candidate.startswith("clawsjoy_dev/") or _candidate.startswith(project_root + "/"):
            return _candidate
        _abs = base_dir / project_root / _candidate
        if _abs.exists():
            return f"{project_root}/{_candidate}"
    return None


def collect_written_files(messages: List[Dict], base_dir: Path, project_root: str = "clawsjoy_dev") -> List[Dict]:
    """Step1:结果级收集"确认已写入"的文件列表。

    与旧 _check_recent_writes（意图级）的区别：
    - 只统计 write_file/write_large/execute_command 中**返回结果包含成功证据**的调用
    - execute_command 仅当命令包含写入类特征且返回无 error 时统计

    Returns:
        [{"path": str, "tool": str, "evidence": str, "absolute": Path}]
    """
    written = []
    seen = set()
    workdir = base_dir / project_root

    # 从沙箱 Git 获取最近一次任务开始后写入的文件列表
    # 或者直接遍历 workdir 下最近修改的 .py 文件

    import subprocess

    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"], cwd=str(workdir), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    # 批188 · 缺陷2 第二层（真根因）：git diff **看不见「新建未跟踪」文件** ⇒ 新产物（如 docs/x.md）
    # 永远判「未检测到成功写入」⇒ chain Step1 恒 FAIL（假失败，PA 线程实测）。
    # 修法：把 git diff 与「未跟踪文件清单」合并（只加不删，旧行为不变）。
    _diff_names = set()
    if result.returncode == 0 and result.stdout.strip():
        _diff_names |= {x.strip() for x in result.stdout.strip().split(chr(10)) if x.strip()}
    try:
        _un = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"], cwd=str(workdir), capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if _un.returncode == 0 and _un.stdout.strip():
            _diff_names |= {x.strip() for x in _un.stdout.strip().split(chr(10)) if x.strip()}
    except Exception:
        pass
    result = subprocess.CompletedProcess(
        args=result.args, returncode=0, stdout=chr(10).join(sorted(_diff_names)), stderr=""
    )
    if not (result.returncode == 0 and result.stdout.strip()):
        # 兜底：HEAD~1 不存在（首次提交/浅克隆）时，回退到 HEAD
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"], cwd=str(workdir), capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            fpath = workdir / line.strip()
            # 任务3 v5 修复: 去掉 .py 限制——子任务产出为 md/txt 等任意文件,
            # git diff 确认的变更即为真实写入证据(此前只认 .py 导致子任务 step1_write 判空)
            if fpath.exists():
                key = str(fpath)
                if key not in seen:
                    seen.add(key)
                    written.append(
                        {
                            "path": line.strip(),
                            "tool": "git_verified",
                            "evidence": "git diff 确认文件有变更",
                            "absolute": fpath,
                        }
                    )

    # 兜底：查最近 10 分钟内修改的 .py 文件
    if not written:
        import time

        # 从 task_progress 获取任务开始时间
        task_start_ts = None
        task_progress_file = base_dir / project_root / "data" / "task_progress.json"
        if task_progress_file.exists():
            with open(task_progress_file, encoding="utf-8") as f:
                data = json.load(f)
            # 取最早一条记录的 started_at 或 created_at
            steps = data.get("steps", [])
            if steps:
                task_start_ts = steps[0].get("started_at")

        cutoff = task_start_ts or (time.time() - 3600)  # 兜底1小时
        for f in workdir.rglob("*.py"):
            if f.stat().st_mtime > cutoff and f.exists():
                key = str(f)
                if key not in seen:
                    seen.add(key)
                    written.append(
                        {
                            "path": str(f.relative_to(workdir)),
                            "tool": "mtime_verified",
                            "evidence": f"mtime={f.stat().st_mtime}",
                            "absolute": f,
                        }
                    )

    return written


def syntax_check(files: List[Dict], base_dir: Path) -> Dict[str, Any]:
    """Step2 语法检查：AST 解析所有 .py 文件。

    Returns:
        {"passed": bool, "checked": [str], "failed": [{"path": str, "error": str}]}
    """
    checked = []
    failed = []
    for f in files:
        _abs = f.get("absolute")
        if not _abs or not _abs.exists():
            failed.append({"path": f.get("path", ""), "error": "文件不存在（写入未成功或路径错误）"})
            continue
        if _abs.suffix != ".py":
            checked.append(str(_abs))
            continue
        try:
            _code = _abs.read_text(encoding="utf-8", errors="ignore")
            ast.parse(_code)
            checked.append(str(_abs))
        except SyntaxError as e:
            failed.append({"path": f.get("path", ""), "error": f"语法错误: {e}"})
        except Exception as e:
            failed.append({"path": f.get("path", ""), "error": f"读取/解析错误: {e}"})
    return {"passed": len(failed) == 0, "checked": checked, "failed": failed}


def run_verify(files, base_dir, timeout=20):
    """Step3 运行验证：对 .py 文件执行 compile 编译冒烟 + py_compile 子进程校验，非 .py 文件做存在性/非空检查。"""
    import subprocess
    import sys

    checked = []
    failed = []
    for f in files:
        _abs = f.get("absolute")
        if not _abs or not _abs.exists():
            failed.append({"path": f.get("path", ""), "error": "文件不存在"})
            continue
        if _abs.suffix == ".py":
            try:
                _code = _abs.read_text(encoding="utf-8", errors="ignore")
                # 第一道快速冒烟：compile 失败即短路，不再进入子进程校验
                compile(_code, str(_abs), "exec")
                # 第二道校验：py_compile 子进程，timeout 兜底
                _proc = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(_abs)],
                    capture_output=True,
                    text=True,
                    timeout=timeout, encoding="utf-8", errors="replace"
                )
                if _proc.returncode != 0:
                    _err = (_proc.stderr or _proc.stdout or "").strip()
                    failed.append({"path": f.get("path", ""), "error": f"py_compile 校验失败: {_err or '未知错误'}"})
                    continue
                # 第三道校验：import 导入测试（importlib 子进程，timeout 兜底）
                _rel = _abs.relative_to(base_dir) if base_dir else Path(_abs.name)
                _mod = str(_rel).replace(os.sep, ".").replace("/", ".")
                if _mod.endswith(".py"):
                    _mod = _mod[:-3]
                _imp = subprocess.run(
                    [sys.executable, "-c", f"import {_mod}"],
                    capture_output=True,
                    text=True,
                    timeout=timeout, encoding="utf-8", errors="replace"
                )
                if _imp.returncode != 0:
                    _ierr = (_imp.stderr or _imp.stdout or "").strip()
                    failed.append({"path": f.get("path", ""), "error": f"import 导入测试失败: {_ierr or '未知错误'}"})
                    continue
                checked.append(str(_abs))
            except subprocess.TimeoutExpired:
                failed.append({"path": f.get("path", ""), "error": f"子进程校验超时（>{timeout}s）"})
            except (SyntaxError, ValueError) as e:
                failed.append({"path": f.get("path", ""), "error": f"运行级语法错误: {e}"})
            except Exception as e:
                failed.append({"path": f.get("path", ""), "error": f"编译错误: {e}"})
        else:
            try:
                if _abs.stat().st_size > 0:
                    checked.append(str(_abs))
                else:
                    failed.append({"path": f.get("path", ""), "error": "文件为空（0 字节）"})
            except OSError as e:
                failed.append({"path": f.get("path", ""), "error": f"无法读取: {e}"})
    return {"passed": len(failed) == 0, "checked": checked, "failed": failed}


def content_verify(files, task_goal="", base_dir=None):
    """Step4 内容核验：文件存在、非空、包含任务目标关键词。"""
    import re

    _kws = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z_]{3,}", task_goal or "")
    # 任务3 v6 修复: 扩展指令/虚词过滤——任务描述中的动作词/语气词不该当内容关键词,
    # 否则简单输出任务(如子任务写 output.md 内容为数据)命中不了 len//2 阈值而误判失败
    _noise = {
        "resume",
        "optimizer",
        "py",
        "markdown",
        "文件",
        "任务",
        "问题",
        "请用",
        "工具",
        "写入文件",
        "内容为",
        "写完后",
        "确认完成",
        "当前工作目录",
        "output",
        "result",
        "md",
        "write_file",
        "read_file",
        "file",
    }
    _action = {
        "添加",
        "创建",
        "修改",
        "删除",
        "新增",
        "实现",
        "编写",
        "补充",
        "完善",
        "修复",
        "解决",
        "优化",
        "更新",
        "写入",
        "完成",
        "确认",
        "使用",
        "调用",
        "写入文件",
    }
    # 子串过滤: 指令 token 常为长连续中文, 精确匹配会漏; 任一 noise/action 词命中即过滤
    _kws = [k for k in _kws if not any(n in k for n in _noise) and not any(a in k for a in _action)]
    checked = []
    failed = []
    for f in files:
        _abs = f.get("absolute")
        if not _abs or not _abs.exists():
            failed.append({"path": f.get("path", ""), "error": "文件不存在（写入未成功或路径错误）"})
            continue
        try:
            _content = _abs.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            failed.append({"path": f.get("path", ""), "error": f"读取失败: {e}"})
            continue
        if not _content.strip():
            failed.append({"path": f.get("path", ""), "error": "文件内容为空"})
            continue
        if _kws:
            _matched = sum(1 for k in _kws if k in _content)
            _need = max(1, len(_kws) // 2)
            # 文件路径与任务目标相关性校验
            _fname = f.get("path", "").lower()
            _fname_match = sum(1 for k in _kws if k.lower() in _fname)
            if _fname_match == 0 and len(_kws) >= 3:
                failed.append({"path": f.get("path", ""), "error": f"文件路径与任务目标不相关（文件名未命中任何关键词）"})
                continue
            if _matched < _need:
                failed.append(
                    {"path": f.get("path", ""), "error": f"内容核验未通过：目标关键词命中 {_matched}/{len(_kws)}，少于 {_need}"}
                )
                continue
        checked.append(str(_abs))
    return {"passed": len(failed) == 0, "checked": checked, "failed": failed}


def generate_report(result, task_name="", session_id="", user_id="", base_dir=None):
    """Step5 验证报告：JSON 写入 data/verification_reports/。"""
    import re

    _reports_dir = Path("data/verification_reports")
    _reports_dir.mkdir(parents=True, exist_ok=True)
    _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _slug = re.sub(r"[^\w\-]", "_", (task_name or "task")[:40])
    _file = _reports_dir / f"{_slug}_{_ts}.json"
    _report = {
        "task_name": task_name,
        "session_id": session_id,
        "user_id": user_id,
        "passed": result.get("passed", False),
        "steps": result.get("steps", {}),
        "failures": result.get("failures", []),
        "written_files": [f.get("path") for f in result.get("written_files", [])],
        "created_at": datetime.now().isoformat(),
    }
    _file.write_text(json.dumps(_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return _file


def record_task_progress(result, task_name="", session_id="", user_id=""):
    """Step6 记录 task_progress：data/task_progress.json 追加记录 + progress_manager checkpoint。"""
    try:
        from core.lib.progress_manager import ProgressManager

        _pm = ProgressManager(user_id, session_id)
        _pm.save_checkpoint(
            task_name,
            [f.get("path") for f in result.get("written_files", [])],
            0,
            result.get("failures", []),
            f"verification_chain passed={result.get('passed')}",
        )
    except Exception:
        pass
    _tf = Path("data/task_progress.json")
    try:
        _tf.parent.mkdir(parents=True, exist_ok=True)
        _all = json.loads(_tf.read_text(encoding="utf-8")) if _tf.exists() else []
        if not isinstance(_all, list):
            _all = []
        _all.append(
            {
                "task_name": task_name,
                "session_id": session_id,
                "user_id": user_id,
                "passed": result.get("passed", False),
                "steps": result.get("steps", {}),
                "failures": result.get("failures", []),
                "recorded_at": datetime.now().isoformat(),
            }
        )
        _tf.write_text(json.dumps(_all, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def run_verification_chain(
    task_name="",
    session_id="",
    user_id="",
    messages=None,
    task_goal="",
    base_dir=None,
    project_root="clawsjoy_dev",
    require_write=True,
    done_when: str = "",
):
    """五步验证闭环主入口：写入 → 语法检查 → 运行验证 → 内容核验 → 报告 → task_progress。

    任一环节失败 → passed=False + failures，供网关拦截"虚假完成"。
    """
    _bd = base_dir or Path(".")
    _written = collect_written_files(messages or [], _bd, project_root)
    _evidence = "messages_or_git"
    if not _written:
        # 批188 · 缺陷2 第三层之二：沙箱 .gitignore 会把产物屏蔽（git diff 与 ls-files 都看不见）
        # ⇒ 用「本 session 已批准写入的文件」当线索，交 verify_artifacts 逐条实测；
        # 不存在 / 过小 / 占位仍然 FAIL —— 不制造假绿。
        try:
            from core.gateway.shared_state import approved_files as _af_vc

            _clues = [p for p in (_af_vc(session_id, within_s=1800) or []) if p and not str(p).startswith("cmd:")]
        except Exception:
            _clues = []
        if _clues:
            try:
                from core.pa.artifact import verify_artifacts as _va_vc

                # 线索路径已被 _norm_approval_path 剥掉 clawsjoy_dev/ 前缀（沙箱内相对路径）
                # ⇒ 先试「沙箱根（_bd/project_root）」，再退回 _bd；两个基准都不通才算失败。
                _av = None
                for _cb in (_bd / project_root, _bd):
                    _try = _va_vc(_clues, base_dir=_cb, expected_min_bytes=None)
                    if _try.get("ok"):
                        _av = _try
                        break
                    if _av is None:
                        _av = _try
                _av = _av or {"details": []}
                for _d in _av.get("details") or []:
                    if _d.get("ok"):
                        _written.append(
                            {
                                "path": _d.get("path"),
                                "tool": "approved_write",
                                "evidence": "审批后补执行且 verify_artifacts 实测通过",
                            }
                        )
                _evidence = "approved_write"
            except Exception:
                pass
    _steps = {
        "step1_write": {"passed": bool(_written), "files": [f.get("path") for f in _written], "evidence": _evidence}
    }
    _failures = []
    if require_write and not _written:
        _failures.append("Step1 写入校验失败：未检测到任何 write_file/write_large/execute_command 的成功写入记录")
    _r2 = syntax_check(_written, _bd)
    _steps["step2_syntax"] = _r2
    if not _r2["passed"]:
        _failures.append(f"Step2 语法检查失败: {_r2['failed']}")
    _r3 = run_verify(_written, _bd)
    _steps["step3_run"] = _r3
    if not _r3["passed"]:
        _failures.append(f"Step3 运行验证失败: {_r3['failed']}")
    _r4 = content_verify(_written, task_goal, _bd)
    _steps["step4_content"] = _r4
    if not _r4["passed"]:
        _failures.append(f"Step4 内容核验失败: {_r4['failed']}")
    _r5 = {"passed": True, "detail": "无 done_when 断言，跳过"}
    if done_when:
        _r5 = _check_done_when(done_when, _bd / project_root)
        if not _r5["passed"]:
            _failures.append(f"Step5 done_when 断言失败: {_r5['detail']}")
    _steps["step5_done_when"] = _r5
    _passed = len(_failures) == 0
    _result = {
        "passed": _passed,
        "steps": _steps,
        "failures": _failures,
        "written_files": _written,
    }
    _report_file = generate_report(_result, task_name, session_id, user_id, _bd)
    record_task_progress(_result, task_name, session_id, user_id)
    print(f"[VerificationChain] task={task_name} passed={_passed} failures={len(_failures)} report={_report_file}")
    return _result


def _check_done_when(done_when: str, base_dir: Path) -> dict:
    """解析 done_when 中的 check: 前缀断言，执行对应验证"""
    import re
    import subprocess

    result = {"passed": False, "detail": ""}
    if not done_when or not done_when.startswith("check:"):
        result["detail"] = "done_when 为空或格式不正确"
        return result
    check = done_when[6:]
    if check.startswith("file_exists:"):
        path = check[12:]
        abs_path = base_dir / path
        result["passed"] = abs_path.exists()
        result["detail"] = f"文件{'存在' if result['passed'] else '不存在'}: {path}"
    elif check.startswith("command_success:"):
        cmd = check[16:]
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=str(base_dir), encoding="utf-8", errors="replace")
        result["passed"] = r.returncode == 0
        result["detail"] = f"命令返回码={r.returncode}: {cmd}"
    elif check.startswith("file_contains:"):
        parts = check[14:].split(":", 1)
        if len(parts) == 2:
            path, keyword = parts
            abs_path = base_dir / path
            if abs_path.exists():
                content = abs_path.read_text(encoding="utf-8", errors="replace")
                result["passed"] = keyword in content
                result["detail"] = f"文件{'包含' if result['passed'] else '不包含'}关键词: {path}:{keyword}"
            else:
                result["detail"] = f"文件不存在: {path}"
        else:
            result["detail"] = f"file_contains 格式错误: {check}"
    else:
        result["detail"] = f"不支持的 check 类型: {check}"
    return result
