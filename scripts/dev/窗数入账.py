# -*- coding: utf-8 -*-
"""窗数入账 —— 「白幕 ×2」之齿（**只读** · ⛔ 不动机务 · 唯加一行账）

承 pm_1913 §二.3 之准（低险 ∧ 只读 ∧ 落 ``scripts/dev/**``）：
每次采 ⇒ 账增三栏 —— **可见窗之数** ／ **其题**（前 60 字）／ **其 rect**（＋ 旗）。

用法::

    python -X utf8 -B scripts/dev/窗数入账.py                    # 采一次 ⇒ 入账（人读表）
    python -X utf8 -B scripts/dev/窗数入账.py --json             # 机读本次
    python -X utf8 -B scripts/dev/窗数入账.py --quiet            # 唯入账（⛔ 打印）
    python -X utf8 -B scripts/dev/窗数入账.py --show 20          # 唯读账尾（⛔ 采样）
    python -X utf8 -B scripts/dev/窗数入账.py --watch 5 --for 60 # 每 5 s 采 · 共 60 s（捕瞬态）
    python -X utf8 -B scripts/dev/窗数入账.py --self-test

账：``<repo>/data/tmp/cdp/_guard/guard_windows_probe.jsonl``（一行一次 · **只增** ·
⛔ 不动 guard 之既存账 ／ ⛔ 动 ``guard_chrome.ps1`` 之行为）。

判（白幕之形 · 承 pm_1913 §二 · 唯**报告**）：
  ① **PA 之可见窗 ≥ 2** ⇒ 疑「白幕 ×2」
  ② 任一可见窗 **离屏**（与**虚拟屏**不相交 ∧ ⛔ 最小化）∨ **零尺寸** ⇒ 疑「离屏首绘」

⭐⭐ 一手之正（本器 v1 之自正 · 即刻见 `--self-test` 之「最小化」例）：
  ``IsWindowVisible`` 于**最小化**之窗亦返 ``True`` ∧ 其 ``rect`` 恒 ``(-32000, -32000, …)``
  ⇒ ⭐ **``-32000`` 恒为「最小化」之常形**（⛔ 离屏首绘）⇒ 判据须以 ``IsIconic`` 为准
  （⛔ 以 ``rect`` 猜 —— 否则**假红**）。

⚠ 「可见」＝ ``IsWindowVisible`` ∧ **有题** ⇒ 器 ⛔ 关窗 ／ ⛔ 杀进程 ／ ⛔ 发消息 ／ ⛔ 读屏。
退出码: 0 = 常态 ｜ 1 = 疑（白幕之形）｜ 2 = 采样失败 ｜ 3 = 入参错
"""
import ctypes
import io
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
TITLE_HEAD = 60
PA_MARK = "ClawsJoy PA"
MINIMIZED_AT = -30000          # 唯作「⛔ 读得虚拟屏」时之兜底之据（真判以 IsIconic 为准）
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACCOUNT = os.path.join(REPO, "data", "tmp", "cdp", "_guard", "guard_windows_probe.jsonl")


# ---------------------------------------------------------------- 判（纯逻辑）
def head(title, n=TITLE_HEAD):
    """题之头（⛔ 换行 · 超长截）。"""
    return " ".join(str(title or "").split())[:n]


def intersects(rect, vs):
    """窗之 rect 与**虚拟屏** ``(x, y, w, h)`` 相交否 —— ⛔ 读得虚拟屏 ⇒ 恒 ``True``（免假红）。"""
    l, t, r, b = [int(x) for x in rect]
    vx, vy, vw, vh = [int(x) for x in vs]
    if vw <= 0 or vh <= 0:
        return True
    return not (r <= vx or l >= vx + vw or b <= vy or t >= vy + vh)


def window_row(w):
    """一窗 ⇒ 一行（pid ／ 题 ／ rect ／ 旗）—— ⭐ 最小化 ≠ 离屏（v1 之自正）。"""
    l, t, r, b = [int(x) for x in (w.get("rect") or (0, 0, 0, 0))]
    flags = []
    if w.get("iconic"):
        flags.append("minimized")
    else:
        if not intersects((l, t, r, b), w.get("vs") or (0, 0, 0, 0)):
            flags.append("offscreen")
        if (r - l) <= 0 or (b - t) <= 0:
            flags.append("zero-size")
    if PA_MARK in str(w.get("title") or ""):
        flags.append("pa")
    return {"pid": int(w.get("pid") or 0), "title": head(w.get("title")),
            "rect": [l, t, r, b], "flags": flags}


def classify_visible(windows, chrome_pids):
    """⇒ 可见之 chrome 窗（pid ∈ chrome_pids ∧ visible ∧ 有题）· 按 (pid, hwnd) 排。"""
    pids = set(int(p) for p in (chrome_pids or []))
    out = []
    for w in windows or []:
        if not w.get("visible"):
            continue
        if int(w.get("pid") or 0) not in pids:
            continue
        if not str(w.get("title") or "").strip():
            continue
        out.append(w)
    return sorted(out, key=lambda w: (int(w.get("pid") or 0), int(w.get("hwnd") or 0)))


def build_record(windows, chrome_pids, ts, chrome_total=None, hidden_with_title=None):
    """窗之列 ⇒ 一行账（纯逻辑 · ⛔ 碰机）。"""
    rows = [window_row(w) for w in classify_visible(windows, chrome_pids)]
    pa = [x for x in rows if "pa" in x["flags"]]
    mini = [x for x in rows if "minimized" in x["flags"]]
    bias = [x for x in rows if ("offscreen" in x["flags"]) or ("zero-size" in x["flags"])]
    suspect = []
    if len(pa) >= 2:
        suspect.append("pa-windows>=2（疑白幕 ×2）")
    if bias:
        suspect.append("offscreen-or-zero（疑离屏首绘）")
    return {
        "ts": ts,
        "chrome_procs": chrome_total,
        "visible_chrome": len(rows),
        "visible_pa": len(pa),
        "visible_minimized": len(mini),
        "hidden_chrome_with_title": hidden_with_title,
        "windows": rows,
        "suspect": suspect,
        "verdict": "suspect" if suspect else "ok",
    }


def rc_of(rec):
    return 1 if rec.get("suspect") else 0


def jsonl_of(rec):
    return json.dumps(rec, ensure_ascii=False, separators=(",", ":"))


def fmt_lines(rec):
    out = ["窗数入账 · %s ｜ 可见之 chrome 窗 %d（PA %d · 其中最小化 %d）｜ 判 ＝ %s"
           % (rec["ts"], rec["visible_chrome"], rec["visible_pa"], rec["visible_minimized"], rec["verdict"])]
    for w in rec["windows"]:
        out.append("  可见 pid=%-7s rect=%-24s %s ｜ %s"
                   % (w["pid"], str(w["rect"]),
                      ("[" + " ／ ".join(w["flags"]) + "]") if w["flags"] else "[—]", w["title"]))
    if not rec["windows"]:
        out.append("  （无可见之 chrome 窗）")
    for s in rec["suspect"]:
        out.append("  ⚠ 疑：" + s)
    return out


# ---------------------------------------------------------------- 采样（唯读）
def sample_windows():
    """枚举顶层窗 ⇒ [{hwnd, pid, title, rect, visible, iconic, vs}]（⛔ 发消息 ／ ⛔ 关窗）。"""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    out = []

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = (WNDENUMPROC, wintypes.LPARAM)
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = (wintypes.HWND,)
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = (wintypes.HWND,)
    user32.IsIconic.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(RECT))
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetSystemMetrics.argtypes = (ctypes.c_int,)
    user32.GetSystemMetrics.restype = ctypes.c_int

    # SM_XVIRTUALSCREEN 76 ／ SM_YVIRTUALSCREEN 77 ／ SM_CXVIRTUALSCREEN 78 ／ SM_CYVIRTUALSCREEN 79
    vs = (user32.GetSystemMetrics(76), user32.GetSystemMetrics(77),
          user32.GetSystemMetrics(78), user32.GetSystemMetrics(79))

    def cb(hwnd, _lp):
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 2)
        user32.GetWindowTextW(hwnd, buf, n + 2)
        rc = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rc))
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append({
            "hwnd": int(hwnd),
            "pid": int(pid.value),
            "title": buf.value or "",
            "rect": (rc.left, rc.top, rc.right, rc.bottom),
            "visible": bool(user32.IsWindowVisible(hwnd)),
            "iconic": bool(user32.IsIconic(hwnd)),
            "vs": vs,
        })
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def sample_chrome():
    """chrome.exe 之 pid 集（经 PowerShell · 唯读）⇒ (pids, total)。"""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
          "Select-Object ProcessId | ConvertTo-Json -Compress")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    if out.returncode != 0:
        raise RuntimeError("powershell rc=%s %s" % (out.returncode, (out.stderr or "")[:200]))
    raw = (out.stdout or "").strip()
    if not raw:
        return [], 0
    data = json.loads(raw)
    rows = data if isinstance(data, list) else [data]
    pids = [int(r.get("ProcessId") or 0) for r in rows]
    return pids, len(pids)


def append_account(rec, path=ACCOUNT):
    """一行入账（**只增** · LF · utf-8）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "a", encoding="utf-8", newline="") as f:
        f.write(jsonl_of(rec) + chr(10))
    return path


def read_tail(path=ACCOUNT, n=10):
    if not os.path.exists(path):
        return []
    lines = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    return [l for l in lines if l.strip()][-int(n):]


def now_ts():
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def take_one(chrome_pids=None, chrome_total=None):
    """采一次 ⇒ 一行账（并回）。"""
    if chrome_pids is None:
        chrome_pids, chrome_total = sample_chrome()
    wins = sample_windows()
    pids = set(chrome_pids)
    hidden = [w for w in wins if (not w.get("visible")) and int(w.get("pid") or 0) in pids
              and str(w.get("title") or "").strip()]
    rec = build_record(wins, chrome_pids, now_ts(), chrome_total=chrome_total,
                       hidden_with_title=len(hidden))
    append_account(rec)
    return rec


# ---------------------------------------------------------------- 自证（纯逻辑）
def _self_test():
    cases = []
    def W(hwnd, pid, title, rect, vis=True, iconic=False, vs=(0, 0, 2560, 1440)):
        return {"hwnd": hwnd, "pid": pid, "title": title, "rect": rect,
                "visible": vis, "iconic": iconic, "vs": vs}
    pa = "ClawsJoy PA · v3 工作台（3 主面 · 同源真页） - Google Chrome"
    MINI = (-32000, -32000, -31840, -31972)
    cases.append(("正控.一扇可见 PA 窗（正位）⇒ ok",
                  build_record([W(1, 100, pa, (0, 0, 1600, 900))], [100], "t1")["verdict"] == "ok"))
    cases.append(("正控.rc ＝ 0",
                  rc_of(build_record([W(1, 100, pa, (0, 0, 1600, 900))], [100], "t1")) == 0))
    cases.append(("⭐一手.最小化（iconic · rect -32000）⇒ ⛔ 疑（v1 之自正）",
                  rc_of(build_record([W(1, 100, pa, MINI, iconic=True)], [100], "t1")) == 0
                  and "minimized" in build_record([W(1, 100, pa, MINI, iconic=True)],
                                                  [100], "t1")["windows"][0]["flags"]))
    cases.append(("反控.非最小化 ∧ 离屏 ⇒ 疑 offscreen",
                  rc_of(build_record([W(1, 100, pa, (-32000, -32000, -31840, -31972),
                                        iconic=False)], [100], "t1")) == 1))
    cases.append(("反控.二扇可见 PA 窗 ⇒ 疑白幕 ×2",
                  "pa-windows>=2（疑白幕 ×2）" in build_record(
                      [W(1, 100, pa, (0, 0, 900, 600)), W(2, 100, pa, (0, 0, 900, 600))],
                      [100], "t1")["suspect"]))
    cases.append(("反控.零尺寸（非最小化）⇒ 亦疑",
                  rc_of(build_record([W(1, 100, pa, (0, 0, 0, 0))], [100], "t1")) == 1))
    cases.append(("反控.不可见窗 ⛔ 入可见",
                  build_record([W(1, 100, pa, (0, 0, 900, 600), vis=False)], [100], "t1")["visible_chrome"] == 0))
    cases.append(("反控.非 chrome pid 之窗 ⛔ 入",
                  build_record([W(1, 42, "记事本", (0, 0, 900, 600))], [100], "t1")["visible_chrome"] == 0))
    cases.append(("反控.虚拟屏读不到 ⇒ ⛔ 假红（相交恒 True）",
                  intersects((-32000, -32000, -31840, -31972), (0, 0, 0, 0)) is True))
    cases.append(("空例.无窗 ⇒ ok",
                  build_record([], [], "t1")["verdict"] == "ok"))
    cases.append(("题.截 60 字",
                  len(build_record([W(1, 100, "x" * 200, (0, 0, 900, 600))], [100], "t1")["windows"][0]["title"]) == TITLE_HEAD))
    rec = build_record([W(1, 100, pa, (0, 0, 1600, 900))], [100], "t1", chrome_total=7)
    try:
        json.loads(jsonl_of(rec))
        cases.append(("账.行可 json 回读", True))
    except Exception:
        cases.append(("账.行可 json 回读", False))
    ok = sum(1 for _, v in cases if v)
    for name, v in cases:
        print("  [%s] %s" % ("PASS" if v else "FAIL", name))
    print("%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


# ---------------------------------------------------------------- 入口
def _arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def main():
    if "--self-test" in sys.argv:
        return _self_test()
    known_flags = {"--json", "--quiet", "--self-test", "--show", "--watch", "--for"}
    argv = sys.argv[1:]
    bad = []
    for i, a in enumerate(argv):
        if a in known_flags:
            continue
        if a.lstrip("-").isdigit() and i > 0 and argv[i - 1] in ("--show", "--watch", "--for"):
            continue
        bad.append(a)
    if bad:
        print("rc=3 入参错: " + repr(bad))
        return 3
    if "--show" in argv:
        lines = read_tail(ACCOUNT, int(_arg("--show", 10)))
        if not lines:
            print("（账空 ∨ 账不在：%s）" % ACCOUNT)
            return 0
        for l in lines:
            print(l)
        return 0
    watch = _arg("--watch")
    if watch:
        step = max(1, int(watch))
        total = int(_arg("--for", 60))
        worst = 0
        t0 = time.time()
        while (time.time() - t0) < total:
            try:
                rec = take_one()
            except Exception as e:
                print("rc=2 采样失败: %s" % e)
                return 2
            if "--quiet" not in argv:
                for l in fmt_lines(rec):
                    print(l)
            worst = max(worst, rc_of(rec))
            time.sleep(step)
        print("[彻] 共 %d s ／ 每 %d s 一采 ⇒ 最坏判 ＝ %s" % (total, step, "疑" if worst else "常态"))
        return worst
    try:
        rec = take_one()
    except Exception as e:
        print("rc=2 采样失败: %s" % e)
        return 2
    if "--json" in argv:
        print(jsonl_of(rec))
    elif "--quiet" not in argv:
        for l in fmt_lines(rec):
            print(l)
        print("  账：%s" % ACCOUNT)
    return rc_of(rec)


if __name__ == "__main__":
    sys.exit(main())
