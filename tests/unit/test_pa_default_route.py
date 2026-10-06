# -*- coding: utf-8 -*-
u"""pm_1471 §三 之测：**默认之值**（一处定形 · 可用者优先 · ⛔ 静默换）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_default_route.py -q

判据：
  ⒈ 默认之值 ⛔ 本机 7B：`DEFAULT_PROVIDER != "local:ollama"` ∧ `DEFAULT_MODEL["model"]`
     唯自注册表（≡ `default_model_of(DEFAULT_PROVIDER)` ∧ ∈ `known_models()`）。
  ⒉ 正控（首选可用）：首选之态 ∈ `AVAIL_OK` ⇒ route ＝ 首选 · note ＝ ""。
  ⒊ 反控（首选 ⛔ 可用 ⇒ 代者 ＋ 显形）：route ＝ 面内**首个可用**者 · note 含「不可用」∧「代之」。
  ⒋ 三控（皆 ⛔ 可用）：回首选之默认模型 · note 含「不可用」∧「亦无可用者」· **⛔ 崩**。
  ⒌ 一处定形：`public_view()["default"]` ≡ `default_view()`（含 `note` 键）。
  ⒍ 齿：首选 ⛔ 可用 ⇒ 若「静默」（route ＝ 首选 ∧ note ＝ ""）则本测须红。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import providers as P  # noqa: E402

LOCAL_ID = "local:ollama"
REMOTE_ID = "remote:deepseek"
IN_ = P.AVAIL_STATES[0]      # 在
KEYED = P.AVAIL_STATES[3]    # 钥已配
NOKEY = P.AVAIL_STATES[4]    # 未配钥
OFFLINE = P.AVAIL_STATES[2]  # 未接


# ---------- ⒈ 默认之值之源 ----------

def test_default_is_not_local_7b_and_names_from_registry():
    u"""⒈：默认 ⛔ 本机 7B；模型名唯自注册表（一处定形 · 免二处漂）。"""
    assert P.DEFAULT_PROVIDER != LOCAL_ID
    assert P.DEFAULT_PROVIDER == REMOTE_ID
    assert P.DEFAULT_MODEL["provider"] == P.DEFAULT_PROVIDER
    assert P.DEFAULT_MODEL["model"] == P.default_model_of(P.DEFAULT_PROVIDER)
    assert P.DEFAULT_MODEL["model"] in P.known_models()
    assert P.DEFAULT_MODEL["model"] != "qwen2.5:7b-instruct-q4_0-gpu"


def test_avail_ok_is_single_place():
    u"""AVAIL_OK ＝ 「可用」之二态（一处定形）。"""
    assert P.AVAIL_OK == (IN_, KEYED)
    for _bad in (P.AVAIL_STATES[1], OFFLINE, NOKEY, P.AVAIL_STATES[5]):
        assert _bad not in P.AVAIL_OK


# ---------- ⒉ 正控 ----------

def test_preferred_available_uses_preferred_no_note(monkeypatch):
    u"""⒉：首选可用 ⇒ 用之 · note ＝ ""（⛔ 无谓显形）。"""
    monkeypatch.setattr(P, "available_state", lambda pid: (KEYED, u"u"))
    r, note = P.default_route()
    assert r["provider"] == P.DEFAULT_PROVIDER, r
    assert r["model"] == P.default_model_of(P.DEFAULT_PROVIDER), r
    assert r["thinking"] is None
    assert note == "", note


# ---------- ⒊ 反控（代者 ＋ 显形） ----------

def test_unavailable_preferred_falls_to_available_and_surfaces(monkeypatch):
    u"""⒊：首选 ⛔ 可用 ⇒ 面内首个可用者代之 ∧ note 明书（⛔ 静默换）。"""
    def _av(pid):
        return (NOKEY, u"密钥 ⛔ 在") if pid == P.DEFAULT_PROVIDER else (IN_, u"127.0.0.1:11434 通 ∧ 1 个模型")
    monkeypatch.setattr(P, "available_state", _av)
    r, note = P.default_route()
    assert r["provider"] == LOCAL_ID, r
    assert r["model"] == P.default_model_of(LOCAL_ID), r
    assert u"不可用" in note and u"代之" in note, note
    assert (P.PROVIDERS[P.DEFAULT_PROVIDER].get("label") or P.DEFAULT_PROVIDER) in note, note
    # 齿：若「静默」（route 仍首选 ∨ note 空）⇒ 上行须红
    assert not (r["provider"] == P.DEFAULT_PROVIDER and note == ""), r


# ---------- ⒋ 三控（皆 ⛔ 可用） ----------

def test_all_unavailable_returns_preferred_and_is_loud(monkeypatch):
    u"""⒋：皆 ⛔ 可用 ⇒ 回首选之默认模型 · note 明书「亦无可用者」· ⛔ 崩。"""
    monkeypatch.setattr(P, "available_state", lambda pid: (NOKEY, u"密钥 ⛔ 在（key_env=K）"))
    r, note = P.default_route()
    assert r["provider"] == P.DEFAULT_PROVIDER, r
    assert r["model"] == P.default_model_of(P.DEFAULT_PROVIDER), r
    assert u"不可用" in note and u"亦无可用者" in note, note


def test_clean_machine_no_ollama_prefers_cloud(monkeypatch):
    u"""净机之预演：本机「未接」（无 Ollama）∧ 远端钥已配 ⇒ 默认落**云端**（演示首屏之正）。"""
    def _av(pid):
        return (KEYED, u"密钥在") if pid == P.DEFAULT_PROVIDER else (OFFLINE, u"127.0.0.1:11434 ⛔ 通")
    monkeypatch.setattr(P, "available_state", _av)
    r, note = P.default_route()
    assert r["provider"] == REMOTE_ID and P.provider_kind(r["provider"]) == "remote", r
    assert note == "", note


# ---------- ⒌ 一处定形 ----------

def test_public_view_default_is_default_view(monkeypatch):
    u"""⒌：`public_view()["default"]` ≡ `default_view()`（含 `note` 键 · 与 session_model 同源）。"""
    monkeypatch.setattr(P, "available_state", lambda pid: (KEYED, u"u"))
    pv = P.public_view()
    assert pv["default"] == P.default_view(), pv["default"]
    assert "note" in pv["default"], pv["default"]
    assert pv["default"]["model"] == P.default_route()[0]["model"]


# ---------- ⒍ 齿（随默认之路 ⇒ ⛔ 硬编本机） ----------

def test_default_max_tokens_follows_default_route(monkeypatch):
    u"""⒍：`default_max_tokens()` 随 `default_route()` 之 provider（⛔ 硬编本机 params）。"""
    monkeypatch.setattr(P, "available_state", lambda pid: (KEYED, u"u"))
    pid = P.default_route()[0]["provider"]
    want = int((P.PROVIDERS[pid].get("params") or {}).get("max_tokens") or P.DEFAULT_MAX_TOKENS)
    assert P.default_max_tokens() == want

    # 反控：默认落本机（首选 ⛔ 用）⇒ 随本机 params（读 env CLAWSJOY_MAX_TOKENS）
    monkeypatch.setitem(P.PROVIDERS[LOCAL_ID], "params", {"max_tokens": 4321})
    monkeypatch.setattr(P, "available_state",
                        lambda pid: (IN_, u"u") if pid == LOCAL_ID else (NOKEY, u"no"))
    assert P.default_route()[0]["provider"] == LOCAL_ID
    assert P.default_max_tokens() == 4321
