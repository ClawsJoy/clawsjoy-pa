# -*- coding: utf-8 -*-
"""查散落浏览器 —— 「跑毕必收」之齿（**只读** ｜ ⛔ 不杀进程 · ⛔ 不改他物）

用法::

    python -X utf8 -B scripts/dev/查散落浏览器.py            # 人读表
    python -X utf8 -B scripts/dev/查散落浏览器.py --json     # 机读
    python -X utf8 -B scripts/dev/查散落浏览器.py --self-test

判据（一手 · 承 pm_1898 §三）：凡 ``chrome.exe`` 之命令行含 ``--headless``
且 **其父非** ``chrome.exe``（＝根实例）⇒ 记为「一枚散落之无头实例」。
⚠ 只报 **根实例**（其子为渲染/工具进程，随根走），免刷屏。

归属：按 ``--user-data-dir`` **全径** 之名归一 ——
``cw<号>*`` ⇒ CodexWindows线 ｜ ``*paseo-pm*`` ⇒ 项目经理 ｜
``*ts_scratch*`` ⇒ 技术总监 ｜ ``*chrome_cdp`` ⇒ guard 之常驻（**非散落**）｜
否则 ``?（未知）``。⚠ 归属只据 **profile 名** 之命名约定 —— 是**线索**，⛔ 非铁证。

退出码: 0 = 无散落 ｜ 1 = 有散落 ｜ 2 = 取样失败 ｜ 3 = 入参错
"""
import json
import re
import subprocess
import sys

BS = chr(92)   # 反斜杠（免转义地狱）
OWNER_RULES = (
    ("CodexWindows线", re.compile(r"cw\d", re.I)),
    ("项目经理", re.compile(r"paseo-pm", re.I)),
    ("技术总监", re.compile(r"ts_scratch", re.I)),
    ("guard（常驻 · 非散落）", re.compile(r"chrome_cdp$", re.I)),
)
_PORT = re.compile(r"--remote-debugging-port=(\d+)")
_UDD = re.compile(r'--user-data-dir=(?:"([^"]*)"|(\S+))')
_HEADLESS = re.compile(r"--headless(=new|=old)?")


def parse_cmdline(cmd):
    """命令行 ⇒ ``(port, user_data_dir, headless)``；缺 ⇒ ``None``。"""
    cmd = cmd or ""
    m = _PORT.search(cmd)
    port = int(m.group(1)) if m else None
    m = _UDD.search(cmd)
    udd = (m.group(1) or m.group(2)) if m else None
    return port, udd, bool(_HEADLESS.search(cmd))


def attribute(udd):
    """``--user-data-dir`` ⇒ 席（**线索** · 据名之约定）。"""
    if not udd:
        return "?（未知 · 无 profile）"
    full = str(udd).replace("/", BS).rstrip(BS)
    for name, pat in OWNER_RULES:
        if pat.search(full):
            return name
    return "?（未知）· " + full.split(BS)[-1]


def is_root(proc, by_id):
    """父非 ``chrome.exe`` ⇒ 本实例之根（免逐子报）。"""
    parent = by_id.get(int(proc.get("ParentProcessId") or 0))
    return parent is None or str(parent.get("Name", "")).lower() != "chrome.exe"


def sample():
    """取 chrome.exe 之 ``(pid, ppid, cmd)``（经 PowerShell · 唯读）。"""
    q = "Name='chrome.exe'"
    ps = (
        "Get-CimInstance Win32_Process -Filter \"" + q + "\" | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    out = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
    )
    if out.returncode != 0:
        raise RuntimeError("powershell rc=%s %s" % (out.returncode, (out.stderr or "")[:200]))
    raw = (out.stdout or "").strip()
    if not raw:
        return []
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def find_strays(procs):
    """⇒ [(pid, owner, port, udd), ...] —— 只取「无头 ∧ 根 ∧ 非 guard 常驻」。"""
    by_id = {}
    for p in procs:
        by_id[int(p.get("ProcessId") or 0)] = p
    out = []
    for p in procs:
        port, udd, headless = parse_cmdline(p.get("CommandLine"))
        if not headless or not is_root(p, by_id):
            continue
        owner = attribute(udd)
        if owner.startswith("guard"):
            continue
        out.append((int(p.get("ProcessId") or 0), owner, port, udd))
    return sorted(out)


def _self_test():
    """纯逻辑自证（⛔ 不碰真机）。"""
    T = BS + "Temp" + BS
    C = BS + "Users" + BS + "x" + BS + ".clawsjoy" + BS
    P = BS + "paseo-workspace" + BS
    cases = []
    cases.append(("parse.headless",
                  parse_cmdline("chrome.exe --headless=new --remote-debugging-port=9223 --user-data-dir=" + T + "cw1807cdp_abc about:blank")
                  == (9223, T + "cw1807cdp_abc", True)))
    cases.append(("parse.quoted",
                  parse_cmdline('chrome.exe --remote-debugging-port=9222 --user-data-dir="' + C + 'chrome_cdp" http://x/pa.html')
                  == (9222, C + "chrome_cdp", False)))
    cases.append(("attr.cw", attribute(T + "cw1807cdp_abc").startswith("CodexWindows")))
    cases.append(("attr.pm", attribute(P + ".paseo-pm" + BS + "x") == "项目经理"))
    cases.append(("attr.td", attribute(P + "_tmp" + BS + "ts_scratch" + BS + "p1468" + BS + "cdp_profile") == "技术总监"))
    cases.append(("attr.guard", attribute(C + "chrome_cdp").startswith("guard")))
    cases.append(("attr.unknown", attribute(T + "zzz").startswith("?")))
    procs = [
        {"ProcessId": 10, "ParentProcessId": 9, "Name": "chrome.exe",
         "CommandLine": "chrome.exe --headless=new --user-data-dir=" + T + "cw1_x"},
        {"ProcessId": 11, "ParentProcessId": 10, "Name": "chrome.exe",
         "CommandLine": "chrome.exe --headless=new --user-data-dir=" + T + "cw1_x"},
        {"ProcessId": 12, "ParentProcessId": 9, "Name": "chrome.exe",
         "CommandLine": "chrome.exe --remote-debugging-port=9222 --user-data-dir=" + C + "chrome_cdp"},
        {"ProcessId": 13, "ParentProcessId": 9, "Name": "chrome.exe",
         "CommandLine": "chrome.exe --user-data-dir=" + T + "plain"},
    ]
    cases.append(("strays.only_root_headless_non_guard",
                  find_strays(procs) == [(10, "CodexWindows线", None, T + "cw1_x")]))
    ok = sum(1 for _, v in cases if v)
    for name, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", name))
    print("%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


def main():
    if "--self-test" in sys.argv:
        return _self_test()
    known = {"--json", "--self-test"}
    bad = [a for a in sys.argv[1:] if a not in known]
    if bad:
        print("rc=3 入参错: " + repr(bad))
        return 3
    try:
        procs = sample()
    except Exception as e:
        print("rc=2 取样失败: %s" % e)
        return 2
    strays = find_strays(procs)
    if "--json" in sys.argv:
        print(json.dumps({"chrome_total": len(procs), "strays": strays}, ensure_ascii=False))
    else:
        print("chrome.exe 共 %d 个进程 · 散落之无头根实例 %d 枚" % (len(procs), len(strays)))
        for pid, owner, port, udd in strays:
            print("  散落 pid=%-7s 席=%-16s port=%-6s profile=%s" % (pid, owner, port or "-", udd))
        if not strays:
            print("  （无 —— 跑毕皆收）")
    return 1 if strays else 0


if __name__ == "__main__":
    sys.exit(main())