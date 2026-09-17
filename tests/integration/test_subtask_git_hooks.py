"""任务3 P1: git 钩子 sandbox_base 透传（子任务独立 git 操作）"""
import sys, subprocess
sys.path.insert(0, ".")
import pytest
from pathlib import Path

from core.gateway.sandbox_git import _sandbox_git_pre_write, _sandbox_git_post_write


def test_git_hooks_use_sandbox_base(tmp_path, monkeypatch):
    """sandbox_base 指定时 git 钩子在子任务 git 上操作（而非共享沙箱）"""
    calls = []

    def _fake_run(cmd, **kw):
        calls.append((cmd, kw.get("cwd", "")))
        _out = b"stash-ref-123" if "stash" in cmd else b""
        return subprocess.CompletedProcess(cmd, 0, stdout=_out, stderr=b"")

    monkeypatch.setattr("core.gateway.sandbox_git.subprocess.run", _fake_run)
    sub_base = tmp_path / "subtasks" / "sub_x"
    sub_base.mkdir(parents=True)
    (sub_base / ".git").mkdir()
    # pre_write: stash create 在子任务 git
    ref = _sandbox_git_pre_write("u1", "s1", sandbox_base=sub_base)
    assert ref is not None
    stash_calls = [c for c in calls if "stash" in c[0]]
    assert stash_calls, "应调用 git stash"
    assert str(sub_base) in stash_calls[0][1], f"stash cwd 应为子任务沙箱: {stash_calls[0][1]}"
    # post_write: add 在子任务 git
    calls.clear()
    _sandbox_git_post_write("u1", "s1", "output.md", ref, sandbox_base=sub_base)
    add_calls = [c for c in calls if c[0][0:2] == ["git", "add"]]
    assert add_calls, "应调用 git add"
    assert str(sub_base) in add_calls[0][1], f"add cwd 应为子任务沙箱: {add_calls[0][1]}"


def test_git_hooks_default_shared(monkeypatch):
    """默认（不传 sandbox_base）行为不变——仍用共享沙箱（回归保护）"""
    import core.gateway.sandbox_git as sg
    calls = []
    def _fake_run(cmd, **kw):
        calls.append(kw.get("cwd", ""))
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
    monkeypatch.setattr(sg, "subprocess", type("M", (), {"run": _fake_run})())
    # 共享沙箱无 .git → pre_write 返回 None（不调用 git）
    monkeypatch.setattr(sg, "_get_sandbox_base", lambda u, s: Path("/tmp/nonexist_sandbox"))
    ref = _sandbox_git_pre_write("u1", "s1")
    assert ref is None, "共享沙箱无 .git 时应返回 None"
    assert not calls, "不应调用 git"
