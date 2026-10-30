# -*- coding: utf-8 -*-
u"""legacy_verify/run_quick 之测：面 7+2 · C10 真 PASS · C12/C13 N/A · ⛔ 9/9."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legacy_verify import run_quick as RQ
from legacy_verify.adapters import precision_inject_v9 as A

IDS = [cid for cid, _fn in RQ.CHECKS]

PASS_IDS = ("C1", "C2", "C5", "C6", "C7", "C10", "C9")
NA_IDS = ("C12", "C13")


def _res(cid, status, evidence=None):
    return {"id": cid, "status": status, "evidence": evidence or {}}


def _plan():
    plan = {cid: "PASS" for cid in PASS_IDS}
    plan.update({cid: "N/A" for cid in NA_IDS})
    return plan


def _injected(c10_status="PASS"):
    plan = _plan()
    plan["C10"] = c10_status
    return {cid: (lambda c=cid: _res(c, plan[c])) for cid in IDS}


# ---------- summarize / profile ----------

def test_summarize_counts_and_face():
    results = [_res("C1", "PASS"), _res("C2", "PASS"), _res("C5", "PASS"),
               _res("C6", "PASS"), _res("C7", "PASS"), _res("C10", "PASS"),
               _res("C12", "N/A"), _res("C13", "N/A"), _res("C9", "PASS")]
    doc = RQ.summarize(results)
    assert doc["face"] == "legacy_7_2"
    assert (doc["pass"], doc["fail"], doc["na"]) == (7, 0, 2), doc
    assert [r["id"] for r in doc["results"]] == ["C1", "C2", "C5", "C6", "C7",
                                                  "C10", "C12", "C13", "C9"]


def test_run_checks_expected_profile_injected():
    doc = RQ.run_checks(_injected())
    assert (doc["pass"], doc["fail"], doc["na"]) == (7, 0, 2), doc


def test_not_9_of_9():
    u"""7 PASS ＋ 2 N/A ⇒ ⛔ 9/9；N/A 不得当 PASS。"""
    doc = RQ.summarize([_res(cid, _plan()[cid]) for cid in IDS])
    assert doc["face"] == "legacy_7_2"
    assert doc["pass"] == 7 and doc["na"] == 2 and doc["fail"] == 0
    assert doc["pass"] != 9
    statuses = {r["id"]: r["status"] for r in doc["results"]}
    assert statuses["C12"] == "N/A" and statuses["C13"] == "N/A"


def test_c10_pass_uses_legacy_walker(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    monkeypatch.setattr(A, "vault_root_or_none", lambda: tmp_path)
    monkeypatch.setattr(RQ, "LEGACY_MANIFEST", tmp_path / "none_manifest.txt")
    got = RQ.check_c10()
    assert got["status"] == "PASS", got
    ev = got["evidence"]
    assert ev["walker"] == "legacy_v5_tolerant" and ev["file_count"] >= 1
    assert isinstance(ev["errors"], list) and ev["error_count"] == 0


def test_c10_fail_when_walker_unset(monkeypatch):
    monkeypatch.setattr(A, "vault_root_or_none", lambda: None)
    monkeypatch.setattr(RQ, "LEGACY_MANIFEST", Path("none_manifest.txt"))
    got = RQ.check_c10()
    assert got["status"] == "FAIL", got


def test_c12_c13_are_na_not_pass():
    for cid, fn in (("C12", RQ.check_c12), ("C13", RQ.check_c13)):
        got = fn()
        assert got["id"] == cid and got["status"] == "N/A", got
        assert got["evidence"].get("not_pass") is True


# ---------- C2：活端 5102 count=6 ∧ ids 全等（⛔ dev 14 子集） ----------

def _live_doc(ids, count=None):
    return {"ok": True, "count": count if count is not None else len(ids),
            "rows": [{"id": i} for i in ids]}


def _default_ids():
    return RQ._roster_default_ids()


def test_c2_live_six_exact_pass(monkeypatch):
    ids = _default_ids()
    monkeypatch.setattr(RQ, "_fetch_live_roster",
                        lambda url=RQ.LIVE_ROSTER_URL, timeout=5: (_live_doc(ids), ""))
    got = RQ.check_c2()
    assert got["status"] == "PASS", got
    assert got["evidence"]["url"] == "http://127.0.0.1:5102/v9/pa/roster"
    assert got["evidence"]["count"] == 6 and got["evidence"]["exact_eq"] is True


def test_c2_dev14_subset_is_red(monkeypatch):
    ids = _default_ids() + ["dev_%d" % i for i in range(8)]
    assert len(ids) == 14
    monkeypatch.setattr(RQ, "_fetch_live_roster",
                        lambda url=RQ.LIVE_ROSTER_URL, timeout=5: (_live_doc(ids), ""))
    got = RQ.check_c2()
    assert got["status"] == "FAIL", got
    assert got["evidence"]["count"] == 14 and got["evidence"]["exact_eq"] is False


def test_c2_endpoint_unavailable_fail(monkeypatch):
    monkeypatch.setattr(RQ, "_fetch_live_roster",
                        lambda url=RQ.LIVE_ROSTER_URL, timeout=5:
                        (None, "活端不可用：URLError（%s）" % url))
    got = RQ.check_c2()
    assert got["status"] == "FAIL", got
    assert "活端不可用" in got["evidence"]["error"]
    assert got["evidence"]["note"].startswith("活端不可用")


def test_c2_count6_but_ids_not_equal_fail(monkeypatch):
    ids = _default_ids()[:5] + ["extra"]
    monkeypatch.setattr(RQ, "_fetch_live_roster",
                        lambda url=RQ.LIVE_ROSTER_URL, timeout=5: (_live_doc(ids), ""))
    got = RQ.check_c2()
    assert got["status"] == "FAIL", got
    assert got["evidence"]["exact_eq"] is False


def test_c2_rows_not_six_fail(monkeypatch):
    ids = _default_ids() + ["extra"]
    monkeypatch.setattr(RQ, "_fetch_live_roster",
                        lambda url=RQ.LIVE_ROSTER_URL, timeout=5:
                        (_live_doc(ids, count=6), ""))
    got = RQ.check_c2()
    assert got["status"] == "FAIL", got


def test_c2_source_does_not_read_dev_roster_json():
    u"""⛔ 仓内 dev roster 回落：源内无该读法（唯一 C2 源＝活端常量）。"""
    src = (ROOT / "legacy_verify" / "run_quick.py").read_text(encoding="utf-8")
    assert "_roster_runtime_ids" not in src
    assert "roster.json" not in src
    assert "LIVE_ROSTER_URL" in src and ":5102" in src
    assert RQ.LIVE_ROSTER_URL == "http://127.0.0.1:5102/v9/pa/roster"


# ---------- C9 适配 ----------

def _fake_c9(monkeypatch, base="http://127.0.0.1:5102", health=200,
             proc=(1_700_000_000, ""), newest=1_699_999_990):
    monkeypatch.setattr(A, "base_url", lambda: base)
    monkeypatch.setattr(RQ, "_health_status", lambda url, timeout=5: health)
    monkeypatch.setattr(RQ, "_proc_started_after", lambda n: proc)
    monkeypatch.setattr(RQ, "_newest_source_mtime", lambda: newest)


def test_c9_pass_with_5102_health_and_fresh_process(monkeypatch):
    _fake_c9(monkeypatch)
    got = RQ.check_c9()
    assert got["status"] == "PASS", got


def test_c9_fail_on_5002(monkeypatch):
    _fake_c9(monkeypatch, base="http://127.0.0.1:5002")
    assert RQ.check_c9()["status"] == "FAIL"


def test_c9_fail_on_unhealthy(monkeypatch):
    _fake_c9(monkeypatch, health="ERR:URLError")
    assert RQ.check_c9()["status"] == "FAIL"


def test_c9_fail_on_stale_process(monkeypatch):
    _fake_c9(monkeypatch, proc=(1_699_999_000, ""), newest=1_699_999_990)
    assert RQ.check_c9()["status"] == "FAIL"


# ---------- main 退出码 ----------

def _doc(plan):
    return RQ.summarize([_res(cid, plan[cid]) for cid in IDS])


def test_main_exit0_on_expected_profile(monkeypatch, capsys):
    monkeypatch.setattr(RQ, "run_checks", lambda checks=None: _doc(_plan()))
    rc = RQ.main()
    raw = capsys.readouterr().out
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    assert rc == 0, (rc, raw)
    assert len(lines) == 1
    got = json.loads(lines[0])
    assert got["face"] == "legacy_7_2"
    assert (got["pass"], got["fail"], got["na"]) == (7, 0, 2)


def test_main_exit2_on_profile_drift(monkeypatch, capsys):
    plan = _plan()
    plan["C10"] = "FAIL"          # 6 PASS / 1 FAIL ⇒ 面漂移
    monkeypatch.setattr(RQ, "run_checks", lambda checks=None: _doc(plan))
    rc = RQ.main()
    capsys.readouterr()
    assert rc == 2


def test_main_exit2_if_c10_fail(monkeypatch, capsys):
    u"""计数纵 7/0/2，C10 非 PASS ⇒ 面判 2（⛔ 假绿）。"""
    doc = _doc(_plan())
    doc["results"] = [dict(r, status="FAIL") if r["id"] == "C10" else r
                      for r in doc["results"]]
    monkeypatch.setattr(RQ, "run_checks", lambda checks=None: doc)
    rc = RQ.main()
    capsys.readouterr()
    assert rc == 2, u"C10 ⛔ PASS ⇒ 面须 2"


def test_main_exit3_on_exception(monkeypatch, capsys):
    def _boom(checks=None):
        raise RuntimeError("boom")
    monkeypatch.setattr(RQ, "run_checks", _boom)
    rc = RQ.main()
    got = json.loads([ln for ln in capsys.readouterr().out.splitlines() if ln.strip()][0])
    assert rc == 3
    assert got["face"] == "legacy_7_2" and got["error"]
