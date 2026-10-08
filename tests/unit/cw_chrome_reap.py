# -*- coding: utf-8 -*-
r"""跑毕必收 —— CW 席之起浏览器者之**收** ＋ **账**（pm_1914 §二 · 承 pm_1898 §三）。

一事（pm_1914 §一 之照实）：我席昔以「临时命令行起 headless Chrome」跑 CDP 器 ⇒
  **跑毕 ⛔ 收** ⇒ 遗 `5` 枚散落实例（TD 一手枚举）＋ 一大批 `%TEMP%\cw*` 之 profile。
⭐ 故立此器：**起 ⇒ 用 ⇒ 收（finally）⇒ 入账**，一处收四步；凡我席之浏览器跑 ⇒ 皆走此路。

三物：
  ① `run_headless(...)` —— 上下文管理器：起 ⇒ yield ⇒ **finally 收**（`taskkill /T /F` ＋ 删 profile）；
  ② `reap(pid, profile)` —— 自清一枚散落实例（同法：`taskkill /T /F` ＋ 删 profile）；
  ③ `_append(row)` —— 入账（`_pm/_chrome_runs.jsonl` · 逐行 `{ts,pid,port,profile,reaped,why}`）。

⚠ 只读之核：`strays()` —— 引 TD 之只读器（`scripts/dev/查散落浏览器.py --json`）为**常回归**；
  ⛔ 其器在 ⇒ 以己之 PS 取（同法 · ⛔ 杀）。

界：本器唯我席之进程 ／ `%TEMP%\cw*` 之 profile；⛔ 他席之进程 ／ ⛔ 他径。
"""
import contextlib
import datetime
import json
import os
import random
import shutil
import string
import subprocess
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "_pm", "_chrome_runs.jsonl")
TD_VIEWER = os.path.join(ROOT, "scripts", "dev", u"查散落浏览器.py")
TEMP = tempfile.gettempdir()
NO_WINDOW = 0x08000000

CHROME_CANDIDATES = (
    os.environ.get("CW_CHROME") or "",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
)


def chrome_exe():
    u"""本机 chrome.exe 之全径（⛔ 在 ⇒ `None`）。"""
    for c in CHROME_CANDIDATES:
        if c and os.path.isfile(c):
            return c
    return None


def _rand(n=8):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")


def _append(row):
    u"""入账（⛔ 静默：⛔ 成 ⇒ 唯返 `False` —— 其报归齿）。"""
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        with open(LEDGER, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return True
    except Exception:
        return False


def read_ledger():
    u"""读账（逐行 ⇒ `dict`）；⛔ 在 ⇒ `[]`。"""
    out = []
    if not os.path.isfile(LEDGER):
        return out
    try:
        import io
        for ln in io.open(LEDGER, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    except Exception:
        pass
    return out


def _ps_chrome():
    u"""chrome.exe 之 `(pid,ppid,cmd)`（经 PowerShell · **只读**）。"""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
          "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress")
    r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120, creationflags=NO_WINDOW)
    if r.returncode != 0 or not (r.stdout or "").strip():
        raise RuntimeError("powershell rc=%s" % r.returncode)
    d = json.loads(r.stdout)
    return d if isinstance(d, list) else [d]


def _strays_from_rows(rows):
    u"""**纯逻辑**：chrome 之 `(ProcessId,ParentProcessId,Name,CommandLine)` 之列 ⇒ 散落之 `[(pid, profile, port)]`。

    ⭐ 判（同 TD 之只读器 · 承 pm_1898 §三）：① 命令行含 `--headless` ② 其父**非** `chrome.exe`（＝根实例）
    ⇒ 记一枚根；其子随根走（⛔ 各计）。⛔ 触真机 ⇒ 供齿喂假行。
    """
    by_id = {}
    for p in rows:
        by_id[int(p.get("ProcessId") or 0)] = p
    out = []
    for p in rows:
        cmd = p.get("CommandLine") or ""
        if "--headless" not in cmd:
            continue
        par = by_id.get(int(p.get("ParentProcessId") or 0))
        if par is not None and str(par.get("Name", "")).lower() == "chrome.exe":
            continue
        profile = ""
        port = 0
        for tok in cmd.split():
            if tok.startswith("--user-data-dir="):
                profile = tok.split("=", 1)[1].strip(chr(34))
            elif tok.startswith("--remote-debugging-port="):
                try:
                    port = int(tok.split("=", 1)[1])
                except Exception:
                    port = 0
        out.append((int(p.get("ProcessId") or 0), profile, port))
    return sorted(out)


def strays():
    u"""散落之无头实例 —— 先引 TD 之只读器（`--json`）⇒ ⛔ 在 ⇒ 以己之 PS 取。

    ⭐ 「散落」之判（同 TD 之器）：根实例（其父非 `chrome.exe`）∧ 命令行含 `--headless`。
    返 `[(pid, profile, port), ...]`。
    """
    if os.path.isfile(TD_VIEWER):
        try:
            r = subprocess.run(["python", "-X", "utf8", "-B", TD_VIEWER, "--json"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=180, creationflags=NO_WINDOW)
            if r.returncode in (0, 1):
                d = json.loads((r.stdout or "").strip().splitlines()[-1])
                return [(int(x[0]), str(x[3]), int(x[2])) for x in d.get("strays", [])]
        except Exception:
            pass
    try:
        rows = _ps_chrome()
    except Exception:
        return []
    return _strays_from_rows(rows)


def my_profiles():
    r"""`%TEMP%\cw*` 之目录（我席之名约 · ⛔ 他径）。"""
    d = TEMP
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, n) for n in os.listdir(d)
            if n.lower().startswith("cw") and os.path.isdir(os.path.join(d, n))]


def _kill_tree(pid):
    u"""杀其树（Windows：`taskkill /T /F`）；返 `True` ＝ 已尽。"""
    try:
        r = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, creationflags=NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


def _pid_alive(pid):
    try:
        r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, creationflags=NO_WINDOW)
        return str(pid) in (r.stdout or "")
    except Exception:
        return False


@contextlib.contextmanager
def run_headless(port, tag="t", wait_s=6.0, extra=(), why=""):
    u"""起 ⇒ 用 ⇒ **finally 收** ⇒ 入账（一处收四步）。

    ⭐ `tag` 用 `cw<号>*` 之名约（承 TD 之器之归属 · ⛔ 他名 ⇒ 归属 `?`）。
    收之三步：① `taskkill /T /F`（根 ＋ 其子）② 删其 profile（⛔ 留残）③ 入账（pid ／ 口 ／ profile ／ 收否）。
    """
    exe = chrome_exe()
    if not exe:
        raise RuntimeError(u"chrome.exe ⛔ 在 ⇒ ⛔ 起")
    prof = os.path.join(TEMP, "cw%s_%s" % (tag, _rand()))
    args = [exe, "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--remote-debugging-port=%d" % int(port),
            "--user-data-dir=" + prof, "--window-size=1440,900", "about:blank"]
    args.extend(extra)
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=NO_WINDOW)
    p.cw_profile = prof          # ⭐ 附于 proc：供齿核（profile 已去否）
    p.cw_port = int(port)
    row = {"ts": _now(), "pid": p.pid, "port": int(port), "profile": prof,
           "reaped": False, "why": why or tag}
    t0 = time.time()
    try:
        while time.time() - t0 < wait_s:
            try:
                import socket
                s = socket.create_connection(("127.0.0.1", int(port)), 0.4)
                s.close()
                break
            except Exception:
                time.sleep(0.25)
        yield p
    finally:
        _kill_tree(p.pid)
        for _ in range(40):
            if not _pid_alive(p.pid):
                break
            time.sleep(0.25)
        row["reaped"] = not _pid_alive(p.pid)
        try:
            if os.path.isdir(prof):
                shutil.rmtree(prof, ignore_errors=True)
        except Exception:
            pass
        row["profile_gone"] = not os.path.isdir(prof)
        _append(row)


def reap(pid, profile=None, why="reap"):
    u"""收一枚（`taskkill /T /F` ＋ 删 profile）⇒ 入账 ⇒ 返 `True` ＝ 已尽。

    ⭐ 「**跑毕必收**」之二径之一（另一径 ＝ `run_headless` 之 `finally`）：凡我席之散落实例 ⇒ 走此路收 ＋ 入账。
    """
    _kill_tree(int(pid))
    for _ in range(40):
        if not _pid_alive(int(pid)):
            break
        time.sleep(0.25)
    gone = not _pid_alive(int(pid))
    gone_prof = True
    if profile:
        try:
            if os.path.isdir(profile):
                shutil.rmtree(profile, ignore_errors=True)
            gone_prof = not os.path.isdir(profile)
        except Exception:
            gone_prof = False
    _append({"ts": _now(), "pid": int(pid), "port": 0, "profile": profile or "",
             "reaped": gone, "profile_gone": gone_prof, "why": why})
    return gone
