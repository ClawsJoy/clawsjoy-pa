#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dsh_pa_verify v2 —— WSL 侧 PA 产物核验 CLI（薄壳，调 core/pa/verify.py）。

v2(2026-09-28): 核验逻辑**单源**到 PA 后端 core/pa/verify.py（同一器经 POST|GET /v9/pa/verify 暴露）；
  CLI 另加 C11 = live 路由可达核验。
用法: python3 tools/dsh_pa_verify.py all [--json OUT] [--skip-scan]
"""
import argparse
import json
import os
import sys
import time
import urllib.request

V9 = os.environ.get("DSH_V9ROOT", "/home/flybo/clawsjoy_v5")
BASE = os.environ.get("DSH_PA_BASE", "http://127.0.0.1:5002")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="all", choices=["all"])
    ap.add_argument("--json", default="")
    ap.add_argument("--skip-scan", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, V9)
    from core.pa.verify import run_checks

    s = run_checks(skip_scan=a.skip_scan, live_http=True)
    try:
        with urllib.request.urlopen(BASE + "/v9/pa/verify?skip_scan=1", timeout=60) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
        c11 = {"id": "C11", "pass": bool(d.get("ok")),
               "evidence": "GET /v9/pa/verify -> ok=%s pass=%s/%s" % (d.get("ok"), d.get("pass"), d.get("total"))}
    except Exception as e:
        c11 = {"id": "C11", "pass": False, "evidence": "GET /v9/pa/verify 失败: %s" % e}
    s["results"].append(c11)
    s["total"] = len(s["results"])
    s["pass"] = sum(1 for x in s["results"] if x["pass"])
    s["ok"] = s["pass"] == s["total"]
    s["verifier"] = "dsh_pa_verify v2 (core/pa/verify.py)"
    print("== dsh_pa_verify v2 == %s  (V9=%s)" % (time.strftime("%Y-%m-%d %H:%M:%S %z"), V9))
    for x in s["results"]:
        print("  [%s] %-4s %s" % ("PASS" if x["pass"] else "FAIL", x["id"], x["evidence"]))
    print("== 合计 %d/%d PASS ==" % (s["pass"], s["total"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=1)
        print("已写证据:", a.json)
    return 0 if s["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
