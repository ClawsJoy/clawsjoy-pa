# -*- coding: utf-8 -*-
u"""DSH 专用凭据（P2-2）：与 PA provider key 分开存放/传递。

- 存储：<PA_DATA_DIR>/dsh.env（可用 PA_DSH_ENV_FILE 覆盖）；
- 变量：PA_DSH_DEEPSEEK_API_KEY（只在 PA → DSH 子进程时映射为 DEEPSEEK_API_KEY）；
- PA 自己的 DEEPSEEK_API_KEY 不再传给 DSH；
- 只回布尔，不回值。
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_NAME = "PA_DSH_DEEPSEEK_API_KEY"


def _path():
    p = os.getenv("PA_DSH_ENV_FILE")
    if p:
        return Path(p)
    return Path(os.getenv("PA_DATA_DIR", "data/v9/pa")) / "dsh.env"


def _clean(value):
    s = str(value if value is not None else "").strip()
    if not s:
        return False, "空值"
    for bad, name in ((chr(10), "换行"), (chr(13), "回车"), (chr(0), "NUL")):
        if bad in s:
            return False, "值含" + name
    if any(ord(c) > 127 or c.isspace() for c in s):
        return False, "含非 ASCII 或空白字符（API key 只应有英数/减号）"
    return True, s


def get_key():
    u"""取 DSH 专用 key（env 优先；否则读 dsh.env）；不回显。"""
    v = (os.getenv(ENV_NAME) or "").strip()
    if v:
        return v
    p = _path()
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith(ENV_NAME + "="):
                return s.split("=", 1)[1].strip()
    except Exception:
        return ""
    return ""


def state():
    return {"configured": bool(get_key()), "env": ENV_NAME, "file": str(_path())}


def set_key(value):
    ok, val = _clean(value)
    if not ok:
        return False, val
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if p.is_file():
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines()
                 if not ln.strip().startswith(ENV_NAME + "=")]
    lines.append(ENV_NAME + "=" + val)
    p.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    os.environ[ENV_NAME] = val
    return True, {"file": str(p), "action": "set"}


def clear_key():
    os.environ.pop(ENV_NAME, None)
    p = _path()
    if p.is_file():
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines()
                 if not ln.strip().startswith(ENV_NAME + "=")]
        p.write_text(chr(10).join(lines) + (chr(10) if lines else ""), encoding="utf-8")
    return True, {"file": str(p), "action": "clear"}


def ensure_loaded():
    u"""若 env 未设而盘上有 DSH key ⇒ 载入进程 env（供子进程映射）。"""
    if (os.getenv(ENV_NAME) or "").strip():
        return
    k = get_key()
    if k:
        os.environ[ENV_NAME] = k
