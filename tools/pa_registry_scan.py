# -*- coding: utf-8 -*-
"""pa_registry_scan.py — PA 自册「扫」原型（只读）.

扫：paseo 本机席 / CLI / SSH 别名；全入 pending，⛔ 自动 active。
输出：data/tmp/pa_registry_pending.json（只写 tmp，⛔ 写产品）。
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PA_JSON = Path("data/tmp/paseo_agents.json")
OUT = Path("data/tmp/pa_registry_pending.json")


def load_paseo():
    if not PA_JSON.exists():
        return []
    b = PA_JSON.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return json.loads(b.decode(enc))
        except Exception:
            continue
    return []


def run(cmd, timeout=3):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return (p.stdout or p.stderr or "").strip().splitlines()[0][:120]
    except Exception as e:
        return "ERR:" + str(e)[:80]


def main():
    cards = [{
        "id": "pa", "kind": "self", "name": "老板 PA", "class": "self",
        "provider": "dsh", "capabilities": ["规划", "派活", "核账", "守门"],
        "boundary": "无真席；代发以老板名义", "fragility": "low",
        "cost": "见 /v9/pa/cost", "invoke": "本进程",
        "probe": "self", "verified": True, "status": "active",
        "approved_by": "老板", "approved_at": "2026-10-27",
    }]
    seats = load_paseo()
    for a in seats:
        cards.append({
            "id": "seat:" + a.get("shortId", ""),
            "kind": "seat", "name": a.get("name", ""), "class": "本机席",
            "provider": a.get("provider", ""), "capabilities": ["seat"],
            "boundary": "provider-dependent", "fragility": "medium",
            "cost": "unknown", "invoke": "paseo agent send " + a.get("shortId", "") + " --prompt-file <file>",
            "probe": "paseo agent inspect " + a.get("shortId", ""),
            "verified": False, "status": "pending",
            "approved_by": "", "approved_at": "",
            "status_now": a.get("status", ""), "cwd": a.get("cwd", ""),
        })
    for name in ("codex", "claude", "dsh", "pi", "opencode"):
        p = shutil.which(name)
        if not p:
            continue
        cards.append({
            "id": "cli:" + name, "kind": "cli", "name": name, "class": "CLI",
            "provider": name, "capabilities": ["cli"],
            "boundary": "非交互；stdin=DEVNULL", "fragility": "medium",
            "cost": "unknown", "invoke": p + " <task>",
            "probe": run([p, "--version"]) if name != "opencode" else run([p, "--version"]),
            "verified": False, "status": "pending",
            "approved_by": "", "approved_at": "",
        })
    ssh = Path.home() / ".ssh" / "config"
    if ssh.exists():
        for ln in ssh.read_text(encoding="utf-8", errors="replace").splitlines():
            s = ln.strip()
            if s.lower().startswith("host ") and "*" not in s:
                alias = s.split(None, 1)[1].strip()
                cards.append({
                    "id": "ssh:" + alias, "kind": "ssh", "name": alias, "class": "云 VM",
                    "provider": "ssh", "capabilities": ["remote"],
                    "boundary": "网络/凭据依赖", "fragility": "high",
                    "cost": "unknown", "invoke": "ssh " + alias + " <cmd>",
                    "probe": "ssh -G " + alias,
                    "verified": False, "status": "pending",
                    "approved_by": "", "approved_at": "",
                })
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("[scan] cards", len(cards), "by kind", dict(Counter(c["kind"] for c in cards)),
          "by status", dict(Counter(c["status"] for c in cards)))
    for c in cards:
        print("  %-6s %-28s %-10s %s" % (c["kind"], c["id"][:28], c["status"], c["probe"][:60]))
    print("[out]", OUT)


if __name__ == "__main__":
    main()
