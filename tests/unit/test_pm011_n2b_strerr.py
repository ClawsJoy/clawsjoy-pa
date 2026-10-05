# -*- coding: utf-8 -*-
r"""PM-011 · N2b（2026-09-30 · CW b2a5182）：`core\pa\gateway_routes.py` 同族 **6 处**
`jsonify({... "error": str(<例外>)})` —— **校形状 ＋ ⛔ 不回异常原文**。

PM 裁（原话要点）：
  (1) 范围 ＝ 同批 6 处（同文件同形；一次改齐比留尾巴好）；
  (2) ⭐ 纪律：**6 处必须各有专属反例门**，⛔ 不许一处有齿、五处搭车 —— 防的正是「全红一起亮」的装饰层；
  (3) 反例门判据：**响应体 ⛔ 不含任何 Python 异常类名**；
  (4) 严重度排序按**出口面**（原文泄漏 ＞ 含糊体），⛔ 不按发现顺序。

6 处（改前行号 → 路由）：
  :979   `pa_proxy`            上游 HTTPError 分支（用 `str(e)`）
  :1031  `pa_caliber_change`   通用 500 兜底（用 `str(_e)`）
  :1309  `pa_ppt_comments_get` 通用 500 兜底
  :1325  `pa_ppt_comments_post` 通用 500 兜底 ＋ 形状吞（非空 list 会 `.get` ⇒ AttributeError）
  :1337  `pa_artifact_thumbs_post` 同上
  :1377  `pa_kb_mapping`       通用 500 兜底

外加**同函数相邻**两处（我自报，见件 §扫描口径更正）：
  :981   `pa_proxy` 通用分支（`err("… %s" % str(e))` —— ⛔ 不是 jsonify，故我上一版扫描的 28 处名单**漏了它**）
  :926   `pa_proxy` 的 `p = request.json or {}` 形状吞

本件**不 mock 被审对象**：走真路由（Flask `test_client` ＋ 临时 `PA_DATA_DIR`）；
只有**被调用的下游模块**（ppt_comments ／ artifact_thumbs ／ build_kb_mapping ／ urlopen）被替换成会抛异常的桩。
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]

# ⛔ 响应体里不得出现的「Python 异常类名」族
_CLS_RE = re.compile(r"\b(?:[A-Z][A-Za-z]*Error|Exception|AttributeError|Traceback)\b")
LITERAL_FORBIDDEN = (
    "Traceback", "has no attribute", "object has no attribute",
    "AttributeError", "TypeError", "KeyError", "ValueError", "RuntimeError",
    "HTTPError", "URLError", "ConnectionRefusedError", "Internal server error",
)


def assert_clean(body: str, tag: str):
    for k in LITERAL_FORBIDDEN:
        assert k not in body, "%s：响应体里出现 %r ／ %s" % (tag, k, body[:200])
    m = _CLS_RE.search(body)
    assert not m, "%s：响应体里出现异常类名 %r ／ %s" % (tag, m.group(0), body[:200])


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path / "pa" / "vault"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    # ⭐ 与活服务同链（否则 500 走裸 Werkzeug 页 ⇒ 判据与线上不同形）
    from core.lib.error_handler import register_error_handlers
    register_error_handlers(app)
    from core.pa.gateway_routes import register_pa_routes
    register_pa_routes(app)
    return app.test_client()


# ============================== :979 proxy · 上游 HTTPError ==============================

def test_979_proxy_http_error_keeps_status_and_has_no_classname(client, monkeypatch):
    def boom(url, *a, **k):
        raise urllib.error.HTTPError("http://127.0.0.1:3890/kv/all", 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    r = client.post("/v9/pa/proxy", json={"method": "GET", "path": "/kv/all", "user_id": "t"})
    assert r.status_code == 404, "上游状态必须如实回传（实测 %s）" % r.status_code
    d = r.get_json() or {}
    assert d.get("ok") is False and d.get("status") == 404
    e = str(d.get("error") or "")
    assert "404" in e and "Not Found" in e, "上游状态行没保留：%r" % e
    assert_clean(r.data.decode("utf-8", "replace"), ":979")


# ============================== :981 proxy · 通用失败分支 ==============================

def test_981_proxy_generic_failure_is_sanitized(client, monkeypatch):
    def boom(url, *a, **k):
        raise ConnectionRefusedError("refused-by-test-981")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    r = client.post("/v9/pa/proxy", json={"method": "GET", "path": "/kv/all", "user_id": "t"})
    assert r.status_code == 400
    d = r.get_json() or {}
    assert d.get("ok") is False
    body = r.data.decode("utf-8", "replace")
    assert "refused-by-test-981" not in body, ":981 把异常原文回客户端了：%s" % body[:200]
    assert d.get("error") == "proxy 调用失败（内部错误，已记日志）"
    assert_clean(body, ":981")


# ============================== :926 proxy · 形状 ==============================

@pytest.mark.parametrize("body", [[], [1], "x", 0], ids=["list-empty", "list", "str", "int"])
def test_926_proxy_body_shape_400(client, body):
    r = client.post("/v9/pa/proxy", json=body)
    assert r.status_code == 400, "形状错应 400（实测 %s）" % r.status_code
    d = r.get_json() or {}
    assert d.get("ok") is False
    assert "body 需要 JSON 对象" in str(d.get("error") or ""), d.get("error")


# ============================== :1031 caliber/change ==============================

def test_1031_caliber_change_internal_is_sanitized(client):
    # why 传对象 ⇒ 下游 `.strip()` ⇒ AttributeError（改前会把 "'dict' object has no attribute 'strip'" 回客户端）
    r = client.post("/v9/pa/caliber/change",
                    json={"id": "z1", "status": "unverified", "owner": "t", "why": {"a": 1}})
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    assert "'dict' object has no attribute" not in body, ":1031 泄漏异常原文：%s" % body[:200]
    assert_clean(body, ":1031")


def test_1031_caliber_change_body_shape_400(client):
    r = client.post("/v9/pa/caliber/change", json=[])
    assert r.status_code == 400
    d = r.get_json() or {}
    assert d.get("ok") is False and "body 需要 JSON 对象" in str(d.get("error") or "")


def test_1031_declared_validation_still_readable(client):
    """⭐ 候选面 ≠ 病面：`CaliberStoreError` 是**下游自陈的校验消息**（400 面），⛔ 不该被一起抹掉。"""
    r = client.post("/v9/pa/caliber/change", json={})
    assert r.status_code == 400
    assert "id" in str((r.get_json() or {}).get("error") or "")


# ============================== :1309 ppt/comments GET ==============================

def test_1309_ppt_comments_get_internal_is_sanitized(client, monkeypatch):
    from core.pa import ppt_comments as _pc

    def boom(*a, **k):
        raise RuntimeError("boom-internal-1309")

    monkeypatch.setattr(_pc, "list_comments", boom)
    r = client.get("/v9/pa/ppt/comments?deck=d1")
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    # ⭐ 反向断言：只查「类名」是不够的 —— 任意内部原文同样不许进响应体
    assert "boom-internal-1309" not in body, ":1309 把异常原文回客户端了：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == "ppt/comments: 读内部错误（已记日志）"
    assert_clean(body, ":1309")


# ============================== :1325 ppt/comments POST ==============================

def test_1325_ppt_comments_post_shape_400(client):
    r = client.post("/v9/pa/ppt/comments", json=[1])
    assert r.status_code == 400, "非空 list 形状 ⇒ 改前 AttributeError ⇒ 500；现应 400（实测 %s）" % r.status_code
    assert "body 需要 JSON 对象" in str((r.get_json() or {}).get("error") or "")


def test_1325_ppt_comments_post_internal_is_sanitized(client, monkeypatch):
    from core.pa import ppt_comments as _pc

    def boom(*a, **k):
        raise RuntimeError("boom-internal-1325")

    monkeypatch.setattr(_pc, "add_comment", boom)
    r = client.post("/v9/pa/ppt/comments", json={"deck": "d1", "page_index": 1, "comment": "x"})
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    # ⭐ 反向断言：只查「类名」是不够的 —— 任意内部原文同样不许进响应体
    assert "boom-internal-1325" not in body, ":1325 把异常原文回客户端了：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == "ppt/comments: 写内部错误（已记日志）"
    assert_clean(body, ":1325")


# ============================== :1337 artifact/thumbs POST ==============================

def test_1337_thumbs_shape_400(client):
    r = client.post("/v9/pa/artifact/thumbs", json=[1])
    assert r.status_code == 400
    assert "body 需要 JSON 对象" in str((r.get_json() or {}).get("error") or "")


def test_1337_thumbs_internal_is_sanitized(client, monkeypatch):
    from core.pa import artifact_thumbs as _at

    def boom(*a, **k):
        raise RuntimeError("boom-internal-1337")

    monkeypatch.setattr(_at, "save_thumbs", boom)
    r = client.post("/v9/pa/artifact/thumbs", json={"deck": "d1", "files": []})
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    # ⭐ 反向断言：只查「类名」是不够的 —— 任意内部原文同样不许进响应体
    assert "boom-internal-1337" not in body, ":1337 把异常原文回客户端了：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == "artifact/thumbs: 内部错误（已记日志）"
    assert_clean(body, ":1337")


# ============================== :1377 kb_mapping ==============================

def test_1377_kb_mapping_internal_is_sanitized(client, monkeypatch):
    import core.pa.gateway_routes as _gr

    def boom(*a, **k):
        raise RuntimeError("boom-internal-1377")

    monkeypatch.setattr(_gr, "build_kb_mapping", boom)
    r = client.get("/v9/pa/kb_mapping")
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    # ⭐ 反向断言：只查「类名」是不够的 —— 任意内部原文同样不许进响应体
    assert "boom-internal-1377" not in body, ":1377 把异常原文回客户端了：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == "kb_mapping: 内部错误（已记日志）"
    assert_clean(body, ":1377")