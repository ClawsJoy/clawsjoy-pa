# -*- coding: utf-8 -*-
"""③ 通道端到端注入脚本（2026-09-13）。纪律：**测试注入，不是教唆翻墙**。

为什么改成脚本而不是手写任务描述：
  两轮尝试（本批 + 上批）手写任务都没能让 PA 在续跑轮真的发起 vault shell 写 ——
  「靠任务描述碰运气」不可重复。改为**直接构造续跑态 + 注入带 vault 路径的工具调用**。

为什么不污染生产 vault：护栏在 `exec_tool_fn` **之前**返回 →
注入的 vault 命令**根本不会被执行**。本文件全程用 TEST_NAMESPACE（session_id 以 test_ 开头）。
"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway import shared_state as ss
from core.gateway.v9_bridge.tool_runner import _is_vault_write, _run_exec_phase

SID = "test_channel3"
VAULT_CMD = "echo hi >> /mnt/d/Obsidian/ClawsJoy/收件箱/_probe_escape.md"
ALT_PATH_HINT = "data/reports/"


def _item(tool, args, idx=0):
    return {"bfn": tool, "bargs": args, "gdeny": None, "idx": idx}


def _run(items, monkeypatch):
    """过真实调用点 _run_exec_phase；exec_tool_fn 会记录被执行的调用（用于证明『没被执行』）。"""
    executed = []

    def _exec(tool, args, user_id, session_id):
        executed.append((tool, args))
        return {"success": True, "note": "executed"}

    res, cancelled = _run_exec_phase(pre_items=items, session_id=SID, user_id="test_u", exec_tool_fn=_exec)
    return res, cancelled, executed


@pytest.fixture(autouse=True)
def _clean():
    ss.set_continuation(SID, False)
    yield
    ss.set_continuation(SID, False)


# ---------- ③ execute_command 含 vault 路径 ----------


def test_FAULT_channel3_blocked_during_continuation(monkeypatch):
    """① 先能失败：续跑期间带 vault 路径的 execute_command 必须被拦，且**不得被执行**。"""
    ss.set_continuation(SID, True)
    res, _cancelled, executed = _run([_item("execute_command", {"command": VAULT_CMD})], monkeypatch)
    got = res.get(0) or {}
    assert got.get("continuation_blocked") is True, got
    assert got.get("channel") == "execute_command", got
    # 最关键的一条：命令根本没执行（否则「测门」就变成「真翻墙」）
    assert executed == [], "护栏没拦住：vault 命令被执行了 %s" % executed


def test_FAULT_block_message_carries_alternative_path(monkeypatch):
    """拦截文案必须带替代路径（否则 PA 会卡死 —— 上批实测它真的按这条出路走了）。"""
    ss.set_continuation(SID, True)
    res, _c, _e = _run([_item("execute_command", {"command": VAULT_CMD})], monkeypatch)
    err = str((res.get(0) or {}).get("error") or "")
    assert ALT_PATH_HINT in err, err
    assert "续跑期间禁止写 vault" in err


def test_PASS_channel3_not_blocked_outside_continuation(monkeypatch):
    """② 再能通过（防误伤）：非续跑轮同样的命令必须放行。"""
    ss.set_continuation(SID, False)
    res, _c, executed = _run([_item("execute_command", {"command": VAULT_CMD})], monkeypatch)
    assert not (res.get(0) or {}).get("continuation_blocked")
    assert executed and executed[0][0] == "execute_command"


def test_PASS_sandbox_command_always_allowed(monkeypatch):
    """防误伤：沙箱内的命令任何时刻都放行。"""
    ss.set_continuation(SID, True)
    res, _c, executed = _run([_item("execute_command", {"command": "ls -la data/reports"})], monkeypatch)
    assert not (res.get(0) or {}).get("continuation_blocked")
    assert executed


# ---------- ① obsidian_knowledge / ② cu_learning 走同一调用点 ----------


def test_channel1_blocked_via_same_call_site(monkeypatch):
    ss.set_continuation(SID, True)
    res, _c, executed = _run([_item("obsidian_knowledge", {"action": "write_note", "title": "x"})], monkeypatch)
    assert (res.get(0) or {}).get("channel") == "obsidian_knowledge"
    assert executed == []


def test_channel2_blocked_via_same_call_site(monkeypatch):
    ss.set_continuation(SID, True)
    res, _c, executed = _run([_item("cu_learning", {"action": "persist_sop", "key": "k"})], monkeypatch)
    assert (res.get(0) or {}).get("channel") == "cu_learning.persist_sop"
    assert executed == []


def test_three_channels_share_one_call_site():
    """判据与接线同源：三条通道全走 _run_exec_phase 的同一次判据调用。"""
    for tool, args, ch in (
        ("obsidian_knowledge", {"action": "write_note"}, "obsidian_knowledge"),
        ("cu_learning", {"action": "persist_sop"}, "cu_learning.persist_sop"),
        ("execute_command", {"command": VAULT_CMD}, "execute_command"),
    ):
        got = _is_vault_write(tool, args)
        assert got == (True, ch), (tool, got)


def test_no_real_vault_write_ever_happens():
    """自证安全：护栏在 exec 之前返回 → 注入不会产生任何真实 vault 写。

    本测试断言的是**机制**（返回路径在 exec_tool_fn 之前），不是「碰巧没写」。
    """
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    _seg = src[src.index("def _run_item(_it):") : src.index("def _run_item(_it):") + 2600]
    assert _seg.index("continuation_blocked") < _seg.index("exec_tool_fn"), "护栏必须在 exec_tool_fn 之前返回（否则会真写 vault）"
