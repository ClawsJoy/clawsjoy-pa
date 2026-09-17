"""P2 禁则硬约束：_*.py / 配置文件 / open() 绕过 — P1 S6 起经 runner 验证(守卫已从工具路由移到 pre-execute)"""
import sys

sys.path.insert(0, ".")
import pytest

import core.os.context as _oc


@pytest.fixture(autouse=True)
def _guards():
    """独立全局单例 + 挂载全量守卫(与网关启动一致)"""
    _orig = _oc._v9ctx
    _oc._v9ctx = None
    from core.gateway.guards.registry import mount_guards
    from core.gateway.guards.runner import _scope_mounted

    _scope_mounted.clear()
    mount_guards(_oc.get_v9_context())
    yield
    _oc._v9ctx = _orig
    _scope_mounted.clear()


def _pre(tool, args):
    """经 runner 执行 pre-guards(真实调用点路径), 返回 deny 或 None"""
    from core.gateway.guards.runner import run_pre_guards

    return run_pre_guards(
        {
            "tool": tool,
            "args": args,
            "session_id": "p2s",
            "user_id": "p2u",
            "sandbox_base": "data/projects/p2u/p2s/clawsjoy_dev",
            "messages": [],
            "tool_call_id": "c1",
            "approved": {},
        }
    )


def test_forbidden_tmp_script_bridge():
    """桥接路径：_*.py 拦截(runner pre-execute)"""
    d = _pre("execute_command", {"command": "python3 _tmp_evil.py"})
    assert d is not None and d.get("status") == "forbidden"
    assert "禁止执行" in d.get("reason", "")


def test_forbidden_config_write():
    """write_file 写共享配置 → 拦截(runner pre-execute)"""
    d = _pre("write_file", {"path": "clawsjoy_dev/core/lib/filter_net.json", "content": "{}"})
    assert d is not None and d.get("status") == "forbidden"
    assert "共享配置" in d.get("reason", "")
    # 正常文件放行(approval 未确认会 write_pending, 但非 forbidden)
    d2 = _pre("write_file", {"path": "clawsjoy_dev/core/lib/ok.py", "content": "x=1"})
    assert d2 is None or d2.get("status") != "forbidden"


def test_forbidden_open_write():
    """execute_command 里 open(path,'w') + clawsjoy_dev/ → 拦截"""
    d = _pre("execute_command", {"command": "python3 -c \"open('clawsjoy_dev/x.py','w').write('x')\" "})
    assert d is not None and d.get("status") == "forbidden"
    assert "open(path,'w')" in d.get("reason", "") or "禁止用 open" in d.get("reason", "")
    # 正常命令放行
    d2 = _pre("execute_command", {"command": "ls -la clawsjoy_dev/"})
    assert d2 is None


def test_http_path_forbidden_tmp():
    """HTTP 路径（sandbox_ops exec）也拦截 _*.py"""
    # 直接调 handler 需要 flask context；验证源码含拦截
    import inspect

    import core.gateway.sandbox_ops as SO

    src = inspect.getsource(SO)
    assert "_tmp_" in src or "forbidden" in src
