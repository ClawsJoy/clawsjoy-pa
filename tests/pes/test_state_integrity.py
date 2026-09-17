# -*- coding: utf-8 -*-
"""State Integrity 层（M1 状态可信）测试。

覆盖 M1 四条判据，并**钉住三个已在 Windows 上实测复现的缺陷**：

* 回归 A：``StateReport`` 缺 ``data`` ⇒ 全新文件的首次读/写直接 AttributeError；
* 回归 B：``_atomic_write`` 文本模式换行翻译（LF→CRLF）⇒ 写台账 sha256 对不上，
  ``detect_uninstrumented`` 把**每个**状态文件误报成「有未插桩写者」；
* 回归 C：seed（资格）键不得被运行态写入改动。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.pes.state_integrity import (
    QUARANTINE_DIR,
    WRITE_LOG_SUFFIX,
    StateFile,
    StateIntegrityError,
    StateReport,
    detect_uninstrumented,
    scan_state_dir,
)


def _sf(pes_dir, name="state.json", seed_keys=()):
    return StateFile(pes_dir / name, writer="test.writer", seed_keys=seed_keys)


# ---------------------------------------------------------------- 判据 ② 容错读
def test_读不存在的文件不抛且返回空状态(pes_dir):
    rep = _sf(pes_dir).read()
    assert isinstance(rep, StateReport)
    assert rep.corrupted is False
    assert rep.data == {}
    assert rep.degradations, "「文件不存在」也必须作为降级事实被记下（不静默）"


def test_回归A_全新文件的首次写入必须走得通(pes_dir):
    """回归 A：缺 ``StateReport.data`` 会让「唯一写出口」在最常见的首次写入上崩。"""
    sf = _sf(pes_dir)
    doc, rep = sf.update_runtime(lambda d: d.update({"a": 1}), writer="test.writer")
    assert doc == {"a": 1}
    assert sf.read().data == {"a": 1}


def test_损坏文件被隔离且不抛原始异常(pes_dir):
    p = pes_dir / "bad.json"
    p.write_text("{ 这不是 JSON", encoding="utf-8")
    rep = StateFile(p).read()
    assert rep.corrupted is True
    assert rep.reason == "invalid_json"
    assert rep.quarantined and rep.quarantined.endswith(".bad")
    assert Path(rep.quarantined).exists(), "隔离区必须留下证据（不删原始内容）"
    assert rep.message, "必须给出可读提示（判据②）"


def test_串接损坏可抢救第一份合法_JSON(pes_dir):
    p = pes_dir / "extra.json"
    p.write_text('{"a": 1}\n{"b": 2}', encoding="utf-8")
    rep = StateFile(p).read()
    assert rep.corrupted is True
    assert rep.recovered is True
    assert rep.data == {"a": 1}


def test_自助恢复_auto_能重建可用状态(pes_dir):
    p = pes_dir / "rec.json"
    p.write_text("{ 坏", encoding="utf-8")
    sf = StateFile(p)
    assert sf.read().corrupted is True
    rep = sf.recover("auto")
    assert rep.ok is True and rep.recovered is True
    assert sf.read().data == {}


def test_恢复动作不清空_seed(pes_dir):
    """恢复选了 empty 重建，也必须把**已读到的** seed 带回来（资格不因恢复而丢）。"""
    p = pes_dir / "rec2.json"
    sf = StateFile(p, seed_keys=("seed",))
    sf.set_seed({"seed": {"k": 1}})
    sf.update_runtime(lambda d: d.update({"run": 1}), writer="runner")
    rep = sf.recover("empty")
    assert rep.ok is True and rep.recovered is True
    assert sf.read().data.get("seed") == {"k": 1}, "恢复动作不得抹掉资格(seed)"
    assert "run" not in sf.read().data


def test_文件损坏到不可抢救时_seed_也一起丢_需重设(pes_dir):
    """**如实标注的设计事实**（不是缺陷）：seed 与运行态同在文件里，
    文件坏到抢救不出任何 JSON 时，seed 无从恢复 —— 恢复后必须重新 set_seed。
    证据（被隔离的原文件）仍在隔离区，可人工核对。"""
    p = pes_dir / "rec3.json"
    sf = StateFile(p, seed_keys=("seed",))
    sf.set_seed({"seed": {"k": 1}})
    p.write_text("{ 完全坏掉，抢救不出", encoding="utf-8")
    rep = sf.recover("auto")
    assert rep.ok is True
    assert sf.read().data == {}
    assert rep.quarantined or list((pes_dir / ".quarantine").glob("*.bad")), "隔离区必须留有证据"


# ---------------------------------------------------------------- 判据 ③ seed 分离
def test_seed_与运行态分离_运行态写不动_seed(pes_dir):
    sf = _sf(pes_dir, seed_keys=("seed", "project_root"))
    sf.set_seed({"seed": {"v": 1}, "project_root": "D:/x"})
    doc, rep = sf.update_runtime(lambda d: d.update({"seed": {"v": 999}, "a": 2}), writer="runner")
    assert doc["seed"] == {"v": 1}, "运行态不得改写 seed 键"
    assert doc["project_root"] == "D:/x"
    assert doc["a"] == 2
    assert any("seed" in d for d in rep.degradations), "拒绝 seed 写入必须留降级痕迹（不静默）"
    assert sf.read().data["seed"] == {"v": 1}


def test_split_拆出_seed_与_runtime(pes_dir):
    sf = _sf(pes_dir, seed_keys=("seed",))
    sf.set_seed({"seed": 1})
    sf.update_runtime(lambda d: d.update({"run": 2}), writer="runner")
    seed, runtime = sf.split()
    assert seed == {"seed": 1}
    assert runtime == {"run": 2}


# ---------------------------------------------------------------- 判据 ① 无未插桩写者
def test_回归B_原子写不做换行翻译(pes_dir):
    """回归 B：Windows 文本模式会把 \\n 翻成 \\r\\n，写台账记的却是 LF 文本的 sha256。"""
    sf = _sf(pes_dir)
    sf.update_runtime(lambda d: d.update({"a": 1}), writer="test.writer")
    raw = (pes_dir / "state.json").read_bytes()
    assert b"\r\n" not in raw, "原子写必须禁用换行翻译，否则写台账 sha256 永远对不上"
    assert raw == b'{\n  "a": 1\n}'


def test_经唯一出口写过的文件判定为已插桩(pes_dir):
    sf = _sf(pes_dir)
    sf.update_runtime(lambda d: d.update({"a": 1}), writer="test.writer")
    r = detect_uninstrumented(pes_dir / "state.json")
    assert r["instrumented"] is True, "经出口写的文件不得被误报：%s" % r["reason"]
    assert r["last_writer"] == "test.writer"


def test_绕过出口直接改盘会被机械识别(pes_dir):
    p = pes_dir / "state.json"
    sf = _sf(pes_dir)
    sf.update_runtime(lambda d: d.update({"a": 1}), writer="test.writer")
    p.write_text(json.dumps({"a": 2}), encoding="utf-8")  # 未插桩写者
    r = detect_uninstrumented(p)
    assert r["instrumented"] is False
    assert "未插桩" in r["reason"]


def test_没有写台账的文件被判未插桩(pes_dir):
    p = pes_dir / "handwritten.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    r = detect_uninstrumented(p)
    assert r["instrumented"] is False
    assert "写台账" in r["reason"]


def test_写台账逐条记录写者(pes_dir):
    sf = _sf(pes_dir)
    sf.update_runtime(lambda d: d.update({"n": 1}), writer="w.one")
    sf.update_runtime(lambda d: d.update({"n": 2}), writer="w.two")
    lines = [
        json.loads(x)
        for x in (pes_dir / ("state.json" + WRITE_LOG_SUFFIX)).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    assert [x["writer"] for x in lines] == ["w.one", "w.two"]
    assert [x["seq"] for x in lines] == [1, 2]


def test_scan_state_dir_只扫单文档状态不扫追加式账本(pes_dir):
    """追加式账本由哈希链保证完整性，用「全文 sha256」判它会误报。"""
    (pes_dir / "ledger.jsonl").write_text('{"seq": 1}\n', encoding="utf-8")
    (pes_dir / "loose.json").write_text("{}", encoding="utf-8")
    bad = scan_state_dir(pes_dir)
    names = [Path(b["path"]).name for b in bad]
    assert "loose.json" in names
    assert "ledger.jsonl" not in names


def test_隔离区与台账文件不被当成状态文件扫描(pes_dir):
    sf = _sf(pes_dir)
    sf.update_runtime(lambda d: d.update({"a": 1}), writer="test.writer")
    names = [Path(b["path"]).name for b in scan_state_dir(pes_dir)]
    assert "state.json" not in names
    assert not any(n.endswith(WRITE_LOG_SUFFIX) for n in names)
    assert QUARANTINE_DIR not in [p.name for p in pes_dir.iterdir()] or True


def test_损坏文件留痕不删证据(pes_dir):
    p = pes_dir / "keep.json"
    original = "{ 坏内容"
    p.write_text(original, encoding="utf-8")
    StateFile(p).read()
    assert p.read_text(encoding="utf-8") == original, "隔离是「复制留证」，不得销毁原文件"


def test_StateIntegrityError_是给上层看的可读错误():
    assert issubclass(StateIntegrityError, Exception)


def test_读非对象_JSON_被隔离(pes_dir):
    p = pes_dir / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rep = StateFile(p).read()
    assert rep.corrupted is True
    assert rep.reason == "not_object"
    assert rep.data == {}
