# -*- coding: utf-8 -*-
u"""installer_post.py -- 「双击即装」之后置（承 pm_1577 §二 ／ §三 · 老板裁 ⒞）。

位次：`ClawsJoyPA-Setup.exe`（iexpress 自解压）⇒ 解包入 `%TEMP%\\IXP*.TMP` ⇒ 跑 `install_pa.cmd`
     ⇒ `tar -xf payload.zip` 入装根 ⇒ 调本器 ⇒ ⒜ 立目录 ⒝ 三快捷（开始菜单 ＋ 桌面）
     ⒞ 注册「应用与功能」之卸载项（**HKCU** · ⛔ 须管理员） ⒟ 落安装记录（含包之源） ⒠ 报 ＋ 自检。

一条铁律（承 pm_1577 §二裁一）：**净机 ⛔ 有 Python** ⇒ 本器恒以**自带之 runtime**
  （`<装根>\\runtime\\python.exe`）跑 —— 其「净机之代」之要（⛔ 借系统之 python）。
  故本器**唯用标准库**（⛔ flask ／ ⛔ yaml ／ ⛔ pip ／ ⛔ 起服）。

一处定形（⛔ 二源）：
  ⭐ 立目录之表 ＝ `install_win_pa.dir_items()`（含 `data/kb` 之六骨架 · 承 note_kernel）
  ⭐ 端口之真源 ＝ `core.lib.port_config.gateway_port()`（⛔ 本器另写字面 —— 唯启动器引之）
  ⭐ 起停之唯一入口 ＝ `scripts/win_pa/pa_nowindow.py`（⛔ 本器 ⛔ 另起）

用法（常规由 install_pa.cmd 调）：
  <装根>\\runtime\\python.exe -X utf8 <装根>\\scripts\\win_pa\\installer_post.py --go [--dest <装根>]
  ... --dry（缺省）｜ --json ｜ --self-test ｜ --no-desktop ｜ --no-shortcuts
退出码：0 成 ｜ 2 败 ｜ 3 入口错
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
VERSION = u"1.0"

APP_ID = u"ClawsJoyPA"
DISPLAY_NAME = u"ClawsJoy PA（PA 网关 · 本地）"
PUBLISHER = u"ClawsJoy"
UNINSTALL_KEY = BS.join((u"Software", u"Microsoft", u"Windows", u"CurrentVersion", u"Uninstall", APP_ID))
# ⚠ 拆写（免「自查之字面自指」之假红）：本是杀器之域，本器 ⛔ 触
_SYSREG_A = u"HKEY_" + u"LOCAL_" + u"MACHINE"
_SYSREG_B = u"HK" + u"LM"

LAUNCH_START = u"启动ClawsJoyPA.cmd"
LAUNCH_STOP = u"停止ClawsJoyPA.cmd"
LAUNCH_OPEN = u"打开ClawsJoyPA页面.cmd"
LAUNCH_UNINSTALL = u"卸载ClawsJoyPA.cmd"

#: 三快捷（**一源**）：(显示名, 指向之件, 说明) —— 开始菜单与桌面同此三者
SHORTCUTS = (
    (u"启动 ClawsJoy PA", LAUNCH_START, u"起 PA 网关（无窗）"),
    (u"停止 ClawsJoy PA", LAUNCH_STOP, u"停 PA 网关"),
    (u"打开 ClawsJoy PA 页面", LAUNCH_OPEN, u"在默认浏览器开 PA 页面"),
)
#: 开始菜单另加「卸载」（发现性 · ⛔ 桌面）
SM_EXTRA = ((u"卸载 ClawsJoy PA", LAUNCH_UNINSTALL, u"卸载（data\\ 保留）"),)


class _Sink(io.StringIO):
    u"""收杂记之池（core 之 config 于导入期向 stdout 打数行）—— ⚠ 须容忍 reconfigure。"""

    def reconfigure(self, *a, **k):
        return None


def runtime_exe(root):
    return os.path.join(root, u"runtime", u"python.exe")


def _iw():
    u"""安装器（**一处出**）：立目录之表 ⛔ 本器另写。"""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    return __import__(u"install_win_pa")


def plan_dirs(dest):
    u"""将立之目录（**一处定形**）—— 名字取 `install_win_pa.dir_items()`（含 `data/kb` 之六骨架），
    路径一律挂在给定之**装根**之下（⛔ 用模块自己的 ROOT —— 那在源树里跑会把目录立到仓里）。"""
    iw = _iw()
    out = []
    for d in iw.dir_items():
        rel = os.path.relpath(d[u"abs"], iw.ROOT)
        out.append(os.path.join(dest, rel))
    return out


def default_dest():
    u"""装根之默认：`%LOCALAPPDATA%\\ClawsJoyPA`（**用户级** ⇒ ⛔ UAC · ⛔ 管理员）。"""
    la = os.environ.get(u"LOCALAPPDATA") or os.path.join(os.path.expanduser(u"~"), u"AppData", u"Local")
    return os.path.join(la, APP_ID)


def _head():
    return (u"@echo off\r\n"
            u"setlocal EnableExtensions\r\n"
            + u"rem ⭐ 装根由 %~dp0 定位 ⇒ 整根可移（承 pm_1577 · 一处定形）\r\n"
            + u"set \"ROOT=%~dp0\"\r\n"
            + u"if \"%ROOT:~-1%\"==\"" + BS + u"\" set \"ROOT=%ROOT:~0,-1%\"\r\n"
            + u"cd /d \"%ROOT%\"\r\n")


def launcher_texts():
    u"""四启动器之逐字（**一源**）—— 皆以 `%~dp0` 定位 ⇒ 装根可移；皆走唯一入口 `pa_nowindow.py`。"""
    head = _head()
    py = u"\"%ROOT%" + BS + u"runtime" + BS + u"python.exe\""
    pn = u"\"%ROOT%" + BS + u"scripts" + BS + u"win_pa" + BS + u"pa_nowindow.py\""
    start = (head
             + u"echo [PA] 起服务（无窗）…… 首启约 30 秒\r\n"
             + py + u" -X utf8 " + pn + u" start\r\n"
             + u"set \"RC=%ERRORLEVEL%\"\r\n"
             + u"if not \"%RC%\"==\"0\" echo [PA] 起服失败 rc=%RC% —— 因见上之数行\r\n"
             + u"if not \"%RC%\"==\"0\" pause\r\n"
             + u"endlocal & exit /b %RC%\r\n")
    stop = (head
            + py + u" -X utf8 " + pn + u" stop\r\n"
            + u"set \"RC=%ERRORLEVEL%\"\r\n"
            + u"endlocal & exit /b %RC%\r\n")
    # ⚠ Python 之一行 ⛔ 用 `%` 格式化（批处理 `for /f` 会吞之）⇒ 以 `+` 拼
    openp = (head
             + u"set \"URL=\"\r\n"
             + u"for /f \"usebackq delims=\" %%U in (`" + py
             + u" -X utf8 -c \"import sys;sys.path.insert(0,r'%ROOT%');"
             + u"from core.lib.port_config import gateway_port;"
             + u"print('http://127.0.0.1:'+str(gateway_port())+'/web/pa.html')\"`) do set \"URL=%%U\"\r\n"
             + u"if not defined URL set \"URL=http://127.0.0.1:5103/web/pa.html\"\r\n"
             + u"start \"\" \"%URL%\"\r\n"
             + u"endlocal & exit /b 0\r\n")
    uninst = (head
              + py + u" -X utf8 \"%ROOT%" + BS + u"scripts" + BS + u"win_pa" + BS
              + u"uninstall_pa.py\" --go --root \"%ROOT%\"\r\n"
              + u"set \"RC=%ERRORLEVEL%\"\r\n"
              + u"pause\r\n"
              + u"endlocal & exit /b %RC%\r\n")
    return {LAUNCH_START: start, LAUNCH_STOP: stop, LAUNCH_OPEN: openp, LAUNCH_UNINSTALL: uninst}


def write_launchers(root, dry=False):
    rows = []
    for name, text in launcher_texts().items():
        p = os.path.join(root, name)
        rows.append(u"  [launcher] %s" % p)
        if not dry:
            with io.open(p, "w", encoding="utf-8", newline=u"") as fh:
                fh.write(text)
    return rows


def _ps_quote(s):
    return u"'" + str(s).replace(u"'", u"''") + u"'"


def sm_dir():
    appdata = os.environ.get(u"APPDATA") or u""
    return os.path.join(appdata, u"Microsoft", u"Windows", u"Start Menu", u"Programs", APP_ID)


def desk_dir():
    return os.path.join(os.path.expanduser(u"~"), u"Desktop")


def shortcut_paths(desktop=True):
    u"""(名, 径) 之表 —— 开始菜单之子夹（三 ＋ 卸载）＋ 桌面（三 · 可关）。"""
    spec = SHORTCUTS + SM_EXTRA
    out = [(n, os.path.join(sm_dir(), n + u".lnk")) for n, _t, _d in spec]
    if desktop:
        out += [(n, os.path.join(desk_dir(), n + u".lnk")) for n, _t, _d in SHORTCUTS]
    return out


def make_shortcuts(root, desktop=True, dry=False):
    u"""三快捷（＋「卸载」入开始菜单）—— 以 WScript.Shell（⛔ 第三方依）。"""
    ps = [u"$sh = New-Object -ComObject WScript.Shell"]
    spec = {n: (t, d) for n, t, d in (SHORTCUTS + SM_EXTRA)}
    rows = []
    for name, lnk in shortcut_paths(desktop):
        target, desc = spec[name]
        rows.append(u"  [shortcut] %s -> %s" % (lnk, target))
        if dry:
            continue
        os.makedirs(os.path.dirname(lnk), exist_ok=True)
        ps.append(u"$s = $sh.CreateShortcut(%s)" % _ps_quote(lnk))
        ps.append(u"$s.TargetPath = %s" % _ps_quote(os.path.join(root, target)))
        ps.append(u"$s.WorkingDirectory = %s" % _ps_quote(root))
        ps.append(u"$s.Description = %s" % _ps_quote(desc))
        ps.append(u"$s.IconLocation = %s" % _ps_quote(runtime_exe(root) + u",0"))
        ps.append(u"$s.Save()")
    if dry:
        return rows
    fd, ps1 = tempfile.mkstemp(prefix=u"cjpa_lnk_", suffix=u".ps1")
    os.close(fd)
    try:
        with io.open(ps1, "w", encoding="utf-8") as fh:
            fh.write(u"\r\n".join(ps) + u"\r\n")
        r = subprocess.run([u"powershell", u"-NoProfile", u"-NonInteractive",
                            u"-ExecutionPolicy", u"Bypass", u"-File", ps1],
                           capture_output=True, text=True, encoding=u"utf-8", errors=u"replace")
        if r.returncode != 0:
            rows.append(u"  [shortcut] ⛔ 败 rc=%s：%s" % (r.returncode, (r.stderr or u"")[-300:]))
    finally:
        try:
            os.remove(ps1)
        except Exception:
            pass
    return rows


def uninstall_values(root):
    u"""卸载项之逐键（**一源**）—— 域 ＝ HKCU（⛔ 系统级 ⇒ ⛔ 提权）。"""
    return [
        (u"DisplayName", u"REG_SZ", DISPLAY_NAME),
        (u"DisplayVersion", u"REG_SZ", VERSION),
        (u"Publisher", u"REG_SZ", PUBLISHER),
        (u"InstallLocation", u"REG_SZ", root),
        (u"DisplayIcon", u"REG_SZ", runtime_exe(root)),
        (u"UninstallString", u"REG_SZ", u"\"" + os.path.join(root, LAUNCH_UNINSTALL) + u"\""),
        (u"QuietUninstallString", u"REG_SZ", u"\"" + os.path.join(root, LAUNCH_UNINSTALL) + u"\""),
        (u"NoModify", u"REG_DWORD", 1),
        (u"NoRepair", u"REG_DWORD", 1),
    ]


def register_uninstall(root, dry=False):
    vals = uninstall_values(root)
    rows = [u"  [registry] HKCU" + BS + UNINSTALL_KEY]
    rows += [u"    %s = %s" % (k, v) for k, _t, v in vals]
    if dry:
        return rows
    import winreg
    key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_WRITE)
    try:
        for k, t, v in vals:
            winreg.SetValueEx(key, k, 0, winreg.REG_SZ if t == u"REG_SZ" else winreg.REG_DWORD, v)
    finally:
        winreg.CloseKey(key)
    return rows


def source_stamp(root):
    u"""包之源（**取自包内之册** —— `bundle_manifest.json` 之「源」键 · 承 pm_1573 §二）。"""
    p = os.path.join(root, u"bundle_manifest.json")
    try:
        man = json.loads(io.open(p, encoding=u"utf-8").read())
    except Exception as e:
        return {u"册": u"⛔ 读不到（%s: %s）" % (type(e).__name__, e)}
    return {u"册": os.path.relpath(p, root), u"源": man.get(u"源") or u"⛔ 无「源」键"}


def preflight(root):
    u"""起服前自检（**唯一出处** ＝ `preflight_start.py`）⇒ (rc, 数行)。⛔ 本器另判。"""
    exe = runtime_exe(root)
    sc = os.path.join(root, u"scripts", u"win_pa", u"preflight_start.py")
    if not os.path.isfile(exe) or not os.path.isfile(sc):
        return 3, [u"⛔ 见 %s ∨ %s" % (exe, sc)]
    r = subprocess.run([exe, u"-X", u"utf8", sc, u"--root", root],
                       capture_output=True, text=True, encoding=u"utf-8", errors=u"replace",
                       timeout=180)
    out = [l for l in ((r.stdout or u"") + (r.stderr or u"")).splitlines() if l.strip()]
    return r.returncode, out


def plan(dest, desktop=True, shortcuts=True):
    return {
        u"version": VERSION,
        u"dest": dest,
        u"runtime": runtime_exe(dest),
        u"dirs": plan_dirs(dest),
        u"launchers": sorted(launcher_texts()),
        u"shortcuts": ([p for _n, p in shortcut_paths(desktop)] if shortcuts else []),
        u"registry": u"HKCU" + BS + UNINSTALL_KEY,
        u"source": source_stamp(dest),
    }


def render_and_maybe_apply(p, dry, do_shortcuts=True):
    dest = p[u"dest"]
    lines = [u"[install_post] 装根 ＝ %s（**用户级** · ⛔ 须管理员）" % dest]
    if not os.path.isdir(dest):
        lines.append(u"[install_post] ⛔ 见装根 ⇒ **⛔ 装**（先解 `payload.zip`）")
        return 2, lines
    if not os.path.isfile(p[u"runtime"]):
        lines.append(u"[install_post] ⛔ 见自带运行时：%s ⇒ **⛔ 装**" % p[u"runtime"])
        return 2, lines
    lines.append(u"[install_post] 自带运行时：%s（**净机 ⛔ 有 Python** 之要）" % p[u"runtime"])
    todo = [d for d in p[u"dirs"] if not os.path.isdir(d)]
    lines.append(u"[install_post] 将立目录 %d 件（已在 %d ⇒ no-op）" % (len(todo), len(p[u"dirs"]) - len(todo)))
    if not dry:
        for d in list(p[u"dirs"]):
            os.makedirs(d, exist_ok=True)
    lines += [u"  [dir] %s" % os.path.relpath(d, dest) for d in p[u"dirs"]]
    lines += write_launchers(dest, dry)
    if do_shortcuts:
        lines += make_shortcuts(dest, desktop=bool(p[u"shortcuts"]), dry=dry)
    else:
        lines.append(u"  [shortcut] ⛔ 本轮跳过（--no-shortcuts）")
    lines += register_uninstall(dest, dry)
    lines.append(u"[install_post] 报源：%s" % json.dumps(p[u"source"], ensure_ascii=False))
    if dry:
        lines.append(u"[install_post] 干跑（⛔ 未动）—— --go 方真做")
        return 0, lines
    rec = dict(p, installed_at=time.strftime(u"%Y-%m-%dT%H:%M:%S%z"))
    rec[u"source"] = source_stamp(dest)
    with io.open(os.path.join(dest, u"install_record.json"), "w", encoding="utf-8", newline=u"") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, indent=1))
    lines.append(u"[install_post] 安装记录：%s" % os.path.join(dest, u"install_record.json"))
    prc, plines = preflight(dest)
    lines.append(u"[install_post] 起服前自检 rc=%s（**唯一出处** preflight_start.py）" % prc)
    lines += [u"    " + x for x in plines]
    if prc != 0:
        lines.append(u"[install_post] ⚠ 自检 ⛔ 全过 ⇒ **装已成**，然起服会拒 ⇒ 先按其因修")
    lines.append(u"[install_post] 成。双击「启动 ClawsJoy PA」起服；卸载：开始菜单 ⇒ 卸载 ClawsJoy PA")
    return 0, lines


def self_test():
    fails = []
    hits = []

    def say(ok, name):
        hits.append(bool(ok))
        print(u"  %s %s" % (u"+" if ok else u"X", name))
        if not ok:
            fails.append(name)

    lt = launcher_texts()
    say(set(lt) == {LAUNCH_START, LAUNCH_STOP, LAUNCH_OPEN, LAUNCH_UNINSTALL}, u"正控：四启动器之名齐")
    for n, t in lt.items():
        say((u"runtime" + BS + u"python.exe") in t, u"正控：%s 走**自带之 runtime**（⛔ 系统 python）" % n)
        say(u"%~dp0" in t, u"正控：%s 以 %%~dp0 定位（装根可移）" % n)
    say(u"pa_nowindow.py" in lt[LAUNCH_START] and u" start" in lt[LAUNCH_START],
        u"正控：启动器走**唯一入口** pa_nowindow.py start")
    say(u"pa_nowindow.py" in lt[LAUNCH_STOP] and u" stop" in lt[LAUNCH_STOP],
        u"正控：停止器走**唯一入口** pa_nowindow.py stop")
    say(u"port_config" in lt[LAUNCH_OPEN], u"正控：打开页面之端口取自**真源** port_config（⛔ 字面）")
    say(u"uninstall_pa.py" in lt[LAUNCH_UNINSTALL], u"正控：卸载器走 uninstall_pa.py")
    say(UNINSTALL_KEY.startswith(u"Software" + BS + u"Microsoft"), u"正控：卸载键之域")
    say((_SYSREG_A not in UNINSTALL_KEY) and (_SYSREG_B not in UNINSTALL_KEY),
        u"正控：卸载键为**用户级**（⛔ 系统级 ⇒ ⛔ 提权）")
    say(len(SHORTCUTS) == 3, u"正控：三快捷（启动 ／ 停止 ／ 打开页面）")
    d = default_dest()
    say(d.lower().endswith(BS + u"clawsjoypa"), u"正控：默认装根 = LOCALAPPDATA 之实 ⇒ %s" % d)
    say(len(shortcut_paths(True)) == 7 and len(shortcut_paths(False)) == 4,
        u"反控：--no-desktop ⇒ 唯开始菜单（4 ＝ 三 ＋ 卸载）")
    say(all(u"Desktop" not in p for _n, p in shortcut_paths(False)), u"反控：关桌面 ⇒ 桌面无快捷")
    p = plan(u"C:" + BS + u"__nope__", desktop=False)
    say(not os.path.isdir(u"C:" + BS + u"__nope__"), u"反控：plan 唯读（⛔ 动盘）")
    rc, ln = render_and_maybe_apply(plan(u"C:" + BS + u"__nope__"), True)
    say(rc == 2 and any(u"⛔ 装" in x for x in ln), u"反控：装根 ⛔ 在 ⇒ rc 2 ∧ 报「⛔ 装」")
    src = io.open(__file__, encoding=u"utf-8").read()
    say((_SYSREG_A not in src) and (_SYSREG_B not in src), u"反控：源 ⛔ 含系统级域")
    say((u"rm" + u"tree") not in src, u"反控：源 ⛔ 含删树（卸载归 uninstall_pa）")
    say(u"vec" + u"tor_kb" not in src, u"反控：源 ⛔ 自造知识库子径字面（唯引内核）")
    print(u"=== installer_post 自测 %d/%d ===" % (sum(hits), len(hits)))
    print(u"[self-test] %s" % (u"PASS" if not fails else u"FAIL"))
    for f in fails:
        print(u"  [FAIL] %s" % f)
    return 0 if not fails else 2


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--dest", default=u"")
    ap.add_argument(u"--go", action=u"store_true")
    ap.add_argument(u"--dry", action=u"store_true")
    ap.add_argument(u"--json", action=u"store_true")
    ap.add_argument(u"--no-desktop", action=u"store_true")
    ap.add_argument(u"--no-shortcuts", action=u"store_true")
    ap.add_argument(u"--self-test", action=u"store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    dry = not a.go
    dest = os.path.abspath(a.dest) if a.dest else default_dest()
    # ⚠ `--json` 须**纯 JSON**：core 之 config 于导入期向 stdout 打数行 ⇒ 收其杂记（归 `杂记` 键 · ⛔ 弃）
    _buf = _Sink()
    with contextlib.redirect_stdout(_buf):
        p = plan(dest, desktop=not a.no_desktop)
        rc, lines = render_and_maybe_apply(p, dry, do_shortcuts=not a.no_shortcuts)
    chatter = _buf.getvalue()
    if a.json:
        print(json.dumps({u"version": VERSION, u"dry_run": dry, u"rc": rc,
                          u"plan": p, u"lines": lines, u"杂记": chatter},
                         ensure_ascii=False, indent=2))
    else:
        if chatter:
            sys.stdout.write(chatter)
        for x in lines:
            print(x)
    return rc


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))