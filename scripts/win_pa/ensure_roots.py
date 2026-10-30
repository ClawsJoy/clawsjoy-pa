# -*- coding: utf-8 -*-
r"""ensure_roots.py -- 安装期「三根 junction」之唯一出处（PA 9.0.14 P0-2）。

病（一手 · 2026-10-28 · docs/71）：9.0.13 装后壳虽起、/health 200，但 gateway 仍向
  装根写 payload\logs\engine.log ／ payload\data\{v8,v9,users,vector_kb,...}
  ⇒ Program Files / 普通用户装根只读 ⇒ 装级复测 FAIL。

法：安装器于装根内立三 junction（装根保持只读）：
  <root>\logs -> %LOCALAPPDATA%\ClawsJoyPA\logs
  <root>\data -> %LOCALAPPDATA%\ClawsJoyPA\data
  <root>\vec  -> %LOCALAPPDATA%\ClawsJoyPA\vec
⇒ 凡「相对装根」之写（含尚未改成绝对根者）皆落用户级目录。

纪律：
  1. 目标目录只在 base 之下；卸载只解 junction，**⛔ 删目标**（data 在目标里）。
  2. 已有真目录 ⇒ 先迁其内容入目标（合并；同名冲突 ⇒ 源件改名为 <name>.from_install_<stamp>，两侧皆留），
     再立 junction。
  3. 幂等：junction 已指对 ⇒ no-op；错 link ⇒ 只解 link 再立（⛔ 动目标）；非目录之件 ⇒ 报因 ⛔ 删。
  4. 失败 fail-loud（人话之因）；但 **⛔ 阻安装**（调用方以 rc ＋ 日志记之，安装继续）。
  5. 本器 **唯标准库**（净机之载 runtime 可跑）。

用法（由 NSIS customInstall ／ installer_post.py 调）：
  python -X utf8 -B ensure_roots.py ensure [--root <装根>] [--base <目录>] [--log-file <文件>] [--dry-run]
  python -X utf8 -B ensure_roots.py verify [...]
  python -X utf8 -B ensure_roots.py remove [...]      # 卸载：只解 junction（⛔ 删目标）
退出码：0 成 ／ 2 红 ／ 3 入口错
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

#: 三根（**一处定形**）：(名, 装根内之子径) —— 目标子径同名（base\<名>）
ROOTS = (
    (u"logs", u"logs"),
    (u"data", u"data"),
    (u"vec", u"vec"),
)
COMPANY_DIR = u"ClawsJoyPA"
LOG_NAME = u"ensure_roots.log"

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def script_root():
    r"""本器所在之装根：<root>\scripts\win_pa\ensure_roots.py ⇒ <root>。"""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def default_base(env=None):
    r"""三根之父 ⇒ %LOCALAPPDATA%\ClawsJoyPA（⛔ 装根）。"""
    e = os.environ if env is None else env
    la = (e.get(u"LOCALAPPDATA") or u"").strip()
    if not la:
        up = (e.get(u"USERPROFILE") or u"").strip()
        la = os.path.join(up, u"AppData", u"Local") if up else u""
    if not la:
        home = os.path.expanduser(u"~")
        la = os.path.join(home, u".local", u"share") if home and home != u"~" else os.path.join(
            os.environ.get(u"TEMP") or u".", u"ClawsJoyPA-local")
    return os.path.join(la, COMPANY_DIR)


def plan(root=None, base=None, env=None):
    u"""三根之计划（⛔ 动盘）⇒ [{name, link, target}]。"""
    r = os.path.abspath(root or script_root())
    b = os.path.abspath(base or default_base(env))
    out = []
    for name, sub in ROOTS:
        out.append({u"name": name,
                    u"link": os.path.join(r, sub),
                    u"target": os.path.join(b, sub)})
    return out


def _is_junction(p):
    try:
        return bool(os.path.isjunction(p))          # Python 3.12+
    except AttributeError:                          # pragma: no cover -- 旧解释器兜底
        try:
            return bool(os.path.islink(p)) and os.path.isdir(p)
        except OSError:
            return False
    except OSError:
        return False


def _strip_target(t):
    for pre in (u"\\\\?\\", u"\\??\\"):
        if t.startswith(pre):
            t = t[len(pre):]
    return t


def junction_target(p):
    u"""junction 之实指（归一 · ⛔ 解链）；非 junction ⇒ None。"""
    if not _is_junction(p):
        return None
    try:
        return os.path.abspath(os.path.normpath(_strip_target(os.readlink(p))))
    except OSError:
        return None


def classify(p):
    u"""一个装根内之件之态：missing ／ junction ／ dir ／ file。"""
    if not os.path.lexists(p):
        return u"missing"
    if _is_junction(p):
        return u"junction"
    if os.path.isdir(p):
        return u"dir"
    return u"file"


def _same(a, b):
    if not a or not b:
        return False
    return os.path.normcase(os.path.abspath(os.path.normpath(a))) == \
        os.path.normcase(os.path.abspath(os.path.normpath(b)))


def make_junction(link, target):
    u"""mklink /J（junction · ⛔ 须管理员）⇒ (ok, 原文)。"""
    parent = os.path.dirname(link)
    try:
        if parent:
            os.makedirs(parent, exist_ok=True)
    except OSError as e:
        return False, u"父目录 ⛔ 立：%s" % e
    if os.name != u"nt":
        return False, u"非 Windows ⇒ ⛔ 立 junction"
    try:
        r = subprocess.run([u"cmd", u"/c", u"mklink", u"/J", link, target],
                           capture_output=True, text=True, encoding=u"utf-8",
                           errors=u"replace")
    except OSError as e:
        return False, u"mklink ⛔ 跑：%s" % e
    txt = ((r.stdout or u"") + (r.stderr or u"")).strip().replace(u"\r", u" ").replace(u"\n", u" ")
    return r.returncode == 0, txt


def remove_junction(link):
    u"""只解 junction（⛔ 删目标）⇒ (ok, 原文)。"""
    if classify(link) != u"junction":
        return False, u"非 junction（⛔ 动）"
    try:
        os.rmdir(link)                              # 删 reparse point，⛔ 递归 ⇒ 目标不动
        return True, u"已解"
    except OSError as e:
        try:
            r = subprocess.run([u"cmd", u"/c", u"rmdir", link], capture_output=True,
                               text=True, encoding=u"utf-8", errors=u"replace")
            if r.returncode == 0:
                return True, u"已解（cmd rmdir）"
            return False, u"解 junction ⛔ 得：%s" % ((r.stderr or r.stdout or u"").strip() or e)
        except OSError as e2:
            return False, u"解 junction ⛔ 得：%s" % e2


def migrate_dir(src, dst, stamp=None):
    u"""真目录 src 迁入 dst（合并）⇒ 迁之记；迁毕 src 须为空且被删（供立 junction）。"""
    stamp = stamp or time.strftime(u"%Y%m%d_%H%M%S")
    os.makedirs(dst, exist_ok=True)
    rows = []
    for name in sorted(os.listdir(src)):
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if not os.path.lexists(d):
            shutil.move(s, d)
            rows.append(u"迁 %s" % name)
        else:
            alt = os.path.join(dst, u"%s.from_install_%s" % (name, stamp))
            shutil.move(s, alt)
            rows.append(u"迁 %s ⇒ %s（目标已有同名 · 两侧皆留）" % (name, os.path.basename(alt)))
    try:
        os.rmdir(src)                               # 唯空目录可删（⛔ 递归）
    except OSError as e:
        raise RuntimeError(u"源目录迁后 ⛔ 空（%s）⇒ ⛔ 立 junction（目标未动）" % e)
    return rows


def _log_writer(log_path):
    u"""日志：追加到 log_path（父目录立之）；亦印屏。⛔ 无 log_path ⇒ 唯印屏。"""
    rows = []

    def put(line):
        rows.append(line)
        try:
            print(line)
        except Exception:
            pass
        if not log_path:
            return
        try:
            d = os.path.dirname(os.path.abspath(log_path))
            if d:
                os.makedirs(d, exist_ok=True)
            with open(log_path, u"a", encoding=u"utf-8") as fh:
                fh.write(u"%s %s\n" % (time.strftime(u"%Y-%m-%dT%H:%M:%S"), line))
        except OSError:
            pass
    put.rows = rows
    return put


def ensure(root=None, base=None, env=None, log_path=None, dry_run=False):
    u"""立 ／ 正 ／ 迁三根 ⇒ (ok, rows, log_path)。幂等；失败逐根报因（⛔ 抛）。"""
    rows = []
    log = _log_writer(log_path)
    ok_all = True
    stamp = time.strftime(u"%Y%m%d_%H%M%S")
    log(u"[roots] ensure root=%s base=%s dry=%s" % (os.path.abspath(root or script_root()),
                                                   os.path.abspath(base or default_base(env)), bool(dry_run)))
    for item in plan(root=root, base=base, env=env):
        link, target = item[u"link"], item[u"target"]
        state = classify(link)
        try:
            if state == u"junction":
                cur = junction_target(link)
                if _same(cur, target) and os.path.isdir(target):
                    rows.append(u"[PASS] %s 已指 %s" % (item[u"name"], target))
                    log(u"[roots] %s junction 已对 ⇒ no-op" % item[u"name"])
                    continue
                if dry_run:
                    rows.append(u"[DRY] %s junction 错指（%s ⇒ %s）" % (item[u"name"], cur, target))
                    log(u"[roots] %s dry：将解旧 link 再立" % item[u"name"])
                    continue
                rok, rwhy = remove_junction(link)
                if not rok:
                    ok_all = False
                    rows.append(u"[FAIL] %s 旧 junction ⛔ 解：%s" % (item[u"name"], rwhy))
                    log(u"[roots] FAIL %s %s" % (item[u"name"], rwhy))
                    continue
            elif state == u"dir":
                if dry_run:
                    rows.append(u"[DRY] %s 真目录 ⇒ 将迁内容入 %s 再立 junction" % (item[u"name"], target))
                    log(u"[roots] %s dry：将迁真目录入目标" % item[u"name"])
                    continue
                try:
                    moved = migrate_dir(link, target, stamp)
                except (OSError, RuntimeError) as e:
                    ok_all = False
                    rows.append(u"[FAIL] %s 迁 ⛔ 得：%s" % (item[u"name"], e))
                    log(u"[roots] FAIL %s 迁：%s" % (item[u"name"], e))
                    continue
                log(u"[roots] %s 真目录已迁 %d 件 ⇒ 将立 junction" % (item[u"name"], len(moved)))
            elif state == u"file":
                ok_all = False
                rows.append(u"[FAIL] %s 是非目录之件（⛔ 删 · 人工处置）：%s" % (item[u"name"], link))
                log(u"[roots] FAIL %s 非目录" % item[u"name"])
                continue
            if dry_run:
                rows.append(u"[DRY] %s 将立 junction %s -> %s" % (item[u"name"], link, target))
                log(u"[roots] %s dry：将立 junction" % item[u"name"])
                continue
            try:
                os.makedirs(target, exist_ok=True)
            except OSError as e:
                ok_all = False
                rows.append(u"[FAIL] %s 目标目录 ⛔ 立（%s）：%s" % (item[u"name"], target, e))
                log(u"[roots] FAIL %s 目标：%s" % (item[u"name"], e))
                continue
            mok, mwhy = make_junction(link, target)
            if not mok:
                ok_all = False
                rows.append(u"[FAIL] %s junction ⛔ 立（%s）：%s" % (item[u"name"], link, mwhy))
                log(u"[roots] FAIL %s %s" % (item[u"name"], mwhy))
                continue
            chk = junction_target(link)
            if not _same(chk, target):
                ok_all = False
                rows.append(u"[FAIL] %s junction 立后 ⛔ 对（得 %s）" % (item[u"name"], chk))
                log(u"[roots] FAIL %s 立后 ⛔ 对" % item[u"name"])
                continue
            rows.append(u"[PASS] %s junction %s -> %s" % (item[u"name"], link, target))
            log(u"[roots] %s junction 立成" % item[u"name"])
        except Exception as e:                      # noqa: BLE001 -- 照实报因 · ⛔ 阻安装
            ok_all = False
            rows.append(u"[FAIL] %s 异常：%s: %s" % (item[u"name"], type(e).__name__, e))
            log(u"[roots] FAIL %s %s: %s" % (item[u"name"], type(e).__name__, e))
    log(u"[roots] ensure %s" % (u"PASS" if ok_all else u"FAIL"))
    return ok_all, rows, log_path


def verify(root=None, base=None, env=None, log_path=None):
    u"""三根之核（唯读）⇒ (ok, rows, log_path)。"""
    rows = []
    log = _log_writer(log_path)
    ok_all = True
    for item in plan(root=root, base=base, env=env):
        state = classify(item[u"link"])
        if state != u"junction":
            ok_all = False
            rows.append(u"[FAIL] %s 非 junction（%s）：%s" % (item[u"name"], state, item[u"link"]))
            log(u"[roots] verify FAIL %s 非 junction" % item[u"name"])
            continue
        cur = junction_target(item[u"link"])
        if not _same(cur, item[u"target"]):
            ok_all = False
            rows.append(u"[FAIL] %s 指错（得 %s ⇒ 应 %s）" % (item[u"name"], cur, item[u"target"]))
            log(u"[roots] verify FAIL %s 指错" % item[u"name"])
            continue
        if not os.path.isdir(item[u"target"]):
            ok_all = False
            rows.append(u"[FAIL] %s 目标不在：%s" % (item[u"name"], item[u"target"]))
            log(u"[roots] verify FAIL %s 目标不在" % item[u"name"])
            continue
        rows.append(u"[PASS] %s -> %s" % (item[u"name"], item[u"target"]))
        log(u"[roots] verify %s PASS" % item[u"name"])
    log(u"[roots] verify %s" % (u"PASS" if ok_all else u"FAIL"))
    return ok_all, rows, log_path


def remove(root=None, base=None, env=None, log_path=None):
    u"""卸载：只解 junction（⛔ 删目标；真目录 ⛔ 动）⇒ (ok, rows, log_path)。"""
    rows = []
    log = _log_writer(log_path)
    ok_all = True
    for item in plan(root=root, base=base, env=env):
        state = classify(item[u"link"])
        if state == u"junction":
            rok, rwhy = remove_junction(item[u"link"])
            if not rok:
                ok_all = False
                rows.append(u"[FAIL] %s junction ⛔ 解：%s" % (item[u"name"], rwhy))
                log(u"[roots] remove FAIL %s %s" % (item[u"name"], rwhy))
            else:
                rows.append(u"[PASS] %s junction 已解（目标保留：%s）" % (item[u"name"], item[u"target"]))
                log(u"[roots] remove %s 已解" % item[u"name"])
        elif state == u"dir":
            rows.append(u"[SKIP] %s 是真目录（⛔ 删 · 保数据）：%s" % (item[u"name"], item[u"link"]))
            log(u"[roots] remove SKIP %s 真目录" % item[u"name"])
        elif state == u"file":
            rows.append(u"[SKIP] %s 是非目录之件（⛔ 删）" % item[u"name"])
            log(u"[roots] remove SKIP %s 非目录" % item[u"name"])
        else:
            rows.append(u"[SKIP] %s 不在 ⇒ no-op" % item[u"name"])
            log(u"[roots] remove %s missing" % item[u"name"])
    log(u"[roots] remove %s" % (u"PASS" if ok_all else u"FAIL"))
    return ok_all, rows, log_path


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"action", nargs=u"?", default=u"ensure",
                    choices=[u"ensure", u"verify", u"remove"], help=u"ensure(default) ／ verify ／ remove")
    ap.add_argument(u"--root", default=u"", help=u"装根（缺省 ＝ 本器所在装根）")
    ap.add_argument(u"--base", default=u"", help=u"三根之父（缺省 %%LOCALAPPDATA%%\\ClawsJoyPA）")
    ap.add_argument(u"--log-file", default=u"", help=u"日志（缺省 <base>\\logs\\ensure_roots.log）")
    ap.add_argument(u"--dry-run", action=u"store_true")
    ap.add_argument(u"--json", action=u"store_true")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root) if a.root else script_root()
    base = os.path.abspath(a.base) if a.base else default_base()
    log_path = a.log_file or os.path.join(base, u"logs", LOG_NAME)
    if a.action == u"verify":
        ok, rows, _lp = verify(root=root, base=base, log_path=log_path)
    elif a.action == u"remove":
        ok, rows, _lp = remove(root=root, base=base, log_path=log_path)
    else:
        ok, rows, _lp = ensure(root=root, base=base, log_path=log_path, dry_run=a.dry_run)
    if a.json:
        print(json.dumps({u"ok": bool(ok), u"action": a.action, u"root": root, u"base": base,
                          u"log": log_path, u"rows": rows}, ensure_ascii=False, indent=2))
    else:
        print(u"[ensure_roots] action=%s root=%s base=%s ⇒ %s" % (
            a.action, root, base, u"PASS" if ok else u"FAIL"))
        for x in rows:
            print(u"  " + x)
    return 0 if ok else 2


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))
