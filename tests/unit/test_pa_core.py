# -*- coding: utf-8 -*-
"""2026-09-10 PA 内核 v0: 画像沉淀/修订/待办/上下文(确定性, 不依赖 LLM)"""
import sys

sys.path.insert(0, ".")
import pytest

from core.pa.pa_core import PaCore


@pytest.fixture()
def pa(tmp_path):
    return PaCore(data_dir=str(tmp_path / "pa"))


def test_no_seed_on_first_init(pa):
    u"""去种子（承 pm_1770 §二.1⒝）：首启 **⛔ 灌** —— 画像 ／ 账本皆空（承「空库之诚」）。

    ⚠ 昔之作 `test_seed_on_first_init`（断言 >= 10 条 ／ >= 3 条）⇒ **已拔** ——
      那条**正控**恰是今天的病（以本席之私记充机主之实）。
    """
    assert pa.profile.entries == []
    assert pa.ledger.items == []


def test_sediment_adds_entry(pa):
    r = pa.handle(
        "profile_sediment",
        {"domain": "aesthetic", "value": "老板圈定 A Electric Studio", "source": "2026-09-10 老板拍板", "confidence": "high"},
    )
    assert r["ok"]
    e = r["entry"]
    assert e["status"] == "confirmed" and e["domain"] == "aesthetic"
    # ⚠ 昔此断言「旧候选条目仍在」（那来自种子）⇒ 去种子后改为：**唯新条**
    act = pa.profile.active("aesthetic")
    assert [x["value"] for x in act] == ["老板圈定 A Electric Studio"]


def test_revise_supersedes(pa):
    # ⚠ 去种子后：本测自造一条 proposed（昔赖种子之 style 条）
    tgt = pa.profile.add("style", "沟通: 结论先行 + 少开放式问卷",
                         source="本测", confidence="medium", status="proposed")
    r = pa.handle("profile_revise", {"id": tgt["id"], "value": "沟通: 需要更多展开与上下文(修正版)", "source": "2026-09-10 老板校准"})
    assert r["ok"] and r["entry"]["supersedes"] == tgt["id"]
    # 旧条目不再 active
    assert all(e["id"] != tgt["id"] for e in pa.profile.active("style"))
    # revised 标记
    old = next(e for e in pa.profile.entries if e["id"] == tgt["id"])
    assert old["status"] == "revised"


def test_context_brief(pa):
    # ⚠ 去种子后：本测自带件（昔赖种子之 aesthetic ／ style ／ M3）
    pa.profile.add("aesthetic", "(测) 双主题 A+B", source="本测", confidence="high", status="confirmed")
    pa.profile.add("style", "(测) 结论先行", source="本测", confidence="high", status="confirmed")
    pa.ledger.add("M3: (测) 三页样张", kind="todo")
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
