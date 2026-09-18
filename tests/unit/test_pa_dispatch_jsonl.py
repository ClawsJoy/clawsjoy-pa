# -*- coding: utf-8 -*-
"""X-16 方案稿 §九.2 落地验收：`DispatchRecord` 改**真 append**（`.jsonl`）—— DS 2026-09-18 拍。

前置核查（方案稿 §十.2 要求「先核是否有读方依赖『全量列表』语义」；本批已核）：
  **有** —— `core/pa/pa_core.py:115` 返回 `{"rows": self.dispatch_rec.rows}` ⇒
  `GET /v9/pa/dispatch/history`；既有用例 `tests/unit/test_pa_v1.py::test_dispatch_pass_with_stub`
  与 `tests/unit/test_pa_routes.py::test_dispatch_stub_pass` 都断言 `hist["rows"]`
  ⇒ `.jsonl` 改造**必须**保持 `rows` = **全量历史**（判据①②钉的就是这一条）。

判据（与「被判定的事」同层）：
 ① 全量语义：追加后 `rows` 是全量，**新会话重载**也读得到；
 ② 真 append：n 条记录 = 文件恰好 n 行（旧写法是整文件重写成缩进 JSON 数组）；
 ③ 坏行**不静默**：末行半截 ⇒ 其余历史保留 + `corrupt_lines == 1` + stderr 有报（不许当空历史）；
 ④ 结构判据（留 PA 侧）：缺 `task_id` ⇒ `add()` 抛且**不写**（fail-loud）；
 ⑤ 旧格式兼容：只有 `dispatch.json`（数组）时**只读**它；`add()` 后旧文件**逐字节不变**。
"""
from __future__ import annotations

import json

import pytest

from core.pa.dispatch import DispatchRecord


def test_append_keeps_full_history(tmp_path):
    """① 全量语义不丢：新会话重载后仍读到全部记录。"""
    p = tmp_path / "dispatch.jsonl"
    rec = DispatchRecord(p)
    rec.add({"task_id": "t1", "verdict": "pass"})
    rec.add({"task_id": "t2", "verdict": "reject"})
    assert [r["task_id"] for r in rec.rows] == ["t1", "t2"]
    assert [r["task_id"] for r in DispatchRecord(p).rows] == ["t1", "t2"]


def test_true_append_one_line_per_row(tmp_path):
    """② 真 append：n 条 = n 行（不再是「整文件重写」）。"""
    p = tmp_path / "dispatch.jsonl"
    rec = DispatchRecord(p)
    rec.add({"task_id": "a"})
    rec.add({"task_id": "b"})
    text = p.read_text(encoding="utf-8")
    assert text.count("\n") == 2 and text.endswith("\n")
    assert [json.loads(l)["task_id"] for l in text.splitlines()] == ["a", "b"]


def test_broken_line_reported_not_swallowed(tmp_path, capsys):
    """③ 坏行：跳过但计数 + 报 stderr；其余历史保留（绝不把损坏当空历史）。"""
    p = tmp_path / "dispatch.jsonl"
    rec = DispatchRecord(p)
    rec.add({"task_id": "ok1"})
    with open(p, "a", encoding="utf-8", newline="\n") as fh:
        fh.write('{"task_id": "trunc')          # 模拟崩溃留下的半行
    rec2 = DispatchRecord(p)
    assert [r["task_id"] for r in rec2.rows] == ["ok1"]
    assert rec2.corrupt_lines == 1
    assert "第 2 行不可解析" in capsys.readouterr().err


def test_add_refuses_row_without_task_id(tmp_path):
    """④ PA 侧业务结构判据：缺 task_id ⇒ 抛且不写。"""
    p = tmp_path / "dispatch.jsonl"
    rec = DispatchRecord(p)
    with pytest.raises(ValueError):
        rec.add({"verdict": "pass"})
    assert (not p.exists()) or p.read_bytes() == b""
    assert rec.rows == []


def test_legacy_json_read_only_not_rewritten(tmp_path):
    """⑤ 旧格式兼容：只读、不改写；历史连续（旧在前、新在后）。"""
    legacy = tmp_path / "dispatch.json"
    legacy.write_text(json.dumps([{"task_id": "old"}], ensure_ascii=False), encoding="utf-8")
    before = legacy.read_bytes()
    rec = DispatchRecord(tmp_path / "dispatch.jsonl")
    assert [r["task_id"] for r in rec.rows] == ["old"]
    rec.add({"task_id": "new"})
    assert legacy.read_bytes() == before
    assert [r["task_id"] for r in DispatchRecord(tmp_path / "dispatch.jsonl").rows] == ["old", "new"]