"""#21 总工具数硬上限: 配置读取 / fallback / 超限强制终止(max_total_tools=32)"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest


@pytest.fixture(autouse=True)
def _clear_policy(monkeypatch):
    import core.gateway.shared_state as ss

    monkeypatch.setattr(ss, "_EXECUTION_POLICY_CACHE", None)
    yield


def test_config_reads_max_total_tools():
    """execution_policy.yaml 读取 max_total_tools=48(R1 2026-08-30 调宽 32→48: 仅防失控第二道闸)"""
    import core.gateway.shared_state as ss

    budget = (ss._load_v9_execution_policy() or {}).get("execution_budget", {}) or {}
    assert budget.get("max_total_tools") == 48


def test_fallback_default_32(monkeypatch):
    """配置缺失 → fallback 32"""
    import core.gateway.shared_state as ss

    monkeypatch.setattr(ss, "_EXECUTION_POLICY_CACHE", {})
    d = ss._load_v9_execution_policy() or {}
    _max_total = int((d.get("execution_budget", {}) or {}).get("max_total_tools", 32) or 32)
    assert _max_total == 32


def test_bridge_loop_reads_config():
    """bridge_loop 源码读 max_total_tools + 超限检查"""
    from pathlib import Path

    import agent_gateway_enhanced as main

    src = Path(main.__file__).read_text(encoding="utf-8") + Path("core/gateway/v9_chat/entry.py").read_text(
        encoding="utf-8"
    )  # P3-B: 编排已下沉
    assert "max_total_tools" in src
    assert "_max_total_tools" in src
    assert "工具调用总数已达上限" in src, "应有超限收敛提示"
    assert "强制结束循环" in src or "break" in src


def test_progress_total_is_max_total_tools(monkeypatch):
    """_ts_progress total = max_total_tools(32 而非硬编码 8)"""
    from pathlib import Path

    import agent_gateway_enhanced as main

    src = Path(main.__file__).read_text(encoding="utf-8") + Path("core/gateway/v9_chat/entry.py").read_text(
        encoding="utf-8"
    )  # P3-B: 编排已下沉
    assert (
        '"total": _max_total_tools' in src or '"total": _v9_max_total_tools' in src
    ), "progress total 应为 max_total_tools"
    assert '"total": 8' not in src, "不应再硬编码 total 8"


def test_progress_total_steps_unified_32(monkeypatch):
    """P1-1: total_steps 全部统一为 max_total_tools(32), 无硬编码 8"""
    from pathlib import Path

    import agent_gateway_enhanced as main

    src = Path(main.__file__).read_text(encoding="utf-8") + Path("core/gateway/v9_chat/entry.py").read_text(
        encoding="utf-8"
    )  # P3-B: 编排已下沉
    assert '"total_steps": _max_total_tools' in src, "bridge_loop 内部 total_steps 应为 _max_total_tools"
    assert '"total_steps": _v9_max_total_tools' in src, "stream wrapper total_steps 应为 _v9_max_total_tools"
    assert '"total_steps": 8' not in src, "不应再硬编码 total_steps 8"
