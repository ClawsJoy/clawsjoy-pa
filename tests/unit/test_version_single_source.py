# -*- coding: utf-8 -*-
u"""版号之「一处定形」之测（承 pm_1384 §三.5）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_version_single_source.py -q

判据：
  ⒈ `core/lib/version.py` 之 `__version__` ≡ `pyproject.toml[project].version`
  ⒉ **活面**（`routes/static.py` 注册之 `/`）所报 version ≡ `__version__`
  ⒊ 三档（`routes/static.py` ／ `core/web/health.py` ／ `core/routes/system_routes.py`）
     ⛔ 再书版号字面（旧字面 ⇒ 拔）
  ⒋ **反控**：扫描器喂植入之假字面 ⇒ 必逮（⛔ 无齿之闸 ＝ 假绿）
"""
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib.version import SERVICE_NAME, __version__, service_info  # noqa: E402

#: 版号「字面」之三档（真源之候选；旧为各自硬编）
_VER_SITE = ("routes/static.py", "core/web/health.py", "core/routes/system_routes.py")

#: 「报告之版号字面」之形 —— `"version": "6.0.0"` 类（值以数字起）
_LIT_RE = re.compile(r'["\']version["\']\s*:\s*["\']([0-9][^"\']*)["\']')


def _literals(src):
    u"""报体里之版号字面（反控之的：把假字面喂进来 ⇒ 须逮）。"""
    return _LIT_RE.findall(src)


def _src(rel):
    return io.open(str(ROOT / rel), encoding="utf-8", errors="replace").read()


def test_pyproject_version_matches_module():
    u"""包版（真源之一）≡ 模块（真源之二）—— 二源分歧即此测红。"""
    txt = io.open(str(ROOT / "pyproject.toml"), encoding="utf-8").read()
    blk = re.search(r"^\[project\]\s*$(.*?)(?=^\[|\Z)", txt, re.S | re.M)
    assert blk, "pyproject.toml 无 [project] 块"
    m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', blk.group(1), re.M)
    assert m, "[project] 无 version"
    assert m.group(1) == __version__, (m.group(1), __version__)


def test_service_info_shape():
    assert service_info() == {"service": SERVICE_NAME, "version": __version__}


def test_live_root_reports_single_source():
    u"""活面：本档注册之 `/` 所报 ≡ 真源（⛔ 只看源码 · 须真跑一次）。"""
    from flask import Flask

    from routes.static import bp as static_bp

    app = Flask(__name__)
    app.register_blueprint(static_bp)
    app.config["TESTING"] = True
    resp = app.test_client().get("/")
    assert resp.status_code == 200
    assert resp.get_json() == {"service": SERVICE_NAME, "version": __version__}, resp.get_json()


def test_no_version_literal_in_sites():
    for rel in _VER_SITE:
        got = _literals(_src(rel))
        assert got == [], (rel, got)


def test_detector_has_teeth():
    u"""反控：植入一假字面 ⇒ 扫描器必逮（⛔ 无齿）。"""
    fake = 'return jsonify({"service": "X", "version": "6.0.0"})'
    assert _literals(fake) == ["6.0.0"], "反控失败：植入之假字面未被逮"
    assert _literals('return jsonify({"service": "X", "version": __version__})') == []
