# -*- coding: utf-8 -*-
"""G-02 子项⑥ 续 验收：**证据不完整时把原始 stdout 落盘**（2026-09-18 · 老板/DS 拍「做」）。

背景（实测）：本批 5 次跑里 3 次命中「汇总 N / 解析 N-1」⇒ stale 误判 ⇒ 假红；但日志里只有
「差额 1」，**看不到那一行长什么样** ⇒ 机制无法定位（`raw_r10` 落盘原始 stdout 后才排除了一轮）。

判据：① 证据不完整 ⇒ 留存一件原始 stdout（内容一致）；② 滚动副本不存在 ⇒ 返回 None 且不抛；
③ 只保留最新 `_RAW_KEEP` 份（防堆积）；④ 留存**纯留痕**：判定（`bad`）不得引用 `gaps`/`_raw_kept`。
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
_TOOL = _REPO / "tools" / "check_test_baseline.py"


def _load():
    spec = importlib.util.spec_from_file_location("_cj_gate_keepraw", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seed(tmp_path, text="RAW-STDOUT-BODY\n"):
    (tmp_path / "raw_last.txt").write_text(text, encoding="utf-8")
    return tmp_path / "raw_last.txt"


def test_keeps_raw_when_evidence_incomplete(tmp_path, monkeypatch):
    """证据不完整 ⇒ 留存原始 stdout，内容与滚动副本一致。"""
    m = _load()
    monkeypatch.setattr(m, "_RUN_DIR", tmp_path)
    _seed(tmp_path, "RAW-STDOUT-BODY\nsecond line\n")
    kept = m._keep_raw_stdout(["parse_selfcheck"])
    assert kept, "未留存"
    p = pathlib.Path(kept) if pathlib.Path(kept).is_absolute() else _REPO / kept
    assert p.exists() and p.parent.name == "raw"
    assert p.read_text(encoding="utf-8") == "RAW-STDOUT-BODY\nsecond line\n"
    assert "parse_selfcheck" in p.name, "文件名要带理由（便于事后按名索引）"


def test_missing_rolling_copy_is_safe(tmp_path, monkeypatch):
    """没有滚动副本（异常路径）⇒ 返回 None，不抛异常（不得把门禁搞红）。"""
    m = _load()
    monkeypatch.setattr(m, "_RUN_DIR", tmp_path)
    assert m._keep_raw_stdout(["pytest_rc"]) is None


def test_prunes_to_newest_keep(tmp_path, monkeypatch):
    """只保留最新 `_RAW_KEEP` 份（文件名以时间戳开头 ⇒ 按名排序即按时间）。"""
    m = _load()
    monkeypatch.setattr(m, "_RUN_DIR", tmp_path)
    monkeypatch.setattr(m, "_RAW_KEEP", 2)
    d = tmp_path / "raw"
    d.mkdir(parents=True)
    for i in range(5):
        (d / ("20260101T00000%d_old.txt" % i)).write_text("x", encoding="utf-8")
    _seed(tmp_path)
    kept = m._keep_raw_stdout(["counts_short"])
    assert kept
    names = sorted(p.name for p in d.glob("*.txt"))
    assert len(names) == 2, names
    # 新增那份（时间戳最新，排序最后）+ 次新的一份留存
    assert names[-1].endswith("counts_short.txt"), names


def test_retention_is_wired_into_run_and_main():
    """静态判据：`_run_pytest` 落滚动副本；`main` 在 gaps 非空时调用留存并记账。"""
    src = _TOOL.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert "_run_pytest" in fns and "main" in fns
    run_src = ast.get_source_segment(src, fns["_run_pytest"])
    main_src = ast.get_source_segment(src, fns["main"])
    assert "raw_last.txt" in run_src, "滚动副本未落盘"
    assert "_keep_raw_stdout(gaps)" in main_src, "main 未在 gaps 非空时留存"
    assert "\"raw_stdout_kept\": _raw_kept," in main_src, "last_run.json 未记账留存路径"
    assert "\"evidence_gaps\": gaps," in main_src, "last_run.json 未记账漏因"


def test_retention_never_touches_verdict():
    """静态判据：留存**纯留痕** —— 判定（bad 列表）不得引用 gaps / _raw_kept / warnings。"""
    src = _TOOL.read_text(encoding="utf-8")
    tree = ast.parse(src)
    main = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    seg = ast.get_source_segment(src, main)
    assert "bad.append" in seg
    for line in seg.splitlines():
        if "bad.append" in line:
            for forbidden in ("gaps", "_raw_kept", "warnings", "raw_stdout"):
                assert forbidden not in line, "判定层引用了留痕口径: %s" % line
