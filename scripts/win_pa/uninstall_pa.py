# -*- coding: utf-8 -*-
u"""uninstall_pa.py -- 双击安装包之卸载器（承 pm_1577 §二.3 ⒝ · 「可卸 ＋ 明书留下何物」）。

位次：开始菜单「卸载 ClawsJoy PA」⇒ `卸载ClawsJoyPA.cmd` ⇒ 本器（**以自带之 runtime 跑**）。

所撤（逐条）：
  ⒜ 停服（**唯一入口** `pa_nowindow.py stop` · ⛔ 本器 ⛔ 另杀进程）
  ⒝ 快捷（开始菜单之子夹 ＋ 桌面之三件）
  ⒞ 「应用与功能」之卸载项（**HKCU** · ⛔ 系统级 ⇒ ⛔ 提权）
  ⒟ 二计划任务（**委** `uninstall_win_pa.py --go` —— 一处定形 · ⛔ 本器另删）
  ⒠ 程序件（`runtime/` ／ `core/` ／ `web/` ／ `scripts/` … ⇒ 经**派生之清理批**删 ——
     因 `python.exe` 自身被锁：本器退后由 detached cmd 删 ⇒ ⛔ 自删之病）

所留（**明书** · 承 pm_1577 §四.1「唯 data\\ 留」）：
  ⭐ `<装根>\\data\\`（你的资料与设置 ＋ 内置知识库骨架）—— 缺省**留**
  ⭐ `PA_VAULT_DIR`（若装时装过 ⇒ 那是**你选的库根** ⇒ 本器 ⛔ 撤 · 免误删主人之选）
  ⭐ `--purge` ⇒ 并删 `data\\`（彻底清干净）

三禁（承 pm_1382 §二.2 之族）：
  ⓐ 缺省干跑（先印「将撤何物」）· 唯 `--go` 方真撤
  ⓑ 幂等：已在 ⇒ 撤；不在 ⇒ 报「无物可撤」（rc 0 · ⛔ 崩）
  ⓒ ⛔ 触 `data/**`（除 `--purge`）· ⛔ 触系统级注册表 · ⛔ 停 ／ 改他实例

用法：
  python -X utf8 scripts\\win_pa\\uninstall_pa.py                # 干跑
  python -X utf8 scripts\\win_pa\\uninstall_pa.py --go           # 真撤（留 data\）
  python -X utf8 scripts\\win_pa\\uninstall_pa.py --go --purge   # 真撤（并删 data\）
  ... --root <装根> ｜ --json ｜ --self-test
退出码：0 正常（含「无物可撤」）｜ 2 有撤败 ｜ 3 入口错
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
VERSION = u"1.0"
KEEP = u"data"          # ⭐ 留下之物（**一名一义**）：装根下之子径名


def _ip():
    u"""安装之后置（**一处出**）：快捷之表 ＋ 卸载键之域 ⛔ 本器另写。"""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    return __import__(u"installer_post")


def runtime_exe(root):
    return os.path.join(root, u"runtime", u"python.exe")


def cleanup_text(root, purge=False):
    u"""派生之清理批（**一处定形**）—— `python.exe` 锁于装根 ⇒ 唯本器退后方可删。"""
    head = [u"@echo off",
            u"setlocal",
            u"rem 待本器（python.exe）退 —— ⛔ 以 timeout（重定向时不可用）⇒ 以 ping 延时",
            u"ping -n 4 127.0.0.1 >nul",
            u"cd /d \"%TEMP%\""]
    if purge:
        body = [u"rmdir /s /q \"" + root + u"\" >nul 2>&1"]
        tail = [u"echo [uninstall] 已彻底删：%s" % root]
    else:
        body = [u"for /d %%D in (\"" + root + u"\\*\") do (",
                u"  if /i not \"%%~nxD\"==\"" + KEEP + u"\" rmdir /s /q \"%%D\" >nul 2>&1",
                u")",
                u"del /q \"" + root + u"\\*\" >nul 2>&1"]
        tail = [u"echo [uninstall] 程序件已删。留下：%s" % os.path.join(root, KEEP),
                u"echo [uninstall] 彻底清干净（连资料）：rmdir /s /q \"" + root + u"\""]
    return u"\r\n".join(head + body + tail + [u"endlocal", u"del /q \"%~f0\" >nul 2>&1"]) + u"\r\n"


def plan(root, purge=False):
    ip = _ip()
    sm = ip.sm_dir()
    desk = ip.desk_dir()
    items = []
    items.append({"item": "service", "name": u"停服（pa_nowindow.py stop）", "live": True})
    for n, p in ip.shortcut_paths(True):
        items.append({"item": "shortcut", "name": p, "live": os.path.isfile(p)})
    items.append({"item": "registry", "name": u"HKCU" + BS + ip.UNINSTALL_KEY, "live": _reg_live(ip.UNINSTALL_KEY)})
    for v in (u"PA_VAULT_DIR",):
        items.append({"item": "env-keep", "name": u"HKCU" + BS + u"Environment" + BS + v, "live": None})
    items.append({"item": "files", "name": root,
                  "live": os.path.isdir(root),
                  "purge": bool(purge), "keep": ([] if purge else [KEEP])})
    items.append({"item": "note", "name": u"计划任务 ⇒ 委 uninstall_win_pa.py --go", "live": None})
    items.append({"item": "note", "name": u"sm=%s ／ desk=%s" % (sm, desk), "live": None})
    return items


def _reg_live(subkey):
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey)
        winreg.CloseKey(k)
        return True
    except Exception:
        return False


def _reg_delete(subkey):
    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)
        return 0
    except Exception:
        return 2


def do_shortcuts(dry):
    ip = _ip()
    rc = 0
    lines = []
    for _n, p in ip.shortcut_paths(True):
        if not os.path.isfile(p):
            lines.append(u"  [shortcut] %s -> 不在（无物可撤）" % p)
            continue
        lines.append(u"  [shortcut] %s -> 撤" % p)
        if not dry:
            try:
                os.remove(p)
            except Exception as e:
                lines.append(u"    ⛔ %s: %s" % (type(e).__name__, e))
                rc = 2
    sm = ip.sm_dir()
    if os.path.isdir(sm):
        left = os.listdir(sm)
        lines.append(u"  [shortcut] 开始菜单子夹 %s -> %s" % (sm, u"余 %s" % left if left else u"空 ⇒ 并撤"))
        if not dry and not left:
            try:
                os.rmdir(sm)
            except Exception as e:
                lines.append(u"    ⛔ %s: %s" % (type(e).__name__, e))
                rc = 2
    return rc, lines


def do_stop(root, dry):
    exe = runtime_exe(root)
    pn = os.path.join(root, u"scripts", u"win_pa", u"pa_nowindow.py")
    if not (os.path.isfile(exe) and os.path.isfile(pn)):
        return 0, [u"  [service] ⛔ 见 %s ⇒ 跳（无物可撤）" % pn]
    if dry:
        return 0, [u"  [service] %s -X utf8 %s stop（干跑 · ⛔ 未跑）" % (exe, pn)]
    r = subprocess.run([exe, u"-X", u"utf8", pn, u"stop"], capture_output=True, text=True,
                       encoding=u"utf-8", errors=u"replace", timeout=120)
    out = [l for l in ((r.stdout or u"") + (r.stderr or u"")).splitlines() if l.strip()]
    return (0 if r.returncode == 0 else 2), [u"  [service] rc=%s" % r.returncode] + [u"    " + x for x in out]


def do_tasks(root, dry):
    exe = runtime_exe(root)
    sc = os.path.join(root, u"scripts", u"win_pa", u"uninstall_win_pa.py")
    if not (os.path.isfile(exe) and os.path.isfile(sc)):
        return 0, [u"  [tasks] ⛔ 见 %s ⇒ 跳" % sc]
    cmd = [exe, u"-X", u"utf8", sc, u"--go"]
    if dry:
        return 0, [u"  [tasks] %s（干跑 · ⛔ 未跑）" % u" ".join(cmd)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding=u"utf-8", errors=u"replace",
                       timeout=120)
    out = [l for l in ((r.stdout or u"") + (r.stderr or u"")).splitlines() if l.strip()]
    return (0 if r.returncode == 0 else 2), [u"  [tasks] rc=%s" % r.returncode] + [u"    " + x for x in out]


def spawn_cleanup(root, purge):
    fd, path = tempfile.mkstemp(prefix=u"cjpa_uninst_", suffix=u".cmd")
    os.close(fd)
    with io.open(path, "w", encoding=u"utf-8", newline=u"") as fh:
        fh.write(cleanup_text(root, purge))
    DETACHED = 0x00000008
    NEWGRP = 0x00000200
    subprocess.Popen([u"cmd", u"/c", path], creationflags=DETACHED | NEWGRP,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     close_fds=True)
    return path


def render(root, purge, dry):
    items = plan(root, purge)
    lines = [u"[uninstall] 装根 ＝ %s（purge=%s）" % (root, purge)]
    lines.append(u"[uninstall] 将撤：")
    for i in items:
        if i["item"] == "note":
            lines.append(u"  (%s)" % i["name"])
        elif i["item"] == "env-keep":
            lines.append(u"  %-56s %s" % (i["name"], u"**留**（你选的库根 · ⛔ 误删）"))
        elif i["item"] == "files":
            lines.append(u"  %-56s %s（留 %s）" % (i["name"], u"在（将删）" if i["live"] else u"不在",
                                                u"无" if purge else KEEP))
        else:
            lines.append(u"  %-56s %s" % (i["name"], u"在（将撤）" if i["live"] else u"不在（无物可撤）"))
    rc = 0
    if dry:
        lines.append(u"[uninstall] 干跑（⛔ 未撤）—— --go 方真撤")
        return 0, lines
    _rc, _l = do_stop(root, dry)
    rc = rc or _rc
    lines += _l
    _rc, _l = do_shortcuts(dry)
    rc = rc or _rc
    lines += _l
    ip = _ip()
    if _reg_live(ip.UNINSTALL_KEY):
        lines.append(u"  [registry] HKCU" + BS + ip.UNINSTALL_KEY + u" -> 撤（rc=%s）" % _reg_delete(ip.UNINSTALL_KEY))
    else:
        lines.append(u"  [registry] HKCU" + BS + ip.UNINSTALL_KEY + u" -> 不在（无物可撤）")
    _rc, _l = do_tasks(root, dry)
    rc = rc or _rc
    lines += _l
    if os.path.isdir(root):
        p = spawn_cleanup(root, purge)
        lines.append(u"  [files] 清理批已派（本器退后删）：%s" % p)
        if purge:
            lines.append(u"  [files] 并删 %s（--purge ⇒ 连资料）" % os.path.join(root, KEEP))
        else:
            lines.append(u"  [files] 留：%s（你的资料与设置）" % os.path.join(root, KEEP))
    else:
        lines.append(u"  [files] %s -> 不在（无物可撤）" % root)
    lines.append(u"[uninstall] 留下：%s"
                 % (u"无（--purge）" if purge else (os.path.join(root, KEEP) + u"（**明书** · 承 pm_1577 §四.1）")))
    lines.append(u"[uninstall] 完 —— 本窗可关（清理批在后台跑约 3 秒）")
    return rc, lines


def self_test():
    fails = []
    hits = []

    def say(ok, name):
        hits.append(bool(ok))
        print(u"  %s %s" % (u"+" if ok else u"X", name))
        if not ok:
            fails.append(name)

    root = u"C:" + BS + u"__cjpa_nope__"
    txt = cleanup_text(root)
    say(u"ping -n 4" in txt, u"正控：清理批以 ping 延时（⛔ timeout —— 重定向时不可用）")
    say((u"%%~nxD\"==\"" + KEEP) in txt, u"正控：清理批**不删** %s\\（逐名比较）" % KEEP)
    say((chr(13) + chr(10) + u"rmdir /s /q " + chr(34) + root + chr(34)) not in txt, u"反控：⛔ 整根删（唯 --purge 方如此）")
    say(u"%~f0" in txt, u"正控：清理批自清（%~f0）")
    ptxt = cleanup_text(root, purge=True)
    say((chr(13) + chr(10) + u"rmdir /s /q " + chr(34) + root + chr(34)) in ptxt, u"正控：--purge ⇒ 整根删（连 data）")
    rc, ln = render(root, False, True)
    say(rc == 0 and any(u"干跑" in x for x in ln), u"正控：缺省干跑 ⇒ rc 0")
    say(not os.path.isdir(root), u"反控：干跑 ⛔ 动盘")
    say(any(u"**留**" in x for x in ln), u"正控：库根键入「留」之列（⛔ 误删主人之选）")
    ip = _ip()
    say(ip.UNINSTALL_KEY.startswith(u"Software" + BS + u"Microsoft"), u"正控：卸载键之域")
    say(u"winreg.HKEY_CURRENT_USER" in io.open(__file__, encoding=u"utf-8").read(),
        u"正控：注册表唯用户级（winreg.HKEY_CURRENT_USER）")
    src = io.open(__file__, encoding=u"utf-8").read()
    say((u"HKEY_" + u"LOCAL_" + u"MACHINE") not in src and (u"HK" + u"LM") not in src,
        u"反控：源 ⛔ 含系统级域（⛔ 提权）")
    say(u"pa_nowindow.py" in src and u"uninstall_win_pa.py" in src,
        u"正控：停服 ／ 任务皆**委**既有之唯一入口（⛔ 本器另杀 ／ 另删）")
    print(u"=== uninstall_pa 自测 %d/%d ===" % (sum(hits), len(hits)))
    print(u"[self-test] %s" % (u"PASS" if not fails else u"FAIL"))
    for f in fails:
        print(u"  [FAIL] %s" % f)
    return 0 if not fails else 2


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--root", default=u"")
    ap.add_argument(u"--go", action=u"store_true")
    ap.add_argument(u"--purge", action=u"store_true")
    ap.add_argument(u"--json", action=u"store_true")
    ap.add_argument(u"--self-test", action=u"store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    root = os.path.abspath(a.root) if a.root else ROOT
    dry = not a.go
    rc, lines = render(root, a.purge, dry)
    if a.json:
        print(json.dumps({"version": VERSION, "dry_run": dry, "purge": a.purge, "root": root,
                          "rc": rc, "items": plan(root, a.purge), "lines": lines},
                         ensure_ascii=False, indent=2))
    else:
        for x in lines:
            print(x)
    return rc


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))