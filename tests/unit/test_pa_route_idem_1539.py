# -*- coding: utf-8 -*-
u"""pm_1539 §二.1 ／ pm_1543 §二.⒜ ／ pm_1542 §三.3 之齿（CW b2a5182 · 2026-10-06）。

三事：
  K1 正控（走径之幂等）：`more.js` 之包装**首渲**照旧前置一行走径（⛔ 回归）。
  K2 反控（重渲 ⛔ 增行）：`renderThread()` 重喂**已含走径之标**（`data-pa-route` 之 html ∨
     以走径行 ／ 出机行开头之纯文）⇒ **⛔ 再前置**（`reload` 实测 `.paroute` 2 ⇒ 4 · 我 `1543` 一手）。
  K3 拒答之标（一处定形）：`send.js` 之拒答支**自落己标**（`kind:'self'` · 承 pm_1483 §一 之同法）
     ∧ ⛔ 旧「（后端之辞 ⛔ 载入）」之字（其义反）∧ 引后端之 `verdict`（缺 ⇒ 明书）。
  K4 `**粗**`（MD 之标）⇒ `paSelfMulSafe` **⛔ 转 `×`**（老板一手：屏上 `（ × 能力端点册 × ）`）。

以何形调用：python -X utf8 -B -m pytest tests/unit/test_pa_route_idem_1539.py -q
"""
from __future__ import annotations

import io, json, re, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MORE = ROOT / "web" / "pa" / "faces" / "more.js"
SEND = ROOT / "web" / "pa" / "faces" / "send.js"
SDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
CORE = ROOT / "web" / "pa" / "core.js"
TASKS = ROOT / "web" / "pa" / "faces" / "tasks.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_route_idem1539"

ANCHOR_A = u"/* ⭐「本机 / 远端」之二集"
ANCHOR_B = u"function paProvMount(){"
ROUTE = u"🔌 走径："
UNDEF = u"（后端未给）"


def _fn(src: str, name: str) -> str:
    i = src.find("function " + name + "(")
    assert i > 0, "未找到函数 " + name
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
    raise AssertionError("函数 " + name + " 花括号不配平")


def _prelude() -> str:
    core = io.open(str(CORE), encoding="utf-8").read()
    tasks = io.open(str(TASKS), encoding="utf-8").read()
    m = re.search(r"var EPOCH_SEC_RE = .*?;", core)
    assert m, "EPOCH_SEC_RE 未找到"
    return (m.group(0) + "\n" + _fn(core, "fmtStamp") + "\n"
            + u"const PA_STAMP = { fmt: fmtStamp, secRe: EPOCH_SEC_RE };\n"
            + _fn(tasks, "paEsc") + "\n")


def _slice() -> str:
    s = io.open(str(MORE), encoding="utf-8").read()
    return s[s.index(ANCHOR_A):s.index(ANCHOR_B)]


def _run_more(cases: dict) -> dict:
    u"""cases: name -> {rec, at, content, html}（`rec=None` ⇒ 无回执 ⇒ 落 `paRouteLine(null)`）。"""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    js = (_prelude()
          + u"const window = {};\nlet REC = [];\n"
          + u"window.addMsg = function(role, content, skipStore, html, tid){"
            u" REC.push({role: role, content: content, html: html, tid: tid}); };\n"
          + _slice() + "\n"
          + u"const CASES = " + json.dumps(cases, ensure_ascii=False) + ";\n"
          + u"const out = {};\n"
          + u"for(const k of Object.keys(CASES)){\n"
            u"  const c = CASES[k];\n"
            u"  REC = [];\n"
            u"  const L = paRouteLabel(c.rec);\n"
            u"  window.PASelfRouteLast = L ? {label: L, at: (c.at || ''), url: '/v9/pa/dialog'} : null;\n"
            u"  window.addMsg('assistant', c.content, false, c.html === undefined ? undefined : c.html, 'tid1');\n"
            u"  out[k] = REC.length ? {content: REC[0].content, html: REC[0].html} : null;\n"
            u"}\nconsole.log(JSON.stringify(out));\n")
    f = SCRATCH / "route_idem.js"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _count(line: str, sub: str) -> int:
    return line.count(sub)


# ============================ K1 ／ K2 走径之幂等 ============================

REMOTE = {"answer_route": {"kind": "remote", "provider": "deepseek", "model": "deepseek-flash"}}


def test_K1_正控_首渲照旧前置一行():
    out = _run_more({"a": {"rec": REMOTE, "at": "2026-10-06 12:00:00",
                           "content": "BODY", "html": "<p>BODY</p>"}})
    c = out["a"]["content"]; h = out["a"]["html"]
    # ⭐ 去壳（pm_1812 §二.1）：走径 ／ 出机 二标皆入**折叠**（一处定形）
    #    ⇒ 用户面（纯文 `content`）⛔ 载；原文照录在折叠体内（`_count(h, …) == 1`）。
    assert _count(c, ROUTE) == 0, c
    assert u"本轮经云端 · 内容将出机 · 模型 deepseek-flash" in h, h
    assert _count(h, ROUTE) == 1, h
    assert _count(h, "data-pa-route") == 1, h


def test_K2_反控_重渲不增行():
    first = _run_more({"a": {"rec": REMOTE, "at": "2026-10-06 12:00:00",
                             "content": "BODY", "html": "<p>BODY</p>"}})["a"]
    second = _run_more({"b": {"rec": None, "at": "",
                              "content": first["content"], "html": first["html"]}})["b"]
    assert _count(second["html"], ROUTE) == 1, second["html"]
    assert _count(second["html"], "data-pa-route") == 1, second["html"]   # ⛔ 折上加折
    assert second["content"] == first["content"], (first["content"], second["content"])
    # 纯文之路（无 html）：重喂以走径行开头之串 ⇒ 摘入折叠（⛔ 再前置 · boss 之「二伪行」之源）
    plain = _run_more({"c": {"rec": None, "at": "", "content": ROUTE + UNDEF + "\nBODY"}})["c"]
    assert _count(plain["html"], ROUTE) == 1, plain["html"]
    assert plain["content"] == "BODY", plain["content"]


# ============================ K3 拒答之标 ＋ 字面 ============================

def test_K3_拒答支_自落己标_且无旧字():
    s = io.open(str(SEND), encoding="utf-8").read()
    code = re.sub(r"/\*.*?\*/", "", s, flags=re.S)      # ⚠ 注内之引（律之载）⛔ 计入
    assert u"（后端之辞 ⛔ 载入）" not in code, u"旧字（义反）仍在 send.js 之代码面"
    assert u"后端未给逐字之由（唯 canonical）" in s, u"缺 verdict 时之明书 ⛔ 在"
    assert u"后端判词：" in s, u"未引后端 verdict"
    assert u"window.PASelfRouteLast = {" in s and u"key: '拒答'" in s, u"拒答支 ⛔ 自落己标"
    assert u"kind: 'self'" in s, u"自述/拒答之 kind 须 ⛔ 入远端集（⛔ 上出机标）"


# ============================ K4 `**` 之 MD 标 ⛔ 转 ============================

def _mul_safe(exprs):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    s = io.open(str(SDESC), encoding="utf-8").read()
    m = re.search(r"const PA_MUL_STAR = .*?;", s)
    assert m, "PA_MUL_STAR 未找到"
    js = (m.group(0) + "\n" + _fn(s, "paSelfMulSafe") + "\n"
          + u"const E = " + json.dumps(exprs, ensure_ascii=False) + ";\n"
          + u"console.log(JSON.stringify(E.map(paSelfMulSafe)));\n")
    f = SCRATCH / "mulsafe.js"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_K4_MD之粗标不转乘号():
    out = _mul_safe([u"（**能力端点册**）", u"200*1.1*0.9", u"(1+2)*(3+4)", u"x*y", u"2 * x"])
    assert out[0] == u"（**能力端点册**）", out[0]        # 正控：⛔ 转
    assert out[1] == u"200 × 1.1 × 0.9", out[1]           # 不回归：真算式照转
    assert out[2] == u"(1+2) × (3+4)", out[2]
    assert out[3] == u"x*y" and out[4] == u"2 * x", out[3:]
