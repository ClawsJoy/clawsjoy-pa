# -*- coding: utf-8 -*-
"""② 通道注入 + except 分类 + 类型阈值 回归（2026-09-13）。
② 注入守同一套三判据：验证约束生效 / 副作用零 / 命名空间隔离（test_*）。
"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway import capability_ledger as cl
from core.gateway import shared_state as ss
from core.gateway.v9_bridge.tool_runner import _run_exec_phase
from core.pa.artifact import TYPE_MIN_BYTES, verify_artifact

SID = "test_channel2"


def _run(items):
    executed = []

    def _exec(tool, args, user_id, session_id):
        executed.append((tool, args))
        return {"success": True}

    res, _c = _run_exec_phase(pre_items=items, session_id=SID, user_id="test_u", exec_tool_fn=_exec)
    return res, executed


@pytest.fixture(autouse=True)
def _clean():
    ss.set_continuation(SID, False)
    yield
    ss.set_continuation(SID, False)


# ---------- ② cu_learning.persist_sop ----------


def test_FAULT_channel2_blocked_and_not_executed():
    """① 先能失败：续跑期间 cu_learning.persist_sop 必须被拦，且**不得执行**。"""
    ss.set_continuation(SID, True)
    res, executed = _run(
        [{"bfn": "cu_learning", "bargs": {"action": "persist_sop", "key": "k"}, "gdeny": None, "idx": 0}]
    )
    got = res.get(0) or {}
    assert got.get("continuation_blocked") is True, got
    assert got.get("channel") == "cu_learning.persist_sop", got
    assert executed == [], executed


def test_FAULT_channel2_block_message_has_alternative():
    ss.set_continuation(SID, True)
    res, _e = _run([{"bfn": "cu_learning", "bargs": {"action": "persist_sop"}, "gdeny": None, "idx": 0}])
    assert "data/reports/" in str((res.get(0) or {}).get("error") or "")


def test_PASS_channel2_allowed_outside_continuation():
    """② 再能通过（防误伤）：非续跑轮放行。"""
    ss.set_continuation(SID, False)
    res, executed = _run([{"bfn": "cu_learning", "bargs": {"action": "persist_sop"}, "gdeny": None, "idx": 0}])
    assert not (res.get(0) or {}).get("continuation_blocked")
    assert executed


def test_PASS_cu_learning_read_not_blocked():
    """防误伤：cu_learning 的读类动作不受限。"""
    ss.set_continuation(SID, True)
    res, executed = _run([{"bfn": "cu_learning", "bargs": {"action": "list_sops"}, "gdeny": None, "idx": 0}])
    assert not (res.get(0) or {}).get("continuation_blocked")
    assert executed


# ---------- except 分类 ----------


def test_strict_capabilities_raise():
    """STRICT 能力：不可用必须中断（写盘/状态机类）。"""
    assert cl.is_strict("artifact_write") is True
    assert cl.is_strict("state_transition") is True
    with pytest.raises(RuntimeError):
        cl.on_capability_error("artifact_write", SID, RuntimeError("disk full"), emit=True)


def test_degradable_capabilities_do_not_raise():
    """DEGRADABLE 能力：不可用只降级 + 留痕（核验类）—— 不制造假失败。"""
    assert cl.is_strict("verification") is False
    payload = cl.on_capability_error("verification", SID, RuntimeError("chain broken"), emit=False)
    assert payload.get("result") == "SKIPPED"


def test_env_switch_forces_strict(monkeypatch):
    monkeypatch.setenv("V9_CAPABILITY_STRICT", "1")
    assert cl.is_strict("verification") is True


# ---------- 类型阈值（expected_min_bytes） ----------


def test_FAULT_per_type_thresholds(tmp_path):
    """按类型分别设阈：.md 短文件被拦；未注册/stub 行为明确。"""
    from pathlib import Path

    sb = tmp_path
    (sb / "short.md").write_text("短", encoding="utf-8")
    assert verify_artifact("short.md", base_dir=sb)["ok"] is False
    (sb / "ok.md").write_text("正" * 600, encoding="utf-8")  # ~1800 字节 > 1024
    assert verify_artifact("ok.md", base_dir=sb)["ok"] is True


def test_PASS_unregistered_type_is_not_applicable(tmp_path):
    """未注册扩展名 → 体积启发式不适用（applicable=False），不硬套阈值。"""
    (tmp_path / "x.xyz").write_text("a", encoding="utf-8")
    r = verify_artifact("x.xyz", base_dir=tmp_path)
    assert r["ok"] is True and r.get("applicable") is False, r


def test_stub_check_is_type_independent(tmp_path):
    """stub 精确匹配与类型无关（68 字节是已知假产物，不是启发式）。"""
    (tmp_path / "artifact_pa_task.txt").write_text("x" * 68, encoding="utf-8")
    r = verify_artifact("artifact_pa_task.txt", base_dir=tmp_path)
    assert r["ok"] is False and "占位" in r["reason"]


def test_expected_min_bytes_overrides_type(tmp_path):
    """任务级期望值优先于类型阈值。"""
    (tmp_path / "a.md").write_text("正" * 600, encoding="utf-8")  # ~1800 字节
    assert verify_artifact("a.md", base_dir=tmp_path)["ok"] is True
    r = verify_artifact("a.md", base_dir=tmp_path, expected_min_bytes=5000)
    assert r["ok"] is False and "过小" in r["reason"]


def test_type_registry_covers_measured_types():
    """注册表覆盖实测过的类型，且 json/py/log 明确免体积闸。"""
    assert TYPE_MIN_BYTES[".json"] == 2
    assert TYPE_MIN_BYTES[".py"] is None and TYPE_MIN_BYTES[".log"] is None
    assert TYPE_MIN_BYTES[".md"] == 1024
