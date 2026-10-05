# -*- coding: utf-8 -*-
r"""PA 断点续之只读面（T2-刀6 §二 · 2026-10-05 · 技术总监 f202f89）。

【老板之裁】(乙) 本机自启 ＋ 断点续：**关机期间攒件 · 开机接着干**（⛔ 花钱 ／ ⛔ 云侧）。

【本模块为谁】`GET /v9/pa/resume` 之载荷。**跑器** ＝ `scripts\win_pa\boot_resume.py`
  （⚠ 该件**非本席所落**（本席 16:2x 探时已在 · mtime 16:16:44）⇒ ⛔ 覆；本面 **唯读其真源** ⇒ **⛔ 两套读者**）：
  水印 `data\v9\pa\resume.json`（`{version, last_boot_at, prev_boot_at, done{inbox,mail}, last_counts}`）
  ／ 台账 `data\v9\pa\boot_log.jsonl` ／ 攒件箱 `inbox\`（`_` 起头者 ⛔ 计 · 收走者入 `inbox\_done\`）
  ／ 离线刻 `logs\win_pa.stopped.json` ／ 未竟 `ledger.json` ＋ `dispatch.jsonl`
  ／ 信通未读（真源 `_tools\xintong_tick.py --json --all`）。

【两律（承令）】
  · **只读**：本模块 ⛔ 写任何一侧；`readonly_manifest()` 以**两读同印**自证（⛔ 自报「我只读」）。
  · ⭐ **数须标其出**：「攒件数／续办数／失败件」＝**末次开机账**（跑器自落）⇒ 本面**照录**；
    「幂等跳过数」跑器**未报** ⇒ 本面**自算**（⛔ 以自算充其报 · 明标「本面自算」）。
    ⚠ 无台账 ⇒ 面明报「**未跑**」（⛔ 以 `0` 充「无攒件」）。
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from core.pa import _proc as _proc   # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）

RESUME_VERSION = "2026-10-05.2"
REPO_ROOT = Path(__file__).resolve().parents[2]

XT_TICK = Path(os.getenv("PA_XT_TICK") or r"D:\paseo-workspace\_tools\xintong_tick.py")
XT_DIR = Path(os.getenv("PA_XT_DIR") or r"D:\Obsidian\ClawsJoy\ClawsJoy\内容工坊\02_协作\信通")
SEAT_NAME = os.getenv("PA_RESUME_SEAT_NAME") or "技术总监"


def _sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def root_of(root=None):
    return Path(root or os.getenv("PA_ROOT") or REPO_ROOT)


def data_dir(root=None):
    env = os.getenv("PA_DATA_DIR")
    if env:
        return Path(env)
    return root_of(root) / "data" / "v9" / "pa"


def paths(root=None):
    r = root_of(root)
    d = data_dir(root)
    return {"root": str(r), "data": str(d),
            "watermark": str(d / "resume.json"), "boot_log": str(d / "boot_log.jsonl"),
            "inbox": str(d / "inbox"), "inbox_done": str(d / "inbox" / "_done"),
            "ledger": str(d / "ledger.json"), "dispatch": str(d / "dispatch.jsonl"),
            "stopped": str(r / "logs" / "win_pa.stopped.json"), "life": str(r / "logs" / "win_pa_life.jsonl"),
            "runner": str(r / "scripts" / "win_pa" / "boot_resume.py"),
            "xt_tick": str(XT_TICK), "xt_dir": str(XT_DIR), "seat_name": SEAT_NAME}


def _bytes(p):
    try:
        return Path(p).read_bytes()
    except Exception:
        return None


def _read_json(p):
    b = _bytes(p)
    if b is None:
        return None, "缺"
    try:
        return json.loads(b.decode("utf-8-sig")), ""
    except Exception as e:
        return None, "坏（%s）" % type(e).__name__


# ------------------------------ 跑器之面 ------------------------------
def runner_face(root=None):
    """**跑器**（`scripts\\win_pa\\boot_resume.py`）之身份（唯读 · ⛔ 覆其件）。"""
    p = Path(paths(root)["runner"])
    b = _bytes(p)
    if b is None:
        return {"path": str(p), "state": "缺（⛔ 未落 ⇒ 本面之数皆 `0` 乃**未跑**）", "sha16": None}
    src = b.decode("utf-8", "replace")
    def _g(pat):
        m = re.search(pat, src)
        return (m.group(1) if m else None)
    return {"path": str(p), "state": "在", "sha16": _sha16(b), "bytes": len(b),
            "reader": _g(r'READER\s*=\s*"([^"]*)"'), "version": _g(r'VERSION\s*=\s*([0-9]+)'),
            "gather_cap": _g(r'GATHER_CAP\s*=\s*([0-9]+)'),
            "注": "本席 ⛔ 覆此件（**基不 ⇒ 停手** · 承落盘闸 ⒉）；本面**唯读**其真源"}


# ------------------------------ 水印 ＋ 台账 ------------------------------
def watermark(root=None):
    P = paths(root)
    doc, err = _read_json(P["watermark"])
    b = _bytes(P["watermark"])
    if doc is None:
        return {"state": ("缺（⛔ 未跑过 ⇒ 无水位）" if err == "缺" else err), "path": P["watermark"],
                "doc": {}, "sha16": None}
    if not isinstance(doc, dict):
        return {"state": "坏（须为对象）", "path": P["watermark"], "doc": {},
                "sha16": (None if b is None else _sha16(b))}
    return {"state": "在", "path": P["watermark"], "doc": doc,
            "sha16": (None if b is None else _sha16(b))}


def boot_log_tail(root=None, n=1):
    P = paths(root)
    p = Path(P["boot_log"])
    if not p.is_file():
        return [], {"path": str(p), "state": "缺（⛔ 未跑过）", "n": 0, "lines": 0}
    lines = [x for x in (_bytes(p) or b"").decode("utf-8", "replace").splitlines() if x.strip()]
    rows = []
    for ln in lines[-max(int(n), 1):]:
        try:
            rows.append(json.loads(ln))
        except Exception:
            rows.append({"_坏行": ln[:160]})
    return rows, {"path": str(p), "state": "在", "n": len(rows), "lines": len(lines),
                  "sha16": _sha16(_bytes(p) or b"")}


def stopped_epoch(root=None):
    P = paths(root)
    doc, err = _read_json(P["stopped"])
    if not isinstance(doc, dict):
        return None, "缺（%s）" % err
    try:
        return float(doc.get("epoch")), "%s（ts=%s ／ by=%s）" % (P["stopped"], doc.get("ts"), doc.get("by"))
    except Exception:
        return None, "坏（epoch 不可用：%s）" % doc.get("ts")


# ------------------------------ 攒件（现况 · 本面自算） ------------------------------
def inbox_now(root=None):
    P = paths(root)
    d = Path(P["inbox"])
    out, done_n = [], 0
    if not d.is_dir():
        return out, done_n, {"path": str(d), "state": "缺（⛔ 未跑过 ⇒ 其器首跑会建）", "n": 0}
    for f in sorted(d.iterdir()):
        if f.is_dir() or f.name.startswith("_") or f.name.endswith(".tmp"):
            continue
        b = _bytes(f)
        out.append({"id": f.name, "path": str(f), "sha16": _sha16(b or b""),
                    "mtime": (f.stat().st_mtime if f.exists() else None)})
    dd = Path(P["inbox_done"])
    if dd.is_dir():
        done_n = len([x for x in dd.iterdir() if x.is_file()])
    return out, done_n, {"path": str(d), "state": "在", "n": len(out), "n_done": done_n}


def xt_unread(root=None, timeout=240):
    P = paths(root)
    p = Path(P["xt_tick"])
    if not p.is_file():
        return {"rc": None, "err": "轮询器缺：%s" % p, "all": [], "raw_sha16": None}
    try:
        r = _proc.run_hidden([sys.executable, "-X", "utf8", str(p), "--json", "--all"],
                           capture_output=True, timeout=timeout, cwd=str(p.parent))
    except Exception as e:
        return {"rc": None, "err": "调起失败：%s" % type(e).__name__, "all": [], "raw_sha16": None}
    raw = r.stdout or b""
    try:
        doc = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        doc = None
    if doc is None:
        return {"rc": r.returncode, "err": "输出不可解析（rc=%s ⇒ 3=读数失败）" % r.returncode,
                "all": [], "raw_sha16": _sha16(raw)}
    return {"rc": r.returncode, "err": ("" if r.returncode in (0, 1) else "rc=%s（3=读数失败）" % r.returncode),
            "all": list(doc.get("all") or []), "total": doc.get("total"), "legacy": doc.get("legacy"),
            "baseline": doc.get("baseline"), "unread": doc.get("unread"),
            "raw_sha16": _sha16(raw), "cmd": "python xintong_tick.py --json --all"}


def xt_split(root=None, window=None, timeout=240):
    """信通未读之三分（⛔ ack ／ ⛔ 吞积压）：窗内（≥ 其窗）／ 窗外（遗留）／ 其中发本席。"""
    q = xt_unread(root=root, timeout=timeout)
    win_e = None
    if window:
        try:
            win_e = time.mktime(time.strptime(str(window), "%Y-%m-%d %H:%M:%S"))
        except Exception:
            win_e = None
    inw, outw, mine = [], [], []
    for nm in q.get("all") or []:
        nm = str(nm)
        fp = Path(paths(root)["xt_dir"]) / nm
        try:
            mt = fp.stat().st_mtime
        except Exception:
            mt = None
        rec = {"name": nm, "mtime": mt, "path": str(fp)}
        if win_e is None or (mt is not None and mt >= win_e):
            inw.append(rec)
        else:
            outw.append(rec)
        if ("to_%s" % SEAT_NAME) in nm:
            mine.append(rec)
    q = dict(q)
    q.update({"窗口": window, "窗口之由": "其器之筛 ＝ `mtime ≥ 水印 last_boot_at`（⛔ 无水印 ⇒ ⛔ 收）",
              "窗内未读_n": len(inw), "窗外遗留_n": len(outw), "发本席_n": len(mine),
              "窗内未读": [x["name"] for x in inw][:50], "发本席": [x["name"] for x in mine][:50],
              "dir": paths(root)["xt_dir"]})
    return q


def skipped_selfcalc(root=None):
    """**本面自算**之幂等跳过数（其器未报 `skipped`）：inbox 现存 ∩ 水印 done ／ 窗内未读 ∩ done.mail。"""
    wm = watermark(root).get("doc") or {}
    done = wm.get("done") or {}
    di = set(str(x) for x in (done.get("inbox") or []))
    dm = set(str(x) for x in (done.get("mail") or []))
    ib, _dn, _m = inbox_now(root)
    s_i = sorted(x["id"] for x in ib if x["id"] in di)
    q = xt_split(root=root, window=wm.get("last_boot_at"))
    s_m = sorted(n for n in (q.get("窗内未读") or []) if n in dm)
    return {"幂等跳过数": len(s_i) + len(s_m), "inbox": len(s_i), "mail": len(s_m),
            "由": "本面自算（跑器**未报** `skipped` ⇒ ⛔ 以自算充其报）；面 ＝ inbox 现存 ∩ done.inbox ／ 窗内未读 ∩ done.mail"}


# ------------------------------ 未竟 ------------------------------
def ledger_unfinished(root=None):
    P = paths(root)
    doc, err = _read_json(P["ledger"])
    if not isinstance(doc, dict):
        return [], {"path": P["ledger"], "state": err, "n": 0}
    today = time.strftime("%Y-%m-%d")
    out = []
    for it in (doc.get("items") or []):
        if str((it or {}).get("status") or "").lower() not in ("done", "closed", "取消"):
            due = (it or {}).get("due")
            out.append({"id": str(it.get("id")), "title": str(it.get("title"))[:80],
                        "kind": it.get("kind"), "status": it.get("status"), "due": due,
                        "到期": bool(due and str(due) <= today), "src": P["ledger"]})
    return out, {"path": P["ledger"], "state": "在", "n": len(out)}


def dispatch_unfinished(root=None):
    P = paths(root)
    p = Path(P["dispatch"])
    if not p.is_file():
        return [], {"path": str(p), "state": "缺", "n": 0}
    last = {}
    for ln in (_bytes(p) or b"").decode("utf-8", "replace").splitlines():
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if isinstance(r, dict) and str(r.get("task_id") or "").strip():
            last[str(r["task_id"])] = r
    out = [{"id": k, "status": v.get("status"), "to_seat": v.get("to_seat"), "stage": v.get("stage"),
            "ts": v.get("ts"), "src": str(p)}
           for k, v in sorted(last.items())
           if str(v.get("status") or "").lower() not in ("done", "closed", "failed")]
    return out, {"path": str(p), "state": "在", "n": len(out), "rows": len(last),
                 "注": "其器之筛：`status ∉ {done, closed, failed}`（本面照录其筛 · 另列 failed 之数）"}


# ------------------------------ 只读对表 ------------------------------
def _dir_fp(d):
    d = Path(d)
    if not d.is_dir():
        return None
    parts = []
    for f in sorted(d.iterdir()):
        try:
            st = f.stat()
            parts.append("%s:%d:%d" % (f.name, st.st_size, int(st.st_mtime)))
        except Exception:
            parts.append("%s:?" % f.name)
    return _sha16("|".join(parts).encode("utf-8"))


def readonly_manifest(root=None):
    """⭐ 只读之自证：诸源之印**两读**（⛔ 自报「我只读」）。
    ⚠ 面外之写者（跑器 ／ 他席）可使某源两读异 ⇒ **照实**（⛔ 以「应同」强说同）。"""
    def snap():
        P = paths(root)
        return {"水印": _sha16(_bytes(P["watermark"]) or b""),
                "台账": _sha16(_bytes(P["boot_log"]) or b""),
                "攒件箱": _dir_fp(P["inbox"]),
                "停刻": _sha16(_bytes(P["stopped"]) or b""),
                "起停痕": _sha16(_bytes(P["life"]) or b""),
                "ledger": _sha16(_bytes(P["ledger"]) or b""),
                "dispatch": _sha16(_bytes(P["dispatch"]) or b""),
                "跑器": _sha16(_bytes(P["runner"]) or b""),
                "信通未读": xt_unread(root=root).get("raw_sha16")}
    a, b = snap(), snap()
    diff = sorted(k for k in a if a.get(k) != b.get(k))
    return {"before": a, "after": b, "same": (not diff), "diff": diff,
            "src": "本模块两读（唯读）· 面 ＝ " + " ／ ".join(sorted(a))}


# ------------------------------ 面 ------------------------------
def build_resume(root=None, route_code_sha16=None):
    P = paths(root)
    wm = watermark(root)
    docs = wm.get("doc") or {}
    logs, log_meta = boot_log_tail(root, 1)
    last = logs[-1] if logs else {}
    runner = runner_face(root)
    ib, ib_done, ib_meta = inbox_now(root)
    xt = xt_split(root=root, window=docs.get("last_boot_at"))
    led, led_meta = ledger_unfinished(root)
    dsp, dsp_meta = dispatch_unfinished(root)
    man = readonly_manifest(root)
    st_e, st_src = stopped_epoch(root)
    off_since = (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st_e)) if st_e else None)
    off_s = (round(time.time() - st_e, 1) if st_e else None)
    _gathered = last.get("gathered")
    _resumed = last.get("resumed")
    照实 = []
    if not logs:
        照实.append("无台账（⛔ 未跑过 `boot_resume.py`）⇒ 「攒件数／续办数」之 `0` 乃**未跑**，⛔ 非「无攒件」")
    if wm["state"].startswith("缺"):
        照实.append("无水印 ⇒ 跑器之信通窗**无**（其器明书：无水印 ⇒ ⛔ 收信通）")
    done = docs.get("done") or {}
    out = {
        "ok": True, "at": _now(), "face": "resume", "version": RESUME_VERSION,
        "上次断点": {"last_boot_at": docs.get("last_boot_at"), "prev_boot_at": docs.get("prev_boot_at"),
                  "version": docs.get("version"), "state": wm["state"], "path": wm["path"],
                  "sha16": wm["sha16"], "done": {"inbox": len(done.get("inbox") or []),
                                                "mail": len(done.get("mail") or [])}},
        "离线区间": {"停刻": off_since, "停刻之由": st_src, "离线秒": off_s,
                  "末次开机": last.get("boot_at"), "末次之墙钟": last.get("wall_s"),
                  "注": "其器之信通窗 ＝ 水印 `last_boot_at`（⛔ 停刻）；停刻唯本面之补读"},
        "攒件数": _gathered, "续办数": _resumed,
        "幂等跳过数": skipped_selfcalc(root)["幂等跳过数"],
        "失败件": list(last.get("failed") or []),
        "数之出": {"攒件数／续办数／失败件": "末次开机账（`boot_log.jsonl` 末行 · 跑器自落）⇒ **照录**",
                 "幂等跳过数": skipped_selfcalc(root)["由"]},
        "未竟": {"n": len(led) + len(dsp), "ledger": led, "dispatch": dsp,
               "其器之报": {"open_ledger": last.get("open_ledger"), "open_dispatch": last.get("open_dispatch")},
               "注": "未竟**单列** ⇒ ⛔ 入「续办数」（免「以存量充新办」）；本面 ⛔ 改其状态",
               "src": {"ledger": led_meta, "dispatch": dsp_meta}},
        "水印值": {"path": wm["path"], "sha16": wm["sha16"], "state": wm["state"],
                "last_boot_at": docs.get("last_boot_at"), "prev_boot_at": docs.get("prev_boot_at"),
                "done_inbox_n": len(done.get("inbox") or []), "done_mail_n": len(done.get("mail") or []),
                "last_counts": docs.get("last_counts")},
        "跑器": runner,
        "只读对表": man,
        "现况": {"攒件箱": ib_meta, "信通": {k: xt.get(k) for k in
                ("rc", "err", "cmd", "baseline", "total", "legacy", "unread", "窗口", "窗口之由",
                 "窗内未读_n", "窗外遗留_n", "发本席_n", "窗内未读", "发本席", "dir")},
               "本面之攒件（inbox）": [x["id"] for x in ib][:50]},
        "末次开机账": last,
        "面之径": P,
    }
    if 照实:
        out["照实"] = 照实
    _面 = "GET /v9/pa/resume"
    _滤 = "唯读（水印 ／ 台账 ／ inbox ／ 停刻 ／ 跑器 ／ ledger ／ dispatch ／ 信通未读）"
    _式 = "台账末行照录 ＋ 本面自算（幂等跳过）＋ 诸源两读同印"
    _数 = "攒件=%s 续办=%s 跳过(自算)=%s 未竟=%s" % (_gathered, _resumed, out["幂等跳过数"], out["未竟"]["n"])
    out["器"] = route_code_sha16
    out["印"] = (None if route_code_sha16 is None else
                _sha16(("%s|%s|%s|%s|%s" % (_面, _滤, _式, _数, route_code_sha16)).encode("utf-8")))
    out["印之由"] = ("本路由**自印**：印 ⊂ **器**（＝本路由之码之 sha16）＋ 面 ＋ 滤 ＋ 式 ＋ 数"
                    " ⇒ 器不同则印不同（承 PM 089 §二 ／ 1018 §一）"
                    "｜⚠ 器 ⛔ 得 ⇒ 印 `null`（照实「未核」）")
    out["数之式"] = {"面": _面, "滤": _滤, "式": _式, "数": _数}
    return out