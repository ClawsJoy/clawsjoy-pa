# -*- coding: utf-8 -*-
u"""pm_1502 §一：库根之「源」—— 一处定形 ＋ 今／义二形须合。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_first_run_vault_src.py -q

判据：
  ⒜ `vault_root()` 唯 `vault_root_src()[0]`（⛔ 二处各判）。
  ⒝ 四序之源逐字（env ／ 配置 ／ 内置空库 ／ 末选）＋ 皆无 ⇒ 「未接（选目录）…」。
  ⒞ **同源**：`env_face.resolve_paths()["paths_src"]["vault"]` ≡ `vault_root_src()[1]`。
  ⒟ 今／义二形合（首启之「面之源」）：内置空库在 ⇒ 源 ＝ 「内置空库（本机默认 · 空）」
     ∧ 义含「内置空库」；皆无 ⇒ 今 ＝ 「未接」∧ 源含「未接（选目录）」。
  ⒠ 反控：同机唯易 `PA_VAULT_DIR` ⇒ 值变（⛔ 假绿）。
  ⒡ pm_1503 §一：面之源**逐键「态」**＝机器码（`no_root` ／ `empty` ／ `ok`）· **今随态**
     （no_root ⇒ 今 ＝「未接」）。
  ⒢ pm_1517 §一（裁：取拟一）：其**判据改依「PA 检索面」**（`PA_KB_ASK_SCOPES` ＋ `PA_FACES`
     中根在本库根之下者之件数）—— 一处定形（唯问 `gateway_routes.pa_vault_state_code()`）·
     **⛔ 内核约定六面**（反控：`notes/` 有件 ⇒ 仍 `empty`）。
  ⒣ 净机之预演：自带 `data/kb` 唯六约定子目录 ⇒ `empty`（⛔ `ok`）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import paths as P  # noqa: E402
from core.pa import env_face as EF  # noqa: E402
from core.pa import gateway_routes as GR  # noqa: E402


@pytest.fixture()
def no_orders(monkeypatch):
    u"""四序皆无之态（⛔ 触真盘 · 唯改三器）。"""
    monkeypatch.delenv("PA_VAULT_DIR", raising=False)
    monkeypatch.setattr(P, "_config_vault_root", lambda: None)
    monkeypatch.setattr(P, "_builtin_kb", lambda: None)
    monkeypatch.setattr(P, "org_path", lambda _n: None)


def test_env_order(monkeypatch, tmp_path):
    d = tmp_path / u"myvault"
    d.mkdir()
    monkeypatch.setenv("PA_VAULT_DIR", str(d))
    v, src = P.vault_root_src()
    assert str(v) == str(d), (v, src)
    assert src == "env:PA_VAULT_DIR", src


def test_config_order(no_orders, monkeypatch, tmp_path):
    d = tmp_path / u"cfgvault"
    d.mkdir()
    monkeypatch.setattr(P, "_config_vault_root", lambda: str(d))
    v, src = P.vault_root_src()
    assert str(v) == str(d), (v, src)
    assert src == u"配置:paths.vault_root", src


def test_builtin_order(no_orders, monkeypatch, tmp_path):
    d = tmp_path / u"kb"
    d.mkdir()
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    v, src = P.vault_root_src()
    assert str(v) == str(d), (v, src)
    assert src == u"内置空库（本机默认 · 空）", src


def test_legacy_order(no_orders, monkeypatch, tmp_path):
    d = tmp_path / u"legacy"
    d.mkdir()
    monkeypatch.setattr(P, "org_path", lambda _n: str(d))
    v, src = P.vault_root_src()
    assert str(v) == str(d), (v, src)
    assert src == u"末选:PA_VAULT_LEGACY", src


def test_all_absent(no_orders):
    v, src = P.vault_root_src()
    assert v is None, v
    assert u"未接（选目录）" in src, src
    assert P.vault_root() is None


def test_single_judge_and_same_source(no_orders, monkeypatch, tmp_path):
    u"""⒜ ＋ ⒞：`vault_root()` 唯 src 之 `[0]`；`paths_src.vault` ≡ src（同源）。"""
    d = tmp_path / u"kb"
    d.mkdir()
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    assert str(P.vault_root()) == str(P.vault_root_src()[0]), u"vault_root 非唯 src 之 [0]"
    _pm, ps = EF.resolve_paths()
    assert ps["vault"] == P.vault_root_src()[1], (ps["vault"], P.vault_root_src()[1])
    assert ps["vault"] == u"内置空库（本机默认 · 空）", ps["vault"]


def test_first_run_vault_source_and_meaning(no_orders, monkeypatch, tmp_path):
    u"""⒟ 今／义二形合（内置空库在）—— 源须显「内置空库」∧ 义须明书之（⛔ 混同「未接」）。"""
    d = tmp_path / u"kb"
    d.mkdir()
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    ro = GR._first_run_readout()
    keys = {k[u"键"]: k for k in ro[u"面之源"][u"键"]}
    assert set(keys) == {"PA_ORG_FACES", "PA_WS_ROOT", "PA_VAULT_DIR"}, list(keys)
    for _n, _k in keys.items():
        assert _k.get(u"源"), (u"缺「源」", _n)
    vk = keys["PA_VAULT_DIR"]
    assert vk[u"今"] == str(d), vk
    assert vk[u"源"] == u"内置空库（本机默认 · 空）", vk
    assert u"内置空库" in vk[u"义"], vk
    assert u"未接（选目录）" in vk[u"义"], (u"义须明书「唯四序皆无方现」", vk)


def test_first_run_vault_all_absent(no_orders):
    u"""⒟ 今／义二形合（皆无）—— 今 ＝ 「未接」∧ 源含「未接（选目录）」。"""
    ro = GR._first_run_readout()
    vk = {k[u"键"]: k for k in ro[u"面之源"][u"键"]}["PA_VAULT_DIR"]
    assert vk[u"今"] == u"未接", vk
    assert u"未接（选目录）" in vk[u"源"], vk


def test_anti_hardcoded_unknown_vault_src(no_orders, monkeypatch, tmp_path):
    u"""反控：「源」不得为恒字（⛔ 死书）—— 内置空库之径动 ⇒ 今动（器有齿）。"""
    d1 = tmp_path / u"kb1"; d1.mkdir()
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d1))
    ro1 = {k[u"键"]: k for k in GR._first_run_readout()[u"面之源"][u"键"]}["PA_VAULT_DIR"]
    d2 = tmp_path / u"kb2"; d2.mkdir()
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d2))
    ro2 = {k[u"键"]: k for k in GR._first_run_readout()[u"面之源"][u"键"]}["PA_VAULT_DIR"]
    assert ro1[u"今"] != ro2[u"今"], (ro1, ro2)


# ============================== pm_1503 §一：态之机器码 ==============================
def _vkey(ro):
    return {k[u"键"]: k for k in ro[u"面之源"][u"键"]}[u"PA_VAULT_DIR"]


def test_态码_皆无_no_root(no_orders):
    u"""⒡ 四序皆无 ⇒ 态 ＝ ``no_root`` ∧ 今 ＝「未接」（今随态 · ⛔ 相抵）。"""
    vk = _vkey(GR._first_run_readout())
    assert vk[u"态"] == u"no_root", vk
    assert vk[u"今"] == u"未接", vk


def test_态码_空库_empty_反控非_no_root(no_orders, monkeypatch, tmp_path):
    u"""⒡ 库根在而 0 件 ⇒ 态 ＝ ``empty``（**反控：⛔ 报 ``no_root``**）∧ 今 ＝ 径。"""
    d = tmp_path / u"kb"; d.mkdir()
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    vk = _vkey(GR._first_run_readout())
    assert vk[u"态"] == u"empty", vk
    assert vk[u"态"] != u"no_root", (u"空库 ⛔ 得报「未接」", vk)
    assert vk[u"今"] == str(d), vk


def test_态码_有物_ok(no_orders, monkeypatch, tmp_path):
    u"""⒡ 库根在 ∧ 有件 ⇒ 态 ＝ ``ok`` ∧ 今 ＝ 径。"""
    d = tmp_path / u"kb"
    (d / u"收件箱").mkdir(parents=True)
    (d / u"收件箱" / u"a.md").write_text(u"# t\n", encoding="utf-8")
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    vk = _vkey(GR._first_run_readout())
    assert vk[u"态"] == u"ok", vk
    assert vk[u"今"] == str(d), vk


def test_态码_判据_检索面_反控内核六面(no_orders, monkeypatch, tmp_path):
    u"""⒢ pm_1517 §一：态码唯依 **PA 检索面** —— 反控：`notes/` 有件（内核六面有物）⇒ 仍 `empty`。"""
    from core.lib import note_kernel as NK
    d = tmp_path / u"kb"
    (d / u"notes").mkdir(parents=True)
    (d / u"notes" / u"a.md").write_text(u"# t\n", encoding="utf-8")
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    assert NK.face_state_code(root=str(d)) == NK.STATE_CODE_OK, u"内核六面：有物"
    vk = _vkey(GR._first_run_readout())
    assert vk[u"态"] == u"empty", (u"态须依检索面（⛔ 内核六面）", vk)
    assert vk[u"态"] != NK.STATE_CODE_OK, (u"⛔ 与内核六面同轴", vk)


def test_态码_净机预演_唯六面_empty(no_orders, monkeypatch, tmp_path):
    u"""⒣ 净机之预演：自带 `data/kb`（唯内核约定六面之子目录 · ⛔ `收件箱`／`知识库`）⇒ `empty`。"""
    from core.lib.note_kernel import SUBDIRS
    d = tmp_path / u"kb"
    for _s in SUBDIRS:
        (d / _s).mkdir(parents=True, exist_ok=True)
    (d / u"notes" / u"a.md").write_text(u"# t\n", encoding="utf-8")
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    _vk = _vkey(GR._first_run_readout())
    assert _vk[u"态"] == u"empty", _vk
    assert _vk[u"态"] != u"ok", (u"净机预演须为空库", _vk)


def test_态码_一处定形_唯问后端器(no_orders, monkeypatch, tmp_path):
    u"""⒢ 一处定形：`态` 唯自 `pa_vault_state_code()`（⛔ 另立判据 ⇒ 二源）。"""
    d = tmp_path / u"kb"
    (d / u"收件箱").mkdir(parents=True)
    (d / u"收件箱" / u"a.md").write_text(u"# t\n", encoding="utf-8")
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    _c, _n, _faces = GR.pa_vault_state_code(root=str(d))
    assert _c == GR._first_run_readout()[u"面之源"][u"键"][2][u"态"], u"二处各判 ⇒ 漂"
    assert _n == 1 and _faces == (u"收件箱",), (_n, _faces)


def test_态码_逐键皆在且值域内(no_orders, monkeypatch, tmp_path):
    u"""⒡ 三键各附「态」∧ 值 ∈ {no_root, empty, ok}（机器码 · ⛔ 字面哨符）。"""
    d = tmp_path / u"kb"; d.mkdir()
    monkeypatch.setattr(P, "_builtin_kb", lambda: str(d))
    keys = {k[u"键"]: k for k in GR._first_run_readout()[u"面之源"][u"键"]}
    assert set(keys) == {"PA_ORG_FACES", "PA_WS_ROOT", "PA_VAULT_DIR"}, list(keys)
    for _n, _k in keys.items():
        assert _k.get(u"态") in (u"no_root", u"empty", u"ok"), (u"缺「态」／值越域", _n, _k)
    assert GR._first_run_readout()[u"面之源"].get(u"态域"), u"态域须明书（前端须知其域）"
