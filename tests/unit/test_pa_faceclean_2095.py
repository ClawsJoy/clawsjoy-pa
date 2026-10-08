# -*- coding: utf-8 -*-
r"""pm_2095（CW b2a5182 · 2026-10-09）—— 次批「工程墙」净化之齿。

本批之射程（承 pm_2095 §一 之七物 ＋ §二 之四裁）：
  ⒜ `sys.js` —— 本机体检面：端所给之辞**就地人话化**（`⛔` 之族 ⇒ 人话 · 原字入 `title` ／ `data-raw`）
  ⒝ `selfdesc.js` —— `#paT1Panel` 折首 ＋ 体内平文 ＋ `#paHistList`（会话 id 短形留屏 ∧ 全 id 入 `title`）
  ⒞ `pa.html` —— 诊断区（`#paAboutBody`）之容器 ⇒ `details.eng`（`#paAboutFold`）

⭐ 判据（承 pm_2061 裁⒉ ∧ pm_2091 §一 ∧ pm_2095 §二）：
  **凡「用户须读方能行事」之文 ⇒ 唯人话**；**凡「工程之据」⇒ 形必折（`details.eng`）∨ `title`。**
  ⭐ 折之判**唯认 `details.eng`**（`details.mgrp` ／ `msub` ＝ 导航之折 ⇒ 其**体**仍算**平文**）——
    ⛔ 以「任一 details」充「工程之折」（否则一切皆可藏 ⇒ 齿成空跑）。
  ⚠ 并承 pm_2091 裁⒞ 之并列则：逐行之件 ⇒ 其辨异之最小形宜留屏（⛔ 全入 `title`）。
  ⚠ 盘符（`C:\` ／ `D:\`）**准留**（pm_2095 §二.2 之追认）；端给之**真 id** ／ 真件名 ／ 会话 id
    （`ds_chat` ／ `dsh_wsl` ／ `v9_agent` ／ `web_…` ／ `.agent_state.json` ／ `pa_*`）照实留屏。

S0 ⛔ 空跑：scope 之锚须**皆在** ∧ 屏上字面之数须 ≥ 门限。
S1 **结构齿**（正控）：scope 内之**屏上**字面 ⛔ 载禁记号（`⛔` ／ `**` ／ 反引号 ／ `/v9/` ／ `.jsonl` ／
   「后端」）∧ ⛔ 载**端字段名**（`level` ／ `caps` ／ `invoke` ／ `cost` ／ `probe` ／ `paths` ／ `ids`）。
S1b **逐字**（正控 · ⛔ 触浏览器）：本批之定形辞（`sys.js` ／ `selfdesc.js` ／ `pa.html`）。
S2 **反控**（防「假牙」）：造一处于**屏上**字面 ⇒ **必咬**（`⛔` 一例 ＋ 端字段名一例）；
   造于 `title="…"` 之属性 ⇒ **⛔ 咬**；端给之真 id ／ 盘符 ⇒ **⛔ 咬**。
S3 **真渲齿**（真 Chrome × CDP）：`更多 ▾`（本机体检 ＋ 关于 ＋ 会话历史）＋ `tasks` 面（`#paT1Panel`）
   之**在屏**文 —— 活树遍历 ＋ `checkVisibility` ＋ **`details.eng` 之折判**（钳开诸折后取字）
   ⇒ 平文（⛔ 折内）之禁记号 = 0 ∧ 端字段名 = 0。
S9 **收口**（pm_2108 §三）：`sha16` ⇒ 「指纹」（原字入 `title`）、`placeholder` ⇒ **屏上**（新例ⓒ）、「前端」⇒ 本面。
S10 **计划面**（pm_2109 §一）：`doPlan` / `renderPlan` 之屏上唯人话（端径 / `task_type` / `source` ⇒ `title`）。
S5 **守卫之真路齿**（真 Chrome × CDP · pm_2104 §二）：停手卡（`#paStopAsk`）由 `stopAsk()` 自建
   ⇒ 守卫 ⛔ 得于建卡前索其存在；**正控**（真路 · ⛔ 预置 `#paStopAsk`）⇒ 必见卡题；
   **反控**（删 `window.paStopAsk`）⇒ 必见「停手卡不可用」。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_faceclean_2095.py -q -p no:cacheprovider --basetemp=D:\\pa_tmp\\pt2095
"""
from __future__ import annotations

import io
import bisect
import importlib.util
import json
import os
import re
import socket
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SYS = ROOT / "web" / "pa" / "faces" / "sys.js"
SELF = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
PAGEHTML = ROOT / "web" / "pa.html"

#: 沿用 pm_2091 齿之静态之器（纯函数 · ⛔ 二处各写一套）
_spec = importlib.util.spec_from_file_location(
    "cw_tf2090", str(ROOT / "tests" / "unit" / "test_pa_taskface_clean_2090.py"))
tf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tf)

_STRIP = tf._strip_comments
_LITS = tf._literals
_ANCHOR = tf._anchor
_SCREENPART = tf._screen_part
_FUNCS = tf._funcs
_FSPAN = tf._fspan
_OWNER = tf._owner
_CJK = tf._CJK
_STMT_END = tf._STMT_END
_NEEDLE = tf._NEEDLE
_DRIVE = tf._DRIVE

#: ⚠ 旧形（`tf._screen_part`）之病：先剔**完整**之 `title="…"` ⇒ 留 `title=` ⇒ 复判「悬引」
#:   ⇒ **截去其后之屏上之字**（如 `title="真源：…">件号 ' + …` 之屏上段 `件号 ` 得漏 ⇒ 反控空跑）。
#:   今**自左至右**剔：完整之属性 **剔其值** ∧ **悬引**（值在拼接式之内）⇒ 自此皆属性 ⇒ 弃余。
_ATTR_NAME_RE = re.compile(u'[A-Za-z_:][-A-Za-z0-9_:]*\\s*=\\s*')


#: ⭐⭐ pm_2108 §三.1ⓜ（**新例ⱒ**）：属性之值 ⇒ **屏外**（剔）；然 `placeholder` ／ `value`
#:   之字 **用户真见**（`<input placeholder>` 之提示词 ∕ 逗号值）⇒ **算平文（必咬）**。
#:   ⚠ 旧形**概剔诸属性** ⇒ 把 `title`（屏外 ✓）与 `placeholder`（屏上）**混为一谈**
#:   ⇒ 本收口之 `sha16`（两处 `placeholder`）即由此漏（一手之证：旧法掃得 `0` · 新法掃得必咬）。
_ATTR_ONSCREEN = (u"placeholder", u"value")


def _screen_part_local(txt: str) -> str:
    u"""一处字面 ⇒ 其**屏上**之分（属性 `name="…"` ⛔ 上屏 ⇒ 剔之 · **唯 `placeholder` ／ `value` 留**）。"""
    out, i, n = [], 0, len(txt)
    while i < n:
        m = _ATTR_NAME_RE.match(txt, i)
        if m:
            nm = m.group(0).split(u"=")[0].strip().lower()
            q = txt[m.end():m.end() + 1]
            if q in ('"', "'"):
                e = txt.find(q, m.end() + 1)
                if e < 0:
                    break
                if nm in _ATTR_ONSCREEN:
                    out.append(txt[i:e + 1])
                i = e + 1
                continue
            break
        out.append(txt[i])
        i += 1
    return u"".join(out)


_SCREENPART = _screen_part_local
#: 字面内之 HTML 属性（`title="…"` ／ `data-axis="probe"` 之族）⇒ **屏外** ⇒ 剔之（⛔ 上屏之字）
_ATTR_RE = re.compile(u'[A-Za-z_:][-A-Za-z0-9_:]*\\s*=\\s*"[^"]*"')

#: 禁记号 —— 屏上**恒** ⛔ 许现（无例外）
STRICT_BANS = ((u"cross", u"\u26d4"), (u"star", u"**"), (u"btick", u"`"),
               (u"v9", u"/v9/"), (u"jsonl", u".jsonl"), (u"backend", u"\u540e\u7aef"))
#: ⭐ 端字段名 —— 平文 ⛔ 许现（承 pm_2095 §三.1；`title` ／ 折体 ／ 端给之真 id ⇒ 绿）
FIELDNAMES = (u"level", u"caps", u"invoke", u"cost", u"probe", u"paths", u"ids")
_FIELD_RE = re.compile(u"(?<![A-Za-z0-9_$])(" + u"|".join(FIELDNAMES) + u")(?![A-Za-z0-9_$])")
#: ⭐⭐ 标识名族（pm_2104 §四.5⒟⒝）：端之键 ／ 工程之辞 —— 平文 ⛔ 许现（⇒ `title` ／ 折体）
IDNAMES = (u"task_id", u"decision_id", u"wall_s", u"tokens", u"fail-closed",
            #: ⭐ pm_2108 §三.1ⓝ：`sha16`（凭据之指印之端键）⇒ 平文 ⛔ 许现
            u"sha16",
            #: ⭐⭐ pm_2109 §一.1：计划面之端键（`task_type`）⇒ 入族；
            #:   `source`（其真源在端 · pm_2109 §二.2ⓘ 已另函 TD）⇒ 本侧唯「⛔ 上屏」。
            u"task_type", u"source")
_ID_RE = re.compile(u"(?<![A-Za-z0-9_$])(" + u"|".join(IDNAMES) + u")(?![A-Za-z0-9_$])")
#: ⭐ 原字之 `HTTP `：屏上唯 `<码>`（原字**逐字全**入 `title` · 承 pm_2097 §三.2 ／ pm_2102 §二.3）
_HTTP_RE = re.compile(u"HTTP ")
#: ⭐ 工程语（pm_2102 §一 丁12）：平文 ⛔ 许现
ENGWORDS = (u"\u8def\u7531",   # 「路由」
            u"\u524d\u7aef")    # 「前端」（pm_2108 §三.1ⓝ：名之一处 ⇒ 本面）
_ENG_RE = re.compile(u"|".join(ENGWORDS))
#: 白名单 —— 端给之真 id ／ 真件名 ／ 会话 id（照实之律 · 面 ⛔ 代端改名）
ALLOW = re.compile(u"(?:ds_chat|dsh_wsl|v9_agent|web_[A-Za-z0-9]+|\\.agent_state\\.json|pa_[A-Za-z0-9_]+)")
#: 命令行之旗（`--system-level` ／ `-background` 之族）＝ 端给之真值 ⇒ 白名单
_FLAG_RE = re.compile(u"(?<![A-Za-z0-9])-{1,2}[A-Za-z][-A-Za-z0-9_]*")


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _unesc(s: str) -> str:
    r"""源码之**原文**（`\u26d4` 之族）⇒ 真字。

    ⚠ 一手之验：`_literals` 所给者 ＝ 源码之**原文** ⇒ 若 ⛔ 解码 ⇒ 凡以 `\uXXXX` 写就之字面
      一条也逮不着（原样扫得 `0` 条 · 解码后乃见）⇒ 齿成**空跑**（承律①：量法即读数之半）。
    """
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    return s.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")


def _mask(t: str) -> str:
    u"""白名单之串 ⇒ 掩之（免得齿咬「端给之真 id」／命令行之旗）。"""
    t = _FLAG_RE.sub(lambda m: u"\u3000" * len(m.group(0)), t)
    return ALLOW.sub(lambda m: u"\u3000" * len(m.group(0)), t)


def _bad(t: str) -> list:
    m = _mask(t)
    out = [nm for (nm, pat) in STRICT_BANS if pat in t]
    if _FIELD_RE.search(m):
        out.append(u"fieldname")
    if _DRIVE.search(m):
        out.append(u"drive")
    if re.search(r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b", m):
        out.append(u"underscore")
    if _ID_RE.search(m):
        out.append(u"idname")
    if _HTTP_RE.search(m):
        out.append(u"http")
    if _ENG_RE.search(m):
        out.append(u"engword")
    return out


# ============================== 射程（本批之界） ==============================
#: ⭐⭐ T1 交付面之诸函（pm_2104 §四.4⒝）—— **缩进之函**（IIFE 之内）⇒ 须另取（`_ifuncs`）
_T1_SCOPE_FNS = (u"refLine", u"spendLine", u"costLine", u"numOr", u"loadDecision", u"doAdopt",
                 u"openAuthzCard", u"send", u"fourItems", u"failHTML", u"showFail",
                 u"renderReceipt", u"humanOf", u"flat", u"deliverBody", u"build", u"stopAsk",
                 u"engDetails", u"probeBackend")
#: ⭐⭐ pm_2109 §一：计划面之诸函（`doPlan` / `renderPlan`）—— 本收口**并入**（列而不在射程 ⇒ 齿空跑）。
_PLAN_SCOPE_FNS = (u"doPlan", u"renderPlan")
#: ⭐⭐ 折（`details.eng`）之**体** ⇒ **屏外**（⛔ 上屏）· 逐字明标 ＋ 书其由（pm_2104 §三.4）：
#:   其字（`POST /v9/pa/deliver/mail` ／ `task_id` ／ `decision_id` ／ `fail-closed`）＝ **工程之据**
#:   ⇒ ⛔ 删（删之即违 pm_2061 裁⒉「⛔ 丢真源」）；**反控**：去其折体之容器（＝把其字移入平文）⇒ **必咬**。
_T1_IGN = (
    (u"'<div class=\"engbody\">体：POST /v9/pa/deliver/mail {user_id, task_id, decision_id, to, subject, body_md}'",
     u"返既有回执</div></details>'"),
)
_T1_IGN_WHY = u"折体（`details.eng` 之体）⇒ 屏外 ⇒ 真源 ⛔ 丢 ／ 工程之据 ⛔ 上屏"
_T1_BLOCK_LABEL = u"send:'发送（502）' }"

#: ⭐⭐ 行 `title`（`ask({rows:…})` 之第 3 元）之**原字**落处 ⇒ **屏外**
#:   （pm_2108 §三ⓜ · 承 pm_2106 §三.4「折内 ／ `title` 之落处 ⇒ 入 `_ign`（逐字 ＋ 书其由）」）
_T1_TITLE_IGN = (
    (u"['凭什么', refLine(), '工程之据：原字 sha16", u"（凭据之指印）'],"),
    (u"['引哪封来信', refLine(), '工程之据：原字 sha16", u"（凭据之指印）'],"),
)



def _ifuncs(s: str) -> list:
    u"""**缩进之函**（IIFE 之内）⇒ `[(名, 起, 止)]`（花括号配平 · 同 `tf._funcs`）。

    ⚠ `tf._funcs` 之正则以 `^function` 起 ⇒ 缩进之函（本轮之 T1 诸函）**一条也收不着**。
    """
    out = []
    for m in re.finditer(r"(?:^|\n)[ \t]*(?:async[ \t]+)?function[ \t]+(\w+)[ \t]*\(", s):
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


def _find(s: str, a: str, b: str, frm: int = 0) -> tuple:
    u"""同 `_anchor` 而**⛔ 断言**（缺 ⇒ `(-1, -1)`）—— 俾反控之变体（其锚已被去）得**真扫**。"""
    i = s.find(a, frm)
    if i < 0:
        return (-1, -1)
    j = s.find(b, i)
    if j < 0:
        return (-1, -1)
    return (i, j + len(b))


def _spans(sys_src: str, self_src: str) -> dict:
    u"""本批所动之区间（⛔ 全件扫 —— 全件扫必咬他面无涉之件 ⇒ 越批之界）。"""
    fns = _FUNCS(sys_src)
    sys_sp = [_FSPAN(fns, n) for n in
              (u"paSysHuman", u"paSysSrcHuman", u"paSysItemsHtml", u"paSysPanelHtml",
               u"paSysActBoxHtml", u"paSysFoldReadingsHtml", u"paSysRender")]
    self_sp = [_FSPAN(_FUNCS(self_src), u"paSelfAskStatHtml")]
    self_sp.append(_ANCHOR(self_src, u"function loadDecision(", u"function flat(v){"))
    # 缩进之函（IIFE 之内）⇒ 以锚取区间
    self_sp.append(_ANCHOR(self_src, u"  function probeBackend(){", u"  function go(){"))
    # `#paHistList` 之段（IIFE ⇒ 以注释锚取）
    self_sp.append(_ANCHOR(self_src, u"/* ================= 六 · 7 · 会话历史",
                           u"window.paHistInfo = function()"))
    # ⭐⭐ T1 交付面（pm_2104 §四.4⒝）：缩进之函 ＋ `BLOCK_LABEL`（平文之闸名 · 丁2）
    ifns = _ifuncs(self_src)
    for n in _T1_SCOPE_FNS:
        self_sp.append(_FSPAN(ifns, n))
    for n in _PLAN_SCOPE_FNS:
        self_sp.append(_FSPAN(ifns, n))
    self_sp.append(_find(self_src, u"var BLOCK_LABEL = {", _T1_BLOCK_LABEL))
    ign = [(_ANCHOR(self_src, u"      box.innerHTML = '<summary title=\"工程之据：真源",
                    u".jsonl（append-only）")),
           (_ANCHOR(self_src, u'<details class="eng" id="paAskStatBox">',
                    u"paSelfModeDiagHtml()\n    + '</div></details>'"))]
    for (a, b) in _T1_IGN:
        ign.append(_find(self_src, a, b))
    for (a, b) in _T1_TITLE_IGN:
        ign.append(_find(self_src, a, b))
    return {"sys": sys_sp, "self": self_sp, "ign": ign}


def scan(src: str, spans: list, ign: list) -> dict:
    r"""纯扫（⛔ 触盘）：`{kept, hits}` —— `kept` ＝ scope 内之屏上字面。

    ⚠ **先解码**（`_unesc`）：`_literals` 所给者 ＝ 源码之**原文**（`\u26d4` 之族）
      ⇒ ⛔ 解码则凡以 `\uXXXX` 写就之字面得漏（pm_2104 §四.4「本批之真洞」之一）。
    """
    fns = _FUNCS(src) + _ifuncs(src)
    kept, hits = [], []
    lits = _LITS(src)
    #: ⭐⭐ 界之正（pm_2108 §三.1）：语句之界（`;{}`）⇒ 唯**字面之外**者得为界。
    #:   ⓜ 旧法（`rfind` 直索）⇒ 若前一字面之内含 `;`（`style="font-size:10.5px;color:…"`）
    #:     ⇒ 界落**字面之中** ⇒ `pre_raw` 之引号奇偶判误 ⇒ 其**后**之屏上字面得漏
    #:     （一手之例：`sys.js` 之「这一段就是上面七面读数…（唯前端…）」）。
    #:   ⓝ 我先一手之误（以「前一字面之末」为界）⇒ 界**太近** ⇒ 吞 `say(` ／
    #:     `setAttribute('title',` 之上下文 ⇒ 门后流水 ／ `title` 之字得**误咬**（假红）。
    inside = bytearray(len(src))
    for (_p, _c) in lits:
        _L = min(len(_c) + 2, len(src) - _p)
        inside[_p:_p + _L] = b"\x01" * _L
    divs = [i for i, ch in enumerate(src) if ch in _STMT_END and not inside[i]]
    for (pos, txt) in lits:
        if not any(a >= 0 and a <= pos < b for (a, b) in spans):
            continue
        if any(a >= 0 and a <= pos < b for (a, b) in ign):
            continue
        t = _unesc(txt)
        if not _CJK.search(t):
            continue
        _j = bisect.bisect_left(divs, pos)
        k = divs[_j - 1] if _j else -1
        pre_raw = src[k + 1:pos]
        #: ⭐ 引号奇偶之旧判（`pre_raw.count('"') % 2`）⇒ **去**。
        #:   其原意：探「界落在一字面之内」。今界已为**字面之外**之 `;{}`
        #:   ⇒ 其意已空；反成**假阴**之源：前文若含「字面内不配对之 `"`」（如 `'\u3002</div>'` 之族 · 或属性内之 `"`）
        #:   ⇒ 其后之屏上字面得漏（一手之例：收口之「引哪封来信 · sha16」标、`S2 ⓜ` 之 `⛔`）。
        #:   ⚠ 去之得多而 ⛔ 得少 —— 后之 `_SCREENPART` 自会剔屏外之属性（同时为反控之根）。
        pre = _STRIP(pre_raw)
        if re.search(r"\.title\s*=", pre):
            continue
        if re.search(r"setAttribute\(\s*['\"]title['\"]\s*,", pre):
            continue
        # ⭐ 门后之流水（`say(` ／ `addLog(`）⇒ ⛔ 上屏（⛔ 本批所计 · 另族候议 · pm_2104 §四.1「并报」）
        if re.search(r"\b(?:say|addLog)\s*\(", pre):
            continue
        if _NEEDLE.search(pre.rstrip()):
            continue
        t = _SCREENPART(t)
        kept.append((pos, _OWNER(fns, pos), t))
        b = _bad(t)
        if b:
            hits.append({"line": src[:pos].count("\n") + 1, "fn": _OWNER(fns, pos),
                         "bad": b, "t": t})
    return {"kept": kept, "hits": hits}


_SP = _spans(_read(SYS), _read(SELF))


# ============================== S0 ／ S1 ／ S1b · 静态 ==============================
def test_S0_射程非空():
    u"""⛔ 空跑（防「齿假绿」）：诸锚须**皆在** ∧ 屏上字面须成量。"""
    for nm, spans in ((u"sys.js", _SP["sys"]), (u"selfdesc.js", _SP["self"])):
        miss = [i for i, (a, _b) in enumerate(spans) if a < 0]
        assert miss == [], u"%s：scope 之锚 ⛔ 在（齿将空跑）：%r" % (nm, miss)
    n = len(scan(_read(SYS), _SP["sys"], _SP["ign"])["kept"])
    assert n >= 40, u"`sys.js` scope 内之屏上字面过少（%d）⇒ 射程疑失" % n
    n2 = len(scan(_read(SELF), _SP["self"], _SP["ign"])["kept"])
    assert n2 >= 40, u"`selfdesc.js` scope 内之屏上字面过少（%d）⇒ 射程疑失" % n2


@pytest.mark.parametrize("which", [u"sys", u"self"])
def test_S1_屏上字面唯人话(which):
    u"""pm_2095 §一 ／ §二：scope 内之**屏上**字面 ⛔ 载禁记号 ∧ ⛔ 载端字段名。"""
    src = _read(SYS if which == u"sys" else SELF)
    s = scan(src, _SP[which], _SP["ign"])
    assert s["hits"] == [], u"屏上字面见犯字 %s" % (
        u"；".join(u"%s:%d（%s）%s %r" % (which, h["line"], h["fn"], h["bad"], h["t"][:60])
                   for h in s["hits"][:8]),)


def test_S1b_逐字文案():
    u"""本批之定形辞（源码级 · ⛔ 触浏览器）。"""
    sys_js, self_js, html = _read(SYS), _read(SELF), _read(PAGEHTML)
    # ⒜ sys.js —— 端所给之 `⛔` ⇒ 人话（「不」之族）∧ 原字入门后之 `title` ／ `data-raw`
    assert u"function paSysHuman(s){" in sys_js, u"人话化之函须在（一处定形）"
    assert u"PA_SYS_RAW = '" in sys_js, u"原字之标须在"
    assert u"ta.setAttribute('data-raw', raw);" in sys_js, u"全文块之原字须可寻得（⛔ 丢真源）"
    assert u"'\\u4e0d\\u5916\\u53d1'" in sys_js, u"`⛔ 出机` ⇒ `不外发`（承 pm_2081 §二 名之一处）"
    assert u"PA_SYS_RAW + (it['\u4eba\u8bdd']" in sys_js, u"`人话` 之原字须入 `title`"
    assert u"PA_SYS_RAW + (it['\u8bfb\u6570']" in sys_js, u"`读数` 之原字须入 `title`"
    # ⒝ selfdesc.js —— 折首之盘径 ⇒ `title`（屏上唯人话）
    assert u"\u2463 \u7eed \u00b7 \u4f1a\u8bdd\u5386\u53f2\uff08\u70b9\u5f00\u5373\u89c1" in self_js, \
        u"`#paHistList` 之折首须净（屏上唯人话）"
    assert u"function shortSid(k){" in self_js, u"短形之算须**一处出**（调 `window.paShortSid`）"
    assert u"hEsc(shortSid(sid))" in self_js, u"会话 id 之短形须**留屏**（可辨 · 承裁⒞）"
    assert u"title=\"\u5de5\u7a0b\u4e4b\u636e\uff1a\u4f1a\u8bdd ' + hEsc(sid)" in self_js, \
        u"全 id 须入本行 `title`（⛔ 丢真源）"
    # ⒞ pa.html —— 诊断区之容器 ⇒ `details.eng`
    assert u'<details class="eng" id="paAboutFold"><summary>\u8bca\u65ad\u4e0e\u6765\u6e90' in html, \
        u"诊断区（`#paAboutBody`）之容器须折（承 pm_2095 裁⒜）"
    assert u'<div class="about" id="paAboutBody">' in html, u"`#paAboutBody` 须仍在（真源 ⛔ 丢）"


#: 原字之题（逐字全）—— `原字：后端：HTTP <码>`（承 pm_2097 §三.2：「原字」之义 ＝ 逐字之原 ⇒ ⛔ 半截）
_RAW_TITLE_FULL = u"\u539f\u5b57\uff1a\u540e\u7aef\uff1aHTTP "
_RAW_TITLE_HALF = u"\u539f\u5b57\uff1a\u540e\u7aef\uff1a"


def raw_title_bad(src: str) -> list:
    u"""原字之题之判（纯函数 ⇒ 供反控喂变体）⇒ 犯者之列。"""
    out = []
    if _RAW_TITLE_FULL not in src:
        out.append(u"原字之题 ⛔ 逐字全（缺：`" + _RAW_TITLE_FULL + u"`）")
    return out


def test_S1c_原字须逐字全入_title():
    u"""pm_2097 §三.2（准即办）：`#paT1Panel` 之「与对端之通」——
    屏上唯人话（`<status>（照实）`）∧ 原字逐字全入 `title`⇒ 可查。"""
    src = _read(SELF)
    assert raw_title_bad(src) == [], u"；".join(raw_title_bad(src))
    # 正控：三支同法（一处定形：唯 paint 写之）
    assert u"function paint(disp, st){" in src, u"一处定形之函须在"
    assert src.count(u"el.textContent = disp;") == 1, u"写屏须唯一处"
    # 反控（防假牙）：造半截 ⇒ 必咬
    assert raw_title_bad(src.replace(_RAW_TITLE_FULL, _RAW_TITLE_HALF)) != [], u"反控：半截 ⇒ 须咬"
    assert src.replace(_RAW_TITLE_FULL, _RAW_TITLE_HALF) != src, u"反控之锚 ⛔ 在（将空跑）"


# ============================== S2 · 反控（防「假牙」） ==============================
def test_S2_反控必咬且不妄咬():
    u"""造病 ⇒ **必咬**；造于合法之地（`title` ／ 真 id ／ 盘符）⇒ **⛔ 咬**。"""
    src = _read(SYS)
    base = scan(src, _SP["sys"], _SP["ign"])
    assert base["hits"] == [], u"前提：正形须先净"

    # ⒜ 平文之 `⛔` ⇒ 必咬
    OEM = u"'\\u3002</div>'"
    a0 = u"'\">清之险：' + paSysEsc(paSysHuman(it['清之险']))"
    mut = src.replace(a0, u"'\">清之险：\u26d4 ' + paSysEsc(paSysHuman(it['清之险']))", 1)
    assert mut != src, u"锚 ⛔ 在（反控将空跑）：{0}".format(a0)
    h = scan(mut, _SP["sys"], _SP["ign"])["hits"]
    assert h and any(u"cross" in x["bad"] for x in h), u"平文造 `⛔` ⇒ 必咬（⛔ 假绿）"

    # ⒝ 平文之端字段名 ⇒ 必咬
    a1 = u"'\"\u3002清之险：' + paSysEsc(paSysHuman(it['清之险']))"
    mut = src.replace(u"清之险：' + paSysEsc(paSysHuman(it['清之险']))",
                      u"清之险（caps）：' + paSysEsc(paSysHuman(it['清之险']))", 1)
    assert mut != src
    h = scan(mut, _SP["sys"], _SP["ign"])["hits"]
    assert h and any(u"fieldname" in x["bad"] for x in h), u"平文造端字段名 ⇒ 必咬（⛔ 假绿）"

    # ⒞ `title="…"` 之属性（屏外之地）⇒ ⛔ 咬
    a2 = u"title=\"' + paSysEsc(PA_SYS_RAW + it['人话']"
    mut = src.replace(u"PA_SYS_RAW + (it['人话']", u"PA_SYS_RAW + 'level ' + (it['人话']", 1)
    assert mut != src, u"锚 ⛔ 在：{0}".format(a2)
    assert scan(mut, _SP["sys"], _SP["ign"])["hits"] == [], u"`title` 属性（屏外）⇒ ⛔ 得咬"

    # ⒟ 端给之真 id ／ 盘符（白名单 · 照实留屏）⇒ ⛔ 咬
    probe = scan(u"function paSysX(){ return '\u76d8\u7b26 C:\\Users \\u4f1a\u8bdd web_1791480495074 ds_chat'; }",
                 [], [])
    assert probe["hits"] == [], u"盘符 ／ 端给之真 id ⇒ ⛔ 得咬"


# ============================== S4 · 次批余数（动态辞 · 逐字 · ⛔ 触浏览器） ==============================
#: ⒜ 真源族之残二处 —— `files.js`（承 pm_2101 §一.2 ＋ pm_2102 §二.1 之「其径 ⇒ 路径」）
_SRC_FILES_PAIRS = (
    (u"'来源：本机工作区文件（悬停本行见路径）'",
     u"'来源：本机工作区文件（真源与径 ⇒ 悬停本行即见）'"),
)
#: ⒜ 真源族之残二处 —— `selfdesc.js`（承 pm_2101 §一.2 ＋ pm_2102 §二.2 之「照呈」）
_SRC_SELF_PAIRS = (
    (u"（另列：检索面 —— 悬停本行即见）",
     u"（另列：检索面 —— 真源悬停本行即见）"),
)
FILES = ROOT / "web" / "pa" / "faces" / "files.js"

#: ⒝ `#paT1Panel` 之余数（动态辞 · 承 pm_2101 §二 之三表 ＋ pm_2102 §二.3 ／ §一.4 之二改）
#: 对以（新 · 屏上人话，旧 · 含禁记号 ／ 工程语）为形；反控：新 ⇒ 旧 必咬。
_T1_PAIRS = (
    (u"'交付：无交办 ⇒ 未发'", u"'交付：⛔ 无交办 ⇒ 未发'"),
    (u"'交付：收件人为空 ⇒ 未发（不会开空件）'", u"'交付：⛔ 收件人为空 ⇒ 未发（⛔ 开空件）'"),
    (u"'交付：未拍板 ⇒ 本面不发 · 正在留下「停手」之痕…'",
     u"'交付：⛔ 未拍板（无 decision_id）⇒ 前端不发（「前端之弱保证」）· 正在落「停手」留痕…'"),
    (u"'未拍板 —— 本面之弱保证（未批即不发）；'",
     u"'未拍板（无 decision_id）—— 前端之弱保证（未批 ⇒ 不发）；'"),
    (u"真闸在对端（发信之路内 · 缺拍板 ⇒ 403 宁拒）",
     u"真闸在后端（发信路由内 · 缺 decision_id ⇒ 403 fail-closed）"),
    (u"' · 对端此路将 403 宁拒 · 已出失败回执 · 报给 '",
     u"（「前端之弱保证」）· 后端此路将 403 fail-closed · 已出失败回执 · 报给 "),
    (u"（留痕路径 ", u"（后端 deliver/stop · 留痕径 "),
    (u"'交付：停手卡不可用 ⇒ 未发（宁不发）'",
     u"'交付：⛔ 停手卡不可用（paStopAsk 未就绪）⇒ 未发（fail-closed）'"),
    (u"title: '停手：即将以你名义发信（交付）',", u"title: '⛔ 停手：即将以你名义发信（T1 交付）',"),
    (u"'我方闭环（真闸在对端）'", u"'POST /v9/pa/deliver/mail（我方闭环 · 后端真闸）'"),
    (u"'未取得（发后之回执才给：用时 ／ 字节 ／ 词元 ／ 每件花费 ⇒ 不由本面估）'",
     u"'未取得（后端于发后之回执给 wall_s ／ bytes ／ tokens ／ $/件 ⇒ ⛔ 前端估）'"),
    (u"'（停手时由对端定 · 其「报给谁」恒有）'",
     u"'（停手时由后端 POST /v9/pa/deliver/stop 定 · 其「报给谁」恒有字段）'"),
    (u"'未批 ⇒ 本面不发（本面之弱保证）⇔ 对端会拒（真闸 · 在发信之路内）'",
     u"'未批 ⇒ 前端不发（前端之弱保证）⇔ 后端拒执（真闸 · 在发信路由内）'"),
    (u"'本卡即授权点 ⇒ 点「本次发送」落真拍板再发'",
     u"'本卡即授权点 ⇒ 点「本次发送」落真拍板（POST /v9/pa/decision）再发'"),
    (u"stopTrace('授权点（取消 ⇒ 未授权 ⇒ 未发）', tid, b)",
     u"stopTrace('授权点（老板取消 ⇒ 未授权 ⇒ ⛔ 未发）', tid, b)"),
    (u"showFail('授权点（取消 ⇒ 未授权 ⇒ 未发）', who, axis,",
     u"showFail('授权点（老板取消 ⇒ 未授权 ⇒ ⛔ 未发）', who, axis,"),
    (u"'点了「❌ 取消」⇒ 未授权 ⇒ 未发（此刻后悔 ＝ 什么都不发生）'",
     u"'老板点了「❌ 取消」⇒ 未授权 ⇒ ⛔ 未发（此刻后悔 ＝ 什么都不发生）'"),
    (u"'交付：已取消（未批即未动 · 未发）· 停手留痕之「报给谁」' + who;",
     u"'交付：已取消（未批即未动 · ⛔ 未发）· 停手留痕之「报给谁」' + who\n            + '（面：' + axis + '）';"),
    (u"'交付：授权未落（对端未给拍板）⇒ 未发（宁不发）'",
     u"'交付：⛔ 授权未落（后端未给 decision_id）⇒ 未发（fail-closed）'"),
    (u"'一句话交办：交办为空 ⇒ 未提交（不会开空件）'",
     u"'一句话交办：⛔ 交办为空 ⇒ 未提交（⛔ 开空件）'"),
    (u"'一句话交办：对端未给计划 ⇒ 停在授权点之前（不会自己编步骤）'",
     u"'一句话交办：⛔ 后端未给计划 ⇒ 停在授权点之前（⛔ 前端编步骤）'"),
    (u"'一句话交办：收件人为空 ⇒ 未到授权点'", u"'一句话交办：⛔ 收件人为空 ⇒ 未到授权点'"),
    (u"title=\"原字：HTTP ' + http + '\"><b>回执（对端 · ' + http + '）</b>",
     u"\"><b>回执（后端 · HTTP ' + http + '）</b>"),
    (u"件之刻（对端回执 · 不是本轮）", u"件之刻（后端回执 · ⛔ 本轮刻）"),
    (u"缺（对端回执未给「刻」）", u"缺（后端回执未给「刻」）"),
    (u"title=\"真源：POST /v9/pa/deliver/mail 回执\">件号 ' + H(tid) + ' · 来源：对端回执",
     u"\">task_id ' + H(tid) + ' · 真源：POST /v9/pa/deliver/mail 回执"),
    (u"'（四件 ＋ 引哪封来信 ＋ 件之刻 ＋ 每件花费 皆对端取 · 不由本面估）'",
     u"'（四件 ＋ 引哪封来信 ＋ 件之刻 ＋ $/件 皆后端取 · ⛔ 前端估）'"),
    (u"('请求未送达（' + netErr + '）· 不等于未发')", u"('请求未送达（' + netErr + '）· ⛔ 不等于未发')"),
    (u"⇒ 对端宁拒（真闸）", u"⇒ 后端 fail-closed（真闸）"),
    (u"⇒ 同一件已交过（不重发）", u"⇒ 幂等拒（task_id 已用于另一交办）"),
    (u"? '对端回执'", u"? '后端回执'"),
    (u"? '对端之留痕行'", u"? '后端 deliver/mail 留痕行'"),
    (u"? '对端之「停手收件人」'", u"? '后端 policy.stop_to'"),
    (u"\\uff09\\u21d2 \\u672a\\u62cd\\u677f", u"\\uff09\\u21d2 \\u26d4 \\u672a\\u62cd\\u677f"),
)


def _pairs_bad(src: str, pairs) -> list:
    u"""逐字之判（纯函数 ⇒ 供反控喂变体）：新辞须**一处定形** ∧ 旧辞须 **尽除**。"""
    out = []
    for (new, old) in pairs:
        c = src.count(new)
        if c != 1:
            out.append(u"新辞之数 ⛔ ≠1（%d）：%r" % (c, new))
        if old in src:
            out.append(u"旧辞未除：%r" % (old,))
    return out


def test_S4_次批余数之屏净与反控():
    u"""pm_2101 §一.2 ／ §二（三表）＋ pm_2102 §二（二改 ／ 一处定形）：
    ⒜ 真源族之残二处 ＋ ⒝ `#paT1Panel` 之余数（动态辞）⇒ 屏上唯人话 ∧ 禁记号 ／ 工程语 ⛔ 现。
    ⭐ 形：逐字锚（一处定形）＋ 反控（新 ⇒ 旧 必咬）—— 承 `test_S1c` 之例。
    """
    self_js = _read(SELF)
    files_js = _read(FILES)
    bad = (_pairs_bad(files_js, _SRC_FILES_PAIRS)
           + _pairs_bad(self_js, _SRC_SELF_PAIRS)
           + _pairs_bad(self_js, _T1_PAIRS))
    assert bad == [], u"；".join(bad)
    for (new, old) in _T1_PAIRS:
        mut = self_js.replace(new, old, 1)
        assert mut != self_js, u"反控之锚 ⛔ 在（将空跑）：%r" % (new,)
        assert _pairs_bad(mut, _T1_PAIRS) != [], u"反控：还旧形 ⇒ 须咬：%r" % (new,)
    for (new, old) in _SRC_FILES_PAIRS + _SRC_SELF_PAIRS:
        fsrc = files_js if new in files_js else self_js
        mut = fsrc.replace(new, old, 1)
        assert mut != fsrc, u"反控之锚 ⛔ 在：%r" % (new,)
        assert _pairs_bad(mut, _SRC_FILES_PAIRS + _SRC_SELF_PAIRS) != [], u"反控（真源族）：须咬：%r" % (new,)


# ============================== S6 · 本批逐字文案（静态 · ⛔ 触浏览器） ==============================
#: ⭐⭐ 本批（pm_2104 §四.1 丁 ／ §四.2 自逮 ／ 另逮 ／ §四.3 ⑧ ／ pm_2106 §三.2）之逐字。
#: 形 ＝ `(新, 旧, 定形之数)`：新辞须**恰 n 处**（一处定形 · 承 `test_S1c`）∧ 旧辞须**尽除**。
#: ⚠ `对端 deliver/stop` 合 `n=2`（`whoAxis` 之正控 ／ 取消 二支 —— 一处定形之辞 · 二处落点）。
_T1_PAIRS2 = (
    # ⒜ 真源族之残（refLine ／ spendLine ／ costLine）
    (u"'缺（未附原信 · 对端回执同显「缺」）'",
     u"'缺（未附原信 ⇒ ⛔ 装已附 · 后端回执同显「缺」）'", 1),
    (u"'未取得（对端未给「花了多少」）'",
     u"'未取得（后端未给 花了多少 键）'", 1),
    (u"'用时 ' + numOr(s['wall_s'], ' 秒') + ' · 入 ' + numOr(b['in'], ' 字节') + ' ／ 出 ' + numOr(b['out'], ' 字节')",
     u"'wall_s ' + numOr(s['wall_s'], ' 秒') + ' · 入 ' + numOr(b['in'], ' B') + ' ／ 出 ' + numOr(b['out'], ' B')", 1),
    (u"(' · 取自 ' + String(s['source']))", u"(' · 源 ' + String(s['source']))", 1),
    (u"(' · 量法 ' + String(s['读数之器']))", u"(' · 器 ' + String(s['读数之器']))", 1),
    (u"'未取得（对端未给「成本」）'", u"'未取得（后端未给 成本 键）'", 1),
    (u"'每件 ' + numOr(c['单价_元每件']) + ' ' + String(c['币'] || 'CNY') + ' · 总 '",
     u"'单价 ' + numOr(c['单价_元每件']) + ' ' + String(c['币'] || 'CNY') + ' ／ 件 · 总 '", 1),
    (u"(' · 词元 无（'", u"(' · tokens 无（'", 1),
    (u"(' · 词元 ' + c['tokens'])", u"(' · tokens ' + c['tokens'])", 1),
    # ⒝ 闸名（`BLOCK_LABEL` · 丁2）
    (u"decision_gate:'拍板闸（未拍板 · 403 宁拒）'",
     u"decision_gate:'拍板闸（decision_id · 403 fail-closed）'", 1),
    (u"idem:'幂等闸（同一件已交过 · 409）'",
     u"idem:'幂等闸（同 task_id 异文 · 409）'", 1),
    (u"recipient_scope:'收件人闸（超出允许范围 · 403）'",
     u"recipient_scope:'收件人闸（甲形限域 · 403）'", 1),
    # ⒞ 拍板（`loadDecision` ／ `doAdopt`）
    (u"对端还没有「采纳」之拍板（' + r.status + '）⇒ 照实（不由本面编号）",
     u"对端还没有「采纳」之拍板（HTTP ' + r.status + '）⇒ 照实（不由本面编号）", 1),
    (u"'拍板：无交办 ⇒ 未拍板'", u"'拍板：⛔ 无交办 ⇒ 未拍板'", 1),
    (u"'拍板：请求中…'", u"'拍板：请求中…（POST /v9/pa/decision · 采纳）'", 1),
    (u"'拍板：对端未给拍板件号（'", u"'拍板：后端未给 decision_id（HTTP '", 1),
    (u"'本面自拍 · 件之刻 '", u"'本面自拍（POST /v9/pa/decision）· 件之刻 '", 1),
    (u"'缺（对端未给「刻」）⇒ 本轮读数刻 '", u"'缺（后端未给 ts）⇒ 本轮读数刻 '", 1),
    (u"'拍板：已记入对端之账 · 件号 '", u"'拍板：已落 decision_log · id '", 1),
    # ⒟ 停手卡之诸行（`openAuthzCard`）
    (u"'对端 deliver/stop · '", u"'后端 deliver/stop · '", 2),
    (u"['件号', tid]", u"['task_id', tid]", 1),
    (u"['通道', '我方闭环（真闸在对端）', 'POST /v9/pa/deliver/mail']",
     u"['通道', '我方闭环（真闸在对端）']", 1),
    (u"['报给谁', stopTo() + '（停手时由对端定 · 其「报给谁」恒有）', 'POST /v9/pa/deliver/stop']",
     u"['报给谁', stopTo() + '（停手时由对端定 · 其「报给谁」恒有）']", 1),
    (u"('拍板件号 ' + decId())", u"('decision_id ' + decId())", 1),
    # ⒠ 交付（`send` ／ `fourItems` ／ `failHTML` ／ `renderReceipt`）
    (u"'交付：发送中…'", u"'交付：发送中…（POST /v9/pa/deliver/mail）· task_id '", 1),
    (u"'未取得（对端未给此件）'", u"'未取得（后端未给此件）'", 1),
    (u"['每件花费', costLine(src)]", u"['$/件', costLine(src)]", 1),
    (u"'<div><b>件号</b>：' + H(tid || '—')", u"'<div><b>task_id</b>：' + H(tid || '—')", 1),
    (u"'<div><b>每件花费</b>：' + H(costLine(rco))", u"'<div><b>$/件</b>：' + H(costLine(rco))", 1),
    (u"' ⇒ 对端未接此路'", u"' ⇒ 后端路由未接（器未接之证）'", 1),
    (u"'<div><b>件之刻（对端回执）</b>：'", u"'<div><b>件之刻（后端回执）</b>：'", 1),
    (u"'<div><b>每件花费</b>：' + H(rc ? costLine(rc)", u"'<div><b>$/件</b>：' + H(rc ? costLine(rc)", 1),
    # ⒡ T1 面（折首 ／ 静态平文）＋ 丁10（对话面之去其主）
    (u">交付面</b>（发信 · 由 PA 自己送出）", u">T1 交付面</b>（发信 · 我方闭环）", 1),
    (u"' ⇔ <b>对端会拒</b>（真闸 · 在真发那一步）—— '", u"' ⇔ <b>对端会拒</b>（真闸 · 在发信路由内）—— '", 1),
    (u"引哪封来信 · 件号（凭什么 · 来信之件号）", u"引哪封来信 · 件号（凭什么 · C1）", 1),
    (u"'⚠ 这次没送到 —— 「PA 对话通道暂不可用」（接口未挂载）；检索侧亦未命中 ⇒ 两路皆不通。可：① 再发一次 ② 把本句发我，我查通道挂载。'",
     u"'⚠ 这次没送到 —— 后端说「PA 对话通道暂不可用」（404：接口未挂载）；检索侧亦未命中 ⇒ 两路皆不通。可：① 再发一次 ② 把本句发我，我查后端通道挂载。'", 1),
)
#: ⭐ 本批**新加**之力（⛔ 旧形可对）—— 惟须在 ∧ **恰一处**（真源 ⛔ 丢 ／ 其路须真行）
_T1_ADD2 = (
    (u"title=\"工程之据：T1 交付面\">交付面</b>", 1),
    (u"src.title = '原字：HTTP ' + r.status", 1),
    (u"out.title = '工程之据：POST /v9/pa/deliver/mail · 件号 ' + tid", 1),
    (u"out.title = '工程之据：POST /v9/pa/decision · 采纳'", 1),
    (u"_ds.title = '工程之据：POST /v9/pa/decision · 承 pm_刀11p §二.4'", 1),
    (u"var okSent = false;", 1),
    (u"okSent = (r.status >= 200 && r.status < 300) && d && d.ok !== false && d.success !== false;", 1),
    (u"'交付：已送出 · 回执见下'", 1),
    (u"'交付：未送出 ⇒ 见下之回执'", 1),
    (u"var tip = (r[2] != null && String(r[2]))", 1),
    (u"document.getElementById('paEngNote')", 1),
    (u"d.id = 'paEngNote';", 1),
    (u"setAttribute('data-engskip', '1')", 1),
)
MORE = ROOT / "web" / "pa" / "faces" / "more.js"
#: ⒢（`more.js` · 上屏之支路器名 ⇒ 人话 · pm_2104 §四.3 ⑧）
_MORE_PAIRS2 = ((u"' · 源：界面快照'", u"' · 源 ui_state'", 1),)


def _pairs2_bad(src, pairs) -> list:
    u"""逐字之判（纯函数 ⇒ 供反控喂变体）：新辞须**恰 n 处**（一处定形）∧ 旧辞须**尽除**。"""
    out = []
    for (new, old, n) in pairs:
        c = src.count(new)
        if c != n:
            out.append(u"新辞之数 ⛔ ≠%d（%d）：%r" % (n, c, new[:60]))
        if old in src:
            out.append(u"旧辞未除：%r" % (old[:60],))
    return out


def test_S6_本批逐字文案与反控():
    u"""pm_2104 §四.1（丁全表）＋ §四.2（自逮 5 ／ 另逮 2）＋ pm_2106 §三.2（丁10 去其主）＋ §四.3 ⑧：
    本批所净之诸处 ⇒ **屏上唯人话** ∧ 工程之据 ⇒ `title` ／ 折体（⛔ 丢真源）。
    ⭐ 形：逐字锚（一处定形）＋ 反控（新 ⇒ 旧 必咬）—— 承 `test_S1c` ／ `test_S4` 之例。
    """
    self_js, more_js = _read(SELF), _read(MORE)
    allp = _T1_PAIRS2 + _MORE_PAIRS2
    bad = _pairs2_bad(self_js, _T1_PAIRS2) + _pairs2_bad(more_js, _MORE_PAIRS2)
    for (lit, n) in _T1_ADD2:
        c = self_js.count(lit)
        if c != n:
            bad.append(u"本批之新增 ⛔ 见 ／ 数异（%d≠%d）：%r" % (c, n, lit[:60]))
    assert bad == [], u"；".join(bad)
    # 反控（防「假牙」）：还旧形 ⇒ 必咬
    for (new, old, _n) in allp:
        src = more_js if new in more_js else self_js
        mut = src.replace(new, old, 1)
        assert mut != src, u"反控之锚 ⛔ 在（将空跑）：%r" % (new,)
        assert _pairs2_bad(mut, allp) != [], u"反控：还旧形 ⇒ 须咬：%r" % (new,)


# ============================== S7 · 射程之反控锚（静态 · ⛔ 触浏览器） ==============================
#: ⭐ 折体之起（含其 `engbody` 之标）—— 去其标 ＝ **把折内之字移入平文**（pm_2106 §三.4 之反控）
_FOLD_WRAP = u"'<div class=\"engbody\">体：POST"
_PLAIN_WRAP = u"'体：POST"
#: ⭐ 本批所净之一（逐字 · 其平文曾上屏）—— 还旧形 ⇒ **必咬**（证射程真罩其落处 ／ 解码真行）
_SCAN_ANCHORS2 = (
    (u"'交付：已送出 · 回执见下'",
     u"'交付：发送中…（POST /v9/pa/deliver/mail）· task_id '"),
    (u"'缺（未附原信 · 对端回执同显「缺」）'",
     u"'缺（未附原信 ⇒ ⛔ 装已附 · 后端回执同显「缺」）'"),
    (u"'未取得（对端未给此件）'",
     u"'未取得（后端未给此件）'"),
)


def test_S7_射程之反控锚():
    u"""pm_2104 §四.4（射程之扩）＋ pm_2106 §三.4（须防「折内之字」误咬）：
    ① 正形须先净（前提）② **折体之明标恰在**（其缺 ⇒ 反控将空跑）③ 把折体之字**移入平文**（去其标）
    ⇒ **必咬**（证明标 ⛔ 空跑 ／ 亦证「⛔ 逼删真源」之险已被扼）④ 本批所净之诸处 ⇒ 还旧形 ⇒ **必咬**。
    """
    src, syssrc = _read(SELF), _read(SYS)
    assert scan(src, _SP["self"], _SP["ign"])["hits"] == [], u"前提：正形须先净"
    miss = [i for i, (a, _b) in enumerate(_SP["ign"]) if a < 0]
    assert miss == [], u"`ign` 之明标 ⛔ 在（反控将空跑）：%r" % (miss,)
    # ① 折体之字 ⇒ 移入平文（去其折体之标）⇒ 必咬
    mut = src.replace(_FOLD_WRAP, _PLAIN_WRAP, 1)
    assert mut != src, u"折体之锚 ⛔ 在（反控将空跑）：%r" % (_FOLD_WRAP,)
    sp = _spans(syssrc, mut)
    assert scan(mut, sp["self"], sp["ign"])["hits"], \
        u"折体之字移入平文 ⇒ 必咬（⛔ 则 `_ign` 之明标为「免死金牌」）"
    # ② 本批所净之诸处 ⇒ 还旧形 ⇒ 必咬
    for (new, old) in _SCAN_ANCHORS2:
        m2 = src.replace(new, old, 1)
        assert m2 != src, u"反控之锚 ⛔ 在（将空跑）：%r" % (new,)
        assert scan(m2, _SP["self"], _SP["ign"])["hits"], u"还旧形 ⇒ 必咬（射程未罩）：%r" % (new,)

# ============================== S3 · 真渲齿（真 Chrome × CDP） ==============================
GATEWAY = int(os.environ.get("PA_GATEWAY_PORT", "5102"))

#: ⚠ 活态之 `under` ＝ **已知工程标识之列**（⛔ 通配 `x_y`）—— 通配于**活态**必咬端给之真件名
#:   （体检之盘径夹名 · 承 pm_2095 §二.2「盘符准留」· 我一手验）；通配之网留于**静态之齿**（源码字面 · 真件名 ⛔ 出）。
#: ⭐⭐ pm_2108 §二.3ⓜ：该「已知工程标识之列」⇒ **一处定形**（一常量 · ⛔ 散书）—— 活态（`_PROBE`）唯由此派生。
#: ⭐ pm_2108 §二.3ⓝ：**新端字段名之族 ⇒ 入此表**（与静态之 `IDNAMES` 各司其职：静态取源码之字，活态取 DOM 之字）。
KNOWN_ENG_IDS = (u"task_id", u"decision_id", u"wall_s", u"tokens", u"fail_closed",
                 u"ui_state", u"agent_state", u"deliver_stop", u"body_md", u"user_id",
                 u"sha16", u"task_type", u"source")
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
  function isEng(k){ var c=' ' + String(k.className||'') + ' '; return c.indexOf(' eng ')>=0 || k.hasAttribute('data-engskip'); }
  var R = {cross:/\u26d4/g, star:/\*\*/g, btick:/`/g, tilde:/~~/g, v9:/\/v9\//g,
           jsonl:/\.jsonl/g, backend:/\u540e\u7aef/g,
           field:/(?<![A-Za-z0-9_$])(level|caps|invoke|cost|probe|paths|ids)(?![A-Za-z0-9_$])/g,
           under:/(?<![A-Za-z0-9_$])(__UNDER__)(?![A-Za-z0-9_$])/g,
           frontend:/\u524d\u7aef/g};
  var ALLOW = /(?:ds_chat|dsh_wsl|v9_agent|web_[A-Za-z0-9]+|\.agent_state\.json|pa_[A-Za-z0-9_]+)/g;
  var DRIVE = /[A-Za-z]:[\\\/]/g;
  var hits = [], flatLen = 0, texts = [], flat = [];
  var FLAG = /(?<![A-Za-z0-9])-{1,2}[A-Za-z][-A-Za-z0-9_]*/g;
  function mask(t){ return t.replace(ALLOW, function(m){ return '\u3000'.repeat(m.length); })
    .replace(FLAG, function(m){ return '\u3000'.repeat(m.length); }); }
  function fire(n, txt, eng){
    var m = mask(txt);
    for(var key in R){ var re=new RegExp(R[key].source,'g'), mm;
      while((mm=re.exec(m))!==null){ hits.push({k:key, eng:!!eng, loc:locOf(n),
        t:txt.slice(Math.max(0,mm.index-30), mm.index+50).replace(/\s+/g,' ').trim()}); } }
    var dm = m.match(DRIVE);
    if(dm) hits.push({k:'drive', eng:!!eng, loc:locOf(n), t:txt.slice(0,60)});
  }
  function walk(n, eng){
    for(var i=0;i<n.childNodes.length;i++){
      var k = n.childNodes[i];
      if(k.nodeType === 3){
        var tx = String(k.nodeValue || ''); if(tx.replace(/\s+/g,'') === '') continue;
        if(!vis(n)) continue;
        if(!eng) flatLen += tx.replace(/\s+/g,'').length;
        texts.push((eng?'[E]':'') + tx.replace(/\s+/g,' ').trim());
        if(!eng) flat.push(tx.replace(/\s+/g,' ').trim());
        fire(n, tx, eng);
        continue; }
      if(k.nodeType !== 1) continue;
      if(!vis(k)) continue;
      var tag = String(k.tagName).toLowerCase();
      if(tag === 'details'){ walk(k, eng || isEng(k)); continue; }
      walk(k, eng);
    }
  }
  var roots = [];
  var a = document.getElementById('paMorePanel'); if(a) roots.push(a);
  var b = document.getElementById('paFaceTasks'); if(b) roots.push(b);
  for(var i=0;i<roots.length;i++) walk(roots[i], false);
  return JSON.stringify({n_roots: roots.length, flatLen: flatLen, hits: hits, text: texts.join(' | '), flatText: flat.join(' | ')});
})()
"""
#: ⭐ pm_2108 §二.3ⓜ：活态之标识名列 ⇐ `KNOWN_ENG_IDS`（一处定形 · ⛔ 二处各书）
_PROBE = _PROBE.replace(u"__UNDER__", u"|".join(KNOWN_ENG_IDS))
assert u"__UNDER__" not in _PROBE, u"活态之标识名列须已接（否则齿空跑）"
for _nm in KNOWN_ENG_IDS:
    assert _nm in _PROBE, u"标识名 ⛔ 入活态之表：" + _nm

_OPEN = (u"(function(){ var ds = document.querySelectorAll('details');"
         u" for(var i=0;i<ds.length;i++){ try{ ds[i].setAttribute('open',''); }catch(e){} }"
         u" return ds.length; })()")

_DISMISS = (u"(function(){ var bs = document.querySelectorAll('button');"
            u" for(var i=0;i<bs.length;i++){"
            u" if(String(bs[i].textContent||'').trim() === '\u77e5\u9053\u4e86'){ bs[i].click(); return 'clicked'; } }"
            u" return 'none'; })()")

_DRIVE_UI = (u"(function(){ try{ paMore(true);"
             u" var g=document.getElementById('paMoreGrpSet'); if(g) g.setAttribute('open','');"
             u" var d=document.getElementById('paMoreGrpDo'); if(d) d.setAttribute('open','');"
             u" try{ paSysScan(); }catch(e){}"
             u" try{ var f=document.getElementById('paAboutFold'); if(f) f.setAttribute('open',''); }catch(e){}"
             u" try{ paAboutLoad(true); }catch(e){}"
             u" try{ var h=document.getElementById('paMoreGrpHist'); if(h) h.setAttribute('open',''); }catch(e){}"
             u" return 'ok'; }catch(e){ return 'ERR:' + String(e); } })()")

_MORE_OFF = (u"(function(){ try{ paMore(false); return 'ok'; }catch(e){ return 'ERR:' + String(e); } })()")

_TASKS = (u"(function(){ try{ setFaceById('tasks'); return 'ok'; }"
          u"catch(e){ return 'ERR:' + String(e); } })()")

#: 上屏之锚（本批之逐字 ⇒ 真渲须见 · ⛔ 见 ⇒ 面未渲 ∨ 辞漂）
_MUST_SHOW = (u"\u8bca\u65ad\u4e0e\u6765\u6e90",            # 诊断与来源（折首）
              u"\u672c\u5668\u5168\u7a0b",                  # 本器全程（体检之结论）
              u"\u672c\u673a\u4f53\u68c0\uff08\u53ea\u8bfb")  # 本机体检（只读


def _reap():
    spec = importlib.util.spec_from_file_location(
        "cw_chrome_reap_fc2095", str(ROOT / "tests" / "unit" / "cw_chrome_reap.py"))
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
    if not R.chrome_exe():
        return u"chrome.exe ⛔ 在"
    try:
        import websocket  # noqa: F401
    except Exception:
        return u"python websocket ⛔ 在（websocket-client）"
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
    raise RuntimeError(u"CDP 之页 ⛔ 得（口 %d）" % port)


class _CDP(object):
    def __init__(self, ws):
        import websocket
        self.ws = websocket.create_connection(ws, timeout=120, max_size=256 * 1024 * 1024)
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
    u"""真 Chrome × CDP：`更多 ▾`（体检 ＋ 关于 ＋ 会话历史）＋ `tasks` 面之**在屏**文 ⇒ 禁记号 = 0。

    ⭐ 取法（承我域之尺 · 例⒏ ／ 例⒐）：**活树遍历**（`checkVisibility` ＋ **`details.eng` 折判**）——
      ⛔ 裸 `textContent`（含 `<script>` 源与隐藏件）／ ⛔ 全信 `innerText`（含折内之隐字）／
      ⛔ 以「任一 `details`」充「工程之折」（导航之折之体仍算**平文**）。
    环境不就绪 ⇒ **skip**（⛔ 红）；真跑毕 ⇒ 必收（`cw_chrome_reap`）∧ 图落盘。
    """
    R = _reap()
    reason = _env_reason(R)
    if reason:
        pytest.skip(u"环境不就绪：" + reason)
    port = _free_port()
    with R.run_headless(port=port, tag="cw2095fc", wait_s=15.0,
                        extra=("--remote-allow-origins=*",),
                        why=u"pm_2095 次批之屏净（真渲之齿）"):
        c = _CDP(_ws_url(port))
        c.cmd("Page.enable")
        c.cmd("Runtime.enable")
        c.cmd("Emulation.setDeviceMetricsOverride", width=1440, height=940,
              deviceScaleFactor=1, mobile=False)
        c.cmd("Page.navigate", url="http://127.0.0.1:%d/web/pa.html" % GATEWAY)
        time.sleep(7.0)
        c.js(_DISMISS)
        assert c.js(_DRIVE_UI) == "ok", u"开「更多 ／ 体检 ／ 关于」⛔ 成"
        time.sleep(2.0)
        c.js(_OPEN)
        res = None
        for _ in range(25):
            time.sleep(1.0)
            raw = c.js(_PROBE)
            try:
                res = json.loads(raw)
            except Exception:
                continue
            if int(res.get("flatLen") or 0) > 2000 and u"\u672c\u5668\u5168\u7a0b" in (res.get("text") or ""):
                break
        shot = c.shot(str(tmp_path / "more_w1440.png"))
        assert c.js(_TASKS) == "ok", u"切 `tasks` 面 ⛔ 成"
        time.sleep(1.5)
        c.js(_MORE_OFF)
        time.sleep(0.4)
        c.js(_OPEN)
        raw2 = c.js(_PROBE)
        try:
            res2 = json.loads(raw2)
        except Exception:
            res2 = {}
        shot2 = c.shot(str(tmp_path / "tasks_w1440.png"))

    assert res and int(res.get("n_roots") or 0) >= 1, u"射程之根 ⛔ 在：%r" % (res,)
    assert int(res["flatLen"]) > 2000, u"平文过少 ⇒ 面未渲：%r" % (res["flatLen"],)
    # ⚠ 盘符（`C:\` ／ `D:\`）⇒ **准留**（pm_2095 §二.2 之追认：用户须知「哪一卷紧」方能行事）
    flats = [h for h in res["hits"] if not h["eng"] and h["k"] != u"drive"]
    assert flats == [], u"**平文**见犯字 %s" % (
        u"；".join(u"%s@%s %r" % (h["k"], h["loc"], h["t"][:50]) for h in flats[:8]),)
    flats2 = [h for h in (res2.get("hits") or []) if not h["eng"]]
    assert flats2 == [], u"`tasks` 面**平文**见犯字 %s" % (
        u"；".join(u"%s@%s %r" % (h["k"], h["loc"], h["t"][:50]) for h in flats2[:8]),)
    assert u"\u4e0e\u5bf9\u7aef\u4e4b\u901a\uff1a" in (res2.get("text") or u""), \
        u"`#paT1Panel` 折首之「与对端之通」 ⛔ 在屏（面未渲 ∨ 辞漂）"
    txt = res["text"]
    for lit in _MUST_SHOW:
        assert lit in txt, u"逐字 ⛔ 见（面未渲 ∨ 辞漂）：%r" % (lit,)
    assert shot > 0 and shot2 > 0, u"图须落盘（跑毕必收 ∧ 入账）"

# ============================== S5 · 停手卡之守卫（真路 · 真 Chrome × CDP） ==============================
#: 填表（**真用户之路** · ⛔ 预置 `#paStopAsk`）
_FILL = (u"(function(){"
         u" function setv(id, v){ var e=document.getElementById(id); if(!e) return 'no:'+id;"
         u" e.value = v; e.dispatchEvent(new Event('input',{bubbles:true})); return 'ok'; }"
         u" var r=[];"
         u" r.push(setv('paT1Decision', 'd-test-2104'));"
         u" r.push(setv('paT1Task', 'pm_2104 \u6d4b\u4e4b\u4ea4\u529e'));"
         u" r.push(setv('paT1To', '\u672c\u4eba'));"
         u" r.push(setv('paT1Subject', '\u6d4b\u4e4b\u4e3b\u9898'));"
         u" return r.join(','); })()")

#: 交付（真路 · `window.paT1.deliver()`）
_DELIVER = (u"(function(){ try{ window.paT1.deliver(); return 'ok'; }"
            u"catch(e){ return 'ERR:'+String(e); } })()")

#: 观测：卡在否 ＋ 卡题 ＋ `#paT1Out` 之字（⭐ ⛔ 预置桩 · ⛔ 改源码）
_OBS = (u"(function(){"
        u" var c=document.getElementById('paStopAsk');"
        u" var o=document.getElementById('paT1Out');"
        u" return JSON.stringify({card:!!c,"
        u" title:(c?String(c.textContent).replace(/\\s+/g,' ').trim().slice(0,60):null),"
        u" out:(o?String(o.textContent).replace(/\\s+/g,' ').trim():null)}); })()")

_ASK_TYPE = u"(function(){ return typeof window.paStopAsk; })()"

#: 反控之桩：删 `window.paStopAsk`（⭐ 唯反控用之）
_UNASK = (u"(function(){ try{ window.paStopAsk = null; }catch(e){}"
          u" var c=document.getElementById('paStopAsk');"
          u" if(c && c.parentNode) c.parentNode.removeChild(c);"
          u" return 'ok'; })()")

#: 清场（备复走）
_CLOSE = (u"(function(){ var c=document.getElementById('paStopAsk');"
          u" if(c && c.parentNode) c.parentNode.removeChild(c); return 'ok'; })()")

#: 上屏之锚（本批之逐字 ⇒ 真渲须见 · ⛔ 见 ⇒ 辞漂）
_CARD_TITLE = u"\u505c\u624b\uff1a\u5373\u5c06\u4ee5\u4f60\u540d\u4e49\u53d1\u4fe1\uff08\u4ea4\u4ed8\uff09"
_NO_CARD_MSG = u"\u505c\u624b\u5361\u4e0d\u53ef\u7528"


def _fc_obs(c):
    u"""取观测（`_OBS` ⇒ dict ∨ 空）—— ⛔ 静默（`⛔ 可读` ⇒ 空 ⇒ 上游之断言自会咬）。"""
    raw = c.js(_OBS)
    try:
        d = json.loads(raw)
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


def test_S5_停手卡之守卫之真路():
    u"""pm_2104 §二：`#paStopAsk` **唯由 `stopAsk()` 自建**（`selfdesc.js:3709`–`:3724`）⇒ 守卫（`:4282`）
    ⛔ 得于**建卡之前**索其存在（原 `|| !Q('paStopAsk')` **恒真** ⇒ 卡恒 ⛔ 开 ⇒ 真用户之路断）。

    ⭐ 形（承 `test_S1c`）：**正控** ＝ 真用户之路（⛔ 预置 `#paStopAsk` · 唯 `window.paStopAsk` 在）
      ⇒ **必见卡题** ∧ ⛔ 见「停手卡不可用」；
      **反控** ＝ 删 `window.paStopAsk` ⇒ **必见**「停手卡不可用」∧ 卡 ⛔ 开。
    ⚠ 二控皆须**真咬**：反控之绿 ⇒ 证正控之绿 ⛔ 为「恒绿之空跑」。
    环境不就绪 ⇒ **skip**（⛔ 红）；真跑毕 ⇒ 必收（`cw_chrome_reap`）。
    """
    R = _reap()
    reason = _env_reason(R)
    if reason:
        pytest.skip(u"环境不就绪：" + reason)
    port = _free_port()
    with R.run_headless(port=port, tag="cw2095s5", wait_s=15.0,
                        extra=("--remote-allow-origins=*",),
                        why=u"pm_2104 令：停手卡之守卫（真路之正控 ／ 反控）"):
        c = _CDP(_ws_url(port))
        c.cmd("Page.enable")
        c.cmd("Runtime.enable")
        c.cmd("Emulation.setDeviceMetricsOverride", width=1440, height=940,
              deviceScaleFactor=1, mobile=False)
        c.cmd("Page.navigate", url="http://127.0.0.1:%d/web/pa.html" % GATEWAY)
        time.sleep(7.0)
        c.js(_DISMISS)
        assert c.js(_TASKS) == "ok", u"切 `tasks` 面 ⛔ 成"
        time.sleep(2.5)
        c.js(_OPEN)
        # ⭐ 前提之锚（否则二控皆空跑）
        assert c.js(_ASK_TYPE) == "function", u"`window.paStopAsk` ⛔ 为函数（面未挂载）"
        fill = c.js(_FILL)
        assert fill == u"ok,ok,ok,ok", u"填表（交办 ／ 收件人 ／ 拍板件号）⛔ 成：%r" % (fill,)
        time.sleep(0.6)
        assert _fc_obs(c).get("card") is False, u"前提：`#paStopAsk` 须 ⛔ 在（否则正控成空跑）"
        # ---------- 正控（真路 · ⛔ 预置 `#paStopAsk`）----------
        assert c.js(_DELIVER) == "ok", u"交付（正控）⛔ 成"
        time.sleep(0.8)
        ok = _fc_obs(c)
        assert ok.get("card") is True, \
            u"正控（真路）：卡**必开** —— ⛔ 开 ⇒ 守卫之衍字复发 ∨ 面未挂载：%r" % (ok,)
        assert _CARD_TITLE in (ok.get("title") or u""), \
            u"正控：卡题逐字 ⛔ 见（辞漂 ∨ 未渲）：%r" % (ok.get("title"),)
        assert _NO_CARD_MSG not in (ok.get("out") or u""), \
            u"正控：屏上 ⛔ 得见「停手卡不可用」：%r" % (ok.get("out"),)
        # ---------- 反控（删 `window.paStopAsk`）----------
        c.js(_CLOSE)
        c.js(_UNASK)
        assert c.js(_ASK_TYPE) != "function", u"反控之桩 ⛔ 成（`paStopAsk` 仍在）"
        assert c.js(_DELIVER) == "ok", u"交付（反控）⛔ 成"
        time.sleep(0.8)
        bad = _fc_obs(c)
        assert bad.get("card") is False, u"反控：无 `paStopAsk` ⇒ 卡 ⛔ 得开：%r" % (bad,)
        assert _NO_CARD_MSG in (bad.get("out") or u""), \
            u"反控：须见「停手卡不可用」—— ⛔ 见 ⇒ 正控之绿为假（⛔ 假牙）：%r" % (bad.get("out"),)

# ============================== S8 · 真渲（过程注记之数 ＋ T1 面之平文 · 真 Chrome × CDP） ==============================
#: ⭐ 探器之根 ⇒ `#paT1Panel`（本批之面 · 承 pm_2104 §四.4⒝「射程须及 T1 诸函」）
_T1_ROOTS_OLD = (u"  var a = document.getElementById('paMorePanel'); if(a) roots.push(a);\n"
                 u"  var b = document.getElementById('paFaceTasks'); if(b) roots.push(b);")
_T1_ROOTS_NEW = u"  var a = document.getElementById('paT1Panel'); if(a) roots.push(a);"
assert _T1_ROOTS_OLD in _PROBE, u"`_PROBE` 之根须可换（否则 T1 之探器将空跑）"
_PROBE_T1 = _PROBE.replace(_T1_ROOTS_OLD, _T1_ROOTS_NEW)
assert _PROBE_T1 != _PROBE

#: ⒠ 之数：`#paMoreBody` 内之折（`[data-engskip]`）∧ 其中带 `id="paEngNote"` 者
_CNT_NOTE = (u"(function(){ var b=document.getElementById('paMoreBody'); if(!b) return '{}';"
             u" var a=b.querySelectorAll('details[data-engskip]');"
             u" var c=b.querySelectorAll('details[data-engskip][id=\"paEngNote\"]');"
             u" return JSON.stringify({n:a.length, nid:c.length}); })()")
#: ⚠ 本轮既净 ⇒ 自然之 hit ＝ 0 ⇒ 「合并 ／ 新建」之路**⛔ 得行** ⇒ 反控须**造一 hit**。
#:   此非「预置被验之物」（承 pm_2104 §四.4⒠ 之教训）—— 乃「使被测之路得行」（其 hit 之由 ＝ 端字 `§`）。
_FORCE_HIT = (u"(function(){ try{"
              u" var b=document.getElementById('paMoreBody'); if(!b) return 'noBody';"
              u" var pr=document.createElement('div'); pr.id='cwProbeHit'; pr.textContent='§probe';"
              u" b.appendChild(pr); var r=String(paEngCleanDrawer());"
              u" var a=b.querySelectorAll('details[data-engskip]');"
              u" var c=b.querySelectorAll('details[data-engskip][id=\"paEngNote\"]');"
              u" return JSON.stringify({r:r, n:a.length, nid:c.length}); }"
              u"catch(e){ return 'ERR:'+String(e); } })()")
#: 反控之桩：去其 `id`（＝旧形之「以任一 `data-engskip` 索之」）
_UNID = (u"(function(){ try{ var d=document.getElementById('paEngNote'); if(!d) return 'none';"
         u" d.removeAttribute('id'); return 'ok'; }catch(e){ return 'ERR'; } })()")
_DROP_PROBE = (u"(function(){ var e=document.getElementById('cwProbeHit');"
               u" if(e && e.parentNode) e.parentNode.removeChild(e); return 'ok'; })()")
#: 真源之落处（折首 `title` ／ 折体）须在 ∧ 平文 ⛔ 见 `T1`
_HTMLHAS_T1 = (u"(function(){ var p=document.getElementById('paT1Panel'); if(!p) return '{}';"
               u" var h=p.innerHTML;"
               u" return JSON.stringify({t1title:h.indexOf('title=\"工程之据：T1 交付面\"')>=0,"
               u" foldBody:h.indexOf('POST /v9/pa/deliver/mail')>=0,"
               u" rawT1:h.indexOf('>T1 交付面</b>')>=0}); })()")
#: T1 面**屏上**（折判）须见之逐字
_T1_MUST_SHOW = (u"交付面", u"（发信 · 由 PA 自己送出）", u"与对端之通：",
                 u"（真闸 · 在真发那一步）", u"来信之件号",
                 u"拍板件号（真拍板由对端读 · 不由本面编号）")
#: T1 面**平文** ⛔ 得见之旧形（工程语 ／ 端字段名 ／ 端径 ／ 旧辞）
_T1_MUST_NOT = (u"后端", u"task_id", u"decision_id", u"/v9/", u"C1）", u"fail-closed", u"路由")


def test_S8_真渲_过程注记之数与T1面之平文(tmp_path):
    u"""pm_2104 §四.4⒠（过程注记之增生须治）＋ §四.4⒝（射程须及 T1 诸函）＋ pm_2106 §三.4：
    ⒠ **正控**（真载入 · `go()` 三跑 ⇒ 折数恒 2 ／ 其中 `paEngNote` 1 —— 旧形 ⇒ 3）；
    ⒠ **反控**（去其 `id` ⇒ 造 hit ⇒ **必增生** ⇒ 证「唯 id 乃其锚」）；
    T1 面：**平文**（折判 · ⛔ 裸 `textContent`）犯字 ＝ 0 ∧ 本批逐字在屏 ∧ 旧形 ⛔ 在屏 ∧ 真源在 `title` ／ 折体。
    环境不就绪 ⇒ **skip**（⛔ 红）；真跑毕 ⇒ 必收（`cw_chrome_reap`）∧ 图落盘。
    """
    R = _reap()
    reason = _env_reason(R)
    if reason:
        pytest.skip(u"环境不就绪：" + reason)
    port = _free_port()
    with R.run_headless(port=port, tag="cw2095s8", wait_s=15.0,
                        extra=("--remote-allow-origins=*",),
                        why=u"pm_2104 §四.4⒠（过程注记之数）＋ §四.4⒝（T1 面之真渲平文）"):
        c = _CDP(_ws_url(port))
        c.cmd("Page.enable")
        c.cmd("Runtime.enable")
        c.cmd("Emulation.setDeviceMetricsOverride", width=1440, height=940,
              deviceScaleFactor=1, mobile=False)
        c.cmd("Page.navigate", url="http://127.0.0.1:%d/web/pa.html" % GATEWAY)
        time.sleep(7.5)
        c.js(_DISMISS)
        assert c.js(_DRIVE_UI) == "ok", u"开「更多 ／ 体检 ／ 关于」⛔ 成"
        time.sleep(2.5)
        c.js(_OPEN)
        time.sleep(1.0)
        # ---------- ⒠ 正控：真载入 ⇒ 折之数须恒「2 ／ 1」 ----------
        d0 = json.loads(c.js(_CNT_NOTE) or "{}")
        assert d0.get("n") == 2 and d0.get("nid") == 1, \
            u"⒠：`details[data-engskip]` 须 ＝ 2 ∧ `[id=paEngNote]` ＝ 1（旧形 ⇒ 3）：%r" % (d0,)
        # ⒠ 正控二（幂等）：造一 hit ⇒ 行「合并」之路 ⇒ 其数 ⛔ 增
        d1 = json.loads(c.js(_FORCE_HIT) or "{}")
        assert d1.get("r") not in (None, u"0", u"noBody"), u"正控之 hit ⛔ 生效：%r" % (d1,)
        assert d1.get("n") == 2 and d1.get("nid") == 1, u"正控：既有 ⇒ 须**并之**（⛔ 新建）：%r" % (d1,)
        c.js(_DROP_PROBE)
        # ⒠ 反控：去其 `id` ⇒ 造 hit ⇒ **必新建一条**
        assert c.js(_UNID) == "ok", u"反控之桩 ⛔ 成"
        d2 = json.loads(c.js(_FORCE_HIT) or "{}")
        assert d2.get("n") == 3, u"反控：唯 `id` 乃其锚 —— 去之 ⇒ 必增生：%r" % (d2,)
        c.js(_DROP_PROBE)
        shot1 = c.shot(str(tmp_path / "more_engnote_w1440.png"))
        # ---------- T1 面之真渲（折判 · ⛔ 裸 `textContent`） ----------
        assert c.js(_TASKS) == "ok", u"切 `tasks` 面 ⛔ 成"
        time.sleep(2.5)
        c.js(_OPEN)
        time.sleep(1.0)
        try:
            res = json.loads(c.js(_PROBE_T1))
        except Exception:
            res = {}
        assert int(res.get("n_roots") or 0) == 1, u"T1 之根（`#paT1Panel`）⛔ 在：%r" % (res,)
        assert int(res.get("flatLen") or 0) > 200, u"T1 之平文过少 ⇒ 面未渲：%r" % (res.get("flatLen"),)
        flats = [h for h in (res.get("hits") or []) if not h["eng"] and h["k"] != u"drive"]
        assert flats == [], u"T1 面**平文**见犯字 %s" % (
            u"；".join(u"%s@%s %r" % (h["k"], h["loc"], h["t"][:50]) for h in flats[:8]),)
        txt = res.get("flatText") or u""
        assert txt, u"T1 \u4e4b\u5e73\u6587 \u26d4 \u5f97\uff08\u63a2\u5668\u987b\u7ed9 `flatText`\uff09"
        for lit in _T1_MUST_SHOW:
            assert lit in txt, u"T1 面逐字 ⛔ 见（面未渲 ∨ 辞漂）：%r" % (lit,)
        for old in _T1_MUST_NOT:
            assert old not in txt, u"T1 面**平文**见旧形：%r" % (old,)
        hh = json.loads(c.js(_HTMLHAS_T1) or "{}")
        assert hh.get("t1title") is True, u"真源（`T1 交付面`）须入折首之 `title`（⛔ 丢真源）"
        assert hh.get("foldBody") is True, u"端径（`POST /v9/pa/deliver/mail`）须在折体（⛔ 丢真源）"
        assert hh.get("rawT1") is False, u"平文 ⛔ 得见 `T1`"
        shot2 = c.shot(str(tmp_path / "tasks_t1_w1440.png"))
    assert shot1 > 0 and shot2 > 0, u"图须落盘（跑毕必收 ∧ 入账）"


# ============================== S9 · 收口（pm_2108 §三） ==============================
def _screen_part_old_attrs(txt: str) -> str:
    u"""旧形（本收口之前）：**概剔诸属性** —— 把 `placeholder` ／ `value`（**屏上**）与 `title`（屏外）混为一谈。"""
    return re.sub(u'[A-Za-z_:][-A-Za-z0-9_:]*\\s*=\\s*"[^"]*"', u"", txt)


#: 本收口所净之（新 → 旧）—— 「把其原字移入平文」⇒ **必咬**
_S9_ANCHORS_SELF = (
    (u"' · 指纹 '", u"' · 指纹 sha16 '"),
    (u"引哪封来信 · 指纹<input", u"引哪封来信 · sha16<input"),
    (u'placeholder="原信指纹（留空 ⇒ 显「缺」）"',
     u'placeholder="原信 sha16（留空 ⇒ 显「缺」）"'),
)
_S9_ANCHORS_SYS = (
    (u"可全选后复制（只在这页上 · 不写盘）。",
     u"可全选后复制（唯前端 · 不写盘）。"),
)


def test_S9_收口_sha16与前端与placeholder():
    u"""pm_2108 §三（ⓜ `refLine` ／ ⓝ `:4551` 之标 ／ ⓞ `:4551` 之 `placeholder` ／ ⓟ `sys.js` 之「前端」）
    ＋ §三.1（**新例ⱒ**：`placeholder` ／ `value` ⇒ **屏上** ⇒ 必咬）。

    ① 正控：前提 —— `selfdesc.js` ／ `sys.js` 之屏上字面须先净（`sha16` ／ 前端 皆 ⛔ 许现）
    ② 正控（新例ⱒ）：`placeholder` 之值 ⇒ **入屏**（新法留之 ／ 旧法概剔 ⇒ 漏）
    ③ 反控（必咬）：上诸处**还旧形** ⇒ `scan` 必有 hit
    ④ 反控（射程）：行 `title` 之原字 ⇒ 明标（⛔ 咬）；**去其明标** ⇒ 该字入屏上之数 ⇒ **必咬**
    ⑤ 正控（pm_2108 §二.3ⓞ）：把端之键 `task_id` **移入平文** ⇒ **必咬**（⛔ 以「齿改名」了事）
    """
    src, syssrc = _read(SELF), _read(SYS)
    # ① 正控（前提）
    assert scan(src, _SP["self"], _SP["ign"])["hits"] == [], u"前提：`selfdesc.js` 之屏上须净"
    assert scan(syssrc, _SP["sys"], _SP["ign"])["hits"] == [], u"前提：`sys.js` 之屏上须净"
    # ② 新例ⱒ：`placeholder` 之值 ⇒ 屏上
    demo = u'" placeholder="' + u"原信指纹" + u'（留空 ⇒ 显「缺」）" style="'
    assert u"原信指纹" in _SCREENPART(demo), u"`placeholder` 之值须**入屏**（本收口之裁）"
    assert u"原信指纹" not in _screen_part_old_attrs(demo), u"（对照）旧法概剔诸属性 ⇒ 漏"
    # ③ 反控：还旧形 ⇒ 必咬
    for (new, old) in _S9_ANCHORS_SELF:
        m = src.replace(new, old, 1)
        assert m != src, u"反控之锚 ⛔ 在（将空跑）：%r" % (new,)
        assert scan(m, _SP["self"], _SP["ign"])["hits"], u"还旧形 ⇒ 必咬：%r" % (new,)
    for (new, old) in _S9_ANCHORS_SYS:
        m = syssrc.replace(new, old, 1)
        assert m != syssrc, u"反控之锚 ⛔ 在（将空跑）：%r" % (new,)
        assert scan(m, _SP["sys"], _SP["ign"])["hits"], u"还旧形 ⇒ 必咬（sys）：%r" % (new,)
    # ④ 行 `title` 之原字 ⇒ 明标
    miss = [a for (a, b) in _T1_TITLE_IGN if _find(src, a, b) == (-1, -1)]
    assert miss == [], u"行 `title` 之明标 ⛔ 在（反控将空跑）：%r" % (miss,)
    assert u"原字 sha16" not in u"".join(t for (_p, _f, t) in scan(src, _SP["self"], _SP["ign"])["kept"]), \
        u"`title` 之原字 ⛔ 得入屏上之数（明标须真罩）"
    kept0 = scan(src, _SP["self"], [])["kept"]
    assert any(u"原字 sha16" in t for (_p, _f, t) in kept0), \
        u"（反控）去其明标 ⇒ 该 `title` 之字**入屏上之数**（⇒ 明标 ⛔ 空跑）"
    assert scan(src, _SP["self"], [])["hits"], u"（反控）去其明标 ⇒ 必咬"
    # ⑤ 正控（pm_2108 §二.3ⓞ）：端之键 `task_id` 移入**平文** ⇒ 必咬
    _a5 = u"'（四件 ＋ 引哪封来信 ＋ 件之刻 ＋ 每件花费 皆对端取 · 不由本面估）'"
    assert _a5 in src, u"正控之锚 ⛔ 在（将空跑）"
    m5 = src.replace(_a5, u"'（件号 task_id ＋ 引哪封来信 ＋ 件之刻 ＋ 每件花费 皆对端取 · 不由本面估）'", 1)
    assert m5 != src, u"正控之变 ⛔ 真"
    h5 = scan(m5, _SP["self"], _SP["ign"])["hits"]
    assert h5 and any(u"idname" in x["bad"] for x in h5), \
        u"端之键 `task_id` 移入平文 ⇒ 必咬（⛔ 假绿）"


# ============================== S10 · 计划面（pm_2109 §一） ==============================
def _esc(t: str) -> str:
    u"""人话 ⇒ 源码之 `\\uXXXX` 形（本域之件多以 `\\uXXXX` 书之 ⇒ 逐字锚须同其形）。"""
    return u"".join((u"\\u%04x" % ord(c)) if ord(c) > 127 else c for c in t)


#: 计划面所净之（新 ／ 旧）—— 逐行之锚（源码之拼接式跨行 ⇒ 锚须在一行之内）
#: 「还旧形」⇒ **必咬**（其旧形的罪证：`/v9/` · `HTTP ` · `⛔` · `后端`）。
_PLAN_PAIRS = (
    (u"计划：交办为空 ⇒ 未提交（不会开空件）",
     u"计划：⛔ 交办为空 ⇒ 未提交（⛔ 开空件）"),
    (u"计划：正在出…（约 1 分钟 · 首跑须备模型）",
     u"计划：请求中…（POST /v9/pa/plan）"),
    (u"（对端未回 ／ 计划为空）⇒ 照实",
     u"（POST /v9/pa/plan 未回 ∨ 空 steps）⇒ 照实"),
    (u"（本面不编步骤）</div>",
     u"（本面 ⛔ 不编步骤）</div>"),
    (u"计划：对端未给（", u"计划：后端未给（HTTP "),
    (u"）⇒ 不等于无计划", u"）⇒ ⛔ 不等于无计划"),
    (u"须您亲批；此据接口之定形",
     u"须老板亲批（POST /v9/pa/decision 落 decision_id）"),
)

#: 计四 · 计五 之**屏外**之据（本块 ／ 本行 `title`）
_PLAN_TITLES = (
    u'title="工程之据：源 POST /v9/pa/plan · task_type ',
    u'title="工程之据：POST /v9/pa/decision · decision_id · 缺 ⇒ 403 fail-closed（pm_071 §四）"',
)


def test_S10_计划面之屏净与反控():
    u"""pm_2109 §一（计划面五处）+ §一.1（齿）—— 屏上唯人话
    ∧ 工程之据（端径 / `task_type` / `source` / 内文号）⇒ 本块 / 本行 `title`（⛔ 丢真源）。
    并含其**孪生三处**（`doPlan` 之 `后端` ×1 / `HTTP` ×2 / `⛔` ×1，我一手自速）。

    ① 正控：计划面入 `_SP["self"]`（射程）⇒ 屏上字面须净
    ② 逐字：本件之新辞（一处定形 · 锚在一行之内）∧ 旧辞须除
    ③ 反控（必咬）：还旧形 ⇒ `scan` 必有 hit
    ④ 反控：屏外之据（计四 之 `title`）**移入平文** ⇒ 必咬
    ⑤ 正控（§一.1）：端之键 `task_type` / `source` 移入平文 ⇒ 必咬（`idname`）
    """
    src = _read(SELF)
    # ① 前提（射程真罩：计划面既入 `_SP["self"]` · ⛔ 则本步失灵）
    assert scan(src, _SP["self"], _SP["ign"])["hits"] == [], u"前提：计划面之屏上须净"
    # ② 逐字
    for (new, old) in _PLAN_PAIRS:
        n = src.count(_esc(new))
        assert n == 1, u"新辞之数 ⛔ ≠1（%d）：%r" % (n, new[:40])
        assert _esc(old) not in src, u"旧辞未除：%r" % (old[:40],)
    for t in (u"⚠ 这次没拿到计划", u"计划：已出 "):
        assert _esc(t) in src, u"新辞 ⛔ 在：%r" % (t,)
    for t in (u"后端未给计划", u"未提交（⛔", u"）⇒ ⛔ 不等于无计划"):
        assert _esc(t) not in src, u"旧辞未除：%r" % (t,)
    for t in _PLAN_TITLES:
        assert _esc(t) in src, u"屏外之据 ⛔ 在（计四 / 计五）：%r" % (t[:40],)
    _tail = u"</b> 步</div>"
    assert src.count(_esc(_tail)) == 1, u"计四 之屏上须止于 「步」（端径 ⛔ 上屏）"
    assert u"task_type" not in _SCREENPART(_esc(u'<div style="margin:4px 0 2px" title="工程之据：源 POST /v9/pa/plan · task_type ')), \
        u"计四：`task_type` ⛔ 得入屏上之分"
    # ③ 反控（还旧形 ⇒ 必咬）
    for (new, old) in _PLAN_PAIRS:
        m = src.replace(_esc(new), _esc(old), 1)
        assert m != src, u"反控之锚 ⛔ 在（将空跑）：%r" % (new[:40],)
        assert scan(m, _SP["self"], _SP["ign"])["hits"], u"还旧形 ⇒ 必咬：%r" % (new[:40],)
    # ④ 屏外之据移入平文 ⇒ 必咬
    m4 = src.replace(_esc(_tail), _esc(u"</b> 步（源 POST /v9/pa/plan · task_type "), 1)
    assert m4 != src, u"计四 之反控锚 ⛔ 在（将空跑）"
    assert scan(m4, _SP["self"], _SP["ign"])["hits"], u"计四：屏外之据移入平文 ⇒ 必咬"
    # ⑤ 端之键入平文 ⇒ 必咬
    m5 = src.replace(_esc(_tail), _esc(u"</b> 步 task_type source</div>"), 1)
    assert m5 != src, u"正控之锚 ⛔ 在（将空跑）"
    h5 = scan(m5, _SP["self"], _SP["ign"])["hits"]
    assert h5 and any(u"idname" in x["bad"] for x in h5), \
        u"端之键 `task_type` ／ `source` 入平文 ⇒ 必咬（⛔ 假绿）"
