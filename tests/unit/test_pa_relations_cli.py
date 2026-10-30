# -*- coding: utf-8 -*-
u"""外联脚手架 CLI 之测（task-76）：四子命令 · 退出码 0/2/3/1 · stdin/文件/参数三入口。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_relations_cli.py -q
"""
import hashlib
import importlib.util
import io
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pa_relations.py"

_spec = importlib.util.spec_from_file_location("pa_relations_cli", str(SCRIPT))
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


def _call(capsys, argv):
    rc = cli.main(list(argv))
    raw = capsys.readouterr().out
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    assert len(lines) == 1, u"输出须为单行 JSON：%r" % raw
    return rc, json.loads(lines[0]), raw


def _ev_rec(**over):
    rec = {
        "path": "docs/reports/pa_iter40/10_r6_recheck.md",
        "bytes": 1234,
        "sha16": "0123456789abcdef",
        "captured_at": "2026-10-30T10:14:30+08:00",
        "rerun": "python -X utf8 -B -m pytest tests/unit/test_pa_relations.py -q（两次同）",
    }
    rec.update(over)
    return rec


def _dec_rec(**over):
    rec = {
        "id": "D-20261030-01",
        u"裁决": u"①六拍④：批外置（_trash+manifest+30天回滚），⛔ purge；真删候老板",
        "owner": u"老板/CEO",
        u"状态": "approved",
        u"证据": u"3480 / 裁件（sha16 0123456789abcdef）",
        u"重开条件": u"老板改裁 ∨ 真删/真证书出现",
    }
    rec.update(over)
    return rec


# ============================ evidence ============================

def test_evidence_ok(tmp_path, capsys):
    p = tmp_path / u"件.txt"
    p.write_bytes(u"hello".encode("utf-8"))
    rc, out, _raw = _call(capsys, ["evidence", str(p)])
    assert rc == 0, out
    assert set(out) == {"path", "bytes", "sha16", "captured_at"}, out
    assert out["path"] == str(p)
    assert out["bytes"] == 5
    assert out["sha16"] == hashlib.sha256(b"hello").hexdigest()[:16]
    assert datetime.fromisoformat(out["captured_at"]).tzinfo is not None


def test_evidence_missing_file_rc1(tmp_path, capsys):
    rc, out, raw = _call(capsys, ["evidence", str(tmp_path / "nope.bin")])
    assert rc == 1, out
    assert out["ok"] is False and out["error"]
    assert out["error_type"] in ("FileNotFoundError", "OSError"), out
    assert "Traceback" not in raw, u"⛔ traceback 外泄"


def test_evidence_directory_rc1(tmp_path, capsys):
    rc, out, _raw = _call(capsys, ["evidence", str(tmp_path)])
    assert rc == 1, out
    assert out["ok"] is False and out["error"]


def test_evidence_blank_path_rc1(capsys):
    rc, out, _raw = _call(capsys, ["evidence", ""])
    assert rc == 1, out
    assert out["ok"] is False and out["error_type"] == "ValueError", out


# ============================ validate-evidence ============================

def test_validate_evidence_ok_literal(capsys):
    rc, out, _raw = _call(capsys, ["validate-evidence", json.dumps(_ev_rec(), ensure_ascii=False)])
    assert rc == 0, out
    assert out == {"ok": True, "missing": [], "errors": []}, out


def test_validate_evidence_missing_field_rc2(capsys):
    rec = _ev_rec()
    rec.pop("rerun")
    rc, out, _raw = _call(capsys, ["validate-evidence", json.dumps(rec, ensure_ascii=False)])
    assert rc == 2, out
    assert out["ok"] is False and "rerun" in out["missing"], out


def test_validate_evidence_bad_sha16_rc2(capsys):
    rc, out, _raw = _call(capsys, ["validate-evidence",
                                   json.dumps(_ev_rec(sha16="A" * 16), ensure_ascii=False)])
    assert rc == 2, out
    assert out["ok"] is False and out["errors"], out


def test_validate_evidence_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_ev_rec(), ensure_ascii=False)))
    rc, out, _raw = _call(capsys, ["validate-evidence", "-"])
    assert rc == 0, out
    assert out["ok"] is True


def test_validate_evidence_from_file(tmp_path, capsys):
    p = tmp_path / "ev.json"
    p.write_text(json.dumps(_ev_rec(), ensure_ascii=False), encoding="utf-8")
    rc, out, _raw = _call(capsys, ["validate-evidence", str(p)])
    assert rc == 0, out
    assert out["ok"] is True


def test_validate_evidence_bad_json_rc3(capsys):
    rc, out, _raw = _call(capsys, ["validate-evidence", "{not-json"])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


def test_validate_evidence_non_dict_rc2(capsys):
    rc, out, _raw = _call(capsys, ["validate-evidence", "[]"])
    assert rc == 2, out
    assert out["ok"] is False and out["errors"], out


# ============================ validate-decision ============================

def test_validate_decision_ok_literal(capsys):
    rc, out, _raw = _call(capsys, ["validate-decision", json.dumps(_dec_rec(), ensure_ascii=False)])
    assert rc == 0, out
    assert out == {"ok": True, "missing": [], "errors": []}, out


def test_validate_decision_bad_id_rc2(capsys):
    rc, out, _raw = _call(capsys, ["validate-decision",
                                   json.dumps(_dec_rec(id="D-2026-10-30-01"), ensure_ascii=False)])
    assert rc == 2, out
    assert out["ok"] is False and out["errors"], out


def test_validate_decision_missing_owner_stdin(monkeypatch, capsys):
    rec = _dec_rec()
    rec.pop("owner")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(rec, ensure_ascii=False)))
    rc, out, _raw = _call(capsys, ["validate-decision", "-"])
    assert rc == 2, out
    assert "owner" in out["missing"], out


# ============================ wip ============================

def test_wip_ok_rc0(capsys):
    tasks = [{"owner": "a", "status": "in_progress"},
             {"owner": "b", "status": "in_progress"}]
    rc, out, _raw = _call(capsys, ["wip", json.dumps(tasks, ensure_ascii=False)])
    assert rc == 0, out
    assert out == {"ok": True}, out


def test_wip_duplicate_owner_rc2(capsys):
    tasks = [{"owner": "a", "status": "in_progress"},
             {"owner": "a", "status": "in_progress"}]
    rc, out, _raw = _call(capsys, ["wip", json.dumps(tasks, ensure_ascii=False)])
    assert rc == 2, out
    assert out == {"ok": False}, out


def test_wip_non_list_rc2(capsys):
    rc, out, _raw = _call(capsys, ["wip", "{}"])
    assert rc == 2, out
    assert out["ok"] is False and out["error_type"] == "ValueError", out


def test_wip_bad_json_rc3(capsys):
    rc, out, _raw = _call(capsys, ["wip", "not-json"])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


# ============================ usage / 出口 ============================

def test_no_subcommand_rc3(capsys):
    rc, out, _raw = _call(capsys, [])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


def test_unknown_subcommand_rc3(capsys):
    rc, out, _raw = _call(capsys, ["bogus"])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


def test_missing_argument_rc3(capsys):
    rc, out, _raw = _call(capsys, ["evidence"])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


def test_evidence_then_validate_roundtrip(tmp_path, capsys):
    p = tmp_path / "裁件.md"
    p.write_text(u"# 裁决\n", encoding="utf-8")
    rc, ev, _raw = _call(capsys, ["evidence", str(p)])
    assert rc == 0, ev
    ev["rerun"] = "pytest tests/unit/test_pa_relations_cli.py -q（两次同）"
    ev_path = tmp_path / "ev.json"
    ev_path.write_text(json.dumps(ev, ensure_ascii=False), encoding="utf-8")
    rc2, out, _raw2 = _call(capsys, ["validate-evidence", str(ev_path)])
    assert rc2 == 0, out
    assert out["ok"] is True


# ============================ freshness（T81 · C15） ============================

FRESH_NOW = "2026-10-31T12:00:00+08:00"


def _fresh_rec(days=0.0, **over):
    captured = datetime.fromisoformat(FRESH_NOW) - timedelta(days=days)
    rec = {"captured_at": captured.isoformat(timespec="seconds"), "owner": u"PM"}
    rec.update(over)
    return rec


def _fresh(capsys, days=0.0, *extra):
    rec = _fresh_rec(days)
    return _call(capsys, ["freshness", json.dumps(rec, ensure_ascii=False), "--now", FRESH_NOW] + list(extra))


def test_freshness_ok_rc0(capsys):
    rc, out, _raw = _fresh(capsys, 1)
    assert rc == 0, out
    assert set(out) == {"ok", "age_days", "expires_at", "errors"}, out
    assert out["ok"] is True and out["errors"] == []
    assert out["age_days"] == 1.0, out
    captured = datetime.fromisoformat(FRESH_NOW) - timedelta(days=1)
    assert out["expires_at"] == (captured + timedelta(days=30)).isoformat(), out


def test_freshness_boundary_29_30_31(capsys):
    u"""29 日 / 恰 30 日 ⇒ 0；31 日 ⇒ 2（边界同 T78 之钉）。"""
    expect = ((29, 0), (30, 0), (31, 2))
    for days, want_rc in expect:
        rc, out, _raw = _fresh(capsys, days)
        assert rc == want_rc, (days, out)
        assert out["age_days"] == float(days), (days, out)
        if days == 31:
            assert out["ok"] is False and any(u"超期" in e for e in out["errors"]), out


def test_freshness_future_rc2(capsys):
    rec = _fresh_rec(-1)
    rc, out, _raw = _call(capsys, ["freshness", json.dumps(rec, ensure_ascii=False),
                                   "--now", FRESH_NOW])
    assert rc == 2, out
    assert out["ok"] is False and out["age_days"] == -1.0, out
    assert any(u"未来" in e for e in out["errors"]), out


def test_freshness_bad_date_rc2(capsys):
    rec = {"captured_at": "not-a-date", "owner": "PM"}
    rc, out, _raw = _call(capsys, ["freshness", json.dumps(rec, ensure_ascii=False)])
    assert rc == 2, out
    assert out["ok"] is False and out["age_days"] is None and out["errors"], out


def test_freshness_ttl_override(capsys):
    rc, out, _raw = _fresh(capsys, 10)
    assert rc == 0, out
    rc2, out2, _raw2 = _fresh(capsys, 10, "--ttl-days", "7")
    assert rc2 == 2, out2
    assert any(u"超期" in e for e in out2["errors"]), out2
    rc3, out3, _raw3 = _fresh(capsys, 10, "--ttl-days", "0")
    assert rc3 == 2, out3
    assert any("ttl_days" in e for e in out3["errors"]), out3


def test_freshness_ttl_bad_number_rc3(capsys):
    rc, out, _raw = _fresh(capsys, 1, "--ttl-days", "abc")
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


def test_freshness_from_stdin(monkeypatch, capsys):
    rec = _fresh_rec(1)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(rec, ensure_ascii=False)))
    rc, out, _raw = _call(capsys, ["freshness", "-", "--now", FRESH_NOW])
    assert rc == 0, out
    assert out["ok"] is True and out["age_days"] == 1.0, out


def test_freshness_from_file(tmp_path, capsys):
    p = tmp_path / "fresh.json"
    p.write_text(json.dumps(_fresh_rec(1), ensure_ascii=False), encoding="utf-8")
    rc, out, _raw = _call(capsys, ["freshness", str(p), "--now", FRESH_NOW])
    assert rc == 0, out
    assert out["ok"] is True


def test_freshness_bad_json_rc3(capsys):
    rc, out, _raw = _call(capsys, ["freshness", "{not-json"])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


def test_freshness_owner_blank_rc2(capsys):
    rec = _fresh_rec(1, owner="")
    rc, out, _raw = _call(capsys, ["freshness", json.dumps(rec, ensure_ascii=False),
                                   "--now", FRESH_NOW])
    assert rc == 2, out
    assert any("owner" in e for e in out["errors"]), out


def test_freshness_missing_argument_rc3(capsys):
    rc, out, _raw = _call(capsys, ["freshness"])
    assert rc == 3, out
    assert out["ok"] is False and out["error_type"] == "usage", out


def test_freshness_default_now_rc0(capsys):
    recent = (datetime.now().astimezone() - timedelta(hours=1)).isoformat(timespec="seconds")
    rec = {"captured_at": recent, "owner": "PM"}
    rc, out, _raw = _call(capsys, ["freshness", json.dumps(rec, ensure_ascii=False)])
    assert rc == 0, out
    assert 0.0 < out["age_days"] < 1.0, out
