# -*- coding: utf-8 -*-
u"""甲 件一（pm_1520 §二.1）：`POST /v9/pa/vault/set` —— 选目录 ⇒ 立库根（唯一写端）。

判据（pm_1520 §一.4 之齿）：
  ⒜ 成 ⇒ `{ok, vault_root, vault_root_src, state, at, changed, env_override, note}`
  ⒝ 径 ⛔ 在 ／ ⛔ 为目录 ⇒ 拒 ｜ ⛔ 可写 ⇒ 拒 ｜ path ⛔ 为串 ／ 体缺 path ⇒ 拒
  ⒞ **幂等**：同径重设 ⇒ `changed:false` ∧ ⛔ 报错
  ⒟ 写后 ⇒ `vault_root()` **即得**（⛔ 重起 —— 惰性之齿）∧ `面之源.态` 随变
  ⒠ 清（`{"path": ""}`）⇒ 落回内置空库 ／ 未接（⛔ 再指配置）
  ⒡ `env_override` ／ `note` 与 `first_run` **同源**（`G.vault_env_override()`）
器取：python -X utf8 -B -m pytest tests/unit/test_pa_vault_set_endpoint.py -q --basetemp=<仓外>
"""
import os
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import paths as P            # noqa: E402
from core.pa import gateway_routes as G   # noqa: E402

CFG = u"""# 注（须保）
version: 4.0.0
paths:
  data_root: data      # 行内注
"""


class _OsShim(object):
    u"""`os` 之替身：唯 `access` ⇒ False（余皆真）—— 器取「⛔ 可写」之支。"""

    def __init__(self, real):
        self._r = real

    def __getattr__(self, k):
        if k == u"access":
            return lambda *a, **kw: False
        return getattr(self._r, k)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv(u"PA_DATA_DIR", str(tmp_path / u"pa"))
    monkeypatch.delenv(u"PA_VAULT_DIR", raising=False)
    monkeypatch.delenv(u"PA_VAULT_LEGACY", raising=False)
    cfg = tmp_path / u"cfg" / u"system_unified.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(CFG, encoding=u"utf-8")
    from core.lib.unified_config import unified_config as uc
    monkeypatch.setattr(uc, u"_main_path", cfg)
    monkeypatch.setattr(uc, u"_config", {u"version": u"4.0.0", u"paths": {u"data_root": u"data"}})
    app = Flask(__name__)
    G.register_pa_routes(app)
    app.config[u"TESTING"] = True
    return app.test_client(), cfg


def _post(c, path):
    return c.post(u"/v9/pa/vault/set", json={u"path": path})


def test_A_set_ok(api, tmp_path):
    c, cfg = api
    d = tmp_path / u"kb"; (d / u"收件箱").mkdir(parents=True)
    (d / u"收件箱" / u"a.md").write_text(u"# a\n", encoding=u"utf-8")
    r = _post(c, str(d))
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j[u"ok"] is True and j[u"changed"] is True, j
    assert j[u"vault_root"] == str(d)
    assert j[u"vault_root_src"] == u"配置:paths.vault_root"
    assert j[u"state"] == u"ok", j
    assert j[u"env_override"] is False and j[u"note"] == u""
    assert j[u"file"] == str(cfg) and Path(j[u"backup"]).exists()
    assert u"vault_root" in cfg.read_text(encoding=u"utf-8")


def test_B_idempotent(api, tmp_path):
    c, cfg = api
    d = tmp_path / u"kb"; d.mkdir()
    assert _post(c, str(d)).get_json()[u"changed"] is True
    before = cfg.read_bytes()
    j2 = _post(c, str(d)).get_json()
    assert j2[u"ok"] is True and j2[u"changed"] is False, j2
    assert cfg.read_bytes() == before


def test_C_written_visible_without_restart(api, tmp_path):
    c, _ = api
    d = tmp_path / u"kb"; d.mkdir()
    _post(c, str(d))
    assert str(G.vault_root()) == str(d), u"写后须即得（⛔ 重起）"
    assert P.vault_root_src()[1] == u"配置:paths.vault_root"


def test_D_env_override_true_and_same_source(api, tmp_path, monkeypatch):
    c, _ = api
    monkeypatch.setenv(u"PA_VAULT_DIR", str(tmp_path / u"envkb"))
    d = tmp_path / u"kb"; d.mkdir()
    j = _post(c, str(d)).get_json()
    assert j[u"env_override"] is True, j
    assert j[u"note"] == G.PA_VAULT_ENV_NOTE
    assert j[u"vault_root_src"] == u"env:PA_VAULT_DIR"
    assert G.vault_env_override() == (True, G.PA_VAULT_ENV_NOTE), u"须与 first_run 同源"


def test_E_reject_relative(api):
    c, _ = api
    r = _post(c, u"rel/kb")
    assert r.status_code == 400 and r.get_json()[u"ok"] is False
    assert u"绝对径" in r.get_json()[u"error"]


def test_F_reject_missing_dir(api, tmp_path):
    c, _ = api
    r = _post(c, str(tmp_path / u"nope"))
    assert r.status_code == 400 and u"非目录" in r.get_json()[u"error"]


def test_G_reject_non_string(api):
    c, _ = api
    r = c.post(u"/v9/pa/vault/set", json={u"path": 123})
    assert r.status_code == 400
    r2 = c.post(u"/v9/pa/vault/set", json={})
    assert r2.status_code == 400


def test_H_reject_unwritable(api, tmp_path, monkeypatch):
    c, _ = api
    d = tmp_path / u"kb"; d.mkdir()
    monkeypatch.setattr(G, u"os", _OsShim(os))
    r = _post(c, str(d))
    assert r.status_code == 400 and u"不可写" in r.get_json()[u"error"], r.get_json()


def test_I_clear_falls_back(api, tmp_path):
    c, cfg = api
    d = tmp_path / u"kb"; d.mkdir()
    _post(c, str(d))
    j = _post(c, u"").get_json()
    assert j[u"ok"] is True and j[u"changed"] is True, j
    assert j[u"vault_root_src"] != u"配置:paths.vault_root", j
    assert j[u"state"] in (u"no_root", u"empty"), j