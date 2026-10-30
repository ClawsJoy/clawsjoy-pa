# -*- coding: utf-8 -*-
"""dsh_sessions.py — DSH 会话目录（只读）.

列 $DSH_HOME/sessions/<cwd>/<session>/session.v3.jsonl.zstd 的元数据；
--read <id> 尝试解压（需 zstandard），否则提示用 dsh web 看。
⛔ 写会话；⛔ 改产品。
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOME = Path(os.environ.get("DSH_HOME", str(Path.home() / ".dsh")))
ROOT = HOME / "sessions"


def rows():
    out = []
    if not ROOT.exists():
        return out
    for grp in ROOT.iterdir():
        if not grp.is_dir():
            continue
        for s in grp.iterdir():
            if not s.is_dir():
                continue
            f = s / "session.v3.jsonl.zstd"
            if not f.exists():
                continue
            st = f.stat()
            out.append({"group": grp.name, "id": s.name, "bytes": st.st_size,
                        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)),
                        "path": str(f)})
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--read", default=None)
    ap.add_argument("--limit", type=int, default=15)
    a = ap.parse_args()
    if a.read:
        hit = [r for r in rows() if r["id"].startswith(a.read)]
        if not hit:
            print("[ERR] session not found"); return 2
        p = Path(hit[0]["path"])
        try:
            import zstandard as zstd
            with p.open("rb") as fh:
                data = zstd.ZstdDecompressor().stream_reader(fh).read()
            text = data.decode("utf-8", "replace")
            print(text[:6000])
        except Exception as e:
            print("[no-read]", e)
            print("用 dsh --profile web 在 Web UI 看；或装 zstandard 后重试。")
        return 0
    rs = rows()
    print("[sessions]", len(rs), "root", ROOT)
    for r in rs[:a.limit]:
        print("  %s  %8d B  %s  %s" % (r["mtime"], r["bytes"], r["id"][:8], r["group"][:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
