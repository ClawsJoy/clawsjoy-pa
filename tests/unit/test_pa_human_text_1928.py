# -*- coding: utf-8 -*-
r"""令 1928 之齿 —— 用户面之文：**屏唯人话**（端径 ／ 端字段名入 `title`）＋ **祖链判**（真渲之扫）。

一事（pm_1928 §一 · 我一手真渲之证）：`paModelState(sel, …)` 所写 ⇒ `sel.options[0].textContent`
  真载 `GET /v9/pa/providers 未应答（…）` —— **端径上屏**（且在下拉之项文里 · 比 `title` 更显）
  ⇒ 裁⒜：改人话（「模型表未应答（因）· 扫于刻」）∧ 端径 ／ 端字段名 ── 入 `sel.title`
  （＝**工程之据之地** · 可查 · ⛔ 丢 —— 承 pm_1855 §三.2）。

判据（⭐ 逐条自证 · ⛔ 只报「已绿」）：
  H1 定点（源级）：`paModelRender` 之四个 `paModelState(sel, …)` 之**第一参**（＝屏上之辞）
     ⛔ 载 `GET `／`/v9/`／`models_table`／`HTTP`；**第三参**（＝`title`）载 `/v9/pa/providers`
     （可查之反控 —— ⛔ 以删信息换干净）。
  H2 真函（node · 桩 DOM）：真跑 `paModelRender` 四支 ＋ 得表之支 ⇒ `options[0].textContent` 逐字 ∧
     `title` 逐字 ∧ 得表后 `title` 清（⛔ 留旧态之据）。
  H3 祖链判（真 Chrome × CDP · **真页**）：可见之文（祖链判：`display:none` ／ `visibility` ／
     `opacity:0` ／ **未开之 `<details>`** 皆 ⛔ 计）⇒ 饰四符 ／ 端径 ／ 端字段名 皆 `0`；
     可见之 `title` ⇒ 饰四符 `0`（裁⒝：饰四符扫「屏上 ＋ `title`」· 端径 ／ 字段名 **唯扫屏上**）；
     并真渲 `paModelRender` 四支 ⇒ 项文 ⛔ 载端径 ∧ `title` 载之。
  H4 正控（有齿）：判据食**假扫**（植一命中）⇒ 必红（防「永远 skip」之假绿）。
  H0 守（裁⒞）：`5102` ⛔ 在 ∨ 环境不就绪（⛔ chrome ／ ⛔ node）⇒ **skip**（⛔ 红）∧ ⛔ 触网
     （唯本机回环）；并正控其判据有据（探活败 ⇒ 必判不就绪）。
⚠ **H3 扫之界（照实 · ⛔ 只报「命中 0」而不附「扫的是什么」—— 承 pm_1923 §三.1 之自戒）**：所扫者 ＝
  **载页之态**（`1440` ／ `1024`）之可见之文（`n_el` ／ `n_titles` 随报文附 ⇒ 读之须连此二数一起读）；
  ⭐ 未展开之面（`更多 ▾` 之各节 ／ 密钥面 ／ 未开之 `<details>`）**⛔ 计**（祖链判之定义）
  ⇒ 故本条**⛔ 证**「全页皆净」，唯证「**载页之态**净」∧ 模型选单四态之真渲净。
  同族之**余者**（照实 · 归 `9.0.12` 之面批）：`keys.js` ／ `more.js` 之「源：GET /v9/pa/providers · 扫于…」
  等工程之文，于其面**展开时**方上屏 ⇒ 须另以「展开诸面」之扫收口（本器已备 `paMore(true)` 之钩）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_human_text_1928.py -q -p no:cacheprovider
`"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = os.path.join(ROOT, "web", "pa", "faces", "config.js")
CORE = os.path.join(ROOT, "web", "pa", "core.js")
TASKS = os.path.join(ROOT, "web", "pa", "faces", "tasks.js")
MOD = os.path.join(ROOT, "tests", "unit", "cw_chrome_reap.py")
SCRATCH = os.path.join(ROOT, "data", "tmp", "_cw_zel1928")

#: 屏上之辞 ⛔ 载者（行话 ／ 端径 ／ 端字段名 · 承 pm_1886 §二.2 ｜ pm_1928 §一.1⒝）
SCREEN_BAN = ("/v9/", "/api/", "models_table", "HTTP", "GET ", "POST ", "ui_state", "outbound")
#: 可查（`title`）须载者 —— 端径之真源
TIP_MUST = "/v9/pa/providers"

AT = "12:03:44"          # 假刻（真渲用 · 端字段现刻 ＝ 屏刻）


def _read(p):
    return io.open(p, encoding="utf-8").read()


def _fn(src, name):
    i = src.find("function " + name + "(")
    assert i > 0, u"未找到函数 " + name
    d, opened, e = 0, False, i
    while e < len(src):
        c = src[e]
        if c == "{":
            d += 1
            opened = True
        elif c == "}":
            d -= 1
            if opened and d == 0:
                return src[i:e + 1]
        e += 1
    raise AssertionError(u"函数 " + name + u" 花括号不配平")


def _decl(src, prefix):
    for ln in src.split("\n"):
        if ln.startswith(prefix):
            return ln
    raise AssertionError(u"未找到声明 " + prefix)


# ---------- H1 定点（源级）：屏上之辞 ⛔ 载端径 ／ 字段名 ----------

def _model_state_calls():
    u"""`paModelRender` 之 `paModelState(sel, …)` 之调列（逐条）。"""
    body = _fn(_read(CFG), "paModelRender")
    out = []
    for ln in body.split("\n"):
        i = ln.find("paModelState(sel,")
        if i >= 0:
            out.append(ln[i:])
    return out


@pytest.mark.unit
def test_H1_屏上之辞唯人话():
    u"""第一参（＝真渲之项文）⛔ 载端径 ／ 端字段名 ／ 行话；第三参（＝`sel.title` · 可查）载端径之真源。

    由（一手 · pm_1928 §一.1）：`sel.options[0].textContent` 真载其辞 ⇒ 其文**在屏上**。
    """
    calls = _model_state_calls()
    assert len(calls) == 4, u"四态须四调（未应答 ／ ⛔ 200 ／ 键 ⛔ 在 ／ 0 行）：%d" % len(calls)
    for tail in calls:
        m = re.match(r"paModelState\(sel, (.*?), '([^']*)'", tail)
        assert m, u"未得其参：" + tail
        screen, tip = m.group(1), m.group(2)
        for bad in SCREEN_BAN:
            assert bad not in screen, (
                u"屏上之辞 ⛔ 载「%s」（行话 ／ 端径 ⇒ 人话）：%s" % (bad, screen))
        assert TIP_MUST in tip, u"端径须可查（`title` · ⛔ 丢真源）：" + tip
    assert u"sel.title = String(tip || '')" in _read(CFG), u"可查之一处定形（第三参 ⇒ `title`）"
    assert u"sel.title = '';" in _fn(_read(CFG), "paModelRender"), u"得表 ⇒ 旧态之据须清"


# ---------- H2 真函（node · 桩 DOM）：真跑四支 ----------

_NODE_STUB = r"""
var window = {};
@GAP@
@ESC@
var document = {
  getElementById: function(){ return null; },
  createElement: function(){ return {style:{}, id:'', textContent:'',
                                     appendChild:function(){}, setAttribute:function(){}}; }
};
var localStorage = {getItem: function(){ return null; }, setItem: function(){}};
function MK(){
  var o = {style:{}, disabled:false, title:'', value:'', options:[],
           parentNode:{appendChild:function(){}}, _h:''};
  Object.defineProperty(o, 'innerHTML', {get:function(){ return o._h; }, set:function(v){
    o._h = String(v);
    var re = /<option value="([^"]*)">([\s\S]*?)<\/option>/g, m, arr = [];
    while((m = re.exec(o._h)) !== null){ arr.push({value:m[1], textContent:m[2]}); }
    o.options = arr;
  }});
  return o;
}
var out = {at: AT_LIT};
var sel = MK();
paModelRender(sel, 0, null, AT_LIT, '试之错（真渲）', '');
out.err = {opt: sel.options[0].textContent, title: sel.title};
sel = MK(); paModelRender(sel, 500, null, AT_LIT, '', '');
out.bad200 = {opt: sel.options[0].textContent, title: sel.title};
sel = MK(); paModelRender(sel, 200, {}, AT_LIT, '', '');
out.nokey = {opt: sel.options[0].textContent, title: sel.title};
sel = MK(); paModelRender(sel, 200, {models_table: []}, AT_LIT, '', '');
out.zero = {opt: sel.options[0].textContent, title: sel.title};
sel = MK();
paModelRender(sel, 200, {models_table: [{id:'remote:deepseek', kind:'remote', label:'D', '可用':'钥已配'}]},
              AT_LIT, '', '');
out.ok = {opt: sel.options[0].textContent, title: sel.title, disabled: sel.disabled,
          n: sel.options.length};
sel = MK();
paModelRender(sel, 0, null, AT_LIT, 'x', '');
var t1 = sel.title;
paModelRender(sel, 200, {models_table: [{id:'a', kind:'local'}]}, AT_LIT, '', '');
out.clear = {before: t1, after: sel.title};
console.log(JSON.stringify(out));
"""


def _parts_cfg():
    u"""自 `config.js` 摘其需者（**一处之源** · ⛔ 拄一份字面）。"""
    s = _read(CFG)
    return [
        _decl(s, u"var paModelRows"), _decl(s, u"var paModelKept"),
        _fn(s, u"paModelKindTxt"), _fn(s, u"paModelOptHtml"), _fn(s, u"paModelState"),
        _fn(s, u"paModelAliasMap"), _fn(s, u"paModelResolve"), _fn(s, u"paModelNote"),
        _fn(s, u"paModelPersist"), _fn(s, u"paModelRender"),
    ]


def _gap_block():
    s = _read(CORE)
    i = s.find("window.PA_GAP = {")
    assert i > 0, u"未得 PA_GAP（一处定形）"
    j = s.find("};", i)
    assert j > i, u"PA_GAP 块末未得"
    return s[i:j + 2]


def _node(js, tag):
    os.makedirs(SCRATCH, exist_ok=True)
    f = os.path.join(SCRATCH, tag + ".js")
    io.open(f, "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node")
    assert exe, u"node ⛔ 在"
    r = subprocess.run([exe, f], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, (r.stderr or "")[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


_C = {}


def _stub():
    if "s" not in _C:
        js = (chr(10).join(_parts_cfg()) + chr(10) + _NODE_STUB.replace("@GAP@", _gap_block() + chr(10) + "var PA_GAP = window.PA_GAP;")
              .replace("@ESC@", _fn(_read(TASKS), u"paEsc"))
              .replace("AT_LIT", "'" + AT + "'"))
        _C["s"] = _node(js, "zel1928_stub")
    return _C["s"]


@pytest.mark.unit
def test_H2_真函四支之文():
    u"""真跑 `paModelRender` ⇒ 项文人话 ∧ `title` 载端径 ∧ 得表后 `title` 清。"""
    s = _stub()
    assert s["err"]["opt"].startswith(u"不可达（模型表未应答（试之错（真渲））"), s["err"]["opt"]
    assert s["bad200"]["opt"].startswith(u"不可达（模型表未回成（服务之回 500）"), s["bad200"]["opt"]
    assert u"回退支" in s["nokey"]["opt"] and u"模型表" in s["nokey"]["opt"], s["nokey"]["opt"]
    assert s["zero"]["opt"] == u"模型表照实 0 行（扫于 " + AT + u"）", s["zero"]["opt"]
    for k in ("err", "bad200", "nokey", "zero"):
        opt, tip = s[k]["opt"], s[k]["title"]
        for bad in SCREEN_BAN:
            assert bad not in opt, u"（H2）屏上之辞 ⛔ 载「%s」：%s" % (bad, opt)
        assert TIP_MUST in tip, u"（H2）端径须入 `title`：" + tip
    assert u"云端 · D" in s["ok"]["opt"] and s["ok"]["disabled"] is False, s["ok"]
    assert s["ok"]["n"] == 1, s["ok"]
    assert s["ok"]["title"] == "", u"得表 ⇒ `title` 须清：" + s["ok"]["title"]
    assert TIP_MUST in s["clear"]["before"] and s["clear"]["after"] == "", s["clear"]


# ---------- H3 祖链判（真 Chrome × CDP）：真页之扫 ----------

_SCAN = r"""`
(function(){
  var MARKS = ['**', '~~', String.fromCharCode(96), '*'];
  var TEXT_ONLY = ['/v9/', '/api/', 'http://', 'https://', 'models_table', 'ui_state',
                   'outbound', 'tool_steps', 'GET ', 'POST ', 'HTTP ', 'sha256'];
  var vis = function(el){
    var n = el;
    while(n && n !== document.documentElement){
      var cs = getComputedStyle(n);
      if(cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity || '1') <= 0){
        return false;
      }
      if(n.tagName === 'DETAILS' && !n.open){
        var s = n.querySelector('summary');
        if(!(s && s.contains(el))){ return false; }
      }
      n = n.parentElement;
    }
    return true;
  };
  var out = {marks_text: [], marks_title: [], text_hits: [], n_titles: 0,
             n_el: document.querySelectorAll('body *').length};
  var test = function(where, s){
    MARKS.forEach(function(mk){ if(s.indexOf(mk) >= 0){ out[where].push([mk, s.slice(0, 160)]); } });
    if(where === 'marks_text'){
      TEXT_ONLY.forEach(function(tok){ if(s.indexOf(tok) >= 0){ out.text_hits.push([tok, s.slice(0, 160)]); } });
    }
  };
  var els = document.querySelectorAll('body *');
  for(var i = 0; i < els.length; i++){
    var el = els[i];
    if(el.children.length){ continue; }
    if(!vis(el)){ continue; }
    var t = String(el.textContent || '').replace(/\s+/g, ' ').trim();
    if(t){ test('marks_text', t); }
  }
  var tis = document.querySelectorAll('[title]');
  for(var k = 0; k < tis.length; k++){
    if(!vis(tis[k])){ continue; }
    out.n_titles++;
    var tt = String(tis[k].getAttribute('title') || '');
    if(tt){ test('marks_title', tt); }
  }
  return JSON.stringify(out);
})()
`"""

_FIX = r"""`
(async function(){
  var sel = document.getElementById('cfgModel');
  var out = {found: !!sel, at: AT_LIT};
  if(!sel){ return JSON.stringify(out); }
  var grab = function(){
    var o = sel.options && sel.options[0];
    return {opt: String((o && o.textContent) || ''), title: String(sel.getAttribute('title') || '')};
  };
  paModelRender(sel, 0, null, AT_LIT, '试之错（真渲）', ''); out.err = grab();
  paModelRender(sel, 500, null, AT_LIT, '', ''); out.bad200 = grab();
  paModelRender(sel, 200, {}, AT_LIT, '', ''); out.nokey = grab();
  paModelRender(sel, 200, {models_table: []}, AT_LIT, '', ''); out.zero = grab();
  paModelRender(sel, 200,
    {models_table: [{id:'remote:deepseek', kind:'remote', label:'D', '可用':'钥已配'}]}, AT_LIT, '', '');
  out.ok = {opt: grab().opt, title: String(sel.getAttribute('title') || ''),
            disabled: sel.disabled, n: sel.options.length};
  return JSON.stringify(out);
})()
`"""

_MJS = r"""
import fs from 'node:fs';
const PORT = Number(process.env.CW_CDP_PORT || 0);
const PAGE = process.env.CW_PAGE_URL;
const OUT = process.env.CW_OUT || '';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
class CDP {
  constructor(ws){ this.ws = ws; this.id = 0; this.pend = new Map(); this.ev = [];
    ws.addEventListener('message', (e) => { const m = JSON.parse(e.data);
      if(m.id && this.pend.has(m.id)){ const p = this.pend.get(m.id); this.pend.delete(m.id);
        if(m.error){ p.rej(new Error(JSON.stringify(m.error))); } else { p.res(m.result); } }
      else if(m.method){ this.ev.push(m); } }); }
  send(method, params = {}, sessionId){ const id = ++this.id; const msg = {id, method, params};
    if(sessionId){ msg.sessionId = sessionId; }
    return new Promise((res, rej) => { this.pend.set(id, {res, rej}); this.ws.send(JSON.stringify(msg)); }); }
  async waitEvent(method, ms = 20000){ const t0 = Date.now();
    while(Date.now() - t0 < ms){ const i = this.ev.findIndex((e) => e.method === method);
      if(i >= 0){ return this.ev.splice(i, 1)[0]; } await sleep(60); }
    return null; }
}
const SCAN = SCAN_LIT;
const FIX = FIX_LIT;
const main = async () => {
  const ver = await (await fetch('http://127.0.0.1:' + PORT + '/json/version')).json();
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  const cdp = new CDP(ws);
  const tg = await cdp.send('Target.createTarget', {url: 'about:blank'});
  const at = await cdp.send('Target.attachToTarget', {targetId: tg.targetId, flatten: true});
  const S = at.sessionId;
  await cdp.send('Page.enable', {}, S); await cdp.send('Runtime.enable', {}, S);
  const res = {browser: ver.Browser, widths: []};
  for (const w of [1440, 1024]) {
    await cdp.send('Emulation.setDeviceMetricsOverride',
                   {width: w, height: 900, deviceScaleFactor: 1, mobile: false}, S);
    await cdp.send('Page.navigate', {url: PAGE + '?t=' + Date.now()}, S);
    await cdp.waitEvent('Page.loadEventFired', 25000);
    await sleep(2200);
    const r = await cdp.send('Runtime.evaluate', {expression: SCAN, returnByValue: true, awaitPromise: true}, S);
    res.widths.push({w: w, scan: JSON.parse(r.result.value)});
    if (w === 1440) {
      const f = await cdp.send('Runtime.evaluate', {expression: FIX, returnByValue: true, awaitPromise: true}, S);
      res.fix = JSON.parse(f.result.value);
      if (OUT) {
        const shot = await cdp.send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true}, S);
        fs.writeFileSync(OUT + '/zel1928_page_1440.png', Buffer.from(shot.data, 'base64'));
      }
    }
  }
  if (OUT) { fs.writeFileSync(OUT + '/zel1928_scan.json', JSON.stringify(res, null, 1)); }
  console.log(JSON.stringify(res));
  ws.close();
};
main().catch((e) => { console.error('FATAL', e && e.message); process.exit(1); });
"""


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _gateway_port():
    u"""真源：`core/lib/port_config.gateway_port()`（未配 ⇒ 食回落 · 本判用）。"""
    try:
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from core.lib import port_config
        return int(port_config.gateway_port())
    except Exception:
        return 5102


def _health_ok(port):
    u"""活端探（唯本机回环 · ⛔ 触网）。"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % int(port), timeout=3) as r:
            return int(getattr(r, "status", 200)) == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def R():
    assert os.path.isfile(MOD), u"器不在盘: %s" % MOD
    spec = importlib.util.spec_from_file_location("cw_chrome_reap_1928", MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _env_reason(R):
    u"""环境就绪否（⛔ 就绪 ⇒ 其因；就绪 ⇒ ""）。"""
    if not R.chrome_exe():
        return u"chrome.exe ⛔ 在"
    if not shutil.which("node"):
        return u"node ⛔ 在"
    if not _health_ok(_gateway_port()):
        return u"活端（%d）⛔ 应" % _gateway_port()
    return ""


def _verdict(scan):
    u"""纯判：一扫之果 ⇒ 违者之列（⛔ 触真机 · 供 H4 喂假扫）。"""
    bad = []
    for mk, s in scan.get("marks_text", []):
        bad.append((u"饰上屏（屏上之文）", mk, s))
    for mk, s in scan.get("marks_title", []):
        bad.append((u"饰入 title", mk, s))
    for tok, s in scan.get("text_hits", []):
        bad.append((u"行话 ／ 端径上屏", tok, s))
    return bad


@pytest.mark.unit
def test_H0_守_环境判据有据(R, monkeypatch):
    u"""守之正控：探活败 ⇒ 必判「不就绪」（H3 走 skip 而非误红）∧ 三者备 ⇒ 无因（防「永远 skip」）。"""
    mod = sys.modules[__name__]
    monkeypatch.setattr(mod, "_health_ok", lambda p: False)
    r1 = _env_reason(R)
    assert r1 != "", u"探活败 ⇒ 必判不就绪"
    monkeypatch.setattr(mod, "_health_ok", lambda p: True)
    monkeypatch.setattr(R, "chrome_exe", lambda: r"C:\x\chrome.exe")
    monkeypatch.setattr(mod.shutil, "which", lambda n: r"C:\x\node.exe")
    r2 = _env_reason(R)
    assert r2 == "", u"三者皆备 ⇒ 无因（⇒ H3 真跑）：" + r2


@pytest.mark.unit
def test_H4_判据有齿():
    u"""正控：假扫（植一命中）⇒ 判必红（防「永远 skip」之假绿）。"""
    clean = {"marks_text": [], "marks_title": [], "text_hits": []}
    assert _verdict(clean) == []
    assert _verdict({"marks_text": [["**", u"试"]], "marks_title": [], "text_hits": []}), u"屏上之饰须逮"
    assert _verdict({"marks_text": [], "marks_title": [["~~", u"试"]], "text_hits": []}), u"title 之饰须逮"
    assert _verdict({"marks_text": [], "marks_title": [], "text_hits": [["/v9/", u"试"]]}), u"端径须逮"
    assert _verdict({"marks_text": [], "marks_title": [], "text_hits": [["models_table", u"试"]]}), u"字段名须逮"


@pytest.mark.unit
def test_H3_祖链判真页之扫(R):
    u"""真 Chrome × CDP：二档宽 × 真页 ⇒ 可见之文 ／ `title` 之扫 ∧ 模型选单四态之真渲。

    ⚠ 所扫者 ＝ **载页之态**（未展开之面 ⛔ 计）—— 报文附 `n_el` ／ `n_titles`
      （＝真扫了多少 · 承 pm_1923 §三.1「⛔ 只报命中 0 而不附扫的是什么」）。

    守（裁⒞）：环境不就绪 ⇒ **skip**（⛔ 红）。
    """
    reason = _env_reason(R)
    if reason:
        pytest.skip(u"环境不就绪：" + reason)
    port = _gateway_port()
    cdp_port = _free_port()
    js = (_MJS.replace("SCAN_LIT", _SCAN).replace("FIX_LIT", _FIX)
          .replace("AT_LIT", "'" + AT + "'"))
    os.makedirs(SCRATCH, exist_ok=True)
    f = os.path.join(SCRATCH, "zel1928_scan.mjs")
    io.open(f, "w", encoding="utf-8", newline="\n").write(js)
    env = dict(os.environ)
    env["CW_CDP_PORT"] = str(cdp_port)
    env["CW_PAGE_URL"] = "http://127.0.0.1:%d/web/pa.html" % port
    env["CW_OUT"] = SCRATCH
    with R.run_headless(port=cdp_port, tag="zel1928", wait_s=15.0, why=u"pm_1928 祖链判"):
        r = subprocess.run(["node", f], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=300)
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, (r.stderr or "")[-1500:])
    res = json.loads(r.stdout.strip().splitlines()[-1])
    for item in res["widths"]:
        bad = _verdict(item["scan"])
        assert bad == [], u"第 %d 档：可见之文 ／ title 之扫见命中：%s" % (item["w"], bad[:6])
        assert item["scan"]["n_el"] > 200, u"扫而未得页（隔离失败？）：%r" % item["scan"]["n_el"]
    fix = res.get("fix") or {}
    assert fix.get("found"), u"未得 #cfgModel（页未载全？）"
    for k in ("err", "bad200", "nokey", "zero"):
        opt, tip = fix[k]["opt"], fix[k]["title"]
        for banned in SCREEN_BAN:
            assert banned not in opt, u"（H3）真渲之项文 ⛔ 载「%s」：%s" % (banned, opt)
        assert TIP_MUST in tip, u"（H3）端径须入 `title`：" + tip
    assert fix["zero"]["opt"] == u"模型表照实 0 行（扫于 " + AT + u"）", fix["zero"]
    assert fix["ok"]["title"] == "" and fix["ok"]["disabled"] is False, fix["ok"]