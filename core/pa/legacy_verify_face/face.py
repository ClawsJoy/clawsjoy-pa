# -*- coding: utf-8 -*-
u"""legacy 7+2 检查面之产品化副本（T125 · 只读 · ⛔ 建路由 · ⛔ import 顶层 legacy_verify）.

面 **legacy_7_2** ＝ 7 PASS（C1/C2/C5/C6/C7/C10/C9）＋ 2 N/A（C12/C13：quick 面
skip_scan 未扫，⛔ 计 PASS）。C2 读活端 5102 roster 恰 6 全等；C10 真跑本包容错 walker；
C12/C13 明标 N/A。暴露 run_legacy_7_2() -> {face,pass,fail,na,results[]}。

唯读：import 现役模块 / 读文件 / GET localhost:5102 / psutil 读进程 —— ⛔ 写盘 / ⛔ 调子系统。
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from core.pa.legacy_verify_face import walker as W

FACE = "legacy_7_2"
EXPECTED = {"pass": 7, "fail": 0, "na": 2}
BASE_PORT = 5102
LIVE_ROSTER_URL = "http://127.0.0.1:%d/v9/pa/roster" % BASE_PORT
NEWEST_SOURCES = ("core/pa/roster.py", "core/gateway/precision_inject.py",
                  "config/v9/execution_policy.yaml")
ROOT = Path(__file__).resolve().parents[3]


def _result(cid, status, evidence):
    return {"id": cid, "status": status, "evidence": evidence}


# ---------- C1/C2：现役 roster（C2 活端 6 全等） ----------

def _roster_default_ids():
    from core.pa import roster as R
    return [str(c.get("id") or "") for c in getattr(R, "_DEFAULT_CARDS", [])
            if isinstance(c, dict)]


def _fetch_live_roster(url=LIVE_ROSTER_URL, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
    except Exception as exc:                                 # noqa: BLE001
        return None, "活端不可用：%s（%s）" % (type(exc).__name__, url)
    if status != 200:
        return None, "活端 HTTP %s（%s）" % (status, url)
    try:
        return json.loads(raw.decode("utf-8", "replace")), ""
    except Exception as exc:                                 # noqa: BLE001
        return None, "活端 JSON 不可解：%s（%s）" % (type(exc).__name__, url)


def check_c1():
    try:
        ids = _roster_default_ids()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C1", "FAIL", "import roster 失败：%s" % type(exc).__name__)
    ok = len(ids) == 6 and all(ids)
    return _result("C1", "PASS" if ok else "FAIL",
                   {"source_default_ids": ids, "n": len(ids),
                    "note": "活端 6 为基；⛔ obsidian_brain 期待作废"})


def check_c2():
    doc, err = _fetch_live_roster()
    if doc is None:
        return _result("C2", "FAIL", {"url": LIVE_ROSTER_URL, "error": err,
                                      "note": "活端不可用 ⇒ FAIL（⛔ 回落 dev）"})
    try:
        defaults = _roster_default_ids()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C2", "FAIL", {"url": LIVE_ROSTER_URL,
                                      "error": "import roster 失败：%s" % type(exc).__name__})
    rows = doc.get("rows") if isinstance(doc, dict) else None
    ids = [str(r.get("id") or "") for r in (rows or []) if isinstance(r, dict)]
    count = doc.get("count") if isinstance(doc, dict) else None
    exact = len(ids) == len(defaults) and sorted(ids) == sorted(defaults)
    ok = (count == 6 and len(ids) == 6 and exact and bool(defaults)
          and "obsidian_brain" not in ids)
    return _result("C2", "PASS" if ok else "FAIL",
                   {"url": LIVE_ROSTER_URL, "count": count, "rows_n": len(ids),
                    "ids": ids, "default_ids": defaults, "exact_eq": exact,
                    "note": "活端 6 全等（⛔ dev 14 子集）" if ok
                            else "活端非 6 全等 ⇒ FAIL"})


# ---------- C5/C6/C7：现役扫描模块之只读适配 ----------

def _pi():
    from core.gateway import precision_inject as pi
    return pi


def _vault_root_or_none():
    s = str(_pi()._vault_path() or "").strip()
    if not s or s == ".":
        return None
    return Path(s)


def _sops_dir():
    return str((_pi()._obsidian_cfg() or {}).get("sops_dir") or "SOPs")


def _knowledge_files_ok():
    pi = _pi()
    root = _vault_root_or_none()
    out = {}
    for key, info in (getattr(pi, "_KNOWLEDGE_FILES", {}) or {}).items():
        info = info if isinstance(info, dict) else {}
        path = None
        err = ""
        fn = getattr(pi, "_resolve_knowledge_path", None)
        if callable(fn):
            try:
                path = fn(key)
            except Exception as exc:                         # noqa: BLE001
                err = type(exc).__name__
        if path is None:
            rel = info.get("rel") or info.get("sandbox_rel")
            if root is not None and rel:
                path = root / str(rel)
        p = Path(str(path)) if path is not None else None
        out[key] = {"schema": sorted(str(k) for k in info.keys()),
                    "path": str(p) if p is not None else "",
                    "exists": bool(p is not None and p.is_file()),
                    "resolve_error": err}
    return out


def check_c5():
    try:
        got = _knowledge_files_ok()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C5", "FAIL", "knowledge 适配异常：%s" % type(exc).__name__)
    schema_ok = all(("sandbox_rel" in x["schema"] or "rel" in x["schema"])
                    for x in got.values())
    ok = bool(got) and schema_ok and all(x["exists"] for x in got.values())
    return _result("C5", "PASS" if ok else "FAIL",
                   {"files": got, "schema_compatible": schema_ok})


def check_c6():
    try:
        root = _vault_root_or_none()
        sd = _sops_dir()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C6", "FAIL", "vault/sops 适配异常：%s" % type(exc).__name__)
    exists = bool(root is not None and sd and (root / sd).is_dir())
    return _result("C6", "PASS" if exists else "FAIL",
                   {"vault_root": str(root) if root is not None else None,
                    "sops_dir": sd, "exists": exists,
                    "note": "⛔ Path(空)→CWD" if root is None else ""})


def _legacy_scan_excluded(rel):
    top = str(rel).replace(chr(92), "/").split("/", 1)[0]
    return top in W.DEFAULT_SKIP


def _scan_cases():
    cases = (
        ("_冷区/x.md", True), ("_垃圾箱/P/d.md", True),
        (".obsidian/x.md", True), ("Templates/t.md", True),
        ("工作区/SOPs/SOPs/a.md", False), ("dsh/a.md", False),
        ("工作区/_冷区/x.md", False),
        ("Templates" + chr(92) + "t.md", True),
    )
    return {rel: {"expected": exp, "actual": _legacy_scan_excluded(rel),
                  "ok": _legacy_scan_excluded(rel) == exp}
            for rel, exp in cases}


def check_c7():
    cases = _scan_cases()
    bad = {k: v for k, v in cases.items() if not v["ok"]}
    return _result("C7", "PASS" if not bad else "FAIL",
                   {"cases": cases, "mismatch": bad,
                    "note": "legacy 口径＝顶层段＋静态四名＋反斜杠归一"})


# ---------- C10：本包容错 walker（真 PASS） ----------

def check_c10():
    root = _vault_root_or_none()
    if root is None:
        return _result("C10", "FAIL", {"state": "unset", "root": None,
                                       "note": "vault 未接 ⇒ FAIL"})
    try:
        rep = W.walk(root)
        errs = W.last_walk_errors()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C10", "FAIL", "legacy walker 异常：%s" % type(exc).__name__)
    ok = (rep.get("walker") == W.WALKER_ID and rep.get("state") == "ok"
          and bool(int(rep.get("file_count") or 0)) and isinstance(errs, list))
    return _result("C10", "PASS" if ok else "FAIL",
                   {"walker": rep.get("walker"), "state": rep.get("state"),
                    "root": rep.get("root"), "file_count": rep.get("file_count"),
                    "error_count": rep.get("error_count"), "errors": (errs or [])[:3],
                    "tolerant": "scandir 保已读 ＋ 错误入册",
                    "note": "C10 真 PASS（本包 walker）" if ok else "walker 不可验 ⇒ FAIL"})


# ---------- C12/C13：quick 面 N/A ----------

def check_c12():
    return _result("C12", "N/A", {"reason": "quick 面 skip_scan 未扫（codex/ 容错恢复未验）",
                                  "not_pass": True})


def check_c13():
    return _result("C13", "N/A", {"reason": "quick 面 skip_scan 未扫；full 面清单另判",
                                  "not_pass": True})


# ---------- C9：5102 + health + 进程起点 ----------

def _base_url():
    env = (os.environ.get("PA_VERIFY_BASE") or "").strip()
    if env:
        return env.rstrip("/")
    try:
        from core.lib.port_config import gateway_base_url
        return gateway_base_url()
    except Exception:                                        # noqa: BLE001
        return "http://127.0.0.1:%d" % BASE_PORT


def _health_status(url, timeout=5):
    try:
        with urllib.request.urlopen(url + "/health", timeout=timeout) as resp:
            return resp.status
    except Exception as exc:                                 # noqa: BLE001
        return "ERR:%s" % type(exc).__name__


def _newest_source_mtime():
    newest = 0.0
    for rel in NEWEST_SOURCES:
        p = ROOT / rel
        if p.is_file():
            newest = max(newest, p.stat().st_mtime)
    return newest


def _proc_started_after(newest):
    try:
        import psutil
    except Exception:                                        # noqa: BLE001
        return None, "psutil 缺（进程起点不可验）"
    for p in psutil.process_iter(["cmdline", "create_time"]):
        cl = p.info.get("cmdline") or []
        if any("agent_gateway_enhanced" in str(c or "") for c in cl):
            ct = p.info.get("create_time")
            if ct is not None:
                return float(ct), ""
    return None, "无 agent_gateway_enhanced 进程"


def check_c9():
    base = _base_url()
    try:
        port = urllib.parse.urlsplit(base).port
    except Exception:                                        # noqa: BLE001
        port = None
    health = _health_status(base)
    newest = _newest_source_mtime()
    ct, why = _proc_started_after(newest)
    fresh_proc = ct is not None and ct >= newest
    ok = health == 200 and port == BASE_PORT and fresh_proc
    return _result("C9", "PASS" if ok else "FAIL",
                   {"base_url": base, "port": port, "health": health,
                    "process_start": (time.strftime("%Y-%m-%dT%H:%M:%S",
                                                    time.localtime(ct)) if ct else None),
                    "newest_source": time.strftime("%Y-%m-%dT%H:%M:%S",
                                                   time.localtime(newest)),
                    "process_fresh": fresh_proc, "why": why,
                    "note": "BASE=5102；/health 200 ＋ 进程起点同验"})


CHECKS = (
    ("C1", check_c1), ("C2", check_c2), ("C5", check_c5), ("C6", check_c6),
    ("C7", check_c7), ("C10", check_c10), ("C12", check_c12),
    ("C13", check_c13), ("C9", check_c9),
)


def summarize(results):
    counts = {"PASS": 0, "FAIL": 0, "N/A": 0}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"face": FACE, "pass": counts["PASS"], "fail": counts["FAIL"],
            "na": counts["N/A"], "results": results}


def run_legacy_7_2(checks=None):
    u"""跑 9 检（checks 可注入 {id: callable} 供测试）⇒ {face,pass,fail,na,results[]}。"""
    out = []
    for cid, fn in CHECKS:
        if checks is not None and cid in checks:
            out.append(checks[cid]())
        else:
            out.append(fn())
    return summarize(out)


__all__ = ["FACE", "EXPECTED", "LIVE_ROSTER_URL", "CHECKS", "summarize", "run_legacy_7_2"]
