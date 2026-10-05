# -*- coding: utf-8 -*-
"""PM-011 · PA_BUILD 构建指纹（2026-09-30 · PM 批）。

PM 判据：「**页面能报自身构建 sha16 且我的探针读数必带它**」——消灭「两版页面无法区分」
的归属之争（现场：PM 把旧气泡重绘读成现役行为，因为分不清手上的页面是哪一版）。

⚠ 本文件是**第二版**：第一版把功能用例打在了 `core/web/health.py::health_bp` 上 ——
  那个 bp **全仓 0 处注册**（死码）⇒ 用例全绿而线上**毫无变化**。
  ⭐ 教训（已入 T6）：**判据必须打在真源上**；「测试绿」不等于「线上真的变了」。
  抓出它的是现场复核（`/web/pa.html` 响应头没有指纹），⛔ 不是测试。

钉死：T1 指纹＝服务端现算 ｜ T2 反例门：换字节指纹必变 ｜ T3 页面确实会显示
      ｜ T4/T5 真源响应头（no-store ＋ 指纹；别的静态件不盖）｜ T6 **真源钉死**。
"""
import hashlib
import os
import re
import sys

sys.path.insert(0, ".")

from flask import Flask

from core.pa import gateway_routes as gr
from routes.static import bp as static_bp   # ⭐ 真源（agent_gateway_enhanced.py:385/392）

PAGE = os.path.join("web", "pa.html")
# 拆面（承 pm 1334 §二.1 · 页面 ＝ 壳 ＋ 支）：T3 之判须并读三面
#   容器 ＝ 壳（web/pa.html）／ fetchPaBuild 之体 ＝ web/pa/faces/shell.js ／ 调用点 ＝ web/pa/faces/config.js
PAGE_FACES = (PAGE,
              os.path.join("web", "pa", "faces", "shell.js"),
              os.path.join("web", "pa", "faces", "config.js"))
MAIN = "agent_gateway_enhanced.py"


def _sha16(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def _app():
    a = Flask(__name__, root_path=os.path.abspath("."))
    a.register_blueprint(static_bp)
    return a


def _registered_bp_modules():
    """从主文件**推导**「哪些模块的 bp 真被注册了」（⛔ 不写死模块名）。"""
    main = open(MAIN, encoding="utf-8").read()
    out = []
    for mod, alias in re.findall(r"from\s+([\w\.]+)\s+import\s+bp\s+as\s+(\w+)", main):
        if re.search(r"register_blueprint\(\s*" + re.escape(alias) + r"\s*\)", main):
            out.append(mod)
    return out


def test_t1_fingerprint_is_measured_from_the_served_file():
    app = _app()
    with app.test_request_context("/"):
        b = gr._frontend_build()
    assert b.get("exists") is True, b
    assert b["sha16"] == _sha16(PAGE), b
    assert b["bytes"] == os.path.getsize(PAGE), b
    assert b["mtime"], "必须带时点（读数必带时点）"


def test_t2_反例门_换字节则指纹必变(monkeypatch, tmp_path):
    """反例门：同一读数口径下换掉文件内容 ⇒ 指纹必须翻面。

    若失败（指纹不变）⇒ 读的是常量/缓存 ⇒ T1 的「现算」不成立、判据无齿。
    """
    d = tmp_path / "web"
    d.mkdir()
    f = d / "pa.html"
    f.write_bytes(b"A" * 10)
    monkeypatch.setattr(gr, "_web_root", lambda: str(d))
    s1 = gr._frontend_build()["sha16"]
    assert s1 == hashlib.sha256(b"A" * 10).hexdigest()[:16]
    f.write_bytes(b"B" * 10)
    s2 = gr._frontend_build()["sha16"]
    assert s2 != s1, "换字节指纹未变 ⇒ 读的是常量，判据无齿"
    assert s2 == hashlib.sha256(b"B" * 10).hexdigest()[:16]


def test_t3_page_reports_it():
    t = "\n".join(open(f, encoding="utf-8").read() for f in PAGE_FACES)
    assert 'id="paBuild"' in t, "缺徽标容器"
    assert "fetchPaBuild" in t and "fetchPaBuild()" in t, "缺取指纹的函数或 boot 调用"
    assert "data-pa-build" in t, "缺 data-pa-build（探针/脚本读这个）"
    assert "'/v9/pa/build'" in t or '"/v9/pa/build"' in t, "页面必须打构建指纹路由"
    assert "读数不可得" in t, "缺「读数不可得」态（⛔ 不许静默）"


def test_t4_真源响应头带指纹与no_store():
    c = _app().test_client()
    r = c.get("/web/pa.html")
    assert r.status_code == 200
    assert "no-store" in (r.headers.get("Cache-Control") or ""), r.headers
    assert r.headers.get("X-PA-Build-Sha16") == _sha16(PAGE), r.headers
    assert len(r.get_data()) == os.path.getsize(PAGE)


def test_t5_非pa_html不得被盖PA指纹():
    c = _app().test_client()
    r = c.get("/web/index.html")
    if r.status_code != 200:
        return  # 不适用（不等于没验）
    assert "X-PA-Build-Sha16" not in r.headers, "PA 指纹串到别的静态件上了"


def test_t6_判据必须打在真源上():
    """⭐ 把「真源」钉死：提供 /web/<path:filename> 的**注册 bp** 必须就是带指纹的那份。

    这条是本文件第一版翻车的产物（指纹写在没人注册的 health_bp 上 ⇒ 用例绿、线上空）。
    它从主文件推导真源，⛔ 不写死模块名；哪天有人再挪文件而漏改这里，它会判红。
    """
    mods = _registered_bp_modules()
    assert mods, "没能从 %s 推导出任何已注册的 bp（判据自身失效，须修本测试）" % MAIN
    live = []
    for m in mods:
        p = m.replace(".", os.sep) + ".py"
        if os.path.exists(p) and '"/web/<path:filename>"' in open(p, encoding="utf-8").read():
            live.append(m)
    assert len(live) == 1, "应恰好只有一个**已注册**的 bp 提供 /web/<path:filename>，实得 %r" % live
    src = open(live[0].replace(".", os.sep) + ".py", encoding="utf-8").read()
    assert "X-PA-Build-Sha16" in src, "构建指纹没打在真源 %s 上（打在别处 ⇒ 线上无变化＝假绿）" % live[0]
    assert "no-store" in src, "真源 %s 缺 no-store" % live[0]
