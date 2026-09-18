# -*- coding: utf-8 -*-
"""X-17② 批 2 · PA 四处 store 接统一出口（DS 2026-09-18 拍 A）。

【本批要证的两件事】
 ① **坏状态 fail-loud 未被出口降级**：出口 `StateFile` 只认「顶层是不是 dict」，
    PA 的业务结构判据（`threads` / `cards` / `items` / `entries` 需为 list）**留在 PA 侧**；
    接线后「结构不符 ⇒ 拒绝写入」必须仍然成立。
 ② **写走统一出口**：跨进程锁 + 原子替换 + 写者归属台账（`*.writes.jsonl`）。

【反例证明（改前必假）】本文件在接线前的 HEAD 上运行必须**大面积红**：
  HEAD 的四处 `save()` 都是 `write_text` **无条件覆写** ⇒「坏状态拒绝写入」全部不成立，
  且不产生写者台账。实测：HEAD ⇒ 6 failed / 3 passed（见本批回报）。
"""
import json
from pathlib import Path

import pytest

from core.pa.state_out import PA_STORES, PAStateCorrupt


# ============================================================ threads
def _threads_path(d, uid="u1"):
    return Path(d) / ("threads_%s.json" % uid)


def test_threads_save_损坏_拒绝写入且零写入(tmp_path):
    from core.pa.threads import ThreadStore, ThreadStoreCorrupt

    p = _threads_path(tmp_path)
    p.write_text('{"mode": "chat", "threads": [', encoding="utf-8")  # 截断 ⇒ 坏文件
    bad = p.read_bytes()

    with pytest.raises(ThreadStoreCorrupt):
        ThreadStore(str(tmp_path)).save("u1", {"mode": "chat", "threads": [], "activeThread": None})

    assert p.read_bytes() == bad, "坏状态不得被写入（活文件一个字节不动）"


def test_threads_save_结构不符_也拒绝写入(tmp_path):
    """顶层是 dict、但 `threads` 不是 list —— **出口看不出来**，只有 PA 侧判据能拦。"""
    from core.pa.threads import ThreadStore, ThreadStoreCorrupt

    p = _threads_path(tmp_path)
    p.write_text(json.dumps({"threads": "oops"}), encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(ThreadStoreCorrupt):
        ThreadStore(str(tmp_path)).save("u1", {"threads": [], "activeThread": None})

    assert p.read_bytes() == bad


def test_threads_save_成功_原子且留写者台账(tmp_path):
    from core.pa.threads import ThreadStore

    ThreadStore(str(tmp_path)).save("u1", {"mode": "chat", "threads": [], "activeThread": None})

    log = _threads_path(tmp_path).with_name("threads_u1.json.writes.jsonl")
    assert log.exists(), "接统一出口后必须留写者归属台账"
    row = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert row["writer"] == "pa.threads"
    assert row["sha256"] and row["bytes"] > 0


def test_threads_load_不存在_空状态不抛(tmp_path):
    """护栏：不存在 ≠ 损坏（新用户正常）。"""
    from core.pa.threads import ThreadStore

    assert ThreadStore(str(tmp_path)).load("nobody")["threads"] == []


# ============================================================ ledger
def test_ledger_构造期_损坏_抛且零写入(tmp_path):
    from core.pa.ledger import TodoStore

    p = tmp_path / "ledger.json"
    p.write_text("{ 半截", encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        TodoStore(str(p))

    assert p.read_bytes() == bad


def test_ledger_结构不符_拒绝写入(tmp_path):
    from core.pa.ledger import TodoStore

    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({"version": 1, "items": "oops"}), encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        TodoStore(str(p))

    assert p.read_bytes() == bad


def test_ledger_save_成功_原子且留写者台账(tmp_path):
    from core.pa.ledger import TodoStore

    p = tmp_path / "ledger.json"
    TodoStore(str(p)).add("测一条", kind="todo")

    log = p.with_name("ledger.json.writes.jsonl")
    assert log.exists()
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["writer"] == "pa.ledger"
    assert json.loads(p.read_text(encoding="utf-8"))["items"][0]["title"] == "测一条"


# ============================================================ profile
def test_profile_构造期_损坏_抛且零写入(tmp_path):
    from core.pa.profile import ProfileStore

    p = tmp_path / "profile.json"
    p.write_text("{ 半截", encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        ProfileStore(str(p))

    assert p.read_bytes() == bad


def test_profile_结构不符_拒绝写入(tmp_path):
    from core.pa.profile import ProfileStore

    p = tmp_path / "profile.json"
    p.write_text(json.dumps({"version": 1, "entries": {}}), encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        ProfileStore(str(p))

    assert p.read_bytes() == bad


def test_profile_save_成功_原子且留写者台账(tmp_path):
    from core.pa.profile import ProfileStore

    p = tmp_path / "profile.json"
    ProfileStore(str(p)).add("style", "直接", source="test", confidence="high", status="confirmed")

    log = p.with_name("profile.json.writes.jsonl")
    assert log.exists()
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["writer"] == "pa.profile"
    assert json.loads(p.read_text(encoding="utf-8"))["entries"][0]["value"] == "直接"


# ============================================================ roster
def test_roster_存在但坏_抛且不覆写(tmp_path, monkeypatch):
    """**「纯读即覆写」的对治点**：此前 load() 会静默回落内置卡并落盘覆盖（不可逆）。"""
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path))
    from core.pa import roster as R

    p = Path(R._path())
    p.write_text('{"cards": [', encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        R.load()

    assert p.read_bytes() == bad, "纯读不得覆写文件"


def test_roster_结构不符_抛(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path))
    from core.pa import roster as R

    p = Path(R._path())
    p.write_text(json.dumps({"cards": "oops"}), encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        R.load()

    assert p.read_bytes() == bad


def test_roster_不存在_初始化并落盘(tmp_path, monkeypatch):
    """护栏：不存在 ⇒ 首次运行初始化（**不是**损坏）。"""
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path))
    from core.pa import roster as R

    d = R.load()
    assert len(d["cards"]) >= 6
    assert Path(R._path()).exists()


def test_roster_save_成功_留写者台账(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path))
    from core.pa import roster as R

    R.load()
    log = Path(R._path()).with_name("roster.json.writes.jsonl")
    assert log.exists()
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["writer"] == "pa.roster"


# ============================================================ 判据范围
def test_判据范围_是PA_store白名单_不是data_v9全域():
    joined = " ".join(PA_STORES)
    assert "ledger.json" in joined and "roster.json" in joined and "threads_" in joined
    assert "turn_registry" not in joined, "非 PA store 不在白名单（判据不同）"
