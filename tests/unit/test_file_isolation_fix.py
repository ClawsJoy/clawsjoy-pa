"""文件隔离修复回归测试: 子任务路径解析(subtasks/{tid} 双重嵌套 + 跨线程主沙箱访问)"""
import sys

sys.path.insert(0, ".")
from pathlib import Path

from core.gateway.path_utils import _normalize_path, _resolve_path, _subtask_offset


def _sub_base():
    return Path("data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA")


def test_subtask_offset_detects():
    """subtask base 偏移识别"""
    assert _subtask_offset(_sub_base()) == "subtasks/taskA"
    assert _subtask_offset(Path("data/projects/u/s/clawsjoy_dev")) == ""
    assert _subtask_offset(Path("data/projects/u/s/clawsjoy_dev/subtasks/x")) == "subtasks/x"
    assert _subtask_offset(Path("/tmp/other")) == ""


def test_subtask_relative_path_stays_in_thread():
    """相对路径 → 落在子任务 base 内"""
    got = _resolve_path(_sub_base(), "result.md")
    assert str(got) == "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA/result.md"


def test_subtask_abs_with_subtasks_no_double_nesting():
    """绝对路径含 subtasks/taskA → 对齐 base(不双重嵌套)"""
    got = _resolve_path(_sub_base(), "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA/result.md")
    assert str(got) == "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA/result.md"
    # clawsjoy_dev + subtasks 前缀
    got2 = _resolve_path(_sub_base(), "clawsjoy_dev/subtasks/taskA/result.md")
    assert str(got2) == "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA/result.md"
    # 裸 subtasks 前缀
    got3 = _resolve_path(_sub_base(), "subtasks/taskA/result.md")
    assert str(got3) == "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA/result.md"
    # 完整绝对路径
    got4 = _resolve_path(
        _sub_base(), "/home/flybo/clawsjoy_v5/data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA/result.md"
    )
    assert str(got4) == "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA/result.md"


def test_subtask_main_sandbox_abs_stays_main():
    """显式指向主沙箱的绝对路径 → 保持主沙箱(跨线程读/写可用)"""
    got = _resolve_path(_sub_base(), "data/projects/user1/sess1/clawsjoy_dev/result.md")
    assert str(got) == "data/projects/user1/sess1/clawsjoy_dev/result.md"
    got2 = _resolve_path(_sub_base(), "data/projects/user1/sess1/clawsjoy_dev/data/reports/r.md")
    assert str(got2) == "data/projects/user1/sess1/clawsjoy_dev/data/reports/r.md"


def test_subtask_tmp_abs_stays_abs():
    """绝对 /tmp 路径保持原样"""
    got = _resolve_path(_sub_base(), "/tmp/out.md")
    assert str(got) == "/tmp/out.md"


def test_main_sandbox_unaffected():
    """主沙箱 base 行为不变(非 subtask)"""
    main = Path("data/projects/user1/sess1/clawsjoy_dev")
    got = _resolve_path(main, "clawsjoy_dev/result.md")
    assert str(got) == "data/projects/user1/sess1/clawsjoy_dev/result.md"
    got2 = _resolve_path(main, "data/projects/user1/sess1/clawsjoy_dev/a.md")
    assert str(got2) == "data/projects/user1/sess1/clawsjoy_dev/a.md"


def test_subtask_similar_name_no_false_match():
    """相似子任务名(subtasks/taskA vs taskAB)不应误判"""
    got = _resolve_path(_sub_base(), "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskAB/x.md")
    # 不同子任务 → 不应对齐到 taskA; 保持原有行为(落到子任务内嵌套或主沙箱)
    assert "taskAB" in str(got)


def test_subtask_other_sibling_consistent():
    """审核修复: 指向其他子任务(taskAB)的路径, 三种写法落点一致(不双重嵌套)"""
    sub = Path("data/projects/user1/sess1/clawsjoy_dev/subtasks/taskA")
    r1 = _resolve_path(sub, "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskAB/x.md")
    r2 = _resolve_path(sub, "clawsjoy_dev/subtasks/taskAB/x.md")
    r3 = _resolve_path(sub, "subtasks/taskAB/x.md")
    expect = "data/projects/user1/sess1/clawsjoy_dev/subtasks/taskAB/x.md"
    assert str(r1) == expect, f"abs: {r1}"
    assert str(r2) == expect, f"clawsjoy_dev: {r2}"
    assert str(r3) == expect, f"bare: {r3}"
