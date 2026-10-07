# -*- coding: utf-8 -*-
"""V9-PES · Windows 底座（Storage / Agent 外围层的平台适配）。

对应总任务书工程版 v1 **第四章「Windows 版本目标」**，逐条落成可调用件：

| 领域 | 落点 |
|---|---|
| 文件系统 | :func:`normalize_path` / :func:`same_path` / :func:`join_under` / :func:`classify_path` —— **禁止裸字符串拼路径**，沙箱路径解析单一出口 |
| 本地进程 | :class:`ProcessLedger` —— 进程有句柄与生命周期台账，**不留孤儿** |
| PowerShell | :func:`shell_guard` —— **逐条过门**、可回放、**不静默降级到 shell**、危险命令硬拒 |
| 浏览器 | :data:`BROWSER_ISOLATION` —— **默认**专用实例 + 独立 ``user-data-dir``；复用日常 profile 只允许**显式接管**（``wired=False``，声明性） |
| WSL | :data:`WSL_BOUNDARY` —— **跨环境 = 跨信任边界**，需单独授权（``wired=True``，消费者＝:func:`is_wsl_path`） |
| git | :func:`is_sandbox_repo` / :func:`is_real_repo` —— 沙箱 git 与真项目 git **必须区分**（不自动推远程） |

设计纪律：本模块**只做平台事实与契约常量**，**不做业务决策**（决策在 authorization 层）。
"""

from __future__ import annotations

import os
import subprocess
from core.lib import _proc as _proc_xh   # ⭐ pm_1791 §三.2：窗隐唯「_proc」出口（⛔ 裸调）
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

#: 仓库根（core/pes/windows.py → parents[2]）
REPO_ROOT = Path(__file__).resolve().parents[2]

#: 沙箱根（相对仓库）
SANDBOX_REL = "data"

#: 金库根（知识/台账）
VAULT_REL = "data/v9/pa"

#: Windows 最大路径（不含长路径前缀）
_WIN_MAX_PATH = 260

#: 浏览器隔离契约 —— **默认**专用实例；复用日常 profile 属「显式接管」
#:
#: **声明性（``wired=False``）**：本常量**无生产代码消费者**；实际策略落在
#: ``scripts/agent_client/``（显式 ``--profile`` 接管 + 启动日志打印实际 profile 路径）。
#: ``wired`` 不是自述句，而是被 ``tests/pes/test_windows_base.py`` 按**实测** AST 消费者数校验：
#: wired 与实测不符 / 缺 wired / 声明性缺 declarative_note ⇒ 三者任一即红。
#:
#: 口径（``X-18`` · 2026-09-18 拍）：复用老板日常 Chrome profile **不是禁止项**，
#: 而是**只能显式接管**（``user_profile_reuse=explicit_only``）—— 不许静默接管。
BROWSER_ISOLATION: Dict[str, Any] = {
    "dedicated_instance_by_default": True,
    "separate_user_data_dir_by_default": True,
    "user_profile_reuse": "explicit_only",  # silent | explicit_only | forbidden
    "wired": False,
    "declarative_note": "全仓生产代码消费者 = 0；实际策略在 scripts/agent_client/（显式 --profile 接管 + 启动打印实际路径）。",
    "note": "默认必须专用实例 + 独立 user-data-dir；不得**静默**接管老板日常 Chrome profile（显式接管须在启动日志打印实际 profile 路径）。",
}

#: WSL 边界契约 —— 跨环境 = 跨信任边界
#:
#: **已接线（``wired=True``）**：消费者 = 同模块 :func:`is_wsl_path` 的 ``markers``。
#:
#: 2026-09-18 归一（DS 拍「归并＝接线」）：此前是**两份真源** —— 实现在 :func:`is_wsl_path`
#: 内硬编码 **6 个** markers，契约只列 **4 个**（缺 ``/var/``、``/tmp/``）⇒ 现改为
#: **契约即真源**（:func:`is_wsl_path` 直接读本键），契约补齐到 **6 个**；
#: **行为逐字节不变**（6 个一个不多一个不少）。原 4 值清单保留在台账 ``X-18`` 行的更正段。
WSL_BOUNDARY: Dict[str, Any] = {
    "cross_env_is_trust_boundary": True,
    "requires_explicit_grant": True,
    "wired": True,
    "note": "Windows ↔ WSL 调用需显式适配层与单独授权；不得当作本地同信任域调用。",
    "wsl_markers": ("/mnt/", "/home/", "/usr/", "/etc/", "/var/", "/tmp/"),
}


# ============================== 文件系统 ==============================
def normalize_path(p) -> str:
    """路径**统一归一**：绝对化 + 正斜杠 + 解析符号链接（存在时）。

    为什么不用 ``str(Path)``：Windows 下 ``str(Path)`` 给反斜杠，
    而项目内部契约是正斜杠（详见 codex 笔记 ``windows-path-separator-contract``）。
    """
    path = Path(str(p))
    try:
        path = path.expanduser()
    except Exception:
        pass
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        if path.exists():
            path = path.resolve()
        else:
            path = Path(os.path.abspath(str(path)))
    except Exception:
        path = Path(os.path.abspath(str(path)))
    return path.as_posix()


def same_path(a, b) -> bool:
    """路径等价判定。**Windows 大小写不敏感**，POSIX 敏感 —— 这里按平台正确判定。"""
    na, nb = normalize_path(a), normalize_path(b)
    if os.name == "nt":
        return na.lower() == nb.lower()
    return na == nb


def long_path(p) -> str:
    """给超长路径加 ``\\\\?\\`` 前缀（Windows 生效，其它平台原样返回）。"""
    s = str(Path(p))
    if os.name != "nt":
        return s
    if s.startswith("\\\\?\\"):
        return s
    if len(s) < _WIN_MAX_PATH:
        return s
    if s.startswith("\\\\"):
        return "\\\\?\\UNC\\" + s.lstrip("\\")
    return "\\\\?\\" + s


def join_under(base, *parts) -> Path:
    """**唯一拼接出口**：在 ``base`` 之下拼 ``parts``，**越界即拒**。

    禁止裸字符串拼路径（总任务书第四章）。越界（含 ``..`` 逃逸）抛 ``ValueError``，
    **不静默**返回 base。
    """
    b = Path(normalize_path(base))
    t = b
    for raw in parts:
        piece = str(raw).replace("\\", "/").strip("/")
        if piece in ("", "."):
            continue
        if piece == "..":
            raise ValueError("join_under 拒绝 `..`：不允许越出 base")
        t = t / piece
    nb, nt = normalize_path(b), normalize_path(t)
    if os.name == "nt":
        ok = nt.lower() == nb.lower() or nt.lower().startswith(nb.lower() + "/")
    else:
        ok = nt == nb or nt.startswith(nb + "/")
    if not ok:
        raise ValueError("join_under 越界：%s 不在 %s 之下" % (nt, nb))
    return t


def classify_path(p) -> str:
    """把路径归到**信任域**：``sandbox`` / ``vault`` / ``repo`` / ``system`` / ``external``。

    用途：产物归属必须显式区分（沙箱 vs 真项目）—— 总任务书 §3.2 Storage 层。
    """
    n = normalize_path(p)
    low = n.lower()
    sb = normalize_path(REPO_ROOT / SANDBOX_REL).lower()
    vr = normalize_path(REPO_ROOT / VAULT_REL).lower()
    rr = normalize_path(REPO_ROOT).lower()
    if low == vr or low.startswith(vr + "/"):
        return "vault"
    if low == sb or low.startswith(sb + "/"):
        return "sandbox"
    if low == rr or low.startswith(rr + "/"):
        return "repo"
    drive, _ = os.path.splitdrive(n)
    if os.name == "nt" and drive:
        sysroot = (os.environ.get("SystemRoot") or "C:\\Windows").replace("\\", "/").lower()
        if low.startswith(sysroot) or low.startswith("c:/windows"):
            return "system"
    return "external"


def is_sandbox_repo(p) -> bool:
    """是否**沙箱内**的 git 工作副本（沙箱 git 与真项目 git 必须区分）。"""
    n = normalize_path(p)
    if os.path.isdir(os.path.join(n, ".git")) is False and not n.endswith(".git"):
        gitdir = os.path.join(n, ".git")
        if not os.path.isdir(gitdir):
            return False
    return classify_path(n) in ("sandbox", "vault")


def is_real_repo(p) -> bool:
    """是否**真项目**仓库（非沙箱）—— 真项目提交须走唯一出口且**不自动推远程**。"""
    return classify_path(p) in ("repo",) and Path(normalize_path(p), ".git").is_dir()


def is_wsl_path(p) -> bool:
    """是否指向 WSL/Linux 侧路径（跨信任边界）。

    **先看原始写法，再看归一化结果**：Windows 上 ``Path("/home/x")`` 被解释为
    「当前盘符根下的 home/x」（``D:/home/x``）。只判归一化结果的话，``/home/`` 这类
    Linux 绝对路径会被**误判成非 WSL 路径** ⇒「跨环境 = 跨信任边界」的守卫静默失效。

    markers **不在此另立字面量**：单一真源 = :data:`WSL_BOUNDARY` 的 ``wsl_markers``
    （2026-09-18 归一；此前这里是第二份真源，见 ``L-09``）。
    """
    markers = WSL_BOUNDARY["wsl_markers"]
    raw = str(p or "").replace(chr(92), "/").strip().lower()
    if raw.startswith(markers):
        return True
    if normalize_path(p).lower().startswith(markers):
        return True
    return False


# ============================== 本地进程 ==============================
class ProcessLedger:
    """本地子进程**句柄与生命周期台账**（总任务书第四章：**不留孤儿**）。

    落盘 JSON（走 State Integrity 的唯一出口），进程结束即标记 ``exited``；
    :meth:`reap_orphans` 找出「台账里 running 但实际已不在」的条目并结清，
    使「有没有孤儿」成为**可查询**的事实，而不是靠人看任务管理器。
    """

    def __init__(self, path=None, state_store=None):
        self.path = path or str(REPO_ROOT / "data" / "v9" / "pes" / "processes.json")
        self._store = state_store

    def _store_obj(self):
        if self._store is not None:
            return self._store
        from core.pes.state_integrity import StateFile

        self._store = StateFile(self.path, writer="pes.process_ledger", seed_keys=())
        return self._store

    def register(self, pid: int, argv, cwd="", purpose="") -> Dict[str, Any]:
        rec = {
            "pid": int(pid),
            "argv": [str(x) for x in (argv if isinstance(argv, (list, tuple)) else [argv])],
            "cwd": normalize_path(cwd) if cwd else "",
            "purpose": str(purpose or ""),
            "state": "running",
            "started_at": time.time(),
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        data, _ = self._store_obj().update_runtime(
            lambda d: d.setdefault("processes", []).append(rec), writer="pes.process_ledger"
        )
        return rec

    def finish(self, pid: int, exit_code: Optional[int] = None) -> bool:
        hit = {"n": 0}

        def _mut(d):
            for r in d.get("processes", []):
                if r.get("pid") == int(pid) and r.get("state") == "running":
                    r["state"] = "exited"
                    r["exit_code"] = exit_code
                    r["ended_at"] = time.time()
                    hit["n"] += 1

        self._store_obj().update_runtime(_mut, writer="pes.process_ledger")
        return hit["n"] > 0

    @staticmethod
    def alive(pid: int) -> bool:
        """进程是否仍在（不依赖 psutil）。"""
        pid = int(pid)
        if pid <= 0:
            return False
        if os.name == "nt":
            try:
                out = _proc_xh.run_hidden(
                    ["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
                )
                return ("%d" % pid) in (out.stdout or "")
            except Exception:
                return False
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    def reap_orphans(self) -> List[Dict[str, Any]]:
        """结清「台账 running 但进程已不在」的条目。"""
        orphans: List[Dict[str, Any]] = []

        def _mut(d):
            for r in d.get("processes", []):
                if r.get("state") == "running" and not self.alive(r.get("pid", 0)):
                    r["state"] = "reaped"
                    r["ended_at"] = time.time()
                    orphans.append(dict(r))

        self._store_obj().update_runtime(_mut, writer="pes.process_ledger")
        return orphans

    def running(self) -> List[Dict[str, Any]]:
        d = (self._store_obj().read().data or {})
        return [r for r in d.get("processes", []) if r.get("state") == "running"]


# ============================== PowerShell 门禁 ==============================
#: 硬拒命令（破坏性/越权），**不降级、不提示、直接拒**
_HARD_DENY = (
    "rm -rf /", "rm -rf /*", "format ", "diskpart", "cipher /w",
    "vssadmin delete", "bcdedit", "takeown /f c:", "icacls c:",
    "del /f /s /q c:", "rd /s /q c:", ":(){", "shutdown /",
    "reg delete hklm", "net user", "sc delete", "wmic shadowcopy delete",
)

#: 需要「老板级」确认的动词（写/发/改/花）
_GATED_VERBS = (
    "remove-item", "del ", "rmdir", "rm ", "move-item", "mv ",
    "set-content", "out-file", "add-content", "new-item",
    "git push", "git commit", "pip install", "npm install", "npm i ",
    "start-process", "invoke-webrequest", "curl ", "wget ",
    "schtasks", "reg add", "set-itemproperty",
)


def shell_guard(command: str, shell: str = "powershell") -> Dict[str, Any]:
    """PowerShell 命令**逐条过门**（总任务书第四章：可回放、不静默降级、危险硬拒）。

    返回 ``{"decision": "allow"|"ask"|"deny", "reason": str, "verb": str}``。
    **fail-closed**：识别不出意图时给 ``ask``，绝不给 ``allow``。
    """
    cmd = str(command or "")
    low = " " + cmd.lower().replace("\\", "/") + " "
    for bad in _HARD_DENY:
        if bad in low:
            return {"decision": "deny", "reason": "危险命令硬拒：命中 `%s`" % bad, "verb": bad}
    # 不静默降级到 shell：显式调用 cmd.exe / powershell -c 视为降级请求 ⇒ 需门
    for marker in ("cmd.exe", "cmd /c", "powershell -c", "pwsh -c", "bash -c", "sh -c", "wsl "):
        if marker in low:
            return {
                "decision": "ask",
                "reason": "疑似 shell 降级/跨环境调用（`%s`）⇒ 需老板级确认" % marker,
                "verb": marker,
            }
    for verb in _GATED_VERBS:
        if verb in low:
            return {"decision": "ask", "reason": "写/发/改/花类动词 `%s` 需过门" % verb, "verb": verb}
    return {"decision": "allow", "reason": "只读或无副作用", "verb": ""}


__all__ = [
    "REPO_ROOT",
    "SANDBOX_REL",
    "VAULT_REL",
    "BROWSER_ISOLATION",
    "WSL_BOUNDARY",
    "normalize_path",
    "same_path",
    "long_path",
    "join_under",
    "classify_path",
    "is_sandbox_repo",
    "is_real_repo",
    "is_wsl_path",
    "ProcessLedger",
    "shell_guard",
]
