# -*- coding: utf-8 -*-
u"""pm_1548 \u00a7\u4e00.3 \u88c1 \u24dc \u4e4b\u9f7f\uff08CW b2a5182 \u00b7 2026-10-06\uff09\u3002

\u4e00\u4e8b\uff1a\u201c\u5408\u5e76\u8ba1\u6570\u201d\u4e4b\u6807 \u201c\u672c\u8f6e\u201d \u21d2 \u201c\u672c\u9875\u201d
\uff08\u5176\u6570\u5b9e\u4e3a\u300c\u672c\u9875\u4e4b\u5185\u540c\u5b57\u4e4b\u884c\u6570\u300d\u00b7\u8df3\u8f6e\u6301\u4e45 \u00b7 products.js:346-370 \u4e4b\u952e \uff1d \u884c\u6587\u672c\u5168\u4e32\uff09\u3002
  L1 \u6b63\u63a7\uff08\u5b57\u9762\uff09\uff1a\u201c\u5408\u5e76\u8ba1\u6570 \u672c\u9875 \u00d7\u201d \u8ba1 4 \u5904\uff08:828 :999 :2367 + \u6ce8\u91ca :2384\uff09\uff1b
     \u201c\uff08\u5408\u5e76\u8ba1\u6570\uff1a\u672c\u9875 \u00d7\u201d \u8ba1 2 \u5904\uff08:829 :1003\uff09\u3002
  L2 \u53cd\u63a7\uff08\u65e7\u5b57\u7edd\u8ff9\uff09\uff1a\u65e7\u6807\uff08\u672c\u8f6e\uff09\u4e24\u5f62\u5404 == 0\u3002
  L3 \u6b63\u63a7\uff08\u771f\u8dd1 paSelfMulPass \u00b7 node\uff09\uff1a\u540c\u4e00\u884c \u00d73 \u21d2 title \u4e3a
     \u201c\u5408\u5e76\u8ba1\u6570 \u672c\u9875 \u00d73\u201d\uff0c\u4e14\u6ce8\u8bb0\u4e3a \u201c\uff08\u5408\u5e76\u8ba1\u6570\uff1a\u672c\u9875 \u00d73\uff09\u201d\uff08\u2117 \u672c\u8f6e\uff09\u3002

\u4ee5\u4f55\u5f62\u8c03\u7528\uff1apython -X utf8 -B -m pytest tests/unit/test_pa_mul_label_1548.py -q
"""
from __future__ import annotations

import io, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_mul_label1548"

A_OLD = u"\u5408\u5e76\u8ba1\u6570 \u672c\u8f6e \u00d7"
B_OLD = u"\uff08\u5408\u5e76\u8ba1\u6570\uff1a\u672c\u8f6e \u00d7"
A_NEW = u"\u5408\u5e76\u8ba1\u6570 \u672c\u9875 \u00d7"
B_NEW = u"\uff08\u5408\u5e76\u8ba1\u6570\uff1a\u672c\u9875 \u00d7"


def _src() -> str:
    return io.open(str(SDESC), encoding="utf-8").read()


def _fn(src: str, name: str) -> str:
    i = src.find("function " + name + "(")
    assert i > 0, "\u672a\u627e\u5230\u51fd\u6570 " + name
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
    raise AssertionError("\u51fd\u6570 " + name + " \u82b1\u62ec\u53f7\u4e0d\u914d\u5e73")


def _mul_re_line(src: str) -> str:
    for ln in src.split("\n"):
        if ln.startswith("const PA_MUL_RE"):
            return ln.strip()
    raise AssertionError("\u672a\u627e\u5230 PA_MUL_RE")


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node \u5931\u8d25 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


# ============================ L1 ／ L2 \u5b57\u9762 ============================

def test_L1_label_is_benye():
    s = _src()
    assert s.count(A_NEW) == 4, s.count(A_NEW)
    assert s.count(B_NEW) == 2, s.count(B_NEW)


def test_L2_old_label_gone():
    s = _src()
    assert s.count(A_OLD) == 0, u"\u65e7\u6807\uff08\u672c\u8f6e\uff09\u4ecd\u5728 \u00b7 \u8df3\u8f6e\u4e4b\u6570\u4e0d\u5f97\u4e66\u672c\u8f6e"
    assert s.count(B_OLD) == 0, u"\u65e7\u6807\uff08\u672c\u8f6e\uff09\u4ecd\u5728 \u00b7 \u6ce8\u8bb0\u4e4b\u5f62"


# ============================ L3 \u771f\u8dd1 ============================

RUN_JS = u"""__MULRE__
__HIT__
__CLEAN__
__HUMAN__
var CAP = { note: null };
function paEngNoteEl(raw){ CAP.note = String(raw); return { tag: 'note' }; }
function paEngHit(){ return false; }
const PA_ENG_ERR = /$^/;
const PA_ENG_WORDS = /$^/;
__PASS__
var el = {
  textContent: 'TEST-LINE   \u00d73', title: '', dataset: {},
  querySelector: function(){ return null; },
  setAttribute: function(k, v){ this.dataset[String(k).replace(/^data-/, '')] = v; },
  appendChild: function(c){ this.kids = (this.kids || []); this.kids.push(c); }
};
var document = {
  getElementById: function(){ return { querySelectorAll: function(){ return [el]; } }; },
  createElement: function(){ return { style: {}, querySelector: function(){ return {}; }, appendChild: function(){}, setAttribute: function(){} }; }
};
var n = paSelfMulPass();
console.log(JSON.stringify({ n: n, title: el.title, note: CAP.note, dn: el.dataset.n, text: el.textContent }));
"""


def test_L3_real_run_label_is_benye():
    s = _src()
    js = (RUN_JS.replace("__MULRE__", _mul_re_line(s))
                .replace("__HIT__", _fn(s, "paSelfMulHit"))
                .replace("__CLEAN__", _fn(s, "paSelfMulClean"))
                .replace("__HUMAN__", _fn(s, "paLogHuman"))
                .replace("__PASS__", _fn(s, "paSelfMulPass")))
    out = _node(js, "mul")
    assert out["n"] == 1 and out["dn"] == "3", out
    assert out["title"] == u"\u5408\u5e76\u8ba1\u6570 \u672c\u9875 \u00d73", out["title"]
    assert out["note"] == u"TEST-LINE\n\uff08\u5408\u5e76\u8ba1\u6570\uff1a\u672c\u9875 \u00d73\uff09", repr(out["note"])
    assert u"\u672c\u8f6e" not in out["title"] and u"\u672c\u8f6e" not in out["note"], out
    assert out["text"] == u"TEST-LINE", out["text"]