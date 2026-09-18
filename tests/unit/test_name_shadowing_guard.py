# -*- coding: utf-8 -*-
"""X-22 防回潮（**结构判据**）：类内「方法名 ∩ 实例属性名」必须为空。

背景（X-22 · 2026-09-18 落地）：`core/lib/llm_client.py::LLMClient._init` 里
`self._ollama_available = False` 把同类 `def _ollama_available(self, timeout)` **盖住**
（同名遮蔽）⇒ `:256` 的 `if self._ollama_available():` 恒抛
`TypeError: 'bool' object is not callable`，被外层 `except Exception` 误归因为
「云端 API 不可用，降级到 Ollama」⇒ #24「首Token优先」恒不可达，且每次都被记成外部故障。
DS 2026-09-18 拍：**属性改名**（`self._ollama_available` → `self._ollama_probe_ok`），
方法名保留，单独成批。

判据形态是**结构**（AST）而非字面量 ⇒ 它同时管住三件事：
  ① 新增遮蔽 ⇒ 红（本次这类缺陷不得再出现）；
  ② 陈旧豁免 ⇒ 红（基线条目已不复现时必须删条目，不能留成噪声）；
  ③ 判据空转 ⇒ 红（扫描量 / 类数下限断言）。
基线留痕：`tests/baseline/name_shadowing_baseline.json`（每条含落点、观测、状态）。
"""
import ast
import json
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[2]
_SCAN_ROOTS = ("core", "tools", "scripts")
_SKIP_DIRS = {"__pycache__", ".git", "node_modules", "data", ".venv", "venv", "build", "dist"}
_BASELINE = _REPO / "tests" / "baseline" / "name_shadowing_baseline.json"


def _scan():
    """扫生产代码里的同名遮蔽。返回 (found_keys, stats, unparseable)。"""
    files = []
    for rel in _SCAN_ROOTS:
        for path in (_REPO / rel).rglob("*.py"):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
    files.sort()
    found = []
    unparseable = []
    classes = 0
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as exc:  # noqa: PERF203
            unparseable.append("%s: %s" % (path.relative_to(_REPO).as_posix(), exc))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            classes += 1
            methods = {
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            attrs = set()
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for sub in ast.walk(item):
                    target = None
                    if isinstance(sub, ast.Assign) and len(sub.targets) == 1:
                        target = sub.targets[0]
                    elif isinstance(sub, ast.AnnAssign):
                        target = sub.target
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        attrs.add(target.attr)
            for name in sorted(methods & attrs):
                found.append(
                    "%s :: %s.%s"
                    % (path.relative_to(_REPO).as_posix(), node.name, name)
                )
    return found, {"files": len(files), "classes": classes}, unparseable


def _baseline():
    return json.loads(_BASELINE.read_text(encoding="utf-8"))


def test_无新增同名遮蔽():
    """① 新遮蔽 = 红；同时断言扫描量下限（防判据空转）。"""
    found, stats, unparseable = _scan()
    assert unparseable == [], "生产 .py 必须能被 AST 解析（解析失败本身就是红）：%s" % unparseable
    assert stats["files"] >= 500, "扫描文件数过少 ⇒ 判据可能空转：%s" % stats
    assert stats["classes"] >= 400, "扫描类数过少 ⇒ 判据可能空转：%s" % stats
    allowed = {entry["key"] for entry in _baseline()["entries"]}
    new = sorted(set(found) - allowed)
    assert new == [], (
        "出现新的同名遮蔽（方法名被实例属性盖住 ⇒ 调用恒抛或静默取到 truthy 属性）：%s\n"
        "修法二选一：属性改名 或 方法改名；确需豁免则登记进 %s 并写明状态。"
        % (new, _BASELINE.relative_to(_REPO).as_posix())
    )


def test_基线无陈旧豁免():
    """② 陈旧豁免 = 红：条目已不复现却留着，基线会变成噪声掩体。"""
    found, _stats, _unparseable = _scan()
    stale = sorted({entry["key"] for entry in _baseline()["entries"]} - set(found))
    assert stale == [], "基线里的豁免已不再复现，必须删条目：%s" % stale


def test_基线条目字段完备且键自洽():
    """③ 基线条目必须能定位（path/class/name 拼出的 key 与 key 字段一致）。"""
    entries = _baseline()["entries"]
    assert entries, "基线不得为空而无说明（空则写空列表）"
    for entry in entries:
        for field in ("id", "key", "path", "class", "name", "severity", "observed", "status"):
            assert entry.get(field), "条目缺字段 %s：%s" % (field, entry.get("id"))
        assert entry["key"] == "%s :: %s.%s" % (entry["path"], entry["class"], entry["name"]), (
            "条目 key 与 path/class/name 不自洽：%s" % entry["id"]
        )


def test_基线声明的扫描范围与判据一致():
    """④ 防悄悄缩范围：基线的 scan_scope 必须等于判据实际扫描根。"""
    assert tuple(_baseline()["scan_scope"]) == _SCAN_ROOTS, (
        "基线 scan_scope 与判据扫描范围不一致（改范围必须同时改判据，且要说明理由）"
    )
