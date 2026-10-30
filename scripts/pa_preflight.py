# -*- coding: utf-8 -*-
u"""pa_preflight.py -- PA 交付自检门（task-92 · **只读** · 单行 JSON）。

三面汇总：
  ① 版本：`core.lib.version.__version__`（真源，⛔ 手写）；
  ② 反目标：跑 `tools/check_anti_goals.py`（有 `--json` 则取其 JSON；无则解析
     `[PASS|FAIL|MANUAL] <id> ...` 行），汇总 **pass ／ fail ／ manual**（三态分离）；
  ③ 证据账：`core.pa.evidence_ledger.verify(ledger, max_age_days=30)`（30 天保鲜 ＋
     owner 读侧强制缺省）⇒ ok ／ total ／ bad。

输出（stdout 单行 JSON）：
  {"version": "...", "anti_goals": {...}, "ledger": {...}, "verdict": "..."}
  verdict ∈ PASS ／ PASS_WITH_MANUAL（**有 MANUAL ⇒ ⛔ 不判 PASS**）／ FAIL ／ ERROR

退出码：
  0 ＝ 无 FAIL 且 ledger ok（MANUAL 不算 FAIL ⇒ 可 0，但 verdict 明标 PASS_WITH_MANUAL）
  2 ＝ 有 FAIL 或 ledger bad
  3 ＝ 用法 ／ 运行错（脚本缺、anti-goals 无输出等）

边界：只读；⛔ 改产品码／路由；⛔ 把 MANUAL 当 PASS；⛔ 伪造账（ledger 唯读调用）。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MAX_AGE_DAYS = 30

MARK_RE = re.compile(r"^\[(PASS|FAIL|MANUAL)\]\s+(\S+)")

STATES = ("PASS", "FAIL", "MANUAL")


class _UsageError(Exception):
    u"""用法／参数形之错（退出码 3）。"""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise _UsageError(message)


def _quiet():
    u"""core.pa 导入期有配置/向量之印 ⇒ 导去 stderr，保 stdout 唯单行 JSON。"""
    sink = sys.stderr if sys.stderr is not None else io.StringIO()
    return contextlib.redirect_stdout(sink)


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()


def _error(exc, error_type=None):
    _emit({"version": None, "anti_goals": None, "ledger": None,
           "verdict": "ERROR", "error": str(exc)[:300],
           "error_type": error_type or type(exc).__name__})
    return 3


def _version():
    with _quiet():
        from core.lib.version import __version__
    return str(__version__)


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300)


def _counts_from_items(items):
    items = [x for x in items if isinstance(x, dict)]
    counts = {s: 0 for s in STATES}
    out = []
    for it in items:
        st = str(it.get("status") or "MANUAL")
        if st not in STATES:
            st = "MANUAL"
        counts[st] += 1
        out.append({"id": str(it.get("id") or ""), "status": st})
    return counts, out


def _summarize(doc):
    if not isinstance(doc, dict):
        raise ValueError("anti-goals JSON 非对象")
    items = doc.get("items")
    if isinstance(items, list) and items:
        counts, out_items = _counts_from_items(items)
    else:
        s = doc.get("summary") or {}
        counts = {st: int(s.get(st.lower(), 0) or 0) for st in STATES}
        out_items = []
    total = doc.get("summary", {}).get("total") if isinstance(doc.get("summary"), dict) else None
    return {"pass": counts["PASS"], "fail": counts["FAIL"], "manual": counts["MANUAL"],
            "total": int(total) if isinstance(total, int) else sum(counts.values()),
            "items": out_items,
            "status": str(doc.get("verdict") or "")}


def _parse_marks(text):
    items = []
    for line in (text or "").splitlines():
        m = MARK_RE.match(line.strip())
        if m:
            items.append({"id": m.group(2), "status": m.group(1)})
    return items


def _anti_goals(script, root):
    u"""跑 anti-goals 器 ⇒ 汇总；优先 `--json`（临时件），无则解析三态行。"""
    script = Path(script)
    if not script.is_file():
        raise RuntimeError("anti-goals 器不在：%s" % script)
    with tempfile.TemporaryDirectory(prefix="pa_preflight_") as td:
        json_path = Path(td) / "anti_goals.json"
        cmd = [sys.executable, "-X", "utf8", "-B", str(script),
               "--json", str(json_path), "--root", str(root)]
        first = _run(cmd)
        doc = None
        if json_path.is_file():
            try:
                doc = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                doc = None
        if doc is not None:
            got = _summarize(doc)
            got["rc"] = first.returncode
            return got
        # 回退：有些器无 --json ⇒ 无件；先看首跑 stdout，再不行重跑不带 --json
        items = _parse_marks(first.stdout)
        rc = first.returncode
        if not items:
            second = _run([sys.executable, "-X", "utf8", "-B", str(script),
                           "--root", str(root)])
            items = _parse_marks(second.stdout)
            rc = second.returncode
        if not items:
            raise RuntimeError("anti-goals 无 --json 件且无 PASS/FAIL/MANUAL 行（rc=%s）" % rc)
        counts, out_items = _counts_from_items(items)
        return {"pass": counts["PASS"], "fail": counts["FAIL"], "manual": counts["MANUAL"],
                "total": len(items), "items": out_items, "status": "", "rc": rc}


def _ledger_verify(ledger_path):
    with _quiet():
        from core.pa import evidence_ledger as EL
    path = ledger_path or str(EL.default_ledger_path())
    got = EL.verify(path, max_age_days=MAX_AGE_DAYS)
    out = {"ok": bool(got.get("ok")), "total": int(got.get("total") or 0),
           "bad": got.get("bad") or [], "max_age_days": MAX_AGE_DAYS,
           "path": str(path)}
    return out


def _build_parser():
    ap = _Parser(prog="pa_preflight.py", description=u"PA 交付自检门（版本／反目标／账 · 只读）")
    ap.add_argument("--ledger", default=None,
                    help=u"证据账径（缺省 env PA_EVIDENCE_LEDGER ／ PA 数据域）")
    ap.add_argument("--anti-goals-script", dest="anti_goals_script",
                    default=str(Path(ROOT) / "tools" / "check_anti_goals.py"),
                    help=u"反目标机检器之径（缺省 tools/check_anti_goals.py）")
    ap.add_argument("--root", default=ROOT, help=u"被检仓根（缺省本仓）")
    return ap


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    try:
        ns = parser.parse_args(args)
    except _UsageError as exc:
        return _error(exc, "usage")
    try:
        version = _version()
        anti = _anti_goals(ns.anti_goals_script, ns.root)
        ledger = _ledger_verify(ns.ledger)
    except Exception as exc:
        return _error(exc)
    anti_fail = int(anti.get("fail") or 0)
    anti_manual = int(anti.get("manual") or 0)
    ledger_ok = bool(ledger.get("ok"))
    if anti_fail or not ledger_ok:
        verdict, code = "FAIL", 2
    elif anti_manual:
        verdict, code = "PASS_WITH_MANUAL", 0
    else:
        verdict, code = "PASS", 0
    _emit({"version": version, "anti_goals": anti, "ledger": ledger, "verdict": verdict})
    return code


if __name__ == "__main__":
    raise SystemExit(main())
