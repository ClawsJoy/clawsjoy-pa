# -*- coding: utf-8 -*-
r"""PM-011 · 第 1 批（N5-GET）· `core\gateway\file_center.py` 专属门（CW b2a5182 · 2026-09-30）。

PM 12:0x 裁（§二／§三）：第 1 批 ＝ 本文件（现役 ＋ 文件面 ＋ 读文件内容/下载 ⇒ 最重）；
  · 口径 **⒜ 整文件统一 400**（含 `session_id` 两处一并改）⇒ 消掉同文件两种风格；
  · 判据：**空查询 ⇒ 400（缺 user_id）**，⛔ 不许默认 `"default"`。

⭐ 一处判据一个源：`_query`/`_need`/`_body`/`_need_text` ＋ 唯一 400 装饰器 `_bad_400`。
⚠ **分类**（本件把它机检钉住，⛔ 不当说辞）：
  · 「调用方输入不合格」（缺必填／非法路径／非法文件名／内容超限）⇒ **400**；
  · 「业务/资源状态」（文件不存在／沙箱不存在／内部异常）⇒ **200 ＋ `success:false`**（承 PM 早先裁「200+notok ⛔ 非假绿」）。
⚠ 本件全程 hermetic（`_get_sandbox_base` 指向 `tmp_path`）⇒ ⛔ 不碰生产沙箱。
"""
from __future__ import annotations

import io
import os

import pytest
from flask import Flask

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FC = os.path.join(ROOT, "core", "gateway", "file_center.py")
BAD_JSON = b"{not json"
# 「业务/资源状态」类 —— ⛔ 允许 200+notok（⛔ 不是「调用方输入不合格」）
BUSINESS = ("文件不存在", "沙箱不存在")


def _err(r):
    return (r.get_json() or {}).get("error") or ""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    from core.lib.error_handler import register_error_handlers

    register_error_handlers(app)

    import core.lib.gateway_helpers as gh

    monkeypatch.setattr(gh, "_get_sandbox_base", lambda uid, sid: str(tmp_path))
    from routes.files import bp as _bp

    app.register_blueprint(_bp)
    return app.test_client()


# ==================== 门 F0 · 同族只在唯一入口（机检） ====================

def test_f0_no_default_subject_and_single_entry():
    """⭐ 判据：本文件 ⛔ 不许再有「默认值冒充调用方意图」；`request.args or {}` 只许在唯一入口 `_query()` 内。"""
    import ast

    src = io.open(FC, encoding="utf-8", newline="").read()
    assert '"default"' not in src, "仍有字面默认值"
    tree = ast.parse(src)
    sites = []
    for n in ast.walk(tree):
        if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or) and len(n.values) == 2:
            a, b = n.values
            if (isinstance(a, ast.Attribute) and a.attr in ("args", "values")
                    and isinstance(a.value, ast.Name) and a.value.id == "request"
                    and isinstance(b, ast.Dict) and not b.keys):
                sites.append(n.lineno)
    assert len(sites) == 1, "同族应只剩唯一入口 1 处（实测 %s）" % sites
    q = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_query"]
    assert len(q) == 1 and q[0].lineno < sites[0] <= (q[0].end_lineno or q[0].lineno), \
        "那 1 处不在 `_query()` 内 ⇒ 有散落站点"


# ==================== 门 F1 · `/v9/files` ====================

def test_f1a_list_missing_user_id_is_400(client):
    r = client.get("/v9/files")
    assert r.status_code == 400, "空查询须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/files" in e and "user_id" in e, "须带路由定位 ＋ 说缺什么：%r" % e


def test_f1b_list_missing_session_id_is_400(client):
    r = client.get("/v9/files?user_id=u1")
    assert r.status_code == 400, "缺 session_id 须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert "缺 session_id" in _err(r), _err(r)


def test_f1c_list_valid_shape_is_200(client):
    r = client.get("/v9/files?user_id=u1&session_id=s1")
    assert r.status_code == 200, "好形状须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert (r.get_json() or {}).get("success") is True, r.data[:200]


# ==================== 门 F2 · `/v9/files/content` ====================

def test_f2a_content_missing_user_id_is_400(client):
    r = client.get("/v9/files/content")
    assert r.status_code == 400, r.status_code
    assert "缺 user_id" in _err(r), _err(r)


def test_f2b_content_missing_id_is_400(client):
    r = client.get("/v9/files/content?user_id=u1&session_id=s1")
    assert r.status_code == 400, r.status_code
    assert "缺 id" in _err(r), _err(r)


def test_f2c_content_valid_shape_business_miss_stays_200(client):
    """⭐ 分类：好形状但文件不存在 ⇒ **200 ＋ `success:false`**（业务面 ⛔ 不改成 400）。"""
    r = client.get("/v9/files/content?user_id=u1&session_id=s1&id=deadbeefdeadbeef")
    assert r.status_code == 200, "业务失败须留 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert (r.get_json() or {}).get("error") in BUSINESS, r.data[:200]


# ==================== 门 F3 · `/v9/files/diffs` ====================

def test_f3a_diffs_missing_user_id_is_400(client):
    r = client.get("/v9/files/diffs")
    assert r.status_code == 400, r.status_code
    assert "缺 user_id" in _err(r), _err(r)


def test_f3b_diffs_missing_path_is_400(client):
    r = client.get("/v9/files/diffs?user_id=u1&session_id=s1")
    assert r.status_code == 400, r.status_code
    assert "缺 path" in _err(r), _err(r)


def test_f3c_diffs_valid_shape_is_200(client):
    r = client.get("/v9/files/diffs?user_id=u1&session_id=s1&path=a/b.md")
    assert r.status_code == 200, r.status_code
    assert (r.get_json() or {}).get("success") is True, r.data[:200]


# ==================== 门 F4 · `/v9/files/download` ====================

def test_f4a_download_missing_user_id_is_400(client):
    r = client.get("/v9/files/download")
    assert r.status_code == 400, r.status_code
    assert "缺 user_id" in _err(r), _err(r)


def test_f4b_download_missing_id_is_400(client):
    r = client.get("/v9/files/download?user_id=u1&session_id=s1")
    assert r.status_code == 400, r.status_code
    assert "缺 id" in _err(r), _err(r)


def test_f4c_download_valid_shape_business_miss_stays_200(client):
    r = client.get("/v9/files/download?user_id=u1&session_id=s1&id=deadbeefdeadbeef")
    assert r.status_code == 200, r.status_code
    assert (r.get_json() or {}).get("error") in BUSINESS, r.data[:200]


# ==================== 门 F5 · `/v9/media` ====================

def test_f5a_media_missing_user_id_is_400(client):
    r = client.get("/v9/media")
    assert r.status_code == 400, r.status_code
    assert "缺 user_id" in _err(r), _err(r)


def test_f5b_media_missing_path_is_400(client):
    r = client.get("/v9/media?user_id=u1&session_id=s1")
    assert r.status_code == 400, r.status_code
    assert "缺 path" in _err(r), _err(r)


def test_f5c_media_traversal_is_400(client):
    """⭐ 防穿越：呼叫方给的路径越出沙箱 ⇒ 400（⛔ 不是 200+notok ⇒ 也 ⛔ 不是第三種状态码）。"""
    r = client.get("/v9/media?user_id=u1&session_id=s1&path=../../etc/passwd")
    assert r.status_code == 400, "非法路径须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert "非法路径" in _err(r), _err(r)


def test_f5d_media_valid_shape_business_miss_stays_200(client):
    r = client.get("/v9/media?user_id=u1&session_id=s1&path=nope.png")
    assert r.status_code == 200, r.status_code
    assert (r.get_json() or {}).get("error") in BUSINESS, r.data[:200]


# ==================== 门 F6 · `/v9/files/save`（POST） ====================

def test_f6a_save_missing_user_id_is_400(client):
    r = client.post("/v9/files/save", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert "缺 user_id" in _err(r), _err(r)


def test_f6b_save_missing_session_id_is_400(client):
    r = client.post("/v9/files/save", json={"user_id": "u1"})
    assert r.status_code == 400, r.status_code
    assert "缺 session_id" in _err(r), _err(r)


def test_f6c_save_missing_filename_is_400(client):
    r = client.post("/v9/files/save", json={"user_id": "u1", "session_id": "s1"})
    assert r.status_code == 400, r.status_code
    assert "缺 filename" in _err(r), _err(r)


def test_f6d_save_bad_json_is_400(client):
    """⭐ 原行为是**静默吞**（`except Exception: _b = {}` ⇒ 200「session_id 必填」）⇒ 改为形状判据 400。"""
    r = client.post("/v9/files/save", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, r.status_code
    assert "不是合法 JSON" in _err(r), _err(r)


def test_f6e_save_oversize_is_400(client):
    r = client.post("/v9/files/save", json={"user_id": "u1", "session_id": "s1",
                                            "filename": "x.md", "content": "a" * (200 * 1024 + 1)})
    assert r.status_code == 400, r.status_code
    assert "内容超限" in _err(r), _err(r)


def test_f6f_save_valid_shape_is_200(client, tmp_path):
    r = client.post("/v9/files/save", json={"user_id": "u1", "session_id": "s1",
                                            "filename": "probe.md", "content": "# hi"})
    assert r.status_code == 200, "好形状须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert (r.get_json() or {}).get("success") is True, r.data[:200]
    assert (tmp_path / "data" / "reports" / "probe.md").exists(), "应落在（被 patch 的）沙箱内"


# ==================== 门 F7 · 「一种风格」（机检分类，⛔ 不当说辞） ====================

def test_f7_caller_input_errors_are_all_400_no_second_style():
    """⭐ PM §二 要的「消掉同文件两种风格」⇒ 机检：**调用方输入类**的拒绝必须**全部**是 400。

    白名单＝「业务/资源状态」（`文件不存在`/`沙箱不存在`）与内部异常（`str(_…`）—— 那些留 200+notok。
    """
    src = io.open(FC, encoding="utf-8", newline="").read()
    bad = []
    for i, l in enumerate(src.split("\n"), 1):
        s = l.strip()
        if not s.startswith('return jsonify({"success": False'):
            continue
        if s.rstrip().endswith(", 400"):
            continue
        if any(m in s for m in BUSINESS) or "str(_" in s:
            continue
        bad.append((i, s[:100]))
    assert bad == [], "仍有两种风格（调用方输入类却回 200）：%s" % bad