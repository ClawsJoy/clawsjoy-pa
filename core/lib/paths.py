# -*- coding: utf-8 -*-
"""跨平台路径解析（WSL ↔ Windows）。

背景：历史代码把 WSL 专用路径直接写成默认值：

  - Obsidian vault：``/mnt/d/Obsidian/ClawsJoy/ClawsJoy``
  - Playwright 浏览器缓存：``/mnt/d/whisper_cache/ms-playwright``
  - Windows 命令解释器：``/mnt/c/Windows/System32/cmd.exe``

在 Windows 副本上 ``/mnt/d/...`` 会被解析成「当前盘符下的 \\mnt\\d\\...」
（例如 ``D:\\mnt\\d\\Obsidian\\...``）—— 既不抛错、也找不到真实目录，
属于**静默写错位置**，比直接报错更难排查。

这里统一按平台解析，并保留环境变量覆盖能力：
``PA_VAULT_DIR`` / ``PLAYWRIGHT_BROWSERS_PATH`` / ``COMSPEC``。
"""
import os
import tempfile
from pathlib import Path

WSL_VAULT = "/mnt/d/Obsidian/ClawsJoy/ClawsJoy"
WIN_VAULT = "D:\\Obsidian\\ClawsJoy\\ClawsJoy"
WSL_BROWSERS = "/mnt/d/whisper_cache/ms-playwright"
WIN_BROWSERS = "D:\\whisper_cache\\ms-playwright"
WSL_CMD_EXE = "/mnt/c/Windows/System32/cmd.exe"
WIN_CMD_EXE = "C:\\Windows\\System32\\cmd.exe"

IS_WINDOWS = os.name == "nt"


def _first_existing(*candidates):
    """返回第一个真实存在的目录，全都不存在时返回 None。"""
    for candidate in candidates:
        if candidate and Path(str(candidate)).is_dir():
            return str(candidate)
    return None


def vault_root():
    """Obsidian vault 根目录。优先 PA_VAULT_DIR，其次探测 WSL/Windows 实际路径。"""
    env = os.environ.get("PA_VAULT_DIR")
    if env:
        return Path(env)
    found = _first_existing(WSL_VAULT, WIN_VAULT)
    if found:
        return Path(found)
    return Path(WIN_VAULT if IS_WINDOWS else WSL_VAULT)


def _win_default_browsers():
    """Playwright 在 Windows 上的**自带默认**缓存：``%LOCALAPPDATA%\\ms-playwright``。

    ``D:\\whisper_cache\\ms-playwright`` 是从 WSL 带过来的缓存，里面只有
    ``*-linux64`` 构建；Windows 要用 ``*-win64``，所以默认优先用本地这一份。
    """
    base = os.environ.get("LOCALAPPDATA")
    return str(Path(base) / "ms-playwright") if base else None


def playwright_browsers_path():
    """Playwright chromium 缓存目录（决定 "Executable doesn't exist" 是否出现）。"""
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env:
        return env
    if IS_WINDOWS:
        # Windows 侧：先本地默认（真正的 win64 构建）→ D: 缓存 → WSL 缓存
        found = _first_existing(_win_default_browsers(), WIN_BROWSERS, WSL_BROWSERS)
        return found or _win_default_browsers() or WIN_BROWSERS
    found = _first_existing(WSL_BROWSERS, WIN_BROWSERS)
    return found or WSL_BROWSERS


def cmd_exe():
    """Windows 命令解释器；WSL 侧走 /mnt/c interop，Windows 侧用 COMSPEC。"""
    if IS_WINDOWS:
        return os.environ.get("COMSPEC") or WIN_CMD_EXE
    return WSL_CMD_EXE


def runtime_tmp_dir():
    """宿主**运行时临时根目录**（带 clawsjoy 命名空间）。

    为什么需要它：历史代码把 Linux 临时目录写死成 ``/tmp/...``。Windows 上
    ``/tmp/x`` 会解析成 ``<当前盘符>:\\tmp\\x``（本机 ``D:\\tmp`` **不存在**）——
    不抛错、但写到别处（**静默写错位置**，比报错更难排查）。

    **WSL 侧行为零变化**：``tempfile.gettempdir()`` 在 Linux/WSL 上就是 ``/tmp``
    （故本函数在 WSL 返回 ``/tmp/clawsjoy``，与既有语义同域），Windows 侧是 ``%TEMP%``。
    覆盖：``PA_RUNTIME_TMP``。
    """
    env = os.environ.get("PA_RUNTIME_TMP")
    base = Path(env) if env else Path(tempfile.gettempdir()) / "clawsjoy"
    # 目录不存在时创建（幂等）；只读/受限环境下静默降级，不因临时目录不可建而中断
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return base


def runtime_tmp_path(*parts):
    """``runtime_tmp_dir()`` 下的一个路径，**返回正斜杠字符串**。

    为什么返回正斜杠：这些路径会经 JSON / 工具参数传给 agent 再回传
    （如 ``write_finalize(temp_path=...)``），**反斜杠在 JSON 与模型回抄时容易被吞**。
    Windows API（``open`` / ``Path``）接受正斜杠。
    """
    return runtime_tmp_dir().joinpath(*[str(x) for x in parts]).as_posix()


def map_linux_tmp(path):
    """把外部（文本 / agent 给出）的 ``/tmp/...`` 映射到宿主运行时临时目录；其它原样返回。

    只映射**前缀**，不改写其余内容。POSIX 侧 ``/tmp/x`` 与 ``runtime_tmp_dir()/x``
    本来就是同一处 ⇒ 本函数在 WSL 上是**恒等映射**；Windows 侧把 ``D:\\tmp\\x``
    这类误写纠正到真实位置。
    """
    p = str(path or "")
    if not p.startswith("/tmp/"):
        return p
    return runtime_tmp_path(p[len("/tmp/"):])


def to_host_path(path):
    """把外部传入的路径规整为**本机可用**的路径。

    WSL：``C:\\Users\\x`` -> ``/mnt/c/Users/x``（interop 需要挂载形式）
    Windows：``/mnt/c/Users/x`` -> ``C:\\Users\\x``，其余原样返回
    """
    p = str(path or "").strip()
    if not p:
        return p
    p = p.replace("\\", "/")

    if IS_WINDOWS:
        # /mnt/<drive>/... -> <DRIVE>:/...
        if p.startswith("/mnt/") and len(p) > 6 and p[6] == "/":
            return "%s:/%s" % (p[5].upper(), p[7:])
        if len(p) > 2 and p[1] == ":":
            return p[0].upper() + p[1:]
        return p

    # POSIX（WSL）：<drive>:/... -> /mnt/<drive>/...
    if len(p) > 2 and p[1] == ":" and p[2] == "/":
        return "/mnt/%s/%s" % (p[0].lower(), p[3:])
    return p