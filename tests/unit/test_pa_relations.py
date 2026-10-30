# -*- coding: utf-8 -*-
u"""PA 外联脚手架 v1 校验器之测（task-74）：make_evidence ／ validate_evidence ／
validate_decision ／ check_wip —— 正例 ＋ 反例（⛔ 只判形 · ⛔ 静默放行）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_relations.py -q
"""
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import relations as R  # noqa: E402


def _evidence(**over):
    rec = {
        "path": "docs/reports/pa_iter40/10_r6_recheck.md",
        "bytes": 1234,
        "sha16": "0123456789abcdef",
        "captured_at": "2026-10-30T10:14:30+08:00",
        "rerun": "python -X utf8 -B -m pytest tests/unit/test_pa_relations.py -q（两次同）",
    }
    rec.update(over)
    return rec


def _decision(**over):
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


# ============================ make_evidence ============================

def test_make_evidence_positive(tmp_path):
    p = tmp_path / u"件.txt"
    p.write_bytes(u"hello 世界".encode("utf-8"))
    rec = R.make_evidence(p)
    assert set(rec) == {"path", "bytes", "sha16", "captured_at"}, rec
    assert rec["path"] == str(p)
    assert rec["bytes"] == len(p.read_bytes())
    assert rec["sha16"] == hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    at = datetime.fromisoformat(rec["captured_at"])
    assert at.tzinfo is not None, u"取刻须带时区（⛔ UTC 冒充 ／ ⛔ 无时区）"
    full = dict(rec, rerun="pytest tests/unit/test_pa_relations.py -q（两次同）")
    assert R.validate_evidence(full) == {"ok": True, "missing": [], "errors": []}


def test_make_evidence_empty_file(tmp_path):
    p = tmp_path / "empty.bin"
    p.write_bytes(b"")
    rec = R.make_evidence(p)
    assert rec["bytes"] == 0
    assert rec["sha16"] == hashlib.sha256(b"").hexdigest()[:16]


def test_make_evidence_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        R.make_evidence(tmp_path / "nope.bin")


def test_make_evidence_directory_raises(tmp_path):
    with pytest.raises((IsADirectoryError, OSError)):
        R.make_evidence(tmp_path)


def test_make_evidence_blank_path_raises():
    for bad in (None, "", "   "):
        with pytest.raises(ValueError):
            R.make_evidence(bad)


def test_make_evidence_only_reads_and_is_deterministic(tmp_path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"same")
    before = (p.read_bytes(), p.stat().st_mtime_ns, sorted(q.name for q in tmp_path.iterdir()))
    r1 = R.make_evidence(p)
    r2 = R.make_evidence(p)
    assert r1["sha16"] == r2["sha16"] and r1["bytes"] == r2["bytes"]
    after = (p.read_bytes(), p.stat().st_mtime_ns, sorted(q.name for q in tmp_path.iterdir()))
    assert before == after, u"取件录 ⛔ 写盘 ／ ⛔ 改件"


def test_make_evidence_detects_content_change(tmp_path):
    p = tmp_path / "y.txt"
    p.write_bytes(b"one")
    h1 = R.make_evidence(p)["sha16"]
    p.write_bytes(b"two")
    h2 = R.make_evidence(p)["sha16"]
    assert h1 != h2, u"内容变 ⇒ 印必变（⛔ 以旧证充今证）"


# ============================ validate_evidence ============================

def test_validate_evidence_requires_all_five_fields():
    full = _evidence()
    assert R.validate_evidence(full)["ok"] is True
    for key in R.EVIDENCE_FIELDS:
        rec = dict(full)
        rec.pop(key)
        got = R.validate_evidence(rec)
        assert got["ok"] is False, key
        assert key in got["missing"], (key, got)


def test_validate_evidence_sha16_shape():
    assert R.validate_evidence(_evidence(sha16="0" * 16))["ok"] is True
    for bad in ("0" * 15, "0" * 17, "A" * 16, "g" * 16, "0123456789abcde", 123):
        got = R.validate_evidence(_evidence(sha16=bad))
        assert got["ok"] is False, bad
        assert got["errors"], bad


def test_validate_evidence_bytes_rules():
    assert R.validate_evidence(_evidence(bytes=0))["ok"] is True
    for bad in (-1, True, "3", 1.5, None):
        got = R.validate_evidence(_evidence(bytes=bad))
        assert got["ok"] is False, bad
        assert got["errors"] or "bytes" in got["missing"], bad


def test_validate_evidence_captured_at_iso():
    got = R.validate_evidence(_evidence(captured_at="2026-10-30"))
    assert got["ok"] is True, got
    for bad in ("not-a-date", "2026-13-40T00:00:00+08:00", "", "   "):
        got = R.validate_evidence(_evidence(captured_at=bad))
        assert got["ok"] is False, bad
        assert got["errors"], bad


def test_validate_evidence_rerun_required_and_nonempty():
    rec = _evidence()
    rec.pop("rerun")
    assert "rerun" in R.validate_evidence(rec)["missing"]
    for bad in ("", "   ", None):
        got = R.validate_evidence(_evidence(rerun=bad))
        assert got["ok"] is False, bad


def test_validate_evidence_path_type_and_extra_keys():
    assert R.validate_evidence(_evidence(path=123))["ok"] is False
    extra = _evidence(ledger="T-70", decision="D-20261030-01", mtime="2026-10-30")
    assert R.validate_evidence(extra)["ok"] is True, u"额外键（账/裁/刻）⛔ 拒"


def test_validate_evidence_non_dict_is_explicit():
    for bad in (None, [], "x", 3):
        got = R.validate_evidence(bad)
        assert got["ok"] is False and got["errors"], bad


# ============================ validate_decision ============================

def test_validate_decision_positive():
    assert R.validate_decision(_decision()) == {"ok": True, "missing": [], "errors": []}


def test_validate_decision_requires_six_fields():
    full = _decision()
    for key in R.DECISION_FIELDS:
        rec = dict(full)
        rec.pop(key)
        got = R.validate_decision(rec)
        assert got["ok"] is False, key
        assert key in got["missing"], (key, got)


def test_validate_decision_id_shape_and_date():
    for good in ("D-20261030-01", "D-20260101-99"):
        assert R.validate_decision(_decision(id=good))["ok"] is True, good
    for bad in ("D-2026-10-30-01", "D-2026103-01", "X-20261030-01", "D-20261301-01", "D-20261030-1", 123):
        got = R.validate_decision(_decision(id=bad))
        assert got["ok"] is False, bad
        assert got["errors"], bad


def test_validate_decision_states_enum():
    for st in R.DECISION_STATES:
        assert R.validate_decision(_decision(**{u"状态": st}))["ok"] is True, st
    for bad in ("unknown", "", "DONE", "进行中", None):
        got = R.validate_decision(_decision(**{u"状态": bad}))
        assert got["ok"] is False, bad


def test_validate_decision_evidence_forms():
    for good in (u"3480 / 裁件", {u"path": "a", "sha16": "0" * 16}, [u"证据一"]):
        assert R.validate_decision(_decision(**{u"证据": good}))["ok"] is True, good
    for bad in ("", "   ", [], {}):
        got = R.validate_decision(_decision(**{u"证据": bad}))
        assert got["ok"] is False, bad
        assert got["errors"], bad


def test_validate_decision_blank_text_fields():
    for field in (u"裁决", "owner", u"重开条件"):
        for bad in ("", "   "):
            got = R.validate_decision(_decision(**{field: bad}))
            assert got["ok"] is False, (field, bad)
            assert got["errors"], (field, bad)


def test_validate_decision_optional_and_unknown_keys_allowed():
    rec = _decision()
    rec.update({u"日期": u"2026-10-30", u"范围": u"迭代40", "note": "留痕"})
    assert R.validate_decision(rec)["ok"] is True


def test_validate_decision_non_dict_is_explicit():
    for bad in (None, [], "D-20261030-01", 1):
        got = R.validate_decision(bad)
        assert got["ok"] is False and got["errors"], bad


# ============================ 件—裁 roundtrip ============================

def test_evidence_roundtrip_feeds_decision(tmp_path):
    p = tmp_path / "裁件.md"
    p.write_text(u"# 裁决\n", encoding="utf-8")
    ev = R.make_evidence(p)
    ev["rerun"] = u"pytest tests/unit/test_pa_relations.py -q（两次同）"
    assert R.validate_evidence(ev)["ok"] is True
    d = _decision(**{u"证据": ev})
    assert R.validate_decision(d)["ok"] is True, d


# ============================ check_wip ============================

def test_check_wip_distinct_owners_ok():
    assert R.check_wip([
        {"owner": "a", "status": "in_progress"},
        {"owner": "b", "status": "in_progress"},
        {"owner": "a", "status": "completed"},
        {"owner": "c", "status": "pending"},
    ]) is True


def test_check_wip_same_owner_twice_false():
    assert R.check_wip([
        {"owner": "a", "status": "in_progress"},
        {"owner": "a", "status": "in_progress"},
    ]) is False


def test_check_wip_empty_and_completed_duplicates_ok():
    assert R.check_wip([]) is True
    assert R.check_wip([
        {"owner": "a", "status": "completed"},
        {"owner": "a", "status": "completed"},
        {"owner": "a", "status": "pending"},
    ]) is True


def test_check_wip_status_normalization():
    assert R.check_wip([
        {"owner": "a", "status": " In_Progress "},
        {"owner": "a", "status": "in_progress"},
    ]) is False
    assert R.check_wip([
        {"owner": " a ", "status": "in_progress"},
        {"owner": "a", "status": "in_progress"},
    ]) is False


def test_check_wip_malformed_entries_fail_closed():
    for tasks in ([{}], [{"owner": "a"}], ["x"], [{"owner": "a", "status": "in_progress"}, {}]):
        assert R.check_wip(tasks) is False, tasks


def test_check_wip_tasks_must_be_list():
    for bad in (None, {}, "x", 3):
        with pytest.raises(ValueError):
            R.check_wip(bad)


# ============================ validate_evidence · require_owner（T89） ============================

def test_validate_evidence_owner_optional_by_default():
    u"""缺省 require_owner=False ⇒ 旧行为（T74 之录无 owner 亦合）。"""
    rec = _evidence()
    assert "owner" not in rec
    assert R.validate_evidence(rec)["ok"] is True


def test_validate_evidence_require_owner_missing_is_missing():
    got = R.validate_evidence(_evidence(), require_owner=True)
    assert got["ok"] is False
    assert "owner" in got["missing"], got
    assert got["errors"] == [], got


@pytest.mark.parametrize("bad", ["", "   ", 123, None])
def test_validate_evidence_require_owner_blank_or_nonstr(bad):
    rec = _evidence(owner=bad)
    got = R.validate_evidence(rec, require_owner=True)
    assert got["ok"] is False, bad
    if bad is None:
        assert "owner" in got["missing"], got
    else:
        assert any("owner" in e for e in got["errors"]), (bad, got)


def test_validate_evidence_require_owner_valid_and_no_mutation():
    rec = _evidence(owner=u"PD")
    before = dict(rec)
    got = R.validate_evidence(rec, require_owner=True)
    assert got == {"ok": True, "missing": [], "errors": []}, got
    assert rec == before, u"校验器 ⛔ 改入参"
