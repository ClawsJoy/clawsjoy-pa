# -*- coding: utf-8 -*-
"""(乙) 本机自启 ＋ 断点续 —— 关机期间攒件，开机接着干。

五步（老板令 · 逐字对应）:
  1. 等环境        等盘/目录就位（有限轮询 · ⛔ 无限等）
  2. 起服          复用**既有**起服路 pa_nowindow.py start（⛔ 另造启动器 · ⛔ 直 kill）
  3. 验活          GET /health 至 200（超时 ⇒ 落账为**失败** · ⛔ 静默）
  4. 断点续        读水印 resume.json ⇒ 收攒件(inbox 落盘件 ＋ 信通信箱未读)
                   ⇒ 捞未竟(ledger 未完成 / dispatch 未 done)
                   ⇒ 逐件续办(走**产品面** POST /v9/pa/ledger/add)
                   ⇒ 按件 id 去重(⛔ 重办) ⇒ ⭐ **唯件已办完方前移水印**
  5. 落账          data\\v9\\pa\\boot_log.jsonl 逐次一行

攒件之真源:
  · <main-repo>\\data\\v9\\pa\\inbox\\   ← ⭐ **件落盘即攒，⛔ 不依赖服务在跑**
  · 信通信箱（<vault>\\...\\内容工坊\\02_协作\\信通）← 机器关了，邮件仍在

用法:
  python boot_resume.py                 # 开机任务用（全跑）
  python boot_resume.py --status        # 只读：打印水印 ＋ 最近一次开机账
  python boot_resume.py --json          # 机读（最后一行打 JSON）
  python boot_resume.py --no-start      # 跳过起服（已确认在跑时）
  python boot_resume.py --dry-run       # ⛔ 不写产品面（演练）
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _org_path(env_name):
    u"""组织物之径（⛔ 字面 · 承 pm_1409 §二.3）—— 缺 ⇒ `None`（调用处显「未接（组织版）」）。

    自 `core.lib.paths.org_path`（功能级门 `PA_ORG_FACES` · 默认关）；⛔ 得导 ⇒ `None`（照实「未接」）。
    """
    try:
        _root = str(Path(__file__).resolve().parents[2])
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from core.lib.paths import org_path
        return org_path(env_name)
    except Exception:
        return None


# ⭐ 2026-10-06（pm_1409 §二.3 · 批二）：仓根自 `__file__` 推（⛔ 字面绝对径）。
V9 = Path(__file__).resolve().parents[2]
PADIR = V9 / "data" / "v9" / "pa"
INBOX = PADIR / "inbox"
INBOX_DONE = INBOX / "_done"
RESUME = PADIR / "resume.json"
BOOTLOG = PADIR / "boot_log.jsonl"
LEDGER = PADIR / "ledger.json"
DISPATCH = PADIR / "dispatch.jsonl"
NOWINDOW = V9 / "scripts" / "win_pa" / "pa_nowindow.py"
# ⭐ 信通之器与箱 ＝ **组织专用**（pm_1409 §二.3 · 批二）⇒ `org_path`；缺 ⇒ `None`
#   ⇒ 调用处显「未接（组织版）」而**跳过**（⛔ 崩 ／ ⛔ 字面兜底）。
XINTONG = _org_path("PA_XINTONG_TICK")
XINTONG_DIR = _org_path("PA_XINTONG_DIR")
GATHER_CAP = 20       # ⭐ 防呆闸：攒件 > 此数 ⇒ 疑积压冒充离线攒件 ⇒ ⛔ 办（2026-10-05 首跑之事故）
API = "http://127.0.0.1:5102"
READER = "PM(boot_resume)"
VERSION = 1

EVENT = []          # 逐步落账（人话）
FAILD = []          # 失败项（⛔ 静默）


def say(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    EVENT.append(line)


def warn(msg):
    FAILD.append(msg)
    say("⚠ " + msg)


def sha16(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
    except Exception:
        return None

# ⭐ 窗隐（PM 2026-10-05 令 · **一处定形**）：凡本器之 subprocess ⇒ 一律带 `CREATE_NO_WINDOW`。
#   ⚠ 真源 ＝ `core\pa\_proc.py`（⛔ 各写一套）｜然 ⛔ 走 `from core.pa import _proc`：
#     `core\pa\__init__.py` 会拉 `pa_core` ＋ `vault_brain` ⇒ 实测 **≈ 1.6 s ＋ 配置／向量库初始化**
#     ⇒ 本器意在「**环境未就位亦可跑**」⇒ 故唯按**文件路径**载该器（同真源 · ⛔ 载整包）。
def _load_proc():
    _p = V9 / "core" / "pa" / "_proc.py"
    try:
        import importlib.util
        _spec = importlib.util.spec_from_file_location("_pa_proc_hidden", str(_p))
        _m = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_m)
        if callable(getattr(_m, "run_hidden", None)):
            return _m
        warn("窗隐器形不符（无 run_hidden）：%s" % _p)
    except Exception as e:
        warn("窗隐器载入失败（%s: %s）：%s" % (type(e).__name__, str(e)[:120], _p))
    return None


_PROC = _load_proc()


def run_hidden(cmd, **kw):
    u"""本器唯一 subprocess 出口（窗隐）。真源在 `core\\pa\\_proc.py`；
    载不到 ⇒ **本地等价**（同一表达式 · 并已落警 · ⛔ 静默）。"""
    if _PROC is not None:
        return _PROC.run_hidden(cmd, **kw)
    kw["creationflags"] = int(kw.get("creationflags", 0) or 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(cmd, **kw)



# ---------------------------------------------------------------- 1 等环境
def step_env(wait_s=60):
    t0 = time.time()
    while time.time() - t0 < wait_s:
        if V9.is_dir() and PADIR.is_dir():
            say("1 等环境：就位（%.1fs）· %s" % (time.time() - t0, PADIR))
            return True
        time.sleep(1.0)
    warn("1 等环境：%ds 内 V9/PADIR 未就位 ⇒ 失败" % wait_s)
    return False


# ---------------------------------------------------------------- 2/3 起服·验活
def health(timeout=4):
    try:
        with urllib.request.urlopen(API + "/health", timeout=timeout) as r:
            return r.status == 200, r.read().decode("utf-8", "replace")[:160]
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])


def wait_health(seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        ok, _ = health()
        if ok:
            return True, round(time.time() - t0, 1)
        time.sleep(1.5)
    return False, round(time.time() - t0, 1)


def step_start(no_start=False):
    ok, detail = health()
    if ok:
        say("2 起服：已在跑 ⇒ 跳过（幂等）· /health 200")
        return True
    if no_start:
        warn("2 起服：--no-start 且 /health 未通 ⇒ 失败")
        return False
    say("2 起服：/health 未通 ⇒ 走既有路 pa_nowindow.py start --wait 90")
    try:
        p = run_hidden(
            [sys.executable, "-X", "utf8", str(NOWINDOW), "start", "--wait", "90"],
            cwd=str(V9), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240,
        )
        for ln in (p.stdout or "").strip().splitlines()[-4:]:
            say("   | " + ln.strip())
        if p.returncode != 0:
            warn("2 起服：rc=%d" % p.returncode)
    except Exception as e:
        warn("2 起服：%s: %s" % (type(e).__name__, str(e)[:160]))
    ok, waited = wait_health(120)
    if ok:
        say("3 验活：/health 200（再等 %.1fs）" % waited)
        return True
    warn("3 验活：120s 内 /health 未 200 ⇒ 失败")
    return False


# ---------------------------------------------------------------- 4 断点续
def load_resume():
    if RESUME.is_file():
        try:
            d = json.loads(RESUME.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
        except Exception as e:
            warn("水印读失败（当空账续跑）: %s: %s" % (type(e).__name__, str(e)[:120]))
    return {"version": VERSION, "last_boot_at": None, "prev_boot_at": None,
            "done": {"inbox": [], "mail": []}}


def save_resume(d):
    tmp = RESUME.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(RESUME))


def gather_inbox():
    """落盘即攒 ⇒ 唯取文件(⛔ 目录)、唯取非 _ 起头者。"""
    out = []
    if not INBOX.is_dir():
        return out
    for f in sorted(INBOX.iterdir()):
        if f.is_dir() or f.name.startswith("_"):
            continue
        try:
            body = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            warn("收件读失败 %s: %s" % (f.name, str(e)[:100]))
            continue
        out.append({"id": f.name, "src": "inbox", "path": str(f), "sha16": sha16(f),
                    "text": body.strip().replace("\n", " ")[:300]})
    return out


def _mtime_ts(p):
    try:
        return os.path.getmtime(p)
    except Exception:
        return 0.0


def gather_mail(since_ts=None):
    """信通信箱 —— ⭐ **唯取「离线窗内」新到之件**（mtime ≥ 上次断点）。

    ⛔ **全量未读**：历史积压乃他方**真未读** ⇒ ⛔ 吞（2026-10-05 首跑之事故：75 件被吞）。
    ⛔ **不 ack**：我方之跑 ⛔ 代他方标「已读」⇒ 去重**唯凭我方水印** resume.json。
    ⛔ **无水印 ⇒ 不收**：无上次断点则无从判「离线窗」⇒ 首跑唯取 inbox。
    """
    if not XINTONG or not Path(XINTONG).is_file():
        warn("信通器未接（组织版）⇒ 跳过（PA_XINTONG_TICK ⛔ 设 ∨ 器不在）")
        return []
    if not XINTONG_DIR:
        warn("信通箱未接（组织版）⇒ 跳过（PA_XINTONG_DIR ⛔ 设）")
        return []
    if not since_ts:
        say("   （⛔ 无水印 ⇒ 无从判离线窗 ⇒ 信通不收；首跑唯取 inbox）")
        return []
    try:
        p = run_hidden([sys.executable, "-X", "utf8", str(XINTONG), "--json", "--all"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
        obj = json.loads((p.stdout or "").strip().splitlines()[-1])
    except Exception as e:
        warn("收信通失败: %s: %s" % (type(e).__name__, str(e)[:140]))
        return []
    try:
        _since = time.mktime(time.strptime(str(since_ts), "%Y-%m-%d %H:%M:%S"))
    except Exception:
        warn("断点值不可解析（%s）⇒ ⛔ 收信通" % since_ts)
        return []
    out, skipped = [], 0
    for name in (obj.get("all") or []):
        fp = Path(XINTONG_DIR) / name
        if _mtime_ts(fp) < _since:
            skipped += 1                      # ⭐ 离线窗之前 ⇒ 他方积压 ⇒ ⛔ 收
            continue
        out.append({"id": name, "src": "mail", "path": str(fp), "text": ""})
    if skipped:
        say("   （信通：离线窗**之前**之未读 %d 件 ⇒ ⛔ 收，留给他方）" % skipped)
    return out


def pending():
    """捞未竟：ledger 未完成 ＋ dispatch 未 done。"""
    led, dis = [], []
    try:
        d = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {}
        items = d.get("items") if isinstance(d, dict) else d
        for it in (items or []):
            if str(it.get("status", "")).lower() not in ("done", "closed", "取消"):
                led.append({"id": it.get("id"), "title": str(it.get("title"))[:80],
                            "status": it.get("status"), "kind": it.get("kind")})
    except Exception as e:
        warn("捞 ledger 失败: %s: %s" % (type(e).__name__, str(e)[:120]))
    try:
        if DISPATCH.is_file():
            for ln in DISPATCH.read_text(encoding="utf-8", errors="replace").splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    row = json.loads(ln)
                except Exception:
                    continue
                if str(row.get("status", "")).lower() not in ("done", "closed", "failed"):
                    dis.append({"task_id": row.get("task_id"), "status": row.get("status"),
                                "objective": str(row.get("objective"))[:70]})
    except Exception as e:
        warn("捞 dispatch 失败: %s: %s" % (type(e).__name__, str(e)[:120]))
    return led, dis


def ledger_add(title, note):
    body = json.dumps({"title": title[:120], "kind": "todo", "note": note[:400]}).encode("utf-8")
    req = urllib.request.Request(API + "/v9/pa/ledger/add", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def consume(item, dry=False):
    """续办一件：走产品面登记待办 ⇒ 原件归位（inbox 移 _done / 信通 ack）。"""
    title = "开机续办[%s] %s" % (item["src"], item["id"])
    note = item.get("text") or item.get("path") or ""
    if dry:
        return True, "dry-run 未写"
    try:
        r = ledger_add(title, note)
        if not r.get("ok"):
            return False, "ledger/add: %s" % str(r.get("error"))[:90]
    except Exception as e:
        return False, "产品面: %s: %s" % (type(e).__name__, str(e)[:90])
    if item["src"] == "inbox":
        INBOX_DONE.mkdir(parents=True, exist_ok=True)
        dst = INBOX_DONE / item["id"]
        if dst.exists():
            dst = INBOX_DONE / (item["id"] + "." + time.strftime("%H%M%S"))
        try:
            shutil.move(item["path"], str(dst))
        except Exception as e:
            return False, "归位失败: %s" % str(e)[:90]
    else:
        # ⭐ ⛔ 不 ack：我方之跑 ⛔ 代他方标「已读」（去重唯凭我方水印 resume.json）
        pass
    return True, "已续办"


def step_resume(dry=False, off_since=None):
    rs = load_resume()
    done_i = set(rs.get("done", {}).get("inbox") or [])
    done_m = set(rs.get("done", {}).get("mail") or [])

    items = [x for x in gather_inbox() if x["id"] not in done_i]
    # ⭐ 2026-10-05（PM-82 · 我之设计误）：**信通之件 ⛔ 再入「开机续办」** ——
    #   信通自有**唤醒线**（`pm_line_driver` 直投 · 承 L-246「发出 ≠ 送到」）⇒ 我方收件之形 ＝「读 ＋ ack」；
    #   若此处再 gather ⇒ **一件两处**（台账多一行「开机续办[mail] …」· 实证 ＝ `t7`）⇒ ⛔ 重复计。
    #   ⇒ 本器只管 `inbox\` 之**攒件盘**；信通之件**交唤醒线**（`gather_mail` 保留唯备查 · ⛔ 不入 items）。
    _mail_seen = gather_mail(rs.get("last_boot_at"))   # 唯读 · 只作日志
    if _mail_seen:
        say("   （信通离线窗内 %d 件 ⇒ ⛔ 入「开机续办」；交唤醒线之「读 ＋ ack」）" % len(_mail_seen))
    led, dis = pending()
    # ⭐ 防呆闸：攒件异常多 ⇒ 疑把「积压」当「离线攒件」（2026-10-05 首跑之事故）⇒ 一件不办
    if len(items) > GATHER_CAP:
        warn("攒件 %d 件 > 闸值 %d ⇒ ⛔ 收办（防呆：疑积压冒充离线攒件）" % (len(items), GATHER_CAP))
        items = []
    say("4 断点续：攒件 inbox=%d mail=%d ｜ 未竟 ledger=%d dispatch=%d ｜ 水印 done(inbox %d/mail %d)"
        % (len([x for x in items if x['src'] == 'inbox']), len([x for x in items if x['src'] == 'mail']),
           len(led), len(dis), len(done_i), len(done_m)))

    ok_n, bad_n, new_i, new_m = 0, 0, [], []
    for it in items:
        ok, why = consume(it, dry=dry)
        if ok:
            ok_n += 1
            (new_i if it["src"] == "inbox" else new_m).append(it["id"])
            say("   ✓ 续 [%s] %s" % (it["src"], it["id"]))
        else:
            bad_n += 1
            warn("续办失败 [%s] %s ⇒ %s（留在原地，下次重试）" % (it["src"], it["id"], why))

    # ⭐ 唯件已办完方前移水印（失败者**不**入水印 ⇒ 下次重试）
    if not dry:
        rs["done"] = {"inbox": sorted(done_i | set(new_i)), "mail": sorted(done_m | set(new_m))}
        rs["prev_boot_at"] = rs.get("last_boot_at")
        rs["last_boot_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        rs["version"] = VERSION
        rs["last_counts"] = {"gathered": len(items), "resumed": ok_n, "failed": bad_n,
                             "open_ledger": len(led), "open_dispatch": len(dis), "off_since": off_since}
        save_resume(rs)
        say("4 断点续：水印已前移 ⇒ done(inbox %d/mail %d)" % (len(rs["done"]["inbox"]), len(rs["done"]["mail"])))
    return {"gathered": len(items), "resumed": ok_n, "failed": bad_n,
            "skipped": 0, "open_ledger": len(led), "open_dispatch": len(dis),
            "inbox": len([x for x in items if x["src"] == "inbox"]),
            "mail": len([x for x in items if x["src"] == "mail"])}


# ---------------------------------------------------------------- 5 落账
def write_log(rec):
    BOOTLOG.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOTLOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def status(argv):
    """只读：水印 ＋ 最近一次开机账（⛔ 不写）。"""
    rs = load_resume()
    last = None
    if BOOTLOG.is_file():
        lines = [l for l in BOOTLOG.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
        if lines:
            try:
                last = json.loads(lines[-1])
            except Exception:
                last = {"raw": lines[-1][:200]}
    ok, detail = health()
    out = {"ok": True, "health": ok, "health_detail": detail,
           "resume_path": str(RESUME), "resume_exists": RESUME.is_file(),
           "bootlog_path": str(BOOTLOG), "bootlog_lines": (
               len([l for l in BOOTLOG.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()])
               if BOOTLOG.is_file() else 0),
           "inbox_pending": len(gather_inbox()) if INBOX.is_dir() else 0,
           "watermark": {"last_boot_at": rs.get("last_boot_at"), "prev_boot_at": rs.get("prev_boot_at"),
                         "done_inbox": len(rs.get("done", {}).get("inbox") or []),
                         "done_mail": len(rs.get("done", {}).get("mail") or [])},
           "last_boot": last}
    print(json.dumps(out, ensure_ascii=False, indent=2) if "--json" in argv else
          "面: %s\nexists=%s ｜ /health=%s ｜ 攒件待办=%s\n水印: last=%s prev=%s done(inbox %s/mail %s)\nboot_log: %s 行\n最近一次: %s"
          % (RESUME, RESUME.is_file(), ok, out["inbox_pending"], out["watermark"]["last_boot_at"],
             out["watermark"]["prev_boot_at"], out["watermark"]["done_inbox"], out["watermark"]["done_mail"],
             out["bootlog_lines"], json.dumps(last, ensure_ascii=False)[:400] if last else "（无）"))
    return 0


def main():
    argv = sys.argv[1:]
    if "--status" in argv:
        return status(argv)
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0

    dry = "--dry-run" in argv
    no_start = "--no-start" in argv
    t_start = time.time()
    INBOX.mkdir(parents=True, exist_ok=True)
    if not (INBOX / "_读我.txt").exists():
        (INBOX / "_读我.txt").write_text(
            "此目录即「攒件盘」：把一件写成一个文件丢进来即可 —— 不要求 PA 在跑。\n"
            "开机时 boot_resume.py 会逐件收走（_) 起头的文件被忽略，留给说明）。\n"
            "收走的件移入 _done/，并登记到 PA 账本。\n", encoding="utf-8")

    say("=== boot_resume 起 · %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
    ok = step_env()
    if ok:
        ok = step_start(no_start=no_start)
    res = {"gathered": 0, "resumed": 0, "failed": len(FAILD), "skipped": 0,
           "open_ledger": 0, "open_dispatch": 0, "inbox": 0, "mail": 0}
    if ok:
        res = step_resume(dry=dry)
    rec = {"boot_at": time.strftime("%Y-%m-%d %H:%M:%S"), "ts": round(time.time(), 3),
           "health": bool(ok), "dry_run": dry, "no_start": no_start,
           "wall_s": round(time.time() - t_start, 1), "env_ok": bool(ok),
           "resumed": res.get("resumed"), "gathered": res.get("gathered"),
           "inbox": res.get("inbox"), "mail": res.get("mail"),
           "open_ledger": res.get("open_ledger"), "open_dispatch": res.get("open_dispatch"),
           "failed": FAILD, "steps": EVENT, "version": VERSION}
    write_log(rec)
    say("=== boot_resume 终 · 攒 %s ⇒ 续 %s ｜ 未竟 ledger=%s dispatch=%s ｜ 失败 %d ｜ %.1fs ==="
        % (rec["gathered"], rec["resumed"], rec["open_ledger"], rec["open_dispatch"], len(FAILD), rec["wall_s"]))
    if "--json" in argv:
        print(json.dumps(rec, ensure_ascii=False))
    return 0 if ok and not [f for f in FAILD if "续办失败" in f] else 1


if __name__ == "__main__":
    sys.exit(main())
