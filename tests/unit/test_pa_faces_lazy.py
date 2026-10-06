# -*- coding: utf-8 -*-
u"""甲 件三（pm_1520 §二.3）：面表 ⇒ **惰算** —— 改根 ⛔ 重起即随变（⛔ 缓存残留）。

判据：
  ⒜ `_FACE_WS` ／ `_FACE_VR` 随 env **当刻**变（⛔ import 即定形）
  ⒝ `PA_FACES` ／ `pa_faces()` **同物**（一处定形）· 面根随 `PA_WS_ROOT` ／ `PA_VAULT_DIR` 变
  ⒞ `PA_ORG_FACES` 门：开 ⇒ `org` ＋ 七面；关 ⇒ `product` ＋ 唯 `死件账` ∧ 素材面空表
  ⒟ 反控：先读 ⇒ 改根 ⇒ 再读 ⇒ **须异**（⛔ 旧缓存残留）
  ⒠ `__getattr__` 之界：未名 ⇒ `AttributeError`
  ⒡ 端到端：库根由空 ⇒ 有件 ⇒ `pa_vault_state_code()` 由 `empty` ⇒ `ok`（⛔ 重起）
器取：python -X utf8 -B -m pytest tests/unit/test_pa_faces_lazy.py -q --basetemp=<仓外>
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as G   # noqa: E402

_KEYS = ("PA_ORG_FACES", "PA_WS_ROOT", "PA_VAULT_DIR", "PA_VAULT_LEGACY")


def _clean(monkeypatch):
    for k in _KEYS:
        monkeypatch.delenv(k, raising=False)


def _roots(tb, name):
    for row in tb:
        if row[0] == name:
            return row[4] if len(row) == 7 else row[1]
    return None


def test_face_ws_vr_lazy(monkeypatch, tmp_path):
    _clean(monkeypatch)
    a = tmp_path / "a"; a.mkdir()
    b = tmp_path / "b"; b.mkdir()
    monkeypatch.setenv("PA_WS_ROOT", str(a))
    monkeypatch.setenv("PA_VAULT_DIR", str(a))
    assert str(G._FACE_WS) == str(a) and str(G._FACE_VR) == str(a)
    monkeypatch.setenv("PA_WS_ROOT", str(b))
    monkeypatch.setenv("PA_VAULT_DIR", str(b))
    assert str(G._FACE_WS) == str(b), u"⛔ 随 env 当刻变（import 即定形）"
    assert str(G._FACE_VR) == str(b), u"⛔ 随 env 当刻变（import 即定形）"


def test_pa_faces_same_source(monkeypatch, tmp_path):
    _clean(monkeypatch)
    monkeypatch.setenv("PA_ORG_FACES", "1")
    ws1 = tmp_path / "ws1"; ws1.mkdir()
    vr1 = tmp_path / "vr1"; vr1.mkdir()
    monkeypatch.setenv("PA_WS_ROOT", str(ws1))
    monkeypatch.setenv("PA_VAULT_DIR", str(vr1))
    assert G.PA_FACES == G.pa_faces(), u"旧名与新门须同物（一处定形）"
    assert [x[0] for x in G.PA_FACES] == [u"文件", u"台账", u"平台台账", u"台账·信通",
                                          u"梦中月水中花", u"文件·产出", u"死件账"]
    assert _roots(G.PA_FACES, u"文件") == (str(ws1),)
    assert _roots(G.PA_FACES, u"平台台账")[0].startswith(str(vr1))


def test_pa_faces_no_stale_cache(monkeypatch, tmp_path):
    _clean(monkeypatch)
    monkeypatch.setenv("PA_ORG_FACES", "1")
    ws1 = tmp_path / "ws1"; ws1.mkdir()
    ws2 = tmp_path / "ws2"; ws2.mkdir()
    monkeypatch.setenv("PA_WS_ROOT", str(ws1))
    r1 = _roots(G.PA_FACES, u"文件")
    monkeypatch.setenv("PA_WS_ROOT", str(ws2))
    r2 = _roots(G.PA_FACES, u"文件")
    assert r1 == (str(ws1),) and r2 == (str(ws2),), (r1, r2)
    assert r1 != r2, u"⛔ 旧缓存残留（反控）"


def test_gate_org_off_product_only(monkeypatch, tmp_path):
    _clean(monkeypatch)
    monkeypatch.setenv("PA_WS_ROOT", str(tmp_path))
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path))
    assert G.PA_FACES_GATE == u"product" == G.pa_faces_gate()
    assert [x[0] for x in G.PA_FACES] == [u"死件账"]
    assert G.PA_SRC_FACES == () and G.PA_SRC_FACES_GATE == u"product"


def test_gate_org_on_src_faces(monkeypatch, tmp_path):
    _clean(monkeypatch)
    monkeypatch.setenv("PA_ORG_FACES", "1")
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path))
    assert G.PA_FACES_GATE == u"org" == G.pa_faces_gate()
    assert [x[0] for x in G.PA_SRC_FACES] == [u"文件", u"出图"]
    assert G.PA_SRC_FACES == G.pa_src_faces()
    assert G.PA_SRC_FACES_GATE == G.pa_src_faces_gate() == u"org"


def test_getattr_unknown_raises(monkeypatch):
    with pytest.raises(AttributeError):
        getattr(G, u"no_such_name_xyz_1520")


def test_state_follows_vault_root(monkeypatch, tmp_path):
    _clean(monkeypatch)
    vr = tmp_path / "vr"
    (vr / u"收件箱").mkdir(parents=True)
    monkeypatch.setenv("PA_VAULT_DIR", str(vr))
    assert G.pa_vault_state_code()[0] == u"empty"
    (vr / u"收件箱" / u"a.md").write_text(u"# a\n", encoding="utf-8")
    assert G.pa_vault_state_code()[0] == u"ok", u"⛔ 重起即可见（惰算）"