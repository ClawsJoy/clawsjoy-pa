"""P1 S3: 锚点B 越权守卫收编测试 — G2路径越权 + G3高危命令, 与原内联逻辑一致"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

from pathlib import Path

import pytest

from core.gateway.guards import EscapeGuard
from core.gateway.security import _SYS_ESCAPE_PATTERNS, _detect_sys_escape, _is_path_escape
from core.os.context import V9Context


@pytest.fixture(autouse=True)
def _fresh_ctx():
    return V9Context()


@pytest.fixture()
def sandbox(tmp_path):
    """模拟沙箱根: tmp_path/clawsjoy_dev"""
    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _run(ctx, payload):
    g = EscapeGuard()
    ctx.mount(g)
    return ctx.waterfall("tools/pre-execute", payload)


# ===== G2 路径越权 =====


def test_path_escape_inside_sandbox(_fresh_ctx, sandbox):
    """沙箱内相对路径 → 放行"""
    r = _run(
        _fresh_ctx, {"tool": "write_file", "args": {"path": "output.md"}, "sandbox_base": sandbox, "session_id": "s"}
    )
    assert r is None


def test_path_escape_clawsjoy_prefix(_fresh_ctx, sandbox):
    """clawsjoy_dev/ 前缀(在沙箱内) → 放行"""
    r = _run(
        _fresh_ctx,
        {"tool": "write_file", "args": {"path": "clawsjoy_dev/output.md"}, "sandbox_base": sandbox, "session_id": "s"},
    )
    assert r is None


def test_path_escape_absolute_denied(_fresh_ctx, sandbox):
    """绝对路径(/etc/x) → 拒绝 escalation_blocked"""
    r = _run(
        _fresh_ctx, {"tool": "write_file", "args": {"path": "/etc/passwd"}, "sandbox_base": sandbox, "session_id": "s"}
    )
    assert r is not None
    assert r["status"] == "escalation_blocked"
    assert r["blocked"]["reason"] == "路径越权"
    assert r["error"]["escalated"] is True


def test_path_escape_dotdot_denied(_fresh_ctx, sandbox):
    """../ 逃逸 → 拒绝"""
    r = _run(
        _fresh_ctx, {"tool": "write_file", "args": {"path": "../../etc/x"}, "sandbox_base": sandbox, "session_id": "s"}
    )
    assert r is not None and r["status"] == "escalation_blocked"


def test_path_escape_tilde_denied(_fresh_ctx, sandbox):
    """~ 开头 → 拒绝"""
    r = _run(
        _fresh_ctx, {"tool": "write_file", "args": {"path": "~/secret"}, "sandbox_base": sandbox, "session_id": "s"}
    )
    assert r is not None and r["status"] == "escalation_blocked"


def test_path_escape_non_write_tool(_fresh_ctx, sandbox):
    """断点2: 读工具系统路径越权也要拦(只读白名单外); 项目相对路径放行"""
    r = _run(
        _fresh_ctx, {"tool": "read_file", "args": {"path": "/etc/passwd"}, "sandbox_base": sandbox, "session_id": "s"}
    )
    assert r is not None and r["status"] == "escalation_blocked", "读系统路径应拦截"
    # 只读白名单: 项目相对路径放行
    r2 = _run(
        _fresh_ctx,
        {
            "tool": "read_file",
            "args": {"path": "core/gateway/session_log.py"},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r2 is None, "项目相对路径应放行(回退项目根)"


def test_path_escape_matches_security_module(_fresh_ctx, sandbox):
    """guard 与 security._is_path_escape 逐例一致"""
    cases = [
        ("a.py", False),
        ("/etc/x", True),
        ("~/x", True),
        ("clawsjoy_dev/a.py", False),
        ("../x", True),
        ("sub/dir/f.py", False),
    ]
    for p, expect in cases:
        got = _run(_fresh_ctx, {"tool": "write_file", "args": {"path": p}, "sandbox_base": sandbox, "session_id": "s"})
        assert (got is not None) == expect, f"path={p} expect={expect} got={got}"


# ===== G3 高危命令 =====


def test_cmd_safe_passes(_fresh_ctx, sandbox):
    """安全命令 → 放行"""
    r = _run(
        _fresh_ctx,
        {"tool": "execute_command", "args": {"command": "echo hi"}, "sandbox_base": sandbox, "session_id": "s"},
    )
    assert r is None


def test_cmd_rm_root_denied(_fresh_ctx, sandbox):
    """rm -rf / → 拒绝"""
    r = _run(
        _fresh_ctx,
        {"tool": "execute_command", "args": {"command": "rm -rf /"}, "sandbox_base": sandbox, "session_id": "s"},
    )
    assert r is not None and r["status"] == "escalation_blocked"
    assert "rm -rf" in r["blocked"]["reason"]


def test_cmd_redirect_system_dir_denied(_fresh_ctx, sandbox):
    """写重定向到系统目录 → 拒绝(模式16)"""
    r = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": "echo x > /etc/passwd"},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r is not None and r["status"] == "escalation_blocked"
    assert "系统目录" in r["blocked"]["reason"]


def test_cmd_dev_null_allowed(_fresh_ctx, sandbox):
    """>/dev/null 合法丢弃 → 放行(豁免)"""
    r = _run(
        _fresh_ctx,
        {"tool": "execute_command", "args": {"command": "ls > /dev/null"}, "sandbox_base": sandbox, "session_id": "s"},
    )
    assert r is None


def test_cmd_matches_security_module(_fresh_ctx, sandbox):
    """guard 与 security._detect_sys_escape 逐例一致"""
    cases = [
        "echo hi",
        "rm -rf /",
        "mkfs.ext4 /dev/sda",
        "reboot",
        "shutdown -h now",
        "dd if=/dev/zero of=/dev/sda",
        "echo x > /etc/passwd",
        "echo x > /tmp/a.txt",
        "ls > /dev/null",
        "python3 -c 'print(1)'",
    ]
    for cmd in cases:
        expect = _detect_sys_escape(cmd) is not None
        got = _run(
            _fresh_ctx,
            {"tool": "execute_command", "args": {"command": cmd}, "sandbox_base": sandbox, "session_id": "s"},
        )
        assert (got is not None) == expect, f"cmd={cmd} expect={expect} got={got}"


def test_patterns_are_tuples():
    """_SYS_ESCAPE_PATTERNS 全是 (pattern, reason) 对"""
    for p in _SYS_ESCAPE_PATTERNS:
        assert isinstance(p, tuple) and len(p) == 2


# ===== 沙箱外写出拦截(echo/curl/wget/python 写系统路径) =====


def test_cmd_redirect_tmp_allowed_system_denied(_fresh_ctx, sandbox):
    """重定向 /tmp(合法临时) → 放行; /etc(系统目录) → 拒绝"""
    r = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": "echo test > /tmp/x.txt"},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r is None, "写 /tmp 临时文件应放行: %r" % r
    r2 = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": "echo test > /etc/x.txt"},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r2 is not None and "系统目录" in r2["blocked"]["reason"]


def test_cmd_curl_o_tmp_denied(_fresh_ctx, sandbox):
    """curl -o /tmp/x.txt → 拒绝(下载写系统目录, 无 > 重定向也拦)"""
    r = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": "curl -o /tmp/x.txt https://a.com"},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r is not None and r["status"] == "escalation_blocked"
    assert "下载工具写系统目录" in r["blocked"]["reason"]


def test_cmd_wget_O_abs_denied(_fresh_ctx, sandbox):
    """wget -O /data/x → 拒绝(绝对路径写)"""
    r = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": "wget -O /data/x https://a.com"},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r is not None and r["status"] == "escalation_blocked"


def test_cmd_curl_o_relative_allowed(_fresh_ctx, sandbox):
    """curl -o data/x.txt(相对路径, 沙箱内) → 放行"""
    r = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": "curl -o data/x.txt https://a.com"},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r is None


def test_cmd_python_open_tmp_allowed_system_denied(_fresh_ctx, sandbox):
    """python open('/tmp/x','w') 临时文件 → 放行; /etc → 拒绝"""
    r = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": 'python3 -c \'open("/tmp/x","w").write("a")\''},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r is None, "写 /tmp 临时文件应放行: %r" % r
    r2 = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": 'python3 -c \'open("/etc/x","w").write("a")\''},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r2 is not None and "open 写系统路径" in r2["blocked"]["reason"]


def test_cmd_python_open_relative_allowed(_fresh_ctx, sandbox):
    """python open('data/x','w') 沙箱内 → 放行"""
    r = _run(
        _fresh_ctx,
        {
            "tool": "execute_command",
            "args": {"command": 'python3 -c \'open("data/x","w").write("a")\''},
            "sandbox_base": sandbox,
            "session_id": "s",
        },
    )
    assert r is None


def test_cmd_read_tmp_allowed(_fresh_ctx, sandbox):
    """cat /tmp / ls /tmp 只读 → 放行"""
    for cmd in ("cat /tmp/x.txt", "ls /tmp/"):
        r = _run(
            _fresh_ctx,
            {"tool": "execute_command", "args": {"command": cmd}, "sandbox_base": sandbox, "session_id": "s"},
        )
        assert r is None, cmd


def test_escape_patterns_include_tmp_and_downloads():
    """_SYS_ESCAPE_PATTERNS 覆盖 /tmp 写重定向、curl/wget 绝对写、open(tmp,'w')"""
    src = open("core/gateway/security.py", encoding="utf-8").read()
    seg = src[src.index("_SYS_ESCAPE_PATTERNS") : src.index("def _is_path_escape")]
    assert "tmp" in seg and "下载工具写系统目录" in seg
    assert "open 写系统路径" in seg
