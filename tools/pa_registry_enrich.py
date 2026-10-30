# -*- coding: utf-8 -*-
"""pa_registry_enrich.py — 给 pilot 卡补 control_plane / view / session_store / access_level（只写 tmp）.

原则：一席一卡，多路（primary + fallbacks）；窗是 view，⛔ 另建卡。
"""
from __future__ import annotations
import datetime, json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path("data/tmp/pa_registry_probed.json")
OUT = Path("data/tmp/pa_registry_pilot_v2.json")
NOW = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
DSH_HOME = os.environ.get("DSH_HOME", str(Path.home() / ".dsh"))


def enrich(c):
    cid = c["id"]
    if cid == "pa":
        c.update({"control_plane": "self", "view": "pa-focus",
                  "view_cmd": "PA 本体", "session_store": "pa",
                  "access_level": "L4", "fallbacks": []})
    elif c["kind"] == "seat":
        c.update({"control_plane": "paseo", "view": "paseo-ui",
                  "view_cmd": "Paseo app", "session_store": "paseo",
                  "access_level": "L3", "fallbacks": ["paseo-cli"]})
    elif cid == "cli:dsh":
        c.update({"control_plane": "dsh-cli", "view": "dsh-web",
                  "view_cmd": 'dsh --profile web', "session_store": DSH_HOME + "\\sessions",
                  "session_store_note": "real dir on C; D:\\dsh_backup_20260915 is .broken backup",
                  "session_policy": {"archive_after_days": 7, "archive_below_bytes": 1024, "keep_large": True, "review_medium": True, "archive_root": r"D:\dsh-home\sessions_archive"},
                  "session_counts": {"before": 368, "archived": 262, "active": 106},
                  "access_level": "L2", "fallbacks": ["paseo(dsh)"]})
    elif cid == "cli:codex":
        c.update({"control_plane": "codex-cli", "view": "codex-app",
                  "view_cmd": "codex app / codex resume", "session_store": r"D:\codex-home\cli\sessions",
                  "session_store_alt": r"D:\codex-home\desktop\sessions",
                  "session_store_note": "CODEX_HOME=cli; C:\\Users\\flybo\\.codex is junction -> desktop",
                  "access_level": "L2", "fallbacks": ["paseo(codex-deepseek)"]})
    elif cid == "cli:pi":
        c.update({"control_plane": "paseo", "view": "paseo-ui",
                  "view_cmd": "Paseo app", "session_store": "paseo",
                  "access_level": "L3", "fallbacks": ["pi-cli"]})
    else:
        c.update({"control_plane": "unknown", "view": "pa-focus",
                  "session_store": "unknown", "access_level": "L1", "fallbacks": []})
    c["enriched_at"] = NOW
    return c


def main():
    cards = json.loads(SRC.read_text(encoding="utf-8"))
    cards = [enrich(c) for c in cards]
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("[cards]", len(cards), "status", dict(Counter(c["status"] for c in cards)))
    print("[control_plane]", dict(Counter(c["control_plane"] for c in cards)))
    print("[view]", dict(Counter(c["view"] for c in cards)))
    for c in cards:
        print("  %-6s %-10s %-12s %-10s %-4s %s" % (
            c["kind"], c["id"][:10], c["control_plane"], c["view"], c["access_level"], c["status"]))
    print("[out]", OUT)


if __name__ == "__main__":
    main()
