# -*- coding: utf-8 -*-
u"""pm_1464 \u00a7\u4e00\uff0f\u00a7\u4e8c\u4e4b\u6d4b\uff1a**\u53ef\u9009\u6a21\u578b\u8868**\uff08\u4e00\u884c\u4e00\u6a21\u578b\uff09\uff0b **\u53ef\u7528\u6001**\u2014\u2014 \u4e00\u5904\u5b9a\u5f62\u3002

\u4ee5\u4f55\u5f62\u8c03\u7528\uff08\u5224\u901a \uff0f \u65ad\u987b\u9644\uff09\uff1a
  python -X utf8 -B -m pytest tests/unit/test_pa_models_table.py -q

\u5224\u636e\uff1a
  \u24dc `provider_kind` \u4e00\u5904\u5b9a\u5f62\uff1a`ollama \u21d2 local`\uff08\u77ed\u540d\u4e0e\u6ce8\u518c\u952e\u540c\u679c\uff09\u3001`deepseek \u21d2 remote`\u3001\u672a\u8bc6 \u21d2 `unknown`\u3002
  \u24dd **\u9f7f**\uff1a`provider_kind` \u00b7 `route_kind` \u00b7 `src_label` \u00b7 `providers[].kind` **\u540c\u6e90** \u2014\u2014 \u6dfb\u4e00\u4f2a\u4f9b\u5e94\u5546\u21d2 **\u56db\u8005\u540c\u6b65\u8ddf**\u3002
  \u24de `models_table`\uff1a\u884c\u4e4b `id` \u2261 `known_models()`\uff1b\u884c\u5fc5\u6709 `kind \u2208 {\u672c\u673a\u4e4b\u96c6}`\u3001`\u53ef\u7528`\u3002
  \u24df \u53ef\u7528\u6001\u4e09\u6001\uff08\u9010\u5b57\uff09\uff1a\u672c\u673a \u21d2 `\u5728` ／ `\u7a7a`\uff08\u901a\u800c 0 \u6a21\u578b \u00b7 \u7a7a \u2260 \u7f3a\uff09\uff0f `\u672a\u63a5`\uff08\u7aef\u53e3 \u26d4 \u901a \u00b7 \u51c0\u673a\u4e4b\u6001\uff09\uff1b
     \u8fdc\u7aef \u21d2 `\u94a5\u5df2\u914d` ／ `\u672a\u914d\u94a5`\uff1b\u505c\u7528 \u21d2 `\u505c\u7528`\u3002
  \u24e0 **\u8bf4\u4e00\u7528\u4e00**\uff1a\u884c\u4e4b `id` \u21d2 `resolve_model`\u5f97\u540c\u503c \u2227 \u884c\u4e4b `kind` \u21d2 `route_kind`\u5f97\u540c\u503c\u3002
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import providers as P  # noqa: E402

LOCAL_ID = "local:ollama"
REMOTE_ID = "remote:deepseek"


# ---------- \u24dc \uff0b \u24dd\uff1a\u4e00\u5904\u5b9a\u5f62 \uff0b \u9f7f ----------

def test_provider_kind_single_source():
    u"""\u24dc\uff1a\u77ed\u540d\u4e0e\u6ce8\u518c\u952e\u540c\u679c\uff1b\u672a\u8bc6 \u21d2 `unknown`\uff1b\u7a7a \u21d2 `""`\u3002"""
    assert P.provider_kind("ollama") == "local"
    assert P.provider_kind(LOCAL_ID) == "local"
    assert P.provider_kind("deepseek") == "remote"
    assert P.provider_kind(REMOTE_ID) == "remote"
    assert P.provider_kind("glm") == "remote"
    assert P.provider_kind("who-new") == "unknown"
    assert P.provider_kind("") == ""
    assert P.provider_kind(None) == ""


def test_kind_is_one_place(monkeypatch):
    u"""\u24dd \u9f7f\uff1a\u56db\u8005\uff08`provider_kind` \u00b7 `route_kind` \u00b7 `src_label` \u00b7 `providers[].kind`\uff09\u540c\u6e90\u3002"""
    monkeypatch.setitem(P.PROVIDER_KIND, "fakevendor", "remote")
    monkeypatch.setitem(P.PROVIDERS, "remote:fakevendor",
                        {"id": "remote:fakevendor", "label": "F", "kind": "local",
                         "base_url": "https://x", "key_env": "X_KEY", "models": [], "params": {}})
    monkeypatch.setattr(P, "is_enabled", lambda pid: (True, "u"))
    # \u26a0 \u6ce8\u518c\u8868\u5b57\u9762\u4e3a local\uff0c\u7136 `PROVIDER_KIND` \u8868\u4e3a remote\uff1a\u540c\u6e90\u8005\u53d6**\u8868**
    assert P.provider_kind("remote:fakevendor") == "remote"
    assert P.route_kind({"provider": "fakevendor"}) == "remote"
    assert P.src_label({"provider": "fakevendor", "model": "m"}) == "src: remote:m"


def test_public_view_provider_kind_is_derived():
    u"""\u24dd\u2032\uff1a`providers[].kind` \u26d4 \u53d6\u6ce8\u518c\u8868\u5b57\u9762 \u2014\u2014 \u987b \u2261 `provider_kind(id)`\u3002"""
    for it in P.public_view()["providers"]:
        assert it["kind"] == P.provider_kind(it["id"]), it["id"]


# ---------- \u24de\uff1a\u8868\u4e4b\u884c ----------

def test_models_table_rows():
    u"""\u24de\uff1a\u884c \u2261 \u767d\u540d\u5355\uff1b\u884c\u5fc5\u6709 kind \u00b7 \u53ef\u7528\u3002"""
    pv = P.public_view()
    rows = pv["models_table"]
    assert [r["id"] for r in rows] == list(P.known_models())
    by_prov = {i["id"]: i for i in pv["providers"]}
    for r in rows:
        assert r["kind"] in ("local", "remote"), r
        assert r["kind"] == by_prov[r["provider_id"]]["kind"], r
        assert r["可用"] in P.AVAIL_STATES, r
        assert isinstance(r["key_configured"], bool), r
        assert r["provider"] and r["provider_id"], r


def test_models_table_never_carries_key_value(monkeypatch):
    u"""P2 \u2463 \u5ef6\uff1a\u8868\u4e5f \u26d4 \u8f7d\u5bc6\u94a5\u503c\uff08\u54e8\u5175\u503c\u8bc1\uff09\u3002"""
    sentinel = "sk-" + "SENTINEL" + "-1464"
    monkeypatch.setenv("DEEPSEEK_API_KEY", sentinel)
    blob = json.dumps(P.public_view(), ensure_ascii=False)
    assert sentinel not in blob
    assert "DEEPSEEK_API_KEY" in blob


# ---------- \u24df\uff1a\u53ef\u7528\u6001 ----------

def test_availability_local_localhost(monkeypatch):
    u"""\u24df\uff1a\u672c\u673a \u2014\u2014 \u901a \u2227 \u6709\u6a21\u578b \u21d2 `\u5728`\uff1b\u901a\u800c 0 \u6a21\u578b \u21d2 `\u7a7a`\uff1b\u7aef\u53e3 \u26d4 \u901a \u21d2 `\u672a\u63a5`\u3002"""
    monkeypatch.setattr(P, "_tcp_open", lambda *a, **k: True)
    assert P.available_state(LOCAL_ID)[0] == u"\u5728"
    monkeypatch.setitem(P.PROVIDERS[LOCAL_ID], "models", [])
    assert P.available_state(LOCAL_ID)[0] == u"\u7a7a"
    monkeypatch.setitem(P.PROVIDERS[LOCAL_ID], "models",
                        [{"id": "qwen2.5:7b-instruct-q4_0-gpu", "isDefault": True}])
    monkeypatch.setattr(P, "_tcp_open", lambda *a, **k: False)
    st, why = P.available_state(LOCAL_ID)
    assert st == u"\u672a\u63a5", st           # \u2b50 \u51c0\u673a\u65e0 Ollama \u5373\u6b64\u6001\uff08\u26d4 \u5e76\u5165\u300c\u7a7a\u300d\uff09
    assert "11434" in why, why


def test_availability_remote_and_disabled(monkeypatch):
    u"""\u24df\uff1a\u8fdc\u7aef\u94a5\u5df2\u914d \u21d2 `\u94a5\u5df2\u914d`\uff08\u63a2\u6d3b\u672a\u6d4b\uff09\uff1b\u65e0\u94a5 \u21d2 `\u672a\u914d\u94a5`\uff1benv \u505c\u7528 \u21d2 `\u505c\u7528`\u3002"""
    monkeypatch.setattr(P, "is_enabled", lambda pid: (True, "u"))
    monkeypatch.setattr(P, "key_state", lambda pid: "configured")
    assert P.available_state(REMOTE_ID)[0] == u"\u94a5\u5df2\u914d"
    monkeypatch.setattr(P, "key_state", lambda pid: "missing")
    assert P.available_state(REMOTE_ID)[0] == u"\u672a\u914d\u94a5"
    monkeypatch.setattr(P, "is_enabled", lambda pid: (False, "\u505c\u7528\uff08env CLAWSJOY_PA_PROVIDERS_DISABLED \u5217\u4e4b\uff09"))
    st, why = P.available_state(REMOTE_ID)
    assert st == u"\u505c\u7528" and "\u505c\u7528" in why, (st, why)


def test_availability_states_are_words_not_bool(monkeypatch):
    u"""\u24df\u2032\uff1a\u4e00\u540d\u853d\u4e8c\u6001\u4e4b\u6212 \u2014\u2014 \u6001\u5fc5\u4e3a**\u8bcd**\uff0c\u4e14\u8bcd\u8868\u4e00\u5904\u5b9a\u5f62\u3002"""
    assert P.AVAIL_STATES == (u"\u5728", u"\u7a7a", u"\u672a\u63a5", u"\u94a5\u5df2\u914d", u"\u672a\u914d\u94a5", u"\u505c\u7528")
    monkeypatch.setattr(P, "_tcp_open", lambda *a, **k: True)
    for pid in P.PROVIDERS:
        st = P.available_state(pid)[0]
        assert st in P.AVAIL_STATES and isinstance(st, str), (pid, st)


# ---------- \u24e0\uff1a\u8bf4\u4e00\u7528\u4e00 ----------

def test_say_one_use_one():
    u"""\u24e0\uff1a\u8868\u4e2d\u6240\u5217 \u21d2 \u767d\u540d\u5355\u6536 \u2227 \u8d70\u5f84\u4e4b kind \u540c\u503c\uff08\u8868\u4e4b\u540d \u2261 \u56de\u6267\u4e4b\u540d\uff09\u3002"""
    for r in P.public_view()["models_table"]:
        assert P.resolve_model(r["id"]) == r["id"], r["id"]
        assert P.route_kind({"provider": r["provider"], "model": r["id"]}) == r["kind"], r["id"]
        assert P.src_label({"provider": r["provider"], "model": r["id"]}) == "src: %s:%s" % (r["kind"], r["id"])