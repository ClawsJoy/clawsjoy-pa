# -*- coding: utf-8 -*-
"""防误伤：vault **读** 不得被判成写（2026-09-13 修我自己的误伤）。

事故（子代理盘点发现、我复核确认）：`_is_vault_write` 只检查命令串里有没有 vault 路径，
于是 grep/cat/ls **vault 读**也被判成写 → 续跑期 PA 连「读 vault 自证」都做不了。
这正是我自己刚立的体检项「判据用子串匹配 = 误伤温床」的又一实例。
"""
import sys

sys.path.insert(0, ".")
from core.gateway.v9_bridge.tool_runner import _is_vault_write

V = "/mnt/d/Obsidian/ClawsJoy/收件箱/x.md"


def test_FAULT_vault_reads_are_not_vault_writes():
    """① 先能失败：对 vault 的**读**命令必须放行。"""
    for cmd in (
        "grep -rn foo %s" % V,
        "cat %s" % V,
        "ls /mnt/d/Obsidian/ClawsJoy",
        "head -20 %s" % V,
        "wc -l %s" % V,
        "find /mnt/d/Obsidian -name '*.md'",
    ):
        assert _is_vault_write("execute_command", {"command": cmd})[0] is False, cmd


def test_PASS_vault_writes_are_still_blocked():
    """② 再能通过：写命令仍必须被拦（收紧不能放松）。"""
    for cmd in (
        "echo x >> %s" % V,
        "cat a >> %s" % V,
        "cp a %s" % V,
        "mv a %s" % V,
        "rm %s" % V,
        "tee %s" % V,
        "sed -i s/a/b/ %s" % V,
    ):
        assert _is_vault_write("execute_command", {"command": cmd})[0] is True, cmd


def test_non_vault_commands_unaffected():
    """与 vault 无关的命令（读写都）不受影响。"""
    assert _is_vault_write("execute_command", {"command": "echo x > data/reports/a.md"})[0] is False
    assert _is_vault_write("execute_command", {"command": "ls -la data/reports"})[0] is False
