# -*- coding: utf-8 -*-
u"""PA preflight 自检门之测（task-92）：版本 ／ 反目标三态 ／ 账 30 天保鲜 ／ 0-2-3 码。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_preflight.py -q
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib.version import __version__  # noqa: E402
from core.pa import evidence_ledger as EL  # noqa: E402

SCRIPT = ROOT / "scripts" / "pa_preflight.py"
_spec = importlib.util.spec_from_file_location("pa_preflight", str(SCRIPT))
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

KEYS = {"version", "anti_goals", "ledger", "verdict"}


def _call(capsys, argv):
    rc = cli.main(list(argv))
    raw = capsys.readouterr().out
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    assert len(lines) == 1, u"输出须为单行 JSON：%r" % raw
    return rc, json.loads(lines[0]), raw


def _statuses(n_pass=9, n_manual=1, n_fail=0):
    return ["PASS"] * n_pass + ["MANUAL"] * n_manual + ["FAIL"] * n_fail


def _fake_anti(tmp_path, statuses, name="fake_anti.py"):
    u"""假 anti-goals：有 --json ⇒ 写 JSON；同时打三态行。"""
    items = [{"id": "AG-%02d" % (i + 1), "status": st,
              "title": "fake %d" % (i + 1), "kind": "AUTO", "src": "x",
              "detail": "", "evidence": []} for i, st in enumerate(statuses)]
    summary = {"pass": statuses.count("PASS"), "fail": statuses.count("FAIL"),
               "manual": statuses.count("MANUAL"), "total": len(statuses)}
    doc = {"root": ".", "items": items, "summary": summary,
           "verdict": "FAIL" if summary["fail"] else
                      ("NO_FAIL_WITH_MANUAL" if summary["manual"] else "ALL_PASS")}
    p = tmp_path / name
    p.write_text(
        "import argparse, json, sys\n"
        "ap = argparse.ArgumentParser()\n"
        "ap.add_argument('--json')\n"
        "ap.add_argument('--root')\n"
        "a = ap.parse_args()\n"
        "items = " + repr(items) + "\n"
        "for it in items:\n"
        "    print('[%s] %s %s' % (it['status'], it['id'], it.get('title', '')))\n"
        "if a.json:\n"
        "    open(a.json, 'w', encoding='utf-8').write(" + repr(json.dumps(doc, ensure_ascii=False)) + ")\n"
        "raise SystemExit(2 if any(it['status'] == 'FAIL' for it in items) else 0)\n",
        encoding="utf-8")
    return p


def _fake_lines(tmp_path, statuses, name="fake_lines.py"):
    u"""假 anti-goals：**无 --json** 支持（额外参数忽略），只打三态行 ⇒ 走解析回退。"""
    body = "".join("print('[%s] AG-%02d fake')\n" % (st, i + 1)
                   for i, st in enumerate(statuses))
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def _ledger(tmp_path, tamper=False, ownerless=False):
    f = tmp_path / "ev.txt"
    f.write_bytes(b"evidence")
    rec = EL.build_record(f, "PM", "D-1", "pytest -q（两次同）")
    if ownerless:
        rec.pop("owner")
    if tamper:
        f.write_bytes(b"changed")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(json.dumps(rec, ensure_ascii=False) + chr(10), encoding="utf-8")
    return ledger


# ============================ 正例 / 三态 ============================

def test_pass_with_manual_rc0_and_verdict_not_pass(tmp_path, capsys):
    anti = _fake_anti(tmp_path, _statuses(n_pass=8, n_manual=2))
    ledger = _ledger(tmp_path)
    rc, out, raw = _call(capsys, ["--anti-goals-script", str(anti), "--ledger", str(ledger)])
    assert rc == 0, out
    assert set(out) == KEYS, out
    assert out["version"] == __version__, out
    ag = out["anti_goals"]
    assert (ag["pass"], ag["fail"], ag["manual"], ag["total"]) == (8, 0, 2, 10), ag
    assert out["verdict"] == "PASS_WITH_MANUAL", u"MANUAL ⛔ 当 PASS"
    assert out["verdict"] != "PASS"
    led = out["ledger"]
    assert led["ok"] is True and led["total"] == 1 and led["max_age_days"] == 30, led
    assert led["path"] == str(ledger), led


def test_all_pass_verdict_pass_rc0(tmp_path, capsys):
    anti = _fake_anti(tmp_path, _statuses(n_pass=10, n_manual=0))
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(anti), "--ledger", str(_ledger(tmp_path))])
    assert rc == 0, out
    assert out["anti_goals"]["manual"] == 0
    assert out["verdict"] == "PASS", out


def test_fail_status_rc2_verdict_fail(tmp_path, capsys):
    anti = _fake_anti(tmp_path, _statuses(n_pass=8, n_manual=1, n_fail=1))
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(anti), "--ledger", str(_ledger(tmp_path))])
    assert rc == 2, out
    assert out["anti_goals"]["fail"] == 1
    assert out["verdict"] == "FAIL", out


def test_manual_only_not_pass(tmp_path, capsys):
    anti = _fake_anti(tmp_path, _statuses(n_pass=9, n_manual=1))
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(anti), "--ledger", str(_ledger(tmp_path))])
    assert rc == 0, out
    assert out["anti_goals"]["manual"] == 1
    assert out["anti_goals"]["pass"] == 9
    assert out["verdict"] == "PASS_WITH_MANUAL", u"有 MANUAL ⇒ ⛔ 判「全绿」"


# ============================ 账（ledger 30d） ============================

def test_ledger_tamper_rc2_verdict_fail(tmp_path, capsys):
    anti = _fake_anti(tmp_path, _statuses(n_pass=10, n_manual=0))
    ledger = _ledger(tmp_path, tamper=True)
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(anti), "--ledger", str(ledger)])
    assert rc == 2, out
    led = out["ledger"]
    assert led["ok"] is False and led["bad"], led
    assert out["verdict"] == "FAIL", out


def test_ledger_missing_rc2(tmp_path, capsys):
    anti = _fake_anti(tmp_path, _statuses(n_pass=10, n_manual=0))
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(anti),
                                   "--ledger", str(tmp_path / "nope.jsonl")])
    assert rc == 2, out
    assert out["ledger"]["ok"] is False and out["ledger"]["total"] == 0, out["ledger"]
    assert out["verdict"] == "FAIL"


def test_ledger_ownerless_rc2(tmp_path, capsys):
    anti = _fake_anti(tmp_path, _statuses(n_pass=10, n_manual=0))
    ledger = _ledger(tmp_path, ownerless=True)
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(anti), "--ledger", str(ledger)])
    assert rc == 2, out
    assert out["ledger"]["bad"][0]["reason"] == "owner", out["ledger"]


# ============================ 回退：无 --json ⇒ 解析三态行 ============================

def test_fallback_parse_marks_pass_with_manual(tmp_path, capsys):
    anti = _fake_lines(tmp_path, _statuses(n_pass=7, n_manual=3))
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(anti), "--ledger", str(_ledger(tmp_path))])
    assert rc == 0, out
    ag = out["anti_goals"]
    assert (ag["pass"], ag["fail"], ag["manual"], ag["total"]) == (7, 0, 3, 10), ag
    assert out["verdict"] == "PASS_WITH_MANUAL", out


def test_fallback_parse_marks_fail_rc2(tmp_path, capsys):
    anti = _fake_lines(tmp_path, _statuses(n_pass=9, n_manual=0, n_fail=1))
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(anti), "--ledger", str(_ledger(tmp_path))])
    assert rc == 2, out
    assert out["anti_goals"]["fail"] == 1


# ============================ 用法 / 运行错 ============================

def test_anti_script_missing_rc3(tmp_path, capsys):
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(tmp_path / "nope.py"),
                                   "--ledger", str(_ledger(tmp_path))])
    assert rc == 3, out
    assert out["verdict"] == "ERROR" and out["error"], out


def test_anti_script_no_output_rc3(tmp_path, capsys):
    bad = tmp_path / "silent.py"
    bad.write_text("raise SystemExit(1)\n", encoding="utf-8")
    rc, out, _raw = _call(capsys, ["--anti-goals-script", str(bad), "--ledger", str(_ledger(tmp_path))])
    assert rc == 3, out
    assert out["verdict"] == "ERROR", out


def test_usage_bad_argument_rc3(capsys):
    rc, out, _raw = _call(capsys, ["--bogus-arg"])
    assert rc == 3, out
    assert out["verdict"] == "ERROR" and out["error_type"] == "usage"
