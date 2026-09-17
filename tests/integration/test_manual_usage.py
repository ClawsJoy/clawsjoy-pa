"""「说明书用了但Agent不用」方案：P0指示牌 / P1按需注入 / P2禁则硬约束"""
import os
import sys

sys.path.insert(0, ".")
import pytest


def test_p0_prompt_has_manual_indicator():
    """P0: agent_system.md 含 manual 查询引导"""
    text = open("config/prompts/agent_system.md", encoding="utf-8").read()
    assert "entity_type='manual'" in text
    assert "操作手册" in text or "agent_manual" in text


def test_p1_manual_injection_matches_chapters(monkeypatch):
    """P1: manual 分支按任务变量匹配章节"""
    import core.lib.sag_audit_bridge as SAB
    from core.lib.precision_feed import _load_asset

    # mock SAG 章节
    fake_chapters = [
        {
            "entity_type": "manual",
            "entity_name": "1. 工具清单",
            "signature": "read_file 用途参数禁用",
            "file_path": "agent_manual.md",
        },
        {"entity_type": "manual", "entity_name": "4. 禁则清单", "signature": "禁止 _*.py 脚本", "file_path": "agent_manual.md"},
        {
            "entity_type": "manual",
            "entity_name": "3. 完成标准",
            "signature": "5 项 checklist",
            "file_path": "agent_manual.md",
        },
    ]
    monkeypatch.setattr(
        SAB, "query_entities", lambda entity_type=None, query=None, limit=50, project_id="default": fake_chapters
    )
    # 写任务 → 应匹配「工具清单」或「禁则清单」（含"写"关键词）
    out = _load_asset("manual", {"max_chars": 2000}, "u", "s", task_name="用 write_file 修改文件")
    assert out, "写任务应注入 manual 章节"
    assert "工具清单" in out or "禁则清单" in out
    # 验证任务 → 应匹配「完成标准」
    out2 = _load_asset("manual", {"max_chars": 2000}, "u", "s", task_name="验证 py_compile 通过")
    assert "完成标准" in out2 or "工具清单" in out2


def test_p1_manual_injection_empty_when_no_sag(monkeypatch):
    """P1: SAG 无 manual 实体 → 返回空（不报错）"""
    import core.lib.sag_audit_bridge as SAB
    from core.lib.precision_feed import _load_asset

    monkeypatch.setattr(SAB, "query_entities", lambda **kw: [])
    out = _load_asset("manual", {"max_chars": 2000}, "u", "s", task_name="任意任务")
    assert out == ""


def test_p2_forbidden_scripts_blocked():
    """P2: execute_command 含 _tmp_/_vfy 等 → runner pre-execute 返回 forbidden"""
    import core.os.context as _oc

    _orig = _oc._v9ctx
    _oc._v9ctx = None
    try:
        from core.gateway.guards.registry import mount_guards
        from core.gateway.guards.runner import run_pre_guards

        mount_guards(_oc.get_v9_context())
        d = run_pre_guards(
            {
                "tool": "execute_command",
                "args": {"command": "python3 _tmp_test.py"},
                "session_id": "p2s",
                "user_id": "p2u",
                "sandbox_base": "data/projects/p2u/p2s/clawsjoy_dev",
                "messages": [],
            }
        )
        assert d is not None and d.get("status") == "forbidden"
        assert "禁止执行" in d.get("reason", "")
        # 正常命令放行（不拦截）
        d2 = run_pre_guards(
            {
                "tool": "execute_command",
                "args": {"command": "python3 -m py_compile core/gateway/security.py"},
                "session_id": "p2s",
                "user_id": "p2u",
                "sandbox_base": "data/projects/p2u/p2s/clawsjoy_dev",
                "messages": [],
            }
        )
        assert d2 is None
    finally:
        _oc._v9ctx = _orig
