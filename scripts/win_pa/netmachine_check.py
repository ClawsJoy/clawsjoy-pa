# -*- coding: utf-8 -*-
u"""净机预检器 —— 「此机是否净 ＋ 其信息清单」（承 pm_1439 §三.2 ／ pm_1440 §二.1）。

其的：M2（净机之验）之**第一跳** —— 于净机侧跑本器 ⇒ 报「净 ／ ⛔ 净 ＋ 逐项之据 ＋ 刻」。
本器**只读** —— ⛔ 装 ／ ⛔ 改 ／ ⛔ 删（承「⛔ 代操作」之族）。

净之五项（逐项附「据」）：
  ① ⛔ 我方之开发物（`clawsjoy_v9` ／ `clawsjoy_build` ／ `paseo-workspace` ／ `内容工坊` ／ 席册 …）
  ② ⛔ `data\\**` 之残留（仓之运行产物）  ③ ⛔ 侧车（`*.before_*`）  ④ 端口（`5102` ／ `11434`）之占用
  ⑤ 依赖之齐（`requirements-runtime.txt` 逐条 ∧ `wheel\\` 之有无）
清单之十项（加「虚拟化」—— 形 2 之硬前提）：Windows 版 ／ 位数 ／ Home ／ Pro ／ 盘余 ／ 内存 ／ Python ／ Ollama ／ GPU ＋ 显存。

⚠ 限（⛔ 掩）：① 端口之判 ＝ TCP connect（⛔ 判「何进程」—— 须提权 ⇒ 唯报「有 ／ 无 监听」）
  ② GPU ／ 显存 ＝ 三路之优取（`nvidia-smi` ⇒ PowerShell CIM ⇒ `wmic`）⇒ 皆败 ⇒ 报「⛔ 判」（⛔ 猜）
  ③ 依赖之判 ＝ `importlib.metadata` 之「已装 ∨ 未装」＋ 粗比版（⛔ 完备之符意 · ⛔ 真装）
  ④ 「净」＝ 本器所扫之面（⛔ 全机 —— 唯列其标 · 承「界内 ⛔ ＝ 准」之族）

用法：
  python -X utf8 scripts\\win_pa\\netmachine_check.py            # 人读之报
  python -X utf8 scripts\\win_pa\\netmachine_check.py --json
  python -X utf8 scripts\\win_pa\\netmachine_check.py --self-test
退出码：0 ＝ 净（诸项皆过）｜2 ＝ ⛔ 净（有项 ⛔）｜3 ＝ 入口错 ｜1 ＝ 器自错
"""
from __future__ import annotations

import argparse
import ctypes
import io
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time

# ⭐ 窗隐（pm_1865 §二.1 · **一处定形**）：本层之 spawn ⇒ 一律经 `_proc`（⛔ 手写 creationflags）。
#   由：本层器常由**无控制台之父**起（任务宿主 `svchost` ／ `DETACHED_PROCESS` 之器）⇒ 裸 spawn
#   ⇒ Windows **新开**一个控制台窗（屏上一闪 · pm_1862 §一② ／ §一① 之一手）。
#   真源 ＝ `core/pa/_proc.py`；本层器 `scripts/win_pa/_proc.py` ① 同目录 `import _proc`
#   （常路）—— ⛔ 成 ⇒ ② 按**文件路径**载（⛔ 倚 sys.path · 同 `boot_resume.py:94-122` 之形）；
#   皆败 ⇒ `None`（caller 退**本地等价** · 并落警 · ⛔ 静默）。
def _load_proc():
    try:
        import _proc
        return _proc
    except Exception:                                     # noqa: BLE001 — 照实退下一步
        pass
    try:
        import importlib.util as _ilu
        _s = _ilu.spec_from_file_location("_win_pa_proc", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_proc.py"))
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)
        return _m
    except Exception as _e:                               # noqa: BLE001 — 照实报因
        sys.stderr.write(u"⚠ 窗隐器皆载不到（%s: %s）\n" % (type(_e).__name__, str(_e)[:120]))
    return None


_PROC = _load_proc()


def run_hidden(cmd, **kw):
    u"""本器之 spawn 出口（窗隐 · ⛔ 各处手写 creationflags）。真源载不到 ⇒ 本地等价。"""
    if _PROC is not None:
        return _PROC.run_hidden(cmd, **kw)
    kw["creationflags"] = int(kw.get("creationflags", 0) or 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(cmd, **kw)


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BS = chr(92)
GATEWAY_PORT = 5102
OLLAMA_PORT = 11434
REQ_FILE = u"requirements-runtime.txt"
#: 我方开发物之标（净机 ⛔ 应有）—— 唯列其标（⛔ 全机之扫）
def _dev_marks():
    home = os.path.expanduser(u"~")
    return (
        u"D:" + BS + u"clawsjoy_v9",
        u"D:" + BS + u"clawsjoy_build",
        u"D:" + BS + u"codex-home",
        u"D:" + BS + u"paseo-workspace",
        os.path.join(home, u"paseo-workspace"),
        os.path.join(home, u".agents"),
        os.path.join(home, u"Documents", u"Obsidian"),
    )
#: 残留之目录（相对包之根）
RESIDUE_DIRS = (u"data", u"logs", u"dist")


# ------------------------------------------------------------------ 纯函数（可自测）
def parse_requirements(text):
    u"""requirements 之文 ⇒ [(名, 约束, spec)。⛔ 外依（唯 stdlib）。"""
    rows = []
    for ln in (text or u"").split(u"\n"):
        ln = ln.split(u"#")[0].strip()
        if not ln:
            continue
        m = re.match(u"^([A-Za-z0-9_.\\-]+)\\s*(.*)$", ln)
        if not m:
            continue
        rows.append((m.group(1), m.group(2).strip()))
    return rows


def ver_tuple(s):
    u"""版之串 ⇒ 数之组（粗 · 尽取前导数字）；⛔ 解 ⇒ ()。"""
    parts = re.findall(u"\\d+", s or u"")
    return tuple(int(x) for x in parts[:4])


def spec_ok(installed, spec):
    u"""粗比：`>=x` ／ `>x` ／ `==x` ／ 空 ⇒ True。⚠ 唯前导数字（⛔ 完备之符意）。"""
    if not (spec or u"").strip():
        return True
    if installed is None:
        return False
    iv = ver_tuple(installed)
    for m in re.finditer(u"(>=|<=|==|!=|>|<)\\s*([0-9][0-9A-Za-z_.\\-]*)", spec):
        op, want = m.group(1), ver_tuple(m.group(2))
        if not want:
            continue
        if op == u">=" and not (iv >= want):
            return False
        if op == u">" and not (iv > want):
            return False
        if op == u"<=" and not (iv <= want):
            return False
        if op == u"<" and not (iv < want):
            return False
        if op == u"==" and not (iv == want):
            return False
        if op == u"!=" and not (iv != want):
            return False
    return True


def judge(items):
    u"""诸「净」之项 ⇒ (判之字, ⛔ 之数)。ok ＝ None ⇒ 「⛔ 判」（⛔ 计为 ⛔）。"""
    bad = [x for x in items if x.get(u"ok") is not True]
    return (u"净" if not bad else u"⛔ 净"), len(bad)


# ------------------------------------------------------------------ 探（唯读）
def probe_ports(ports=(GATEWAY_PORT, OLLAMA_PORT), host=u"127.0.0.1", timeout=0.6):
    out = {}
    for p in ports:
        s = socket.socket()
        s.settimeout(timeout)
        try:
            rc = s.connect_ex((host, p))
        except Exception:
            rc = -1
        finally:
            s.close()
        out[p] = (rc == 0)
    return out


def probe_memory():
    class _MS(ctypes.Structure):
        _fields_ = [(u"dwLength", ctypes.c_ulong), (u"dwMemoryLoad", ctypes.c_ulong),
                    (u"ullTotalPhys", ctypes.c_ulonglong), (u"ullAvailPhys", ctypes.c_ulonglong),
                    (u"ullTotalPageFile", ctypes.c_ulonglong), (u"ullAvailPageFile", ctypes.c_ulonglong),
                    (u"ullTotalVirtual", ctypes.c_ulonglong), (u"ullAvailVirtual", ctypes.c_ulonglong),
                    (u"ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    try:
        m = _MS()
        m.dwLength = ctypes.sizeof(_MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return int(m.ullTotalPhys), int(m.ullAvailPhys)
    except Exception:
        pass
    return None, None


def probe_disks():
    out = []
    try:
        mask = int(ctypes.windll.kernel32.GetLogicalDrives())
    except Exception:
        mask = 0
    for i in range(26):
        if mask & (1 << i):
            d = chr(65 + i) + u":" + BS
            try:
                u = shutil.disk_usage(d)
                out.append((d, int(u.total), int(u.free)))
            except Exception:
                pass
    return out


def probe_win_reg():
    try:
        import winreg
    except Exception:
        return {}
    out = {}
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           u"SOFTWARE" + BS + u"Microsoft" + BS + u"Windows NT" + BS + u"CurrentVersion")
        try:
            for nm in (u"ProductName", u"EditionID", u"DisplayVersion", u"CurrentBuild", u"UBR", u"InstallationType"):
                try:
                    v, _ = winreg.QueryValueEx(k, nm)
                    out[nm] = v
                except Exception:
                    pass
        finally:
            winreg.CloseKey(k)
    except Exception:
        pass
    return out


def probe_gpu():
    u"""⇒ (行之表, 源之名)。三路之优取 —— 皆败 ⇒ ([], None)。"""
    exe = shutil.which(u"nvidia-smi")
    if exe:
        try:
            r = run_hidden([exe, u"--query-gpu=name,memory.total", u"--format=csv,noheader"],
                               capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and (r.stdout or u"").strip():
                return [x.strip() for x in r.stdout.strip().split(u"\n")], u"nvidia-smi"
        except Exception:
            pass
    ps = shutil.which(u"powershell") or shutil.which(u"pwsh")
    if ps:
        try:
            cmd = [ps, u"-NoProfile", u"-Command",
                   u"Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + ' | ' + $_.AdapterRAM }"]
            r = run_hidden(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and (r.stdout or u"").strip():
                return [x.strip() for x in r.stdout.strip().split(u"\n")], u"powershell-cim"
        except Exception:
            pass
    w = shutil.which(u"wmic")
    if w:
        try:
            r = run_hidden([w, u"path", u"win32_VideoController", u"get", u"name,AdapterRAM"],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and (r.stdout or u"").strip():
                return [x.strip() for x in r.stdout.strip().split(u"\n") if x.strip()], u"wmic"
        except Exception:
            pass
    return [], None


def probe_virt():
    u"""CPU 之虚拟化（形 `2` 之硬前提）⇒ (值是 ∨ None, 源 ∨ None)。⚠ 须提权 ∨ ⛔ 得 ⇒ None。"""
    ps = shutil.which(u"powershell") or shutil.which(u"pwsh")
    if ps:
        try:
            cmd = [ps, u"-NoProfile", u"-Command",
                   u"$c=Get-CimInstance Win32_ComputerSystem; $p=Get-CimInstance Win32_Processor; "
                   u"'HypervisorPresent=' + $c.HypervisorPresent + ';VirtualizationFirmwareEnabled=' + "
                   u"($p | Select-Object -First 1).VirtualizationFirmwareEnabled"]
            r = run_hidden(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and (r.stdout or u"").strip():
                return u" ／ ".join(x.strip() for x in r.stdout.strip().split(u"\n") if x.strip()), u"powershell-cim"
        except Exception:
            pass
    return None, None


def scan_sidecars(root, limit=200):
    hits = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (u"__pycache__", u".git", u"node_modules")]
        for f in fn:
            if u".before_" in f:
                hits.append(os.path.join(dp, f))
                if len(hits) >= limit:
                    return hits
    return hits


def count_files(p, limit=20000):
    u"""件之数（⛔ 递归止于 limit —— 免天量之目；达限 ⇒ 报「≥限」）。"""
    n = 0
    if os.path.isdir(p):
        for dp, dn, fn in os.walk(p):
            n += len(fn)
            if n >= limit:
                return limit
    return n


# ------------------------------------------------------------------ 主
def build_report(root=ROOT):
    ts = time.strftime(u"%Y-%m-%d %H:%M:%S")
    reg = probe_win_reg()
    total_mem, free_mem = probe_memory()
    redisks = probe_disks()
    gpul, gpusrc = probe_gpu()
    ports = probe_ports()
    devs = [(m, os.path.exists(m)) for m in _dev_marks()]
    residues = [(d, count_files(os.path.join(root, d)), os.path.isdir(os.path.join(root, d)))
                for d in RESIDUE_DIRS]
    sides = scan_sidecars(root)
    reqp = os.path.join(root, REQ_FILE)
    reqs = parse_requirements(io.open(reqp, encoding=u"utf-8", errors=u"replace").read()) if os.path.isfile(reqp) else []
    inst = []
    for name, spec in reqs:
        try:
            from importlib import metadata as _md
            v = _md.version(name)
        except Exception:
            v = None
        inst.append((name, spec, v, spec_ok(v, spec)))
    wheels = []
    wd = os.path.join(root, u"wheel")
    if os.path.isdir(wd):
        wheels = [f for f in os.listdir(wd) if f.lower().endswith(u".whl")]
    info = [
        (u"刻", ts, u"本器之取刻"),
        (u"Windows", platform.platform(), u"platform.platform()"),
        (u"版之数", u".".join(str(x) for x in (sys.getwindowsversion()[:3])), u"sys.getwindowsversion"),
        (u"ProductName", reg.get(u"ProductName", u"(⛔ 判)"), u"HKLM CurrentVersion"),
        (u"EditionID", reg.get(u"EditionID", u"(⛔ 判)"), u"HKLM CurrentVersion"),
        (u"DisplayVersion", reg.get(u"DisplayVersion", u"(⛔ 判)"), u"HKLM CurrentVersion"),
        (u"Build", u"%s.%s" % (reg.get(u"CurrentBuild", u"?"), reg.get(u"UBR", u"?")), u"HKLM CurrentVersion"),
        (u"位数", platform.machine(), u"platform.machine"),
        (u"Python", sys.version.split()[0], u"sys.version"),
        (u"Python(外)", shutil.which(u"python") or u"(⛔ 有)", u"shutil.which"),
        (u"Ollama", shutil.which(u"ollama") or u"(⛔ 有)", u"shutil.which"),
        (u"Ollama 之口", u"有监听" if ports.get(OLLAMA_PORT) else u"无监听", u"TCP 127.0.0.1:%d" % OLLAMA_PORT),
        (u"内存", (u"%.1f GB ／ 余 %.1f GB" % (total_mem / 1073741824.0, free_mem / 1073741824.0))
         if total_mem else u"(⛔ 判)", u"GlobalMemoryStatusEx"),
        (u"GPU", (u" ／ ".join(gpul) if gpul else u"(⛔ 判)"), gpusrc or u"三路皆败"),
    ]
    _vh, _vs = probe_virt()
    info.append((u"虚拟化", _vh if _vh else u"(⛔ 判)", _vs or u"powershell-cim 皆败（⛔ 猜）"))
    for d, t, f in redisks:
        info.append((u"盘 %s" % d, u"共 %.1f GB ／ 余 %.1f GB" % (t / 1073741824.0, f / 1073741824.0), u"shutil.disk_usage"))
    gate = [
        {"id": u"开发物", "ok": not any(x[1] for x in devs),
         "ev": u"命中 %d ／ 标 %d：%s" % (sum(1 for x in devs if x[1]), len(devs),
                                        u"、".join(x[0] for x in devs if x[1]) or u"无"),
         "need": u"⛔ 应有（净机之标）"},
        {"id": u"data 残留", "ok": all(n == 0 for _, n, _ in residues),
         "ev": u"；".join(u"%s＝%s%d 件%s" % (d, u"≥" if n >= 20000 else u"", n, u"（⛔ 有）" if ex else u"（无）") for d, n, ex in residues),
         "need": u"0 件"},
        {"id": u"侧车", "ok": not sides,
         "ev": u"%d 件%s" % (len(sides), (u"：%s" % sides[0]) if sides else u""),
         "need": u"0 件（*.before_*）"},
        {"id": u"端口", "ok": not (ports.get(GATEWAY_PORT) and ports.get(OLLAMA_PORT)),
         "ev": u"；".join(u"%d＝%s" % (p, u"有监听" if v else u"无监听") for p, v in sorted(ports.items())),
         "need": u"5102 无（起前）／11434 无（未装模型）"},
        {"id": u"依赖", "ok": all(x[3] for x in inst),
         "ev": u"逐条 %d：%s" % (len(inst), u"；".join(u"%s %s%s" % (n, s or u"", u"" if ok else u" ⛔")
                                                     for n, s, v, ok in inst)),
         "need": u"皆已装（∧ wheel\\ 有 %d 之轮）" % len(wheels)},
    ]
    verdict, nbad = judge(gate)
    return {"ts": ts, "root": root, "info": info, "gate": gate, "verdict": verdict, "bad": nbad,
            "wheels": len(wheels)}


def _print_report(rep):
    out = []
    out.append(u"[净机预检] 刻 %s ｜ 包之根 %s" % (rep["ts"], rep["root"]))
    out.append(u"== 信息清单 ==")
    for k, v, ev in rep["info"]:
        out.append(u"  %-14s : %-46s （据：%s）" % (k, v, ev))
    out.append(u"== 净之判 ==")
    for g in rep["gate"]:
        out.append(u"  %s %-10s 需 %s ｜ 据 %s" % (u"OK " if g["ok"] else u"⛔ ", g["id"], g["need"], g["ev"]))
    out.append(u"=> 判：%s（⛔ 之项 %d）" % (rep["verdict"], rep["bad"]))
    return u"\n".join(out)


def _self_test():
    ok = tot = 0
    def rep(name, got, want):
        nonlocal ok, tot
        tot += 1
        hit = (got == want)
        ok += 1 if hit else 0
        sys.stdout.write(u"  %s %s => %s（望 %s）\n" % (u"OK " if hit else u"✗ ", name, got, want))
    rep(u"① requirements 之解", parse_requirements(u"# 注\nflask>=3.1.2\npsutil\n"),
        [(u"flask", u">=3.1.2"), (u"psutil", u"")])
    rep(u"② 版之比（>=）", [spec_ok(u"3.1.2", u">=3.1.2"), spec_ok(u"3.0.9", u">=3.1.2"), spec_ok(None, u">=1")],
        [True, False, False])
    rep(u"③ 判（皆过 ⇒ 净）", judge([{"ok": True}, {"ok": True}]), (u"净", 0))
    rep(u"④ 判（一项 ⛔ ⇒ ⛔ 净 · 有齿）", judge([{"ok": True}, {"ok": False}, {"ok": None}]), (u"⛔ 净", 2))
    s = socket.socket()
    s.bind((u"127.0.0.1", 0))
    s.listen(1)
    p = s.getsockname()[1]
    try:
        got = probe_ports(ports=(p,), timeout=0.5)
        rep(u"⑤ 端口之探（活 口 ⇒ 有监听 · 有齿）", got.get(p), True)
    finally:
        s.close()
    got2 = probe_ports(ports=(p,), timeout=0.5)
    rep(u"⑥ 端口之探（闭 口 ⇒ 无监听）", got2.get(p), False)
    sys.stdout.write(u"  => self-test %s（%d/%d）\n" % (u"OK" if ok == tot else u"FAIL", ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--json", action=u"store_true")
    ap.add_argument(u"--self-test", action=u"store_true", dest=u"self_test")
    ap.add_argument(u"--root", default=ROOT)
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if not os.path.isdir(a.root):
        sys.stderr.write(u"入口错：⛔ 有之根 %s\n" % a.root)
        return 3
    rep = build_report(a.root)
    if a.json:
        sys.stdout.write(json.dumps(rep, ensure_ascii=False, indent=1) + u"\n")
    else:
        sys.stdout.write(_print_report(rep) + u"\n")
    return 0 if rep["bad"] == 0 else 2


if __name__ == u"__main__":
    if hasattr(sys.stdout, u"reconfigure"):
        sys.stdout.reconfigure(encoding=u"utf-8", errors=u"replace")
    sys.exit(main())
