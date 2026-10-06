# -*- coding: utf-8 -*-
u"""首启引导（`GET /v9/pa/first_run`）之测（承 pm_1384 §三.3 · 判成 ⒜⒝⒞⒟）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_first_run.py -q

判据：
  ⒜ 数据在本机（**人话** · ⛔ 行话）＋ 逐条附「据」
  ⒝ 模型**三态**（未接 ／ 在·无权重 ／ 在∧可用 · ＋ 不可达／未核）＋ **因**非空（⛔ 静默）
  ⒞ 数据目录 ＝ **真源**（`env_face.resolve_paths()` 之值 ／ 源）· ⛔ 造径
  ⒟ ⛔ 静默：缺则入「缺」（逐条 项 ／ 因）· 模型非「在∧可用」⇒ 必入「缺」
  余：⛔ 旧开发机之径之**字面**入面 ／ banner ⛔ `removeChild(` ／ ⛔ `paDismissCard(`
  反控：遥测器**有齿**（喂 `posthog.` ⇒ 必逮 ／ 定义块自理 ⇒ ⛔ 自指 ／ 净 ⇒ 0）
"""
import json
import os
import re
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as G  # noqa: E402

#: 模型之三态 ＋ 二兜底（承 30b523c 之三态器 · `scripts/win_pa/preflight_start.py`）
STATES = (u"未接", u"在·无权重", u"在∧可用", u"不可达", u"未核")

#: 旧开发机之径之**字面**（⛔ 入面 ／ ⛔ 入本功能之源）—— 承 pm_1366 §三 ⓒ
LEGACY_LIT = ("C:/Users/", "C:\\Users\\", "wpsai_v2_render", "D:/npm-global", "D:\\npm-global")

#: 「话」之禁用术语（＝ 行话 · 承 ⒜）——「据」不在此列（据**须**可核 ⇒ 术语可）
JARGON = ("resolve_paths", "get_data_root", "unified_config", "env_face", "core/lib", "core/pa",
          "os.path", ".py:")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    G.register_pa_routes(app)
    app.config["TESTING"] = True
    return app.test_client()


def _ro(client):
    r = client.get("/v9/pa/first_run")
    assert r.status_code == 200, r.status_code
    return r.get_json()


def _banner_src():
    u"""`web/pa.html` 之首启引导**行内脚本**（`pa/boot.js` 之前那段）—— ⛔ 后端可代。"""
    s = (ROOT / "web" / "pa.html").read_text(encoding="utf-8")
    head = s[:s.index("pa/boot.js")]
    st = head.rindex("<script>")
    return head[st + len("<script>"):head.index("</script>", st)]


def test_http_200_与键皆在(client):
    d = _ro(client)
    assert d["ok"] is True
    assert d["version"] == G.PA_FIRST_RUN_VERSION
    assert re.match(r"^\d{4}-\d{2}-\d{2}\.\d+$", G.PA_FIRST_RUN_VERSION), G.PA_FIRST_RUN_VERSION
    assert isinstance(d.get("印"), str) and len(d["印"]) == 16, d.get("印")
    for k in (u"at", u"口径", u"数据在本机", u"数据目录", u"模型", u"缺", u"须知"):
        assert k in d, k


def test_须知_为真且附据_话非行话(client):
    d = _ro(client)
    need = d["须知"]
    assert isinstance(need, list) and len(need) >= 4, need
    for x in need:
        assert x.get("话") and x.get("据"), x
        assert x["据"].strip(), x
        for j in JARGON:
            assert j not in x["话"], (j, x["话"])
    blob = u"".join(x["话"] for x in need)
    for w in (u"数据", u"上传", u"本机"):
        assert w in blob, w


def test_数据在本机_是且显据(client):
    v = _ro(client)[u"数据在本机"]
    assert v["是"] is True
    assert v["上传"] is False
    assert v.get("据") and v.get("辞"), v
    assert u"上传" in v["辞"], v["辞"]


def test_模型三态_在枚举内且附因(client):
    m = _ro(client)[u"模型"]
    assert m["态"] in STATES, m
    assert m["因"], u"态 %s 之因空 ＝ 静默（⛔ 装成可用）" % m["态"]
    assert m["三态器"], m
    if m["态"] == u"在∧可用":
        assert isinstance(m["models"], int) and m["models"] > 0, m
    elif m["态"] == u"在·无权重":
        assert m["models"] == 0, m


def test_数据目录_系真源_非造径(client):
    d = _ro(client)
    from core.pa import env_face as EF
    pm, ps = EF.resolve_paths()
    dd = d[u"数据目录"]
    assert dd["值"] == pm.get("data"), (dd["值"], pm.get("data"))
    assert dd["源"] == ps.get("data"), dd["源"]
    assert dd.get("可指之径"), dd
    if dd["值"]:
        assert os.path.isabs(dd["值"]), dd["值"]
    else:
        assert any(u"数据目录" in x["项"] for x in d["缺"]), d["缺"]


def test_缺则显因(client):
    d = _ro(client)
    for x in d["缺"]:
        assert x.get("项") and x.get("因"), x
    assert (u"「缺」列 %d 项" % len(d["缺"])) in d["须知"][-1]["据"], d["须知"][-1]


def test_反控_模型非可用必入缺(client, monkeypatch):
    u"""⛔ 静默：强令三态器报「未接」⇒ 必入「缺」（⛔ 吞其缺）。"""
    monkeypatch.setattr(G, "_ollama_tri", lambda: {
        "态": u"未接", "因": u"⛔ 未接：127.0.0.1:11434 无应答 ⇒ 本机模型路不可用 ｜ 修之门：stub",
        "models": None, "首": None, "三态器": "stub"})
    d = _ro(client)
    assert d[u"模型"]["态"] == u"未接"
    assert any(u"模型" in x["项"] for x in d["缺"]), d["缺"]


def test_旧开发机字面不入面(client):
    blob = json.dumps(_ro(client), ensure_ascii=False)
    for lit in LEGACY_LIT:
        assert lit not in blob, lit


def test_本功能源码_无旧开发机字面():
    s = (ROOT / "core" / "pa" / "gateway_routes.py").read_text(encoding="utf-8")
    i = s.index("PA_FIRST_RUN_VERSION")
    seg = s[i:s.index("def _ask_scope", i)]
    assert seg, u"取段空 ＝ 判据无齿"
    for lit in LEGACY_LIT:
        assert lit not in seg, lit


def test_反控_遥测器有齿(tmp_path, monkeypatch):
    u"""反控（承「器须有齿」之律）：喂 `posthog.` 必逮 ／ 定义块自理 ⇒ ⛔ 自指 ／ 净 ⇒ 0。"""
    core = tmp_path / "core"
    core.mkdir(parents=True, exist_ok=True)
    (core / "a_clean.py").write_text(u"def f():\n    return 1\n", encoding="utf-8")
    monkeypatch.setattr(G, "_UI_REPO", tmp_path)
    assert G._telemetry_scan() == [], u"净 ⇒ 必 0（⛔ 假红）"
    (core / "b_hit.py").write_text(u"import posthog\nposthog.capture('x')\n", encoding="utf-8")
    hits = G._telemetry_scan()
    assert any("b_hit.py" in h for h in hits), hits
    assert any(u"posthog." in h for h in hits), hits
    (core / "b_hit.py").write_text(u'_TELEMETRY_MARKS = ("posthog.",)\nX = 1\n', encoding="utf-8")
    assert G._telemetry_scan() == [], u"唯定义块 ＝ 自指 ⇒ 必剔（⛔ 假红）"


def test_banner_无removeChild_无绝对径_且非静默():
    b = _banner_src()
    assert "removeChild(" not in b, u"撞 CW 之计数判据"
    assert "paDismissCard(" not in b
    assert re.search(r"[A-Za-z]:[\\/]", b) is None, re.findall(r"[A-Za-z]:[\\/]", b)
    assert "/v9/pa/first_run" in b, u"须读后端之读数（⛔ 前端自断）"
    assert u"没读成" in b, u"后端 ⛔ 在答 ⇒ 须明书（⛔ 装成「已就绪」）"
