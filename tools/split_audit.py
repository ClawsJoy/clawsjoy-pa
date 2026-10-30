# -*- coding: utf-8 -*-
"""split_audit.py — ②v1 拆件验收器（只读 · **适配 13 件架构**）。

判据（当前架构 · ②v1 拆件后 · 2026-10-30 T49）：
  1. 源面 ＝ `core/pa/pa_routes_*.py`（**12 件**，含公共件 `pa_routes_common.py`）
     ＋ `core/pa/gateway_routes.py`（**兼容门面**）⇒ 共 **13 件**；
  2. 公共件唯建蓝图（`bp = Blueprint`）＋ `def register_pa_routes(`；
     11 个簇件各有 `def register(`（导入即挂 · endpoint 名不变）；
  3. 每件 ≤800 行；
  4. 路由集（method+path+func）≡ 基线（现 103 条）；missing／extra／func 变／dupe ⇒ rc=2；
     基线若带 `count` 字段，须等于 `len(routes)`（⛔ 陈数）；
  5. 退出码：0 全绿 ／ 2 有红 ／ 4 未拆（NOT_SPLIT）。

用法：
  python -X utf8 -B tools/split_audit.py --check
  python -X utf8 -B tools/split_audit.py --self-test

边界：只读源码／基线；自测件落**系统 temp**（⛔ 写仓 ／ ⛔ 改产品路由）。
"""
from __future__ import annotations
import argparse
import glob
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_diff import parse  # noqa: E402

ROOT = "core/pa"
BASE = "tests/baseline/route_baseline_v0.json"

#: 期望之簇件数（pa_routes_*.py，含公共件 pa_routes_common.py）
EXPECT_CLUSTER_FILES = 12
#: 期望总件数（簇件 ＋ gateway_routes.py）
EXPECT_TOTAL_FILES = EXPECT_CLUSTER_FILES + 1
GATEWAY_NAME = "gateway_routes.py"
SHARED_NAME = "pa_routes_common.py"
MAX_LINES = 800


def _read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def _line_count(path):
    return sum(1 for _ in io.open(path, encoding="utf-8", errors="replace"))


def _row(path, role):
    """单件之读数：行数／路由数／角色／违例旗。"""
    txt = _read(path)
    lines = _line_count(path)
    flags = []
    if lines > MAX_LINES:
        flags.append(">800")
    if role == "shared":
        if "bp = Blueprint(" not in txt:
            flags.append("no-bp")
        if "def register_pa_routes(" not in txt:
            flags.append("no-register-pa")
    elif role == "cluster":
        if "def register(" not in txt:
            flags.append("no-register")
    # facade：兼容门面 ⛔ 另有形状要求（唯须在件；其路由计入比对）
    return {"name": os.path.basename(path), "lines": lines,
            "routes": len(parse(path)), "role": role, "flags": flags}


def audit(root, base, quiet=False, expect_files=EXPECT_CLUSTER_FILES):
    """验收一处拆件树。返回 (rc, info)。rc：0 绿 ／ 2 红 ／ 4 未拆。"""
    clusters = sorted(glob.glob(os.path.join(root, "pa_routes_*.py")))
    if not clusters:
        if not quiet:
            print("[NOT_SPLIT] %s 下无 pa_routes_*.py" % root)
        return 4, {"files": 0, "bad": 0, "missing": 0, "extra": 0,
                   "func": 0, "dupes": 0, "routes": 0}
    rows = []
    bad = 0
    for p in clusters:
        role = "shared" if os.path.basename(p) == SHARED_NAME else "cluster"
        row = _row(p, role)
        if row["flags"]:
            bad += 1
        rows.append(row)
    gateway = os.path.join(root, GATEWAY_NAME)
    if os.path.exists(gateway):
        row = _row(gateway, "facade")
        if row["flags"]:
            bad += 1
        rows.append(row)
    else:
        bad += 1
        rows.append({"name": GATEWAY_NAME, "lines": 0, "routes": 0,
                     "role": "facade", "flags": ["missing"]})
    if len(clusters) != expect_files:
        bad += 1

    # 路由集：全源面（簇件 ＋ 门面）逐件 parse；同 method+path 二次 ⇒ dupe
    got, dupes = {}, []
    for row in rows:
        path = os.path.join(root, row["name"])
        if not os.path.exists(path):
            continue
        for r in parse(path):
            key = (r["method"], r["path"])
            if key in got:
                dupes.append(key)
            got[key] = r.get("func", "")

    with io.open(base, encoding="utf-8") as fh:
        doc = json.load(fh)
    want = {(r["method"], r["path"]): r.get("func", "") for r in doc["routes"]}
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    changed = sorted(k for k in set(want) & set(got)
                     if want[k] and got[k] and want[k] != got[k])
    count_field = doc.get("count")
    count_stale = count_field is not None and count_field != len(want)
    if dupes:
        bad += 1
    if count_stale:
        bad += 1

    if not quiet:
        print("[files] %d（期望 %d = %d 个 pa_routes_*.py ＋ %s）｜shared=%s"
              % (len(rows), expect_files + 1, expect_files, GATEWAY_NAME, SHARED_NAME))
        for row in rows:
            print("  %-34s %5d 行  %3d 路由  %-7s %s"
                  % (row["name"], row["lines"], row["routes"], row["role"],
                     ",".join(row["flags"])))
        print("[routes] got=%d baseline=%d missing=%d extra=%d func=%d dupes=%d"
              % (len(got), len(want), len(missing), len(extra), len(changed), len(dupes)))
        if count_stale:
            print("  [COUNT]   基线 count=%r ≠ len(routes)=%d（陈数）"
                  % (count_field, len(want)))
        for m, p in missing[:5]:
            print("  [MISSING] %s %s" % (m, p))
        for m, p in extra[:5]:
            print("  [EXTRA]   %s %s" % (m, p))
        for k in changed[:5]:
            print("  [FUNC]    %s %s: %s -> %s" % (k[0], k[1], want[k], got[k]))
        for k in dupes[:5]:
            print("  [DUP]     %s %s" % k)

    ok = (bad == 0 and not missing and not extra and not changed
          and not dupes and not count_stale and len(rows) == expect_files + 1)
    if not quiet:
        print("[verdict] %s" % ("PASS（13 件 · diff=0）" if ok else
                                 "FAIL（files=%d bad=%d missing=%d extra=%d func=%d dupes=%d）"
                                 % (len(rows), bad, len(missing), len(extra),
                                    len(changed), len(dupes))))
    return (0 if ok else 2), {
        "files": len(rows), "bad": bad, "missing": len(missing),
        "extra": len(extra), "func": len(changed), "dupes": len(dupes),
        "routes": len(got),
    }


def _write(path, text):
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def self_test() -> int:
    """正控（形合 ⇒ 0）＋ 反控（>800 ⇒ 2；缺门面 ⇒ 2；基线多一条 ⇒ 2；空根 ⇒ 4）。"""
    tmp = tempfile.mkdtemp(prefix="split_audit_")
    try:
        root = os.path.join(tmp, "pa")
        os.makedirs(root)
        cluster = (
            'from flask import Blueprint\n'
            'bp = Blueprint("pa_routes", __name__)\n'
            '@bp.route("/v9/pa/x", methods=["GET"])\n'
            'def pa_x():\n    return "x"\n'
            '@bp.route("/v9/pa/y", methods=["POST"])\n'
            'def pa_y():\n    return "y"\n'
            'def register(bp):\n    return bp\n')
        common = ('from flask import Blueprint\n'
                  'bp = Blueprint("pa_routes", __name__)\n'
                  'def register_pa_routes(app, brain=None):\n    return bp\n')
        gateway = 'from core.pa.pa_routes_common import register_pa_routes\n'
        _write(os.path.join(root, "pa_routes_a.py"), cluster)
        _write(os.path.join(root, SHARED_NAME), common)
        gw_path = os.path.join(root, GATEWAY_NAME)
        _write(gw_path, gateway)
        base = os.path.join(tmp, "base.json")
        routes = [{"method": "GET", "path": "/v9/pa/x", "func": "pa_x"},
                  {"method": "POST", "path": "/v9/pa/y", "func": "pa_y"}]
        _write(base, json.dumps({"version": 1, "source": "pa_routes_*",
                                 "count": 2, "routes": routes}, ensure_ascii=False))

        rc_ok, _ = audit(root, base, quiet=True, expect_files=2)

        # 反控 1：801 行簇件 ⇒ 2
        big = os.path.join(root, "pa_routes_big.py")
        _write(big, "\n".join(["# x"] * 801) + "\n")
        rc_big, _ = audit(root, base, quiet=True, expect_files=2)
        os.remove(big)

        # 反控 2：缺兼容门面 ⇒ 2
        os.remove(gw_path)
        rc_nogw, _ = audit(root, base, quiet=True, expect_files=2)
        _write(gw_path, gateway)

        # 反控 3：基线多一条（current 缺） ⇒ 2
        base2 = os.path.join(tmp, "base2.json")
        more = routes + [{"method": "GET", "path": "/v9/pa/z", "func": "pa_z"}]
        _write(base2, json.dumps({"version": 1, "count": 3, "routes": more},
                                 ensure_ascii=False))
        rc_missing, _ = audit(root, base2, quiet=True, expect_files=2)

        # 反控 4：空根 ⇒ 4（NOT_SPLIT）
        empty = os.path.join(tmp, "empty")
        os.makedirs(empty)
        rc_empty, _ = audit(empty, base, quiet=True, expect_files=2)

        ok = (rc_ok == 0 and rc_big == 2 and rc_nogw == 2
              and rc_missing == 2 and rc_empty == 4)
        print("[self-test] %s（正控=%d 反控>800=%d 反控缺门面=%d 反控缺路由=%d 未拆=%d）"
              % ("PASS" if ok else "FAIL", rc_ok, rc_big, rc_nogw, rc_missing, rc_empty))
        return 0 if ok else 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--baseline", default=BASE)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.check:
        return audit(a.root, a.baseline)[0]
    print("usage: --check | --self-test [--root core/pa] [--baseline ...]")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
