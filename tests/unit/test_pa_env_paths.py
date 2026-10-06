# -*- coding: utf-8 -*-
"""⭐ 件④ ⓐⓑ 之测（承 pm_1366 §三 验收三测 一）：一处出径之绝对 ∧ shim 自 NPM_GLOBAL 推（反控）∧ ⛔ 字面硬编。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_env_paths.py -q
"""
import ast
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import env_face as E  # noqa: E402

_ENV = None


def _env():
    global _ENV
    if _ENV is None:
        _ENV = E.build_env()
    return _ENV


def test_ws_root_is_abs_str(monkeypatch):
    """ws_root 一处出径（承 pm_1366 §三 ⓐ）：env PA_WS_ROOT ⇒ 绝对；缺（∧ tools 缺）⇒ None ＋ 源述「未接」。

    ⚠ 承 pm_1399 §二.3（批一）：组织物（`_tools` 之父）已切出 ⇒ 本机缺 env 时 ws_root 可為
    ``None``（四态之「未接（组织版）」）—— 本测须认之（⛔ 以「恒为绝对」为契）。
    """
    fake = os.path.join(os.path.abspath(os.sep), "tmp", "ws_root_probe")
    monkeypatch.setenv("PA_WS_ROOT", fake)
    ws = E.build_env().get("ws_root")
    assert isinstance(ws, str) and os.path.isabs(ws), ws
    monkeypatch.delenv("PA_WS_ROOT", raising=False)
    v, src = E.resolve_ws_root({"tools": None})
    assert v is None and "未接" in str(src), (v, src)


def test_paths_keys_contract():
    assert set(_env()["paths"].keys()) == set(E.PATH_KEYS)


def test_paths_all_absolute_or_none():
    for k, v in _env()["paths"].items():
        if v is None:
            continue
        assert isinstance(v, str) and os.path.isabs(v), (k, v)


def test_none_path_has_src_noted():
    """⭐ 径为 None ⇒ 其源述须明书「未接」（⛔ 以字面兜底 —— 承 pm_1366 §三）。"""
    e = _env()
    for k, v in e["paths"].items():
        if v is None:
            assert "未接" in str(e["paths_src"].get(k) or ""), (k, e["paths_src"].get(k))


def test_shim_files_derived_from_npm_global(monkeypatch):
    """⭐ shim 皆自 NPM_GLOBAL 推；反控：改 PA_NPM_GLOBAL ⇒ 果变（⛔ 假反控）。"""
    fake = os.path.join("X:", "no-such-npm")
    monkeypatch.setenv("PA_NPM_GLOBAL", fake)
    a = [f["path"] for f in E.allowlist()["files"] if "shim" in f["label"]]
    assert [os.path.basename(x) for x in a] == [n + ".CMD" for n in E.SHIM_NAMES], a
    assert all(os.path.normcase(os.path.dirname(x)) == os.path.normcase(fake) for x in a), a
    monkeypatch.delenv("PA_NPM_GLOBAL", raising=False)
    b = [f["path"] for f in E.allowlist()["files"] if "shim" in f["label"]]
    assert b != a, (a, b)


def test_units_only_from_resolved_drives():
    """⭐ units 自 _drive_letters() 出（⛔ 字面盘符 ⇒ 净机报一不存在之盘）。"""
    letters = set(E._drive_letters())
    for u in E.allowlist()["units"]:
        assert u["unit"].split(":")[1] in letters, u


def test_source_has_no_hardcoded_npm_global_or_drives():
    src = io.open(E.__file__, encoding="utf-8", newline="").read()
    assert 'for d in "CD"' not in src
    needle = "npm-global" + chr(92)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert needle not in node.value, node.value
