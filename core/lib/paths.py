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