# -*- coding: utf-8 -*-
"""2026-09-10 PA 内核 v0: 画像沉淀/修订/待办/上下文(确定性, 不依赖 LLM)"""
import sys

sys.path.insert(0, ".")
import pytest

from core.pa.pa_core import PaCore


@pytest.fixture()
def pa(tmp_path):
    return PaCore(data_dir=str(tmp_path / "pa"))


def test_seed_on_first_init(pa):
    assert len(pa.profile.entries) >= 10
    assert len(pa.ledger.items) >= 3
    # 种子含 lesson 域(试错教训)与 decision(principal)
    assert any(e["domain"] == "lesson" for e in pa.profile.entries)
    assert any(e["domain"] == "decision" and "principal" in e["value"] for e in pa.profile.entries)


def test_sediment_adds_entry(pa):
    r = pa.handle(
        "profile_sediment",
        {"domain": "aesthetic", "value": "老板圈定 A Electric Studio", "source": "2026-09-10 老板拍板", "confidence": "high"},
    )
    assert r["ok"]
    e = r["entry"]
    assert e["status"] == "confirmed" and e["domain"] == "aesthetic"
    # 旧候选条目应仍在(提案), 不覆盖历史
    act = pa.profile.active("aesthetic")
    assert any("候选主题" in x["value"] for x in act)


def test_revise_supersedes(pa):
    # 找一个 proposed 风格条目修正
    tgt = next(e for e in pa.profile.entries if e["domain"] == "style" and e["status"] == "proposed")
    r = pa.handle("profile_revise", {"id": tgt["id"], "value": "沟通: 需要更多展开与上下文(修正版)", "source": "2026-09-10 老板校准"})
    assert r["ok"] and r["entry"]["supersedes"] == tgt["id"]
    # 旧条目不再 active
    assert all(e["id"] != tgt["id"] for e in pa.profile.active("style"))
    # revised 标记
    old = next(e for e in pa.profile.entries if e["id"] == tgt["id"])
    assert old["status"] == "revised"


def test_context_brief(pa):
    r = pa.handle("context")
    assert r["ok"]
    assert "【aesthetic】" in r["profile"] and "【style】" in r["profile"]
    assert "M3" in r["ledger"]


def test_todo_lifecycle(pa):
    r = pa.handle("todo_add", {"title": "晨报机制", "kind": "todo"})
    tid = r["item"]["id"]
    assert pa.handle("todo_done", {"id": tid})["ok"]
    assert all(i["id"] != tid for i in pa.ledger.open_items())


def test_persistence(tmp_path):
    d = str(tmp_path / "pa2")
    a = PaCore(data_dir=d)
    a.handle("profile_sediment", {"domain": "style", "value": "持久化测试", "confidence": "medium"})
    b = PaCore(data_dir=d)  # 重新加载
    assert any(e["value"] == "持久化测试" for e in b.profile.entries)


def test_markdown_render(pa):
    r = pa.handle("profile_markdown")
    assert r["ok"] and r["markdown"].startswith("# PA 画像档案")
