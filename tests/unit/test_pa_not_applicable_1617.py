# -*- coding: utf-8 -*-
u"""pm_1617 §二.3 ＝ pm_1614 §二.1 之齿（CW b2a5182 · 2026-10-07）。

一事：`gate.decision = not_applicable`（库根未接 ∨ 检索面为空）⇒ **显后端之 canon** ∧ **⛔ 落模型**。
  病（净机 · 老板之屏一手）：该支 `refused=false ∧ grounded=false` ⇒ 直落 `sendPA` ⇒ `/v9/pa/dialog`
    ⇒ 屏上现「模型调用失败：本机与云端皆不可用（[WinError 2] …）」（＝ pm_1614 §〇 之的）。
  法：`send.js` 之闸支加 `not_applicable` 之一路（**一处定形**：字面唯取后端 `answer_canon` ⇒ `answer`
    ⇒ `verdict` · ⛔ 前端自造文）。

  取原文**真跑**（`send.js` 之闸区块 `let _askMeta = null;` → `await sendPA(...)`）：node 为器，
    `addMsg` ／ `paSetState` ／ `paAskGate` ／ `recordPaTurn` ／ `sendPA` ／ `window` 为桩
    （其 ＝ 本测之边界 · ⛔ 被审之逻辑）。`paLooksLikeKnowledgeQuestion` 由案给（⛔ 重测其判）。

  N1 正控（not_applicable）⇒ 显 canon 逐字 ∧ **⛔ sendPA**（⇒ ⛔ /v9/pa/dialog · ⛔ 落模型）
      ∧ 落盘之标 `answer_source='not_applicable'` ∧ **⛔ 冒** `origin`。
  N2 正控（not_applicable 而无 answer_canon —— 库根未接支）⇒ 显 `verdict` 逐字（⛔ 空 ∧ ⛔ 造辞）。
  N3 反控（grounded=true）⇒ sendPA **照旧**（`origin='grounded'`）。
  N4 反控（refused=true）⇒ sendPA **⛔**（既有拒答支 ⛔ 破）。
  N5 反控（非知识问）⇒ sendPA 照旧（`meta=null`）。
  N6 一处定形（结构）：字面 `'not_applicable'` 恰 2 处（判 1 ＋ 回落默认 1）∧ `answer_canon` 唯 1 处。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_not_applicable_1617.py -q
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SJ = ROOT / "web" / "pa" / "faces" / "send.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_notapp1617"

A = u"    let _askMeta = null;"
B = u"    if(cfg.chan==='pa') await sendPA(text, t, _askMeta);"

CANON_EMPTY = u"\u672c\u673a\u8fd8\u6ca1\u6709\u53ef\u68c0\u7d22\u7684\u8d44\u6599\uff08\u68c0\u7d22\u9762\u4e3a\u7a7a\uff09\u21d2 \u6211\u4e0d\u7b54\u6b64\u95ee\u3002"
VERDICT_UNSET = u"\u672a\u63a5\uff08\u9009\u76ee\u5f55\uff09\uff1a\u5e93\u6839 \u26d4 \u5f97 \u21d2 \u672c\u8f6e \u26d4 \u626b\u63cf\u21d2 \u62d2\u7b54\u4e0e\u5426\u7686\u4e0d\u6210\u7acb\uff08\u5f85\u9009\u76ee\u5f55\uff09"
REFUSAL_CANON = u"\u672c\u673a\u65e0\u636e \u21d2 \u6211\u4e0d\u7b54\u6b64\u95ee\u3002"


def _block() -> str:
    s = io.open(str(SJ), encoding="utf-8").read()
    i = s.find(A)
    assert i >= 0, u"未找到闸区块之头（%s）" % A
    j = s.find(B, i)
    assert j > 0, u"未找到闸区块之末（%s）" % B
    return s[i:j + len(B)]


HARNESS = u"""const REC = {msgs: [], calls: [], route: null};
let _g = null, _know = false;
function addMsg(k, t){ REC.msgs.push([k, String(t)]); }
function paSetState(k, note){ REC.calls.push(['state', k, String(note == null ? '' : note)]); }
function paLooksLikeKnowledgeQuestion(t){ return _know; }
async function paAskGate(t){ return _g; }
const PA_REFUSE_CANON = __REFUSAL_CANON__;
function paRefusalCanon(g){ const v = (g && typeof g.refusal_canon === 'string') ? g.refusal_canon : ''; return v || PA_REFUSE_CANON; }
function paRefusalStale(t){ const s = String(t == null ? '' : t).trim(); if(!s) return false;
  return (s.indexOf('\u67e5\u4e0d\u5230') === 0) || /\u77e5\u8bc6\u5e93\u91cc\u6ca1\u6709\u76f8\u5173\u5185\u5bb9/.test(s) || /\u5e93\u91cc\u65e0\u4f9d\u636e/.test(s); }
async function recordPaTurn(sid, u, a, meta){ REC.calls.push(['turn', meta]);
  return {recorded: true, session_lines_before: 1, session_lines_after: 2, events_lines_before: 1, events_lines_after: 2}; }
async function sendPA(text, t, meta){ REC.calls.push(['sendPA', meta]); }
async function startPlan(){ REC.calls.push(['startPlan', null]); }
async function sendAgent(){ REC.calls.push(['sendAgent', null]); }
const paRun = {receipt: null, evidence: null};
globalThis.window = globalThis;
window.PASelfRouteLast = null;

async function _run(text, t, cfg){
__BLOCK__
}

const CASES = [
 ['not_app', {know:true, g:{ok:true, gate:{decision:'not_applicable'},
     answer_canon:__CANON__, answer_source:'not_applicable',
     verdict:'\u4e0d\u9002\u7528\uff08\u641c\u7d22\u9762\u4e3a\u7a7a\uff1a\u77e5\u8bc6\u5e93\u76ee\u5f55\u4e0d\u53ef\u8fbe \u21d2 \u62d2\u7b54\u4e0e\u5426\u90fd\u4e0d\u6210\u7acb\uff09',
     searched:0, scope:['\u6536\u4ef6\u7bb1', '\u77e5\u8bc6\u5e93'], read_at:'2026-10-07 12:00:00', threshold:0.42}}],
 ['not_app_nocanon', {know:true, g:{ok:true, gate:{decision:'not_applicable'},
     answer:'', answer_source:'not_applicable', verdict:__VERDICT__, searched:0,
     scope:['\u6536\u4ef6\u7bb1'], read_at:'2026-10-07 12:00:01', threshold:null}}],
 ['grounded', {know:true, g:{ok:true, grounded:true, answer_source:'knowledge', gate:{decision:'grounded'}}}],
 ['refused', {know:true, g:{ok:true, refused:true, answer_source:'refused', refusal_canon:__REFUSAL_CANON__,
     verdict:'\u62d2\u7b54\uff08\u5e93\u91cc\u65e0\u4f9d\u636e\uff09', searched:540,
     scope:['\u6536\u4ef6\u7bb1'], read_at:'2026-10-07 12:00:02', threshold:0.42}}],
 ['ungated', {know:false, g:null}]
];

(async function(){
  const out = {};
  for (const c of CASES) {
    for (const k of Object.keys(REC)) { REC[k] = (k === 'route') ? null : []; }
    window.PASelfRouteLast = null;
    _g = c[1].g; _know = c[1].know;
    await _run('\u53f0\u8d26\u91cc\u6709\u54ea\u4e9b\u9879\u76ee\uff1f', {id: 'T1'}, {chan: 'pa'});
    out[c[0]] = {msgs: REC.msgs, calls: REC.calls, route: window.PASelfRouteLast};
  }
  console.log(JSON.stringify(out));
})();
"""


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _v() -> dict:
    js = (HARNESS
          .replace("__BLOCK__", _block())
          .replace("__CANON__", json.dumps(CANON_EMPTY, ensure_ascii=False))
          .replace("__VERDICT__", json.dumps(VERDICT_UNSET, ensure_ascii=False))
          .replace("__REFUSAL_CANON__", json.dumps(REFUSAL_CANON, ensure_ascii=False)))
    return _node(js, "notapp1617")


def _call(v, name):
    return [c for c in v["calls"] if c[0] == name]


# ---------- N1 ／ N2：正控（令三之的） ----------

def test_N1_正控_不适用须显canon且不落模型():
    v = _v()["not_app"]
    msgs = [m[1] for m in v["msgs"]]
    assert any(CANON_EMPTY in m for m in msgs), msgs
    assert _call(v, "sendPA") == [], u"not_applicable ⇒ ⛔ 得落模型（sendPA）"
    assert _call(v, "startPlan") == [] and _call(v, "sendAgent") == [], v["calls"]
    tn = _call(v, "turn")
    assert len(tn) == 1, v["calls"]
    meta = tn[0][1] or {}
    assert meta.get("answer_source") == "not_applicable", meta
    assert "origin" not in meta, u"`origin` 之封闭集无「不适用」⇒ ⛔ 冒（照实「未标」）: %s" % meta
    assert meta.get("grounded") is False, meta
    assert (v["route"] or {}).get("label", {}).get("kind") == "self", v["route"]
    assert (v["route"] or {}).get("label", {}).get("key") == u"\u4e0d\u9002\u7528", v["route"]


def test_N2_正控_无canon支须显后端之判词逐字():
    v = _v()["not_app_nocanon"]
    msgs = [m[1] for m in v["msgs"]]
    joined = u"\n".join(msgs)
    assert VERDICT_UNSET in joined, joined
    assert _call(v, "sendPA") == [], u"无 canon 亦 ⛔ 得落模型"


# ---------- N3 ～ N5：反控（既有三路 ⛔ 破） ----------

def test_N3_反控_有据支照旧落模型():
    v = _v()["grounded"]
    sp = _call(v, "sendPA")
    assert len(sp) == 1, v["calls"]
    assert (sp[0][1] or {}).get("origin") == "grounded", sp


def test_N4_反控_拒答支仍不落模型():
    v = _v()["refused"]
    assert _call(v, "sendPA") == [], v["calls"]
    assert any(REFUSAL_CANON in m[1] for m in v["msgs"]), v["msgs"]


def test_N5_反控_非知识问照旧且meta为空():
    v = _v()["ungated"]
    sp = _call(v, "sendPA")
    assert len(sp) == 1, v["calls"]
    assert sp[0][1] is None, sp


# ---------- N6：一处定形（结构） ----------

def test_N6_一处定形_字面唯取后端():
    s = io.open(str(SJ), encoding="utf-8").read()
    assert s.count(u"'not_applicable'") == 2, u"判 1 ＋ 回落默认 1（⛔ 三处各写）"
    assert s.count(u"=== 'not_applicable'") == 1, u"判之点须一处"
    assert s.count(u"g.answer_canon") == 1, u"canon 之取须一处（⛔ 二源）"
    assert s.count(u"g.gate.decision") == 1, u"闸之判须唯取后端 `g.gate.decision`（代码面一处）"
