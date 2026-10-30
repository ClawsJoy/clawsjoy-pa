# -*- coding: utf-8 -*-
"""pa_registry_probe.py — 逐卡 probe（只读；只写 data/tmp）.

pending 卡：seat ⇒ paseo ls 的 status；cli ⇒ 已有 --version。
probe ≠ approve：status 仍 pending，verified 仍 false。
"""
from __future__ import annotations
import datetime, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path("data/tmp/pa_registry_pilot.json")
OUT = Path("data/tmp/pa_registry_probed.json")
NOW = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def main():
    cards = json.loads(SRC.read_text(encoding="utf-8"))
    n = 0
    for c in cards:
        if c["status"] != "pending":
            continue
        c["probe_at"] = NOW
        if c["kind"] == "seat":
            st = c.get("status_now", "?")
            c["probe"] = "paseo ls: " + st
            c["probe_ok"] = st in ("idle", "running")
        elif c["kind"] == "cli":
            c["probe_ok"] = not str(c.get("probe", "")).startswith("ERR")
        else:
            c["probe_ok"] = False
        n += 1
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("[probe]", n, "pending; by status", dict(Counter(c["status"] for c in cards)),
          "; by ok", dict(Counter(str(c.get("probe_ok")) for c in cards if c["status"] == "pending")))
    for c in cards:
        if c["status"] == "pending":
            print("  %-6s %-28s ok=%-5s %s" % (c["kind"], c["id"][:28], str(c.get("probe_ok")), c.get("probe", "")[:70]))
    print("[out]", OUT)


if __name__ == "__main__":
    main()
