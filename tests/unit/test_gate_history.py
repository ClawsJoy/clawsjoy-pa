# -*- coding: utf-8 -*-
"""P1 验收：门禁的**只追加**历史 `gate_history.jsonl`（2026-09-18 · 老板/DS 拍「做」）。

背景（只读审计结论 `codex/2026-09-18-g02-parse-miss-telemetry-coverage-audit.md`）：
子项⑥ 的字段其实已经齐了（`evidence_gaps` 里就是结构化 token），但 `last_run.json`
每跑**覆盖**、`data/` 又被 gitignore ⇒ **不留历史** ⇒「漏解析率 / 末行异常率」
**没有分母**，攒不出「率」。

判据：① 每跑 append **一行** JSONL（字段齐、不覆盖）；② 超过 `_HIST_KEEP` 只保留最新
（防无限增长）；③ **纯留痕** —— 判定（`bad`）不得引用历史口径，且落盘必须被 try 兜住
（失败只记 warnings，**不红门禁**）。
"""
from __future__ import annotations

import ast
import importlib.util
import json
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
_TOOL = _REPO / "tools" / "check_test_baseline.py"


def _load():
    spec = importlib.util.spec_from_file_location("_cj_gate_history", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_appends_one_jsonl_line_with_required_fields(tmp_path, monkeypatch):
    """每跑 append **一行**；字段齐；**不覆盖**旧行（append-only）。"""
    m = _load()
    monkeypatch.setattr(m, "_RUN_DIR", tmp_path)
    rec = {"ts": "2026-09-18T08:00:00", "evidence_gaps": [], "summary_off_last_line": False,
           "pytest_rc": 1, "collected": 1851, "counts": {"failed": 25, "passed": 1818},
           "reported_pass": True}
    m._append_history(rec)
    m._append_history(dict(rec, evidence_gaps=["parse_selfcheck", "parse_miss"],
                           reported_pass=False))
    p = tmp_path / "gate_history.jsonl"
    assert p.exists(), "历史未落盘"
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, lines                      # 只追加 ⇒ 不覆盖
    assert json.loads(lines[0]) == rec
    assert json.loads(lines[1])["evidence_gaps"] == ["parse_selfcheck", "parse_miss"]
    assert json.loads(lines[1])["reported_pass"] is False


def test_history_caps_to_newest_keep(tmp_path, monkeypatch):
    """超过 `_HIST_KEEP` 行只保留最新（防无限增长），且新行在末尾。"""
    m = _load()
    monkeypatch.setattr(m, "_RUN_DIR", tmp_path)
    monkeypatch.setattr(m, "_HIST_KEEP", 3)
    p = tmp_path / "gate_history.jsonl"
    p.write_text("".join('{"n": %d}\n' % i for i in range(5)), encoding="utf-8")
    m._append_history({"n": 5})
    got = [json.loads(x)["n"] for x in p.read_text(encoding="utf-8").splitlines()]
    assert got == [3, 4, 5], got


def test_history_is_pure_telemetry_and_wired():
    """静态判据：接线到 main；落盘被 try 兜住；判定层不得引用留痕口径。"""
    src = _TOOL.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert "_append_history" in fns, "未定义 _append_history"
    seg = ast.get_source_segment(src, fns["main"])
    assert "_append_history(" in seg, "main 未落历史"
    assert '"history_kept": _hist_kept,' in seg, "last_run.json 未记账历史路径"
    assert "except Exception" in seg, "落盘未被 try 兜住（失败会红门禁）"
    for line in seg.splitlines():
        if "bad.append" in line:
            for forbidden in ("gaps", "_raw_kept", "warnings", "raw_stdout",
                              "_hist_kept", "history"):
                assert forbidden not in line, "判定层引用了留痕口径: %s" % line
