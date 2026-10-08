# -*- coding: utf-8 -*-
u"""pm_2091 §三.2（CW b2a5182 · 2026-10-09）—— `tasks` 面「工程墙」净化之齿。

一事：`web/pa/faces/tasks.js`（屏上唯人话 · 工程之据入门后之 `title` ／ `details.eng`）
      ＋ `web/pa.html` 一行（「派活 · 提交」之 `src` 槽 —— 端径 ⇒ `title`）。

⭐ 判据（承 pm_2061 裁⒉ ∧ pm_2091 §一）：**凡「用户须读方能行事」之文 ⇒ 唯人话**；
   **凡「工程之据」（端径 ／ 键名 ／ 盘径 ／ 会话 id ／ 类名）⇒ 入门后之折 ∨ `title`。**
⚠ 并承 pm_2091 裁⒞ 之并列则：**凡「逐行之件」⇒ 其辨异之最小形宜留屏**（⛔ 全入 `title`，否则满屏同形）。

S0 ⛔ 空跑（防「齿假绿」）：scope 之函数须**皆在** ∧ 屏上字面之数须 ≥ 门限。
S1 **结构齿**（正控）：scope 内之**屏上**字面 ⛔ 载禁记号（`⛔` ／ `**` ／ 反引号 ／ `/v9/` ／
   盘径 ／ `.jsonl` ／ 裸标识（`x_y`）／ 「后端」）。
S1b **逐字**（正控 · ⛔ 触浏览器）：pm_2091 §一 之二处微调 ＋ 逐字文案（屏上 ∧ 源码同）。
S2 **反控**（防「假牙」）：造一处 `⛔` 于**屏上**字面 ⇒ **必咬**；
   造于 `ENG_*` ／ `title` 之 HTML 属性 ／ 折（`details.eng`）之体 ⇒ **⛔ 咬**。
S3 **真渲齿**（真 Chrome × CDP）：`tasks` 面之**在屏**文（活树遍历 ＋ `checkVisibility` ＋ 折判）
   ⇒ 禁记号 = 0 ∧ 微记号（`x_y` ／ 「后端」）唯在**折首**（`details` 之 summary ⇒ 承「工程之据入门后之折」）。

⭐ 何以 scope 惟六函数（⛔ 全件扫）：本批所动者**唯此**（`git diff -U0` 之射程）
   ⇒ 全件扫必咬他面无涉之诸件（`paLoadEnvFace` ／ `paLoadRcptFace` ／ `paLoadLinesFace` …）
   ⇒ 越批之界 ∧ 破坏性。**射程 ＝ 本批之界**。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_taskface_clean_2090.py -q -p no:cacheprovider --basetemp=D:\\pa_tmp\\pt2090
"""
from __future__ import annotations

import io
import json
import os
import re
import socket
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / "web" / "pa" / "faces" / "tasks.js"
PAGEHTML = ROOT / "web" / "pa.html"

#: 本批所动之函数（`git diff -U0` 之射程 ＝ 本齿之射程）
SCOPE_FNS = (u"paRow", u"paEnsureSubGuard", u"paEnvAgentsRows", u"paLoadTasks",
             u"paRenderLocalTasks", u"paSubRouteInit")

#: 禁记号 —— 屏上**恒** ⛔ 许现（无例外）
STRICT_BANS = ((u"cross", u"\u26d4"), (u"star", u"**"), (u"btick", u"`"),
               (u"v9", u"/v9/"), (u"jsonl", u".jsonl"), (u"backend", u"\u540e\u7aef"))
#: 微记号 —— **折内**许现（工程注记 ／ 端给之真 id · 见 S3）
WEAK_BANS = ((u"underscore", r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b"),)
_DRIVE = re.compile(r"[A-Za-z]:[\\/]")
_CJK = re.compile(u"[\u4e00-\u9fff]")


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _bad(t: str) -> list:
    u"""一处屏上之字 ⇒ 命中之禁记号（⛔ 空 ⇒ 净）。"""
    out = [nm for nm, pat in STRICT_BANS if pat in t]
    for nm, pat in WEAK_BANS:
        if re.search(pat, t):
            out.append(nm)
    if _DRIVE.search(t):
        out.append(u"drive")
    return out


# ============================== 静态之器（纯函数 ⇒ 供反控喂变体） ==============================
_REGEX_OK_PREV = set("([,=:[!&|?{};+-*%~^<>") | {None, "\n"}


def _strip_comments(s: str) -> str:
    u"""去注（⛔ 伤字面内之字）。"""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            j = s.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in "\"'`":
            q = c
            out.append(c)
            i += 1
            while i < n:
                if s[i] == "\\":
                    out.append(s[i:i + 2])
                    i += 2
                    continue
                out.append(s[i])
                if s[i] == q:
                    i += 1
                    break
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _literals(s: str) -> list:
    u"""字面之列 `[(pos, 真文)]`（单 ／ 双 ／ 反引之引皆收；正则 ⛔ 以引充之）。"""
    out, i, n, prev = [], 0, len(s), None
    while i < n:
        c = s[i]
        if c in " \t\r\n":
            if c == "\n":
                prev = c
            i += 1
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            j = s.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and (prev is None or prev in _REGEX_OK_PREV):
            j, incls = i + 1, False
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "[":
                    incls = True
                elif s[j] == "]":
                    incls = False
                elif s[j] == "/" and not incls:
                    break
                elif s[j] == "\n":
                    break
                j += 1
            i = j + 1
            prev = "/"
            continue
        if c in "\"'`":
            q, j, buf = c, i + 1, []
            while j < n:
                if s[j] == "\\":
                    buf.append(s[j:j + 2])
                    j += 2
                    continue
                if s[j] == q:
                    break
                buf.append(s[j])
                j += 1
            out.append((i, "".join(buf)))
            i = j + 1
            prev = q
            continue
        prev = c
        i += 1
    return out


def _funcs(s: str) -> list:
    u"""`[(名, 起, 止)]` —— 以花括号配平（⛔ 以缩进猜）。"""
    out = []
    for m in re.finditer(r"(?:^|\n)(?:async\s+)?function\s+(\w+)\s*\(", s):
        i = s.index("{", m.end() - 1)
        d, j = 0, i
        while j < len(s):
            if s[j] == "{":
                d += 1
            elif s[j] == "}":
                d -= 1
                if d == 0:
                    break
            j += 1
        out.append((m.group(1), m.start(), j + 1))
    return out


def _fspan(fns: list, name: str) -> tuple:
    for (nm, a, b) in fns:
        if nm == name:
            return (a, b)
    return (-1, -1)


def _owner(fns: list, p: int) -> str:
    best = None
    for (nm, a, b) in fns:
        if a <= p < b and (best is None or a > best[1]):
            best = (nm, a, b)
    return best[0] if best else u"(top)"


def _arg_spans(s: str, p: int) -> list:
    u"""自 `p` 处之 `(` 起 ⇒ 诸实参之 `[(起, 止)]`（引 ／ 括号皆配平）。"""
    i = s.index("(", p)
    d, args, cur, j = 0, [], i + 1, i
    while j < len(s):
        ch = s[j]
        if ch in "\"'`":
            q = ch
            j += 1
            while j < len(s):
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == q:
                    break
                j += 1
        elif ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
            if d == 0:
                args.append((cur, j))
                return args
        elif ch == "," and d == 1:
            args.append((cur, j))
            cur = j + 1
        j += 1
    return args


def _anchor(s: str, a: str, b: str, frm: int = 0) -> tuple:
    u"""`a` 起 ⇒ `b` 止（含）之区间 —— ⛔ 在 ⇒ **立断**（免「静默失明」＝假绿）。"""
    i = s.find(a, frm)
    assert i >= 0, u"锚 ⛔ 在（齿之射程漂矣）：" + a[:60]
    j = s.find(b, i)
    assert j >= 0, u"锚之末 ⛔ 在（齿之射程漂矣）：" + b[:60]
    return (i, j + len(b))


def _ignores(src: str, fns: list) -> list:
    u"""**合法之地**之区间（工程之据之槽）：
      ① `ENG_*` 之声明（工程之据之地 · 入 `title` ／ 折者）；
      ② `title` 槽之实参（`paRow` 第 `5` ／ `paV3Tip` 第 `2` ／ `paAttachRowTitle` 第 `3`、`4`）；
      ③ `details.eng` 之**体**（`engbody` ／ 测试痕折之体）；
      ④ `subFailNotes`（唯入 `title` 之链）。
    """
    sp = []
    for m in re.finditer(r"(?:const|var|let)\s+ENG_\w+\s*=", src):
        j = src.find(";\n", m.start())
        sp.append((m.start(), j + 2 if j > 0 else m.end()))
    for m in re.finditer(r"\bpaRow\(", src):
        a = _arg_spans(src, m.start())
        if len(a) >= 5:
            sp.append(a[4])
    for m in re.finditer(r"\bpaV3Tip\(", src):
        a = _arg_spans(src, m.start())
        if len(a) >= 2:
            sp.append(a[1])
    for m in re.finditer(r"\bpaAttachRowTitle\(", src):
        a = _arg_spans(src, m.start())
        for k in (2, 3):
            if len(a) > k:
                sp.append(a[k])
    i_env = src.index(u"function paEnvAgentsRows(")
    sp.append(_anchor(src, u"'<div class=\"engbody\">'", u"'</div></details>';", i_env))
    i_tk = src.index(u"async function paLoadTasks(")
    sp.append(_anchor(src, u"'<details class=\"eng\" data-tt=\"taskledger\">'",
                      u"tst.map(rowOf).join('')", i_tk))
    sp.append(_anchor(src, u"const subFailNotes =", u"}) : [];", i_tk))
    return sp


def _inside(p: int, sp: list) -> bool:
    return any(x >= 0 and x <= p < y for (x, y) in sp)


_STMT_END = u";{}"
_NEEDLE = re.compile(r"(indexOf|includes|startsWith|endsWith|test)\s*\($")
#: 名约（pm_2061 裁⒉ 之实）：凡此尾之名 ⇒ 其字面**唯入** `title` ／ 折（⛔ 上屏之平文）
_TITLE_LHS = (u"Title", u"Tip", u"Str")
#: 折内之值：声明在折外 ／ 唯入 `details.eng` 之体（`paEnvAgentsRows` 之「探活」列）
_FOLD_BOUND = (u"probeCell",)


def _screen_part(txt: str) -> str:
    u"""一处字面 ⇒ 其**屏上**之分（`title="…"` 之属性 ⛔ 上屏 ⇒ 剔之）。"""
    t = re.sub(r'title="[^"]*"', "title=", txt)
    t = re.sub(r"title='[^']*'", "title=", t)
    k = t.find("title=")
    if k >= 0:
        rest = t[k + len("title="):]
        if not (rest.startswith('"') or rest.startswith("'")):
            t = t[:k]
    return t


def scan(src: str) -> dict:
    u"""纯扫（⛔ 触盘）：`{kept, hits, fns}` —— `kept` ＝ scope 内之屏上字面。"""
    fns = _funcs(src)
    spans = [_fspan(fns, n) for n in SCOPE_FNS]
    ign = _ignores(src, fns)
    kept, hits = [], []
    for (pos, txt) in _literals(src):
        if not any(a <= pos < b for (a, b) in spans):
            continue
        if _inside(pos, ign):
            continue
        if not _CJK.search(txt):
            continue
        k = max(src.rfind(c, 0, pos) for c in _STMT_END)
        prefix_raw = src[k + 1:pos]
        if prefix_raw.count('"') % 2 == 1:
            continue
        prefix = _strip_comments(prefix_raw)
        if re.search(r"\.title\s*=", prefix):
            continue
        if re.search(r"setAttribute\(\s*['\"]title['\"]\s*,", prefix):
            continue
        if _NEEDLE.search(prefix.rstrip()):
            continue
        m = re.match(r"\s*(?:const|var|let)?\s*([A-Za-z_$][\w$]*)\s*=", prefix)
        lhs = m.group(1) if m else u""
        if lhs.endswith(_TITLE_LHS) or lhs in _FOLD_BOUND:
            continue
        t = _screen_part(txt)
        kept.append((pos, _owner(fns, pos), t, lhs))
        b = _bad(t)
        if b:
            hits.append({"line": src[:pos].count("\n") + 1, "fn": _owner(fns, pos),
                         "bad": b, "lhs": lhs, "t": t})
    return {"kept": kept, "hits": hits, "fns": fns}


# ============================== S0 ／ S1 ／ S1b · 静态 ==============================
def test_S0_射程非空():
    u"""⛔ 空跑（防「齿假绿」）：scope 六函数须**皆在** ∧ 屏上字面须成量。"""
    s = scan(_read(TASKS))
    miss = [n for n in SCOPE_FNS if _fspan(s["fns"], n)[0] < 0]
    assert miss == [], u"scope 之函数 ⛔ 在（齿将空跑）：%r" % (miss,)
    assert len(s["kept"]) >= 60, u"scope 内之屏上字面过少（%d）⇒ 射程疑失" % len(s["kept"])
    assert u"paRow" in [n for (n, _a, _b) in s["fns"]], u"`paRow` 须在"


def test_S1_屏上字面唯人话():
    u"""pm_2091 §一：scope 内之**屏上**字面 ⛔ 载禁记号（工程之据 ⇒ `title` ／ 折 · ⛔ 平文）。"""
    s = scan(_read(TASKS))
    assert s["hits"] == [], u"屏上字面见禁记号 %s" % (
        u"；".join(u"`tasks.js:%d`（%s）%s %r" % (h["line"], h["fn"], h["bad"], h["t"][:60])
                    for h in s["hits"][:8]),)


def test_S1b_逐字文案():
    u"""pm_2091 §一 之二处微调 ＋ 本批之逐字文案（源码级 · ⛔ 触浏览器）。"""
    js = _read(TASKS)
    html = _read(PAGEHTML)
    # ⭐ 二处微调（pm_2091 §一.2 · 以之为准）
    assert u"已去掉测试痕" in js, u"#1 之微调 ⛔ 见（「已滤测试痕」⇒「已去掉测试痕」）"
    assert u"已滤测试痕" not in js, u"#1 之旧辞仍在"
    assert u"请勿重复按" in js, u"#4 之微调 ⛔ 见（「别重复按」⇒「请勿重复按」）"
    assert u"别重复按" not in js, u"#4 之旧辞仍在"
    # ⭐ 逐字（pm_2091 §一 之九处 · 抽三处定形者）
    assert u"本机暂无「受理态」之读数 —— 上列为本页已接之数" in js, u"#3 之逐字 ⛔ 符"
    assert u"本机派活记录（按「投到席 ∧ 未收口」计）" in js, u"#3（等待外部结果）之逐字 ⛔ 符"
    assert u"本机组织席位册" in js, u"#6 之名 ⛔ 见"
    assert u"本机两条派活之路" in js, u"#6 之逐字 ⛔ 符"
    # ⭐ 端径 ⇒ `title`（⛔ 平文）：派活 · 提交 一处
    assert u'title="POST /v9/subtask/create">送到本机执行' in html, \
        u"`pa.html` 之端径须入 `title` ∧ 屏上唯人话（承 pm_2091 §一）"
    # ⭐ 裁⒞：逐行之件 ⇒ 留短形 ∧ 全文入 `title`
    assert u"function paShortSid(k){" in js, u"裁⒞：短形之函须在"
    assert u"'…' + s.slice(-6)" in js, u"裁⒞：短形须**留屏可辨**（⛔ 全入 title）"
    assert u"title=\"会话 ' + paEsc(String(k))" in js, \
        u"裁⒞：全文须仍可**悬停**得（⛔ 丢真源）"
    # ⭐ 裁⒜：`PA_GAP.todo` 本批 ⛔ 动（承 PM 之裁）⇒ 仍为一体
    assert u"PA_GAP.todo()" in js and u"window.PA_GAP" not in js, u"裁⒜：`PA_GAP` ⛔ 得于本件重定义"


# ============================== S2 · 反控（防「假牙」） ==============================
def test_S2_反控必咬且不妄咬():
    u"""造病 ⇒ **必咬**；造于合法之地 ⇒ **⛔ 咬**（防「一概咬」之假牙 —— 与「永远绿」同病）。"""
    src = _read(TASKS)
    base = scan(src)
    assert base["hits"] == [], u"前提：正形须先净"

    # ⒜ 屏上之平文（`paRow` 之第 `3` 参 · 屏上之 `.s` 槽）⇒ 必咬
    mut = src.replace(u"'本机两条派活之路'", u"'\u26d4 本机两条派活之路'", 1)
    assert mut != src
    h = scan(mut)["hits"]
    assert h and any(u"cross" in x["bad"] for x in h), u"屏上之平文造病 ⇒ 必咬（⛔ 假绿）"

    # ⒝ `ENG_*`（工程之据之地）⇒ ⛔ 咬
    mut = src.replace(u"const ENG_clientSrc = '\u6e90\uff1aGET /v9/pa/local_client/status';",
                      u"const ENG_clientSrc = '\u26d4 \u6e90\uff1aGET /v9/pa/local_client/status';", 1)
    assert mut != src
    assert scan(mut)["hits"] == [], u"`ENG_*`（工程之据之地）⇒ ⛔ 得咬"

    # ⒞ `title="…"` 之 HTML 属性（屏外之地）⇒ ⛔ 咬
    mut = src.replace(u'title="\u6e90\uff1aGET /v9/pa/roster?full=1"',
                      u'title="\u26d4 \u6e90\uff1aGET /v9/pa/roster?full=1"', 1)
    assert mut != src
    assert scan(mut)["hits"] == [], u"`title` 属性（屏外）⇒ ⛔ 得咬"

    # ⒟ `details.eng` 之体（折内 ＝ 工程注记之地）⇒ ⛔ 咬
    mut = src.replace(u"'\u6e90\uff1aGET /v9/pa/roster?full=1#'",
                      u"'\u26d4 \u6e90\uff1aGET /v9/pa/roster?full=1#'", 1)
    assert mut != src
    assert scan(mut)["hits"] == [], u"`details.eng` 之体（折内）⇒ ⛔ 得咬"


# ============================== S3 · 真渲齿（真 Chrome × CDP） ==============================
GATEWAY = int(os.environ.get("PA_GATEWAY_PORT", "5102"))

_PROBE = r"""
(function(){
  function vis(e){ try{ if(e.checkVisibility){ return e.checkVisibility({checkOpacity:true, checkVisibilityCSS:true}); } }catch(x){}
    var r = e.getBoundingClientRect(); return !(r.width <= 0 && r.height <= 0); }
  function locOf(el){ var seg=[], n=el;
    for(var i=0;i<4 && n && n.nodeType===1;i++){ var s=String(n.tagName).toLowerCase();
      if(n.id) s+='#'+n.id;
      var c=(n.className && typeof n.className==='string')?n.className.trim().split(/\s+/).slice(0,2).join('.'):'';
      if(c) s+='.'+c; seg.push(s); n=n.parentElement; }
    return seg.join('<'); }
  var R = {cross:/\u26d4/g, star:/\*\*/g, btick:/`/g, tilde:/~~/g, v9:/\/v9\//g,
           drive:/[A-Za-z]:[\\\/]/g, jsonl:/\.jsonl/g,
           underscore:/\b[a-z][a-z0-9]*_[a-z0-9_]+\b/g,
           backstage:/\u540e\u7aef/g, internal:/\u4ed6\u5e2d|\u9057\u7559|\u4ef6\u53f7|\u7aef\u5f84/g};
  var root = document.getElementById('paFaceTasks');
  if(!root) return JSON.stringify({err:'no-face'});
  var texts = [], hits = [];
  function fire(n, txt, fold){ for(var key in R){ var re=new RegExp(R[key].source,'g'), m;
      while((m=re.exec(txt))!==null){ hits.push({k:key, fold:!!fold, loc:locOf(n),
        t:txt.slice(Math.max(0,m.index-30), m.index+50).replace(/\s+/g,' ').trim()}); } } }
  (function walk(n, fold){
    for(var i=0;i<n.childNodes.length;i++){
      var k = n.childNodes[i];
      if(k.nodeType === 3){
        var tx = String(k.nodeValue || ''); if(tx.replace(/\s+/g,'') === '') continue;
        if(!vis(n)) continue;
        texts.push((fold?'[F]':'') + tx.replace(/\s+/g,' ').trim());
        fire(n, tx, fold);
        continue; }
      if(k.nodeType !== 1) continue;
      if(!vis(k)) continue;
      var tag = String(k.tagName).toLowerCase();
      if(tag === 'details' && !k.hasAttribute('open')){
        var sm = k.querySelector('summary');
        if(sm && vis(sm)){
          var st = String(sm.textContent || '').replace(/\s+/g,' ').trim();
          texts.push('[F]' + st); fire(k, st, true); }
        continue; }
      walk(k, fold || (tag === 'details'));
    }
  })(root, false);
  var t = texts.join(' | '), bans = {};
  for(var kk in R){ var mm = t.match(R[kk]); bans[kk] = mm ? mm.length : 0; }
  return JSON.stringify({on: root.classList.contains('on'), len: t.length,
                         bans: bans, hits: hits, text: t});
})()
"""

_DISMISS = (u"(function(){ var bs = document.querySelectorAll('button');"
            u" for(var i=0;i<bs.length;i++){"
            u" if(String(bs[i].textContent||'').trim() === '\u77e5\u9053\u4e86'){ bs[i].click(); return 'clicked'; } }"
            u" return 'none'; })()")

_SWITCH = (u"(function(){ try{ setFaceById('tasks'); return 'ok'; }"
           u"catch(e){ return 'ERR:' + String(e); } })()")

#: 静文之上屏锚（本批之逐字 ⇒ 真渲须见 · ⛔ 见 ⇒ 面未渲 ∨ 辞漂）
_MUST_SHOW = (u"\u672c\u673a\u6d3e\u6d3b\u8bb0\u5f55",           # 本机派活记录
              u"\u672c\u673a\u5de5\u5177\u6d41\u6c34",           # 本机工具流水
              u"\u5df2\u53bb\u6389\u6d4b\u8bd5\u75d5",           # 已去掉测试痕
              u"\u672c\u673a\u80fd\u5e72\u54ea\u4e9b\u6d3b",     # 本机能干哪些活
              u"\u672c\u673a\u7ec4\u7ec7\u5e2d\u4f4d\u518c",     # 本机组织席位册
              u"\u672c\u673a\u4e24\u6761\u6d3e\u6d3b\u4e4b\u8def")  # 本机两条派活之路


def _reap():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cw_chrome_reap_tf2090", str(ROOT / "tests" / "unit" / "cw_chrome_reap.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _health_ok(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=3) as r:
            return int(getattr(r, "status", 0) or 0) == 200
    except Exception:
        return False


def _env_reason(R):
    u"""环境之守：⛔ 备 ⇒ skip 之由（⛔ 红 ∧ ⛔ 触网出外）。"""
    if not R.chrome_exe():
        return u"chrome.exe ⛔ 在"
    try:
        import websocket  # noqa: F401
    except Exception:
        return u"python websocket ⛔ 在（webscoket-client）"
    if not _health_ok(GATEWAY):
        return u"活端（%d）⛔ 应" % GATEWAY
    return u""


def _free_port():
    sk = socket.socket()
    sk.bind(("127.0.0.1", 0))
    p = sk.getsockname()[1]
    sk.close()
    return p


def _ws_url(port, tries=40):
    for _ in range(tries):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=3) as r:
                lst = json.loads(r.read().decode("utf-8", "replace"))
            for t in lst:
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    return t["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError("CDP 之页 ⛔ 得（口 %d）" % port)


class _CDP(object):
    def __init__(self, ws):
        import websocket
        self.ws = websocket.create_connection(ws, timeout=90, max_size=256 * 1024 * 1024)
        self.i = 0

    def cmd(self, m, **p):
        self.i += 1
        mid = self.i
        self.ws.send(json.dumps({"id": mid, "method": m, "params": p}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == mid:
                return r

    def js(self, e):
        r = self.cmd("Runtime.evaluate", expression=e, returnByValue=True, awaitPromise=False)
        try:
            return r["result"]["result"]["value"]
        except Exception:
            return json.dumps(r)[:400]

    def shot(self, path):
        import base64
        r = self.cmd("Page.captureScreenshot", format="png", captureBeyondViewport=False)
        io.open(path, "wb").write(base64.b64decode(r["result"]["data"]))
        return os.path.getsize(path)


def test_S3_真渲之屏净(tmp_path):
    u"""真 Chrome × CDP：`tasks` 面之**在屏**文 ⇒ 禁记号 = 0 ∧ 微记号唯在**折首**。

    ⭐ 取法（承我域之尺 · 例⒏ ／ 例⒐）：**活树遍历**（`checkVisibility` ＋ 折判）——
      ⛔ 裸 `textContent`（含 `<script>` 源与隐藏件）⛔ 全信 `innerText`（含折内之隐字）。
    禁记号（`⛔` ／ `**` ／ 反引号 ／ `/v9/` ／ 盘径 ／ `.jsonl` ／ 他席之内部语）⇒ **恒 0**；
    微记号（`x_y` 裸标识 ／ 「后端」）⇒ 唯在 `details` 之 **summary**（＝工程之据入门后之折之地）——
      ⭐ 端给之**真 id**（如 `ds_chat`）照实留屏（承 pm_2091 裁⒞ 之并列则）。
    环境不就绪 ⇒ **skip**（⛔ 红）；真跑毕 ⇒ 必收（`cw_chrome_reap`）∧ 图落盘。
    """
    R = _reap()
    reason = _env_reason(R)
    if reason:
        pytest.skip(u"环境不就绪：" + reason)
    port = _free_port()
    with R.run_headless(port=port, tag="cw2090tk", wait_s=15.0,
                        extra=("--remote-allow-origins=*",),
                        why=u"pm_2091 tasks 面之屏净（真渲之齿）"):
        c = _CDP(_ws_url(port))
        c.cmd("Page.enable")
        c.cmd("Runtime.enable")
        c.cmd("Emulation.setDeviceMetricsOverride", width=1440, height=940,
              deviceScaleFactor=1, mobile=False)
        c.cmd("Page.navigate", url="http://127.0.0.1:%d/web/pa.html" % GATEWAY)
        time.sleep(7.0)
        assert c.js(_SWITCH) == "ok", u"切 `tasks` 面 ⛔ 成"
        time.sleep(1.0)
        c.js(_DISMISS)
        res = None
        for _ in range(20):
            time.sleep(1.0)
            raw = c.js(_PROBE)
            try:
                res = json.loads(raw)
            except Exception:
                continue
            if res.get("on") and int(res.get("len") or 0) > 600 and \
                    u"\u672c\u673a\u6d3e\u6d3b\u8bb0\u5f55" in (res.get("text") or ""):
                break
        shot = c.shot(str(tmp_path / "tasks_w1440.png"))

    assert res and res.get("on") is True, u"`tasks` 面 ⛔ 在屏（`on`）：%r" % (res,)
    assert int(res["len"]) > 600, u"屏文过少 ⇒ 面未渲：%r" % (res["len"],)
    strict = [k for (k, _p) in STRICT_BANS] + [u"tilde", u"drive", u"internal"]
    bad = {k: v for k, v in res["bans"].items() if k in strict and v}
    assert bad == {}, u"屏上见禁记号 %s｜逐处 %s" % (
        bad, u"；".join(u"%s@%s %r" % (h["k"], h["loc"], h["t"][:50])
                        for h in res["hits"] if h["k"] in bad)[:900])
    loose = [h for h in res["hits"] if h["k"] in (u"underscore", u"backstage")]
    plain = [h for h in loose if not h["fold"]]
    assert plain == [], u"微记号现于**平文**（宜入门后之折）：%s" % (
        u"；".join(u"%s@%s %r" % (h["k"], h["loc"], h["t"][:50]) for h in plain[:6]),)
    txt = res["text"]
    for lit in _MUST_SHOW:
        assert lit in txt, u"逐字 ⛔ 见（面未渲 ∨ 辞漂）：%r" % (lit,)
    assert shot > 0, u"图须落盘（跑毕必收 ∧ 入账）"