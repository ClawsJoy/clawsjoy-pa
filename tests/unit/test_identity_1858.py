# -*- coding: utf-8 -*-
u"""本机身份之「铸」与「归一」（pm_1858 §二 ／ §三 ／ §四）之测 —— 技术总监席 f202f89 · 2026-10-08。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_identity_1858.py -q

正控（事之实）：
  ⒈ 无 owner ＋ 无旧值 ⇒ 铸 `owner_*` **一次** ∧ 二次调用**同值**（⛔ 再铸）∧ 档之形合（schema ／ id ／ created_at ／ source）；
  ⒉ 无 owner ＋ 携 `web_*` 且其 threads 件**非空** ⇒ **认领**该值（`owner.json.id ≡ 该值` · source 照实）；
  ⒊ owner 在 ＋ 携**他** `web_*` ⇒ **仍用 owner**（⛔ 被覆盖）∧ 其 threads 归档**仍归 owner**（⛔ 生他件）；
  ⒋ 认领 ⇒ 旧 threads 件**逐字节**（sha256 同）留底于 `_legacy/` ∧ 活件一字不动；异名归位亦逐字节；
  ⒌ `GET /v9/pa/whoami` ⇒ 唯本机（远机 `403`）∧ 形（owner_id ／ display ／ display_source ／ source ／ claimed_from?）；
  ⒍ `data/v9/pa` 之下 ⛔ 再生 `web_<ms>` 之新件（跑一轮面之流程 ⇒ 件数不增）。

反控（器之牙）：
  ⒎ **空壳**（`threads == []`）⇒ ⛔ 认领（照铸新 owner）∧ 空壳入 `_legacy/`；
  ⒏ owner 档坏 ⇒ **fail-loud**（⛔ 静默另铸 —— 那会静默变成别人）∧ 坏件**原地留着**（⛔ 移走）；
  ⒐ 空 ⛔ 混 缺：无 owner 件 ⇒ `None`（新机之正 · ⛔ 以「无」充「坏」）；画像无「名」⇒ display ＝「本机」∧ 源照实；
  ⒑ 既有之齿 ⛔ 破：`u1` 式之值**直通**（⛔ 触身份）∧ `archive` 缺 `user_id` 仍 `400`。
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as G  # noqa: E402
from core.pa import identity as ID  # noqa: E402

_OWNER_ID = re.compile("^owner_[0-9a-f]{12}$")


def _sha(p):
    return hashlib.sha256(Path(str(p)).read_bytes()).hexdigest()


def _write_threads(d, uid, threads):
    p = Path(str(d)) / ("threads_%s.json" % uid)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = {"mode": "chat", "threads": threads,
           "activeThread": (threads[0]["id"] if threads else None)}
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _item(iid="pa_new"):
    return {"id": iid, "title": "新归档", "archived_at": "2026-10-08",
            "msgs": [{"role": "user", "content": "新"}]}


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "pa"
    monkeypatch.setenv("PA_DATA_DIR", str(d))
    return d


@pytest.fixture()
def client(data_dir):
    app = Flask(__name__)
    G.register_pa_routes(app)
    return app.test_client()


# ---------------------------------------------------------------- 正控 ⒈ 铸一次
def test_铸一次_二次同值(data_dir):
    u"""⒈：无 owner ＋ 无旧值 ⇒ 铸一次 ∧ 二次同值 ∧ 档之形合（⛔ 再铸）。"""
    a = ID.ensure_owner(str(data_dir))
    b = ID.ensure_owner(str(data_dir))
    assert _OWNER_ID.match(a["id"]), a["id"]
    assert a["source"] == ID.SOURCE_MINTED and a["id"] == b["id"], a
    on = json.loads((data_dir / "owner.json").read_text(encoding="utf-8"))
    assert sorted(on) == ["created_at", "id", "schema", "source"], on
    assert on["schema"] == ID.OWNER_SCHEMA and on["created_at"] and on["id"] == a["id"]
    assert (data_dir / "owner.json.writes.jsonl").exists(), u"须走统一出口（留写者台账）"
    before = (data_dir / "owner.json").read_bytes()
    ID.ensure_owner(str(data_dir), hint="web_777")
    assert (data_dir / "owner.json").read_bytes() == before, u"owner 既立 ⇒ ⛔ 再铸"


# ---------------------------------------------------------------- 正控 ⒉ 认领
def test_认领_旧式id(data_dir):
    u"""⒉⒋：携 web_* ∧ 其件非空 ⇒ 认领该值（id ≡ 该值）∧ 逐字节留底 ∧ 活件一字不动。"""
    src = _write_threads(data_dir, "web_1790773805388", [{"id": "t1", "title": "在聊"}])
    before, n0 = _sha(src), src.stat().st_size
    o = ID.ensure_owner(str(data_dir), hint="web_1790773805388")
    assert o["id"] == "web_1790773805388" and o["source"] == ID.SOURCE_CLAIMED, o
    assert o["claimed_from"] == "web_1790773805388"
    on = json.loads((data_dir / "owner.json").read_text(encoding="utf-8"))
    assert on["id"] == "web_1790773805388" and on["source"] == ID.SOURCE_CLAIMED, on
    assert ID.resolve(str(data_dir), hint="web_1790773805388") == "web_1790773805388"
    assert o[u"迁移"]["字节"] == n0 and o[u"迁移"]["sha256"] == before, o[u"迁移"]
    assert _sha(src) == before, u"活件一字不动"
    keep = data_dir / "_legacy" / "threads_web_1790773805388.json"
    assert keep.exists() and _sha(keep) == before, u"旧件留底（⛔ 删 · 可回退）"


# ---------------------------------------------------------------- 正控 ⒊ 恒用 owner
def test_owner既立_他值不可覆盖(data_dir, client):
    u"""⒊：owner 在 ＋ 携他 web_* ⇒ 仍用 owner ∧ 归档仍归 owner ∧ ⛔ 生他件。"""
    o = ID.ensure_owner(str(data_dir))
    r = client.post("/v9/pa/archive", json={"user_id": "web_999", "items": [_item()]})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    want = data_dir / ("threads_%s.json" % o["id"])
    assert str(want) == d["path"], d
    assert not (data_dir / "threads_web_999.json").exists(), u"⛔ 由 hint 定归属"
    assert ID.resolve(str(data_dir), hint="web_999") == o["id"]
    st = json.loads(want.read_text(encoding="utf-8"))
    assert [x["id"] for x in st["archived"]] == ["pa_new"], st


# ---------------------------------------------------------------- 正控 ⒋ 异名归位
def test_归位之异名_逐字节(data_dir):
    u"""⒋：异名归位 ⇒ 新名逐字节同（sha256 同）∧ 旧件入 _legacy/（⛔ 未校先移）。"""
    p = _write_threads(data_dir, "web_1", [{"id": "t", "title": "旧"}])
    b = p.read_bytes()
    out = ID.migrate(str(data_dir), "owner_zz", old_id="web_1")
    dst = data_dir / "threads_owner_zz.json"
    assert dst.read_bytes() == b and _sha(dst) == out["sha256"], out
    assert not p.exists() and out["移"] is True, out
    assert (data_dir / "_legacy" / "threads_web_1.json").read_bytes() == b


# ---------------------------------------------------------------- 正控 ⒌ whoami 之形
def test_whoami_唯本机_形(data_dir, client):
    u"""⒌：远机 403；本机 ⇒ 形合 ∧ display 为人话（⛔ 机器号 ／ 内部缩写上屏）。"""
    r = client.get("/v9/pa/whoami", environ_base={"REMOTE_ADDR": "10.0.0.5"})
    assert r.status_code == 403, r.status_code
    g = client.get("/v9/pa/whoami")
    assert g.status_code == 200, g.get_data(as_text=True)
    d = g.get_json()
    assert d["ok"] is True and _OWNER_ID.match(d["owner_id"]), d
    assert d["source"] == ID.SOURCE_MINTED and d["owner_file"] == "owner.json"
    assert d["display"] == u"本机" and d["display_source"] == "default", d
    assert "claimed_from" not in d, d
    for bad in ("web_", "owner_", "core/pa", "threads_", ".json"):
        assert bad not in d["display"], (bad, d["display"])


def test_whoami_认领之形(data_dir, client):
    u"""⒌：携 web_*（件非空）⇒ claimed_from 照实 ∧ 面之辞仍取 display（⛔ 自拼）。"""
    _write_threads(data_dir, "web_7", [{"id": "t", "title": "在聊"}])
    d = client.get("/v9/pa/whoami?user_id=web_7").get_json()
    assert d["owner_id"] == "web_7" and d["source"] == ID.SOURCE_CLAIMED, d
    assert d["claimed_from"] == "web_7" and d["display"] == u"本机", d


def test_不携hint_旧史看得见(data_dir, client):
    u"""⒌⒐：不携 hint ⇒ 铸新 owner ∧ 盘上旧史**逐件照实列**（⛔ 窃 ／ ⛔ 静默）。"""
    p = _write_threads(data_dir, "web_7", [{"id": "t", "title": "在聊"}])
    b0 = p.read_bytes()
    d = client.get("/v9/pa/whoami").get_json()
    assert _OWNER_ID.match(d["owner_id"]), d
    assert d[u"未认领之旧史"] == [{"件": "threads_web_7.json", "字节": p.stat().st_size}], d
    assert p.read_bytes() == b0, u"旧史一字未动（⛔ 窃他人之史）"


# ---------------------------------------------------------------- 正控 ⒍ ⛔ 再生 web 件
def test_面之流程_不生web新件(data_dir, client):
    u"""⒍：跑一轮面之流程（四端点 · 四个不同 web_* 之值）⇒ threads 件数**不增**。"""
    client.post("/v9/pa/archive", json={"user_id": "web_111", "items": [_item("a1")]})
    client.get("/v9/pa/threads?user_id=web_222")
    client.post("/v9/pa/session_model",
                json={"user_id": "web_333", "model": "remote:deepseek-v4-flash"})
    client.get("/v9/pa/whoami?user_id=web_444")
    js = sorted(p.name for p in data_dir.glob("threads_*.json"))
    assert len(js) == 1 and js[0].startswith("threads_owner_"), js
    for bad in ("web_111", "web_222", "web_333", "web_444"):
        assert not (data_dir / ("threads_%s.json" % bad)).exists(), bad


# ---------------------------------------------------------------- 反控 ⒎ 空壳
def test_空壳不认领_入legacy(data_dir):
    u"""⒎：空壳（threads == []）⇒ ⛔ 认领（照铸新 owner）∧ 空壳入 _legacy/。"""
    p = _write_threads(data_dir, "web_5", [])
    n0 = p.stat().st_size
    o = ID.ensure_owner(str(data_dir), hint="web_5")
    assert _OWNER_ID.match(o["id"]) and o["source"] == ID.SOURCE_MINTED, o
    assert o[u"清壳"] == [{"件": "threads_web_5.json", "字节": n0, "移": True}], o[u"清壳"]
    assert not p.exists(), u"空壳须入 _legacy/（⛔ 再积）"
    assert (data_dir / "_legacy" / "threads_web_5.json").exists()
    assert ID.resolve(str(data_dir), hint="web_5") == o["id"], u"归一仍落 owner"


# ---------------------------------------------------------------- 反控 ⒏ 档坏 fail-loud
def test_owner档坏_fail_loud(data_dir, client):
    u"""⒏：档坏（结构不符 ／ JSON 非法）⇒ fail-loud ∧ 坏件**原地留着** ∧ ⛔ 另铸。"""
    data_dir.mkdir(parents=True, exist_ok=True)
    p = data_dir / "owner.json"
    p.write_text(json.dumps({"id": "", "schema": "pa.owner/1"}), encoding="utf-8")
    before = p.read_bytes()
    with pytest.raises(ID.OwnerCorrupt):
        ID.ensure_owner(str(data_dir))
    r = client.get("/v9/pa/whoami")
    assert r.status_code == 409, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is False and d["error"] == "owner_state_corrupt", d
    assert p.read_bytes() == before, u"坏件须原地留着（⛔ 隔离移走 ⇒ 下次就另铸 ⇒ 静默变成别人）"
    assert not list(data_dir.glob("owner.json.*")), u"⛔ 另铸"
    p.write_text("{" + "not json", encoding="utf-8")
    with pytest.raises(ID.OwnerCorrupt):
        ID.ensure_owner(str(data_dir))


# ---------------------------------------------------------------- 反控 ⒐ 空 ⛔ 混 缺
def test_读面之实(data_dir):
    u"""⒐：不存在 ⇒ None（⛔ 以「无」充「坏」）；空壳 ⇒ False；有史 ⇒ True。"""
    assert ID.read_owner(str(data_dir)) is None
    assert ID.threads_state_of(str(data_dir), "web_x") is None
    _write_threads(data_dir, "web_x", [])
    assert ID.threads_state_of(str(data_dir), "web_x") is False
    _write_threads(data_dir, "web_y", [{"id": "t"}])
    assert ID.threads_state_of(str(data_dir), "web_y") is True
    assert ID.is_client_label("web_1") and not ID.is_client_label("u1")
    assert not ID.is_client_label("web_") and not ID.is_client_label("")


def test_display_画像有名则其名(data_dir):
    u"""⒐：画像有「名」之实 ⇒ 其名；⛔ 无 ⇒ 「本机」；读不动 ⇒ 源照实 unreadable。"""
    assert ID.display_of(str(data_dir)) == (u"本机", "default")
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "profile.json").write_text(json.dumps(
        {"entries": [{"id": "e1", "domain": "fact", "key": u"称呼",
                     "value": u"老板", "status": "confirmed"}]}, ensure_ascii=False), encoding="utf-8")
    assert ID.display_of(str(data_dir)) == (u"老板", "profile")
    (data_dir / "profile.json").write_text("{" + "bad", encoding="utf-8")
    assert ID.display_of(str(data_dir)) == (u"本机", "unreadable")


# ---------------------------------------------------------------- 反控 ⒑ 旧齿 ⛔ 破
def test_兼容_u1式直通(data_dir, client):
    u"""⒑：u1 式之值**直通**（⛔ 触身份 —— 承 pm_1858 §四.3 旧齿之保）。"""
    assert ID.resolve(str(data_dir), "u1") == "u1"
    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": [_item("x1")]})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert (data_dir / "threads_u1.json").exists()
    assert not (data_dir / "owner.json").exists(), u"u1 式之值 ⛔ 触身份"
    assert client.get("/v9/pa/session_model?user_id=u2").get_json()["model"] == ""


def test_缺与非法之值(client):
    u"""⒑：archive 缺 user_id 仍 400；whoami 之 user_id 非法 ⇒ 400 显因（⛔ 静默铸）。"""
    r = client.post("/v9/pa/archive", json={"items": [_item()]})
    assert r.status_code == 400 and not r.get_json()["ok"], r.get_json()
    g = client.get("/v9/pa/whoami?user_id=a/b")
    assert g.status_code == 400 and not g.get_json()["ok"], g.get_json()
