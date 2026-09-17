"""P1 S2: 无状态守卫收编测试 — 与原内联逻辑行为一致"""
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest
from core.os.context import V9Context
from core.gateway.guards import (
    QuotaGuard, ModeGuard, ForcedToolGuard, ForbiddenGuard,
)


@pytest.fixture(autouse=True)
def _fresh_ctx():
    return V9Context()


def _run(ctx, guard, payload):
    """挂载单守卫并 waterfall, 返回拒绝结果或 None"""
    g = guard()
    ctx.mount(g)
    return ctx.waterfall("tools/pre-execute", payload)


# ===== G9 配额 =====

def test_quota_guard_passes_when_allowed(monkeypatch, _fresh_ctx):
    """配额充足 → 放行"""
    import core.gateway.quota_manager as qm
    monkeypatch.setattr(qm, "check_tool_quota", lambda t, s: (True, 10, ""))
    monkeypatch.setattr(qm, "_quota_table", {"s1": {}})
    monkeypatch.setattr(qm, "init_quota", lambda s: None)
    r = _run(_fresh_ctx, QuotaGuard, {"tool": "read_file", "session_id": "s1"})
    assert r is None


def test_quota_guard_denies_when_exhausted(monkeypatch, _fresh_ctx):
    """配额超限 → 拒绝 quota_exhausted(与原逻辑同 error 结构)"""
    import core.gateway.quota_manager as qm
    monkeypatch.setattr(qm, "check_tool_quota", lambda t, s: (False, 0, "配额不足"))
    monkeypatch.setattr(qm, "_quota_table", {"s1": {}})
    monkeypatch.setattr(qm, "init_quota", lambda s: None)
    r = _run(_fresh_ctx, QuotaGuard, {"tool": "read_file", "session_id": "s1"})
    assert r is not None and r["status"] == "quota_exhausted"
    assert r["error"]["error"] == "配额不足" and r["error"]["quota_exhausted"] is True


# ===== G10 模式 =====

def test_mode_guard_allows_non_list_tools(_fresh_ctx):
    """非 list/search/query 工具不受模式限制"""
    r = _run(_fresh_ctx, ModeGuard, {"tool": "read_file", "session_id": "s", "messages": []})
    assert r is None


def test_mode_guard_denies_minimal_mode(monkeypatch, _fresh_ctx):
    """minimal 模式禁用 list_dir(与原逻辑同 hint 结构)"""
    import core.gateway.quota_manager as qm
    monkeypatch.setattr(qm, "get_mode", lambda s, h: "minimal")
    monkeypatch.setattr(qm, "get_mode_tools", lambda s, h: ["read_file", "write_file"])
    r = _run(_fresh_ctx, ModeGuard, {
        "tool": "list_dir", "session_id": "s",
        "messages": [{"role": "user", "content": "改代码"}],
    })
    assert r is not None and r["status"] == "mode_limited"
    assert "不支持" in r["error"]["error"]
    assert r["error"]["mode"] == "minimal"


def test_mode_guard_allows_full_mode(monkeypatch, _fresh_ctx):
    """full 模式放行 list_dir"""
    import core.gateway.quota_manager as qm
    monkeypatch.setattr(qm, "get_mode", lambda s, h: "full")
    monkeypatch.setattr(qm, "get_mode_tools", lambda s, h: ["read_file", "write_file", "list_dir"])
    r = _run(_fresh_ctx, ModeGuard, {
        "tool": "list_dir", "session_id": "s", "messages": [],
    })
    assert r is None


# ===== G11 强制工具校验 =====

def test_forced_tool_guard_allows_read_without_modify(_fresh_ctx):
    """用户消息无修改词 → 读工具放行"""
    r = _run(_fresh_ctx, ForcedToolGuard, {
        "tool": "read_file",
        "messages": [{"role": "user", "content": "查询信息"}],
    })
    assert r is None


def test_forced_tool_guard_denies_read_on_modify(_fresh_ctx):
    """2026-08-30 根本修复: 读工具永不禁用 — 修改任务也允许读(Agent 读文件是必要前置,
    写保护由 write_file 审批/execute_command 写审批承担, 禁读只会迫使 awk/cat 绕行)"""
    r = _run(_fresh_ctx, ForcedToolGuard, {
        "tool": "read_file",
        "messages": [{"role": "user", "content": "请修改 main.py"}],
    })
    assert r is None, "读工具应永远放行: " + str(r)


def test_forced_tool_guard_allows_write_on_modify(_fresh_ctx):
    """用户要求修改 + 调写工具 → 放行"""
    r = _run(_fresh_ctx, ForcedToolGuard, {
        "tool": "write_file",
        "messages": [{"role": "user", "content": "请修改 main.py"}],
    })
    assert r is None


# ===== G12+G13 禁则 =====

def test_forbidden_exec_tmp_script(_fresh_ctx):
    """§4.1: execute_command 含 _tmp_ → 拒绝 forbidden"""
    r = _run(_fresh_ctx, ForbiddenGuard, {
        "tool": "execute_command",
        "args": {"command": "python3 _tmp_test.py"},
    })
    assert r is not None and r["status"] == "forbidden"
    assert "§4.1" in r["error"]["error"]


def test_forbidden_exec_open_write(_fresh_ctx):
    """§4.3: open(path,'w') 直写 → 拒绝 forbidden"""
    r = _run(_fresh_ctx, ForbiddenGuard, {
        "tool": "execute_command",
        "args": {"command": "python3 -c 'open(\"clawsjoy_dev/x.py\",\"w\")'"},
    })
    assert r is not None and r["status"] == "forbidden"
    assert "§4.3" in r["error"]["error"]


def test_forbidden_exec_safe_command(_fresh_ctx):
    """安全命令放行"""
    r = _run(_fresh_ctx, ForbiddenGuard, {
        "tool": "execute_command",
        "args": {"command": "echo hi"},
    })
    assert r is None


def test_forbidden_write_config_file(_fresh_ctx):
    """§4.2: write_file 写 filter_net.json → 拒绝 forbidden"""
    r = _run(_fresh_ctx, ForbiddenGuard, {
        "tool": "write_file",
        "args": {"path": "core/lib/filter_net.json", "content": "x"},
    })
    assert r is not None and r["status"] == "forbidden"
    assert "§4.2" in r["error"]["error"]


def test_forbidden_write_normal_file(_fresh_ctx):
    """write_file 正常文件放行"""
    r = _run(_fresh_ctx, ForbiddenGuard, {
        "tool": "write_file",
        "args": {"path": "output.md", "content": "x"},
    })
    assert r is None
