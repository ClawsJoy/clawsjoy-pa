# -*- coding: utf-8 -*-
"""X-12 尺 · 端口单源闸（**只读**机检）。

判据（真源唯一）
  端口／URL 的唯一真源 = ``config/system/system_unified.yaml`` 的
  ``services.gateway.port``；出口 = ``core/lib/port_config.py``。调用点
  **不得复述**数值 —— 复述了就会在端口错峰后**静默打到另一棵树**（X-04 家族）。

白名单（**只减不增**；修好一条删一条）
  - ``archive/`` · ``*.bak`` · ``*.corrupt``   归档／残留（L-08：不自动删）
  - D 类标树件（WSL／容器面）：``Dockerfile.prod`` · ``start_all.sh`` ·
    ``scripts/dsh_sync.sh`` · ``tools/sync_check.sh``
  - 尺自身 ``tools/port_single_source_check.py``（模式串必然含该字面量）
  - ``*.md`` 文档：**只计不判**（读数，不入红格）

退出码
  0 = 无「非白名单」命中（绿）
  1 = 有（**红**）
  2 = 白名单条目失效（文件已不存在 ⇒ 白名单该缩，防「清单只增不减」）

用法
  python tools/port_single_source_check.py            # 人读
  python tools/port_single_source_check.py --json     # 机读
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {
    "data", ".git", "node_modules", "__pycache__", ".venv", "venv", ".idea",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
}

PATTERNS = (re.compile(r"localhost:5002"), re.compile(r"127\.0\.0\.1:5002"))

WHITELIST_EXT = (".bak", ".corrupt")
WHITELIST_DIRS = ("archive/",)
WHITELIST_FILES = (
    "Dockerfile.prod",
    "start_all.sh",
    "scripts/dsh_sync.sh",
    "tools/sync_check.sh",
    "tools/port_single_source_check.py",
)

FRONT_EXT = (".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".vue", ".css")
CFG_EXT = (".yaml", ".yml", ".json", ".toml", ".ini", ".env", ".example", ".cfg", ".conf", ".txt")


def classify(rel, ext):
    if ext == ".md":
        return "DOC"
    if rel.startswith("tests/") or rel.startswith("tools/"):
        return "T"
    if ext == ".py":
        return "A"
    if ext in FRONT_EXT:
        return "B"
    if ext in CFG_EXT:
        return "C"
    return "D"


def whitelisted(rel):
    if rel.startswith(WHITELIST_DIRS):
        return True
    if rel in WHITELIST_FILES:
        return True
    if rel.lower().endswith(WHITELIST_EXT):
        return True
    return False


def scan():
    hits = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            ext = os.path.splitext(fn)[1].lower()
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if any(pat.search(line) for pat in PATTERNS):
                            hits.append({
                                "cls": classify(rel, ext),
                                "rel": rel,
                                "line": i,
                                "whitelisted": whitelisted(rel),
                                "text": line.strip()[:140],
                            })
            except OSError:
                continue
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    hits = scan()
    offenders = [h for h in hits if not h["whitelisted"] and h["cls"] != "DOC"]
    doc = [h for h in hits if h["cls"] == "DOC"]
    white = [h for h in hits if h["whitelisted"]]

    stale = [f for f in WHITELIST_FILES if not os.path.isfile(os.path.join(ROOT, f.replace("/", os.sep)))]

    by_cls = {}
    for h in offenders:
        by_cls[h["cls"]] = by_cls.get(h["cls"], 0) + 1

    rc = 2 if stale else (1 if offenders else 0)
    if a.json:
        print(json.dumps({
            "rc": rc, "total": len(hits), "offenders": len(offenders),
            "by_class": by_cls, "whitelisted": len(white), "doc": len(doc),
            "stale_whitelist": stale, "hits": offenders,
        }, ensure_ascii=False, indent=1))
        return rc

    print("[X-12 尺] 端口单源闸 · ROOT=%s" % ROOT)
    print("  命中合计 %d 行  |  非白名单（红）%d 行  |  白名单 %d 行  |  文档(只计) %d 行"
          % (len(hits), len(offenders), len(white), len(doc)))
    print("  红格分类: " + (" ".join("%s=%d" % kv for kv in sorted(by_cls.items())) or "无"))
    if stale:
        print("  ⚠ 白名单条目已失效（该删）: %s" % ", ".join(stale))
    for h in offenders:
        print("  %s  %s:%d  %s" % (h["cls"], h["rel"], h["line"], h["text"]))
    print("  rc=%d  (%s)" % (rc, {0: "绿", 1: "红", 2: "白名单失效"}[rc]))
    return rc


if __name__ == "__main__":
    sys.exit(main())