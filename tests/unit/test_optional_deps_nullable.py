# -*- coding: utf-8 -*-
u"""净机之「可选之依」之齿（承 pm_1598 §二 令三 · 显式降级）。

由（pm_1598 §一 之第三层）：净机无 Postgres ／ Ollama ⇒ 包内 runtime ⛔ 有 `psycopg2` ／
  `ollama` ⇒ 其**顶层** `import` ⇒ `ModuleNotFoundError` 于**载入之刻** ⇒ 整机起不来。
故立规：**可选之依** 须 ⒜ 顶层导入**键**（try ／ except）⒝ 用点**显式降级**（⛔ AttributeError 混过）。

器取：`python -X utf8 -B -m pytest tests/unit/test_optional_deps_nullable.py -q`
"""
from __future__ import annotations

import ast
import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
#: 净机上「必无」之第三方 —— 本齿**屏**之 ⇒ 与开发机是否真装无关（决然 · ⛔ 假绿）
BLOCKED = (u"psycopg2", u"psycopg2.extras", u"psycopg2.pool", u"ollama")
NULLABLE = (u"core/lib/code_entity_extractor.py",
            u"core/lib/v8/feedback_collector.py",
            u"core/agents/builtin/self_upgrading_agent.py")

_PROBE = u'''
import sys
for n in {blocked!r}:
    sys.modules[n] = None          # ⇒ import 必 ImportError（⛔ 依本机真装与否）
sys.path.insert(0, {root!r})
import core.lib.code_entity_extractor as CE
assert CE.psycopg2 is None, CE.psycopg2
try:
    CE.ConnectionPool(u"postgresql://u:p@127.0.0.1:5432/db")
    print(u"FAIL_CONN_NO_RAISE")
except CE.DbUnavailable as e:
    print(u"CE_DB_UNAVAILABLE=%s" % e)
except Exception as e:
    print(u"FAIL_CONN_WRONG_EXC=%s" % type(e).__name__)
import core.lib.v8.feedback_collector as FC
assert FC.psycopg2 is None, FC.psycopg2
import core.agents.builtin.self_upgrading_agent as SU
assert SU.psycopg2 is None and SU.ollama is None, (SU.psycopg2, SU.ollama)
print(u"ALL_IMPORTS_OK")
'''


def _run_probe():
    line = _PROBE.format(blocked=BLOCKED, root=str(ROOT))
    r = subprocess.run([sys.executable, u"-X", u"utf8", u"-B", u"-c", line],
                       capture_output=True, text=True, encoding=u"utf-8",
                       errors=u"replace", cwd=str(ROOT), timeout=300)
    return r


def test_nullable_deps_import_without_the_lib():
    u"""⒈ 屏 `psycopg2` ／ `ollama` ⇒ 三件**仍可载**（⛔ ModuleNotFoundError）。"""
    r = _run_probe()
    out = r.stdout or u""
    assert u"ALL_IMPORTS_OK" in out, (r.returncode, out[-800:], (r.stderr or u"")[-800:])
    assert u"ModuleNotFoundError" not in (r.stderr or u""), (r.stderr or u"")[-800:]


def test_use_point_degrades_explicitly():
    u"""⒉ 用点之降级**显**（DbUnavailable · ⛔ AttributeError ／ ⛔ 静默）。"""
    r = _run_probe()
    out = r.stdout or u""
    assert u"CE_DB_UNAVAILABLE=" in out, (r.returncode, out[-800:])
    assert u"psycopg2 未安装" in out, out[-800:]
    assert u"FAIL_CONN_WRONG_EXC" not in out and u"FAIL_CONN_NO_RAISE" not in out, out[-800:]


def _module_level_imports(rel):
    u"""模块级（**无 try 护**）之导入之顶名（复 pm_1598 令三之器 · 同式）。"""
    tree = ast.parse(io.open(str(ROOT / rel), encoding=u"utf-8").read())
    out = set()

    def walk_body(node, in_try):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if not in_try:                      # ⛔ try 护者 ⇒ 正是**立规**所要之形
                if isinstance(node, ast.Import):
                    for a in node.names:
                        out.add(a.name.split(u".")[0])
                elif node.level == 0 and node.module:
                    out.add(node.module.split(u".")[0])
            return
        if isinstance(node, ast.Try):
            for b in node.body:
                walk_body(b, True)
            for h in node.handlers:
                for b in h.body:
                    walk_body(b, in_try)
            for b in list(node.orelse) + list(node.finalbody):
                walk_body(b, in_try)
            return
        if isinstance(node, (ast.If, ast.With, ast.For, ast.While)):
            for ch in ast.iter_child_nodes(node):
                walk_body(ch, in_try)

    for st in tree.body:
        walk_body(st, False)
    return out


def test_nullable_is_not_imported_at_module_level_unguarded():
    u"""⒊ 立规：三件之顶层**无** `psycopg2` ／ `ollama` 之裸导入（承「一处定形」）。"""
    bad = {}
    for rel in NULLABLE:
        hit = _module_level_imports(rel) & {u"psycopg2", u"ollama"}
        if hit:
            bad[rel] = sorted(hit)
    assert not bad, bad