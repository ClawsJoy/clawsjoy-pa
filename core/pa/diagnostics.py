# -*- coding: utf-8 -*-
u"""一键打包诊断（**唯落本机 · ⛔ 出机** · 承 pm_1634 §二.2 · 技术总监席 f202f89 · 2026-10-07）。

由（pm_1634 §一.2）：内测之痛 ＝「净机取日志难」⇒ 须**一键**出一包（用户自行复制 ∨ 贴入板）
  ⇒ ⛔ 自动上传（⛔ 出站请求）。
脱敏（**铁律** · 承 pm_1634 §一.2 ＋ §三.3）：
  * 包中**⛔ 含**：`config/.env` ／ `config/secrets*` ／ 密钥之值 ／ 画像 ／ 台账 ／ 会话内容 ／
    知识库正文 ／ 用户数据（`data/`）。
  * 取法 ＝ **白名单**（唯五源）：`version.json` 之真读数 ｜ 装根**顶级清单**（名 ＋ 字节 · ⛔ 内容）｜
    日志之**尾**（有界 ＋ 脱敏）｜`/health` 之快照 ｜ 环境摘要 ⇒ **⛔ 递归取件 ∧ ⛔ 取用户数据**。
  * 其证 ＝ 哨兵（密钥之值入环境 ＋ 入日志）⇒ 齿「⛔ 在包」（承 pm_1634 §三.3）。
"""
from __future__ import annotations

import io
import json
import os
import platform
import time
import zipfile

from core.lib import feedback_target as FT
from core.pa import feedback_store as FS

#: 日志尾之界（一处定形）—— ⛔ 全量（防包体失控 ∧ 防泄）
TAIL_LINES = 200
TAIL_BYTES = 96 * 1024
MAX_LOGS = 12
#: 装根顶级清单之界
MAX_ENTRIES = 400
#: 明确**⛔ 入包**之名（一处定形 —— 白名单之外，此为双保险之**点名**）
NEVER = (u".env", u"secrets", u"secrets.yaml", u"cookies", u"profile", u"画像", u"台账",
         u"session", u"memory", u"data")


def out_root(root=None, env=None):
    u"""包之落处（**一处定形**）：`%LOCALAPPDATA%\\ClawsJoyPA\\diag`（⛔ 入仓 ∧ ⛔ 入包之载荷）；
    无 `LOCALAPPDATA` ⇒ 回落 `<装根>/data/pa/diag`（仍本机 · ⛔ 出机）。"""
    env = os.environ if env is None else env
    la = (env.get(u"LOCALAPPDATA") or u"").strip()
    if la:
        return os.path.join(la, u"ClawsJoyPA", u"diag")
    return os.path.join(root or FT.root_dir(), u"data", u"pa", u"diag")


def _read_version(root):
    try:
        from core.lib import build_info                    # 一处定形（甲 ／ 己 之共骨）
        d, note = build_info.read(root)
        return (d or {}), (None if d else note)
    except Exception as e:                                  # noqa: BLE001 — 照实报因
        return {}, u"%s: %s" % (type(e).__name__, e)


def _root_listing(root, env):
    u"""装根之顶级清单（名 ＋ 字节 ＋ 刻）—— **⛔ 内容** ∧ ⛔ 递归；点名之件（NEVER）亦只列名。"""
    sen = FS.sentinels(env)
    rows = []
    try:
        names = sorted(os.listdir(root))
    except OSError as e:
        return [u"（装根 ⛔ 读：%s）" % e]
    for nm in names[:MAX_ENTRIES]:
        p = os.path.join(root, nm)
        try:
            st = os.stat(p)
            kind = u"<目录>" if os.path.isdir(p) else u"%d 字节" % st.st_size
            rows.append(u"%-42s %-14s %s" % (FS.scrub(nm, sen), kind,
                                             time.strftime(u"%Y-%m-%dT%H:%M", time.localtime(st.st_mtime))))
        except OSError:
            rows.append(u"%-42s <⛔ 读>" % FS.scrub(nm, sen))
    if len(names) > MAX_ENTRIES:
        rows.append(u"…（余 %d 件略 · 一处定形之界 MAX_ENTRIES=%d）" % (len(names) - MAX_ENTRIES, MAX_ENTRIES))
    return rows


def _log_tails(root, env):
    u"""日志之尾（有界 ＋ 脱敏）⇒ `[(名, 文)]`；**⛔ 整取**（唯 `logs/` 之 `.log` ／ `.log.N` ／ `.err`）。"""
    sen = FS.sentinels(env)
    d = os.path.join(root, u"logs")
    out = []
    if not os.path.isdir(d):
        return out
    cand = []
    for nm in os.listdir(d):
        if not nm.endswith((u".log", u".err")) and u".log." not in nm:
            continue
        p = os.path.join(d, nm)
        try:
            cand.append((os.path.getmtime(p), nm, p))
        except OSError:
            continue
    for _m, nm, p in sorted(cand, reverse=True)[:MAX_LOGS]:
        try:
            with io.open(p, u"rb") as fh:
                fh.seek(0, 2)
                sz = fh.tell()
                fh.seek(max(0, sz - TAIL_BYTES))
                raw = fh.read()
        except OSError as e:
            out.append((nm, u"（⛔ 读：%s）" % e))
            continue
        txt = raw.decode(u"utf-8", u"replace").splitlines()[-TAIL_LINES:]
        out.append((nm, FS.scrub(u"\n".join(txt), sen)))
    return out


def _env_summary(root, port=None, env=None):
    env = os.environ if env is None else env
    src = FT.load(root, env)
    rows = [u"刻            %s" % time.strftime(u"%Y-%m-%dT%H:%M:%S%z"),
            u"OS            %s %s（%s）" % (platform.system(), platform.release(), platform.version()),
            u"Python        %s" % platform.python_version(),
            u"装根（PA_HOME） %s" % root,
            u"CWD           %s" % os.getcwd(),
            u"CPU           %s（%s 核）" % (platform.processor(), os.cpu_count()),
            u"端口          %s" % (port if port is not None else u"（未传）"),
            u"更新通道       %s" % _update_channel(root, env),
            u"反馈落点       mode=%s channel=%s 出机=%s" % (src[u"mode"], src[u"channel"], src[u"outbound"]),
            u"提示           %s" % FT.notice(src)]
    try:
        import shutil as _sh
        t, u_, f = _sh.disk_usage(root)
        rows.append(u"磁盘          总 %.1f GB ／ 余 %.1f GB" % (u_ / 1073741824.0, f / 1073741824.0))
    except Exception:                                          # noqa: BLE001 — 照实略
        pass
    return rows


def _update_channel(root, env):
    try:
        from core.lib import update_source as US
        return US.load(root, env).get(u"channel") or u""
    except Exception:                                          # noqa: BLE001 — 照实略
        return u"（⛔ 读）"


README = u"""ClawsJoy PA 诊断包（**唯落本机** · ⛔ 已上传 · ⛔ 自动发送）
============================================================
内含（白名单 · 五源）：
  1. version.json     —— 当前版本之真读数（甲 ／ 己之共骨）
  2. 装根清单.txt     —— 装根**顶级**之名 ＋ 字节 ＋ 刻（⛔ 内容 ∧ ⛔ 递归）
  3. health.json      —— /health 之快照（真读数）
  4. 环境.txt         —— 系统 ／ Python ／ 端口 ／ 通道 ／ 磁盘 之摘要
  5. 日志/*.tail.txt  —— 日志之**尾**（有界 200 行 ／ 96 KB · 已脱敏）

**⛔ 不含**：`config/.env` ∧ 密钥之值 ∧ 画像 ∧ 台账 ∧ 会话内容 ∧ 知识库正文 ∧ `data/` 之用户数据。
（承「用户那台电脑才是 PA 的家」—— 本包须你**自己**决定是否交给客服席。）

怎么交？（内测期三途 · ⛔ 自动）
  * 直接贴到本机之留言板（附件）；或
  * 复制本包（自己选途：微信 ／ 邮件 ／ 局域网之分享面）；或
  * 告知客服席「包在哪」，由人工上门取。
"""


def build(root=None, health=None, port=None, out_root_dir=None, now=None, env=None):
    u"""打一包 ⇒ `(zip 之径, rows)`。**唯本机**（⛔ 出站 · ⛔ 上传 · 承 pm_1634 §二.2）。"""
    root = root or FT.root_dir()
    env = os.environ if env is None else env
    sen = FS.sentinels(env)
    fid = FS.new_id(now)
    dest = out_root_dir or out_root(root, env)
    os.makedirs(dest, exist_ok=True)
    zp = os.path.join(dest, u"%s_诊断包.zip" % fid)
    ver, vnote = _read_version(root)
    rows = [u"[diag] 打包 %s" % zp]
    health_doc = json.loads(json.dumps(health, ensure_ascii=False, default=str)) if health else None
    with zipfile.ZipFile(zp, u"w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(u"README.txt", README)
        z.writestr(u"version.json", json.dumps(ver, ensure_ascii=False, indent=1))
        z.writestr(u"装根清单.txt", u"\n".join(_root_listing(root, env)) + u"\n")
        z.writestr(u"health.json", json.dumps(FS.scrub(json.dumps(health_doc, ensure_ascii=False, indent=1), sen),
                                             ensure_ascii=False, indent=1) if health_doc is not None
                   else u"（⛔ 得 —— 未传健康快照）")
        z.writestr(u"环境.txt", u"\n".join(_env_summary(root, port, env)) + u"\n")
        n = 0
        for nm, txt in _log_tails(root, env):
            z.writestr(u"日志/%s.tail.txt" % nm, txt + u"\n")
            n += 1
        rows.append(u"    日志之尾 %d 件（各有界 %d 行 ／ %d KB）" % (n, TAIL_LINES, TAIL_BYTES // 1024))
        if vnote:
            rows.append(u"    ⚠ 版本之真读数之因：%s" % vnote)
    rows.append(u"    落 ＝ %s（%d 字节 · 唯本机 · ⛔ 上传）" % (zp, os.path.getsize(zp)))
    return zp, rows


def members(zp):
    u"""包中之名（供面之公示 ∧ 齿之证 —— 一处定形）。"""
    with zipfile.ZipFile(zp) as z:
        return sorted(z.namelist())


def source_scan(path=None):
    u"""结构齿（**一处定形** · 借 `feedback_store.source_scan`）：本模块 ⛔ 引网络之件。"""
    return FS.source_scan(path or os.path.abspath(__file__))
