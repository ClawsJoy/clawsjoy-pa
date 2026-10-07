# -*- coding: utf-8 -*-
u"""反馈 ／ 求助之「落点声明」（**一处定形** · 承 pm_1634 §二.4 ＋ §二.3 · 技术总监席 f202f89 · 2026-10-07）。

由（PM 一手 · pm_1634 §〇）：老板批「增加留言板，先用局域网内测，但是客服 Agent 需要跟上」
  ⇒ 内测期之板 **唯落本机**（⛔ 出机）∧ 将来接公网中转 ⇒ **唯换「发送」一处**
  ⇒ 故「落点」须**可配 ∧ ⛔ 写死**（与 `update_source.yaml` 同族之形 · 共用之骨）。

形（唯四键 · **一处定形**）：
  mode      `local`（内测 · 默认 ⇒ 唯落本机 · **⛔ 任何网络发送**）｜`relay`（将来之公网中转 · ⛔ P0）
  dir       收件目录（相对装根 ⇒ 换机可携 · 拟 `data/pa/feedback`）
  channel   通道（`internal` ／ 后 `beta` ／ `stable`）—— 与更新源同族之值
  relay_url 中转之址（`mode=relay` 方用 · P0 恒空）
优先序（一处定形 · 与 `update_source` 同）：env ⇒ 文件 `config/feedback_target.yaml` ⇒ 内置默认；
  **逐键报其出**（`origin`）—— 承「凡源须可配 ∧ 切源 ⛔ 须重出包」。
⚠ **⛔ 出网**（本模块唯「读声明」—— ⛔ 送件 ∧ ⛔ 取件）；`outbound()` ＝ 面之「⛔ 出机」之**唯一判据**。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_feedback_1634.py -q
"""
from __future__ import annotations

import ast
import io
import os

from core.lib.update_source import _mini_yaml                    # 一处定形（同一「极简键值」之解）

#: 声明之相对径（**一处定形**）—— 居 `config/`（与 update_source.yaml 同族 ∧ **入包**）
FILENAME = u"config/feedback_target.yaml"

DEFAULT_MODE = u"local"
DEFAULT_DIR = u"data/pa/feedback"
DEFAULT_CHANNEL = u"internal"
DEFAULT_RELAY = u""

MODES = (u"local", u"relay")
KEYS = (u"mode", u"dir", u"channel", u"relay_url")
ENV = {u"mode": u"PA_FEEDBACK_MODE", u"dir": u"PA_FEEDBACK_DIR",
       u"channel": u"PA_FEEDBACK_CHANNEL", u"relay_url": u"PA_FEEDBACK_RELAY_URL"}
_DEFAULT = {u"mode": DEFAULT_MODE, u"dir": DEFAULT_DIR,
            u"channel": DEFAULT_CHANNEL, u"relay_url": DEFAULT_RELAY}

#: 逐项勾选之项（**一处定形** —— `feedback_store` 唯借此处 · ⛔ 二处各写）：
#: **默认全 ⛔ 勾**（承 pm_1634 §二.1 ＋ 红线四条「⛔ 默认带」）。
CONSENT_BUSES = (u"health", u"logs", u"env", u"diag")

#: 面之常驻提示（**一处定形** —— 面（web）唯取此字 · ⛔ 自撰 · 承 pm_1634 §三.1）
NOTICE_LOCAL = u"内测版：留言只存在你这台机器上（⛔ 出机 · ⛔ 联网发送）—— 去处：我们上门取 ∨ 你可以自己复制给我们"
NOTICE_RELAY = u"留言将送到我方之收件端（仅你勾选之内容）"


def root_dir():
    u"""装根 ／ 仓根（**一处定形**）：本档 ＝ `<根>/core/lib/feedback_target.py` ⇒ 上溯三。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def path(root=None):
    return os.path.join(root or root_dir(), FILENAME)


def _from_file(root):
    u"""文件之四键 ⇒ `(dict, note)`；未见 ／ 坏 ⇒ `({}, 因)`（⛔ 静默 · 承「真读数」）。"""
    p = path(root)
    if not os.path.isfile(p):
        return {}, u"未见 %s" % FILENAME
    try:
        import io
        text = io.open(p, encoding=u"utf-8-sig").read()
    except Exception as e:                                        # noqa: BLE001 — 照实报因
        return {}, u"%s 读取败：%s: %s" % (FILENAME, type(e).__name__, e)
    d = None
    try:
        import yaml                                               # type: ignore
        d = yaml.safe_load(text)
    except Exception:                                             # noqa: BLE001 — 无 yaml ⇒ 回落
        d = None
    if not isinstance(d, dict):
        d = _mini_yaml(text)
    if not isinstance(d, dict):
        return {}, u"%s ⛔ 解（唯平表「键: 值」）" % FILENAME
    return {k: d.get(k) for k in KEYS if d.get(k) not in (None, u"")}, u""


def load(root=None, env=None):
    u"""落点之「一处出」⇒ `{mode, dir, channel, relay_url, origin, file, note, outbound}`。"""
    env = os.environ if env is None else env
    fd, fnote = _from_file(root)
    out, origin = {}, {}
    for k in KEYS:
        e = (env.get(ENV[k]) or u"").strip()
        if e:
            out[k] = e
            origin[k] = u"env:%s" % ENV[k]
        elif fd.get(k) not in (None, u""):
            out[k] = str(fd[k])
            origin[k] = u"file:%s" % FILENAME
        else:
            out[k] = _DEFAULT[k]
            origin[k] = u"default"
    if out[u"mode"] not in MODES:
        fnote = (fnote + u"；" if fnote else u"") + u"mode 非常（%s —— 唯 local ／ relay）" % out[u"mode"]
    out[u"origin"] = origin
    out[u"file"] = path(root)
    out[u"note"] = fnote
    out[u"outbound"] = outbound(out)
    return out


def outbound(src):
    u"""**⛔ 出机之唯一判据**（一处定形）：`mode=relay` ∧ 有 http(s) 之 `relay_url` ⇒ True。
    内测（`mode=local` ／ 默认）⇒ **恒 False** ⇒ 面之「发送」**⛔ 得**出站（承 pm_1634 §三.2）。
    """
    if (src or {}).get(u"mode") != u"relay":
        return False
    u = str((src or {}).get(u"relay_url") or u"").strip()
    return bool(u.startswith(u"http://") or u.startswith(u"https://"))


def notice(src=None):
    u"""面之常驻提示（一处定形 · ⛔ 自撰）：`local` ⇒ 「唯在本机」；`relay` ⇒ 「将送出」。"""
    return NOTICE_RELAY if outbound(src if src is not None else load()) else NOTICE_LOCAL


def feedback_dir(root=None, src=None):
    u"""收件目录之绝对径（**一处定形**）—— `dir` 为相对时挂装根。"""
    d = str((src or load(root)).get(u"dir") or DEFAULT_DIR)
    return d if os.path.isabs(d) else os.path.join(root or root_dir(), d)


#: 「⛔ 出机」之结构齿（**一处定形** —— `feedback_store` ／ `diagnostics` 皆唯借此处）：
#: 本系（声明 ／ 收件 ／ 诊断包）之源码**⛔ 引**网络之件（承 pm_1634 §三.2）。
BANNED_MODULES = (u"socket", u"urllib", u"urllib2", u"urllib3", u"requests", u"httpx", u"http",
                  u"ftplib", u"smtplib", u"telnetlib", u"asyncio", u"websockets")


def source_scan(path=None):
    u"""源码之扫 ⇒ `(ok, hits)`：⛔ 引网络之件（⛔ 静默 —— 命中即点名其行）。"""
    p = path or os.path.abspath(__file__)
    src = io.open(p, encoding=u"utf-8").read()
    hits = []
    for n in ast.walk(ast.parse(src)):
        mods = []
        if isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods = [n.module]
        for m in mods:
            if m.split(u".")[0] in BANNED_MODULES:
                hits.append(u"%s:%d %s" % (os.path.basename(p), n.lineno, m))
    return (not hits), hits


def face(root=None, env=None):
    u"""**面之读数**（一处定形 · 承 pm_1640 §一.2 之律「**读一处（`/health`）· 动分端（`/v9/pa/*`）**」）
    ⇒ 唯 `/health.feedback` 与 `/v9/pa/feedback/target`（运维 ／ 机器）**同借此处** ⇒ ⛔ 二处各写其形。
    ⚠ 「面之读数」之正统之处 ＝ **`/health`**；`/v9/pa/*` 者唯**动作**（POST）。本函 ⛔ 出网 · ⛔ 副作用。
    """
    src = load(root, env)
    return {"mode": src[u"mode"], "channel": src[u"channel"], "dir": src[u"dir"],
            "outbound": src[u"outbound"], "notice": notice(src),
            "resolved_dir": feedback_dir(root, src), "origin": src[u"origin"],
            "consent_buses": list(CONSENT_BUSES), "note": src[u"note"]}


def report(root=None):
    u"""自检之逐行（⛔ 静默 · 承「凡读须可查」）。"""
    src = load(root)
    rows = [u"[feedback_target] %s" % path(root),
            u"    mode = %s（出 %s）｜dir = %s｜channel = %s" % (
                src[u"mode"], src[u"origin"][u"mode"], src[u"dir"], src[u"channel"]),
            u"    出机（outbound）＝ %s  ⇒ 面之提示：%s" % (src[u"outbound"], notice(src)),
            u"    收件目录 ＝ %s" % feedback_dir(root, src)]
    if src[u"note"]:
        rows.append(u"    ⚠ %s" % src[u"note"])
    return rows
