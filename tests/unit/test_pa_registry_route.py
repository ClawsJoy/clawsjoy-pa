# -*- coding: utf-8 -*-
u"""PA v1.1 S2a：只读端 `GET /v9/pa/registry`（20 卡 · active 2 ／ pending 18 · 源缺仍 200 且 ⛔ 假卡）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_registry_route.py -q

判据（可机检）：
  ① 200 ＋ JSON：`generated_at` ／ `source` ／ `counts{total,active,pending}` ／ `cards[]`；
  ② 卡之数逐点：20 ／ active 2 ／ pending 18（⛔ 手写常量 —— 与源件逐卡对）；
  ③ 字段齐：id ／ kind ／ name ／ class ／ status ／ control_plane ／ view ／ access_level，
     history_session_id ／ session_format **源有方出**（⛔ 补造）；
  ④ 只读：唯 GET（⛔ 写方法）· GET 后源件字节不改 · 字段白名单（⛔ 陌生键 ／ 敏感键外泄）；
  ⑤ pending ⛔ 可派：`dispatchable` 唯 active 为 True；
  ⑥ 源缺 ／ 空 ／ 坏 ⇒ 仍 200 ＋ `state` ／ `error` 显因 ＋ counts 全 0 ＋ cards 空（⛔ 假卡）。
"""
import json
import shutil
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import pa_routes_registry as REG  # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402

SOURCE = ROOT / "data" / "tmp" / "pa_registry_pilot_v2.json"

CORE_FIELDS = set(REG.CARD_CORE_FIELDS)

ADMIT_FIELDS = CORE_FIELDS | set(REG.CARD_OPT_FIELDS) | {"dispatchable"}


def _app():
    app = Flask("pa_registry_route_test")
    register_pa_routes(app)
    return app


@pytest.fixture()
def client():
    return _app().test_client()


def _source_cards():
    u"""源件逐卡（真源 —— 测试 ⛔ 另抄一份卡）。"""
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def _get(client, remote=None):
    if remote:
        return client.open(REG.REGISTRY_ROUTE, method="GET",
                           environ_overrides={"REMOTE_ADDR": remote})
    return client.get(REG.REGISTRY_ROUTE)


# ---------- ① 200 ＋ 回执形状 ----------

def test_200_json_with_required_keys(client):
    r = _get(client)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.is_json
    d = r.get_json()
    for k in ("generated_at", "source", "counts", "cards", "state", "error", "readonly", "ok"):
        assert k in d, (k, sorted(d))
    assert d["ok"] is True and d["readonly"] is True
    assert d["state"] == "ok", d
    assert d["error"] is None, d
    assert isinstance(d["generated_at"], str) and d["generated_at"], d["generated_at"]
    assert str(d["source"]).endswith(REG.PILOT_BASENAME), d["source"]
    assert set(d["counts"]) == {"total", "active", "pending"}, d["counts"]


# ---------- ② 20 卡 · 逐卡对源 ----------

def test_20_cards_equal_source_cards(client):
    cards = _get(client).get_json()["cards"]
    src = _source_cards()
    assert len(src) == 20, u"源件非 20 卡 ⇒ 本测无从判"
    assert len(cards) == 20, len(cards)
    assert [c.get("id") for c in cards] == [c.get("id") for c in src], u"卡序／卡集 ⛔ 漂"
    ids = [c.get("id") for c in cards]
    assert len(set(ids)) == len(ids), u"卡 id 须唯一"
    for c in cards:
        for k in CORE_FIELDS:
            assert k in c, (k, c.get("id"))
        assert isinstance(c["status"], str) and c["status"], c["id"]
        assert isinstance(c["kind"], str) and c["kind"], c["id"]


def test_counts_exact_20_2_18(client):
    d = _get(client).get_json()
    assert d["counts"] == {"total": 20, "active": 2, "pending": 18}, d["counts"]
    cards = d["cards"]
    assert d["counts"]["total"] == len(cards)
    assert d["counts"]["active"] == sum(1 for c in cards if c["status"] == "active")
    assert d["counts"]["pending"] == sum(1 for c in cards if c["status"] == "pending")
    assert d["counts"]["active"] + d["counts"]["pending"] == d["counts"]["total"], u"本册二态应覆盖全数"


# ---------- ③ 字段齐 · history/session 源有方出 ----------

def test_fields_present_where_available(client):
    cards = _get(client).get_json()["cards"]
    by_id = {c["id"]: c for c in cards}
    src = _source_cards()
    with_history = [x for x in src if x.get("history_session_id") is not None]
    with_format = [x for x in src if x.get("session_format") is not None]
    assert with_history, u"源件无 history_session_id ⇒ 判据无从谈起"
    for x in src:
        card = by_id[x["id"]]
        for k in ("history_session_id", "session_format"):
            want = x.get(k) is not None
            assert (k in card) is want, (x["id"], k, want, sorted(card))
            if want:
                assert card[k] == x[k], (x["id"], k)
    assert {x["id"] for x in with_history} <= {c["id"] for c in cards}
    assert {x["id"] for x in with_format} <= {c["id"] for c in cards}


def test_card_fields_whitelisted_no_foreign_keys(client):
    cards = _get(client).get_json()["cards"]
    for c in cards:
        extra = set(c) - ADMIT_FIELDS
        assert not extra, (c.get("id"), sorted(extra))


# ---------- ④ 只读 · 唯 GET · 零写入 ----------

def test_route_is_get_only():
    app = _app()
    rules = [r for r in app.url_map.iter_rules() if str(r.rule) == REG.REGISTRY_ROUTE]
    assert len(rules) == 1, [str(r) for r in rules]
    rule = rules[0]
    assert str(rule.endpoint) == "pa_routes.pa_registry", rule.endpoint
    methods = set(rule.methods or ())
    assert "GET" in methods, methods
    assert not (methods & {"POST", "PUT", "PATCH", "DELETE"}), methods
    assert not (methods - {"GET", "HEAD", "OPTIONS"}), u"只读端 ⛔ 多方法"


def test_get_does_not_touch_source(client):
    before = SOURCE.read_bytes()
    stat0 = SOURCE.stat()
    assert _get(client).status_code == 200
    assert SOURCE.read_bytes() == before, u"只读端改了源件"
    stat1 = SOURCE.stat()
    assert (stat0.st_size, stat0.st_mtime_ns) == (stat1.st_size, stat1.st_mtime_ns), u"只读端动了源件元数据"


def test_no_credentials_required(client):
    u"""只读端 ⛔ 凭据：非环回之无证 GET 亦 200（唯写路由受 owner 闸）。"""
    r = _get(client, remote="10.9.9.9")
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["readonly"] is True


# ---------- ⑤ pending ⛔ 可派 ----------

def test_pending_not_dispatchable(client):
    cards = _get(client).get_json()["cards"]
    pending = [c for c in cards if c["status"] == "pending"]
    active = [c for c in cards if c["status"] == "active"]
    assert len(pending) == 18 and len(active) == 2, (len(pending), len(active))
    for c in pending:
        assert c["dispatchable"] is False, (c["id"], c["status"])
    for c in active:
        assert c["dispatchable"] is True, (c["id"], c["status"])
    assert all(c["dispatchable"] is (c["status"] == "active") for c in cards)


# ---------- ⑥ 源缺 ／ 空 ／ 坏 ⇒ 200 ＋ 显因 ＋ 空 ----------

def test_missing_source_returns_200_empty_state(tmp_path, monkeypatch):
    missing = tmp_path / "absent_registry.json"
    monkeypatch.setenv(REG.REGISTRY_SOURCE_ENV, str(missing))
    r = _get(_app().test_client())
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is False
    assert d["state"] == "missing", d
    assert d["error"] == "registry_source_missing", d
    assert d["counts"] == {"total": 0, "active": 0, "pending": 0}, d["counts"]
    assert d["cards"] == [], u"源缺 ⛔ 以假卡充数"
    assert d["generated_at"] is None, d["generated_at"]
    assert Path(str(d["source"])).name == missing.name, d["source"]
    assert Path(str(d["source"])).name != REG.PILOT_BASENAME, u"缺时 ⛔ 回落到真源"


def test_empty_source_returns_200_empty_state(tmp_path, monkeypatch):
    p = tmp_path / "empty_registry.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(REG.REGISTRY_SOURCE_ENV, str(p))
    d = _get(_app().test_client()).get_json()
    assert d["ok"] is True
    assert d["state"] == "empty", d
    assert d["counts"] == {"total": 0, "active": 0, "pending": 0}
    assert d["cards"] == [], u"空册 ⛔ 假卡"
    assert d["generated_at"], u"件在则有刻"


def test_corrupt_source_returns_200_invalid_state(tmp_path, monkeypatch):
    p = tmp_path / "corrupt_registry.json"
    p.write_text("{ not json", encoding="utf-8")
    monkeypatch.setenv(REG.REGISTRY_SOURCE_ENV, str(p))
    r = _get(_app().test_client())
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is False
    assert d["state"] == "invalid", d
    assert d["error"] == "registry_source_invalid", d
    assert d["counts"] == {"total": 0, "active": 0, "pending": 0}
    assert d["cards"] == []


# ---------- ④ 白名单：陌生 ／ 敏感键 ⛔ 外泄 ----------

def test_secret_keys_not_passed_through(tmp_path, monkeypatch):
    p = tmp_path / "dirty_registry.json"
    p.write_text(json.dumps([{
        "id": "seat:dirty", "kind": "seat", "name": "脏卡", "class": "本机席",
        "status": "pending", "control_plane": "paseo", "view": "paseo-ui",
        "access_level": "L3", "api_key": "sk-SENTINEL-REGISTRY",
        "token": "SENTINEL-TOKEN", "secret": "SENTINEL-SECRET",
    }], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv(REG.REGISTRY_SOURCE_ENV, str(p))
    r = _get(_app().test_client())
    d = r.get_json()
    assert d["counts"] == {"total": 1, "active": 0, "pending": 1}, d["counts"]
    card = d["cards"][0]
    for bad in ("api_key", "token", "secret"):
        assert bad not in card, (bad, sorted(card))
    for sentinel in ("sk-SENTINEL-REGISTRY", "SENTINEL-TOKEN", "SENTINEL-SECRET"):
        assert sentinel not in r.get_data(as_text=True), u"敏感值外泄：%s" % sentinel


# ---------- ⑤ 装包 seed：payload 无 data/tmp 时须回落 config/pa ----------

def test_seed_config_fallback_when_data_tmp_missing(tmp_path, monkeypatch):
    seed = tmp_path / "config" / "pa" / REG.PILOT_BASENAME
    seed.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "config" / "pa" / REG.PILOT_BASENAME, seed)
    monkeypatch.setattr(REG, "_repo_root", lambda: tmp_path)
    monkeypatch.delenv(REG.REGISTRY_SOURCE_ENV, raising=False)
    d = REG.build_registry()
    assert d["state"] == "ok", d
    assert d["counts"] == {"total": 20, "active": 2, "pending": 18}, d["counts"]
    assert "config/pa/" in d["source"], d["source"]
