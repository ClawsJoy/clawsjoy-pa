# -*- coding: utf-8 -*-
r"""PM-011 · batch2 · `POST /v9/pa/caliber/change` 域因**必带路由定位**（PM 2026-09-30 裁「改」）。

PM 裁（原话要点）：
  · 与 N2／N2c 判据②「错误文本**含出错位置**」**同族**；
  · **同一路由两种风格 ＝ 判据不可分辨** ⇒ 裁「改」；
  · 改法（**一处**）：`return err("caliber/change: %s" % _e)` ＋ 该支**专属反例门**；
  · ⚠ **一次只动一处**：⛔ 不连带改别的路由。

⚠ 本件⛔ 不改 `CaliberStoreError` 的**字句本身**，只**加前缀**；⛔ 不改 HTTP 状态（仍 400）。
改前一手读数（我 v12 §八 报过 · 活服务 ：`body={}` ⇒ 400 `{"ok":false,"error":"缺 id"}` —— ⛔ 无定位）。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]

DOMAIN = [
    ("empty-body", {}, "缺 id"),
    ("bad-status", {"id": "X"}, "status 必须是 confirmed/unverified/pending"),
    ("missing-owner", {"id": "X", "status": "confirmed", "why": "t"},
     "缺 owner（谁负责复认）—— ⛔ 不给默认值"),
    ("update-not-found", {"id": "NOPE", "status": "confirmed", "owner": "PM", "why": "t"},
     "update 找不到卡片: NOPE"),
]
DOMAIN_IDS = [d[0] for d in DOMAIN]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    from core.lib.error_handler import register_error_handlers
    register_error_handlers(app)
    from core.pa.gateway_routes import register_pa_routes
    register_pa_routes(app)
    return app.test_client()


# ==================== 判据：域因**逐字 = 路由前缀 ＋ 原域因** ====================

@pytest.mark.parametrize("name,payload,domain", DOMAIN, ids=DOMAIN_IDS)
def test_c_locator_domain_error_carries_route_prefix(client, name, payload, domain):
    r = client.post("/v9/pa/caliber/change", json=payload)
    assert r.status_code == 400, "%s：域校错误应 400（实测 %s）" % (name, r.status_code)
    e = str((r.get_json() or {}).get("error") or "")
    assert e.startswith("caliber/change:"), "%s：域因没带路由定位：%r" % (name, e)
    assert e == "caliber/change: " + domain, "%s：域因被改动（应只加前缀）：%r" % (name, e)
    assert "Error" not in e and "Traceback" not in e, "%s：响应里出现异常类名：%r" % (name, e)


# ==================== 对照（⛔ 不该被一起改坏的既有行为） ====================

def test_ctl_local_shape_errors_keep_own_prefix(client):
    """本路由**自带守卫**（N2／N2b 落的）文案**逐字不变**。"""
    r = client.post("/v9/pa/caliber/change", json="x")
    assert r.status_code == 400
    assert (r.get_json() or {}).get("error") == "caliber/change: body 需要 JSON 对象（拿到 str）"


def test_ctl_domain_text_itself_still_readable(client):
    """⭐ 候选面 ≠ 病面：`CaliberStoreError` 的**域内字句**（含字段名）⛔ 一个字没动。"""
    r = client.post("/v9/pa/caliber/change", json={})
    assert r.status_code == 400
    assert "id" in str((r.get_json() or {}).get("error") or "")