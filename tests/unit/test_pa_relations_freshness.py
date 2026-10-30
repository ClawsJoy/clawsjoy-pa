# -*- coding: utf-8 -*-
u"""C15 证据保鲜之测（task-78）：`check_freshness` —— TTL 30 天 ＋ owner（域主席）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_relations_freshness.py -q

判据（边界明示）：
  · 恰 30 日整 ⇒ ok=True（**未超**）；30 日 ＋ 1 微秒 ⇒ False；29 ／ 30 ／ 31 日逐一钉。
  · 未来 captured_at ⇒ False；坏日期 ／ 缺字段 ／ 非对象 ⇒ False（⛔ 静默）。
  · owner 可选：缺 ⇒ 合；有而空 ／ 非串 ⇒ False。
  · ttl_days 可覆（>0）；0 ／ 负 ／ 非数 ／ bool ⇒ False。
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import relations as R  # noqa: E402

BASE = datetime.fromisoformat("2026-10-01T12:00:00+08:00")

KEYS = {"ok", "age_days", "expires_at", "errors"}


def _rec(**over):
    rec = {"captured_at": "2026-10-01T12:00:00+08:00", "owner": u"PM"}
    rec.update(over)
    return rec


def _check(days=0.0, rec=None, **kw):
    now = BASE + timedelta(days=days)
    return R.check_freshness(rec if rec is not None else _rec(), now=now, **kw)


# ============================ 正例 / 边界 ============================

def test_fresh_zero_day_ok():
    got = _check(0)
    assert set(got) == KEYS, got
    assert got["ok"] is True and got["errors"] == []
    assert got["age_days"] == 0.0
    assert got["expires_at"] == "2026-10-31T12:00:00+08:00", got


def test_boundary_29_days_ok():
    got = _check(29)
    assert got["ok"] is True, got
    assert got["age_days"] == 29.0


def test_boundary_30_days_exactly_ok():
    u"""TTL=30 ⇒ **恰 30 日整未超** ⇒ ok=True（边界一处定形 · ⛔ 「30 日即过期」之混）。"""
    got = _check(30)
    assert got["ok"] is True, got
    assert got["age_days"] == 30.0
    assert got["expires_at"] == "2026-10-31T12:00:00+08:00"


def test_boundary_30_days_plus_one_microsecond_false():
    now = BASE + timedelta(days=30) + timedelta(microseconds=1)
    got = R.check_freshness(_rec(), now=now)
    assert got["ok"] is False, got
    assert u"超期" in got["errors"][0], got


def test_boundary_31_days_false():
    got = _check(31)
    assert got["ok"] is False, got
    assert got["age_days"] == 31.0
    assert u"超期" in got["errors"][0], got


def test_now_as_iso_string_ok():
    got = R.check_freshness(_rec(), now="2026-10-31T12:00:00+08:00")
    assert got["ok"] is True and got["age_days"] == 30.0, got


def test_utc_z_and_offset_math():
    rec = {"captured_at": "2026-10-01T04:00:00Z", "owner": "PM"}
    got = R.check_freshness(rec, now="2026-10-31T04:00:00+00:00")
    assert got["ok"] is True, got
    assert got["expires_at"] == "2026-10-31T04:00:00+00:00", got


def test_naive_times_are_local_not_utc():
    u"""naive ISO ⇒ 按本机时区解（两者皆 naive ⇒ 差 1 日；⛔ 猜 UTC 致差 8h）。"""
    rec = {"captured_at": "2026-10-01T12:00:00"}
    now = datetime(2026, 10, 2, 12, 0, 0)
    got = R.check_freshness(rec, now=now)
    assert got["ok"] is True, got
    assert got["age_days"] == 1.0, got


def test_default_now_uses_current_clock():
    recent = datetime.now().astimezone() - timedelta(hours=1)
    rec = {"captured_at": recent.isoformat()}
    got = R.check_freshness(rec)
    assert got["ok"] is True, got
    assert 0.0 < got["age_days"] < 1.0, got


# ============================ 反例：时间 ============================

def test_future_captured_at_false():
    rec = _rec(captured_at=(BASE + timedelta(days=1)).isoformat())
    got = R.check_freshness(rec, now=BASE)
    assert got["ok"] is False, got
    assert got["age_days"] == -1.0
    assert u"未来" in got["errors"][0], got


def test_missing_captured_at_false():
    rec = {"owner": "PM"}
    got = R.check_freshness(rec, now=BASE)
    assert got["ok"] is False
    assert got["age_days"] is None and got["expires_at"] == ""
    assert u"必填" in got["errors"][0], got


def test_bad_captured_at_false():
    for bad in ("not-a-date", "2026-13-40T00:00:00+08:00", 12345, None):
        got = R.check_freshness(_rec(captured_at=bad), now=BASE)
        assert got["ok"] is False, bad
        assert got["errors"], bad


def test_bad_now_false():
    got = R.check_freshness(_rec(), now="not-a-date")
    assert got["ok"] is False and got["errors"], got
    assert u"now" in got["errors"][0], got


def test_non_dict_rec_false():
    for bad in (None, [], "x", 3):
        got = R.check_freshness(bad, now=BASE)
        assert got["ok"] is False and got["errors"], bad


# ============================ owner（可选 · 域主席） ============================

def test_owner_optional_absent_ok():
    rec = {"captured_at": "2026-10-01T12:00:00+08:00"}
    got = R.check_freshness(rec, now=BASE)
    assert got["ok"] is True, got


def test_owner_present_must_be_nonempty():
    for bad in ("", "   ", 123, None):
        got = R.check_freshness(_rec(owner=bad), now=BASE)
        assert got["ok"] is False, bad
        assert any("owner" in e for e in got["errors"]), (bad, got)


# ============================ ttl_days 可覆 ============================

def test_ttl_override_positive():
    assert _check(0.5, ttl_days=1)["ok"] is True
    assert _check(2, ttl_days=1)["ok"] is False
    got = _check(0, ttl_days=7)
    assert got["expires_at"] == "2026-10-08T12:00:00+08:00", got


def test_ttl_override_fractional_boundary():
    assert _check(0.5, ttl_days=0.5)["ok"] is True
    assert _check(0.55, ttl_days=0.5)["ok"] is False


def test_ttl_invalid_false():
    for bad in (0, -1, 0.0, "30", True, None):
        got = _check(0, ttl_days=bad)
        assert got["ok"] is False, bad
        assert got["age_days"] is None and got["expires_at"] == "", bad
        assert any("ttl_days" in e for e in got["errors"]), (bad, got)


def test_check_freshness_does_not_mutate_rec():
    rec = _rec()
    before = dict(rec)
    R.check_freshness(rec, now=BASE)
    assert rec == before, u"校验器 ⛔ 改入参"
