# -*- coding: utf-8 -*-
u"""P2 ⑥ · 「出机」之显形（承 pm_1454 §一 ／ §二 ／ §三 · CW b2a5182 · 2026-10-06）。

病（承 P2 ① 之戒）：屏上之「走径标」唯言走哪一源 ⇒ **云端之轮 ⛔ 显「内容出机」**
⇒ 老板/用户**不知内容已出机**（红线之隐）。

判据（逐条 · 与齿共用同一条断言，⛔ 写两份）：
  J1 正控：`kind ∈ 远端集` ⇒ **折叠内**有「本轮经云端 · 内容将出机 · 模型 <实名>」；⭐ 实名**取回执**
          （换回执之名 ⇒ 屏上之名随换 ⇒ 实证 ⛔ 前端硬编）
  J2 反控：`kind = local ／ local_model ／ 本机 ／ 无 kind ／ 无回执` ⇒ **⛔ 有**（实证其无）；
          ⚠ 走径标**仍须在**（⛔ 连走径一并吞 ＝ 假红）
  J3 三控：回执**无 `model`** ⇒ 「（后端未给）」之明标（⛔ 空 ／ ⛔ 崩 · 承 `paRouteLine` 之式）
  J4 位：出机之标**先于**「🔌 走径」行（折叠体内 · 红线先入目 · 承 §一.2）∧ ⭐ **用户面（纯文）二标皆无**

⭐ pm_1812 §二.1 ／ pm_1822 §二.4⒟（去壳 · 要）：二标**皆入折叠**（`<details class="eng paroute">`）——
  用户面（纯文 `content`）**⛔ 载**此二标（工程话 ⛔ 入目）；其**原文照录**在折叠体内（⛔ 删真源）。
  ⇒ 故本条各判之**耳**：位判取 `html`（折叠体）＋ 并断**用户面净化**（`content` 无此二标）。
  J5 齿：把「唯远端」之守挖掉 ⇒ J2 **必红**（⛔ 挖了还能过）
  J6 静态：出机之器**⛔ 含具体模型名**（硬编之戒）；kind 之二集**一处定形**（⛔ 二份字面）
  J7 不回归：`paRouteFromObj` 之渲形与**底件**（`more.js.before_e653b6e030aa9ce3`）之实读**逐字相等**

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_leaves_mark.py -q

本件**不复制代码**：`more.js` 之走径段整段抽出（锚点定界）＋ `tasks.js` 之 `paEsc` ＋
`core.js` 之 `fmtStamp` ／ `EPOCH_SEC_RE` 皆**抽原文**，以 `node` 真跑；
唯 `window`（含 `addMsg` 之**沉**）为桩 —— 其 ＝ 本测之边界（下游渲染器），⛔ 非被审对象。
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MORE = ROOT / "web" / "pa" / "faces" / "more.js"
CORE = ROOT / "web" / "pa" / "core.js"
TASKS = ROOT / "web" / "pa" / "faces" / "tasks.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_leaves1454"

LEAVES = u"本轮经云端 · 内容将出机 · 模型 "
ROUTE = u"🔌 走径："
UNDEF = u"（后端未给）"

#: 走径段之锚（抽出之界 · ⛔ 行号 —— 行号会漂）
ANCHOR_A = u"/* ⭐「本机 / 远端」之二集"
ANCHOR_B = u"function paProvMount(){"


def _fn(src: str, name: str) -> str:
    u"""按花括号配平抽出 `function name(...){...}` 原文（⛔ 复制）。"""
    i = src.find("function " + name + "(")
    assert i > 0, "未找到函数 " + name
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
    raise AssertionError("函数 " + name + " 花括号不配平")


def _pa() -> str:
    return io.open(str(MORE), encoding="utf-8").read()


def _slice() -> str:
    u"""走径段（锚点定界 · ⛔ 行号）。"""
    s = _pa()
    a, b = s.index(ANCHOR_A), s.index(ANCHOR_B)
    return s[a:b]


def _prelude() -> str:
    u"""真源之四件（`EPOCH_SEC_RE` ／ `fmtStamp` ／ `paEsc` ／ `PA_STAMP` 之形）—— 逐字抽出，⛔ 复制。

    ⚠ `PA_STAMP` 之**形**照 `core.js:128` 逐字（`{ fmt: fmtStamp, secRe: EPOCH_SEC_RE }`）；
    本测之 `window` 为**桩对象**（⛔ 真窗）⇒ 该行以 `const` 声明（⛔ `window.PA_STAMP = …`，
    否则绑定 ⛔ 入 more.js 之作用域）。此为**适配**，⛔ 复制被审之逻辑。
    """
    core = io.open(str(CORE), encoding="utf-8").read()
    tasks = io.open(str(TASKS), encoding="utf-8").read()
    m = re.search(r"var EPOCH_SEC_RE = .*?;", core)
    assert m, "EPOCH_SEC_RE 未找到"
    assert u"window.PA_STAMP = { fmt: fmtStamp, secRe: EPOCH_SEC_RE };" in core, \
        u"core.js 之 PA_STAMP 已漂 ⇒ 本测之适配须重钉"
    return (m.group(0) + "\n" + _fn(core, "fmtStamp") + "\n"
            + u"const PA_STAMP = { fmt: fmtStamp, secRe: EPOCH_SEC_RE };\n"
            + _fn(tasks, "paEsc") + "\n")


#: `paRouteFromObj` 之回归矩阵（底件 ↔ 今件 同喂）
FROMOBJ = {
    "remote_obj": {"kind": "remote", "provider": "deepseek", "model": "deepseek-flash"},
    "local_obj": {"kind": "local", "model": "qwen2.5"},
    "alias_api": {"kind": "api", "provider": "openai", "model": "gpt-4o-mini"},
    "alias_yuanduan": {"kind": u"远端", "provider": "p", "model": "m"},
    "alias_local_model": {"kind": "local_model", "model": "m"},
    "alias_benji": {"kind": u"本机", "model": "m"},
    "no_kind": {"provider": "p", "model": "m"},
    "model_only": {"model": "m"},
    "prov_only": {"kind": "remote", "provider": "p"},
    "empty": {},
    "notobj": None,
    "type_key": {"type": "remote", "model": "m"},
    "route_key": {"route": "local", "model": "m"},
}

#: ⭐ 底件（`more.js.before_e653b6e030aa9ce3`）之**实读**（器取 · 2026-10-06）—— 钉住渲形
FROMOBJ_EXPECT = {
    "remote_obj": u"src: remote:deepseek:deepseek-flash",
    "local_obj": u"src: local:qwen2.5",
    "alias_api": u"src: remote:openai:gpt-4o-mini",
    "alias_yuanduan": u"src: remote:p:m",
    "alias_local_model": u"src: local:m",
    "alias_benji": u"src: local:m",
    "no_kind": u"src: p:m（kind 未给）",
    "model_only": u"src: m（kind 未给）",
    "prov_only": u"src: remote:p:—",
    "empty": u"",
    "notobj": u"",
    "type_key": u"src: remote:—:m",
    "route_key": u"src: local:m",
}

REMOTE = {"answer_route": {"kind": "remote", "provider": "deepseek", "model": "deepseek-flash"}}
LOCAL = {"answer_route": {"kind": "local", "model": "qwen2.5"}}


def _run(cases: dict, slice_body: str = None, fromobj: dict = None) -> dict:
    u"""cases: name -> {"rec": <回执>, "at": <刻>}；`rec` 为 None ⇒ 无回执（探针 ⛔ 设 `PASelfRouteLast`）。"""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    js = (_prelude()
          + u"const window = {};\nlet REC = [];\n"
          + u"window.addMsg = function(role, content, skipStore, html, tid){"
            u" REC.push({role: role, content: content, html: html, tid: tid}); };\n"
          + (slice_body if slice_body is not None else _slice()) + "\n"
          + u"const M = " + json.dumps(fromobj or {}, ensure_ascii=False) + ";\n"
          + u"const CASES = " + json.dumps(cases, ensure_ascii=False) + ";\n"
          + u"const out = {msg: {}, label: {}, fromobj: {}};\n"
          + u"for(const k of Object.keys(M)) out.fromobj[k] = paRouteFromObj(M[k]);\n"
          + u"for(const k of Object.keys(CASES)){\n"
            u"  const c = CASES[k];\n"
            u"  REC = [];\n"
            u"  const L = paRouteLabel(c.rec);\n"
            u"  window.PASelfRouteLast = L ? {label: L, at: (c.at || ''), url: '/v9/pa/dialog'} : null;\n"
            u"  window.addMsg('assistant', 'BODY', false, '<p>BODY</p>', 'tid1');\n"
            u"  out.msg[k] = REC.length ? {content: REC[0].content, html: REC[0].html} : null;\n"
            u"  out.label[k] = L;\n"
            u"}\n"
          + u"console.log(JSON.stringify(out));\n")
    f = SCRATCH / "leaves_harness.js"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


# ============================ J1 正控 ============================

def test_J1_正控_远端必有出机标且实名取回执():
    out = _run({"a": {"rec": REMOTE, "at": "2026-10-06 12:00:00"},
                "b": {"rec": {"answer_route": {"kind": "remote", "provider": "deepseek",
                                               "model": "qwen-max-2025"}}, "at": ""}})
    t = out["msg"]["a"]["html"]
    assert LEAVES + "deepseek-flash" in t, t
    # ⭐ 实名**取回执**（⛔ 前端硬编）：换回执之名 ⇒ 屏上之名随换
    t2 = out["msg"]["b"]["html"]
    assert LEAVES + "qwen-max-2025" in t2, t2
    assert LEAVES + "deepseek-flash" not in t2, \
        u"出机之实名不听回执 ⇒ 硬编之嫌：%r" % t2
    # 走径标**⛔ 动**（唯改其位 ⇒ 折叠 · 承「一处定形」）
    assert ROUTE + u"src: remote:deepseek:deepseek-flash（键 answer_route · 采于 2026-10-06 12:00:00）" in t, t
    assert u'data-pa-route="1"' in t and u"engbody" in t, t
    # ⭐ 用户面（纯文）⛔ 载此二标（去壳之要）
    c = out["msg"]["a"]["content"]
    assert u"出机" not in c and ROUTE not in c, c


# ============================ J2 反控 ============================

def test_J2_反控_非远端必无出机标():
    out = _run({"loc": {"rec": LOCAL, "at": ""},
                "lok": {"rec": {"answer_route": {"kind": "local_model", "model": "m"}}, "at": ""},
                "ben": {"rec": {"kind": u"本机", "model": "m"}, "at": ""},
                "unk": {"rec": {"answer_route": {"provider": "p", "model": "m"}}, "at": ""},
                "none": {"rec": None, "at": ""}})
    for k in ("loc", "lok", "ben", "unk"):
        m = out["msg"][k]
        assert "出机" not in m["content"], u"%s：本机之轮竟有出机标：%r" % (k, m["content"])
        assert "出机" not in m["html"], u"%s：html 亦⛔ 得有此标" % k
        assert ROUTE in m["html"], u"%s：走径标被一并吞了（假红）" % k
    # ⚠ 「无回执」（`rec=None`）一例**别判**（承 pm_1076 §三 ／ pm_1812 §二.1⒟）：本轮真无回执
    #    ⇒ 本层**原样**（⛔ 造 `src: —（后端未给）` 之**伪行**）—— 有回执者 ⛔ 吞走径标（上四例）；
    #    无回执者 ⛔ 造标（本例）。二者之别即「空果 ≠ 空实」之落地。
    mn = out["msg"]["none"]
    assert "出机" not in mn["content"] and "出机" not in mn["html"], mn
    assert ROUTE not in mn["html"], u"无回执之轮 ⛔ 得造走径伪行：%r" % mn["html"]


# ============================ J3 三控 ============================

def test_J3_三控_无model之回执须明标后端未给():
    out = _run({"n": {"rec": {"kind": "remote", "provider": "deepseek"}, "at": ""}})
    m = out["msg"]["n"]
    assert LEAVES + UNDEF in m["html"], m["html"]
    assert ROUTE in m["html"], m["html"]
    # ⭐ 折叠体内「出机」居首（先于走径 · 承 §一.2）∧ 用户面无之（去壳）
    assert m["html"].index(u"内容将出机") < m["html"].index(ROUTE), m["html"]
    assert LEAVES not in m["content"] and UNDEF not in m["content"], m["content"]


# ============================ J4 位 ============================

def test_J4_位_出机先于走径_文与html二面():
    out = _run({"r": {"rec": REMOTE, "at": ""}})
    m = out["msg"]["r"]
    # ⭐ 去壳（pm_1812 §二.1）：二标皆入折叠 ⇒ 位判取**折叠体**（`html`）；用户面（纯文）须**无**此二标。
    assert "出机" not in m["content"] and "走径" not in m["content"], m["content"]
    s = m["html"]
    assert "出机" in s and "走径" in s, s
    assert s.index(u"内容将出机") < s.index(u"走径"), \
        u"html（折叠体）：红线 ⛔ 后于走径（须先入目）"


# ============================ J5 齿 ============================

def test_J5_齿_去唯远端之守则反控必红():
    src = _slice()
    guard = u"if(!L || !paRouteIsRemote(L.kind)) return null;"
    assert guard in src, u"守之原文已漂 ⇒ 本条齿须重钉"
    mutant = src.replace(guard, u"if(!L) return null;")
    assert mutant != src, u"改不动 ⇒ 这条齿是假的"
    out = _run({"loc": {"rec": LOCAL, "at": ""}}, slice_body=mutant)
    assert "出机" in out["msg"]["loc"]["html"], \
        u"齿失效：挖掉「唯远端」之守，本机之轮竟然还 ⛔ 无标"


# ============================ J6 静态 ============================

def test_J6_静态_实名不硬编且kind二集一处定形():
    src = _pa()
    body = _fn(src, "paLeavesLine")
    for bad in ("deepseek", "qwen", "flash", u"gpt-"):
        assert bad not in body, u"出机之器含具体模型名（硬编之戒）：%s" % bad
    assert "L.model" in body, u"实名须取回执（`label.model`）"
    # kind 之二集**一处**（`paRouteFromObj` 之支 ／ 出机之判 共此 ⇒ ⛔ 二份字面）
    assert src.count(u"'remote', 'api', '远端'") == 1, u"远端集之字面 ⛔ 二份"
    assert src.count(u"'local', 'local_model', '本机'") == 1, u"本机集之字面 ⛔ 二份"
    assert "paRouteIsRemote(kind)" in _fn(src, "paRouteFromObj"), u"渲形支须共此一判"


# ============================ J7 不回归 ============================

def test_J7_不回归_走径之渲形与底件逐字相等():
    out = _run({}, fromobj=FROMOBJ)
    got = out["fromobj"]
    diff = {k: (FROMOBJ_EXPECT[k], got[k]) for k in FROMOBJ_EXPECT if got[k] != FROMOBJ_EXPECT[k]}
    assert not diff, u"走径之渲形漂（底 ⇒ 今）：%s" % json.dumps(diff, ensure_ascii=False)