# -*- coding: utf-8 -*-
u"""legacy_verify/run_quick.py -- legacy 9 检 quick 面复跑器（只读 · ⛔ 建端 · ⛔ 改 core/）.

面：**legacy_7_2** ＝ 7 PASS（C1/C2/C5/C6/C7/C10/C9）＋ 2 N/A（C12/C13：
quick 面 skip_scan 未扫 ⇒ ⛔ 计 PASS）。⛔ 不报 9/9。

依据（T106 PD 条件 → T112）：C10 由本层自含 **legacy_walker**（scandir 保已读 ＋ 错误入册
＋ 可选清单补面）**真 PASS**（⛔ 现役 os.walk(onerror) 之假面）；C12/C13 仍 N/A（旧码自动 True 是假绿路径）。

输出：stdout 单行 JSON
  {"face":"legacy_7_2","pass":7,"fail":0,"na":2,"results":[{"id","status","evidence"}...]}
退出码：0 ＝ 恰为 7/0/2 ∧ C10 PASS ∧ 9 条齐；2 ＝ 面漂移；3 ＝ 运行错（JSON 亦单行）。
只读：仅 import 现役模块 / 读文件 / GET localhost:5102/health ／ 5102/v9/pa/roster / psutil
读进程 —— ⛔ 写盘 ／ ⛔ 回落仓内 dev 清单（C2 反假绿）。
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legacy_verify.adapters import precision_inject_v9 as A  # noqa: E402

FACE = "legacy_7_2"
EXPECTED = {"pass": 7, "fail": 0, "na": 2}
BASE_PORT = 5102
NEWEST_SOURCES = ("core/pa/roster.py", "core/gateway/precision_inject.py",
                  "config/v9/execution_policy.yaml")
#: legacy 清单补面（可选；legacy 副本在本层 data/v9）
LEGACY_MANIFEST = ROOT / "legacy_verify" / "data" / "v9" / "vault_manifest_win.txt"
#: C2 活端（5102）；⛔ 回落仓内 dev 清单（T113 判：子集判 ／ 读 dev 皆假绿）
LIVE_ROSTER_URL = "http://127.0.0.1:%d/v9/pa/roster" % BASE_PORT


def _quiet():
    return contextlib.redirect_stdout(io.StringIO())


def _result(cid, status, evidence):
    return {"id": cid, "status": status, "evidence": evidence}


# ---------- C1/C2 现役 roster 自洽（PM 裁1：活端 6 为基） ----------

def _roster_default_ids():
    with _quiet():
        from core.pa import roster as R
    return [str(c.get("id") or "") for c in getattr(R, "_DEFAULT_CARDS", [])
            if isinstance(c, dict)]


def _fetch_live_roster(url=LIVE_ROSTER_URL, timeout=5):
    u"""取活端 roster（5102）⇒ (doc, "") ∨ (None, 因)；⛔ 读仓内 dev ／ ⛔ 回落。"""
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
                    "note": "活端 6 为基；⛔ obsidian_brain 期待作废（PM 裁1）"})


def check_c2():
    u"""C2：读**活端 5102** roster ⇒ count=6 ∧ ids **全等**默认 6（⛔ 子集 ／ ⛔ dev 14 回落）。

    端点不可用 ／ HTTP≠200 ／ JSON 坏 ⇒ **FAIL**（⛔ 读仓内 dev 清单充活端）。
    """
    doc, err = _fetch_live_roster()
    if doc is None:
        return _result("C2", "FAIL", {"url": LIVE_ROSTER_URL, "error": err,
                                      "note": "活端不可用 ⇒ FAIL（⛔ 回落 dev 14）"})
    try:
        defaults = _roster_default_ids()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C2", "FAIL", {"url": LIVE_ROSTER_URL,
                                      "error": "import roster 失败：%s" % type(exc).__name__})
    rows = doc.get("rows") if isinstance(doc, dict) else None
    ids = [str(r.get("id") or "") for r in (rows or []) if isinstance(r, dict)]
    count = doc.get("count") if isinstance(doc, dict) else None
    exact = (len(ids) == len(defaults) and sorted(ids) == sorted(defaults))
    ok = (count == 6 and len(ids) == 6 and exact and bool(defaults)
          and "obsidian_brain" not in ids)
    return _result("C2", "PASS" if ok else "FAIL",
                   {"url": LIVE_ROSTER_URL, "count": count, "rows_n": len(ids),
                    "ids": ids, "default_ids": defaults, "exact_eq": exact,
                    "note": "活端 6 全等（⛔ dev 14 子集）" if ok
                            else "活端非 6 全等 ⇒ FAIL（⛔ 假绿）"})


# ---------- C5/C6/C7/C10 适配层 ----------

def check_c5():
    try:
        got = A.knowledge_files_ok()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C5", "FAIL", "adapter knowledge_files_ok 异常：%s"
                       % type(exc).__name__)
    schema_ok = all(("sandbox_rel" in x["schema"] or "rel" in x["schema"])
                    for x in got.values())
    ok = bool(got) and schema_ok and all(x["exists"] for x in got.values())
    return _result("C5", "PASS" if ok else "FAIL",
                   {"files": got, "schema_compatible": schema_ok})


def check_c6():
    try:
        root = A.vault_root_or_none()
        sd = A.sops_dir()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C6", "FAIL", "adapter vault/sops 异常：%s" % type(exc).__name__)
    exists = bool(root is not None and sd and (root / sd).is_dir())
    return _result("C6", "PASS" if exists else "FAIL",
                   {"vault_root": str(root) if root is not None else None,
                    "sops_dir": sd, "exists": exists,
                    "note": "⛔ Path(空)→CWD" if root is None else ""})


def check_c7():
    cases = A.scan_excluded_cases()
    bad = {k: v for k, v in cases.items() if not v["ok"]}
    return _result("C7", "PASS" if not bad else "FAIL",
                   {"cases": cases, "mismatch": bad,
                    "note": "legacy 口径＝顶层段＋静态四名＋反斜杠归一"})


def check_c10():
    u"""C10：真跑本层 legacy 容错 walker（保已读 ＋ 错误入册 ＋ 可选清单补面）⇒ 可 PASS。

    判据（⛔ 空表假绿）：walker 面存在（walker id）∧ state=ok ∧ 有读数（files 或 errors）∧
    legacy_walk_errors() 为 **list**（⛔ None ／ ⛔ dict blocked）。清单缺失不算错（照实记 note）。
    """
    root = A.vault_root_or_none()
    manifest = LEGACY_MANIFEST if LEGACY_MANIFEST.is_file() else None
    try:
        rep = A.legacy_walk(root, manifest=manifest)
        errs = A.legacy_walk_errors()
    except Exception as exc:                                 # noqa: BLE001
        return _result("C10", "FAIL", "legacy_walker 异常：%s" % type(exc).__name__)
    walker_ok = (isinstance(rep, dict) and rep.get("walker") == "legacy_v5_tolerant"
                 and rep.get("state") == "ok")
    has_read = bool(int(rep.get("file_count") or 0) or int(rep.get("error_count") or 0))
    errors_ok = isinstance(errs, list)
    ok = walker_ok and has_read and errors_ok
    return _result("C10", "PASS" if ok else "FAIL",
                   {"walker": rep.get("walker"), "state": rep.get("state"),
                    "root": rep.get("root"), "file_count": rep.get("file_count"),
                    "error_count": rep.get("error_count"),
                    "errors": (errs or [])[:3],
                    "supplemented_count": rep.get("supplemented_count"),
                    "manifest": rep.get("manifest") or "",
                    "manifest_note": rep.get("manifest_note") or "",
                    "tolerant": "scandir 保已读 ＋ 错误入册（⛔ os.walk 整棵丢）",
                    "note": "C10 真 PASS（legacy_walker）" if ok
                            else "walker 不可用/不可验 ⇒ FAIL（⛔ 假绿）"})


# ---------- C12/C13 quick 面 N/A ----------

def check_c12():
    return _result("C12", "N/A",
                   {"reason": "quick 面 skip_scan 未扫（codex/ 容错恢复未验）",
                    "not_pass": True})


def check_c13():
    return _result("C13", "N/A",
                   {"reason": "quick 面 skip_scan 未扫；full 面另缺两份清单（B3）",
                    "not_pass": True})


# ---------- C9 base=5102 + health 200 + 进程起点 ----------

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
    base = A.base_url()
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
                    "note": "BASE=5102（⛔ 5002）；/health 200 ＋ 进程起点同验"})


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


def run_checks(checks=None):
    u"""跑 9 检（checks 可注入 {id: callable} 供测试）；返回 summarize() 之 dict。"""
    out = []
    for cid, fn in CHECKS:
        if checks is not None and cid in checks:
            out.append(checks[cid]())
        else:
            out.append(fn())
    return summarize(out)


def main(argv=None):
    try:
        with _quiet():
            doc = run_checks()
    except Exception as exc:                                 # noqa: BLE001
        doc = {"face": FACE, "pass": 0, "fail": 0, "na": 0, "results": [],
               "error": "%s: %s" % (type(exc).__name__, str(exc)[:200])}
        sys.stdout.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + chr(10))
        return 3
    sys.stdout.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + chr(10))
    ids = [r.get("id") for r in doc.get("results") or []]
    c10 = next((r for r in doc["results"] if r.get("id") == "C10"), None)
    profile_ok = (len(ids) == 9 and doc["pass"] == EXPECTED["pass"]
                  and doc["fail"] == EXPECTED["fail"] and doc["na"] == EXPECTED["na"])
    c10_ok = bool(c10) and c10.get("status") == "PASS"
    return 0 if (profile_ok and c10_ok) else 2


if __name__ == "__main__":
    raise SystemExit(main())
