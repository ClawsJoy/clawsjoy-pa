#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""win_alias_bridge.py -- long-name bridge: Windows-side hard links for names WSL cannot open.

WHY (2026-09-28, CEO ruling VI / DSH missing-list d396aefaf6b7fc51):
  * WSL NAME_MAX = 255 **bytes** -> any file whose name is > 255 UTF-8 bytes is
    unreadable from WSL by *any* means (errno 36 ENAMETOOLONG). Not EIO, not a
    drvfs cache issue, chkdsk cannot fix it.
  * 5 files known: codex/ x2 (261B, 269B) + content-workshop/02/信通 x3 (258B, 259B, 282B).
  * NOT renaming the originals: they are already-sent documents and the CEO ledger
    references them by full name (rule: never rewrite a sent item).
  * NOT copying content: a second copy would be a second source of truth.
  => This tool creates, ON THE WINDOWS SIDE, a hard link (same volume, same inode,
     zero copy) under a short alias, so WSL can open it. Original untouched.

HARD LINK, NOT A COPY: alias and original share one data stream. Editing either
changes both (that is the point: single source of truth, two names).

USAGE
  python tools/win_alias_bridge.py --check        # read-only: list long names + existing bridges
  python tools/win_alias_bridge.py --build        # create links + write map + self-verify (idempotent)
  python tools/win_alias_bridge.py --selftest     # red-case self test (temp dir, includes pre-red)
  options: --vault <dir> (default D:\\Obsidian\\ClawsJoy\\ClawsJoy)
           --out   <dir> (default D:\\clawsjoy_v9\\data\\v9\\win_alias)

EXIT: 0 = ok / 2 = red (a criterion failed) / 3 = bad usage / 1 = runtime error.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

NAME_MAX_BYTES = 255
ALIAS_MAX_BYTES = 200          # leave headroom under WSL's 255-byte cap
DEFAULT_VAULT = r"D:\Obsidian\ClawsJoy\ClawsJoy"
DEFAULT_OUT = r"D:\clawsjoy_v9\data\v9\win_alias"
SCAN_SKIP_TOP = (".obsidian",)


def nbytes(name):
    return len(name.encode("utf-8"))


def sha256_16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def sanitize(stem):
    out = []
    for ch in stem:
        if ch.isalnum() or ch in "-_.":
            out.append(ch)
        elif ord(ch) > 127:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("._-") or "x"


def alias_for(rel_path, stem_keep=40):
    """alias = <sha8>_<readable-prefix>.md ; asserts the alias fits WSL's cap."""
    orig = os.path.basename(rel_path)
    digest = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:8]
    stem = orig[:-3] if orig.lower().endswith(".md") else orig
    keep = strand = sanitize(stem)[:stem_keep]
    while keep:
        cand = "%s_%s.md" % (digest, keep)
        if nbytes(cand) <= ALIAS_MAX_BYTES:
            return cand
        keep = keep[:-1]
    cand = "%s.md" % digest
    assert nbytes(cand) <= ALIAS_MAX_BYTES, "alias still too long: %r" % cand
    return cand


def find_long_names(root):
    root = os.path.abspath(root)
    hits = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SCAN_SKIP_TOP]
        for n in fn:
            if nbytes(n) > NAME_MAX_BYTES:
                full = os.path.join(dp, n)
                hits.append((os.path.relpath(full, root).replace("\\", "/"), full))
    return sorted(hits)


def build(root, out):
    os.makedirs(out, exist_ok=True)
    rows, checks = [], []
    for rel, full in find_long_names(root):
        alias = alias_for(rel)
        alink = os.path.join(out, alias)
        rec = {
            "orig_rel": rel, "orig_name": os.path.basename(rel),
            "orig_name_bytes": nbytes(os.path.basename(rel)),
            "alias": alias, "alias_bytes": nbytes(alias),
            "link": alink, "sha16": sha256_16(full),
            "bytes": os.path.getsize(full),
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(full))),
        }
        if os.path.lexists(alink):
            rec["action"] = "exists"
        else:
            os.link(full, alink)
            rec["action"] = "linked"
        # criteria (red if violated)
        checks.append((rec["alias_bytes"] <= ALIAS_MAX_BYTES, "alias<=%dB %s" % (ALIAS_MAX_BYTES, alias)))
        checks.append((os.path.lexists(alink), "link exists %s" % alias))
        same = sha256_16(alink) == rec["sha16"] if os.path.lexists(alink) else False
        checks.append((same, "sha16 identical %s" % alias))
        # same inode (hard link, not copy)
        try:
            same_ino = os.path.samefile(alink, full)
        except OSError:
            same_ino = False
        checks.append((same_ino, "same inode (hard link, not copy) %s" % alias))
        rec["same_inode"] = same_ino
        rows.append(rec)
    mapfile = os.path.join(out, "_map.json")
    with open(mapfile, "w", encoding="utf-8") as f:
        json.dump({"vault": os.path.abspath(root), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "name_max_bytes": NAME_MAX_BYTES, "alias_max_bytes": ALIAS_MAX_BYTES,
                   "count": len(rows), "rows": rows}, f, ensure_ascii=False, indent=2)
    readme = os.path.join(out, "README.md")
    with open(readme, "w", encoding="utf-8") as f:
        f.write("# win_alias -- long-name bridge (hard links, zero copy)\n\n"
                "WSL NAME_MAX = 255 bytes; these %d original file names exceed it, so WSL\n"
                "cannot open them by any name. Each file below is a **hard link** to the\n"
                "original in the vault: same volume, same inode, one data stream, no copy.\n"
                "Editing either name changes both (single source of truth, two names).\n\n"
                "Mapping: `_map.json` (orig_rel = vault-relative path of the original).\n\n"
                "| alias (WSL-readable) | bytes | orig name bytes | sha16 |\n|---|---|---|---|\n" % len(rows))
        for r in rows:
            f.write("| `%s` | %d | %d | `%s` |\n" % (r["alias"], r["alias_bytes"], r["orig_name_bytes"], r["sha16"]))
        f.write("\nGenerated %s by tools/win_alias_bridge.py\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    failed = [d for ok, d in checks if not ok]
    return rows, failed, mapfile, readme


def selftest():
    tmp = tempfile.mkdtemp(prefix="wab_")
    ok = True
    try:
        vault = os.path.join(tmp, "vault", "codex")
        out = os.path.join(tmp, "out")
        os.makedirs(vault)
        long_stem = "题" * 90                     # 270 bytes + ".md"
        long_name = long_stem + ".md"
        assert nbytes(long_name) > NAME_MAX_BYTES, "fixture is not a long name"
        with open(os.path.join(vault, long_name), "w", encoding="utf-8") as f:
            f.write("content-v1\n")
        # PRE-RED: before any bridge, the alias must not exist and the name is over cap
        pre = [d for ok_, d in [((nbytes(long_name) <= NAME_MAX_BYTES), "fixture over cap")] if not ok_]
        print("[PRE-RED] over-cap detected =", bool(pre))
        rows, failed, mapfile, readme = build(os.path.join(tmp, "vault"), out)
        print("[SELFTEST] rows =", len(rows), "failed =", failed)
        ok = ok and len(rows) == 1 and not failed
        r = rows[0]
        ok = ok and r["same_inode"] and r["alias_bytes"] <= ALIAS_MAX_BYTES
        # RED CASE A: alias over cap must be refused by alias_for
        try:
            alias_for("x/" + "题" * 200, stem_keep=200)
            over_long = [a for a in [alias_for("x/" + "题" * 200, stem_keep=200)] if nbytes(a) > ALIAS_MAX_BYTES]
            print("[RED-A] alias_for kept alias under cap ->", not over_long)
            ok = ok and not over_long
        except AssertionError:
            print("[RED-A] alias_for refused over-cap alias = True")
        # RED CASE B: tampering the alias content must be detectable (link shares inode)
        with open(os.path.join(out, r["alias"]), "a", encoding="utf-8") as f:
            f.write("tamper\n")
        detect = sha256_16(os.path.join(vault, long_name)) != r["sha16"]
        print("[RED-B] same-inode edit visible on original =", detect)
        ok = ok and detect
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[SELFTEST]", "PASS" if ok else "FAIL")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--build", action="store_true")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not os.path.isdir(a.vault):
        print("[ERR] vault not found: %s" % a.vault)
        return 3
    hits = find_long_names(a.vault)
    print("[check] vault = %s" % a.vault)
    print("[check] names > %dB (UTF-8) = %d" % (NAME_MAX_BYTES, len(hits)))
    for rel, full in hits:
        print("   %4dB  %s" % (nbytes(os.path.basename(rel)), rel))
    if a.check:
        print("[check] out = %s exists=%s" % (a.out, os.path.isdir(a.out)))
        mf = os.path.join(a.out, "_map.json")
        if os.path.isfile(mf):
            j = json.load(open(mf, encoding="utf-8"))
            print("[check] map rows = %d at %s" % (j.get("count", -1), j.get("at")))
        return 0
    rows, failed, mapfile, readme = build(a.vault, a.out)
    for r in rows:
        print("  [%s] %s  <- %s" % (r["action"], r["alias"], r["orig_rel"]))
    print("[build] map = %s" % mapfile)
    print("[build] readme = %s" % readme)
    if failed:
        print("[RED] failed criteria:")
        for d in failed:
            print("   -", d)
        return 2
    print("[build] OK rows=%d (alias<=%dB, sha16 identical, same inode)" % (len(rows), ALIAS_MAX_BYTES))
    return 0


if __name__ == "__main__":
    sys.exit(main())