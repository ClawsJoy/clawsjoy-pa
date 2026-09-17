# -*- coding: utf-8 -*-
"""Memory 层测试：append-only + 墓碑 + **上下文来源三元组是资格位**。"""

from __future__ import annotations

import json

import pytest

from core.pes.memory import RECORD_KINDS, SOURCE_TRIPLE, MemoryLog


def _m(pes_dir):
    return MemoryLog(pes_dir / "memory.jsonl")


SRC = {"session_id": "s1", "workspace": "w1", "project": "p1"}


def test_记一条完整来源的记忆(pes_dir):
    r = _m(pes_dir).remember("preference", "输出语言", "中文", SRC)
    assert r["qualified"] is True
    assert r["op"] == "remember"


def test_缺上下文来源三元组即不合格(pes_dir):
    m = _m(pes_dir)
    r = m.remember("preference", "坏来源", "x", {"session_id": "s1"})
    assert r["qualified"] is False
    assert [x["key"] for x in m.unqualified()] == ["坏来源"]


def test_不合格记录默认不进回忆(pes_dir):
    m = _m(pes_dir)
    m.remember("preference", "好", "1", SRC)
    m.remember("preference", "坏", "2", {"project": "p1"})
    assert [r["key"] for r in m.recall()] == ["好"]
    assert [r["key"] for r in m.recall(include_unqualified=True)] == ["坏", "好"]


def test_三类记录(pes_dir):
    assert RECORD_KINDS == ("preference", "conclusion", "context")
    assert SOURCE_TRIPLE == ("session_id", "workspace", "project")


def test_非法记录类型拒绝(pes_dir):
    """回归：``"..." % x, y`` 优先级坑 —— 必须抛 ValueError。"""
    with pytest.raises(ValueError):
        _m(pes_dir).remember("bogus", "k", "v", SRC)


def test_回忆按条件过滤(pes_dir):
    m = _m(pes_dir)
    m.remember("preference", "k1", "v1", SRC)
    m.remember("conclusion", "k2", "v2", SRC)
    m.remember("preference", "k3", "v3", dict(SRC, project="p2"))
    assert [r["key"] for r in m.recall(kind="preference")] == ["k3", "k1"]
    assert [r["key"] for r in m.recall(project="p1")] == ["k2", "k1"]
    assert [r["key"] for r in m.recall(key="k2")] == ["k2"]


def test_回忆新的在前(pes_dir):
    m = _m(pes_dir)
    m.remember("preference", "先", 1, SRC)
    m.remember("preference", "后", 2, SRC)
    assert [r["key"] for r in m.recall()] == ["后", "先"]


def test_忘记写墓碑且原记录保留(pes_dir):
    """append-only：**可审计地忘掉**，不是物理删除。"""
    m = _m(pes_dir)
    r = m.remember("preference", "要忘的", "x", SRC)
    m.forget(r["record_id"], reason="老板撤回")
    assert m.recall() == []
    assert any(x.get("record_id") == r["record_id"] for x in m.rows())
    tombstones = [x for x in m.rows() if x["op"] == "forget"]
    assert tombstones[0]["target"] == r["record_id"]
    assert tombstones[0]["note"] == "老板撤回"


def test_忘记必须有目标(pes_dir):
    with pytest.raises(ValueError):
        _m(pes_dir).forget("")


def test_忘记不存在的记录不炸(pes_dir):
    m = _m(pes_dir)
    m.remember("preference", "保留", "x", SRC)
    m.forget("不存在")
    assert [r["key"] for r in m.recall()] == ["保留"]


def test_哈希链完整且篡改可检(pes_dir):
    m = _m(pes_dir)
    m.remember("preference", "a", 1, SRC)
    m.remember("conclusion", "b", 2, SRC)
    assert m.verify_chain()["ok"] is True
    lines = m.path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["value"] = 999
    lines[0] = json.dumps(row, ensure_ascii=False)
    m.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    v = m.verify_chain()
    assert v["ok"] is False and v["first_bad_seq"] == 1


def test_跨会话恢复包(pes_dir):
    m = _m(pes_dir)
    m.remember("preference", "输出语言", "中文", SRC)
    m.remember("conclusion", "M1 未过", {"why": "R-03"}, SRC)
    m.remember("context", "来源", SRC, SRC)
    b = m.context_bundle(project="p1")
    assert b["preferences"] == {"输出语言": "中文"}
    assert b["conclusions"][0]["key"] == "M1 未过"
    assert b["sources"] == [SRC]
    assert b["count"] == 3


def test_恢复包只含合格记录(pes_dir):
    m = _m(pes_dir)
    m.remember("preference", "坏的", "x", {"session_id": "s1"})
    assert m.context_bundle()["preferences"] == {}


def test_不可序列化的值不炸(pes_dir):
    m = _m(pes_dir)
    r = m.remember("conclusion", "对象", {"f": object()}, SRC)
    assert isinstance(r["value"], dict)
    assert m.verify_chain()["ok"] is True


def test_stats_汇总(pes_dir):
    m = _m(pes_dir)
    a = m.remember("preference", "a", 1, SRC)
    m.remember("conclusion", "b", 2, SRC)
    m.forget(a["record_id"])
    s = m.stats()
    assert s["rows"] == 3 and s["live"] == 1 and s["tombstones"] == 1
    assert s["chain"] is True
    assert s["projects"] == ["p1"]


def test_memory_log_默认单例与显式路径(pes_dir):
    from core.pes.memory import memory_log

    assert memory_log() is memory_log()
    assert memory_log(pes_dir / "a.jsonl").path.name == "a.jsonl"
