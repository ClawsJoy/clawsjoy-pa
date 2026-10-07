# -*- coding: utf-8 -*-
u"""make_uninstaller.py -- 造「卸载器 exe」`卸载ClawsJoyPA.exe`（承 pm_1628 §二.1 令一 · 照 DSH 之 `Uninstall …exe` 族）。

由（PM 一手 · pm_1628 §二.1）：今「应用与功能」之卸载项 ＝ `卸载ClawsJoyPA.cmd`（一 cmd 之窗 · **⛔ 像产品**）
  ⟷ DSH ／ Paseo 之族皆 `Uninstall …exe`（每用户 · `currentUser`）。
⇒ 本器以**构建期**之本机 `csc.exe` 编一极小 C# 启动器：
     确认框（**载「将撤何物」之清单** —— 其辞由自带之 Python 出 · ⛔ C# 之字面）
       ⇒ 用户点 OK ⇒ 以自带之 runtime 跑 `uninstall_pa.py --go` ⇒ 等其毕 ⇒ 以其 rc 退。
⇒ 落装根 `卸载ClawsJoyPA.exe`（**每用户** · `.NET Framework 4.x` ⇒ asInvoker ⇒ **⛔ 提权**）。

⚠ 三条诚（要 · 承「凡壳 ⇒ 其依赖之系统物 ⇒ 须探测 ＋ 人话 ＋ 闸」＋「⛔ 静默失败」）：
  ⒜ 本器**唯构建期**跑（须本机 .NET Framework 之 `csc.exe`）；**净机 ⛔ 编译** ⇒ exe **随包入 payload**
     （`make_client_bundle.py` 于立册前调 `ensure_exe()`；⛔ 得 ⇒ 明书其行 ∧ 卸载项走 `.cmd` 兜底）。
  ⒝ exe 之运行依 ＝ **.NET Framework 4.x**（Win10 ／ Win11 内置 ⇒ 通常免装）；缺 ⇒ 兜底 `.cmd` 仍可卸（⛔ 断）。
  ⒞ C# 源**内嵌**于本器（**一处定形**）⇒ **唯 ASCII**（免编译器之码页病 · 同族于 pm_1578 之 `.cmd`／`.ps1`）。
     其「人话」之辞（确认框之清单）**由 Python 出**（UTF-8 读回 ⇒ Windows 之 MessageBox 为 Unicode）。

用法：
  python -X utf8 scripts\\win_pa\\make_uninstaller.py                    # 干跑（印将动何物 · ⛔ 编译）
  python -X utf8 scripts\\win_pa\\make_uninstaller.py --go --dest <装根 ∨ dist 树>
  ... --csc <csc.exe> ｜ --json ｜ --self-test
退出码：0 成 ｜ 2 前置 ⛔ 足 ∨ 编败 ｜ 3 入口错
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

#: exe 之名（**一处定形** —— 与 `installer_post.UNINSTALL_EXE` 同；由 `test_win_pa_uninstaller_1629` 以器核）
EXE_NAME = u"卸载ClawsJoyPA.exe"
CS_NAME = u"uninstaller.cs"
#: C# 编译之诸参（**一处定形**）—— `winexe` ＝ 无控制台之窗（每用户 · ⛔ 提权 ⇒ ⛔ manifest）
CSC_ARGS = (u"/nologo", u"/target:winexe", u"/optimize+", u"/platform:anycpu",
            u"/r:System.Windows.Forms.dll", u"/warnaserror-")

#: C# 源（**一处定形** · **唯 ASCII**）：确认框（清单由 Python 出）⇒ 以自带 runtime 跑卸载器。
CS_SRC = r"""using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Windows.Forms;

internal static class ClawsJoyPaUninstall
{
    [STAThread]
    private static int Main(string[] args)
    {
        string root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
        root = root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        string py = Path.Combine(root, "runtime", "python.exe");
        string script = Path.Combine(root, "scripts", "win_pa", "uninstall_pa.py");
        if (!File.Exists(py) || !File.Exists(script))
        {
            MessageBox.Show("Cannot find the ClawsJoy PA runtime to uninstall from:" + Environment.NewLine + Environment.NewLine
                + py + Environment.NewLine + script,
                "ClawsJoy PA", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 2;
        }
        bool quiet = args.Length > 0 && args[0] == "--yes";
        if (!quiet)
        {
            string plan = Capture(py, "-X utf8 \"" + script + "\" --root \"" + root + "\"");
            DialogResult r = MessageBox.Show(
                plan + Environment.NewLine + Environment.NewLine
                + "Proceed with the uninstall?" + Environment.NewLine
                + "Your data folder (data) will be KEPT.",
                "ClawsJoy PA", MessageBoxButtons.OKCancel, MessageBoxIcon.Warning);
            if (r != DialogResult.OK) { return 0; }
        }
        ProcessStartInfo psi = new ProcessStartInfo(py);
        psi.Arguments = "-X utf8 \"" + script + "\" --go --root \"" + root + "\"";
        psi.UseShellExecute = false;
        psi.CreateNoWindow = false;
        Process p = Process.Start(psi);
        p.WaitForExit();
        return p.ExitCode;
    }

    private static string Capture(string exe, string arguments)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo(exe);
            psi.Arguments = arguments;
            psi.UseShellExecute = false;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            psi.StandardOutputEncoding = Encoding.UTF8;
            psi.StandardErrorEncoding = Encoding.UTF8;
            psi.CreateNoWindow = true;
            Process p = Process.Start(psi);
            string o = p.StandardOutput.ReadToEnd();
            p.WaitForExit(20000);
            o = o.Trim();
            if (o.Length > 3000) { o = o.Substring(o.Length - 3000); }
            return o;
        }
        catch (Exception e)
        {
            return "Could not read the uninstall plan:" + Environment.NewLine + e.Message;
        }
    }
}
"""


def candidates():
    u"""csc 之候选（**一处定形** · 唯本机之 .NET Framework ∨ PATH）—— ⛔ 猜。"""
    windir = os.environ.get(u"WINDIR") or u"C:" + BS + u"Windows"
    out = []
    for fx in (u"Framework64", u"Framework"):
        out.append(os.path.join(windir, u"Microsoft.NET", fx, u"v4.0.30319", u"csc.exe"))
    w = shutil.which(u"csc.exe") or shutil.which(u"csc")
    if w:
        out.append(w)
    return out


def find_csc(explicit=None):
    u"""取 csc ⇒ `(径, note)`；⛔ 见 ⇒ `(None, 人话之因)`（⛔ 静默）。"""
    if explicit:
        if os.path.isfile(explicit):
            return explicit, u"（--csc 指定）"
        return None, u"--csc 之件 ⛔ 在：%s" % explicit
    for c in candidates():
        if c and os.path.isfile(c):
            return c, u""
    return None, (u"⛔ 见 csc.exe（.NET Framework 4.x 之编译器）—— 候选：%s"
                  u"；⇒ **本机 ⛔ 可编** ⇒ 卸载项走 `卸载ClawsJoyPA.cmd` 兜底（仍可卸）"
                  % u"、".join(candidates()))


def command(csc, dest, cs_path):
    return [csc] + list(CSC_ARGS) + [u"/out:" + os.path.join(dest, EXE_NAME), cs_path]


def build(dest, csc=None, dry=False):
    u"""编 exe ⇒ `(rc, rows)`。前置：装根在 ∧ 自带 runtime 在（否则 ⛔ 编 —— 免出「跑不得」之件）。"""
    rows = []
    exe = os.path.join(dest, EXE_NAME)
    if not os.path.isdir(dest):
        return 2, [u"⛔ 见装根：%s（--dest）" % dest]
    if not os.path.isfile(os.path.join(dest, u"runtime", u"python.exe")):
        return 2, [u"⛔ 见 %s ⇒ **⛔ 编**（exe 唯调自带 runtime；无之 ⇒ 出了也无用）"
                   % os.path.join(dest, u"runtime", u"python.exe")]
    bin_path, note = find_csc(csc)
    rows.append(u"[uninstaller] exe ⇒ %s" % exe)
    rows.append(u"[uninstaller] C# 源（唯 ASCII · 内嵌）%d 字节 ∶ %s" % (len(CS_SRC), CS_NAME))
    if bin_path is None:
        rows.append(u"[uninstaller] %s" % note)
        return (0 if dry else 2), rows
    rows.append(u"[uninstaller] csc ⇒ %s%s" % (bin_path, note or u""))
    rows.append(u"[uninstaller] %s" % u" ".join(command(bin_path, dest, CS_NAME)))
    if dry:
        rows.append(u"[uninstaller] 干跑（⛔ 编译）—— --go 方真编")
        return 0, rows
    t = tempfile.mkdtemp(prefix=u"cjpa_cs_")
    cs = os.path.join(t, CS_NAME)
    try:
        with io.open(cs, "w", encoding=u"ascii", newline=u"\n") as fh:
            fh.write(CS_SRC)
        r = subprocess.run(command(bin_path, dest, cs), capture_output=True, timeout=300)
        out = ((r.stdout or b"") + (r.stderr or b"")).decode(u"utf-8", u"replace").strip()
        if out:
            rows += [u"    " + x for x in out.splitlines()]
        if r.returncode != 0 or not os.path.isfile(exe):
            rows.append(u"[uninstaller] ⛔ 编败 rc=%s（⛔ 造出 exe）" % r.returncode)
            return 2, rows
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        rows.append(u"[uninstaller] ⛔ 编例外：%s: %s" % (type(e).__name__, e))
        return 2, rows
    finally:
        shutil.rmtree(t, ignore_errors=True)
    rows.append(u"[uninstaller] 成：%s（%d 字节 · 每用户 · ⛔ 提权）"
                % (exe, os.path.getsize(exe)))
    return 0, rows


def ensure_exe(dest, csc=None):
    u"""出包之钩（**一处定形** · `make_client_bundle` 之调用）⇒ `(ok, rows)`。
    ⚠ ⛔ 得（无 csc ／ 编败）⇒ `ok=False` 而**明书**（⛔ 静默 ⇒ 卸载项走 .cmd 兜底 · 包仍可交付）。
    """
    rc, rows = build(dest, csc=csc, dry=False)
    return (rc == 0), rows


def self_test():
    fails = []
    hits = []

    def say(ok, name):
        hits.append(bool(ok))
        print(u"  %s %s" % (u"+" if ok else u"X", name))
        if not ok:
            fails.append(name)

    say(all(ord(c) < 128 for c in CS_SRC), u"正控：C# 源**尽 ASCII**（免编译器之码页病 · pm_1578 之族）")
    say(u"uninstall_pa.py" in CS_SRC and u"--go" in CS_SRC,
        u"正控：exe 以自带之 runtime 跑 `uninstall_pa.py --go`（⛔ 另杀进程）")
    say(u"runtime" in CS_SRC and u"python.exe" in CS_SRC, u"正控：唯走自带之 runtime（⛔ 系统 python）")
    say(u"AppDomain.CurrentDomain.BaseDirectory" in CS_SRC,
        u"正控：装根由 exe 之所在定位（整根可移 · ⛔ 硬编本机径）")
    say((u"HKEY_" + u"LOCAL_" + u"MACHINE") not in CS_SRC and (u"HK" + u"LM") not in CS_SRC,
        u"反控：C# 源 ⛔ 含系统级域（每用户 ⇒ ⛔ 提权）")
    say(u"/target:winexe" in CSC_ARGS, u"正控：编作 winexe（无控制台之窗 · 一像产品之项）")
    import ast
    _mods = set()
    for _n in ast.walk(ast.parse(io.open(__file__, encoding=u"utf-8").read())):
        if isinstance(_n, ast.Import):
            _mods |= {a.name.split(u".")[0] for a in _n.names}
        elif isinstance(_n, ast.ImportFrom) and _n.module:
            _mods.add(_n.module.split(u".")[0])
    _extra = sorted(m for m in _mods if m not in set(sys.stdlib_module_names))
    say(_extra in ([], [u"installer_post"]),
        u"反控：本器之依 ⛔ 出标准库（∧ 同目录 installer_post）"
        u"—— 免新工具链（今：%s）" % (_extra or u"无"))
    c, _n = find_csc()
    say(c is None or os.path.isfile(c), u"正控：csc 之取（见 ⇒ 其径；⛔ 见 ⇒ None ＋ 人话）")
    rc, rows = build(u"C:" + BS + u"__cjpa_nope__", dry=True)
    say(rc == 2 and any(u"⛔ 见装根" in x for x in rows), u"反控：装根 ⛔ 在 ⇒ rc 2 ∧ 报因（⛔ 静默）")
    import installer_post as _ip                                # noqa: E402 — 同目录
    say(_ip.UNINSTALL_EXE == EXE_NAME,
        u"正控：exe 之名**一处定形**（make_uninstaller ⟷ installer_post.UNINSTALL_EXE）")
    print(u"=== make_uninstaller 自测 %d/%d ===" % (sum(hits), len(hits)))
    print(u"[self-test] %s" % (u"PASS" if not fails else u"FAIL"))
    for f in fails:
        print(u"  [FAIL] %s" % f)
    return 0 if not fails else 2


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--dest", default=u"")
    ap.add_argument(u"--csc", default=u"")
    ap.add_argument(u"--go", action=u"store_true")
    ap.add_argument(u"--json", action=u"store_true")
    ap.add_argument(u"--self-test", action=u"store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    dest = os.path.abspath(a.dest) if a.dest else ROOT
    rc, rows = build(dest, csc=(a.csc or None), dry=not a.go)
    if a.json:
        print(json.dumps({u"tool": u"make_uninstaller", u"dest": dest, u"exe": os.path.join(dest, EXE_NAME),
                          u"dry_run": (not a.go), u"rc": rc, u"lines": rows, u"cs_bytes": len(CS_SRC)},
                         ensure_ascii=False, indent=2))
    else:
        for x in rows:
            print(x)
    return rc


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))
