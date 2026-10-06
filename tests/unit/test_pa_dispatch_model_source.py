# -*- coding: utf-8 -*-
u"""pm_1468 §二.1「同源」之齿：`core/pa/dispatch.py` 之模型名 ⇒ **唯自注册表**（⛔ 硬编）。

正控：`dispatch_model()` ≡ 注册表 `remote:deepseek` 之 `isDefault` 模型之**实名**（且 ∈ `known_models()`）。
反控：⛔ 字面 `deepseek-flash` ／ `deepseek-v4-flash` 于本件之**活代码**（承「一处定形」）。
齿：注册表缺该 provider ⇒ `RuntimeError`（明报缺源 · ⛔ 静默兜底）。
"""
from __future__ import annotations

import io
import re

import pytest

from core.pa import dispatch as D
from core.pa import providers as P


def test_dispatch_model_is_registry_real_name():
    u"""正控：派件之模型 ＝ 注册表之实名（一处定形）。"""
    want = P.default_model_of("remote:deepseek")
    assert want, u"注册表应有 remote:deepseek 之默认模型"
    assert D.dispatch_model() == want
    assert want in P.known_models()


def test_dispatch_model_follows_registry_change(monkeypatch):
    u"""反控（齿）：改注册表 ⇒ 派件之名随之（⛔ 硬编新名）。"""
    fake = {"remote:deepseek": {"models": [{"id": "zzz-renamed", "isDefault": True}]}}
    monkeypatch.setattr(P, "PROVIDERS", fake)
    assert D.dispatch_model() == "zzz-renamed"


def test_dispatch_model_missing_source_raises(monkeypatch):
    u"""齿：缺源 ⇒ 明报（⛔ 静默字面兜底）。"""
    monkeypatch.setattr(P, "PROVIDERS", {})
    with pytest.raises(RuntimeError):
        D.dispatch_model()


def test_no_hardcoded_model_name_in_dispatch_source():
    u"""反控：本件源内 ⛔ 载模型名字面（唯注 ／ docstring 之引可）。"""
    src = io.open(D.__file__, encoding="utf-8").read()
    live = []
    for i, ln in enumerate(src.splitlines(), 1):
        code = ln.split("#", 1)[0]
        if re.search(r"deepseek-(flash|v4-flash|v4-pro)", code):
            live.append((i, ln.strip()))
    assert live == [], u"活代码内不得硬编模型名：%r" % (live,)
