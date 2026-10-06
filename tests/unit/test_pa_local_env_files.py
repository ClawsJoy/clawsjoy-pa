# -*- coding: utf-8 -*-
u"""本机「可选引导件」之测（承 pm_1453 §一 之裁 · 正控 ／ 反控）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_local_env_files.py -q

判据：
  ⒜ `core/lib/local_env_files.py` ＝ **一处定形**：缺 ⇒ 跳读（⛔ 崩）· 态分「未配 ⟷ 已配」
  ⒝ 首屏显形：`GET /v9/pa/first_run` 之「本机配置」有件 ／ 有「判」／ 态 ∈ 枚举；
     「须知」有「云端密钥」一条（⛔ 静默缺 —— 承「空 ≠ 缺」）
  ⒞ 反控（器须有齿）：起器 `agent_gateway_enhanced.py` **⛔ 有**「无条件 open(_env_path)」
     —— 即：**净机无 `config/.env` ⇒ ⛔ 崩** 之实缺陷 **⛔ 可回潮**
"""
import os
import re
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import local_env_files as LE  # noqa: E402
from core.pa import gateway_routes as G  # noqa: E402

STATES = (LE.STATE_ON, LE.STATE_OFF)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    G.register_pa_routes(app)
    app.config["TESTING"] = True
    return app.test_client()


# ---------------------------------------------------------------- ⒜ 一处定形 · 缺 ⇒ 跳读

def test_缺则跳读不崩(tmp_path):
    u"""缺 ⇒ `present` False ／ `未配` ／ `read_lines` `[]` ／ `has_proxy_line` False（⛔ 崩）。"""
    miss = str(tmp_path / "nope" / ".env")
    assert LE.present(miss) is False
    assert LE.state(miss) == {"在": False, "态": LE.STATE_OFF, "径": miss}
    assert LE.read_lines(miss) == []
    assert LE.has_proxy_line(miss) is False
    # ⛔ 空径 ／ None 亦 ⛔ 崩
    assert LE.present(None) is False and LE.present("") is False
    assert LE.state(None)["径"] is None


def test_有件则照读且态为已配(tmp_path):
    u"""有 ⇒ `已配` ／ 逐行可读 ／ 代理行之判有齿（正控）。"""
    p = tmp_path / ".env"
    p.write_text(u"# \u6ce8\nFOO=1\nHTTP_PROXY=http://127.0.0.1:7890\n", encoding="utf-8")
    assert LE.present(str(p)) is True
    assert LE.state(str(p))["态"] == LE.STATE_ON
    assert LE.read_lines(str(p)) == ["# \u6ce8", "FOO=1", "HTTP_PROXY=http://127.0.0.1:7890"]
    assert LE.has_proxy_line(str(p)) is True
    # 反控：无代理行之件 ⇒ False（⛔ 恒 True）
    p.write_text(u"FOO=1\n", encoding="utf-8")
    assert LE.has_proxy_line(str(p)) is False


def test_有BOM之env亦通(tmp_path):
    u"""有 BOM 之 `.env` 亦通（编码 `utf-8-sig`）—— 首行字面 ⛔ 带 `\\ufeff`。"""
    p = tmp_path / ".env"
    p.write_bytes(u"\ufeffHTTP_PROXY=http://x\n".encode("utf-8"))
    assert LE.has_proxy_line(str(p)) is True, LE.read_lines(str(p))


def test_二件之态附判(tmp_path):
    u"""`local_files_state` 逐项必附「判」（⛔ 裸态）＋ 件之真源为常量（⛔ 各写一遍）。"""
    st = LE.local_files_state(str(tmp_path))
    assert [x["件"] for x in st] == [LE.ENV_REL, LE.SECRETS_REL]
    assert LE.ENV_REL == "config/.env" and LE.SECRETS_REL == "config/secrets.yaml"
    for x in st:
        assert x["名"] and x["义"] and x["判"], x
        assert x["态"] in STATES, x
        assert x["径"].startswith(str(tmp_path)), x


# ---------------------------------------------------------------- ⒝ 首屏显形

def test_首屏显形_本机配置(client):
    d = client.get("/v9/pa/first_run").get_json()
    assert d["version"] == G.PA_FIRST_RUN_VERSION
    assert re.match(r"^\d{4}-\d{2}-\d{2}\.\d+$", G.PA_FIRST_RUN_VERSION)
    cfg = d.get(u"本机配置")
    assert isinstance(cfg, dict), d.keys()
    assert cfg.get(u"口径"), cfg
    assert isinstance(cfg.get(u"件"), list) and len(cfg[u"件"]) == 2, cfg
    for x in cfg[u"件"]:
        assert x[u"态"] in STATES, x
        assert x[u"判"], x
    assert u"留" in cfg[u"口径"] or u"正常" in cfg[u"口径"], cfg[u"口径"]


def test_首屏显形_须知有云端密钥一条(client):
    d = client.get("/v9/pa/first_run").get_json()
    hit = [x for x in d[u"须知"] if u"密钥" in x[u"话"]]
    assert len(hit) == 1, d[u"须知"]
    assert hit[0][u"据"], hit[0]
    assert (u"未配" in hit[0][u"话"]) or (u"已配" in hit[0][u"话"]), hit[0][u"话"]
    assert u"缺" in d[u"须知"][-1][u"话"], u"「缺什么」须仍为末条（承 ⒟ 之判）"


# ---------------------------------------------------------------- ⒞ 反控 · 缺陷 ⛔ 回潮

def _env_open_lines(src):
    u"""起器源码里「`open(_env_path)`」之调用行（**ast** 取 —— ⛔ 被注释骗）。"""
    import ast as _ast
    bad = []
    for _n in _ast.walk(_ast.parse(src)):
        if isinstance(_n, _ast.Call) and getattr(_n.func, "id", "") == "open":
            _a = _n.args[0] if _n.args else None
            if isinstance(_a, _ast.Name) and _a.id == "_env_path":
                bad.append(_n.lineno)
    return bad


def test_反控_起器不再无条件开_env():
    u"""起器源码：⛔ 有 `open(_env_path)`（净机无 `.env` ⇒ 崩 之旧形）· **有** helper 之接。"""
    src = (ROOT / "agent_gateway_enhanced.py").read_text(encoding="utf-8")
    assert _env_open_lines(src) == [], u"旧形回潮：无条件开 .env ⇒ 净机必崩"
    assert "_env_has_proxy" not in src, u"旧变量回潮"
    assert "from core.lib.local_env_files import has_proxy_line" in src, u"⛔ 未接 helper"


def test_反控_判据有齿_旧形必速():
    u"""反控（承「器须有齿」之律）：喂旧形 ⇒ 同一判必速（⛔ 假绿）。"""
    old = u"with open(_env_path, encoding='utf-8') as _f:\n    _f.read()\n"
    assert _env_open_lines(old) == [1], u"旧形必速"
    cur = u"if not has_proxy_line(_env_path):\n    pass\n"
    assert _env_open_lines(cur) == [], u"新形 ⛔ 误报"
