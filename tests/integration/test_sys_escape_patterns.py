"""#104 锚点B：_SYS_ESCAPE_PATTERNS 读写区分 — 2>/dev/null 豁免，真实危险全拦"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.security import _detect_sys_escape

# (命令, 期望: None=放行 / 拦截理由包含串)
SAFE_CASES = [
    "ls -la clawsjoy_dev/ 2>/dev/null || ls -la",
    "python3 -c 'print(1)' 2>/dev/null",
    "make >/dev/null 2>&1",
    "echo done >> /dev/stderr",
    "cat /etc/passwd",
    "ls /etc",
    "echo a >/dev/null",
    # V9 E2E 实证: 2>/dev/null 后跟分号/管道等命令分隔符也应豁免（不是行尾/空白）
    'find . -name "audit.py" 2>/dev/null; echo ---',
    "find . -type d -name gateway 2>/dev/null | head -5",
    "grep foo bar.txt 2>/dev/null && echo found",
    "rm -f /tmp/x",  # 删除临时文件合法
]

BLOCKED_CASES = [
    ("echo test > /etc/passwd", "写入系统目录"),
    ("echo x >> /etc/hosts", "写入系统目录"),
    ("echo y > /dev/sda1", "写入系统目录"),
    ("echo z >>/etc/profile", "写入系统目录"),
    ("echo w > /etc/shadow", "写入系统目录"),
    ("2>/etc/foo cmd", "写入系统目录"),
    ("echo e 2>/etc/passwd", "写入系统目录"),
    ("echo a 1>/etc/hosts", "写入系统目录"),
    ("cmd &>/etc/passwd", "写入系统目录"),
    ("echo x 2>>/etc/profile", "写入系统目录"),
    ("rm -rf /", "rm -rf 根目录"),
    ("python3 -c \"open('/etc/foo','w')\"", "open 写系统路径"),
]


def test_safe_commands_not_blocked():
    """只读/丢弃重定向命令放行（防误报回归）"""
    for cmd in SAFE_CASES:
        r = _detect_sys_escape(cmd)
        assert r is None, f"误拦截: {cmd} -> {r}"


def test_dangerous_commands_blocked():
    """写系统目录/裸设备/高危命令仍拦截"""
    for cmd, reason in BLOCKED_CASES:
        r = _detect_sys_escape(cmd)
        assert r is not None, f"漏拦截: {cmd}"
        assert reason in r[1], f"{cmd} 拦截理由不符: got={r[1]} expect含={reason}"
