# -*- coding: utf-8 -*-
"""G-02 子项⑤ 验收：门禁「漏解析自检」**只告警**（2026-09-18）。

背景（实测）：首跑 ``counts.failed=25`` 但只解析到 24 条 nodeid ⇒ 漏解析那条被误判成
「台账陈旧」⇒ **假红**。修法只加告警，**判定层/退出码一行未动**。

判据：①口径一致 ⇒ **不报警**（防假警报）；②不一致 ⇒ 报出差额；③无法判定但名单非空 ⇒ 提醒。
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
_TOOL = _REPO / "tools" / "check_test_baseline.py"


def _load():
    spec = importlib.util.spec_from_file_location("_cj_gate_selfcheck", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_consistent_counts_do_not_warn():
    """一致 ⇒ None（**不报假警报**：正常跑 25 failed / 25 条 nodeid）。"""
    m = _load()
    assert m._parse_selfcheck({"failed": 25, "passed": 1756}, ["a::x"] * 25) is None
    assert m._parse_selfcheck({"failed": 0, "passed": 3}, []) is None
    # errors 也算进同一口径（pytest 把收集期错误单列）
    assert m._parse_selfcheck({"failed": 1, "errors": 1}, ["a::x", "b::y"]) is None


def test_parse_miss_warns_with_delta():
    """漏解析 ⇒ 报差额（这是本轮实测到的假红形态）。"""
    m = _load()
    w = m._parse_selfcheck({"failed": 25, "passed": 10}, ["a::x"] * 24)
    assert w and "25" in w and "24" in w and "差额 1" in w


def test_unjudgeable_but_nonempty_warns():
    """汇总行缺失但确实解析到失败 ⇒ 提醒（不静默）。

    子项⑥ 修法 A（汇总口径改为「全文取最后一条汇总行」）后，`counts` 为空
    **只可能**是「全文都找不到汇总行」 ⇒ 文案随之由「末行汇总里没有」
    改为「全文都没有」（避免与修法 A 后的实际语义脱节）。
    """
    m = _load()
    assert m._parse_selfcheck({}, []) is None
    w = m._parse_selfcheck({}, ["a::x"])
    assert w and "汇总形态异常" in w


def test_selfcheck_never_touches_verdict():
    """静态判据：自检只进 warnings，**不改 bad / 退出码**。"""
    tree = ast.parse(_TOOL.read_text(encoding="utf-8"))
    src = _TOOL.read_text(encoding="utf-8")
    # 自检的调用点必须是把结果 append 进 warnings
    assert "warnings.append(_selfcheck)" in src
    # main() 里不得出现「用自检结果改 bad」的写法
    main = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert main, "未找到 main"
    seg = ast.get_source_segment(src, main[0])
    assert "_selfcheck" in seg
    for bad in ("bad.append(_selfcheck", "sys.exit(2)", "return 2"):
        assert bad not in seg, "自检影响了判定/退出码：%s" % bad


def test_parse_selfcheck_kind_splits_two_forms():
    """P3（2026-09-18 拍）：两种子形态**分开标记**；口径一致时不标记（防假警报）。

    为什么: 「汇总形态异常」若与「真漏解析」共用一个 token，(b) 会被误计入 (a) 的分子。
    """
    m = _load()
    # (a) 差额型 —— 真漏解析
    assert m._parse_selfcheck_kind({"failed": 25, "passed": 10}, ["a::x"] * 24) == "parse_miss"
    # (b) 汇总形态异常型 —— 全文无计数但解析到失败
    assert m._parse_selfcheck_kind({}, ["a::x"]) == "counts_form_anomaly"
    # 一致 / 无失败 ⇒ 不标记
    assert m._parse_selfcheck_kind({"failed": 25, "passed": 1756}, ["a::x"] * 25) is None
    assert m._parse_selfcheck_kind({"failed": 1, "errors": 1}, ["a::x", "b::y"]) is None
    assert m._parse_selfcheck_kind({}, []) is None


def test_gaps_carry_parent_and_child_tokens():
    """静态判据：`gaps` 同时带**父标记**（旧 `in` 判据不失效）与**子标记**（分口径可数）。

    若只拆子 token、不留父标记 ⇒ 旧的 `"parse_selfcheck" in evidence_gaps` **静默失效**。
    """
    src = _TOOL.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    seg = ast.get_source_segment(src, fns["main"])
    assert 'gaps.append("parse_selfcheck")' in seg, "父标记丢失（旧判据会静默失效）"
    assert "_parse_selfcheck_kind(counts, failed)" in seg, "子口径未接线"
    assert "gaps.append(_selfcheck_kind)" in seg, "子标记未落入 gaps"
