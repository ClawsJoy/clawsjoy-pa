# -*- coding: utf-8 -*-
"""dsh_sessions_manage.py — DSH 会话归档（move，不删）.

默认 dry-run；--go 把 <max-bytes 且 >days 的 session 目录 move 到
D:\dsh-home\sessions_archive\<tag>\<group>\<session>；写 manifest。
--restore <manifest> 可移回。
"""
from __future__ import annotations
import argparse, csv, os, shutil, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"D:\dsh-home\sessions")
ARCH = Path(r"D:\dsh-home\sessions_archive")
SUMMARY = Path("docs/reports/_pa_groundwork_20261027/sessions_by_seat_group_v1.csv")


def meta():
    m = {}
    if SUMMARY.exists():
        with SUMMARY.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                m[r["session_id"]] = r
    return m


def scan(days, max_bytes):
    out = []
    for g in sorted(ROOT.iterdir()):
        if not g.is_dir():
            continue
        for s in sorted(g.iterdir()):
            if not s.is_dir():
                continue
            f = s / "session.v3.jsonl.zstd"
            if not f.exists():
                continue
            st = f.stat()
            age = (time.time() - st.st_mtime) / 86400
            if st.st_size < max_bytes and age > days:
                out.append({"group": g.name, "sid": s.name, "bytes": st.st_size,
                            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)),
                            "age": round(age, 1), "src": str(s)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--max-bytes", type=int, default=1024)
    ap.add_argument("--tag", default=time.strftime("%Y%m%d"))
    ap.add_argument("--restore", default="")
    a = ap.parse_args()
    if a.restore:
        man = Path(a.restore)
        n = 0
        with man.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                src = Path(r["archived"]); dst = Path(r["original"])
                if src.exists() and not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst)); n += 1
        print("[restore]", n); return 0
    items = scan(a.days, a.max_bytes)
    total = sum(x["bytes"] for x in items)
    print("[scan]", len(items), "items", total, "bytes; days", a.days, "max", a.max_bytes)
    for g in sorted({x["group"] for x in items}):
        xs = [x for x in items if x["group"] == g]
        print("  ", g[:50], len(xs), sum(x["bytes"] for x in xs))
    if not a.go:
        print("[dry-run] no move; add --go"); return 0
    m = meta()
    arch = ARCH / a.tag
    manifest = ARCH / ("manifest_" + a.tag + ".csv")
    arch.mkdir(parents=True, exist_ok=True)
    rows = []
    moved = failed = 0
    for x in items:
        dst = arch / x["group"] / x["sid"]
        row = {"session_id": x["sid"], "group": x["group"], "bytes": x["bytes"],
               "mtime": x["mtime"], "original": x["src"], "archived": str(dst),
               "cwd": m.get(x["sid"], {}).get("cwd", ""),
               "seat_group": m.get(x["sid"], {}).get("seat_group", ""), "status": ""}
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                row["status"] = "exists"; failed += 1
            else:
                shutil.move(x["src"], str(dst))
                row["status"] = "moved"; moved += 1
        except Exception as e:
            row["status"] = "ERR:" + str(e)[:80]; failed += 1
        rows.append(row)
    with manifest.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("[go] moved", moved, "failed", failed, "manifest", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
