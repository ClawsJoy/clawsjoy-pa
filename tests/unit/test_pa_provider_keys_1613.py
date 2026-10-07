# -*- coding: utf-8 -*-
u"""pm_1613 令四之后端半之测：供应商密钥之 落 / 清 端（唯本机 ＋ 一次性令牌 · ⛔ 值）。

以何形调用（判通 / 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_provider_keys_1613.py -q

判据：
  ⒜ 领令牌 ⇒ 唯 Cookie（HttpOnly）· 响应体 ⛔ 载值
  ⒝ 正控：落钥 ⇒ 200 ∧ 件内真是 · 回执 ⛔ 载值（哨兵证）
  ⒞ 正控：清钥 ⇒ 200 ∧ 件内其行已去
  ⒟ 反控：⛔ 令牌 / 令牌已用 / 非本机 / 未知供应商 / 无需钥之供应商 / 值含换行 ⇒ 皆拒
  ⒠ GET /v9/pa/providers 唯布尔（无值）
"""
import re
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import provider_keys as PK  # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402

SENTINEL = "sk-" + "SENTINEL" + "-1613"
COOKIE = "pa_key_token"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    envf = tmp_path / "config" / ".env"
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    monkeypatch.setenv("PA_ENV_FILE", str(envf))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    PK.reset_tokens()
    app = Flask(__name__)
    register_pa_routes(app)
    return app, envf


def _issue(app):
    u"""领令牌 ⇒ (client, tok, Set-Cookie)。client 之罐已持 Cookie（其值 ⛔ 入体）。"""
    c = app.test_client()
    r = c.get("/v9/pa/providers/key/token")
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_data(as_text=True)
    sc = r.headers.get("Set-Cookie") or ""
    m = re.search(COOKIE + r"=([0-9a-f]{16,})", sc)
    assert m, sc
    assert m.group(1) not in body, u"令牌值 ⛔ 许入体"
    assert "HttpOnly" in sc, sc
    return c, m.group(1), sc


def test_token_face(env):
    u"""(a) 令牌之面：issued ／ ttl ／ HttpOnly · 值 ⛔ 入体。"""
    app, _ = env
    c, tok, sc = _issue(app)
    d = c.get("/v9/pa/providers/key/token").get_json()  # 可重复领
    assert d["issued"] is True and d["cookie"] == COOKIE and d["expires_in"] > 0


def test_token_rejects_non_loopback(env):
    u"""(d) 令牌端亦唯本机。"""
    app, _ = env
    r = app.test_client().get("/v9/pa/providers/key/token",
                              environ_overrides={"REMOTE_ADDR": "10.9.9.9"})
    assert r.status_code == 403, r.get_data(as_text=True)


def test_set_key_positive(env):
    u"""(b) 正控：落钥 ⇒ 200 ∧ 件内真是 ∧ 回执 ⛔ 载值。"""
    app, f = env
    c, _tok, _sc = _issue(app)
    r = c.post("/v9/pa/providers/key", json={"provider": "remote:deepseek", "key": SENTINEL})
    assert r.status_code == 200, r.get_data(as_text=True)
    txt = r.get_data(as_text=True)
    assert SENTINEL not in txt, u"密钥值 ⛔ 许入回执"
    d = r.get_json()
    assert d["action"] == "set" and d["key_state"] == "configured" and d["key_configured"] is True
    assert d["key_env"] == "DEEPSEEK_API_KEY"
    raw = f.read_text(encoding="utf-8")
    assert ("DEEPSEEK_API_KEY=" + SENTINEL) in raw, raw
    g = app.test_client().get("/v9/pa/providers").get_json()
    deep = [p for p in g["providers"] if p["id"] == "remote:deepseek"][0]
    assert deep["key_state"] == "configured" and SENTINEL not in str(g)


def test_clear_key_positive(env):
    u"""(c) 正控：清钥 ⇒ 200 ∧ 其行已去。"""
    app, f = env
    c1, _t1, _s1 = _issue(app)
    assert c1.post("/v9/pa/providers/key",
                   json={"provider": "remote:deepseek", "key": SENTINEL}).status_code == 200
    assert "DEEPSEEK_API_KEY" in f.read_text(encoding="utf-8")
    c2, _t2, _s2 = _issue(app)
    r2 = c2.post("/v9/pa/providers/key", json={"provider": "remote:deepseek", "key": None})
    assert r2.status_code == 200, r2.get_data(as_text=True)
    d2 = r2.get_json()
    assert d2["action"] == "cleared" and d2["key_state"] == "missing"
    assert "DEEPSEEK_API_KEY" not in f.read_text(encoding="utf-8")


def test_reject_without_token(env):
    u"""(d) 反控：⛔ 令牌 ⇒ 403。"""
    app, _ = env
    r = app.test_client().post("/v9/pa/providers/key",
                               json={"provider": "remote:deepseek", "key": SENTINEL})
    assert r.status_code == 403 and not r.get_json()["ok"]


def test_reject_reused_token(env):
    u"""(d) 反控：用即焚（同令牌二用 ⇒ 403）。"""
    app, _ = env
    c, tok, _sc = _issue(app)
    assert c.post("/v9/pa/providers/key",
                  json={"provider": "remote:deepseek", "key": SENTINEL}).status_code == 200
    c.set_cookie(COOKIE, tok)   # 重植同令牌 ⇒ 用即焚 ⇒ 须拒
    r2 = c.post("/v9/pa/providers/key",
                json={"provider": "remote:deepseek", "key": SENTINEL + "2"})
    assert r2.status_code == 403, r2.get_data(as_text=True)


def test_reject_non_loopback(env):
    u"""(d) 反控：非本机（LAN）⇒ 403（服务绑 0.0.0.0 ⇒ 须显判）。"""
    app, _ = env
    c, _tok, _sc = _issue(app)
    r = c.post("/v9/pa/providers/key",
               json={"provider": "remote:deepseek", "key": SENTINEL},
               environ_overrides={"REMOTE_ADDR": "10.1.2.3"})
    assert r.status_code == 403, r.get_data(as_text=True)


def test_reject_unknown_and_not_required(env):
    u"""(d) 反控：未知供应商 ⇒ 400；无需钥者（Ollama）⇒ 400。"""
    app, _ = env
    c1, _a, _b = _issue(app)
    assert c1.post("/v9/pa/providers/key",
                   json={"provider": "nope", "key": SENTINEL}).status_code == 400
    c2, _a2, _b2 = _issue(app)
    assert c2.post("/v9/pa/providers/key",
                   json={"provider": "local:ollama", "key": SENTINEL}).status_code == 400


def test_reject_value_with_newline(env):
    u"""(d) 反控：值含换行 ⇒ 400（⛔ 一行变多行 · 注入）。"""
    app, f = env
    c, _tok, _sc = _issue(app)
    r = c.post("/v9/pa/providers/key",
               json={"provider": "remote:deepseek", "key": "sk-x" + chr(10) + "EVIL=1"})
    assert r.status_code == 400, r.get_data(as_text=True)
    txt = f.read_text(encoding="utf-8") if f.exists() else ""
    assert "EVIL" not in txt


def test_env_name_from_registry_not_client(env):
    u"""(d) 反控：env 名唯自注册表 ⇒ 客户端 ⛔ 指定任意 env（越权写）。"""
    app, f = env
    c, _tok, _sc = _issue(app)
    r = c.post("/v9/pa/providers/key",
               json={"provider": "remote:deepseek", "key": SENTINEL, "env_name": "PATH"})
    assert r.status_code == 200
    assert "PATH=" not in f.read_text(encoding="utf-8")
