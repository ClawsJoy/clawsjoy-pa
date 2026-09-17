# -*- coding: utf-8 -*-
"""expected_min_bytes 上游接线回归（2026-09-13）。"""
import sys

sys.path.insert(0, ".")
from core.pa.artifact import parse_expected_min_bytes, verify_artifact


def test_FAULT_only_explicit_specs_are_parsed():
    """① 先能失败：只认显式规格，不猜（猜出来的阈值会与类型注册表打架）。"""
    assert parse_expected_min_bytes("min_bytes=2048") == 2048
    assert parse_expected_min_bytes("产物不少于 2KB") == 2048
    assert parse_expected_min_bytes("至少 3000 字节") == 3000
    assert parse_expected_min_bytes("请写一份讲义") is None  # 无规格 → None
    assert parse_expected_min_bytes("") is None
    assert parse_expected_min_bytes(None) is None


def test_PASS_wired_spec_overrides_type_registry(tmp_path):
    """② 再能通过：任务级显式规格覆盖类型注册表。"""
    (tmp_path / "a.md").write_text("正" * 600, encoding="utf-8")  # ~1800 字节
    assert verify_artifact("a.md", base_dir=tmp_path)["ok"] is True  # .md→1024 放行
    r = verify_artifact("a.md", base_dir=tmp_path, expected_min_bytes=5000)
    assert r["ok"] is False and "过小" in r["reason"]


def test_no_spec_falls_back_to_type_registry(tmp_path):
    (tmp_path / "b.py").write_text("x=1", encoding="utf-8")
    r = verify_artifact("b.py", base_dir=tmp_path)  # .py → 免体积闸
    assert r["ok"] is True and r.get("applicable") is False


def test_guard_passes_expected_min_bytes_through():
    """接线断言：完成分支必须把解析出的期望值传给核验。"""
    src = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    assert "parse_expected_min_bytes" in src, "上游未接线"
    assert "expected_min_bytes=_exp_mb" in src, "未把期望值传下去"
