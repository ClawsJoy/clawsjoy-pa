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