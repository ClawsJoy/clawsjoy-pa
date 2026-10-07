# -*- coding: utf-8 -*-
"""供应商密钥之「写」口（唯一 · pm_1613 令四之后端半 · 技术总监席 f202f89 · 2026-10-07）。

承 —— 「更新通道 ＝ 安全面」「密钥唯落本机唯一处」「界面唯布尔」「⛔ 值入屏」。

本模块 ＝ **唯二事**：
  1. 密钥之 落 / 清 —— 唯落 config/.env（本机唯一处 · 承 core.lib.local_env_files.ENV_REL）；
     ⛔ 回值（唯布尔 ＋ 面之辞）；⛔ 入日志。
  2. 一次性令牌之仓（页首载所领 · 用即焚）—— 唯内存 · ⛔ 落盘。

守（硬）：
  * ⛔ 值入屏 / 入日志 / 入回执 —— 本模块凡出「面」皆布尔 ＋ 辞（承 core/pa/mailer.py 之形）。
  * 值之净：⛔ 换行 / ⛔ 回车 / ⛔ NUL（免「一行变多行」之注入）。
  * 境覆盖（测用）：env PA_ENV_FILE 指其件；缺 ⇒ <root>/config/.env。
"""
import os
import re
import secrets
import threading
import time
from pathlib import Path

TOKEN_COOKIE = "pa_key_token"          # 一次性令牌之 Cookie 名（HttpOnly · ⛔ 值上屏）
TOKEN_TTL_S = 180                      # 令牌之寿（秒）
TOKEN_PATH = "/v9/pa/providers/key"    # Cookie 之 Path（覆盖领 / 用二端）

_LOCK = threading.Lock()
_TOKENS = {}   # token -> {"exp": ts}


def root_dir():
    """装根（测用 env PA_ENV_ROOT 覆盖）—— ⛔ 按 CWD（承 mailer 「⛔ 按 CWD」之律）。"""
    v = (os.environ.get("PA_ENV_ROOT") or "").strip()
    if v:
        return Path(v)
    return Path(__file__).resolve().parents[2]


def env_path():
    """密钥之落件 —— env PA_ENV_FILE ⇒ 缺 ⇒ <root>/config/.env（一处定形）。"""
    v = (os.environ.get("PA_ENV_FILE") or "").strip()
    if v:
        return Path(v)
    from core.lib.local_env_files import ENV_REL
    return root_dir().joinpath(*ENV_REL.split("/"))


def clean_value(value):
    """值之净 ⇒ (ok, 值 | 拒之由)。⛔ 空 · ⛔ 换行 / 回车 / NUL。"""
    s = str(value if value is not None else "").strip()
    if not s:
        return False, "空值（清钥 ⇒ 传 key=null）"
    for _bad, _name in ((chr(10), "换行"), (chr(13), "回车"), (chr(0), "NUL")):
        if _bad in s:
            return False, "值含" + _name + "（⛔ 一行变多行）"
    return True, s


def _is_env_name(name):
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(name or "")))


def _line_key(line):
    """其行之 env 名（⛔ 得 ⇒ None；认 export 前缀 / 认 # 注释）。"""
    s = str(line or "").strip()
    if s.startswith("export "):
        s = s[7:].strip()
    if not s or s.startswith("#") or "=" not in s:
        return None
    return s.split("=", 1)[0].strip()


def _read_lines(path):
    """逐行（缺 ⇒ [] · ⛔ 崩 —— 承 local_env_files 之律）。"""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            return f.read().splitlines()
    except (IOError, OSError):
        return []


def _write_lines(path, lines):
    p = Path(path)
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(chr(10).join(lines) + chr(10))


def set_key(env_name, value):
    """落键（换 / 加）⇒ (ok, 面)。面为辞 · ⛔ 值。"""
    name = str(env_name or "").strip()
    if not _is_env_name(name):
        return False, "env 名非法（唯 [A-Za-z_][A-Za-z0-9_]*）"
    ok, val = clean_value(value)
    if not ok:
        return False, val
    p = env_path()
    out, done = [], False
    for ln in _read_lines(p):
        if _line_key(ln) == name:
            if not done:
                out.append(name + "=" + val)
                done = True
            continue                      # 重复行 ⇒ 归一为一行
        out.append(ln)
    if not done:
        out.append(name + "=" + val)
    _write_lines(p, out)
    os.environ[name] = val                # 立即生效（本进程之镜 · 落处仍唯此件）
    return True, {"件": str(p), "操": "set", "行数": len(out)}


def clear_key(env_name):
    """清键（删其行）⇒ (ok, 面)。"""
    name = str(env_name or "").strip()
    if not _is_env_name(name):
        return False, "env 名非法（唯 [A-Za-z_][A-Za-z0-9_]*）"
    p = env_path()
    lines = _read_lines(p)
    out = [ln for ln in lines if _line_key(ln) != name]
    _write_lines(p, out)
    os.environ.pop(name, None)
    return True, {"件": str(p), "操": "clear", "行数": len(out)}


# ---- 一次性令牌（页首载所领 · 用即焚 · 唯内存）----
def _prune_locked(now):
    for k in [k for k, v in _TOKENS.items() if v.get("exp", 0) <= now]:
        _TOKENS.pop(k, None)


def issue_token(ttl_s=TOKEN_TTL_S):
    """领一枚新令牌 ⇒ (token, ttl)。⛔ 入屏 / 入日志（调用方唯置 Cookie）。"""
    tok = secrets.token_hex(32)
    now = time.time()
    with _LOCK:
        _prune_locked(now)
        _TOKENS[tok] = {"exp": now + float(ttl_s)}
    return tok, float(ttl_s)


def consume_token(tok, now=None):
    """用即焚 ⇒ (ok, 由)。⛔ 得 / 过期 / 已用 ⇒ False（由为辞 · ⛔ 值）。"""
    now = now if now is not None else time.time()
    t = str(tok or "").strip()
    if not t:
        return False, "缺一次性令牌（先 GET /v9/pa/providers/key/token）"
    with _LOCK:
        _prune_locked(now)
        rec = _TOKENS.pop(t, None)
    if rec is None:
        return False, "令牌⛔认（过期 | 已用 ⇒ 重领）"
    if rec["exp"] <= now:
        return False, "令牌已过期（重领）"
    return True, ""


def reset_tokens():
    """（测用）清空令牌仓。"""
    with _LOCK:
        _TOKENS.clear()
