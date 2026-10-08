# -*- coding: utf-8 -*-
u"""pm_2025 §二.1 ／ pm_2028 §四.2 之齿 —— 面之回执**唯引用**端之 human 四键。

一事（pm_2025 §一）：端 POST /v9/pa/turn 已自产 human 四键（一句 ／ 做了什么 ／ 动了哪些件 ／
  可否退 · 技术总监 2023 · 我一手验通）；面侧旧形**自拟**（thread 之「✅ 本轮已存档」）∧
  **由原字剥拼**（回执区之六行由 srcOf() ／ 行数 ／ 径 拼出）⇒ 二者皆违 P3。
判据：
  H1 源级：面**唯引用** —— ledgerPass 之屏文取 human 一句（自拟者唯作旧端之回退）∧
     rcRefresh 之人话支⛔ 载自拟之头（nowStr ／ srcOf）。
  H2 真函（node 桩 · ⛔ 以源码字面代屏）：paTurnHuman 对端之三态真样 ⇒ 四键逐字；⛔ 给 ⇒ null。
  H3 真函：ledgerPass ⇒ 屏唯 human 一句 ⊕ 原字入折（⛔ 丢）⊕ **一回执唯用一行**（⛔ 以旧充新）。
  H4 反控：端 ⛔ 给（旧端 ／ 无回执）⇒ 照旧（⛔ 造辞 ／ ⛔ 失行）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_human_receipt_2025.py -q --basetemp=D:/clawsjoy_v9/data/tmp/_pt2025
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_rc2025"

#: 端之三态真样（逐字 · core/pa/gateway_routes.py 之 PA_TURN_HUMAN）
DONE = {"一句": u"✅ 已记下这一轮（可回看）", "做了什么": u"记下你这一轮的话与答复",
        "动了哪些件": u"对话档（只增 · 原稿未动）", "可否退": u"可 —— 只增记；要撤说一声"}
UNKNOWN = {"一句": u"⚠ 这一轮记下没有：一时查不到（可稍后回看）", "做了什么": u"试着记下你这一轮的话与答复",
           "动了哪些件": u"对话档（读数一时取不得）", "可否退": u"可 —— 只增记；要撤说一声"}
MISS = {"一句": u"⚠ 这一轮没记下（可再发一次）", "做了什么": u"本轮未记入档",
        "动了哪些件": u"无", "可否退": u"不适用（未动）"}
#: 屏唯人话之界（承 P3）：行数 ／ 径 ／ 端径 ／ 键名 ⛔ 得自上
FOUR = ("一句", "做了什么", "动了哪些件", "可否退")


def _src():
    return io.open(str(SDESC), encoding="utf-8").read()


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


def _ledger_re_line(src):
    for ln in src.split("\n"):
        if ln.strip().startswith("var LEDGER_RE"):
            return ln.strip()
    raise AssertionError(u"未找到 LEDGER_RE")


def _node(js, tag):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


# ------------------------------- H1 源级 -------------------------------

def test_H1_face_only_quotes_the_human_field():
    src = _src()
    lp = _fn(src, "ledgerPass")
    assert u"paTurnHuman(" in lp, u"ledgerPass 须**取**端之人话（⛔ 自拟）"
    assert u"_h['一句']" in lp, u"屏文须**逐字**取 human 之一句：" + lp[:400]
    assert u"__paHumanUsed" in lp, u"须有「一回执唯用一行」之守（⛔ 以旧回执充新行）"
    rr = _fn(src, "rcRefresh")
    assert u"paTurnHuman(" in rr, u"回执区须取端之人话"
    assert u"_hum['一句']" in rr and u"_hum['做了什么']" in rr, u"四键须各渲"
    assert u"_hum['动了哪些件']" in rr and u"_hum['可否退']" in rr, u"四键须各渲"
    _i0 = rr.index(u"if(_hum){")
    _j0 = rr.index(u"    } else {", _i0)
    hum_branch = rr[_i0:_j0]
    for bad in (u"srcOf()", u"nowStr()", u"rcLines()"):
        assert bad not in hum_branch, u"人话支 ⛔ 得自拟／剥字：" + bad
    assert u"paTurnHuman" in src and u"window.paTurnHuman" in src, u"须一处定形（并可查／可测）"


# ------------------------------- H2 真函 -------------------------------

_H2 = u"""__TURNHUMAN__
var out = {};
out.done = paTurnHuman({human: __DONE__});
out.unknown = paTurnHuman({human: __UNKNOWN__});
out.miss = paTurnHuman({human: __MISS__});
out.none = paTurnHuman({});
out.null_ = paTurnHuman(null);
out.noHuman = paTurnHuman({recorded: true, session_lines_before: 8, session_lines_after: 8,
  session_path: 'data/v9/pa/sessions/x.jsonl'});
out.partial = paTurnHuman({human: {'做了什么': '试'}});
out.extra = paTurnHuman({human: {'一句': '一', '做了什么': '', '可否退': '退'}});
console.log(JSON.stringify(out));
"""


def _h2():
    js = (_H2.replace("__TURNHUMAN__", _fn(_src(), "paTurnHuman"))
             .replace("__DONE__", json.dumps(DONE, ensure_ascii=False))
             .replace("__UNKNOWN__", json.dumps(UNKNOWN, ensure_ascii=False))
             .replace("__MISS__", json.dumps(MISS, ensure_ascii=False)))
    return _node(js, "h2")


def test_H2_real_fn_reads_the_four_keys_verbatim():
    o = _h2()
    assert o["done"] == DONE, o["done"]
    assert o["unknown"] == UNKNOWN, o["unknown"]
    assert o["miss"] == MISS, o["miss"]


def test_H4_no_human_falls_back_and_never_invents():
    o = _h2()
    assert o["none"] is None and o["null_"] is None, o
    assert o["noHuman"] is None, u"无 human ⇒ null（⛔ 由 session_lines_before 等剥字：" + json.dumps(o["noHuman"], ensure_ascii=False)
    assert o["partial"] is None, u"无「一句」⇒ 端未给人话 ⇒ 回退（⛔ 以「做了什么」充）"
    assert o["extra"] == {"一句": u"一", "可否退": u"退"}, o["extra"]


# ------------------------------- H3 真函 · ledgerPass -------------------------------

_H3 = u"""var A = mkLog('\U0001F4BE \u672c\u8f6e\u5df2\u843d\u76d8\uff08\u540e\u7aef\u56de\u6267\uff1a\u4f1a\u8bdd 8\u21928 \u884c \u00b7 data/v9/pa/sessions/x.jsonl\uff09', '1');
var B = mkLog('\U0001F4BE \u672c\u8f6e\u5df2\u843d\u76d8\uff08\u540e\u7aef\u56de\u6267\uff1a\u4f1a\u8bdd 9\u21929 \u884c\uff09', '1');
var C = mkLog('\U0001F50D \u5171\u641c 540 \u4ef6', '1');
ELS = [A, B, C];
ledgerPass();
function screenOf(n){
  var c = n.cloneNode(true);
  var es = c.querySelectorAll('details.eng');
  for(var i = 0; i < es.length; i++){ if(es[i].parentNode){ es[i].parentNode.removeChild(es[i]); } }
  return String(c.textContent);
}
var O = {};
O.aText = String(A.textContent);
O.aScreen = screenOf(A);
O.aUser = String(A.getAttribute('data-pa-user'));
O.bText = String(B.textContent);
O.bScreen = screenOf(B);
O.cText = String(C.textContent);
O.aEng = A.querySelectorAll('details.eng')[0] ? String(A.querySelectorAll('details.eng')[0].textContent) : null;
console.log(JSON.stringify(O));
"""

_PRE = u"""function N(tag, cls){ this.tag = tag || 'div'; this.cls = cls || ''; this.kids = []; this._t = null; this.parentNode = null; this.attrs = {}; this.dataset = {}; }
function T(x){ var n = new N('#text'); n._t = String(x); return n; }
Object.defineProperty(N.prototype, 'textContent', {
  get: function(){ var s = (this._t == null ? '' : this._t); for(var i = 0; i < this.kids.length; i++){ s += this.kids[i].textContent; } return s; },
  set: function(v){ this._t = null; this.kids = [T(String(v))]; } });
Object.defineProperty(N.prototype, 'className', {
  get: function(){ return this.cls; },
  set: function(v){ this.cls = String(v); } });
Object.defineProperty(N.prototype, 'innerHTML', {
  get: function(){ return ''; },
  set: function(html){
    this._t = null; this.kids = [];
    var stack = [this];
    var re = /<\\/([A-Za-z0-9]+)\\s*>|<([A-Za-z0-9]+)((?:\\s+[A-Za-z0-9_:-]+\\s*=\\s*"[^"]*")*)\\s*\\/?>|([^<]+)/g;
    var m;
    while((m = re.exec(String(html))) !== null){
      var top = stack[stack.length - 1];
      if(m[1]){ if(stack.length > 1) stack.pop(); }
      else if(m[2]){
        var el = new N(m[2]); var attrs = m[3] || '';
        var ar = /([A-Za-z0-9_:-]+)\\s*=\\s*"([^"]*)"/g, a;
        while((a = ar.exec(attrs)) !== null){
          if(a[1] === 'class'){ el.cls = a[2]; } else { el.attrs[a[1]] = a[2]; }
        }
        top.appendChild(el); stack.push(el);
      }
      else if(m[4] !== undefined){ top.appendChild(T(m[4])); }
    }
  } });
N.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
N.prototype.getAttribute = function(k){ return this.attrs[k]; };
N.prototype.appendChild = function(c){ c.parentNode = this; this.kids.push(c); return c; };
N.prototype.removeChild = function(c){ var i = this.kids.indexOf(c); if(i >= 0){ this.kids.splice(i, 1); c.parentNode = null; } return c; };
N.prototype.cloneNode = function(deep){ var c = new N(this.tag, this.cls); c._t = this._t; var k;
  for(k in this.attrs){ c.attrs[k] = this.attrs[k]; }
  for(k in this.dataset){ c.dataset[k] = this.dataset[k]; }
  if(deep){ for(var i = 0; i < this.kids.length; i++){ c.appendChild(this.kids[i].cloneNode(true)); } } return c; };
N.prototype.querySelector = function(sel){
  if(sel === '.engbody'){ for(var i = 0; i < this.kids.length; i++){ if(String(this.kids[i].cls).indexOf('engbody') >= 0){ return this.kids[i]; } } }
  return null; };
N.prototype.querySelectorAll = function(sel){
  var out = [];
  (function walk(n){ for(var i = 0; i < n.kids.length; i++){ var k = n.kids[i];
    if(sel === 'details.eng' && k.tag === 'details' && String(k.cls).split(/\\s+/).indexOf('eng') >= 0){ out.push(k); }
    walk(k); } })(this);
  return out; };
var ELS = [];
var document = { querySelectorAll: function(sel){ return ELS; }, createElement: function(t){ return new N(t); } };
function mkLog(raw, n){ var el = new N('div', 'tool-log'); el.setAttribute('data-raw', raw); el.textContent = raw; el.dataset.n = n || '1'; return el; }
__LEDGER__
__TURNHUMAN__
"""


def _h3(receipt_js):
    src = _src()
    pre = (_PRE.replace("__LEDGER__", _ledger_re_line(src))
               .replace("__TURNHUMAN__", _fn(src, "paTurnHuman")))
    js = pre + u"var RECEIPT = " + receipt_js + u";\nvar rcOf = function(){ return RECEIPT; };\n" + _fn(src, "ledgerPass") + u"\n" + _H3.replace("__PRE__", "")
    return _node(js, "h3")


def test_H3_real_fn_screen_is_human_and_raw_goes_behind_fold():
    o = _h3(json.dumps({"human": DONE}, ensure_ascii=False))
    assert o["aScreen"] == DONE["一句"], u"屏上唯人话：" + str(o["aScreen"])
    assert o["aUser"] == DONE["一句"], o["aUser"]
    assert o["aEng"] is not None and u"本轮已落盘（" in o["aEng"], u"原字须入折（⛔ 丢信息）：" + str(o["aEng"])
    assert o["cText"] == u"🔍 共搜 540 件", u"非回执行 ⛔ 动：" + o["cText"]
    assert o["bScreen"] == u"✅ 本轮已存档", u"一回执唯用一行（⛔ 以旧回执之人话充新行）：" + o["bScreen"]
    assert u"本轮已落盘（" in o["aText"], u"原字 ⛔ 丢（须入折）：" + str(o["aText"])


def test_H4b_real_fn_no_human_keeps_legacy_line():
    o = _h3(json.dumps({"recorded": True}, ensure_ascii=False))
    assert o["aScreen"] == u"✅ 本轮已存档", o["aScreen"]
