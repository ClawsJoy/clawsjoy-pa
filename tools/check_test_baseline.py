#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试基线门禁(2026-09-13 基线归零起): 失败条数不增 + 每条失败/skip 必须登记。

为什么要有它:
  旧口径是"逐条同基线(保证不新增, 不保证清零)" —— **只比条数、不比内容**,
  于是"14 个基线失败"稳定多轮没人盘, 噪声里新增也看不出来
  (上一轮误归档 6 个在用模块时, 条数一度涨到 16 才被发现)。
新门禁三条:
  1. 失败条数 > 台账登记数(N) → 红
  2. 有失败但未在 failure_ledger.json 登记(性质/owner/计划) → 红
  3. 出现未在 skip_ledger.json 登记的 skip → 红(skip 不许当垃圾桶)

用法:
  python3 tools/check_test_baseline.py                  # 跑全量并判定
  python3 tools/check_test_baseline.py --no-run          # 只校验台账格式
  python3 tools/check_test_baseline.py --pytest-args "tests/unit -q --tb=no"
退出码: 0 通过 / 1 不通过
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

_REPO = pathlib.Path(__file__).resolve().parent.parent
# 台账**入库**(tests/baseline/, "登记"是可 review 的动作); 运行产物写 data/(gitignored)
_LEDGER = _REPO / "tests" / "baseline"
_RUN_DIR = _REPO / "data" / "test_baseline"
_STATUS_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)\b")
_SUMMARY_RE = re.compile(r"(\d+) (failed|passed|skipped|error)")


def _load(path):
    if not path.exists():
        print(f"[GATE] 缺台账: {path}")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def _run_pytest(extra):
    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=no", "-p", "no:cacheprovider"]
    if extra:
        cmd += extra.split()
    else:
        cmd += ["tests/"]
    print("[GATE] " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True)
    failed, skipped, counts = [], [], {}
    for line in p.stdout.splitlines():
        m = _STATUS_RE.match(line.strip())
        if m:
            _id, _st = m.group(1), m.group(2)
            if _st in ("FAILED", "ERROR"):
                failed.append(_id)
            elif _st == "SKIPPED":
                skipped.append(_id)
    tail = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ""
    for n, k in _SUMMARY_RE.findall(tail):
        counts[k] = int(n)
    return failed, skipped, counts, tail, p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-run", action="store_true", help="只校验台账格式, 不跑测试")
    ap.add_argument("--pytest-args", default="", help="覆盖 pytest 参数(默认 tests/ -v)")
    a = ap.parse_args()

    fl = _load(_LEDGER / "failure_ledger.json")
    sl = _load(_LEDGER / "skip_ledger.json")
    known = {e["id"]: e for e in fl.get("known_failures", [])}
    known_skip = {e["id"]: e for e in sl.get("skips", [])}
    print(f"[GATE] 登记失败 {len(known)} 条 / 登记 skip {len(known_skip)} 条")
    if a.no_run:
        print("[GATE] --no-run: 台账格式 OK")
        return 0

    failed, skipped, counts, tail, rc = _run_pytest(a.pytest_args)
    print(f"[GATE] {tail}")

    bad = []
    # 1) 条数
    if len(failed) > len(known):
        bad.append(f"失败条数 {len(failed)} > 台账登记 {len(known)}")
    # 2) 未登记失败
    unregistered = [t for t in failed if t not in known]
    if unregistered:
        bad.append("未登记失败(必须先登记性质/owner/计划): " + ", ".join(unregistered))
    # 3) 已登记但已修好的(台账要摘除, 防"登记了就一直挂着")
    stale = [t for t in known if t not in failed]
    if stale:
        bad.append("台账已登记但当前不再是失败(请从 known_failures 摘到 resolved): " + ", ".join(stale))
    # 4) 未登记 skip
    unreg_skip = [t for t in skipped if t not in known_skip]
    if unreg_skip:
        bad.append("未登记 skip: " + ", ".join(unreg_skip))
    miss_skip = [t for t in known_skip if t not in skipped]
    if miss_skip:
        bad.append("台账登记 skip 但当前已有结果(请更新 skip_ledger.json): " + ", ".join(miss_skip))

    _RUN_DIR.mkdir(parents=True, exist_ok=True)
    (_RUN_DIR / "last_run.json").write_text(
        json.dumps(
            {
                "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                "counts": counts,
                "failed": failed,
                "skipped": skipped,
                "registry": {"known_failures": len(known), "known_skips": len(known_skip)},
                "verdict": "PASS" if not bad else "FAIL",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if bad:
        print("\n[GATE] ❌ 不通过:")
        for b in bad:
            print("  - " + b)
        return 1
    print("\n[GATE] ✅ 通过(失败 0 · skip 全部登记 · 台账与实际一致)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
