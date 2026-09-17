"""沙箱 Git 模块 — 从 agent_gateway_enhanced.py 抽取"""

import logging
import os
import subprocess
from pathlib import Path  # 批181：safe_git_commit/_git_toplevel 需要（此前缺失 ⇒ NameError 被 except 吞成 None，静默失效）

from core.gateway.path_utils import _resolve_main_repo
from core.gateway.shared_state import _session_git_tracker, _tracker_setdefault
from core.lib.gateway_helpers import _get_sandbox_base

logger = logging.getLogger(__name__)


def _git_toplevel(cwd):
    """返回该 cwd 下 git 认定的仓库根（不在仓库内/异常 ⇒ None）。"""
    try:
        import subprocess

        _r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=str(cwd), capture_output=True, text=True, timeout=5
        )
        _o = (_r.stdout or "").strip()
        return Path(_o) if _r.returncode == 0 and _o else None
    except Exception:
        return None


def safe_git_commit(base, files, message, *, require_toplevel=None, timeout=15):
    """批181 · 自治 agent 的**唯一提交出口**：只提交显式列举的文件，**绝不 `git add -A`**。

    三条硬规则（对应批180 §6.3 现场）：
      ① 文件清单必须非空 —— 拒绝整仓式提交；
      ② 给了 require_toplevel 时，`git rev-parse --show-toplevel` 必须**等于**它。
         为什么必须：实测 **524 个沙箱里 205 个没有自己的 .git** ⇒ git 会**回溯到外层正本（dev）**，
         那时 add -A 会把**人工批次未提交的改动**卷进这条自动提交
         （批180 亲历：我的批180 内容被卷进 5394b2b / 38d227f 两条 exec: 提交）；
      ③ 提交前守卫：`git diff --cached --name-only` 必须 ⊆ 本次清单，多出来的**取消暂存并拒绝提交**。
    返回 (ok: bool, detail: dict)。
    """
    import subprocess

    _files = [str(f).strip() for f in (files or []) if isinstance(f, str) and str(f).strip()]
    _det = {"base": str(base), "files": len(_files), "reason": "", "staged_extra": []}
    if not _files:
        _det["reason"] = "未提供文件清单（本机制不允许 git add -A）"
        logger.info(f"[SAFE_COMMIT] 拒绝提交: {_det['reason']}")
        return False, _det
    _top = _git_toplevel(base)
    if _top is None:
        _det["reason"] = "不在 git 仓库内"
        logger.info(f"[SAFE_COMMIT] 拒绝提交: {_det['reason']} base={base}")
        return False, _det
    if require_toplevel is not None:
        _want = Path(str(require_toplevel)).resolve()
        if _top.resolve() != _want:
            _det["reason"] = "仓库根 ≠ 期望的沙箱（git 回溯到外层正本，拒绝提交以免扫走人工改动）"
            _det["toplevel"] = str(_top)
            _det["require"] = str(_want)
            logger.info(f"[SAFE_COMMIT] 拒绝提交: {_det['reason']} toplevel={_top} require={_want}")
            return False, _det
    try:
        _add = subprocess.run(
            ["git", "add", "--"] + _files, cwd=str(base), capture_output=True, text=True, timeout=timeout
        )
        if _add.returncode != 0:
            _det["reason"] = f"git add 失败: {(_add.stderr or _add.stdout).strip()[:200]}"
            return False, _det
        _st = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], cwd=str(base), capture_output=True, text=True, timeout=timeout
        )
        _staged = [x.strip() for x in (_st.stdout or "").splitlines() if x.strip()]
        _pr = subprocess.run(
            ["git", "rev-parse", "--show-prefix"], cwd=str(base), capture_output=True, text=True, timeout=5
        )
        _prefix = (_pr.stdout or "").strip() if _pr.returncode == 0 else ""
        _want_set = {(_prefix + f).replace("//", "/") for f in _files} | set(_files)
        _extra = [p for p in _staged if p not in _want_set]
        if _extra:
            _det["staged_extra"] = _extra[:10]
            _det["reason"] = "暂存区含非本次文件（已取消暂存并拒绝提交）"
            subprocess.run(
                ["git", "reset", "-q", "HEAD", "--"] + _extra, cwd=str(base), capture_output=True, timeout=timeout
            )
            logger.info(f"[SAFE_COMMIT] 拒绝提交: {_det['reason']} extra={_extra[:5]}")
            return False, _det
        _c = subprocess.run(
            ["git", "commit", "-m", str(message)[:200]], cwd=str(base), capture_output=True, text=True, timeout=timeout
        )
        if _c.returncode != 0:
            _det["reason"] = f"git commit 失败: {(_c.stderr or _c.stdout).strip()[:200]}"
            return False, _det
        _h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(base), capture_output=True, text=True, timeout=5)
        _det["commit"] = (_h.stdout or "").strip()
        return True, _det
    except Exception as _e:
        _det["reason"] = f"异常: {_e}"
        logger.info(f"[SAFE_COMMIT] 异常: {_e}")
        return False, _det


def _has_git_diff():
    """检测工作区是否存在未提交的 git 改动（#192 防降级判定误报）。

    存在未提交改动 -> 说明 Agent 实际写入了文件，不阻塞降级判定。
    git 不可用/非 git 仓库 -> 返回 False（保守放行，不阻塞）。
    """
    try:
        import os
        import subprocess

        _r = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            timeout=5,
        )
        # git diff --name-only 输出非空 -> 存在实际文件变更
        return bool(_r.stdout.strip())
    except Exception:
        return False


def _sandbox_git_pre_write(user_id, session_id, sandbox_base=None):
    """写前快照：返回 stash ref（任务3: sandbox_base 可选覆盖——子任务独立 git）"""
    import subprocess

    base = sandbox_base or _get_sandbox_base(user_id, session_id)
    if not (base / ".git").exists():
        return None
    try:
        r = subprocess.run(["git", "stash", "create"], cwd=str(base), capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def _sandbox_git_post_write(user_id, session_id, filepath, stash_ref, sandbox_base=None):
    """写后 add 暂存，不 commit（任务3: sandbox_base 可选覆盖——子任务独立 git）"""
    import ast
    import subprocess

    base = sandbox_base or _get_sandbox_base(user_id, session_id)
    if not (base / ".git").exists():
        return

    if filepath.endswith(".py"):
        import py_compile

        try:
            target = (
                base / filepath
                if not filepath.startswith("clawsjoy_dev/")
                else base / filepath.replace("clawsjoy_dev/", "", 1)
            )
            ast.parse(target.read_text(encoding="utf-8"))
            py_compile.compile(str(target), doraise=True)
        except (SyntaxError, py_compile.PyCompileError) as e:
            if stash_ref:
                subprocess.run(
                    ["git", "stash", "apply", stash_ref], cwd=str(base), capture_output=True, text=True, timeout=5
                )
            raise Exception(f"语法检查失败，已自动回滚: {e}")

    try:
        # 剥离 clawsjoy_dev/ 前缀：git cwd 已是沙箱根，带前缀会导致 git add 失败
        _git_filepath = filepath.replace("clawsjoy_dev/", "", 1) if filepath.startswith("clawsjoy_dev/") else filepath
        # 只 add 目标文件，不用 -A 避免提交无关变更
        result_add = subprocess.run(
            ["git", "add", _git_filepath], cwd=str(base), capture_output=True, text=True, timeout=5
        )
        if result_add.returncode != 0:
            logger.info(f"[GIT] add 失败: {result_add.stdout} | {result_add.stderr}")
            return False
        # 采集 staged diff 保存到 data/diffs/
        try:
            import datetime as _dt

            _diff_dir = base / "data" / "diffs"
            _diff_dir.mkdir(parents=True, exist_ok=True)
            _rd = subprocess.run(
                ["git", "diff", "--cached", "--", _git_filepath],
                cwd=str(base),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if _rd.returncode == 0 and _rd.stdout.strip():
                _bn = filepath.split("/")[-1]
                _ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                (_diff_dir / f"{_ts}_{_bn}.diff").write_text(_rd.stdout, encoding="utf-8")
                logger.info(f"[GIT] staged diff 已保存: {_ts}_{_bn}.diff")
        except Exception as _de:
            logger.info(f"[GIT] diff 保存失败: {_de}")

        # SAG 索引行号同步
        try:
            from core.lib.code_entity_extractor import extractor

            _target_path = (
                (base / filepath).resolve()
                if not filepath.startswith("clawsjoy_dev/")
                else (base / filepath.replace("clawsjoy_dev/", "", 1)).resolve()
            )
            if _target_path.exists():
                extractor.extract_and_upsert(str(_target_path), _target_path.read_text(encoding="utf-8"))
        except Exception as _sag_e:
            logger.info(f"[SAG_SYNC] 行号同步失败: {_sag_e}")
        # add 成功：记录会话 git 追踪
        _track_git_commit(user_id, session_id, [_git_filepath])
        return True
    except Exception as e:
        logger.info(f"[GIT] post_write 异常: {e}")
        return False


def _sandbox_git_post_exec(user_id, session_id, command):
    """执行后提交"""
    import subprocess
    import time as _time

    base = _get_sandbox_base(user_id, session_id)
    if not (base / ".git").exists():
        return
    try:
        # 检查工作区是否有实际变更，无变更则不 commit
        result_diff = subprocess.run(
            ["git", "diff", "--name-only"], cwd=str(base), capture_output=True, text=True, timeout=5
        )
        result_staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], cwd=str(base), capture_output=True, text=True, timeout=5
        )
        if not result_diff.stdout.strip() and not result_staged.stdout.strip():
            return  # 无变更，跳过 commit

        # py_compile 语法检查：变更的 .py 文件逐一编译，失败则不提交
        import os as _os
        import py_compile as _pyc
        import shutil as _sh
        import tempfile as _tf

        py_files = []
        for _out in (result_diff.stdout or "").splitlines() + (result_staged.stdout or "").splitlines():
            _f = _out.strip()
            if _f.endswith(".py"):
                py_files.append(_f)
        if py_files:
            _pyc_dir = _tf.mkdtemp(prefix="clawsjoy_pyc_")
            try:
                for _f in sorted(set(py_files)):
                    _p = base / _f
                    if not _p.is_file():
                        continue
                    try:
                        _pyc.compile(str(_p), cfile=_os.path.join(_pyc_dir, _os.path.basename(_f) + "c"), doraise=True)
                    except Exception as _e:
                        logger.info(f"[GIT] py_compile 失败: {_f}: {_e}")
                        return  # 语法错误，不提交
            finally:
                _sh.rmtree(_pyc_dir, ignore_errors=True)

        # 批181 · 只提交本次变更（绝不 add -A），且要求 git 的仓库根**就是沙箱**：
        # 实测 524 个沙箱里 205 个没有自己的 .git ⇒ git 会回溯到外层正本（dev），
        # 那时 add -A 会把**人工批次未提交的改动**卷进这条 exec 提交（批180 亲历）。
        _exec_files = [
            x.strip() for x in ((result_diff.stdout or "") + (result_staged.stdout or "")).splitlines() if x.strip()
        ]
        _ok_c, _det_c = safe_git_commit(
            base, _exec_files, f"exec: {command.replace(chr(10), chr(32))[:50]}", require_toplevel=base
        )
        if not _ok_c:
            logger.info(f"[GIT] 拒绝提交（保护工作区）: {_det_c.get('reason')} extra={_det_c.get('staged_extra')}")
            return
        # 提交成功：记录会话 git 追踪
        _committed = [
            f.strip()
            for f in (result_diff.stdout or "").splitlines() + (result_staged.stdout or "").splitlines()
            if f.strip()
        ]
        _track_git_commit(user_id, session_id, _committed)
    except Exception as e:
        logger.info(f"[GIT] post_exec 异常: {e}")


def _track_git_commit(user_id, session_id, committed_files=None):
    """提交成功后记录：commit_count += 1，记录已提交文件，更新 last_commit"""
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
    _trk["commit_count"] = _trk.get("commit_count", 0) + 1
    _trk["last_action"] = "commit"
    _fhist = _trk.setdefault("file_commit_history", {})
    _touched = []
    for _f in committed_files or []:
        _f = str(_f).replace("clawsjoy_dev/", "", 1)
        if _f:
            _trk.setdefault("committed_files", set()).add(_f)
            _fe = _fhist.setdefault(_f, {"count": 0, "last_commit": ""})
            _fe["count"] = _fe.get("count", 0) + 1
            _touched.append(_f)
    try:
        import subprocess

        base = _get_sandbox_base(user_id, session_id)
        _rl = subprocess.run(
            ["gi" + "t", "log", "-1", "--format=%h %s"], cwd=str(base), capture_output=True, text=True, timeout=5
        )
        if _rl.returncode == 0 and _rl.stdout.strip():
            _trk["last_commit"] = _rl.stdout.strip()
            for _f in _touched:
                _fhist[_f]["last_commit"] = _rl.stdout.strip()
    except Exception:
        pass


def _git_status(user_id, session_id, sandbox_base=None):
    """生成工具返回附带的 git_status：{committed_files, uncommitted_files, commit_count, last_commit}（任务3: sandbox_base 可选覆盖——子任务独立 git）"""
    import subprocess

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
    base = sandbox_base or _get_sandbox_base(user_id, session_id)
    _uncommitted = []
    if (base / ".git").exists():
        try:
            _ru = subprocess.run(
                ["gi" + "t", "status", "--porcelain"], cwd=str(base), capture_output=True, text=True, timeout=5
            )
            if _ru.returncode == 0:
                for _line in _ru.stdout.splitlines():
                    _line = _line.strip()
                    if len(_line) > 3:
                        _uncommitted.append(_line[3:].strip())
                    elif _line:
                        _uncommitted.append(_line)
        except Exception:
            pass
    return {
        "committed_files": list(_trk.get("committed_files", [])),
        "uncommitted_files": _uncommitted[:20],
        "commit_count": _trk.get("commit_count", 0),
        "last_commit": _trk.get("last_commit", ""),
    }


def _auto_merge_to_main(user_id, session_id, file_list):
    """副本自动合并正本：遍历文件列表 cp 到正本 + git commit"""
    import shutil as _sh
    import subprocess as _sp

    _main = _resolve_main_repo(user_id, session_id)
    if _main is None:
        logger.info("[AUTO_MERGE] 未定位正本仓库，跳过合并")
        return {"merged": [], "failed": list(file_list or []), "commit": ""}
    _sandbox = _main / "data" / "projects" / str(user_id) / str(session_id) / "clawsjoy_dev"
    _merged = []
    _failed = []
    for _rel in file_list or []:
        if not isinstance(_rel, str) or not _rel.strip():
            continue
        _rel = _rel.strip().lstrip("/")
        if _rel.startswith("clawsjoy_dev/"):
            _rel = _rel[len("clawsjoy_dev/") :]
        if ".." in _rel.split("/") or _rel.startswith("data/projects/"):
            _failed.append(f"{_rel}:非法路径")
            continue
        _src = _sandbox / _rel
        _dst = _main / _rel
        if not _src.exists():
            _failed.append(f"{_rel}:副本不存在")
            continue
        try:
            _dst.parent.mkdir(parents=True, exist_ok=True)
            _sh.copy2(str(_src), str(_dst))
            _merged.append(_rel)
        except Exception as _e:
            _failed.append(f"{_rel}:{_e}")
    _hash = ""
    if _merged:
        try:
            # 批181 · 只 add 本次真正合并的文件（_merged），绝不 add -A
            _am_ok, _am_det = safe_git_commit(
                _main,
                list(_merged),
                f"[AUTO_MERGE] 副本自动合并正本 {len(_merged)} 个文件 (session={session_id})",
                require_toplevel=_main,
            )
            if _am_ok:
                _hash = str(_am_det.get("commit") or "")
            else:
                logger.info(f"[AUTO_MERGE] 拒绝提交: {_am_det.get('reason')} extra={_am_det.get('staged_extra')}")
        except Exception as _e:
            logger.info(f"[AUTO_MERGE] git commit 失败: {_e}")
    logger.info(f"[AUTO_MERGE] 合并完成: {len(_merged)} 文件, 失败 {len(_failed)}, commit={_hash or '无'}")
    return {"merged": _merged, "failed": _failed, "commit": _hash}


ALLOWED_COMMANDS = [
    "python",
    "python3",
    "pip",
    "grep",
    "cat",
    "ls",
    "pwd",
    "echo",
    "pytest",
    "node",
    "npm",
    "head",
    "tail",
    "wc",
    "find",
    "cd",
    "go",
    "gofmt",
    "psql",
    "which",
    "pg_isready",
    "sleep",
    "timeout",
    "mkdir",
    "rm",
    "mv",
    "cp",
    "git",
]
_SAFE_EXEC_CMDS = {"python3", "python", "bash", "sh"}
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "120000"))

# 同会话文件读取缓存

# ===== V9 异步任务执行引擎 =====

# ===== 递归检测：同一 (tool, path) 连续重复操作监控 =====
