# -*- coding: utf-8 -*-
u"""pm_1551 \u00a7\u4e8c.3 \u4e4b\u9f7f\uff08CW b2a5182 \u00b7 2026-10-06\uff09\u3002

\u4e00\u4e8b\uff1a`lastLogs()`\uff08selfdesc.js:3298-3313\uff09\u6539\u53d6\u300c\u7528\u6237\u9762\u4e4b\u5b57\u300d
\uff08clone \u21d2 \u53bb `details.eng` \u21d2 \u53d6 textContent\uff09\u2014\u2014 \u65e7\u6cd5\u53d6\u88f8 `textContent` \u542b\u6298\u53e0\u4e4b\u5de5\u7a0b\u6ce8\u8bb0
\u21d2 \u7ecf `rcLines()` \u4e4b\u300c\u00b7 \u505a\u4e86\u4ec0\u4e48\uff1a\u300d\u5165 `#paHumanReceipt`\uff08\u771f\u4e0a\u5c4f\uff09\u3002
  L1 \u6b63\u63a7\uff1a\u542b `details.eng` \u4e4b\u884c \u21d2 \u53d6\u6587 \u2117 \u542b\u300c\u5de5\u7a0b\u6ce8\u8bb0\u300d \u2117 \u542b\u300c\uff08\u771f\u6e90\uff1a\u300d \u4e14 \u4ecd\u5408 `rcLines` \u4e4b pickLog \u5b57\u7b26\u7c7b\uff08\u9996\u5b57 \u2117 \u7834\uff09\u3002
  L2 \u53cd\u63a7\uff1a\u65e7\u6cd5\uff08\u88f8 textContent\uff09\u21d2 \u5fc5\u542b\u300c\u5de5\u7a0b\u6ce8\u8bb0\u300d\uff08\u8bc1\u75c5\u5728\uff09\u3002
  L3 \u4fdd\u771f\u63a7\uff1a\u65e0 `details.eng` \u4e4b\u884c \u21d2 \u53d6\u6587\u4e0e textContent \u9010\u5b57\u540c\u3002
  L4 \u7a7a\u5b88\uff1a\u60df\u6ce8\u8bb0\u8282 \u21d2 \u56de\u9000 \u00b7 \u2117 \u7a7a\uff1b\u5e76 \u5b88\u56db\uff08\u672c\u4f53 `#thread` \u4e4b `details.eng` \u4ecd\u5728\uff09\u3002

\u4ee5\u4f55\u5f62\u8c03\u7528\uff1apython -X utf8 -B -m pytest tests/unit/test_pa_ledger_face_1551.py -q
"""
from __future__ import annotations

import io, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_ledger_face1551"

ENG = u"\u5de5\u7a0b\u6ce8\u8bb0"
SRC = u"\uff08\u771f\u6e90\uff1a"
FACE = u"\u2705 \u672c\u8f6e\u5df2\u5b58\u6863"


def _src() -> str:
    return io.open(str(SDESC), encoding="utf-8").read()


def _fn(src: str, name: str) -> str:
    i = src.find("function " + name + "(")
    assert i > 0, u"\u672a\u627e\u5230\u51fd\u6570 " + name
    d, opened, e = 0, False, i
    while e < len(src):
        c = src[e]
        if c == "{":
            d += 1; opened = True
        elif c == "}":
            d -= 1
            if opened and d == 0:
                return src[i:e + 1]
        e += 1
    raise AssertionError(u"\u51fd\u6570 " + name + u" \u82b1\u62ec\u53f7\u4e0d\u914d\u5e73")


def _pick_re(src: str) -> str:
    u"""\u53d6 rcLines \u5185 pickLog \u4e4b\u5b57\u7b26\u7c7b\u6b63\u5219\u5b57\u9762\uff08\u4e00\u5904\u5f15\u7528 \u00b7 \u2117 \u53e6\u5b9a\uff09\u3002"""
    for ln in src.split("\n"):
        i = ln.find("var log = pickLog(")
        if i >= 0:
            j = ln.find("/", i)
            k = ln.find("/", j + 1)
            assert j > 0 and k > j, ln
            return ln[j:k + 1]
    raise AssertionError(u"\u672a\u627e\u5230 pickLog \u4e4b\u5b57\u7b26\u7c7b")


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node \u5931\u8d25 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


HARNESS = u"""__LASTLOGS__

function N(tag, cls){ this.tag = tag || 'div'; this.cls = cls || ''; this.kids = []; this._t = null; this.parentNode = null; }
Object.defineProperty(N.prototype, 'textContent', {
  get: function(){ if(this.kids.length){ var s = ''; for(var i = 0; i < this.kids.length; i++){ s += this.kids[i].textContent; } return s; } return this._t == null ? '' : this._t; },
  set: function(v){ this._t = String(v); this.kids = []; }
});
N.prototype.appendChild = function(c){ c.parentNode = this; this.kids.push(c); return c; };
N.prototype.removeChild = function(c){ var i = this.kids.indexOf(c); if(i >= 0){ this.kids.splice(i, 1); c.parentNode = null; } return c; };
N.prototype.cloneNode = function(deep){ var c = new N(this.tag, this.cls); c._t = this._t;
  if(deep){ for(var i = 0; i < this.kids.length; i++){ c.appendChild(this.kids[i].cloneNode(true)); } } return c; };
N.prototype.querySelectorAll = function(sel){
  var out = [];
  (function walk(nd){ for(var i = 0; i < nd.kids.length; i++){ var k = nd.kids[i];
      if(sel === 'details.eng' && k.tag === 'details' && String(k.cls).split(/\\s+/).indexOf('eng') >= 0){ out.push(k); }
      walk(k); } })(this);
  return out;
};
function T(x){ var n = new N('#text'); n._t = String(x); return n; }
function mkLog(face, note){
  var el = new N('div', 'tool-log');
  if(face != null){ el.appendChild(T(face)); }
  if(note != null){
    var d = new N('details', 'eng');
    var s = new N('summary'); s._t = '\\u5de5\\u7a0b\\u6ce8\\u8bb0';
    var b = new N('div', 'engbody'); b._t = note;
    d.appendChild(s); d.appendChild(b);
    el.appendChild(d);
  }
  return el;
}
var ELS = [];
var document = { querySelectorAll: function(sel){ return ELS; } };
var PICK = __PICK__;
var FACE = '\\u2705 \\u672c\\u8f6e\\u5df2\\u5b58\\u6863';
var NOTE = '\\ud83d\\udcbe \\u672c\\u8f6e\\u5df2\\u843d\\u76d8\\uff08\\u540e\\u7aef\\u56de\\u6267 \\u00b7 \\u65e2\\u6709\\u51fa\\u53e3 POST /v9/pa/turn\\uff09\\n\\uff08\\u771f\\u6e90\\uff1a\\u540e\\u7aef POST /v9/pa/turn \\u56de\\u6267 \\u00b7 \\u26d4 \\u7528\\u6237\\u9762\\uff09';
var A = mkLog(FACE, NOTE);
var B = mkLog('\\ud83d\\udd0d \\u5171\\u641c 540 \\u4ef6', null);
var C = mkLog(null, NOTE);
ELS = [A, B, C];
var O = {};
O.pos = lastLogs(12)[0];
O.plain = lastLogs(12)[1];
O.engOnly = lastLogs(12)[2];
O.plainRaw = String(B.textContent || '').replace(/\\s+/g, ' ').trim();
O.engOnlyRaw = String(C.textContent || '').replace(/\\s+/g, ' ').trim();
O.rawHasEng = String(A.textContent || '').replace(/\\s+/g, ' ').trim().indexOf('\\u5de5\\u7a0b\\u6ce8\\u8bb0') >= 0;
O.posHasEng = O.pos.indexOf('\\u5de5\\u7a0b\\u6ce8\\u8bb0') >= 0;
O.posHasSrc = O.pos.indexOf('\\uff08\\u771f\\u6e90\\uff1a') >= 0;
O.posPick = PICK.test(O.pos);
O.bodyKept = A.querySelectorAll('details.eng').length;
console.log(JSON.stringify(O));
"""


def _run() -> dict:
    s = _src()
    js = (HARNESS.replace("__LASTLOGS__", _fn(s, "lastLogs"))
                 .replace("__PICK__", _pick_re(s)))
    return _node(js, "face")


def test_L1_pos_userface_excludes_engnote():
    o = _run()
    assert o["pos"] == FACE, repr(o["pos"])
    assert o["posHasEng"] is False, o
    assert o["posHasSrc"] is False, o
    assert o["posPick"] is True, o
    assert o["bodyKept"] == 1, o          # 守四：本体之 `details.eng` 仍在（留痕 ⛔ 丢）


def test_L2_neg_old_textcontent_leaks():
    o = _run()
    assert o["rawHasEng"] is True, o      # 旧法取 textContent ⇒ 必含「工程注记」＝ 证病在


def test_L3_keep_plain_line_verbatim():
    o = _run()
    assert o["plain"] == o["plainRaw"], (o["plain"], o["plainRaw"])


def test_L4_empty_guard_falls_back():
    o = _run()
    assert o["engOnly"] != "", o
    assert o["engOnly"] == o["engOnlyRaw"], (o["engOnly"], o["engOnlyRaw"])