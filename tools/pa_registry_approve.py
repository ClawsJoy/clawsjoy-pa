# -*- coding: utf-8 -*-
"""pa_registry_approve.py — PA 自册 pilot：批一张（只写 data/tmp）.

读 data/tmp/pa_registry_pending.json；批 <id> ⇒ data/tmp/pa_registry_pilot.json。
⛔ 写产品 roster.json；⛔ 自动批他卡。
"""
from __future__ import annotations
import argparse, datetime, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path("data/tmp/pa_registry_pending.json")
OUT = Path("data/tmp/pa_registry_pilot.json")
NOW = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--approve", required=True)
    ap.add_argument("--by", default="老板")
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    cards = json.loads(SRC.read_text(encoding="utf-8"))
    hit = None
    for c in cards:
        if c["id"] == a.approved if False else c["id"] == a.approve:
            hit = c
            break
    if not hit:
        print("[ERR] not found", a.approve); return 2
    hit["status"] = "active"
    hit["approved_by"] = a.by
    hit["approved_at"] = NOW
    hit["approval_ref"] = a.ref
    hit["verified"] = True
    if hit["id"] == "cli:dsh":
        hit["probe"] = "dsh --version => 0.1.5-rc.1"
        hit["invoke"] = 'dsh --profile headless "<task>"'
        hit["capabilities"] = ["code", "file", "terminal", "review", "plan"]
        hit["boundary"] = "单任务打印即退；⛔ 持久会话（除 web/tui profile）；⛔ GUI"
        hit["fragility"] = "model/profile 依赖；headless 无交互；超时须自带"
        hit["cost"] = "model-dependent；见 /v9/pa/cost"
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("[approve]", hit["id"], "by", a.by, "at", NOW)
    print("[cards]", len(cards), "by status", dict(Counter(c["status"] for c in cards)))
    for c in cards:
        if c["status"] == "active":
            print("  ACTIVE", c["id"], "|", c.get("probe", "")[:80])
    print("[out]", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
