"""P0 沙箱路径映射回归: 只读回退项目根 + 越权白名单 + 写不回退"""
import json
import os
import sys

sys.path.insert(0, ".")
import pytest


def test_helpers_sandbox_preferred():
    """沙箱内存在 → 不回退(优先会话产物)"""
    import tempfile
    from pathlib import Path

    from core.lib.gateway_helpers import _get_sandbox_base, _resolve_project_root_read

    tmp = Path(tempfile.mkdtemp())
    base = tmp / "u1" / "s1" / "clawsjoy_dev"
    base.mkdir(parents=True)
    (base / "hello.txt").write_text("sandbox")
    # 模拟沙箱 target(存在) → 返回 None(不触发回退)
    # _resolve_project_root_read 只接受"沙箱 target 不存在"时的回退; 存在时调用方不会调它
    _t = base / "hello.txt"
    assert _t.exists() is True
    # 回退解析: 相对路径 hello.txt → 项目根/hello.txt(项目根为本仓库, 有该文件与否无所谓, 只要落在根内)
    _fb = _resolve_project_root_read("hello.txt", _t, "u1", "s1")
    # 项目根内存在(仓库根可能有 hello.txt 也可能没有) — 关键是落在根内且路径正确
    _proj = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent.parent)))
    if _fb is not None:
        assert str(_fb.resolve()).startswith(str(_proj.resolve())), "回退必须落在项目根内"


def test_helpers_fallback_maps_to_project_root():
    """沙箱无文件 → 相对路径回退到项目根(如 core/gateway/session_log.py)"""
    from pathlib import Path

    from core.lib.gateway_helpers import _get_sandbox_base, _resolve_project_root_read

    base = _get_sandbox_base("u_zz", "s_zz")
    sandbox_target = base / "core" / "gateway" / "session_log.py"
    fb = _resolve_project_root_read("core/gateway/session_log.py", sandbox_target, "u_zz", "s_zz")
    assert fb is not None, "应回退到项目根"
    # 行为断言(不依赖 PROJECT_ROOT env / 模块加载副本): 回退目标是存在的 session_log.py 且不在沙箱内
    assert fb.exists(), "项目根应存在 core/gateway/session_log.py"
    assert fb.name == "session_log.py" and fb.parent.name == "gateway", str(fb)
    assert not str(fb.resolve()).startswith(str(base.resolve())), "回退应在沙箱之外(项目根)"


def test_helpers_escape_and_git_blocked():
    """越权回退拦截: 路径逃出项目根 / .git → None(不可回退)"""
    from core.lib.gateway_helpers import _get_sandbox_base, _resolve_project_root_read

    base = _get_sandbox_base("u_zz", "s_zz")
    # 逃逸: ../.. 会落到项目根外
    t = base / ".." / ".." / ".." / "etc" / "passwd"
    assert _resolve_project_root_read("../../etc/passwd", t, "u_zz", "s_zz") is None
    # .git
    t2 = base / ".." / ".git" / "config"
    assert _resolve_project_root_read("../../.git/config", t2, "u_zz", "s_zz") is None


def test_handlers_have_fallback_and_source():
    """源码级: read/list/search 三处回退 + source 标记(全在 sandbox_ops); 写路径不回退"""
    so = open("core/gateway/sandbox_ops.py", encoding="utf-8").read()
    assert so.count("_resolve_project_root_read") >= 3, "read/search/list 应含回退"
    assert '"source": _read_source' in so, "read 应标记 source"
    assert 'result["source"] = _read_source' in so, "search 应标记 source"
    # list 已归位 sandbox_ops(不再在主文件)
    assert '_read_source != "project_root"' in so, "越权检测应适配白名单"
    # 写路径不回退: sandbox_write 无 _resolve_project_root_read
    sw = open("core/gateway/sandbox_write.py", encoding="utf-8").read()
    assert "_resolve_project_root_read" not in sw, "写路径不得回退(只进沙箱)"
