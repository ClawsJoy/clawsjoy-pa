# -*- coding: utf-8 -*-
"""route_diff.py — 路由集基线／比对器（②v1 之「89/89 diff=0」判据 · 只读）.

用途：
  --dump <baseline.json>   从 gateway_routes.py 抽 89 条路由，写基线（method+path+func）
  --check <baseline.json>  比对当前文件；缺/多/函数名变 ⇒ rc=2
  --self-test              正控（同文件 ⇒ 0）＋ 反控（删一条 ⇒ 2；改方法 ⇒ 2）

边界：只读源码；只写基线/临时件；⛔ 改产品码；⛔ 写台账。
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT = "core/pa/gateway_routes.py"
SPLIT_GLOB = "core/pa/pa_routes_*.py"
#: P0-2c：/v9/agent 端点用 app.add_url_rule 注册，须纳入同一路由集（⛔ 漏扫）
AGENT_SOURCE = "routes/v9_chat.py"
ROUTE = re.compile(r'@bp\.route\(\s*"([^"]+)"\s*(?:,\s*methods=\[([^\]]*)\])?\s*\)')
DEF = re.compile(r"^\s*def\s+([A-Za-z0-9_]+)\s*\(")


def _name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _str_list(node):
    if isinstance(node, (ast.List, ast.Tuple)):
        return [e.value for e in node.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return []


def _kw(call, name):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _add_url_rule_rows(src):
    u"""解析 app.add_url_rule(...)（含多行）：path/methods/view_func⇒func。"""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    rows = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_url_rule"):
            continue
        rule = _const_str(node.args[0]) if node.args else ""
        if not rule:
            rule = _const_str(_kw(node, "rule"))
        if not rule:
            continue
        methods = _str_list(_kw(node, "methods")) or ["GET"]
        func = _name_of(_kw(node, "view_func")) or _const_str(_kw(node, "endpoint"))
        for meth in methods:
            rows.append({"method": str(meth).upper(), "path": rule, "func": func})
    return rows


def parse(path: str):
    rows = []
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
        lines = src.splitlines()
    for i, ln in enumerate(lines):
        m = ROUTE.search(ln)
        if not m:
            continue
        methods = [x.strip("\"' ") for x in (m.group(2) or "GET").split(",") if x.strip("\"' ")]
        func = ""
        for j in range(i + 1, min(i + 8, len(lines))):
            d = DEF.match(lines[j])
            if d:
                func = d.group(1)
                break
        for meth in methods:
            rows.append({"method": meth.upper(), "path": m.group(1), "func": func})
    rows.extend(_add_url_rule_rows(src))
    # 同 method+path 只留一条（装饰器优先；app.add_url_rule 作补充）
    uniq = {}
    for row in rows:
        uniq.setdefault((row["method"], row["path"]), row)
    rows = list(uniq.values())
    rows.sort(key=lambda r: (r["path"], r["method"]))
    return rows


def default_sources():
    """②v1 拆件后：路由分居 `core/pa/pa_routes_*.py`（蓝图共享 `pa_routes`）⇒ 判据须纳全件。

    ⚠ 只扩**取源面**，⛔ 改判据：仍为「缺／多／函数名变 ⇒ rc=2」，另加「同 method+path 二处 ⇒ rc=2」。
    """
    out = [q for q in sorted(glob.glob(SPLIT_GLOB)) if not q.endswith(".py.new")]
    if os.path.exists(DEFAULT):
        out.insert(0, DEFAULT)
    if os.path.exists(AGENT_SOURCE) and AGENT_SOURCE not in out:
        out.append(AGENT_SOURCE)          # P0-2c：/v9/agent 路由同入一集
    return out


def sources(src):
    if not src:
        return default_sources()
    if isinstance(src, (list, tuple)):
        return list(src)
    return [src]


def parse_all(paths):
    """聚合多件 ⇒ 行；并检重挂（同 method+path 二处不同 func ⇒ 违「一处定形」）。"""
    rows, seen, dupes = [], {}, []
    for p in paths:
        for r in parse(p):
            k = (r["method"], r["path"])
            if k in seen:
                if seen[k] != r.get("func", ""):
                    dupes.append((p, k, r.get("func", "")))
                continue
            seen[k] = r.get("func", "")
            rows.append(r)
    rows.sort(key=lambda r: (r["path"], r["method"]))
    return rows, dupes


def dump(src, out: str) -> int:
    paths = sources(src)
    rows, dupes = parse_all(paths)
    if dupes:
        for p, k, f in dupes:
            print("[DUP]     %s %s (func=%s) @ %s" % (k[0], k[1], f, os.path.basename(p)))
        return 2
    doc = {"version": 1, "source": (os.path.basename(src) if isinstance(src, str) and src
                                     else "pa_routes_* + routes/v9_chat.py"),
           "count": len(rows), "routes": rows}
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("[dump] %d routes -> %s" % (len(rows), out))
    return 0


def check(src: str, base: str) -> int:
    with open(base, encoding="utf-8") as fh:
        doc = json.load(fh)
    want = {(r["method"], r["path"]): r.get("func", "") for r in doc["routes"]}
    paths = sources(src)
    rows, dupes = parse_all(paths)
    got = {(r["method"], r["path"]): r.get("func", "") for r in rows}
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    changed = sorted(k for k in set(want) & set(got) if want[k] and got[k] and want[k] != got[k])
    print("[check] baseline=%d current=%d files=%d dupes=%d" % (len(want), len(got), len(paths), len(dupes)))
    for p, k, f in dupes:
        print("[DUP]     %s %s (func=%s) @ %s" % (k[0], k[1], f, os.path.basename(p)))
    for m, p in missing:
        print("[MISSING] %s %s (func=%s)" % (m, p, want[(m, p)]))
    for m, p in extra:
        print("[EXTRA]   %s %s (func=%s)" % (m, p, got[(m, p)]))
    for k in changed:
        print("[FUNC]    %s %s: %s -> %s" % (k[0], k[1], want[k], got[k]))
    ok = not (missing or extra or changed or dupes)
    print("[verdict] %s" % ("PASS（diff=0）" if ok else
                            "FAIL（missing=%d extra=%d func=%d dupes=%d）" % (len(missing), len(extra), len(changed), len(dupes))))
    return 0 if ok else 2


def self_test() -> int:
    tmp = tempfile.mkdtemp(prefix="route_diff_", dir=os.path.join(os.getcwd(), "data", "tmp"))
    try:
        base = os.path.join(tmp, "base.json")
        dump(None, base)
        rc0 = check(None, base)
        srcs = default_sources()

        def snapshot():
            """把「取源面」全件抄进 tmp（⛔ 动实物）——反控用副本集。"""
            out = []
            for q in srcs:
                d = os.path.join(tmp, os.path.basename(q))
                shutil.copyfile(q, d)
                out.append(d)
            return out

        # 反控 1：删一条路由
        copies = snapshot()
        host = next(q for q in copies if parse(q))
        lines = open(host, encoding="utf-8").read().splitlines()
        idx = next(i for i, l in enumerate(lines) if ROUTE.search(l))
        cut = lines[:idx] + lines[idx + 1:]
        p1 = os.path.join(tmp, "cut.py")
        open(host, "w", encoding="utf-8").write("\n".join(cut) + "\n")
        rc1 = check(copies, base)
        # 反控 2：改方法
        copies = snapshot()
        host = next(q for q in copies if parse(q))
        lines = open(host, encoding="utf-8").read().splitlines()
        mut = lines[:]
        i2 = next(i for i, l in enumerate(mut) if ROUTE.search(l) and "GET" not in l)
        mut[i2] = ROUTE.sub(lambda m: '@bp.route("%s", methods=["GET"])' % m.group(1), mut[i2])
        open(host, "w", encoding="utf-8").write("\n".join(mut) + "\n")
        rc2 = check(copies, base)
        ok = rc0 == 0 and rc1 == 2 and rc2 == 2
        print("[self-test] %s（正控=%d 反控删=%d 反控方法=%d）" % ("PASS" if ok else "FAIL", rc0, rc1, rc2))
        return 0 if ok else 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default=None)
    ap.add_argument("--check", default=None)
    ap.add_argument("--src", default=None)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.dump:
        return dump(a.src, a.dump)
    if a.check:
        return check(a.src, a.check)
    print("usage: --dump <json> | --check <json> [--src file] | --self-test")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
