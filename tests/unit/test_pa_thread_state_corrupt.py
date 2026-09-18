# -*- coding: utf-8 -*-
"""X-17 止损反例证明：坏状态必须 fail-loud，**不得**回落空状态。

背景（受控复现，见 codex/2026-09-18-pa-engineering-self-audit.md 证据 5）：
`ThreadStore.load()` 曾把「文件存在但读不动」与「文件不存在」返回成**同一个空状态**，
`POST /v9/pa/archive` 拿它当**合并基线** ⇒ 一次写即清空历史归档与 threads；
且端点自带的「读回确认」只校验「本次送来 id ⊆ 回读 id」⇒ 只测新增、不测保留 ⇒ 返回 200/ok（假成交）。

本文件即**改前必假、改后必真**的反例证明：
  · 改前（HEAD）：`test_损坏状态_追加必须报错且零写入` 会红（200 假成交 + 文件被覆盖）
  · 改后：全绿
"""
import json
import sys

sys.path.insert(0, ".")
import pytest
from flask import Flask

from core.pa.gateway_routes import register_pa_routes
from core.pa.threads import ThreadStore, ThreadStoreCorrupt

UID = "u1"


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


def _path(data_dir):
    return data_dir / ("threads_%s.json" % UID)


def _state(n=3):
    return {
        "mode": "chat",
        "threads": [{"id": "t1", "title": "在聊",
                        "msgs": [{"role": "user", "content": "hi"}]}],
        "activeThread": "t1",
        "archived": [
            {"id": "old_%d" % i, "title": "历史 %d" % i,
             "archived_at": "2026-09-0%d" % (i + 1),
             "msgs": [{"role": "user", "content": "旧 %d" % i}]}
            for i in range(n)
        ],
    }


def _seed(data_dir, n=3):
    ThreadStore(str(data_dir)).save(UID, _state(n))


def _item(iid="new_1"):
    return {"id": iid, "title": "新归档", "archived_at": "2026-09-18",
            "msgs": [{"role": "user", "content": "新"}]}


def _post(client, item=None):
    return client.post("/v9/pa/archive",
                       json={"user_id": UID, "items": [item or _item()]})


def _ids(data_dir):
    return [a["id"] for a in json.loads(_path(data_dir).read_text(encoding="utf-8"))["archived"]]


# ------------------------------------------------------------ 反例主体
def test_损坏状态_追加必须报错且零写入(data_dir, client):
    """**核心反例**：状态文件损坏时，追加归档必须报错，且**不写一个字**。"""
    _seed(data_dir)
    p = _path(data_dir)
    good = p.read_bytes()
    p.write_bytes(good[: len(good) // 2])       # 截断 ⇒ 坏文件（模拟非原子写被打断）
    corrupt = p.read_bytes()
    assert corrupt != good

    r = _post(client)

    assert r.status_code == 409, "坏状态必须 fail-loud（不得 200 假成交）"
    body = r.get_json()
    assert body["ok"] is False
    assert body["error"] == "thread_state_corrupt"
    assert body.get("written") == 0
    assert p.read_bytes() == corrupt, "坏状态不得被写入（零写入）"

    # 恢复路径不被阻断：备份放回 ⇒ 追加照常成功，且**既有 3 条仍在**
    p.write_bytes(good)
    r2 = _post(client)
    assert r2.status_code == 200
    assert r2.get_json()["archived_total"] == 4
    assert _ids(data_dir) == ["old_0", "old_1", "old_2", "new_1"]


def test_结构不符也视为损坏(data_dir, client):
    """合法 JSON 但结构不符（threads 非 list）同样是坏状态 ⇒ 报错且零写入。"""
    _seed(data_dir)
    p = _path(data_dir)
    p.write_text(json.dumps({"mode": "chat", "threads": "oops",
                             "archived": [{"id": "z1", "msgs": []}]},
                            ensure_ascii=False), encoding="utf-8")
    before = p.read_bytes()

    r = _post(client)

    assert r.status_code == 409
    assert r.get_json()["error"] == "thread_state_corrupt"
    assert p.read_bytes() == before, "零写入"


def test_空文件也视为损坏(data_dir, client):
    """空文件（截断到 0 字节）不得被当成「新用户」⇒ 必须报错。"""
    _seed(data_dir)
    _path(data_dir).write_bytes(b"")
    assert _post(client).status_code == 409


def test_文件不存在仍是空状态_新用户不受影响(data_dir, client):
    """**反向护栏**：不得把「文件不存在」也判成损坏（否则新用户全挂）。"""
    r = client.get("/v9/pa/threads?user_id=" + UID)
    assert r.status_code == 200
    assert r.get_json()["threads"] == []


def test_正常状态_追加仍然保留既有(data_dir, client):
    """回归：合法状态下合并语义不变（3 -> 4，既有条不丢）。"""
    _seed(data_dir)
    r = _post(client)
    assert r.status_code == 200
    assert r.get_json()["archived_total"] == 4


# ------------------------------------------------------------ 另两个调用方
def test_按_id取归档_损坏时不得谎报404(data_dir, client):
    """损坏 ⇒ 409「读不动」；**不得**返 404「确实没这条」（那是假警报）。"""
    _seed(data_dir)
    p = _path(data_dir)
    good = p.read_bytes()
    p.write_bytes(good[: len(good) // 2])

    r = client.get("/v9/pa/archive/old_0?user_id=" + UID)
    assert r.status_code == 409, "读不动 != 不存在"
    assert r.get_json()["error"] == "thread_state_corrupt"

    # 对照：状态合法、id 确实不存在 ⇒ 仍必须 404（本改不得把 404 吞掉）
    p.write_bytes(good)
    assert client.get("/v9/pa/archive/nope?user_id=" + UID).status_code == 404


def test_GET_threads_损坏时fail_loud且前端可安全跳过(data_dir, client):
    """前端是 `if(r.ok)` ⇒ 非 200 会被安全跳过（不炸页面），但**不得**回空状态假装正常。"""
    _seed(data_dir)
    _path(data_dir).write_text("{ 半截", encoding="utf-8")

    r = client.get("/v9/pa/threads?user_id=" + UID)
    assert r.status_code == 409
    assert r.get_json()["ok"] is False


# ------------------------------------------------------------ 单元层
def test_load_单元_抛类型化异常且带出处(tmp_path):
    p = tmp_path / "threads_u9.json"
    p.write_text("{ 坏", encoding="utf-8")
    with pytest.raises(ThreadStoreCorrupt) as ei:
        ThreadStore(str(tmp_path)).load("u9")
    assert ei.value.path.endswith("threads_u9.json")
    assert ei.value.reason


def test_load_单元_不存在时不抛(tmp_path):
    assert ThreadStore(str(tmp_path)).load("nobody")["threads"] == []