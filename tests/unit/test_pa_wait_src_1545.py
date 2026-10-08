# -*- coding: utf-8 -*-
u"""pm_1545 §二.1 ／ §二.2 之齿（CW b2a5182 · 2026-10-06）。

二事：
  L1 正控（等待提示之字 ⇒ 依「本轮实走何路」）：`paSelfModelKind()` 取所选模型行之 `kind`
     ⇒ `local` 书「本机模型」／`remote` 书「云端模型」／表未得书「模型」（⛔ 恒书「本机」）。
     （病：旧文硬编 ⇒ 闲聊轮回落云端时其上屏 ⇒ 不实之辞 · 老板之屏一手。）
  L2 反控（旧字绝迹）：`'等待本机模型回复'` 之字面 ⛔ 在。
  ⭐ pm_2061 §二.2（裁⒉ · 屏上唯人话）：云端轮之「因」句已剔饰符（反控：`**` ⛔ 在）。
  L3 正控（自述轮之源 ⇒ 一轮一清）：`busy0` ⇒ 唯落本轮之源（`paRunSrc = SRC`）；
     非 `busy0` ⇒ 走 `paSetState(…, SRC)`（旧链一字不动）。
  L4 反控（旧法之残）：以旧形（无 `else`）跑 `busy0` ⇒ `paRunSrc` 承前轮
     ⇒ 回执之「做了什么」（`srcOf()` ≡ `paRunSrc`）书**前轮**之径（我一手：自述轮书 `POST /v9/pa/dialog`）。

以何形调用：python -X utf8 -B -m pytest tests/unit/test_pa_wait_src_1545.py -q
"""
from __future__ import annotations

import io, json, re, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_wait_src1545"


def _src() -> str:
    return io.open(str(SDESC), encoding="utf-8").read()


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


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


# ============================ L1 ／ L2 等待提示之字 ============================

PAINT_JS = u"""let paSelfWaitBoundMs = 130000;
__KIND__
__PAINT__
var paModelRows = null;
var paModelSel = function(){ return ''; };
function setEnv(rows, sel){ paModelRows = rows; paModelSel = function(){ return sel; }; }
function paint(){
  var b = { textContent: '' };
  var el = { parentNode: {}, querySelector: function(){ return b; }, setAttribute: function(){} };
  paSelfWaitPaint(el, 3, false);
  return b.textContent;
}
var OUT = {};
setEnv([{ id: 'm1', kind: 'local' }], 'm1');   OUT.local = paint();
setEnv([{ id: 'm2', kind: 'remote' }], 'm2');  OUT.remote = paint();
setEnv([], '');                                OUT.none = paint();
console.log(JSON.stringify(OUT));
"""


def test_L1_等待提示之字依本轮实走何路():
    s = _src()
    js = PAINT_JS.replace("__KIND__", _fn(s, "paSelfModelKind")).replace("__PAINT__", _fn(s, "paSelfWaitPaint"))
    out = _node(js, "wait")
    assert u"本机模型" in out["local"], out["local"]
    assert u"触发" in out["local"], out["local"]
    assert u"云端模型" in out["remote"], out["remote"]
    assert u"本轮走云端（内容将出机）" in out["remote"], out["remote"]
    assert u"**" not in out["remote"], u"用户面载饰符（承 pm_2061 §二.2 裁⒉）—— " + out["remote"]
    assert u"本机模型" not in out["remote"], out["remote"]          # ⭐ 旧病：云端轮书「本机」
    assert u"等待模型回复" in out["none"], out["none"]               # 未得 ⇒ 中性
    assert (u"本机模型" not in out["none"]) and (u"云端模型" not in out["none"]), out["none"]


def test_L2_反控_旧硬编之字绝迹():
    s = _src()
    assert u"等待本机模型回复" not in s, u"旧硬编字面仍在（闲聊轮回落云端时不实）"
    assert u"paSelfModelKind" in s and u"paModelSel" in s and u"paModelRows" in s, u"表之取源缺"


# ============================ L3 ／ L4 自述轮之源 ============================

BRANCH_RE = re.compile(
    u"if\\(!busy0 && typeof paSetState === 'function'\\)\\{ try\\{ paSetState\\('running', '[^']+', SRC\\); \\}catch\\(e\\)\\{\\} \\}"
    u"\\n    else \\{ try\\{ paRunSrc = SRC; \\}catch\\(e\\)\\{\\} \\}")


def _branch() -> str:
    m = BRANCH_RE.search(_src())
    assert m, "未找到「收源」之支（pm_1545 §二.2 之式）"
    return m.group(0)


def _run_src(busy: bool, stmt: str) -> dict:
    js = (u"let paRunSrc = 'POST /v9/pa/dialog';\n"
          u"const SRC = '\u672c\u673a\u81ea\u8ff0\u6765\u6e90';\n"
          u"let calls = [];\n"
          u"function paSetState(k, note, s){ calls.push([k, note, s]); if(s) paRunSrc = String(s); }\n"
          u"let busy0 = " + ("true" if busy else "false") + ";\n"
          + stmt + "\n"
          u"console.log(JSON.stringify({ paRunSrc: paRunSrc, calls: calls.length }));\n")
    return _node(js, "src_" + ("busy" if busy else "free"))


def test_L3_正控_在办亦落本轮之源():
    stmt = _branch()
    busy = _run_src(True, stmt)
    assert busy["paRunSrc"] == u"本机自述来源", busy       # ⭐ 本轮之源（⛔ 承前轮）
    assert busy["calls"] == 0, busy                        # ⛔ 动在办之轮之态
    free = _run_src(False, stmt)
    assert free["paRunSrc"] == u"本机自述来源", free
    assert free["calls"] == 1, free                        # 旧链一字不动


def test_L4_反控_旧形在办则承前轮():
    old = _branch().split(u"\n    else")[0]                # 旧形：无 else 支
    r = _run_src(True, old)
    assert r["paRunSrc"] == u"POST /v9/pa/dialog", r        # 残值之实（我一手）
    assert r["calls"] == 0, r