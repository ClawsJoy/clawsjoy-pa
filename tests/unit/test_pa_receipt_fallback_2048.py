# -*- coding: utf-8 -*-
r"""pm_2048 之齿 —— 回执之 fallback **收一句人话** ＋ 折名**一名** ＋ 轴栏**清符号**（CW b2a5182）。

一事（pm_2048 §一.2 ／ §三.3 ／ §三.4 · 我一手真渲之证）：
  ⒜ 轴栏 `#paModeHintText` 逐字曾载「· 陪着 · 只商量 · ⛔ 替你动手」⇒ 裁：**清**（改「不替你动手」·
     唯人话 · 射程唯此一枚 —— 余十余处 `⛔` 经真渲皆 ⛔ 在屏）。
  ⒝ 回执之 fallback（端 ⛔ 给 `human` · 旧端 ∨ 无回执）：旧形为**六行工程语上屏**，其末行书「工程注记」
     ⇒ **并议**：收为**一句人话** ∧ 其六行仍入本块 `title`（工程之据 · ⛔ 丢信息）。
  ⒞ 折名一名：「工程注记」⇒「来源 ／ 详情」（承 pm_2022 §二.⒞ · 与初访卡一名）。

判据（⭐ 逐条自证 · ⛔ 只报「已绿」）：
  R1 源级：`VAL.companion.note` ⛔ 载 `⛔`；`web/pa.html` 之 `#modelText` 行（**文 ＋ `title`**）⛔ 载 `⛔`。
  R2 源级：`rcRefresh` 之 else 支 ⇒ `hr.textContent` 唯**一次**赋值（⛔ 拼 `_synt` ／ ⛔ `nowStr()`）；
     六行仍入本块 `title`（⛔ 丢信息）。
  R3 源级：`rcRefresh` ／ `rcLines` ／ `ledgerPass` 之**用户面字面** ⛔ 载「工程注记」∧
     折名 ＝「来源 ／ 详情」。
  R4 真函（node · 桩 DOM）：真跑 `rcRefresh`（无回执 ／ 有回执而无 `human` ／ 有 `human` 三态）⇒
     屏文逐字 ∧ 屏文 ⛔ 载禁词（`⛔` ／「工程注记」／端字段名 ／径 ／ `pm_` ／ `/v9/`）∧
     `title` 载六行（⛔ 丢信息）。
  R5 祖链判（真 Chrome × CDP · **真页**）：二档宽（`1440` ／ `1024`）× 「会话」面 ⇒ 屏上之文
     ⛔ 载 `⛔` ／「工程注记」／「未验证」／「缺什么」∧ 轴栏之辞 ＝「· 陪着 · 只商量 · 不替你动手」∧
     fallback 之回执屏文 ＝ **唯一句**（真 inject `human` ⇒ 屏唯端之四行）。
  R6 正控（有齿）：判据食**假扫**（植一命中）⇒ 必红（防「永远 skip」之假绿）。
  R0 守（裁⒞）：`5102` ⛔ 在 ∨ 环境不就绪（⛔ chrome ／ ⛔ node）⇒ **skip**（⛔ 红）∧ ⛔ 触网。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_receipt_fallback_2048.py -q -p no:cacheprovider
"""
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
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SELFDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
HTML = ROOT / "web" / "pa.html"
SCRATCH = ROOT / "data" / "tmp" / "_cw_rc2048"
MOD = ROOT / "tests" / "unit" / "cw_chrome_reap.py"

#: fallback 之屏文（逐字 · 唯此一句）
FALLBACK = u"\U0001F4CB 本轮回执：本轮未取到回执（可再发一次）"
#: 轴栏之辞（逐字 · 一处定形 = VAL.companion.note）
HINT_OK = u"· 陪着 · 只商量 · 不替你动手"
#: 屏上 ⛔ 得见者（本批之射程）
BAN_SCREEN = (u"⛔", u"工程注记", u"未验证", u"缺什么")
#: 屏文 ⛔ 得载者（承 P3：行数 ／ 径 ／ 端键名）
BAN_TEXT = (u"⛔", u"工程注记", u"wall_s", u"bytes", u"tokens", u"pm_", u"/v9/", u".jsonl")
#: 六行（其**键**须在 title ⇒ 反控「⛔ 丢信息」）
SIX = (u"做了什么", u"凭什么", u"花了多少", u"谁批的", u"结论", u"下一步")
#: 端之 human（逐字 · core/pa/gateway_routes.py 之 PA_TURN_HUMAN）
HUMAN = {"一句": u"✅ 已记下这一轮（可回看）", "做了什么": u"记下你这一轮的话与答复",
         "动了哪些件": u"对话档（只增 · 原稿未动）", "可否退": u"可 —— 只增记；要撤说一声"}

_ESC = re.compile(r"\\u([0-9a-fA-F]{4})")


def _de(s):
    u"""JS 之转义（`\\uXXXX`）⇒ 真字（面之文有两形 ⇒ 断言须对**渲染之文**）。"""
    return _ESC.sub(lambda m: chr(int(m.group(1), 16)), s)


def _src():
    return io.open(str(SELFDESC), encoding="utf-8").read()


def _html():
    return io.open(str(HTML), encoding="utf-8").read()


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


def _var_line(src, name):
    for ln in src.split("\n"):
        if ln.strip().startswith("var " + name):
            return ln
    raise AssertionError(u"未找到 var " + name)


# ------------------------------- R1 源级 · 轴栏 -------------------------------

def test_R1_axis_note_has_no_symbol():
    u"""R1：`VAL.companion.note` ⛔ 载 `⛔` ∧ 其辞如实（「不替你动手」· pm_2048 §一.2 之裁）。"""
    s = _de(_src())
    val = s[s.index(u"var VAL = {"):]
    val = val[:val.index(u"};")]
    assert u'note:"陪着 · 只商量 · 不替你动手"' in val, u"陪伴之 `note` 须为人话（⛔ 符号）：" + val[:200]
    assert u"⛔" not in val, u"轴栏之辞 ⛔ 载符号（pm_2048 §一.2）：" + val[:200]
    assert u"真动手 · 有交付 · 可验收" in val, u"同轴之体例须一（办事之辞）"


def test_R1b_static_skeleton_has_no_symbol():
    u"""R1b：`web/pa.html` 之 `#modelText` 行（**文 ＋ `title`**）⛔ 载 `⛔`（静态骨之辞须与 `VAL` 一）。"""
    h = _de(_html())
    rows = [x for x in h.split("\n") if u'id="modelText"' in x]
    assert len(rows) == 1, len(rows)
    assert u"⛔" not in rows[0], u"静态骨 ⛔ 载符号：" + rows[0][:400]
    assert u"不替你动手" in rows[0], u"静态骨须与 `VAL` 同辞：" + rows[0][:400]


# ------------------------------- R2 ／ R3 源级 · 回执 -------------------------------

def test_R2_fallback_is_one_line_and_title_keeps_six():
    u"""R2：`rcRefresh` 之 else 支 ⇒ 屏文唯**一次**赋值（⛔ 拼 `_synt`）∧ 六行仍入 `title`。"""
    s = _src()
    rr = _fn(s, "rcRefresh")
    i = rr.index(u"if(_hum){")
    j = rr.index(u"    } else {", i)
    k = rr.index(u"\n    }", j)
    else_branch = rr[j:k]
    assert else_branch.count(u"hr.textContent") == 1, \
        u"fallback 支须**唯一次**写屏文（⛔ 拼六行）：" + else_branch[:400]
    assert u"_synt.join" not in else_branch, u"六行 ⛔ 得拼入屏文：" + else_branch[:400]
    assert u"nowStr()" not in else_branch, u"读数刻 ⛔ 得上屏（今入 `title`）：" + else_branch[:400]
    assert u"_synt.join" in rr, u"反控（⛔ 丢信息）：六行仍须入本块 `title`"
    assert u"'｜本轮读数刻：'" in _de(rr), u"反控：读数刻须入 `title`（⛔ 丢）"


def test_R3_no_internal_term_on_user_face_and_fold_named_once():
    u"""R3：`rcRefresh` ／ `rcLines` ／ `ledgerPass` 之用户面字面 ⛔ 载「工程注记」∧ 折名一名。"""
    s = _de(_src())
    for name in (u"rcRefresh", u"rcLines", u"ledgerPass", u"whoText", u"costText"):
        body = _fn(s, name)
        assert u"工程注记" not in body, name + u" 之用户面字面 ⛔ 载「工程注记」（pm_2048 §三.4⒜ · 一名）"
    lp = _fn(s, "ledgerPass")
    assert u"<summary>来源 ／ 详情</summary>" in lp, u"折名须为「来源 ／ 详情」：" + lp[:400]
    assert u"来源 ／ 详情" in _fn(s, "rcLines"), u"尾行之去处之名须同一（一名）"


# ------------------------------- R4 真函（node · 桩 DOM） -------------------------------

_NODE_PRE = u"""
function N(tag, cls){ this.tag = tag || 'div'; this.cls = cls || ''; this.kids = []; this._t = null;
  this.parentNode = null; this.attrs = {}; this.dataset = {}; this.title = ''; }
function T(x){ var n = new N('#text'); n._t = String(x); return n; }
Object.defineProperty(N.prototype, 'textContent', {
  get: function(){ var s = (this._t == null ? '' : this._t); for(var i = 0; i < this.kids.length; i++){ s += this.kids[i].textContent; } return s; },
  set: function(v){ this._t = null; this.kids = [T(String(v))]; } });
N.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
N.prototype.getAttribute = function(k){ return this.attrs[k]; };
N.prototype.appendChild = function(c){ c.parentNode = this; this.kids.push(c); return c; };
N.prototype.insertBefore = function(c){ c.parentNode = this; this.kids.unshift(c); return c; };
N.prototype.querySelector = function(){ return null; };
var HR = new N('div'); HR.id = 'paHumanReceipt';
var document = { getElementById: function(id){ return (id === 'paHumanReceipt') ? HR : null; },
  createElement: function(t){ return new N(t); }, querySelectorAll: function(){ return []; } };
var paRun = null, paRunSrc = '', SRC = 'test';
function Q(id){ try{ return document.getElementById(id); }catch(e){ return null; } }
function ensureHost(){ return new N('div'); }
__FNS__
var OUT = {};
paRun = null; rcRefresh();
OUT.none = {text: String(HR.textContent), title: String(HR.title)};
paRun = {receipt: {recorded: true, session_lines_before: 8, session_path: 'data/v9/pa/sessions/x.jsonl'}};
rcRefresh();
OUT.nohuman = {text: String(HR.textContent), title: String(HR.title)};
paRun = {receipt: {human: __HUMAN__}};
rcRefresh();
OUT.human = {text: String(HR.textContent), title: String(HR.title)};
console.log(JSON.stringify(OUT));
"""


def _r4():
    s = _src()
    fns = u"\n".join(_fn(s, n) for n in (u"p2", u"nowStr", u"srcOf", u"rcOf", u"costRaw", u"costText",
                                         u"whoText", u"receiptText", u"lastLogs", u"pickLog",
                                         u"judgeText", u"rcLines", u"paTurnHuman", u"rcRefresh"))
    js = (_NODE_PRE.replace(u"__FNS__", _var_line(s, "RC_COST_NAME") + u"\n" + fns)
          .replace(u"__HUMAN__", json.dumps(HUMAN, ensure_ascii=False)))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / "r4.js"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, (r.stderr or "")[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_R4_real_fn_fallback_is_one_human_line():
    u"""R4：无回执 ／ 有回执而无 `human` ⇒ 屏**逐字** ＝ FALLBACK ∧ ⛔ 载禁词 ∧ 六行在 `title`。"""
    o = _r4()
    for st in ("none", "nohuman"):
        assert o[st]["text"] == FALLBACK, (st, o[st]["text"])
        assert "\n" not in o[st]["text"], u"屏文须唯一句（⛔ 六行）：" + repr(o[st]["text"])
        for bad in BAN_TEXT:
            assert bad not in o[st]["text"], st + u"：屏文 ⛔ 得载「%s」：%s" % (bad, o[st]["text"])
        for k in SIX:
            assert k in o[st]["title"], st + u"：反控（⛔ 丢信息）`title` 须载六行之「%s」" % k


def test_R4b_real_fn_human_branch_quotes_end_word_for_word():
    u"""R4b：有 `human` ⇒ 屏唯端之四行（一句 ／ 做了什么 ／ 动了哪些件 ／ 可否退 · 逐字）。"""
    o = _r4()
    t = o["human"]["text"]
    assert t.startswith(u"\U0001F4CB 本轮回执"), t
    for k in ("一句", "做了什么", "动了哪些件", "可否退"):
        assert HUMAN[k] in t, u"（R4b）须逐字载 human[%s]：%s" % (k, t)
    assert u"本轮读数刻" not in t and u"工程注记" not in t, t


# ------------------------------- R5 祖链判（真 Chrome × CDP） -------------------------------

_SCAN = r"""
(function(){
  function screenText(){
    var out = [];
    (function walk(n){
      for(var i = 0; i < n.childNodes.length; i++){
        var k = n.childNodes[i];
        if(k.nodeType === 3){ var x = String(k.nodeValue || ''); if(x.replace(/\s+/g, '') !== '') out.push(x.replace(/\s+/g, ' ').trim()); continue; }
        if(k.nodeType !== 1) continue;
        var cs = window.getComputedStyle(k);
        if(!cs || cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;
        if(String(k.tagName).toLowerCase() === 'details' && !k.hasAttribute('open')){
          var s = k.querySelector('summary');
          if(s) out.push('[[FOLD:' + String(s.innerText || s.textContent || '').replace(/\s+/g, ' ').trim() + ']]');
          continue;
        }
        walk(k);
      }
    })(document.body);
    return out.join(' | ');
  }
  function box(id){
    var e = document.getElementById(id); if(!e) return null;
    var r = e.getBoundingClientRect();
    return {text: String(e.innerText || '').replace(/\s+/g, ' ').trim(),
            rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]};
  }
  var t = screenText();
  var BAN = ['\u26d4', '\u5de5\u7a0b\u6ce8\u8bb0', '\u672a\u9a8c\u8bc1', '\u7f3a\u4ec0\u4e48'];
  var hits = [];
  for(var i = 0; i < BAN.length; i++){ if(t.indexOf(BAN[i]) >= 0) hits.push(BAN[i]); }
  var folds = [];
  var ds = document.querySelectorAll('details summary');
  for(var q = 0; q < ds.length; q++){ folds.push(String(ds[q].innerText || ds[q].textContent || '').replace(/\s+/g, ' ').trim()); }
  return JSON.stringify({n_el: document.querySelectorAll('body *').length, screen: t, ban_hits: hits,
    hint: box('paModeHintText'), receipt: box('paHumanReceipt'), folds: folds.slice(0, 24)});
})()
"""

_ACK = r"""
(function(){ var bs = document.querySelectorAll('button');
  for(var i = 0; i < bs.length; i++){ if(String(bs[i].textContent || '').indexOf('\u77e5\u9053\u4e86') >= 0){ bs[i].click(); return 1; } }
  return 0; })()
"""

_FACE = r"""
(function(){ try{ setFace(1); return 1; }catch(e){ return 'ERR ' + String(e); } })()
"""

_INJECT = r"""
(function(){
  var o = {};
  try{ if(typeof paRun !== 'undefined' && paRun){ paRun.receipt = {human: __HUMAN__}; o.set = 1; } }catch(e){ o.err = String(e); }
  var host = document.getElementById('thread');
  if(!host){ o.noThread = 1; return JSON.stringify(o); }
  var raw = '\ud83d\udcbe \u672c\u8f6e\u5df2\u843d\u76d8\uff08\u540e\u7aef\u56de\u6267\uff1a\u4f1a\u8bdd 8\u21928 \u884c \u00b7 data/v9/pa/sessions/x.jsonl\uff09';
  var el = document.createElement('div');
  el.className = 'tool-log'; el.setAttribute('data-raw', raw); el.textContent = raw;
  host.appendChild(el); o.injected = 1;
  return JSON.stringify(o);
})()
"""

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
const SCAN = SCAN_LIT, ACK = ACK_LIT, FACE = FACE_LIT, INJECT = INJECT_LIT;
const evalx = async (cdp, S, expr) => JSON.parse((await cdp.send('Runtime.evaluate',
  {expression: expr, returnByValue: true, awaitPromise: false}, S)).result.value);
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
    await sleep(2400);
    await cdp.send('Runtime.evaluate', {expression: ACK, returnByValue: true}, S);
    await sleep(1200);
    await cdp.send('Runtime.evaluate', {expression: FACE, returnByValue: true}, S);
    await sleep(1500);
    const one = {w: w, fallback: await evalx(cdp, S, SCAN), inject: null, human: null};
    if (OUT) {
      const shot = await cdp.send('Page.captureScreenshot', {format: 'png'}, S);
      fs.writeFileSync(OUT + '/rc2048_w' + w + '_fallback.png', Buffer.from(shot.data, 'base64'));
    }
    one.inject = await evalx(cdp, S, INJECT);
    await sleep(1500);
    one.human = await evalx(cdp, S, SCAN);
    if (OUT) {
      const shot2 = await cdp.send('Page.captureScreenshot', {format: 'png'}, S);
      fs.writeFileSync(OUT + '/rc2048_w' + w + '_human.png', Buffer.from(shot2.data, 'base64'));
    }
    res.widths.push(one);
  }
  if (OUT) { fs.writeFileSync(OUT + '/rc2048_scan.json', JSON.stringify(res, null, 1)); }
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
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from core.lib import port_config
        return int(port_config.gateway_port())
    except Exception:
        return 5102


def _health_ok(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % int(port), timeout=3) as r:
            return int(getattr(r, "status", 200)) == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def R():
    assert os.path.isfile(str(MOD)), u"器不在盘: %s" % MOD
    spec = importlib.util.spec_from_file_location("cw_chrome_reap_2048", str(MOD))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _env_reason(R):
    if not R.chrome_exe():
        return u"chrome.exe ⛔ 在"
    if not shutil.which("node"):
        return u"node ⛔ 在"
    if not _health_ok(_gateway_port()):
        return u"活端（%d）⛔ 应" % _gateway_port()
    return ""


def _verdict(scan, state):
    u"""纯判（⛔ 触真机 ⇒ 供 R6 喂假扫）：一举之果 ⇒ 违者之列。"""
    bad = []
    for b in scan.get("ban_hits", []):
        bad.append((u"屏上禁词", b, scan.get("screen", "")[:200]))
    hint = ((scan.get("hint") or {}).get("text") or "")
    if hint != HINT_OK:
        bad.append((u"轴栏之辞 ⛔ 符", HINT_OK, hint[:120]))
    rc = (scan.get("receipt") or {}).get("text") or ""
    if state == "fallback":
        if rc != FALLBACK:
            bad.append((u"fallback 之屏文 ⛔ 符「唯一句」", FALLBACK, rc[:160]))
    else:
        if HUMAN["一句"] not in rc or u"本轮读数刻" in rc:
            bad.append((u"人话支 ⛔ 符（唯端之 human）", HUMAN["一句"], rc[:160]))
    for f in scan.get("folds", []):
        if f == u"工程注记":
            bad.append((u"折名仍「工程注记」", f, ""))
    return bad


def test_R0_env_guard_has_grounds(R, monkeypatch):
    u"""R0：探活败 ⇒ 必判不就绪（R5 走 skip 而非误红）∧ 三者备 ⇒ 无因（防「永远 skip」）。"""
    mod = sys.modules[__name__]
    monkeypatch.setattr(mod, "_health_ok", lambda p: False)
    assert _env_reason(R) != "", u"探活败 ⇒ 必判不就绪"
    monkeypatch.setattr(mod, "_health_ok", lambda p: True)
    monkeypatch.setattr(R, "chrome_exe", lambda: r"C:\x\chrome.exe")
    monkeypatch.setattr(mod.shutil, "which", lambda n: r"C:\x\node.exe")
    assert _env_reason(R) == "", u"三者皆备 ⇒ 无因（⇒ R5 真跑）"


def test_R6_verdict_has_teeth():
    u"""R6 正控：假扫（植一命中）⇒ 必红（防「永远 skip」之假绿）。"""
    clean = {"ban_hits": [], "screen": "", "hint": {"text": HINT_OK},
             "receipt": {"text": FALLBACK}, "folds": [u"来源 ／ 详情"]}
    assert _verdict(clean, "fallback") == []
    assert _verdict(dict(clean, ban_hits=[u"⛔"]), "fallback"), u"屏上符号须逮"
    assert _verdict(dict(clean, hint={"text": u"· 陪着 · 只商量 · ⛔ 替你动手"}), "fallback"), u"轴栏须逮"
    assert _verdict(dict(clean, receipt={"text": u"📋 本轮回执（本轮读数刻 x）\n· 做了什么：—"}), "fallback"), u"fallback 之六行须逮"
    assert _verdict(dict(clean, folds=[u"工程注记"]), "fallback"), u"折名须逮"
    assert _verdict(dict(clean, receipt={"text": u"本轮未取到回执"}), "human"), u"人话支须逮"


def test_R5_祖链判真页之扫(R):
    u"""R5 真 Chrome × CDP：二档宽 × 「会话」面 ⇒ 屏上之文 ⛔ 载符号 ／「工程注记」∧ 轴栏之辞 ∧
    fallback 之屏文 ＝ 唯一句 ∧ 真 inject `human` ⇒ 屏唯端之四行。

    ⚠ 所扫者 ＝ **载页之态 ＋ 会话面**（未展开之面 ⛔ 计）；报文附 `n_el`（＝真扫了多少）。
    守（裁⒞）：环境不就绪 ⇒ **skip**（⛔ 红）∧ ⛔ 触网。
    """
    reason = _env_reason(R)
    if reason:
        pytest.skip(u"环境不就绪：" + reason)
    cdp_port = _free_port()
    bt = u"`"
    js = (_MJS.replace("SCAN_LIT", bt + _SCAN + bt).replace("ACK_LIT", bt + _ACK + bt)
              .replace("FACE_LIT", bt + _FACE + bt)
              .replace("INJECT_LIT", bt + _INJECT.replace(u"__HUMAN__", json.dumps(HUMAN, ensure_ascii=False)) + bt))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / "rc2048_scan.mjs"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    env = dict(os.environ)
    env["CW_CDP_PORT"] = str(cdp_port)
    env["CW_PAGE_URL"] = "http://127.0.0.1:%d/web/pa.html" % _gateway_port()
    env["CW_OUT"] = str(SCRATCH)
    with R.run_headless(port=cdp_port, tag="cw2048", wait_s=15.0, why=u"pm_2048 祖链判（回执 fallback ＋ 轴栏）"):
        r = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=300)
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, (r.stderr or "")[-1500:])
    res = json.loads(r.stdout.strip().splitlines()[-1])
    for item in res["widths"]:
        assert item["fallback"]["n_el"] > 200, u"扫而未得页（隔离失败？）：%r" % item["fallback"]["n_el"]
        assert item["inject"].get("injected") == 1, item["inject"]
        for state in ("fallback", "human"):
            bad = _verdict(item[state], state)
            assert bad == [], u"第 %d 档 · %s：见命中 %s" % (item["w"], state, bad[:6])
