"""任务3 P1: 子任务路径一致性（git 钩子透传 + _resolve_path 分支 A 锚点定位）"""
import sys
sys.path.insert(0, ".")
import pytest
from pathlib import Path

from core.gateway.path_utils import _resolve_path, _normalize_path


def _sub_base(uid="u1", sid="s1", tid="sub_x"):
    """子任务沙箱 base（比共享沙箱多 2 层 subtasks/{tid}）"""
    return Path("data/projects") / uid / sid / "clawsjoy_dev" / "subtasks" / tid


def test_resolve_branchA_subtask_uid_sid_anchor():
    """分支 A: 子任务 base 用 data/projects/ 锚点定位 uid/sid（不再 parts[-3]/[-2] 取错）"""
    sub_base = _sub_base("web_test", "sess_v1", "sub_a1")
    # 含 data/projects/ 的绝对路径 → 归一化到子任务沙箱
    r = _resolve_path(sub_base, "data/projects/web_test/sess_v1/clawsjoy_dev/subtasks/sub_a1/output.md")
    assert "web_test" in r.as_posix() and "sess_v1" in r.as_posix(), f"uid/sid 锚点定位失败: {r}"
    assert "subtasks/sub_a1" in r.as_posix(), f"应落在子任务沙箱: {r}"
    assert r.as_posix().endswith("output.md")


def test_resolve_branchA_subtask_double_clawsjoy():
    """分支 A: 双重 clawsjoy_dev 路径 → 子任务沙箱（base_override 生效）"""
    sub_base = _sub_base("web_test", "sess_v1", "sub_a2")
    r = _resolve_path(sub_base, "clawsjoy_dev/subtasks/sub_a2/result.md")
    assert "subtasks/sub_a2" in r.as_posix(), f"应落在子任务沙箱: {r}"
    assert r.as_posix().endswith("result.md")


def test_resolve_shared_base_unchanged():
    """回归: 共享沙箱 base 行为不变（分支 A uid/sid 仍正确 + 归一化到共享根）"""
    shared = Path("data/projects") / "web_test" / "sess_v1" / "clawsjoy_dev"
    r = _resolve_path(shared, "data/projects/web_test/sess_v1/clawsjoy_dev/a.py")
    assert r.as_posix().endswith("clawsjoy_dev/a.py"), f"共享 base 回归失败: {r}"
    assert "subtasks" not in r.as_posix()


def test_normalize_base_override():
    """_normalize_path base_override: 子任务时归一化结果不回落共享根"""
    sub_base = _sub_base("web_test", "sess_v1", "sub_a3")
    r = _normalize_path("clawsjoy_dev/x.py", "web_test", "sess_v1", base_override=sub_base)
    assert r.as_posix() == (sub_base / "x.py").as_posix(), f"base_override 失败: {r}"
    # 共享默认: 回落共享根
    r2 = _normalize_path("clawsjoy_dev/x.py", "web_test", "sess_v1")
    assert r2.as_posix().endswith("clawsjoy_dev/x.py"), f"默认 base 回归失败: {r2}"
