# -*- coding: utf-8 -*-
"""⭐ enabled 之轻形（承 pm_1380 §一 ／ pm_1382 §三.1）：自 env 派生 ＋ 屏上附源。

⛔ 硬编 True（旧病：写了不生效 ∧ 一名蔽二态）—— 承 pm_1377 §三。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_providers_enabled.py -q
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import providers as P  # noqa: E402


def _view(monkeypatch, csv):
    if csv is None:
        monkeypatch.delenv(P.ENABLED_ENV, raising=False)
    else:
        monkeypatch.setenv(P.ENABLED_ENV, csv)
    return {i["id"]: i for i in P.public_view()["providers"]}


def test_default_all_enabled_with_source(monkeypatch):
    v = _view(monkeypatch, None)
    assert v, "无 provider"
    for it in v.values():
        assert it["enabled"] is True, it["id"]
        assert P.ENABLED_ENV in it["enabled_src"], it["enabled_src"]


def test_disabled_from_env(monkeypatch):
    pid = sorted(P.PROVIDERS)[0]
    v = _view(monkeypatch, pid)
    assert v[pid]["enabled"] is False
    assert "停用" in v[pid]["enabled_src"]
    for k, it in v.items():
        if k != pid:
            assert it["enabled"] is True, k


def test_csv_with_spaces_and_multiple(monkeypatch):
    pids = sorted(P.PROVIDERS)
    v = _view(monkeypatch, " " + pids[0] + " , " + pids[-1] + " ")
    assert v[pids[0]]["enabled"] is False
    assert v[pids[-1]]["enabled"] is False


def test_enabled_is_derived_not_hardcoded(monkeypatch):
    """⭐ 反控：注册表字面恒定 ⇒ 唯 env 可改（承 pm_1380 · 除「能改而不见效」之病）。"""
    pid = sorted(P.PROVIDERS)[0]
    a = _view(monkeypatch, None)
    b = _view(monkeypatch, pid)
    assert a[pid]["enabled"] != b[pid]["enabled"]
