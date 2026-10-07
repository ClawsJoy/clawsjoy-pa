# -*- coding: utf-8 -*-
u"""pm_1645 §二 令一（甲-P0）之齿 —— 增量包之二器 ＋ `/health.update` 键（技术总监席 f202f89 · 2026-10-07）。

一事：把「本批之小修」从建机送到用户机（`534.3 MB` ⟷ `≈ 0.6 MB`）。
  其**形**唯 `core/lib/update_manifest.py` 一处定形；造归 `scripts/win_pa/make_update.py`；
  应用归 `scripts/win_pa/pa_update.py`；读数归 `core/lib/update_check.py`（`/health.update`）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_update_1645.py -q

判据：
  M1 正控：清单之形（唯五键 ＋ 逐件四键）⇒ 合
  M2 反控：`sha256` 非 hex64 ／ `path` 越界 ／ 多键 ／ 缺键 ／ `del` 之 sha ／ `size` 负 ⇒ ⛔ 合
  M3 正反控：`bad_path`（`..` ／ 盘符 ／ 反斜杠 ／ 空段）
  M4 正控：`totals`（`del` ⛔ 计字节 · 三类各计）
  M5 一处定形：`digest` 稳（canonical 键序定 ⇒ 同料同印）
  U1 正控：`face()` 未查 ⇒ `available=False` ∧ `note` 明书「未查」（⛔ 静默）
  U2 正控：`refresh()` 以本机临端之静态面 ⇒ 有新版（`available` ／ `latest_version` ／ `files` ／ `size_bytes`）
  U3 正控：同版 ⇒ `note` ＝「已是最新」∧ `available=False`
  U4 反控：通道 ⛔ 合 ⇒ 明书「⛔ 跨档」∧ `available=False`
  U5 反控：源不可达 ⇒ `available=False` ∧ `note` ／ `note_why` 皆非空 ∧ ⛔ 抛
  U6 结构齿：态 ／ 备份之落处 ⛔ 入装根之 `data/`（唯 LOCALAPPDATA 之 ClawsJoyPA/update）
  U7 结构齿：`face()` **唯读盘**（⛔ 调 `refresh` ／ `fetch` —— 「只读之窗」）
  P1 正反控：二器之 `never()`（`config/.env` ／ `data/` ／ 常件）
  P2 正控 ＋ 反控：`pa_update.verify_all`（印合 ⇒ 过 ／ 印 ⛔ 合 ／ 缺件 ⇒ ⛔ 落）
  P3 正控：`/health` 顶键含 `update`（一处读数 —— ⛔ 新端）
  P4 反控：清单若含 `data/` 之件 ⇒ 应用器**拒**（承 pm_1620 §三.8 之铁律）
  P5 正控：`make_update.plan` 之尺（⛔ 入 `tests/**` ／ `data/**` ∧ 逐件形合）
"""
from __future__ import annotations

import ast
import copy
import functools
import http.server
import json
import os
import socketserver
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "scripts" / "win_pa")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.lib import update_check as UC  # noqa: E402
from core.lib import update_manifest as UM  # noqa: E402
import make_update as MU  # noqa: E402
import pa_update as PU  # noqa: E402


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):  # noqa: D102 — 静音（试之噪）
        pass


class _A(object):
    u"""`argparse.Namespace` 之极小替（供直呼 `pa_update.run`）。"""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def _man_ok():
    return {
        u"version": u"9.0.1",
        u"base_version": u"9.0.0",
        u"channel": u"internal",
        u"built_at": u"2026-10-07T00:00:00+0800",
        u"files": [
            {u"path": u"core/a.py", u"sha256": u"a" * 64, u"size": 3, u"mode": u"add"},
            {u"path": u"core/b.py", u"sha256": u"b" * 64, u"size": 4, u"mode": u"mod"},
            {u"path": u"core/c.py", u"sha256": u"", u"size": 0, u"mode": u"del"},
        ],
    }


def _serve(tmp_path, doc, name=u"update_manifest.json"):
    u"""本机临端之静态面（⛔ 赖公网）—— 落清单 ⇒ 以 HTTP 供之。"""
    (tmp_path / name).write_text(json.dumps(doc, ensure_ascii=False), encoding=u"utf-8")
    handler = functools.partial(_Quiet, directory=str(tmp_path))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, u"http://127.0.0.1:%d/" % httpd.server_address[1]


def _root(tmp_path, version=None):
    r = tmp_path / u"root"
    r.mkdir(exist_ok=True)
    if version:
        (r / u"version.json").write_text(json.dumps({
            u"version": version, u"commit": u"c", u"tree": u"t",
            u"built_at": u"2026-10-07T00:00:00+0800", u"channel": u"internal"}),
            encoding=u"utf-8")
    return r


def _env(tmp_path, url):
    return {u"LOCALAPPDATA": str(tmp_path / u"la"), u"PA_UPDATE_URL": url}


def _func(path, name):
    tree = ast.parse(path.read_text(encoding=u"utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(u"未见函数 %s@%s" % (name, path))


def _calls(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                out.add(f.attr)
            elif isinstance(f, ast.Name):
                out.add(f.id)
    return out


def test_M1_清单形合():
    ok, probs = UM.validate(_man_ok())
    assert ok, probs


def test_M2_反控_清单诸瑕():
    b = copy.deepcopy(_man_ok()); b[u"files"][0][u"sha256"] = u"XYZ"
    bad_sha = b
    b = copy.deepcopy(_man_ok()); b[u"files"][0][u"path"] = u"../evil"
    bad_path = b
    b = copy.deepcopy(_man_ok()); b[u"files"][0][u"extra"] = 1
    extra_key = b
    b = copy.deepcopy(_man_ok()); del b[u"channel"]
    missing_key = b
    b = copy.deepcopy(_man_ok()); b[u"channel"] = u"nightly"
    bad_channel = b
    b = copy.deepcopy(_man_ok()); b[u"files"][2][u"sha256"] = u"a" * 64
    del_with_sha = b
    b = copy.deepcopy(_man_ok()); b[u"files"][0][u"size"] = -1
    neg_size = b
    b = copy.deepcopy(_man_ok()); b[u"files"][1][u"path"] = u"core/a.py"
    dup_path = b
    for i, c in enumerate((bad_sha, bad_path, extra_key, missing_key, bad_channel,
                           del_with_sha, neg_size, dup_path)):
        ok, probs = UM.validate(c)
        assert (not ok) and probs, (i, probs)


def test_M3_bad_path():
    assert UM.bad_path(u"core/a.py") == u""
    for p in (u"../a", u"/abs/a", u"C:/a", u"a\\b", u"a//b", u"a/./b", u"", None, 3):
        assert UM.bad_path(p), p


def test_M4_totals():
    t = UM.totals(_man_ok())
    assert t == {u"n": 3, u"add": 1, u"mod": 1, u"del": 1, u"bytes": 7}, t


def test_M5_digest_stable():
    a = _man_ok()
    b = {k: a[k] for k in reversed(list(a))}
    assert UM.digest(a) == UM.digest(b)
    assert len(UM.digest(a)) == 16


def test_U1_未查则明书(tmp_path):
    f = UC.face(root=str(_root(tmp_path)), env=_env(tmp_path, u"http://127.0.0.1:1/"))
    assert f[u"available"] is False, f
    assert u"未查" in f[u"note"], f
    assert f[u"channel"] == u"internal", f
    assert f[u"manifest_url"].endswith(u"/update_manifest.json"), f


def test_U2_有新版(tmp_path):
    httpd, base = _serve(tmp_path, _man_ok())
    try:
        r = _root(tmp_path, u"9.0.0")
        f = UC.refresh(root=str(r), env=_env(tmp_path, base), timeout=3.0)
        assert f[u"available"] is True, f
        assert f[u"latest_version"] == u"9.0.1", f
        assert f[u"files"] == 3 and f[u"size_bytes"] == 7, f
        assert f[u"current_version"] == u"9.0.0", f
        g = UC.face(root=str(r), env=_env(tmp_path, base))
        assert g[u"available"] is True and g[u"latest_version"] == u"9.0.1", g
    finally:
        httpd.shutdown()


def test_U3_已是最新(tmp_path):
    httpd, base = _serve(tmp_path, _man_ok())
    try:
        r = _root(tmp_path, u"9.0.1")
        f = UC.refresh(root=str(r), env=_env(tmp_path, base), timeout=3.0)
        assert f[u"available"] is False, f
        assert f[u"note"] == u"已是最新", f
    finally:
        httpd.shutdown()


def test_U4_跨档拒(tmp_path):
    doc = _man_ok()
    doc[u"channel"] = u"beta"
    httpd, base = _serve(tmp_path, doc)
    try:
        r = _root(tmp_path, u"9.0.0")
        f = UC.refresh(root=str(r), env=_env(tmp_path, base), timeout=3.0)
        assert f[u"available"] is False, f
        assert u"跨档" in f[u"note"], f
    finally:
        httpd.shutdown()


def test_U5_源不可达(tmp_path):
    r = _root(tmp_path, u"9.0.0")
    f = UC.refresh(root=str(r), env=_env(tmp_path, u"http://127.0.0.1:1/"), timeout=2.0)
    assert f[u"available"] is False, f
    assert f[u"note"] and f[u"note_why"], f


def test_U6_态不入装根之data(tmp_path):
    la = os.path.join(str(tmp_path), u"la")
    env = {u"LOCALAPPDATA": la}
    assert UC.out_dir(root=str(tmp_path), env=env) == os.path.join(la, u"ClawsJoyPA", u"update")
    assert UC.out_dir(root=str(tmp_path), env={}) == os.path.join(str(tmp_path), u"data", u"pa", u"update")
    inside = os.path.join(str(tmp_path), u"data")
    assert not UC.state_path(root=str(tmp_path), env=env).startswith(inside)
    assert not PU.upd_dir(root=str(tmp_path), env=env).startswith(inside)
    assert PU.backup_dir(u"9.0.1", root=str(tmp_path), env=env).endswith(
        os.path.join(u"backup", u"9.0.1"))


def test_U7_face唯读盘():
    fn = _func(ROOT / u"core" / u"lib" / u"update_check.py", u"face")
    calls = _calls(fn)
    assert not (calls & {u"refresh", u"fetch", u"urlopen", u"Request"}), calls


def test_P1_never点名():
    for f in (MU.never, PU.never):
        assert f(u"config/.env"), f
        assert f(u"config/secrets.yaml"), f
        assert f(u"scripts/win_pa/ClawsJoyPA_PA_Boot.xml"), f
        assert f(u"data/pa/feedback/x.json"), f
        assert f(u"core/pa/gateway_routes.py") == u"", f
    assert MU.never(u"tests/unit/a.py") and MU.never(u"dist/a.exe") and MU.never(u"_share/a.txt")
    assert PU.never(u"logs/gateway.log")


def test_P2_verify_all(tmp_path):
    man = {u"version": u"9.0.1", u"base_version": u"9.0.0", u"channel": u"internal",
           u"built_at": u"2026-10-07T00:00:00+0800",
           u"files": [
               {u"path": u"core/a.txt", u"sha256": UM.sha256_bytes(b"hi"), u"size": 2, u"mode": u"add"},
               {u"path": u"core/gone.txt", u"sha256": u"", u"size": 0, u"mode": u"del"}]}
    stg = tmp_path / u"stage"
    (stg / u"core").mkdir(parents=True)
    (stg / u"core" / u"a.txt").write_bytes(b"hi")
    ok, rows = PU.verify_all(man, str(stg))
    assert ok, rows
    bad = copy.deepcopy(man)
    bad[u"files"][0][u"sha256"] = u"0" * 64
    ok2, _rows2 = PU.verify_all(bad, str(stg))
    assert not ok2
    (stg / u"core" / u"a.txt").unlink()
    ok3, rows3 = PU.verify_all(man, str(stg))
    assert (not ok3) and any(u"缺件" in r for r in rows3), rows3


def test_P3_health含update键():
    from flask import Flask

    from core.routes.system_routes import system_bp

    app = Flask(__name__)
    app.register_blueprint(system_bp)
    r = app.test_client().get(u"/health")
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert u"update" in d and isinstance(d[u"update"], dict), sorted(d)
    for k in (u"available", u"channel", u"manifest_url", u"current_version", u"note", u"note_why"):
        assert k in d[u"update"], k


def test_P4_清单含data须拒(tmp_path, monkeypatch):
    for k in (u"PA_UPDATE_URL", u"PA_UPDATE_CHANNEL", u"PA_UPDATE_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    root = _root(tmp_path)
    man = copy.deepcopy(_man_ok())
    man[u"files"] = [{u"path": u"data/pa/x.json", u"sha256": u"a" * 64, u"size": 1, u"mode": u"add"}]
    mp = tmp_path / u"m.json"
    mp.write_text(json.dumps(man, ensure_ascii=False), encoding=u"utf-8")
    a = _A(root=str(root), src=None, manifest=str(mp), staged=None, force=False,
           no_restart=True, go=True, json=False)
    assert PU.run(a) == 2


def test_P5_plan之尺():
    rc, _o = MU.git(str(ROOT), u"rev-parse", u"--verify", u"HEAD~1^{commit}")
    if rc != 0:
        pytest.skip(u"无 HEAD~1")
    rc, rows, man = MU.plan(str(ROOT), u"HEAD~1", u"HEAD", u"9.9.9", u"9.9.8", u"internal",
                            str(ROOT / u"dist" / u"_test_plan"))
    assert rc == 0, rows
    assert man and man[u"files"], rows
    bad = [e[u"path"] for e in man[u"files"]
           if e[u"path"].startswith((u"tests/", u"docs/", u"data/", u"logs/", u"dist/", u"_share/"))]
    assert not bad, bad
    for e in man[u"files"]:
        assert MU.never(e[u"path"]) == u"" and UM.bad_path(e[u"path"]) == u"", e
    ok, probs = UM.validate(man)
    assert ok, probs
    assert any(e[u"path"] == u"version.json" for e in man[u"files"])
