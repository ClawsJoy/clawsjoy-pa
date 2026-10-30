# -*- coding: utf-8 -*-
u"""件—账—印 evidence ledger 之测（task-82）：build_record ／ register（幂等 · 追加 · fsync）／
verify（重算 sha16 抓篡改）／ CLI（register ／ verify）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_evidence_ledger.py -q
"""
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import evidence_ledger as EL  # noqa: E402
from core.pa import relations as R  # noqa: E402

SCRIPT = ROOT / "scripts" / "pa_evidence_register.py"
_spec = importlib.util.spec_from_file_location("pa_evidence_register", str(SCRIPT))
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

RERUN = "python -X utf8 -B -m pytest tests/unit/test_pa_evidence_ledger.py -q（两次同）"


def _mk(tmp_path, name="件.txt", data=b"hello"):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def _rec(tmp_path, decision="D-20261030-01", owner=u"PM", data=b"hello", **over):
    p = _mk(tmp_path, data=data)
    return EL.build_record(p, owner, decision, RERUN, **over)


def _call(capsys, argv):
    rc = cli.main(list(argv))
    raw = capsys.readouterr().out
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    assert len(lines) == 1, u"输出须为单行 JSON：%r" % raw
    return rc, json.loads(lines[0]), raw


# ============================ build_record ============================

def test_build_record_positive(tmp_path):
    p = _mk(tmp_path, data=b"hello world")
    rec = EL.build_record(p, u"PM", "D-20261030-01", RERUN)
    for key in ("path", "bytes", "sha16", "captured_at", "rerun", "owner", "decision"):
        assert key in rec, (key, rec)
    assert rec["path"] == str(p)
    assert rec["bytes"] == 11
    assert rec["sha16"] == hashlib.sha256(b"hello world").hexdigest()[:16]
    assert datetime.fromisoformat(rec["captured_at"]).tzinfo is not None
    assert R.validate_evidence(rec) == {"ok": True, "missing": [], "errors": []}, rec


def test_build_record_captured_at_override_string(tmp_path):
    rec = _rec(tmp_path, captured_at="2026-10-01T12:00:00+08:00")
    assert rec["captured_at"] == "2026-10-01T12:00:00+08:00"


def test_build_record_captured_at_datetime(tmp_path):
    rec = _rec(tmp_path, captured_at=datetime(2026, 10, 1, 12, 0, 0))
    assert rec["captured_at"] == "2026-10-01T12:00:00"


def test_build_record_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        EL.build_record(tmp_path / "nope.bin", "PM", "D-20261030-01", RERUN)


@pytest.mark.parametrize("kw", [
    {"owner": ""}, {"owner": "   "}, {"decision": ""}, {"decision": "  "},
    {"rerun": ""}, {"rerun": "   "},
])
def test_build_record_invalid_fields(tmp_path, kw):
    p = _mk(tmp_path)
    args = {"owner": u"PM", "decision": "D-20261030-01", "rerun": RERUN}
    args.update(kw)
    with pytest.raises(EL.RecordInvalid):
        EL.build_record(p, args["owner"], args["decision"], args["rerun"])


def test_build_record_bad_captured_at_raises(tmp_path):
    with pytest.raises(EL.RecordInvalid):
        _rec(tmp_path, captured_at="not-a-date")


# ============================ register ============================

def test_register_appends_line_and_fsync(tmp_path, monkeypatch):
    calls = []
    real_fsync = EL.os.fsync

    def _spy(fd):
        calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(EL.os, "fsync", _spy)
    ledger = tmp_path / "deep" / "nested" / "ledger.jsonl"
    rec = _rec(tmp_path)
    got = EL.register(ledger, rec)
    assert got["registered"] is True and got["count"] == 1, got
    assert ledger.is_file()
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == rec
    assert lines[0] == EL._canonical(rec), u"行须为 canonical JSON"
    assert calls, u"登记须 fsync（⛔ 停页缓存）"


def test_register_idempotent_same_key(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    rec = _rec(tmp_path)
    assert EL.register(ledger, rec)["registered"] is True
    before = ledger.read_bytes()
    got = EL.register(ledger, rec)
    assert got["registered"] is False and got["count"] == 1, got
    assert ledger.read_bytes() == before, u"幂等命中 ⛔ 再写一行"


def test_register_idempotent_ignores_other_fields(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    p = _mk(tmp_path, data=b"same")
    r1 = EL.build_record(p, "PM", "D-1", RERUN, captured_at="2026-10-01T12:00:00+08:00")
    r2 = EL.build_record(p, "PM", "D-1", "另一次复跑", captured_at="2026-10-02T12:00:00+08:00")
    assert EL.register(ledger, r1)["registered"] is True
    got = EL.register(ledger, r2)
    assert got["registered"] is False, u"键＝path+sha16+decision ⇒ 其余字段 ⛔ 破幂等"
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_register_distinct_decision_appends(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    p = _mk(tmp_path)
    r1 = EL.build_record(p, "PM", "D-1", RERUN)
    r2 = EL.build_record(p, "PM", "D-2", RERUN)
    assert EL.register(ledger, r1)["count"] == 1
    got = EL.register(ledger, r2)
    assert got["registered"] is True and got["count"] == 2, got
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 2


def test_register_distinct_file_appends(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    r1 = EL.build_record(_mk(tmp_path, "a.txt", b"a"), "PM", "D-1", RERUN)
    r2 = EL.build_record(_mk(tmp_path, "b.txt", b"b"), "PM", "D-1", RERUN)
    EL.register(ledger, r1)
    assert EL.register(ledger, r2)["registered"] is True
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 2


def test_register_invalid_record_no_write(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    rec = _rec(tmp_path)
    rec.pop("sha16")
    with pytest.raises(EL.RecordInvalid):
        EL.register(ledger, rec)
    assert not ledger.exists(), u"形坏 ⇒ ⛔ 落半行"


def test_register_corrupt_ledger_raises_no_append(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("not-json" + chr(10), encoding="utf-8")
    before = ledger.read_bytes()
    with pytest.raises(EL.LedgerCorrupt):
        EL.register(ledger, _rec(tmp_path))
    assert ledger.read_bytes() == before, u"账坏 ⇒ ⛔ 静默续写"


def test_register_returns_key(tmp_path):
    rec = _rec(tmp_path, decision="D-9")
    got = EL.register(tmp_path / "ledger.jsonl", rec)
    assert got["key"] == {"path": rec["path"], "sha16": rec["sha16"], "decision": "D-9"}, got


# ============================ verify ============================

def test_verify_ok(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    r1 = EL.build_record(_mk(tmp_path, "a.txt", b"a"), "PM", "D-1", RERUN)
    r2 = EL.build_record(_mk(tmp_path, "b.txt", b"b"), "PM", "D-2", RERUN)
    EL.register(ledger, r1)
    EL.register(ledger, r2)
    got = EL.verify(ledger)
    assert got == {"ok": True, "total": 2, "bad": [], "superseded": []}, got


def test_verify_catches_file_tamper(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    p = _mk(tmp_path, data=b"original")
    rec = EL.build_record(p, "PM", "D-1", RERUN)
    EL.register(ledger, rec)
    p.write_bytes(b"tampered")
    got = EL.verify(ledger)
    assert got["ok"] is False and got["total"] == 1, got
    bad = got["bad"][0]
    assert bad["line"] == 1 and u"印不符" in bad["reason"], bad
    assert bad["actual_sha16"] != bad["expected_sha16"], bad


def test_verify_catches_ledger_field_tamper(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    p = _mk(tmp_path, data=b"abc")
    rec = EL.build_record(p, "PM", "D-1", RERUN)
    EL.register(ledger, rec)
    doc = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    doc["bytes"] = 999
    ledger.write_text(json.dumps(doc, ensure_ascii=False) + chr(10), encoding="utf-8")
    got = EL.verify(ledger)
    assert got["ok"] is False, got
    assert u"印不符" in got["bad"][0]["reason"], got["bad"]


def test_verify_missing_evidence_file(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    p = _mk(tmp_path, data=b"will-delete")
    EL.register(ledger, EL.build_record(p, "PM", "D-1", RERUN))
    p.unlink()
    got = EL.verify(ledger)
    assert got["ok"] is False and got["bad"][0]["line"] == 1, got
    assert u"件不可读" in got["bad"][0]["reason"], got["bad"]


def test_verify_bad_lines(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    text = chr(10).join(["not-json", "", "[1, 2]"]) + chr(10)
    ledger.write_text(text, encoding="utf-8")
    got = EL.verify(ledger)
    assert got["ok"] is False and got["total"] == 3, got
    reasons = [b["reason"] for b in got["bad"]]
    assert any(u"坏 JSON" in r for r in reasons), reasons
    assert any(u"空行" in r for r in reasons), reasons
    assert any(u"非对象" in r for r in reasons), reasons


def test_verify_missing_ledger(tmp_path):
    got = EL.verify(tmp_path / "nope.jsonl")
    assert got["ok"] is False and got["total"] == 0, got
    assert u"账件不存在" in got["bad"][0]["reason"], got


def test_verify_empty_ledger(tmp_path):
    ledger = tmp_path / "empty.jsonl"
    ledger.write_text("", encoding="utf-8")
    assert EL.verify(ledger) == {"ok": True, "total": 0, "bad": [], "superseded": []}


def test_verify_relative_path_with_base_dir(tmp_path):
    p = _mk(tmp_path / "docs", "x.md", b"rel")
    rec = EL.build_record(p, "PM", "D-1", RERUN)
    rec["path"] = "docs/x.md"
    ledger = tmp_path / "ledger.jsonl"
    EL.register(ledger, rec)
    assert EL.verify(ledger, base_dir=tmp_path)["ok"] is True
    assert EL.verify(ledger, base_dir=tmp_path / "elsewhere")["ok"] is False


def test_verify_is_readonly(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    p = _mk(tmp_path, data=b"ro")
    EL.register(ledger, EL.build_record(p, "PM", "D-1", RERUN))
    before = (ledger.read_bytes(), p.read_bytes())
    EL.verify(ledger)
    assert (ledger.read_bytes(), p.read_bytes()) == before


# ============================ 缺省账径优先级（T123） ============================

def _clear_path_env(monkeypatch):
    monkeypatch.delenv(EL.LEDGER_ENV, raising=False)
    monkeypatch.delenv(EL.DATA_ROOT_ENV, raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)


def test_default_ledger_path_env_wins_all(monkeypatch, tmp_path):
    u"""① PA_EVIDENCE_LEDGER > ② CLAWSJOY_DATA_DIR > ③ LOCALAPPDATA > ④ 仓 data。"""
    monkeypatch.setenv(EL.LEDGER_ENV, str(tmp_path / "x.jsonl"))
    monkeypatch.setenv(EL.DATA_ROOT_ENV, str(tmp_path / "root"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "la"))
    assert EL.default_ledger_path() == tmp_path / "x.jsonl"


def test_default_ledger_path_data_root(monkeypatch, tmp_path):
    _clear_path_env(monkeypatch)
    root = tmp_path / "root"
    monkeypatch.setenv(EL.DATA_ROOT_ENV, str(root))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "la"))
    assert EL.default_ledger_path() == root / "v9" / "pa" / "evidence_ledger.jsonl"


def test_default_ledger_path_localappdata(monkeypatch, tmp_path):
    _clear_path_env(monkeypatch)
    la = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(la))
    assert EL.default_ledger_path() == (la / "ClawsJoyPA" / "data" /
                                        "v9" / "pa" / "evidence_ledger.jsonl")


def test_default_ledger_path_repo_fallback(monkeypatch):
    _clear_path_env(monkeypatch)
    got = EL.default_ledger_path()
    assert got == EL.DEFAULT_LEDGER_PATH
    assert got == Path("data") / "v9" / "pa" / "evidence_ledger.jsonl"


def test_default_ledger_path_blank_env_ignored(monkeypatch, tmp_path):
    _clear_path_env(monkeypatch)
    monkeypatch.setenv(EL.LEDGER_ENV, "   ")
    monkeypatch.setenv(EL.DATA_ROOT_ENV, "")
    la = tmp_path / "la"
    monkeypatch.setenv("LOCALAPPDATA", str(la))
    assert EL.default_ledger_path() == (la / "ClawsJoyPA" / "data" /
                                        "v9" / "pa" / "evidence_ledger.jsonl")


def test_default_ledger_path_missing_root_not_fallback(monkeypatch, tmp_path):
    u"""根**不存在**亦照用（⛔ 存在性回落 —— 仅解析径）。"""
    _clear_path_env(monkeypatch)
    root = tmp_path / "missing_root"
    monkeypatch.setenv(EL.DATA_ROOT_ENV, str(root))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "la"))
    assert EL.default_ledger_path() == root / "v9" / "pa" / "evidence_ledger.jsonl"


def test_default_ledger_path_does_not_create_or_write(monkeypatch, tmp_path):
    u"""⛔ 建账 ／ ⛔ 写账：解析径不落盘、不建目录。"""
    _clear_path_env(monkeypatch)
    root = tmp_path / "new_root"
    monkeypatch.setenv(EL.DATA_ROOT_ENV, str(root))
    p = EL.default_ledger_path()
    assert p == root / "v9" / "pa" / "evidence_ledger.jsonl"
    assert not root.exists(), u"⛔ 建目录"
    assert not p.exists(), u"⛔ 建账"


def test_relations_status_source_uses_default_root(monkeypatch, tmp_path):
    u"""res/status 端点 source 应指向**真数据根**（T123 · 端点唯读未改语义）。"""
    from flask import Flask

    from core.pa.gateway_routes import register_pa_routes

    _clear_path_env(monkeypatch)
    root = tmp_path / "installed_root"
    monkeypatch.setenv(EL.DATA_ROOT_ENV, str(root))
    monkeypatch.setattr(EL, "verify",
                        lambda path, max_age_days=None, **kw:
                        {"ok": True, "total": 0, "bad": [], "superseded": []})
    app = Flask(__name__)
    register_pa_routes(app)
    r = app.test_client().get("/v9/pa/relations/status",
                              environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["source"] == str(root / "v9" / "pa" / "evidence_ledger.jsonl")
    assert d["ledger"]["max_age_days"] == 30


# ============================ CLI（register ／ verify） ============================

def test_cli_register_ok(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    ledger = tmp_path / "cli.jsonl"
    rc, out, _raw = _call(capsys, ["register", str(p), "--owner", "PM", "--decision", "D-1",
                                   "--rerun", "pytest -q（两次同）", "--ledger", str(ledger)])
    assert rc == 0, out
    assert out["ok"] is True and out["registered"] is True and out["count"] == 1, out
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_cli_register_idempotent_rc0(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    ledger = tmp_path / "cli.jsonl"
    argv = ["register", str(p), "--owner", "PM", "--decision", "D-1",
            "--rerun", "pytest -q（两次同）", "--ledger", str(ledger)]
    assert _call(capsys, argv)[0] == 0
    rc, out, _raw = _call(capsys, argv)
    assert rc == 0, out
    assert out["registered"] is False and out["count"] == 1, out


def test_cli_verify_ok_rc0(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    ledger = tmp_path / "cli.jsonl"
    _call(capsys, ["register", str(p), "--owner", "PM", "--decision", "D-1",
                   "--rerun", "pytest -q（两次同）", "--ledger", str(ledger)])
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger)])
    assert rc == 0, out
    assert out["ok"] is True and out["total"] == 1, out


def test_cli_verify_tamper_rc2(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    ledger = tmp_path / "cli.jsonl"
    _call(capsys, ["register", str(p), "--owner", "PM", "--decision", "D-1",
                   "--rerun", "pytest -q（两次同）", "--ledger", str(ledger)])
    p.write_bytes(b"changed")
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger)])
    assert rc == 2, out
    assert out["ok"] is False and out["bad"], out


def test_cli_register_missing_file_rc1(tmp_path, capsys):
    rc, out, _raw = _call(capsys, ["register", str(tmp_path / "nope.bin"), "--owner", "PM",
                                   "--decision", "D-1", "--rerun", "x",
                                   "--ledger", str(tmp_path / "cli.jsonl")])
    assert rc == 1, out
    assert out["ok"] is False, out


def test_cli_usage_missing_required_rc3(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    rc, out, _raw = _call(capsys, ["register", str(p), "--ledger", str(tmp_path / "cli.jsonl")])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


def test_cli_no_subcommand_rc3(capsys):
    rc, out, _raw = _call(capsys, [])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


# ============================ verify 接 C15 保鲜（T85） ============================

def _stamp(days=0.0, hours=0.0):
    now = datetime.now().astimezone()
    return (now - timedelta(days=days, hours=hours)).isoformat(timespec="seconds")


def _reg_at(tmp_path, captured_at, decision="D-1", name="件.txt"):
    p = _mk(tmp_path, name)
    rec = EL.build_record(p, "PM", decision, RERUN, captured_at=captured_at)
    ledger = tmp_path / (decision + ".jsonl")
    EL.register(ledger, rec)
    return ledger


def test_verify_max_age_fresh_ok(tmp_path):
    ledger = _reg_at(tmp_path, _stamp(hours=1))
    got = EL.verify(ledger, max_age_days=30)
    assert got == {"ok": True, "total": 1, "bad": [], "superseded": []}, got


def test_verify_max_age_stale_bad(tmp_path):
    ledger = _reg_at(tmp_path, _stamp(days=31))
    got = EL.verify(ledger, max_age_days=30)
    assert got["ok"] is False and got["total"] == 1, got
    bad = got["bad"][0]
    assert bad["reason"] == "stale", bad
    assert bad["age_days"] is not None and abs(bad["age_days"] - 31) < 0.1, bad
    assert any(u"超期" in e for e in bad["freshness_errors"]), bad


def test_verify_max_age_future_bad(tmp_path):
    ledger = _reg_at(tmp_path, _stamp(days=-1))
    got = EL.verify(ledger, max_age_days=30)
    assert got["ok"] is False, got
    bad = got["bad"][0]
    assert bad["reason"] == "future", bad
    assert bad["age_days"] < 0, bad


def test_verify_max_age_override_widens_window(tmp_path):
    ledger = _reg_at(tmp_path, _stamp(days=31))
    assert EL.verify(ledger, max_age_days=40)["ok"] is True, u"TTL 覆宽 ⇒ 31 日龄仍新鲜"
    assert EL.verify(ledger, max_age_days=30)["ok"] is False


def test_verify_default_without_max_age_unchanged(tmp_path):
    u"""不传 max_age_days ⇒ **行为与旧同**：只校形/印，旧证不因「老」而红。"""
    ledger = _reg_at(tmp_path, _stamp(days=400))
    assert EL.verify(ledger) == {"ok": True, "total": 1, "bad": [], "superseded": []}
    assert EL.verify(ledger, max_age_days=None)["ok"] is True
    assert EL.verify(ledger, max_age_days=30)["ok"] is False


def test_verify_max_age_sha_tamper_precedes_freshness(tmp_path):
    p = _mk(tmp_path, "件.txt", b"orig")
    ledger = tmp_path / "ledger.jsonl"
    EL.register(ledger, EL.build_record(p, "PM", "D-1", RERUN, captured_at=_stamp(hours=1)))
    p.write_bytes(b"tampered")
    got = EL.verify(ledger, max_age_days=30)
    assert got["ok"] is False
    assert u"印不符" in got["bad"][0]["reason"], got["bad"]


def test_verify_max_age_invalid_raises(tmp_path):
    ledger = _reg_at(tmp_path, _stamp(hours=1))
    for bad in (0, -1, 0.0, "30", True, []):
        with pytest.raises(ValueError):
            EL.verify(ledger, max_age_days=bad)


def test_verify_max_age_multiple_lines_only_stale_flagged(tmp_path):
    p1 = _mk(tmp_path, "fresh.txt", b"f")
    p2 = _mk(tmp_path, "stale.txt", b"s")
    ledger = tmp_path / "ledger.jsonl"
    EL.register(ledger, EL.build_record(p1, "PM", "D-1", RERUN, captured_at=_stamp(hours=1)))
    EL.register(ledger, EL.build_record(p2, "PM", "D-2", RERUN, captured_at=_stamp(days=31)))
    got = EL.verify(ledger, max_age_days=30)
    assert got["total"] == 2 and got["ok"] is False, got
    assert len(got["bad"]) == 1 and got["bad"][0]["line"] == 2, got["bad"]
    assert got["bad"][0]["reason"] == "stale"


# ---------- CLI --max-age-days ----------

def _register_cli(capsys, p, ledger, captured_at, decision="D-1"):
    return _call(capsys, ["register", str(p), "--owner", "PM", "--decision", decision,
                          "--rerun", "pytest -q（两次同）", "--ledger", str(ledger),
                          "--captured-at", captured_at])


def test_cli_verify_max_age_fresh_rc0(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    ledger = tmp_path / "cli.jsonl"
    assert _register_cli(capsys, p, ledger, _stamp(hours=1))[0] == 0
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger), "--max-age-days", "30"])
    assert rc == 0, out
    assert out["ok"] is True and out["total"] == 1, out


def test_cli_verify_max_age_stale_rc2(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    ledger = tmp_path / "cli.jsonl"
    assert _register_cli(capsys, p, ledger, _stamp(days=31))[0] == 0
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger), "--max-age-days", "30"])
    assert rc == 2, out
    assert out["ok"] is False and out["bad"][0]["reason"] == "stale", out


def test_cli_verify_max_age_future_rc2(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    ledger = tmp_path / "cli.jsonl"
    assert _register_cli(capsys, p, ledger, _stamp(days=-1))[0] == 0
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger), "--max-age-days", "30"])
    assert rc == 2, out
    assert out["bad"][0]["reason"] == "future", out


def test_cli_verify_without_max_age_default_rc0(tmp_path, capsys):
    p = _mk(tmp_path, "件.txt", b"cli")
    ledger = tmp_path / "cli.jsonl"
    assert _register_cli(capsys, p, ledger, _stamp(days=400))[0] == 0
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger)])
    assert rc == 0, out
    assert out["ok"] is True, out


def test_cli_verify_max_age_bad_value_rc3(tmp_path, capsys):
    ledger = _reg_at(tmp_path, _stamp(hours=1))
    for bad in ("0", "-1", "abc"):
        rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger), "--max-age-days", bad])
        assert rc == 3, (bad, out)
        assert out["ok"] is False and out["error_type"] == "usage", (bad, out)


# ============================ owner 读侧强制（T89） ============================

REAL_LEDGER = ROOT / "data" / "v9" / "pa" / "evidence_ledger.jsonl"


def _ownerless_ledger(tmp_path, owner=u"<pop>"):
    p = _mk(tmp_path, "ownerless.txt", b"ownerless")
    rec = EL.build_record(p, "PM", "D-1", RERUN)
    if owner == u"<pop>":
        rec.pop("owner")
    else:
        rec["owner"] = owner
    ledger = tmp_path / "ownerless.jsonl"
    ledger.write_text(json.dumps(rec, ensure_ascii=False) + chr(10), encoding="utf-8")
    return ledger


def test_verify_owner_required_by_default(tmp_path):
    ledger = _ownerless_ledger(tmp_path)
    got = EL.verify(ledger)
    assert got["ok"] is False and got["total"] == 1, got
    bad = got["bad"][0]
    assert bad["reason"] == "owner", bad
    assert "owner" in bad["missing"], bad


def test_verify_owner_missing_can_be_read_with_flag_off(tmp_path):
    u"""旧账（无主）⇒ 显式 require_owner=False 方可通过（T82/T84 兼容口）。"""
    ledger = _ownerless_ledger(tmp_path)
    got = EL.verify(ledger, require_owner=False)
    assert got == {"ok": True, "total": 1, "bad": [], "superseded": []}, got


@pytest.mark.parametrize("owner", ["", "   ", 123])
def test_verify_owner_blank_or_nonstr_bad(tmp_path, owner):
    ledger = _ownerless_ledger(tmp_path, owner=owner)
    got = EL.verify(ledger)
    assert got["ok"] is False, (owner, got)
    assert got["bad"][0]["reason"] == "owner", got["bad"]
    assert EL.verify(ledger, require_owner=False)["ok"] is True, u"关闭 ⇒ 只校形/印"


def test_register_rejects_ownerless_record(tmp_path):
    rec = _rec(tmp_path)
    rec.pop("owner")
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(EL.RecordInvalid):
        EL.register(ledger, rec)
    assert not ledger.exists(), u"写侧强制 owner ⇒ ⛔ 落无主行"


def test_cli_verify_owner_required_default_rc2(tmp_path, capsys):
    ledger = _ownerless_ledger(tmp_path)
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger)])
    assert rc == 2, out
    assert out["ok"] is False and out["bad"][0]["reason"] == "owner", out


def test_cli_verify_no_require_owner_rc0(tmp_path, capsys):
    ledger = _ownerless_ledger(tmp_path)
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger), "--no-require-owner"])
    assert rc == 0, out
    assert out["ok"] is True and out["total"] == 1, out


def test_cli_verify_require_owner_explicit_rc2(tmp_path, capsys):
    ledger = _ownerless_ledger(tmp_path)
    rc, out, _raw = _call(capsys, ["verify", "--ledger", str(ledger), "--require-owner"])
    assert rc == 2, out
    assert out["bad"][0]["reason"] == "owner", out


@pytest.mark.skipif(not REAL_LEDGER.exists(), reason=u"真实账不在")
def test_real_ledger_records_have_owner_and_pass_owner_gate():
    u"""真实账（随合法入账演进 · 现 ≥5 条）：owner 读侧强制**不误伤**（无一条 reason=owner）。

    ⚠ 本测不钉行数：账为 append-only（T84/T90/T93 等合法追加会增行）；只钉 owner 面合规
      与「无 owner 之 bad」。⛔ 改真账、⛔ 造绿。
    """
    recs = [json.loads(ln) for ln in REAL_LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(recs) >= 5, len(recs)
    assert all(isinstance(r.get("owner"), str) and r["owner"].strip() for r in recs), recs
    got = EL.verify(REAL_LEDGER)
    assert [b for b in got["bad"] if b.get("reason") == "owner"] == [], got


@pytest.mark.skipif(not REAL_LEDGER.exists(), reason=u"真实账不在")
def test_real_ledger_evidence_refreshed_copy_ok(tmp_path):
    u"""真实账证据之**刷新副本** ⇒ owner 强制下全绿（⛔ 改真账；副本于 tmp）。

    由：T89 改 `relations.py`（账第 3 条之件）⇒ 真账该条 stale；按 T84 流程刷新证据后，
     各条在缺省 owner 强制 + 30 天保鲜下应全绿 —— 此为「owner 面不误伤」之强证。
    """
    recs = [json.loads(ln) for ln in REAL_LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    fresh = []
    for rec in recs:
        doc = dict(rec)
        target = Path(str(doc.get("path") or ""))
        if target.is_file():
            blob = target.read_bytes()
            sha = hashlib.sha256(blob).hexdigest()[:16]
            if len(blob) != doc.get("bytes") or sha != doc.get("sha16"):
                doc["bytes"] = len(blob)
                doc["sha16"] = sha
        fresh.append(doc)
    copy = tmp_path / "refreshed.jsonl"
    copy.write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in fresh),
                    encoding="utf-8")
    evidence_n = len([r for r in recs if r.get("kind") != "supersede"])
    got = EL.verify(copy, max_age_days=30)
    assert got == {"ok": True, "total": evidence_n, "bad": [], "superseded": []}, got


# ============================ supersede（T93） ============================

def _stale_ledger(tmp_path, name="stale.txt"):
    p = _mk(tmp_path, name, b"old")
    rec = EL.build_record(p, "PM", "D-1", RERUN)
    ledger = tmp_path / "ledger.jsonl"
    EL.register(ledger, rec)
    p.write_bytes(b"new")          # 合法改件 ⇒ 旧印 stale
    return ledger, p, rec


def test_supersede_appends_and_verify_marks_superseded(tmp_path):
    ledger, _p, rec = _stale_ledger(tmp_path)
    before = ledger.read_bytes()
    n_before = len(before.splitlines())
    got = EL.supersede(ledger, rec["path"], rec["sha16"], "D-2", "PA",
                       u"T93：合法改件后旧印退役（留史 ⛔ 删）")
    assert got["registered"] is True and got["kind"] == "supersede", got
    after = ledger.read_bytes()
    assert after.startswith(before), u"supersede ⛔ 改旧行（唯追加）"
    assert len(after.splitlines()) == n_before + 1

    ver = EL.verify(ledger)
    assert ver["ok"] is True and ver["bad"] == [] and ver["total"] == 1, ver
    assert len(ver["superseded"]) == 1, ver
    row = ver["superseded"][0]
    assert row["line"] == 1 and row["reason"] == "superseded", row
    assert row["sha16"] == rec["sha16"] and row["decision"] == "D-2", row
    # 旧行逐字节仍在
    assert after.splitlines()[:n_before] == before.splitlines()


def test_supersede_missing_old_key_rejected(tmp_path):
    ledger, _p, _rec = _stale_ledger(tmp_path)
    before = ledger.read_bytes()
    with pytest.raises(EL.RecordInvalid):
        EL.supersede(ledger, "core/pa/x.py", "0" * 16, "D-2", "PA", "无此旧记录")
    assert ledger.read_bytes() == before, u"缺旧键 ⇒ ⛔ 空退"


def test_supersede_duplicate_is_idempotent(tmp_path):
    ledger, _p, rec = _stale_ledger(tmp_path)
    first = EL.supersede(ledger, rec["path"], rec["sha16"], "D-2", "PA", "r1")
    lines1 = len(ledger.read_text(encoding="utf-8").splitlines())
    second = EL.supersede(ledger, rec["path"], rec["sha16"], "D-3", "PA", "r2")
    assert first["registered"] is True
    assert second["registered"] is False, second
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == lines1, u"重复 ⛔ 重记"
    assert len(EL.verify(ledger)["superseded"]) == 1


@pytest.mark.parametrize("reason", ["", "   ", 123, None])
def test_supersede_bad_reason_rejected(tmp_path, reason):
    ledger, _p, rec = _stale_ledger(tmp_path)
    before = ledger.read_bytes()
    with pytest.raises(EL.RecordInvalid):
        EL.supersede(ledger, rec["path"], rec["sha16"], "D-2", "PA", reason)
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("kw", [
    {"path": ""},
    {"sha16": "A" * 16},
    {"sha16": "0" * 15},
    {"decision": ""},
    {"owner": "  "},
])
def test_supersede_bad_inputs_rejected(tmp_path, kw):
    ledger, _p, rec = _stale_ledger(tmp_path)
    args = {"path": rec["path"], "sha16": rec["sha16"], "decision": "D-2",
            "owner": "PA", "reason": "r"}
    args.update(kw)
    before = ledger.read_bytes()
    with pytest.raises(EL.RecordInvalid):
        EL.supersede(ledger, args["path"], args["sha16"],
                     args["decision"], args["owner"], args["reason"])
    assert ledger.read_bytes() == before


def test_supersede_file_unchanged_not_marked(tmp_path):
    u"""件仍与旧印同 ⇒ 未「已不同」⇒ ⛔ 归 superseded（旧行照常过）。"""
    p = _mk(tmp_path, "same.txt", b"same")
    rec = EL.build_record(p, "PM", "D-1", RERUN)
    ledger = tmp_path / "ledger.jsonl"
    EL.register(ledger, rec)
    EL.supersede(ledger, rec["path"], rec["sha16"], "D-2", "PA", "未改件")
    ver = EL.verify(ledger)
    assert ver["ok"] is True and ver["total"] == 1 and ver["superseded"] == [], ver


def test_supersede_missing_file_marked_superseded(tmp_path):
    p = _mk(tmp_path, "gone.txt", b"gone")
    rec = EL.build_record(p, "PM", "D-1", RERUN)
    ledger = tmp_path / "ledger.jsonl"
    EL.register(ledger, rec)
    p.unlink()
    EL.supersede(ledger, rec["path"], rec["sha16"], "D-2", "PA", "件已移")
    ver = EL.verify(ledger)
    assert ver["ok"] is True and ver["bad"] == [], ver
    assert len(ver["superseded"]) == 1 and ver["superseded"][0]["line"] == 1


def test_verify_malformed_supersede_line_is_bad(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    good = EL.build_record(_mk(tmp_path, "g.txt", b"g"), "PM", "D-1", RERUN)
    EL.register(ledger, good)
    bad = {"kind": "supersede", "path": good["path"], "sha16": "zzz"}
    ledger.write_text(ledger.read_text(encoding="utf-8") + json.dumps(bad) + chr(10),
                      encoding="utf-8")
    ver = EL.verify(ledger)
    assert ver["ok"] is False, ver
    assert any(b.get("reason") == "supersede 形坏" for b in ver["bad"]), ver["bad"]
    assert ver["total"] == 1, u"supersede 行 ⛔ 计 total"


@pytest.mark.skipif(not REAL_LEDGER.exists(), reason=u"真实账不在")
def test_real_ledger_copy_supersede_old_stale(tmp_path):
    u"""真账副本：对旧 stale（优先 ad42）supersede ⇒ verify bad=0 / superseded≥1；真账 ⛔ 动。"""
    real_before = REAL_LEDGER.read_bytes()
    recs = [json.loads(ln) for ln in real_before.decode("utf-8").splitlines() if ln.strip()]
    evidence = [r for r in recs if r.get("kind") != "supersede"]
    existing = {(str(r.get("path") or ""), str(r.get("sha16") or ""))
                for r in recs if r.get("kind") == "supersede"}
    stale = None
    for rec in evidence:
        key = (str(rec.get("path") or ""), str(rec.get("sha16") or ""))
        if key in existing:
            continue                     # 已 supersede 之旧印（T93 真跑）⛔ 重记
        target = Path(str(rec.get("path") or ""))
        if not target.is_file():
            stale = rec
            break
        blob = target.read_bytes()
        sha = hashlib.sha256(blob).hexdigest()[:16]
        if len(blob) != rec.get("bytes") or sha != rec.get("sha16"):
            stale = rec
            break
    copy = tmp_path / "real_copy.jsonl"
    copy.write_bytes(real_before)
    if stale is None:
        # 真账 stale 已 supersede（T93 真跑）⇒ 副本 verify 应已全绿；同键再 supersede ⇒ 幂等 False
        ver = EL.verify(copy, max_age_days=30)
        assert ver["ok"] is True and ver["bad"] == [], ver
        assert ver["total"] == len(evidence), (ver["total"], len(evidence))
        assert ver["superseded"], u"真账应有 superseded 留痕"
        old = ver["superseded"][0]
        got = EL.supersede(copy, old["path"], old["sha16"], "D-08", "PA",
                           u"T93 已 supersede（幂等）")
        assert got["registered"] is False, got
        assert REAL_LEDGER.read_bytes() == real_before, u"⛔ 动真账"
        return
    got = EL.supersede(copy, stale["path"], stale["sha16"], "D-08", "PA",
                       u"T93：T89 合法改件后旧印退役")
    assert got["registered"] is True, got
    ver = EL.verify(copy, max_age_days=30)
    assert ver["ok"] is True and ver["bad"] == [], ver
    assert ver["total"] == len(evidence), (ver["total"], len(evidence))
    assert stale["sha16"] in [s["sha16"] for s in ver["superseded"]], ver["superseded"]
    assert REAL_LEDGER.read_bytes() == real_before, u"⛔ 动真账"


# ---------- CLI supersede ----------

def _cli_supersede(capsys, ledger, rec, reason="T93 退旧印", decision="D-2"):
    return _call(capsys, ["supersede", rec["path"], "--sha16", rec["sha16"],
                          "--decision", decision, "--owner", "PA",
                          "--reason", reason, "--ledger", str(ledger)])


def test_cli_supersede_ok(tmp_path, capsys):
    ledger, _p, rec = _stale_ledger(tmp_path)
    rc, out, _raw = _cli_supersede(capsys, ledger, rec)
    assert rc == 0, out
    assert out["ok"] is True and out["registered"] is True and out["kind"] == "supersede", out
    rc2, ver, _raw2 = _call(capsys, ["verify", "--ledger", str(ledger)])
    assert rc2 == 0, ver
    assert ver["ok"] is True and len(ver["superseded"]) == 1


def test_cli_supersede_duplicate_rc0(tmp_path, capsys):
    ledger, _p, rec = _stale_ledger(tmp_path)
    assert _cli_supersede(capsys, ledger, rec)[0] == 0
    rc, out, _raw = _cli_supersede(capsys, ledger, rec)
    assert rc == 0 and out["registered"] is False, out


def test_cli_supersede_missing_old_key_rc2(tmp_path, capsys):
    ledger, _p, _rec = _stale_ledger(tmp_path)
    rc, out, _raw = _call(capsys, ["supersede", "core/pa/x.py", "--sha16", "0" * 16,
                                   "--decision", "D-2", "--owner", "PA",
                                   "--reason", "r", "--ledger", str(ledger)])
    assert rc == 2, out
    assert out["ok"] is False and out["error"], out


def test_cli_supersede_bad_reason_rc2(tmp_path, capsys):
    ledger, _p, rec = _stale_ledger(tmp_path)
    rc, out, _raw = _cli_supersede(capsys, ledger, rec, reason="")
    assert rc == 2, out
    assert out["ok"] is False, out


def test_cli_supersede_usage_missing_reason_rc3(tmp_path, capsys):
    ledger, _p, rec = _stale_ledger(tmp_path)
    rc, out, _raw = _call(capsys, ["supersede", rec["path"], "--sha16", rec["sha16"],
                                   "--decision", "D-2", "--owner", "PA",
                                   "--ledger", str(ledger)])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out

