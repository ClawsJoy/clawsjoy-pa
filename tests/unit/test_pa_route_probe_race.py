# -*- coding: utf-8 -*-
u"""P0（pm_1467 §一.3 · 式⒈ 探针前置）· 走径探针之竞态 ⇒「出机」标之失真（CW b2a5182 · 2026-10-06）。

病（TD 1466 §三 · 真浏览器 ／ CDP 之器取）：
  `web/pa/faces/more.js` 之回执探针**返原始 `p`** ⇒ 探针之 `resp.clone().json()` 微任务排在
  调用方 `await r.json()` 续段**之后** ⇒ `addMsg` 先跑 ⇒ `paRouteTake()` 取 `null`：
    · 甲（假阴）真云端轮（回执 `kind:"remote"` 已给）⇒ **⛔ 上「出机」标**（红线之隐）；
    · 乙（假阳）甲之标签**残留至下一轮** ⇒ 本机轮之 `addMsg` 取甲之 remote 标 ⇒ **本机答挂「出机」标**
      （**红线反向说谎** · 更险）。
修（式⒈ 探针前置）：返回之 promise **须待 label 置毕方 resolve** ⇒ 调用方之 `await` 续段 ⛔ 得先于
  label 之置 ⇒ 甲除 ∧ 乙（残留之源）随之除。一处（探针 IIFE）· ⛔ 散补 ／ ⛔ 救火。

判据（逐条 · 与齿共用同一条断言，⛔ 写两份）：
  J1 甲 正控：云端轮 ⇒ `await fetch` 归来之刻 `PASelfRouteLast.label.kind === 'remote'`（**前置之专证**）
             ∧ 屏上有「出机」标 ＋ 实名
  J2 反控：本机轮 ⇒ 标 ⛔ 上（实证其无）∧ 走径标仍须在
  J3 乙 三控：**连打二轮（云端 ⇒ 本机）** ⇒ 本机轮 ⛔ 得甲所留之标（**残留 ⛔ 许**）—— 乙之专证
  J4 齿：把前置挖掉（返 `resp` 而不待 `probe`）⇒ J1 ／ J3 **必红**（⛔ 挖了还能过）
  J5 静态：修须**一处**（探针 IIFE）· 非命中 URL 之直通 ⛔ 失

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_route_probe_race.py -q

本件**不复制代码**：走径段（含探针 ＋ `addMsg` 包装）自 `more.js` 抽原文以 `node` 真跑；
`tests/unit/test_pa_leaves_mark.py` 之 `_prelude` ／ `_slice` 复用（**同一器** · ⛔ 二份）。
唯 `window.fetch`（桩 orig）＋ `window.addMsg`（沉）为桩 —— 其 ＝ 本测之边界。
⚠ 桩之**时序**照 TD 之器取：`json()` 微任务即可（调用方之读 · 快）⟷ `clone().json()` 落宏任务
  （`setTimeout 5ms` · 探针之读 · 慢）—— 此即「探针后置」之实形（⛔ 我造之序 · 承器取之实）。
"""
from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MORE = ROOT / "web" / "pa" / "faces" / "more.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_race1467"

LEAVES = u"本轮经云端 · 内容将出机 · 模型 "
ROUTE = u"🔌 走径："
#: 前置之原文（修之实 · 齿之锚）
FIX = u"return probe.then(function(){ return resp; });"

_LEAVES_PY = Path(__file__).with_name("test_pa_leaves_mark.py")
_spec = importlib.util.spec_from_file_location("_cw_leaves_hlp", str(_LEAVES_PY))
_hlp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_hlp)


def _pa() -> str:
    return io.open(str(MORE), encoding="utf-8").read()


def _slice() -> str:
    return _hlp._slice()


REMOTE = {"answer_route": {"kind": "remote", "provider": "deepseek", "model": "deepseek-flash"},
          "reply": "云端之答"}
LOCAL = {"answer_route": {"kind": "local", "model": "qwen2.5"}, "reply": "本机之答"}
URL = "/v9/pa/dialog"


def _run(cases: list, slice_body: str = None) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    js = (_hlp._prelude()
          + u"const window = {};\nlet MSGS = [], SEEN = [], Q = [];\n"
          + u"function mkResp(body){ return {status: 200, ok: true,"
            u" json: function(){ return Promise.resolve(body); },"
            u" clone: function(){ return {status: 200, json: function(){"
            u" return new Promise(function(res){ setTimeout(function(){ res(body); }, 5); }); }}; }}; }\n"
          + u"window.fetch = function(u, o){ const B = (Q.length ? Q.shift() : {});"
            u" return Promise.resolve(mkResp(B)); };\n"
          + u"window.addMsg = function(role, content, skipStore, html, tid){"
            u" if(role === 'assistant') MSGS.push({content: content, html: html}); };\n"
          + (slice_body if slice_body is not None else _slice()) + "\n"
          + u"async function round(u, body){ Q.push(body);"
            u" const r = await window.fetch(u, {method: 'POST'});"
            u" const s = window.PASelfRouteLast; SEEN.push(s && s.label ? s.label.kind : null);"
            u" const d = await r.json();"
            u" window.addMsg('assistant', (d && d.reply) || 'BODY', false, '<p>BODY</p>', 't1'); await new Promise(function(res){ setTimeout(res, 20); }); }\n"
          + u"const CASES = " + json.dumps(cases, ensure_ascii=False) + ";\n"
          + u"(async function(){ const OUT = {runs: []};"
            u" for(const c of CASES){ MSGS = []; SEEN = [];"
            u"   for(const st of c.steps){ await round(st.url, st.body); }"
            u"   OUT.runs.push({name: c.name, seen: SEEN, msgs: MSGS}); }"
            u" console.log(JSON.stringify(OUT)); })();\n")
    f = SCRATCH / "race_harness.js"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\\Program Files\\nodejs\\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _cloud_then_local():
    return [{"name": "cloud_then_local",
             "steps": [{"url": URL, "body": REMOTE}, {"url": URL, "body": LOCAL}]}]


# ============================ J1 甲 正控 ============================

def test_J1_甲_正控_探针须前置_label已置方归():
    out = _run([{"name": "cloud", "steps": [{"url": URL, "body": REMOTE}]}])
    run = out["runs"][0]
    assert run["seen"] == ["remote"], \
        u"甲：`await fetch` 归来之刻 label 未置（探针后置）⇒ %r" % (run["seen"],)
    m = run["msgs"][0]
    assert LEAVES + "deepseek-flash" in m["content"], m["content"]
    assert ROUTE in m["content"], m["content"]


# ============================ J2 反控 ============================

def test_J2_反控_本机轮必无出机标():
    out = _run([{"name": "local", "steps": [{"url": URL, "body": LOCAL}]}])
    run = out["runs"][0]
    assert run["seen"] == ["local"], run["seen"]
    m = run["msgs"][0]
    assert "出机" not in m["content"], u"本机之轮竟有出机标：%r" % m["content"]
    assert ROUTE in m["content"], u"走径标被一并吞了（假红）"


# ============================ J3 乙 三控 ============================

def test_J3_乙_三控_云端后本机_残留须除():
    out = _run(_cloud_then_local())
    run = out["runs"][0]
    assert run["seen"] == ["remote", "local"], run["seen"]
    assert "出机" in run["msgs"][0]["content"], run["msgs"][0]["content"]
    m2 = run["msgs"][1]
    assert "出机" not in m2["content"], \
        u"乙：本机轮取了甲所留之 remote 标（红线反向说谎）：%r" % m2["content"]
    assert ROUTE in m2["content"], m2["content"]


# ============================ J4 齿 ============================

def test_J4_齿_去前置则甲乙俱现():
    src = _slice()
    assert FIX in src, u"前置之原文已漂 ⇒ 本条齿须重钉"
    mutant = src.replace(FIX, u"return resp;")
    assert mutant != src, u"改不动 ⇒ 这条齿是假的"
    out = _run(_cloud_then_local(), slice_body=mutant)
    run = out["runs"][0]
    assert run["seen"][0] is None, \
        u"齿失效：挖掉前置，`await fetch` 归来之刻竟已有 label ⇒ %r" % (run["seen"],)
    assert run["seen"][1] == "remote", \
        u"齿失效：round2 竟未见甲之残留（乙未现）：%r" % (run["seen"],)
    assert "出机" in run["msgs"][1]["content"], \
        u"齿失效：挖掉前置，本机轮竟 ⛔ 无甲所留之标（乙未现）"


# ============================ J5 静态 ============================

def test_J5_静态_修须一处且直通不失():
    src = _pa()
    assert src.count(u"window.fetch = function") == 1, u"探针须**一处**定形（⛔ 二份）"
    assert FIX in src, u"前置之实须在（%s）" % FIX
    assert u"if(!/\\/v9\\/pa\\/(dialog|turn|ask)(\\?|$)/.test(url)) return p;" in src, \
        u"非命中 URL 之直通 ⛔ 失（原行为）"
    assert u"resp.clone().json()" in src, u"探针仍须以 clone 读（⛔ 改答体）"