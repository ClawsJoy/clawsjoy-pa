"""#2 运行时上下文投影回归测试: 快照渲染 + 变化驱动 + 持久 user 消息"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    import core.gateway.context_projection as cp
    import core.gateway.session_log as sl

    monkeypatch.setattr(cp, "_snapshot_cache", {})
    monkeypatch.setattr(sl, "_logs", {})
    _orig = sl.get_session_log

    def _get_iso(sid, base_dir=None):
        return _orig(sid, base_dir=tmp_path)

    monkeypatch.setattr(sl, "get_session_log", _get_iso)
    yield


def test_render_policy_snapshot_fields():
    """快照含沙箱/审批/工具指导; 读自 execution_policy"""
    from core.gateway.context_projection import render_policy_snapshot

    snap = render_policy_snapshot("u1", "s_cp1")
    assert "sandbox_mode" in snap and "approval_mode" in snap and "tool_guidance" in snap
    tg = snap["tool_guidance"]
    assert "execute_command" in tg["exclusive_tools"], "串行工具应含 execute_command"
    assert tg["max_parallel_tools"] == 4
    assert "write_pending" in snap["approval_mode"] and "plan_pending" in snap["approval_mode"]
    # approval 状态透传
    snap2 = render_policy_snapshot("u1", "s_cp1", {"write_pending": True, "plan_pending": False})
    assert snap2["approval_mode"]["write_pending"] is True


def test_project_change_driven():
    """变化才追加: 同快照 → None; 变化 → 文本; ≤600 字"""
    from core.gateway.context_projection import project_runtime_context, render_policy_snapshot

    s1 = render_policy_snapshot("u1", "s_cp2")
    t1 = project_runtime_context("s_cp2", s1)
    assert t1 is not None and len(t1) <= 600, f"首轮应注入且≤600: {len(t1) if t1 else 0}"
    assert "沙箱" in t1 and "审批" in t1, t1
    assert project_runtime_context("s_cp2", s1) is None, "未变不应重复注入"
    # 变化(审批状态翻转) → 再次注入
    s2 = render_policy_snapshot("u1", "s_cp2", {"write_pending": True, "plan_pending": False})
    t2 = project_runtime_context("s_cp2", s2)
    assert t2 is not None and t2 != t1, "变化应再次注入"
    assert project_runtime_context("s_cp2", s2) is None


def test_reset_clears_cache():
    """reset_context_projection → 同快照强制重注"""
    from core.gateway.context_projection import (
        project_runtime_context,
        render_policy_snapshot,
        reset_context_projection,
    )

    s = render_policy_snapshot("u1", "s_cp3")
    assert project_runtime_context("s_cp3", s) is not None
    assert project_runtime_context("s_cp3", s) is None
    reset_context_projection("s_cp3")
    assert project_runtime_context("s_cp3", s) is not None, "reset 后应重注"


def test_injected_message_persists(tmp_path):
    """注入写 user_message 事件(轮起始位) → derive_messages 保留(持久)"""
    from core.gateway.context_projection import project_runtime_context, render_policy_snapshot
    from core.gateway.session_log import get_session_log, log_event

    s = render_policy_snapshot("u1", "s_cp4")
    txt = project_runtime_context("s_cp4", s)
    assert txt is not None
    # 模拟 bridge_loop 注入: role=system(防守卫/分类误读) + 写 user_message 事件(source=runtime_context)
    log_event("s_cp4", "user_message", {"role": "system", "content": txt, "source": "runtime_context"})
    log_event("s_cp4", "user_message", {"role": "user", "content": "原始任务"})
    msgs = get_session_log("s_cp4").derive_messages()
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user"], roles
    assert any(m.get("content") == txt for m in msgs), "快照应持久在投影中"
    # 事件层有 source 标记
    evs = [ev.payload for ev in get_session_log("s_cp4")._events if ev.type == "user_message"]
    assert any(e.get("source") == "runtime_context" for e in evs)


def test_bridge_injection_source():
    """bridge_loop 注入点源码: 每轮开始 render+project; 变化才 log; role=system 防守卫误读"""
    src = (
        open("agent_gateway_enhanced.py", encoding="utf-8").read()
        + open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()
    )  # P3-B: G 块已归位
    assert "render_policy_snapshot(user_id, session_id" in src, "每轮应渲染实时快照"
    assert "project_runtime_context(session_id, _snap_ctx)" in src
    assert '"source": "runtime_context"' in src, "注入应写 runtime_context 事件"
    assert 'messages.append({"role": "system", "content": _ctx_txt})' in src, "快照应 role=system"
    assert "reset_context_projection(session_id)" in src, "新任务应清指纹缓存"
