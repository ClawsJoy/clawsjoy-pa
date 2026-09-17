# -*- coding: utf-8 -*-
"""Windows 底座测试（总任务书第四章逐条）。

路径抽象 / 进程台账 / PowerShell 逐条过门 / 浏览器隔离 / WSL 边界 / git 区分。
"""

from __future__ import annotations

import os

import pytest

from core.pes import windows as w
from core.pes.windows import (
    BROWSER_ISOLATION,
    REPO_ROOT,
    WSL_BOUNDARY,
    ProcessLedger,
    classify_path,
    is_sandbox_repo,
    is_wsl_path,
    join_under,
    long_path,
    normalize_path,
    same_path,
    shell_guard,
)


# ---------------------------------------------------------------- 文件系统
def test_路径统一归一为正斜杠绝对路径():
    n = normalize_path("core/pes")
    assert n == (REPO_ROOT / "core" / "pes").as_posix()
    assert "\\" not in n


def test_相对路径以仓库根为基():
    assert normalize_path("data").startswith(REPO_ROOT.as_posix())


def test_路径等价判定按平台():
    """Windows 大小写不敏感，POSIX 敏感 —— 必须按平台正确判定，不能一刀切。"""
    d = REPO_ROOT / "core" / "pes"
    other = str(d).upper()
    if os.name == "nt":
        assert same_path(d, other) is True
    else:
        assert same_path(d, other) is False


def test_join_under_正常拼接():
    p = join_under(REPO_ROOT, "data", "v9")
    assert p.as_posix() == (REPO_ROOT / "data" / "v9").as_posix()


def test_join_under_拒绝越界():
    with pytest.raises(ValueError):
        join_under(REPO_ROOT, "..")


def test_join_under_拒绝穿越到上级():
    with pytest.raises(ValueError):
        join_under(REPO_ROOT / "data", "..", "..")


def test_长路径在需要时加前缀():
    s = long_path(REPO_ROOT / ("x" * 300))
    if os.name == "nt":
        assert s.startswith("\\\\?\\")
    else:
        assert not s.startswith("\\\\?\\")


def test_短路径不加长路径前缀():
    assert not long_path(REPO_ROOT / "core").startswith("\\\\?\\")


def test_信任域分类_沙箱与金库与仓库():
    assert classify_path(REPO_ROOT / "data" / "x") == "sandbox"
    assert classify_path(REPO_ROOT / "data" / "v9" / "pa" / "x") == "vault"
    assert classify_path(REPO_ROOT / "core" / "pes") == "repo"


def test_信任域分类_系统与外部分开():
    if os.name == "nt":
        assert classify_path("C:/Windows/System32/drivers") == "system"
    assert classify_path("C:/Users/flybo/Documents/x") == "external"


def test_沙箱_git_与真项目_git_必须区分(tmp_path, monkeypatch):
    """沙箱工作副本 vs 真项目仓库 —— 产物归属必须显式区分。"""
    monkeypatch.setattr(w, "REPO_ROOT", tmp_path)
    sandbox_repo = tmp_path / "data" / "work" / "clone"
    (sandbox_repo / ".git").mkdir(parents=True)
    real_repo = tmp_path / "some_repo"
    (real_repo / ".git").mkdir(parents=True)
    assert w.classify_path(sandbox_repo) == "sandbox"
    assert w.is_sandbox_repo(sandbox_repo) is True
    assert w.is_sandbox_repo(real_repo) is False
    assert w.is_real_repo(real_repo) is True


# ---------------------------------------------------------------- WSL 边界
def test_回归_wsl_绝对路径必须被认出():
    """回归：先归一化会把 ``/home/x`` 变成 ``D:/home/x`` ⇒ 守卫静默失效。"""
    for p in ("/home/flybo/x", "/mnt/d/Obsidian", "/usr/bin/python3", "/etc/passwd", "/tmp/a", "/var/log"):
        assert is_wsl_path(p) is True, p


def test_本机路径不算_wsl():
    assert is_wsl_path(REPO_ROOT) is False
    assert is_wsl_path("C:/Windows") is False


def test_wsl_被标为跨信任边界():
    assert WSL_BOUNDARY["cross_env_is_trust_boundary"] is True
    assert WSL_BOUNDARY["requires_explicit_grant"] is True
    assert "/mnt/" in WSL_BOUNDARY["wsl_markers"]


# ---------------------------------------------------------------- PowerShell
def test_危险命令硬拒():
    for cmd in ("rm -rf /", "diskpart", "reg delete hklm", ":(){ :|:& };:"):
        assert shell_guard(cmd)["decision"] == "deny", cmd


def test_写类动词需过门():
    for cmd in ("Remove-Item x.txt", "git push origin main", "pip install requests"):
        assert shell_guard(cmd)["decision"] == "ask", cmd


def test_shell_降级请求需过门():
    """不静默降级：显式 shell / 跨环境调用一律提问。"""
    for cmd in ("cmd /c dir", "powershell -c ls", "wsl ls -la"):
        assert shell_guard(cmd)["decision"] == "ask", cmd


def test_只读命令放行():
    assert shell_guard("Get-ChildItem")["decision"] == "allow"
    assert shell_guard("Get-Content README.md")["decision"] == "allow"


def test_裁决只可能是三种值之一():
    for cmd in ("Get-ChildItem", "Remove-Item x", "rm -rf /", "", "???"):
        assert shell_guard(cmd)["decision"] in ("allow", "ask", "deny"), cmd


def test_硬拒优先于写类提问():
    """破坏性命令即使同时命中写类动词，也必须落到 deny。"""
    assert shell_guard("Remove-Item -Recurse; diskpart")["decision"] == "deny"


# ---------------------------------------------------------------- 浏览器隔离
def test_浏览器必须专用实例且不得接管日常_profile():
    assert BROWSER_ISOLATION["dedicated_instance"] is True
    assert BROWSER_ISOLATION["separate_user_data_dir"] is True
    assert BROWSER_ISOLATION["forbid_user_profile"] is True


# ---------------------------------------------------------------- 进程台账
def test_进程登记后可查在跑(tmp_path):
    ledger = ProcessLedger(path=str(tmp_path / "procs.json"))
    ledger.register(os.getpid(), ["python", "x.py"], purpose="self")
    assert os.getpid() in [r["pid"] for r in ledger.running()]


def test_不留孤儿_已死进程被结清(tmp_path):
    ledger = ProcessLedger(path=str(tmp_path / "procs.json"))
    ledger.register(2147483647, ["ghost"], purpose="bogus")
    assert 2147483647 in [r["pid"] for r in ledger.running()]
    reaped = ledger.reap_orphans()
    assert [r["pid"] for r in reaped] == [2147483647]
    assert 2147483647 not in [r["pid"] for r in ledger.running()]


def test_不存在的进程判定为不在():
    assert ProcessLedger.alive(2147483647) is False
    assert ProcessLedger.alive(0) is False


def test_结束的进程从台账结清(tmp_path):
    ledger = ProcessLedger(path=str(tmp_path / "procs.json"))
    ledger.register(2147483647, ["ghost"])
    assert ledger.finish(2147483647, exit_code=0) is True
    assert ledger.running() == []


def test_进程台账也走状态唯一出口(tmp_path):
    from core.pes.state_integrity import detect_uninstrumented

    ledger = ProcessLedger(path=str(tmp_path / "procs.json"))
    ledger.register(2147483647, ["ghost"])
    assert detect_uninstrumented(tmp_path / "procs.json")["instrumented"] is True
