"""#106 C4: 工具双链一致性测试 — 桥接(tool_router) 与 HTTP(sandbox) 路径解析共享验证"""
import sys, os
sys.path.insert(0, ".")

def test_write_path_consistency():
    """write_file 两链路径解析一致（防 #98/#100 行为漂移回归）"""
    from core.gateway.path_utils import _normalize_path, _resolve_path
    from core.lib.gateway_helpers import _get_sandbox_base
    uid, sid = "cons_test", "sess_1"
    base = _get_sandbox_base(uid, sid)
    # 链A（tool_router 插件用 _resolve_path）
    pA = _resolve_path(base, "clawsjoy_dev/core/lib/a.py")
    # 链B（sandbox_write handler 用 _normalize_path）
    pB = _normalize_path("clawsjoy_dev/core/lib/a.py", uid, sid)
    assert str(pA) == str(pB), f"路径不一致: A={pA} B={pB}"
    # 无前缀也应一致
    pA2 = _resolve_path(base, "core/lib/a.py")
    pB2 = _normalize_path("core/lib/a.py", uid, sid)
    assert str(pA2) == str(pB2), f"无前缀不一致: A={pA2} B={pB2}"


def test_read_path_consistency():
    """read_file 两链路径一致"""
    from core.gateway.path_utils import _normalize_path, _resolve_path
    from core.lib.gateway_helpers import _get_sandbox_base
    uid, sid = "cons_test", "sess_2"
    base = _get_sandbox_base(uid, sid)
    pA = _resolve_path(base, "clawsjoy_dev/core/lib/b.py")
    pB = _normalize_path("clawsjoy_dev/core/lib/b.py", uid, sid)
    assert str(pA) == str(pB)


def test_consecutive_per_session():
    """#106 C1: 配额 per-session 隔离"""
    import core.gateway.shared_state as ss
    ss._consecutive_reads.clear()
    ss._consecutive_reads["sess_a"] = 2
    ss._consecutive_reads["sess_b"] = 1
    assert ss._consecutive_reads["sess_a"] == 2
    assert ss._consecutive_reads["sess_b"] == 1
    # 重置 A 不影响 B
    ss._consecutive_reads["sess_a"] = 0
    assert ss._consecutive_reads["sess_b"] == 1
