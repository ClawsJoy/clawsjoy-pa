# -*- coding: utf-8 -*-
u"""pm_1628 §二.2 令二（版本元数据）之齿 —— 装根 `version.json` 之「一处定形」（技术总监席 f202f89 · 2026-10-07）。

一事：`version.json` ＝ `{version, commit, tree, built_at, channel}`（唯五键）；
  写方 ＝ `installer_post.py`（装时落 · 唯标准库）；读者 ＝ `core/lib/build_info.py`（端）；
  注册表 `DisplayVersion` 之真源 ＝ 此件（今为静态 `1.0` ⇒ 拔）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_version_1629.py -q

判据：
  ⒜ 写／读二方之「形」**一处**：`installer_post.version_payload()` 之键 ≡ `build_info.FIELDS`（⛔ 二处各写）
  ⒝ 正控：装根有 `pyproject.toml` ＋ 册 ⇒ 落 `version.json`，其 `version` ≡ `[project].version`，
     `commit ／ tree ／ built_at` 取册之「源」，`channel` 缺省 `internal`
  ⒞ 反控：干跑 ⇒ **⛔ 落件**（⛔ 动盘）
  ⒟ `DisplayVersion` ≡ `version.json.version`（⛔ 旧静态 `1.0`）
  ⒠ `build_info.report()`：未见 ／ 坏 ⇒ `available=False` ＋ **照实之因**（⛔ 静默 · ⛔ 充）
  ⒡ 端：`/health.build` 在 ∧ `GET /v9/pa/version` 出 `build` ＋ `source`（只读）
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(WPA) not in sys.path:
    sys.path.insert(0, str(WPA))


def _load(rel, name):
    u"""直接以文件载（⛔ 走包导入 —— 免 `core/__init__` 之重初始化）。"""
    spec = importlib.util.spec_from_file_location(name, str(ROOT / rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


BI = _load("core/lib/build_info.py", "_bi1629")
bi_mod = BI


def _mod(name):
    spec = importlib.util.spec_from_file_location("_m1629_" + name.replace(".", "_"), str(WPA / name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PYPROJECT = u'[project]\nname = "clawsjoy"\nversion = "3.4.5"\n'
MANIFEST = {
    u"version": 1,
    u"源": {"commit": "a" * 40, "tree": "b" * 40, "分支": "build/note-v1",
           u"刻": "2026-10-07T11:21:01+0800"},
    u"件之表": [],
}


def _tree(t, with_pyproject=True, with_manifest=True):
    os.makedirs(os.path.join(t, "runtime"), exist_ok=True)
    with io.open(os.path.join(t, "runtime", "python.exe"), "wb") as fh:
        fh.write(b"x")
    if with_pyproject:
        with io.open(os.path.join(t, "pyproject.toml"), "w", encoding="utf-8", newline=u"") as fh:
            fh.write(PYPROJECT)
    if with_manifest:
        with io.open(os.path.join(t, "bundle_manifest.json"), "w", encoding="utf-8", newline=u"") as fh:
            fh.write(json.dumps(MANIFEST, ensure_ascii=False))
    return t


def test_一处定形_写读二方之键同():
    u"""⒜：写方（installer_post）之键 ≡ 读方（build_info.FIELDS）—— 以器核（⛔ 人记）。"""
    m = _mod("installer_post.py")
    got = tuple(m.version_payload(str(ROOT)).keys())
    assert got == tuple(BI.FIELDS), (got, BI.FIELDS)
    assert tuple(bi_mod.FIELDS) == tuple(BI.FIELDS)
    assert m.VERSION_JSON == BI.FILENAME, (m.VERSION_JSON, BI.FILENAME)


def test_正控_落件且逐键合():
    u"""⒝：正控 —— 装根有 pyproject ＋ 册 ⇒ 落 `version.json` ∧ 逐键合（⛔ 本机之时）。"""
    t = tempfile.mkdtemp(prefix="cjpa_ver1629_")
    try:
        _tree(t)
        m = _mod("installer_post.py")
        m.write_version_json(t)
        p = os.path.join(t, m.VERSION_JSON)
        assert os.path.isfile(p), u"⛔ 落 version.json"
        d = json.loads(io.open(p, encoding="utf-8").read())
        assert tuple(d) == tuple(BI.FIELDS), tuple(d)
        assert d[u"version"] == u"3.4.5", d
        assert d[u"commit"] == u"a" * 40 and d[u"tree"] == u"b" * 40, d
        assert d[u"built_at"] == u"2026-10-07T11:21:01+0800", d
        assert d[u"channel"] == u"internal", d
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_反控_干跑不落件():
    u"""⒞：反控 —— `dry=True` ⇒ **⛔ 落件**（⛔ 动盘）。"""
    t = tempfile.mkdtemp(prefix="cjpa_ver1629d_")
    try:
        _tree(t)
        m = _mod("installer_post.py")
        m.write_version_json(t, dry=True)
        assert not os.path.isfile(os.path.join(t, m.VERSION_JSON)), u"干跑竟落了件"
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_反控_无pyproject则明书兜底():
    u"""反控：⛔ 见 pyproject ⇒ `version` 走兜底 ∧ **明书其由**（⛔ 静默 · ⛔ 假读数）。"""
    t = tempfile.mkdtemp(prefix="cjpa_ver1629n_")
    try:
        _tree(t, with_pyproject=False)
        m = _mod("installer_post.py")
        v, why = m.pkg_version(t)
        assert v == m.TOOL_VERSION and u"兜底" in why, (v, why)
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_正控_DisplayVersion取version_json():
    u"""⒟：注册表 `DisplayVersion` ≡ `version.json.version`（⛔ 旧静态 `1.0`）。"""
    t = tempfile.mkdtemp(prefix="cjpa_ver1629v_")
    try:
        _tree(t)
        m = _mod("installer_post.py")
        m.write_version_json(t)
        vals = {k: v for k, _t, v in m.uninstall_values(t)}
        assert vals[u"DisplayVersion"] == u"3.4.5", vals[u"DisplayVersion"]
        assert vals[u"DisplayVersion"] != m.TOOL_VERSION or m.TOOL_VERSION == u"3.4.5"
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_读者_未见与坏皆照实报():
    u"""⒠：`build_info.report()` 未见 ／ 坏 ⇒ `available=False` ＋ 因（⛔ 静默 · ⛔ 充）。"""
    t = tempfile.mkdtemp(prefix="cjpa_ver1629r_")
    try:
        r = BI.report(t)
        assert r[u"available"] is False and r[u"note"], r
        assert all(r[k] is None for k in BI.FIELDS), r
        with io.open(os.path.join(t, BI.FILENAME), "w", encoding="utf-8", newline=u"") as fh:
            fh.write(u"{not json")
        d, note = BI.read(t)
        assert d is None and (u"读取败" in note), note
        # 正控：好件 ⇒ available True ∧ 逐键
        with io.open(os.path.join(t, BI.FILENAME), "w", encoding="utf-8", newline=u"") as fh:
            fh.write(json.dumps({k: "x" for k in BI.FIELDS}))
        r2 = BI.report(t)
        assert r2[u"available"] is True and r2[u"version"] == u"x", r2
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_端_health有build():
    u"""⒡：`/health` 出 `build`（一处定形之读者 · ⛔ 另算）。"""
    from flask import Flask
    from core.routes.system_routes import system_bp
    app = Flask(__name__)
    app.register_blueprint(system_bp)
    d = app.test_client().get("/health").get_json()
    assert u"build" in d and d[u"build"][u"available"] in (True, False), d.get(u"build")
    assert d[u"version"], d


def test_端_v9_pa_version出build与source():
    u"""⒡：`GET /v9/pa/version` ⇒ `build` ＋ `source`（只读 · ⛔ 密钥 ／ ⛔ 用户数据）。"""
    from flask import Flask
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app, brain=None)
    r = app.test_client().get("/v9/pa/version")
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    assert d[u"ok"] is True and u"build" in d and u"source" in d, d
    s = d[u"source"]
    assert s[u"url"].startswith(u"http") and s[u"channel"] and s[u"provider"], s
    assert d[u"manifest_url"].endswith(u"/update_manifest.json"), d[u"manifest_url"]
    blob = json.dumps(d, ensure_ascii=False)
    for bad in (u"api_key", u"API_KEY", u"sk-"):
        assert bad not in blob, u"版本面竟含密钥之影：%s" % bad


def test_反控_installer_post不引core():
    u"""反控：写方**唯标准库**（净机之 runtime ⛔ 引 core —— 本器于装根以自带 python 跑）。"""
    import ast as _ast
    src = io.open(str(WPA / "installer_post.py"), encoding="utf-8").read()
    mods = set()
    for n in _ast.walk(_ast.parse(src)):
        if isinstance(n, _ast.Import):
            mods |= {a.name.split(u".")[0] for a in n.names}
        elif isinstance(n, _ast.ImportFrom) and n.module and n.level == 0:
            mods.add(n.module.split(u".")[0])
    extra = sorted(m for m in mods if m not in set(sys.stdlib_module_names))
    assert extra in ([], [u"installer_post"], [u"install_win_pa"]), extra
