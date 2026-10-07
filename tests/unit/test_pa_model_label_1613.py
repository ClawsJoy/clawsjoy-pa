# -*- coding: utf-8 -*-
u"""pm_1613 令五之测：显示名（label）落表 ⇒ 显形其替换 ＋ 其由（⛔ 静默）。

以何形调用（判通 / 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_model_label_1613.py -q

判据：
  ⒜ 反控（旧病）：显示名 DeepSeek V4 Flash ⇒ 后端表 ⛔ 有 ⇒ 须显形（⛔ 静默）
  ⒝ 实名 / 别名 ⇒ note 空（⛔ 无谓之辞）
  ⒞ 未识之名 ⇒ None ＋ 由
  ⒟ 端之闭环：POST /v9/pa/session_model 喂显示名 ⇒ 落档为实名 ∧ model_source 载其由
  ⒠ 不回归：喂实名 ⇒ model_source 仍「会话档」
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import providers as PV  # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402


def test_label_is_surfaced():
    u"""(a) 显示名 ⇒ 替换 ∧ 由（承 pm_1613 令五）。"""
    _id, note = PV.resolve_model_ex("DeepSeek V4 Flash")
    assert _id == "deepseek-flash", _id
    assert note and "显示名" in note, note


def test_real_name_and_alias_are_silent():
    u"""(b) 实名 / 别名 ⇒ note 空。"""
    assert PV.resolve_model_ex("deepseek-flash") == ("deepseek-flash", "")
    assert PV.resolve_model_ex("deepseek-v4-flash") == ("deepseek-flash", "")
    assert PV.resolve_model_ex("remote:deepseek:deepseek-flash") == ("deepseek-flash", "")


def test_unknown_is_none_with_reason():
    u"""(c) 未识之名 ⇒ None ＋ 由。"""
    _id, note = PV.resolve_model_ex("gpt-4")
    assert _id is None and "未识之模型名" in note


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    register_pa_routes(app)
    return app.test_client()


def test_endpoint_surfaces_substitution(client):
    u"""(d) 端之闭环：显示名 ⇒ 落档实名 ∧ model_source 载由。"""
    r = client.post("/v9/pa/session_model",
                    json={"user_id": "u1", "model": "DeepSeek V4 Flash"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["model"] == "deepseek-flash", r.get_json()
    assert "显示名" in r.get_json()["model_source"], r.get_json()


def test_endpoint_real_name_keeps_src(client):
    u"""(e) 不回归：实名 ⇒ model_source 仍「会话档」。"""
    r = client.post("/v9/pa/session_model",
                    json={"user_id": "u2", "model": "deepseek-flash"})
    assert r.status_code == 200
    assert r.get_json()["model_source"] == "会话档", r.get_json()
    assert client.get("/v9/pa/session_model?user_id=u2").get_json()["model_source"] == "会话档"
