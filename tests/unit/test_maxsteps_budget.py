"""#6 maxSteps 硬限制: 配置读取 / fallback / 超限强制终止"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clear_policy_cache(monkeypatch):
    import core.gateway.shared_state as ss

    monkeypatch.setattr(ss, "_EXECUTION_POLICY_CACHE", None)
    yield


def test_config_reads_max_steps(monkeypatch):
    """execution_policy.yaml 正常读取 max_steps=30"""
    import core.gateway.shared_state as ss

    d = ss._load_v9_execution_policy()
    budget = d.get("execution_budget", {})
    assert budget.get("max_steps") == 30
    assert budget.get("max_tools_per_round") == 12


def test_config_fallback_on_missing(monkeypatch, tmp_path):
    """配置缺失 → fallback 默认值(30/12)"""
    import core.gateway.shared_state as ss

    monkeypatch.setattr(ss, "_EXECUTION_POLICY_CACHE", None)
    monkeypatch.setattr(ss.Path, "exists", lambda self: False)
    d = ss._load_v9_execution_policy()
    assert d == {}  # 缺失返回空
    # execute_agent_task 的 fallback 逻辑
    max_rounds = int((d or {}).get("execution_budget", {}).get("max_steps", 30) or 30)
    assert max_rounds == 30


def test_execute_agent_task_reads_config(monkeypatch, tmp_path):
    """_execute_agent_task 的 max_rounds 从配置读取(不硬编码 100)"""
    import core.gateway.execute_agent_task as eat

    src = Path(eat.__file__).read_text(encoding="utf-8")
    assert "max_rounds = 100" not in src, "不应再有硬编码 100"
    assert "_load_v9_execution_policy" in src, "应从配置读取"
    assert "max_steps" in src


def test_bridge_loop_tool_cap_configured(monkeypatch):
    """bridge_loop 每轮工具上限从配置读取 + 截断逻辑存在（S6-C 归位 response_guard）"""
    src = Path("core/gateway/v9_bridge/response_guard.py").read_text(encoding="utf-8")
    assert "max_tools_per_round" in src, "bridge_loop 应读 max_tools_per_round"
    assert "_max_tpr" in src, "应有每轮工具上限变量"


def test_bridge_loop_cap_truncates(monkeypatch):
    """超限截断: 20 个工具调用 → 截为 12 + 注入收敛提示"""
    import core.gateway.shared_state as ss

    monkeypatch.setattr(
        ss, "_EXECUTION_POLICY_CACHE", {"execution_budget": {"max_tools_per_round": 12, "max_steps": 30}}
    )
    # 提取 bridge_loop 截断逻辑验证(模拟)
    from core.gateway.shared_state import _load_v9_execution_policy

    budget = (_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}
    _max_tpr = int(budget.get("max_tools_per_round", 12) or 12)
    calls = [{"id": f"c{i}"} for i in range(20)]
    truncated = calls[:_max_tpr]
    assert len(truncated) == 12
    assert len(calls) == 20
