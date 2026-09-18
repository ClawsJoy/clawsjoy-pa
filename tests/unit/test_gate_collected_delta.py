# -*- coding: utf-8 -*-
"""G-02 子项④ · 档 A 验收：收集数**变化量**纯留痕。

背景（2026-09-18 · 老板/DS 拍「先 A 后 C、不上 B」；方案稿
``codex/2026-09-18-g02-sub4-collect-baseline-plan.md`` §五）：
``collected``（收集数）此前只有**现值**、没有**变化量** ⇒ 「静默减少」这一路只能人肉对账。
本档只把「与上一跑之差」变成**可对账的数**；**不上判定**（档 C 待攒够「合法收缩」分母再拍）、
**明确不上档 B**（下降即 WARN ＝假警报）。

判据：
① 纯函数 ``_collected_delta(prev, cur)`` = ``cur - prev``（下降 ⇒ 负）；任一不可用 ⇒ ``None``（**不编数**）；
② 前值只读门禁**自己**的上一份快照 ``last_run.json``，**不得读** ``gate_history.jsonl``
   （P1 自定口径：历史文件**不读、不判**）—— 用静态判据钉住；
③ **纯留痕**：判定层（``bad``）不得引用本档口径；不得产生 WARN。
"""
from __future__ import annotations

import ast
import importlib.util
import json
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
_TOOL = _REPO / "tools" / "check_test_baseline.py"


def _load():
    spec = importlib.util.spec_from_file_location("_cj_gate_collected_delta", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_delta_is_signed_difference(tmp_path):
    m = _load()
    assert m._collected_delta(1856, 1874) == 18
    assert m._collected_delta(1874, 1856) == -18   # 下降**如实为负**（本档只留痕，不报警）
    assert m._collected_delta(1874, 1874) == 0


def test_delta_is_none_when_side_unusable():
    m = _load()
    assert m._collected_delta(None, 100) is None    # 首次跑：无前值 ⇒ null，不编数
    assert m._collected_delta(100, None) is None    # 本轮解析不出 ⇒ 不编数
    assert m._collected_delta(True, 5) is None      # bool 不是计数（Python 里 True == 1）
    assert m._collected_delta("100", 5) is None
    assert m._collected_delta(100.0, 5) is None


def test_prev_collected_reads_own_snapshot(tmp_path):
    m = _load()
    assert m._read_prev_collected(tmp_path) is None                       # 缺文件（首跑）
    p = tmp_path / "last_run.json"
    p.write_text("{ not json", encoding="utf-8")
    assert m._read_prev_collected(tmp_path) is None                       # 坏文件**不抛**
    p.write_text(json.dumps({"counts": {}}), encoding="utf-8")
    assert m._read_prev_collected(tmp_path) is None                       # 无 collected 键
    p.write_text(json.dumps({"collected": 1947}), encoding="utf-8")
    assert m._read_prev_collected(tmp_path) == 1947
    p.write_text(json.dumps({"collected": True}), encoding="utf-8")
    assert m._read_prev_collected(tmp_path) is None


def test_wired_stays_telemetry_and_never_reads_history():
    """静态判据：接线到 main 两处写入；判定层不引用；**前值不得取自 gate_history.jsonl**。"""
    src = _TOOL.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    for name in ("_collected_delta", "_read_prev_collected"):
        assert name in fns, "未定义 %s" % name

    seg = ast.get_source_segment(src, fns["main"])
    assert "_collected_delta(" in seg, "main 未计算收集数变化量"
    assert seg.count(u'"collected_delta": _delta_collected,') == 2, \
        "collected_delta 必须同时进 gate_history 行与 last_run.json"
    for line in seg.splitlines():
        if "bad.append" in line:
            for forbidden in ("_delta_collected", "collected_delta", "_prev_collected"):
                assert forbidden not in line, "判定层引用了留痕口径: %s" % line
        if "_delta_collected" in line:
            assert "WARN" not in line, "档 A 不得产生 WARN: %s" % line

    # 只判**代码**、不判注释/docstring：naive 子串判据会被本函数 docstring 里
    # 「**不读** gate_history.jsonl」这句解释命中（判据形状必须匹配缺陷形状 · L-23）。
    node = fns["_read_prev_collected"]
    body = [n for n in node.body
            if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str))]
    code_lines = []
    for n in body:
        for ln in (ast.get_source_segment(src, n) or "").splitlines():
            if not ln.strip().startswith("#"):
                code_lines.append(ln)
    code = "\n".join(code_lines)
    assert "last_run.json" in code, "前值未取自 last_run.json"
    assert "gate_history" not in code, \
        "前值来源不得读 gate_history.jsonl（P1 口径：历史文件不读、不判）"
