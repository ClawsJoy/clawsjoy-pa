# -*- coding: utf-8 -*-
"""review_inbox.py — 「回给 DSH（监督）」索引器（只读 · 指针型 · ⛔ 写台账）.

v2：分 direct（to: DSH）／ cc（cc: DSH 且为回/正/准/裁/报/请）；剔 _tmp_ 与代发件。
用法：
  python -X utf8 -B tools/review_inbox.py --scan
  python -X utf8 -B tools/review_inbox.py --rebuild
  python -X utf8 -B tools/review_inbox.py --unread
  python -X utf8 -B tools/review_inbox.py --mark-read all|<sha16>
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOX = Path(r"D:\Obsidian\ClawsJoy\ClawsJoy\内容工坊\02_协作\信通")
INBOX = BOX / "_review_inbox"
ROOTS = [BOX, Path(r"D:\paseo-workspace\_pm"),
         Path(r"D:\Obsidian\ClawsJoy\ClawsJoy\paseo-pm"),
         Path(r"D:\Obsidian\ClawsJoy\ClawsJoy\codex"),
         Path(r"D:\clawsjoy_v9\_ctx_落盘")]
INDEX = INBOX / "index.ndjson"
READ = INBOX / "_read.ndjson"
ME = "DSH"
KINDS = {"回", "正", "准", "裁", "报", "请", "覆", "记"}
SKIP_DIRS = {"_review_inbox", "_冷区", "_垃圾箱", "node_modules", "__pycache__"}


def sha16(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def read_header(p: Path) -> dict:
    try:
        t = io.open(p, encoding="utf-8", errors="replace").read(8000)
    except Exception:
        return {}
    if not t.startswith("---"):
        return {}
    parts = t.split("---", 2)
    if len(parts) < 3:
        return {}
    h = {}
    for ln in parts[1].splitlines():
        if ":" in ln and not ln.startswith(" "):
            k, v = ln.split(":", 1)
            h[k.strip()] = v.strip()
    return h


def classify(h: dict):
    if not h:
        return None
    to = h.get("to", "")
    cc = h.get("cc", "")
    frm = h.get("from", "")
    typ = h.get("type", "").strip()
    if ME.lower() in to.lower():
        return "direct"
    if ME.lower() in cc.lower() and typ in KINDS and "老板" not in frm and ME not in frm:
        return "cc"
    return None


def iter_files(days: int | None):
    cut = None if days is None else time.time() - days * 86400
    for root in ROOTS:
        if not root.exists():
            continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
            for fn in fns:
                if not (fn.endswith(".md") or fn.endswith(".txt")):
                    continue
                if fn.startswith("_tmp") or fn.startswith("."):
                    continue
                p = Path(dp) / fn
                try:
                    st = p.stat()
                except Exception:
                    continue
                if cut is not None and st.st_mtime < cut:
                    continue
                yield p, st


def load_index() -> list:
    if not INDEX.exists():
        return []
    out = []
    for ln in io.open(INDEX, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def load_read() -> set:
    if not READ.exists():
        return set()
    return {ln.strip().split("\t")[0] for ln in io.open(READ, encoding="utf-8", errors="replace") if ln.strip()}


def scan(days: int | None, rebuild: bool = False) -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    if rebuild and INDEX.exists():
        INDEX.unlink()
    known = {e.get("sha16") for e in load_index()}
    new = 0
    with io.open(INDEX, "a", encoding="utf-8", newline="\n") as fh:
        for p, st in iter_files(days):
            h = read_header(p)
            kind = classify(h)
            if not kind:
                continue
            try:
                b = p.read_bytes()
            except Exception:
                continue
            s16 = sha16(b)
            if s16 in known:
                continue
            rec = {"sha16": s16, "kind": kind, "bytes": len(b),
                   "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)),
                   "num": h.get("序号", ""), "type": h.get("type", ""),
                   "from": h.get("from", ""), "to": h.get("to", ""), "cc": h.get("cc", ""),
                   "status": h.get("status", ""), "path": str(p), "name": p.name}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            known.add(s16)
            new += 1
            print("[new] %-6s %s  %-6s %-22s -> %s" % (kind, s16, rec["num"], rec["from"][:22], p.name))
    print("[scan] new=%d total=%d" % (new, len(known)))
    return new


def unread() -> list:
    read = load_read()
    return [e for e in load_index() if e.get("sha16") not in read]


def mark_read(which: str) -> int:
    read = load_read()
    n = 0
    with io.open(READ, "a", encoding="utf-8", newline="\n") as fh:
        for e in load_index():
            s16 = e.get("sha16")
            if s16 in read:
                continue
            if which == "all" or which == s16:
                fh.write("%s\t%s\n" % (s16, time.strftime("%Y-%m-%dT%H:%M:%S")))
                read.add(s16)
                n += 1
    print("[mark-read] %d" % n)
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--unread", action="store_true")
    ap.add_argument("--mark-read", default=None)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.rebuild:
        scan(a.days, rebuild=True)
        return 0
    if a.scan:
        scan(a.days)
        return 0
    if a.mark_read:
        mark_read(a.mark_read)
        return 0
    rows = unread()
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    direct = [e for e in rows if e.get("kind") == "direct"]
    cc = [e for e in rows if e.get("kind") == "cc"]
    print("[unread] total=%d direct=%d cc=%d" % (len(rows), len(direct), len(cc)))
    for e in sorted(rows, key=lambda x: x.get("mtime", "")):
        print("%s  %-6s %-8s %-24s -> %s" % (e.get("mtime", ""), e.get("kind"), e.get("num", ""), e.get("from", "")[:24], e.get("name", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
