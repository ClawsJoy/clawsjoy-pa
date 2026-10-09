# -*- coding: utf-8 -*-
u"""CEO `2269` 之齿 —— 「今日四行之屏」之**真渲**：首屏四行读数（**数由器出**）＋ **空态四种可示**。

判据（CEO `2269 §一.2`）：⒜ **首屏四行读数**（**其数须由器出** ⇒ ⛔ 前端自算）；⒝ ⭐ **空态四种可示**
（**无数据 ⇒ ⛔ 空白页**）；⒞ 面 ／ 刻 ／ 口径 ／ 印（见同批之报 · ⛔ 本齿）。

⭐ 何以为「真渲之齿」（⛔ 静态读源）：
  ① 起**真 Chrome** × CDP ⇒ 载**真页**（活端 `5102`）；
  ② 取字以**活树之渲值**（`#paToday<Cap>` · 承 `paTodayRenderRows` 一处定形）⇒ ⛔ 读源猜形；
  ③ **反控** ＝ 桩之于**载页前**注入（`Page.addScriptToEvaluateOnNewDocument` ⇒ 面自走其真路
     `paLoadToday` ⇒ `paGetJson` ⇒ `fetch`）—— ⛔ 直改 DOM（那只是「渲」之齿 · ⛔ 证「面由器取数」）。

⚠ 器之「空态」四句 ⛔ 本齿自书 —— 唯取 `GET /v9/pa/today` 之 `空态` 键（**一处之源** · 承
  `pm_1823` P4 ／ `pm_1824 §二.1`）⇒ 桩只改 `数` ／ `件`，⛔ 改 `空态`（否则成「自证」）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_today_empty_2269.py -q -p no:cacheprovider --basetemp=D:\\pa_tmp\\pt2269
"""
from __future__ import annotations

import importlib.util
import json
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GATEWAY = 5102
URL = "http://127.0.0.1:%d/web/pa.html" % GATEWAY
API_URL = "http://127.0.0.1:%d/v9/pa/today" % GATEWAY

#: 四行（`cap` ／ 器之 `序`）—— 序不可易（定义页 §二 ／ `pm_1823` P1）
ROWS = (("Ask", 1), ("Do", 2), ("Wait", 3), ("Trace", 4))

#: 沿用我域之 CDP 器（⛔ 二处各写一套 · 承 `pm_2091` 之族）
_spec = importlib.util.spec_from_file_location(
    "cw_fc2095", str(ROOT / "tests" / "unit" / "test_pa_faceclean_2095.py"))
fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc)


DISMISS = (u"(function(){ var bs=document.querySelectorAll('button');"
           u" for(var i=0;i<bs.length;i++){ var t=String(bs[i].textContent||'').trim();"
           u" if(t==='\u77e5\u9053\u4e86'){ bs[i].click(); return 'clicked'; } }"
           u" return 'none'; })()")

#: 桩（载页**前**注入）：`/v9/pa/today` ⇒ 四行 `数` 归 `0` ∧ `件` 归空 —— **唯此二键**（`空态` ⛔ 动）
STUB = (u"(function(){ var _f = window.fetch;"
        u" window.fetch = function(u, o){"
        u"   var s = String((u && u.url) ? u.url : u);"
        u"   return _f.apply(this, arguments).then(function(r){"
        u"     if(s.indexOf('/v9/pa/today') < 0){ return r; }"
        u"     return r.text().then(function(t){"
        u"       var d; try{ d = JSON.parse(t); }catch(e){ return new Response(t, {status:r.status, headers:r.headers}); }"
        u"       (d['\u884c'] || []).forEach(function(h){ h['\u6570'] = 0; h['\u4ef6'] = []; });"
        u"       return new Response(JSON.stringify(d), {status: 200, headers: {'Content-Type': 'application/json'}});"
        u"     });"
        u"   });"
        u" }; return 'stubbed'; })()")

READ = (u"(function(){ function T(id){ var e=document.getElementById(id);"
        u" return e?String(e.textContent||'').trim():null; }"
        u" var o={when:T('paTodayWhen')};"
        u" ['Ask','Do','Wait','Trace'].forEach(function(c){"
        u"   o['val_'+c]=T('paToday'+c); o['where_'+c]=T('paToday'+c+'Where');"
        u"   var b=document.getElementById('paToday'+c+'Go');"
        u"   o['tip_'+c]=b?String(b.getAttribute('title')||''):null; });"
        u" var t=document.getElementById('paToday');"
        u" o.visible = t ? (t.getBoundingClientRect().height > 0) : false;"
        u" o.faceOn = (function(){ var p=document.getElementById('paFaceToday');"
        u"   return p ? p.classList.contains('on') : false; })();"
        u" return JSON.stringify(o); })()")


def _today_api():
    u"""器之真读数（一手 · ⛔ 经面）——`数` ／ `空态` ／ `判据之在` 皆取其源。"""
    with urllib.request.urlopen(API_URL, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _load(c, stub=False):
    u"""载真页（`stub=True` ⇒ 先注桩）。"""
    c.cmd("Page.enable")
    c.cmd("Runtime.enable")
    c.cmd("Emulation.setDeviceMetricsOverride", width=1440, height=940,
          deviceScaleFactor=1, mobile=False)
    if stub:
        r = c.cmd("Page.addScriptToEvaluateOnNewDocument", source=STUB)
        assert r.get("result"), u"桩 ⛔ 注入：%r" % (r,)
    c.cmd("Page.navigate", url=URL)
    time.sleep(8.0)
    c.js(DISMISS)


def _open(stub):
    R = fc._reap()
    reason = fc._env_reason(R)
    if reason:
        pytest.skip(u"环境不就绪：" + reason)
    port = fc._free_port()
    return R, port


def _row(d, x):
    return [h for h in d[u"\u884c"] if h[u"\u5e8f"] == x][0]


def test_T1_正控_四行之数由器出(tmp_path):
    u"""正控（真路）：四行之渲值 ≡ 器之 `数`（`N 件` ∨ 该行之 `空态` 逐字）—— **⛔ 前端自算**。"""
    R, port = _open(False)
    with R.run_headless(port=port, tag="cw2269a", wait_s=15.0,
                        extra=("--remote-allow-origins=*",),
                        why=u"CEO 2269 今日四行之屏（正控 · 真路）"):
        c = fc._CDP(fc._ws_url(port))
        _load(c, stub=False)
        d = _today_api()
        rd = json.loads(c.js(READ))
        shot = c.shot(str(tmp_path / "today_real_w1440.png"))
    assert d[u"ok"] is True, u"器 ⛔ 应"
    assert u"core/pa/today.py" in d[u"\u5224\u636e\u4e4b\u5728"], u"器须自报判据之在"
    assert rd["faceOn"] is True and rd["visible"] is True, u"首屏「今日」面须在 ∧ 可见：%r" % (rd,)
    assert u"\u672c\u5c4f\u8bfb\u6570" in (rd["when"] or ""), u"刻 ⛔ 得：%r" % (rd["when"],)
    for cap, x in ROWS:
        r = _row(d, x)
        got = rd["val_" + cap]
        assert got, u"行 %s 之值 ⛔ 得（面未渲？）" % cap
        if int(r[u"\u6570"]) > 0:
            assert got == u"%d \u4ef6" % int(r[u"\u6570"]), \
                u"行 %s：面 %r ≠ 器 %d 件（⇒ 疑前端自算 · 承 2269 §一.2⒜）" % (cap, got, int(r[u"\u6570"]))
        else:
            assert got == r[u"\u7a7a\u6001"], \
                u"行 %s：数 0 ⇒ 必显该行之空态逐字（器 %r ≠ 面 %r）" % (cap, r[u"\u7a7a\u6001"], got)
        assert rd["where_" + cap], u"行 %s 之「源」⛔ 得（定义页 §三）" % cap
    assert shot > 0, u"图须落盘"


def test_T2_反控_空态四种可示(tmp_path):
    u"""反控（桩 · 面仍走真路）：四行 `数` 归 0 ⇒ 四行必显**四空态之逐字** ⇒ ⛔ 空白 ∧ ⛔ 「0 件」。

    ⚠ 桩**唯**改 `数` ／ `件` —— `空态` 仍取器之源（⇒ 非「自证」）。
    """
    R, port = _open(True)
    d = _today_api()                      # 器之源（桩 ⛔ 及此 ⇒ 追之在 **面** 之外）
    with R.run_headless(port=port, tag="cw2269b", wait_s=15.0,
                        extra=("--remote-allow-origins=*",),
                        why=u"CEO 2269 今日四行之屏（反控 · 空态四种）"):
        c = fc._CDP(fc._ws_url(port))
        _load(c, stub=True)
        rd = json.loads(c.js(READ))
        shot = c.shot(str(tmp_path / "today_empty_w1440.png"))
    seen = []
    for cap, x in ROWS:
        r = _row(d, x)
        empty = (r[u"\u7a7a\u6001"] or "").strip()
        assert empty, u"器之空态须人话（行 %s）" % cap
        got = rd["val_" + cap]
        assert got == empty, u"行 %s：数 0 ⇒ 必显空态逐字：器 %r ≠ 面 %r" % (cap, empty, got)
        assert got != u"0 \u4ef6", u"行 %s：⛔ 以「0 件」充「没有」（空 ⛔ 混 缺）" % cap
        seen.append(got)
    assert len(set(seen)) == 4, u"四空态须各异（四位一辞 ⇒ 疑前端硬编）：%r" % (seen,)
    assert shot > 0, u"图须落盘"
