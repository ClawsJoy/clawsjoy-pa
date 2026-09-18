# -*- coding: utf-8 -*-
"""X-11 层 1：归档正文落服务端（POST /v9/pa/archive + GET /v9/pa/archive/<id>）。

2026-09-18 老板/DS 拍 A（Windows 起本机网关 + 端口错峰）；本文件只测**端点语义与反例**。
纪律（方案 §三/§四）：按 id 合并 · 只碰 archived · 写后读回确认 · 失败零写入 ·
**假成交必须报错**（不得假装成功）· 查不到返 404（不拿空对象冒充）· 幂等。
"""
import sys

sys.path.insert(0, ".")
import pytest
from flask import Flask

from core.pa.gateway_routes import register_pa_routes
from core.pa.threads import ThreadStore


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "pa"
    monkeypatch.setenv("PA_DATA_DIR", str(d))
    return d


@pytest.fixture()
def client(data_dir):
    app = Flask(__name__)
    register_pa_routes(app)
    return app.test_client()


def _store_path(data_dir, uid):
    return data_dir / ("threads_%s.json" % uid)


def _items():
    return [
        {"id": "pa_a", "title": "会话 A", "archived_at": "2026-09-18T01:00:00Z",
         "msgs": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "在"}]},
        {"id": "pa_b", "title": "会话 B", "archived_at": "2026-09-18T02:00:00Z",
         "msgs": [{"role": "user", "content": "盘点项目"}]},
    ]


# ---------- 正例 + 读端点 ----------

def test_post_archive_ok_and_readback(client, data_dir):
    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": _items()})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True
    assert d["written"] == 2 and d["archived_total"] == 2
    assert str(_store_path(data_dir, "u1")) == d["path"]

    # 落盘真存在（不只看响应）
    st = ThreadStore(str(data_dir)).load("u1")
    ids = [x["id"] for x in st["archived"]]
    assert ids == ["pa_a", "pa_b"]

    # 读端点能取回**正文**
    g = client.get("/v9/pa/archive/pa_a?user_id=u1")
    assert g.status_code == 200
    item = g.get_json()["item"]
    assert item["id"] == "pa_a" and len(item["msgs"]) == 2
    assert item["msgs"][1]["content"] == "在"


def test_get_archive_not_found_404_no_empty_object(client, data_dir):
    client.post("/v9/pa/archive", json={"user_id": "u1", "items": _items()})
    g = client.get("/v9/pa/archive/pa_nope?user_id=u1")
    assert g.status_code == 404
    d = g.get_json()
    assert d["ok"] is False and d["error"] == "archive_not_found"
    assert "item" not in d, "查不到不得拿空对象冒充"


# ---------- 反例 ①：items 为空 ⇒ 400 且零写入 ----------

def test_empty_items_400_and_zero_write(client, data_dir):
    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": []})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False
    assert not _store_path(data_dir, "u1").exists(), "被拒的请求不得留下任何文件"


# ---------- 反例 ②：项缺 id ⇒ 400 且零写入 ----------

def test_item_without_id_400_and_zero_write(client, data_dir):
    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": [{"title": "没有 id", "msgs": []}]})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False
    assert not _store_path(data_dir, "u1").exists()


def test_item_with_blank_id_400_and_zero_write(client, data_dir):
    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": [{"id": "   ", "msgs": []}]})
    assert r.status_code == 400
    assert not _store_path(data_dir, "u1").exists()


def test_bad_batch_does_not_partially_write(client, data_dir):
    """**半截写入**：合法项在前、非法项在后 ⇒ 仍必须零写入（校验全部通过才 save）。"""
    bad = [{"id": "pa_ok", "msgs": [{"role": "user", "content": "x"}]}, {"title": "缺 id"}]
    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": bad})
    assert r.status_code == 400
    assert not _store_path(data_dir, "u1").exists(), "不得先写一半再报错"


# ---------- 反例 ③（假成交）：save 静默失效 ⇒ 必须报「读回不一致」 ----------

def test_silent_save_failure_must_not_report_ok(client, monkeypatch, data_dir):
    def _noop_save(self, user_id, state):
        return {"ok": True, "path": str(self._path(user_id))}  # 说成功，实际一个字没写

    monkeypatch.setattr(ThreadStore, "save", _noop_save)
    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": _items()})
    assert r.status_code == 500
    d = r.get_json()
    assert d["ok"] is False, "静默失效不得返回 ok:True（假成交红线）"
    assert "读回不一致" in d["error"] and d["written"] == 0


# ---------- 语义 1：按 id 合并 + 幂等 ----------

def test_merge_by_id_then_idempotent(client, data_dir):
    a = _items()
    r1 = client.post("/v9/pa/archive", json={"user_id": "u1", "items": a})
    assert r1.get_json()["written"] == 2 and r1.get_json()["archived_total"] == 2

    b = [{"id": "pa_c", "title": "会话 C", "archived_at": "2026-09-18T03:00:00Z", "msgs": []}]
    r2 = client.post("/v9/pa/archive", json={"user_id": "u1", "items": b})
    assert r2.get_json()["written"] == 1 and r2.get_json()["archived_total"] == 3

    # 重发同一批 ⇒ 幂等：written=0，总数不变
    r3 = client.post("/v9/pa/archive", json={"user_id": "u1", "items": b})
    assert r3.get_json()["written"] == 0 and r3.get_json()["archived_total"] == 3

    # 合并**不覆盖**既有条：A 的正文还在
    st = ThreadStore(str(data_dir)).load("u1")
    by = {x["id"]: x for x in st["archived"]}
    assert set(by) == {"pa_a", "pa_b", "pa_c"}
    assert len(by["pa_a"]["msgs"]) == 2


def test_same_id_updates_in_place_no_duplicate(client, data_dir):
    client.post("/v9/pa/archive", json={"user_id": "u1", "items": _items()})
    upd = [{"id": "pa_a", "title": "会话 A（改）", "archived_at": "2026-09-18T01:00:00Z",
            "msgs": [{"role": "user", "content": "新正文"}]}]
    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": upd})
    assert r.get_json()["written"] == 1 and r.get_json()["archived_total"] == 2
    st = ThreadStore(str(data_dir)).load("u1")
    assert [x["id"] for x in st["archived"]].count("pa_a") == 1, "同 id 不得重复追加"


# ---------- 语义 2：只碰 archived（不动 threads / 不动单线程口径） ----------

def test_does_not_touch_threads_or_single_thread_contract(client, data_dir):
    seed = {"mode": "chat", "threads": [{"id": "pa_cur", "msgs": [{"role": "user", "content": "在"}]}],
            "activeThread": "pa_cur"}
    ThreadStore(str(data_dir)).save("u1", dict(seed))

    r = client.post("/v9/pa/archive", json={"user_id": "u1", "items": _items()})
    assert r.status_code == 200

    st = ThreadStore(str(data_dir)).load("u1")
    assert st["threads"] == seed["threads"], "归档端点不得改 threads"
    assert st["activeThread"] == "pa_cur", "归档端点不得改 activeThread"

    # 单线程口径未松动：POST /v9/pa/threads 仍拒绝写入
    p = client.post("/v9/pa/threads", json={"user_id": "u1", "threads": []})
    assert p.status_code == 410 and p.get_json()["ok"] is False


# ---------- 语义 6：user_id 隔离 / 非法 uid ----------

def test_user_id_isolated(client, data_dir):
    """对照式断言：**自己的能取到、别人的取不到** —— 反例证明时发现单边断言会「空转」
    （HEAD 无该路由时也是 404 ⇒ 只断言 404 会在旧版**假通过**）。"""
    client.post("/v9/pa/archive", json={"user_id": "u1", "items": _items()})
    mine = client.get("/v9/pa/archive/pa_a?user_id=u1")
    assert mine.status_code == 200 and mine.get_json()["item"]["id"] == "pa_a"
    other = client.get("/v9/pa/archive/pa_a?user_id=u2")
    assert other.status_code == 404, "别的 user_id 不得看到 u1 的归档"
    assert other.get_json()["error"] == "archive_not_found", "必须是我们自己的 404 语义（不是 Flask 默认 404）"


@pytest.mark.parametrize("bad", ["", None, "..", "../etc", "a/b", "a\\b", "C:x"])
def test_invalid_user_id_400_zero_write(client, data_dir, bad):
    r = client.post("/v9/pa/archive", json={"user_id": bad, "items": _items()})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False
    assert not data_dir.exists() or not list(data_dir.glob("threads_*.json"))