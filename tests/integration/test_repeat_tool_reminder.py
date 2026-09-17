"""连续重复工具调用提醒(借鉴 Harness repeat-tool-reminder)"""
import sys
sys.path.insert(0, ".")
import pytest

from core.gateway import repeat_tool_reminder as rtr


@pytest.fixture(autouse=True)
def _clean():
    rtr._counts.clear()
    rtr.configure()  # 恢复默认阈值
    yield
    rtr._counts.clear()


def test_canonicalize_sorts_keys():
    """canonicalize 深度排序: 键序不同视为相同参数"""
    a = rtr.canonicalize({"path": "a.py", "content": "x", "n": {"b": 1, "a": 2}})
    b = rtr.canonicalize({"content": "x", "n": {"a": 2, "b": 1}, "path": "a.py"})
    assert a == b, f"键序不同应规范化相同: {a} vs {b}"


def test_observe_thresholds():
    """第 3/5/8 次命中阈值返回提醒, 其余 None"""
    msgs = []
    for i in range(1, 9):
        m = rtr.observe("agent1", "read_file", {"path": "a.py"})
        msgs.append((i, m))
    assert msgs[2][1] is not None and "连续 3 次" in msgs[2][1], f"第3次应提醒: {msgs[2]}"
    assert msgs[3][1] is None, f"第4次不应提醒: {msgs[3]}"
    assert msgs[4][1] is not None and "连续 5 次" in msgs[4][1]
    assert msgs[7][1] is not None and "连续 8 次" in msgs[7][1]


def test_observe_different_args_no_trigger():
    """不同参数不算重复"""
    msgs = []
    for p in ("a.py", "b.py", "c.py", "d.py"):
        msgs.append(rtr.observe("agent2", "read_file", {"path": p}))
    assert all(m is None for m in msgs), "不同参数不应触发提醒"


def test_observe_not_blocking():
    """观察不否决: 每次返回提醒或 None, 从不抛错"""
    for i in range(10):
        m = rtr.observe("agent3", "write_file", {"path": "x.py"})
        assert m is None or isinstance(m, str)


def test_reset():
    """reset 后计数清零, 重新从第 1 次计"""
    rtr.observe("agent4", "exec", {"cmd": "ls"})
    rtr.observe("agent4", "exec", {"cmd": "ls"})
    rtr.reset("agent4")
    m = rtr.observe("agent4", "exec", {"cmd": "ls"})
    assert m is None, "reset 后第 1 次不应提醒"
    rtr.observe("agent4", "exec", {"cmd": "ls"})
    m2 = rtr.observe("agent4", "exec", {"cmd": "ls"})
    assert m2 is not None and "连续 3 次" in m2, f"reset 后重新计到第3次: {m2}"


def test_reset_only_agent():
    """reset 只清目标 agent, 不影响其他 agent"""
    rtr.observe("a1", "read_file", {"path": "x"})
    rtr.observe("a1", "read_file", {"path": "x"})
    rtr.observe("b1", "read_file", {"path": "x"})
    rtr.observe("b1", "read_file", {"path": "x"})
    rtr.reset("a1")
    # a1 清零, b1 保留
    assert rtr.observe("b1", "read_file", {"path": "x"}) is not None, "b1 第3次应提醒"
    assert rtr.observe("a1", "read_file", {"path": "x"}) is None, "a1 已重置"


def test_configure_exclude():
    """exclude 通配符: 排除的工具不跟踪"""
    rtr.configure(exclude=["list_*"])
    assert rtr.observe("a", "list_dir", {"path": "/"}) is None
    assert rtr.observe("a", "list_dir", {"path": "/"}) is None, "exclude 工具不计数"
