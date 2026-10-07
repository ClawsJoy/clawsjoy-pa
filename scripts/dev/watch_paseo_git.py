# -*- coding: utf-8 -*-
u"""只观测不干预：daemon 之 git 调用「频率」与「并发峰值」（承 pm_1828 §二.1）。

器（唯读）：ctypes 走 kernel32 之 Toolhelp 快照列进程（≈17 ms / 489 进程），
  每 interval 秒取一次；逐秒记「新起几支 git」与「同时存续几支」，
  并记每支之 父进程 与 命令行（命令行唯对 git 之新见者取 · 走 psutil）。

界（硬）：⛔ 起停服务 / ⛔ 改 env / ⛔ 触 Paseo 之件 / ⛔ 干预 —— 唯列进程 ＋ 落日志。

用：
  python -X utf8 -B scripts/dev/watch_paseo_git.py --seconds 660 --out logs/paseo_git_watch.log

判（承 pm_1828 §二.1）：若 频率峰值 ≪ 64 ／秒 ∧ 并发峰值 ≪ 8 ⇒ 债销；
  若触顶 ⇒ 报 PM（那时方议调 env）。

⚠ 已知之限（照实）：采样有间隔 ⇒ 存续 < interval 之极短进程或漏计 ⇒ 所报为下限。
"""
from __future__ import print_function

import argparse
import ctypes
import os
import sys
import time
from ctypes import wintypes

GIT_NAMES = (u"git.exe", u"git")
THRESH_FREQ = 64   # Paseo git-process-scheduler 缺省：次/秒
THRESH_CONC = 8    # Paseo git-process-scheduler 缺省：最大并发

TH32CS_SNAPPROCESS = 0x00000002


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        (u"dwSize", wintypes.DWORD),
        (u"cntUsage", wintypes.DWORD),
        (u"th32ProcessID", wintypes.DWORD),
        (u"th32DefaultHeapID", ctypes.c_void_p),
        (u"th32ModuleID", wintypes.DWORD),
        (u"cntThreads", wintypes.DWORD),
        (u"th32ParentProcessID", wintypes.DWORD),
        (u"pcPriClassBase", ctypes.c_long),
        (u"dwFlags", wintypes.DWORD),
        (u"szExeFile", ctypes.c_wchar * 260),
    ]


_k32 = None


def _kernel32():
    global _k32
    if _k32 is None:
        k = ctypes.WinDLL(u"kernel32", use_last_error=True)
        k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        k.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
        k.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        _k32 = k
    return _k32


def _list_procs():
    u"""(pid -> (name, ppid)) —— 唯读快照。"""
    k = _kernel32()
    h = k.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    out = {}
    if h == wintypes.HANDLE(-1).value or not h:
        return out
    try:
        e = _PROCESSENTRY32W()
        e.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        ok = k.Process32FirstW(h, ctypes.byref(e))
        while ok:
            out[int(e.th32ProcessID)] = (e.szExeFile, int(e.th32ParentProcessID))
            ok = k.Process32NextW(h, ctypes.byref(e))
    finally:
        k.CloseHandle(h)
    return out


def _cmdline(pid):
    try:
        import psutil
        return u" ".join([str(x) for x in psutil.Process(pid).cmdline()])
    except Exception:
        return u"?"


def _now():
    return time.strftime(u"%Y-%m-%d %H:%M:%S", time.localtime())


def main(argv=None):
    ap = argparse.ArgumentParser(description=u"只观测 daemon 之 git 演进")
    ap.add_argument(u"--seconds", type=float, default=660.0, help=u"观测时长（缺省 660 = 11 分）")
    ap.add_argument(u"--interval", type=float, default=0.25, help=u"采样间隔秒")
    ap.add_argument(u"--out", default=None, help=u"日志（缺省 <root>/logs/paseo_git_watch.log）")
    ap.add_argument(u"--root", default=None)
    a = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(a.root or os.path.dirname(os.path.dirname(here)))
    out = os.path.abspath(a.out or os.path.join(root, u"logs", u"paseo_git_watch.log"))
    d = os.path.dirname(out)
    if d and not os.path.isdir(d):
        os.makedirs(d)

    fh = open(out, u"a", encoding=u"utf-8")

    def emit(line):
        fh.write(line + u"\n")
        fh.flush()

    emit(u"# watch_paseo_git 起 %s  seconds=%s interval=%s pid=%s"
         % (_now(), a.seconds, a.interval, os.getpid()))
    emit(u"# 栏：ts \t sec \t 新起 \t 存续 \t 父进程 \t 命令行")

    t0 = time.time()
    prev = set()
    cur_sec = None
    sec_new = 0
    sec_max_conc = 0
    tasks = []
    total_new = 0
    peak_new = 0
    peak_new_ts = u""
    peak_conc = 0
    peak_conc_ts = u""
    samples = 0
    seconds_seen = 0
    cmd_seen = {}
    parent_starts = {}

    def flush_sec(sec, new_n, max_conc, ts_list):
        if sec is None:
            return
        emit(u"%s\t%d\t%d\t%d\t%s\t%s" % (
            time.strftime(u"%Y-%m-%d %H:%M:%S", time.localtime(sec)),
            sec, new_n, max_conc,
            u";".join(sorted(set(t[0] for t in ts_list))) if ts_list else u"-",
            u" | ".join(t[1] for t in ts_list) if ts_list else u"-"))

    try:
        while True:
            if time.time() - t0 >= a.seconds:
                break
            procs = _list_procs()
            samples += 1
            gitmap = dict((pid, v) for pid, v in procs.items()
                         if (v[0] or u"").lower() in GIT_NAMES)
            live = set(gitmap.keys())
            new_pids = live - prev
            now = int(time.time())
            if cur_sec is None:
                cur_sec = now
            if now != cur_sec:
                flush_sec(cur_sec, sec_new, sec_max_conc, tasks)
                seconds_seen += 1
                cur_sec = now
                sec_new = 0
                sec_max_conc = 0
                tasks = []
            conc = len(live)
            if conc > sec_max_conc:
                sec_max_conc = conc
            for pid in new_pids:
                ppid = gitmap[pid][1]
                pn = (procs.get(ppid) or (u"?", 0))[0] or u"?"
                parent_starts[pn] = parent_starts.get(pn, 0) + 1
                cl = _cmdline(pid)
                cmd_seen[cl] = cmd_seen.get(cl, 0) + 1
                tasks.append((pn, u"%s <- %s: %s" % (pid, pn, cl)))
                sec_new += 1
                total_new += 1
            if sec_new > peak_new:
                peak_new = sec_new
                peak_new_ts = _now()
            if sec_max_conc > peak_conc:
                peak_conc = sec_max_conc
                peak_conc_ts = _now()
            prev = live
            time.sleep(a.interval)
    finally:
        flush_sec(cur_sec, sec_new, sec_max_conc, tasks)
        seconds_seen += 1
        emit(u"# ---- 结 ----")
        emit(u"# 样本数=%d 秒数=%d 起之总=%d" % (samples, seconds_seen, total_new))
        emit(u"# 频率峰值（新起/秒）=%d 于 %s" % (peak_new, peak_new_ts or u"-"))
        emit(u"# 并发峰值（存续）=%d 于 %s" % (peak_conc, peak_conc_ts or u"-"))
        emit(u"# 阈（Paseo 缺省）= %d 次/秒 · %d 并发" % (THRESH_FREQ, THRESH_CONC))
        emit(u"# 各父进程之起数：")
        for k in sorted(parent_starts, key=lambda x: -parent_starts[x]):
            emit(u"#   %s : %d" % (k, parent_starts[k]))
        emit(u"# 命令行之分布：")
        for k in sorted(cmd_seen, key=lambda x: -cmd_seen[x]):
            emit(u"#   %d  %s" % (cmd_seen[k], k))
        emit(u"# ---- 止 ----")
        fh.close()
    print(u"[OK] 观测毕：样本=%d 秒=%d 起=%d 频率峰值=%d/s 并发峰值=%d"
          % (samples, seconds_seen, total_new, peak_new, peak_conc))
    print(u"[OK] 日志：%s" % out)
    return 0


if __name__ == u"__main__":
    sys.exit(main())
