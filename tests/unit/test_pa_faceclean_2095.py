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

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_faceclean_2095.py -q -p no:cacheprovider --basetemp=D:\\pa_tmp\\pt2095
"""
from __future__ import annotations

import io
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
#: 字面内之 HTML 属性（`title="…"` ／ `data-axis="probe"` 之族）⇒ **屏外** ⇒ 剔之（⛔ 上屏之字）
_ATTR_RE = re.compile(u'[A-Za-z_:][-A-Za-z0-9_:]*\\s*=\\s*"[^"]*"')

#: 禁记号 —— 屏上**恒** ⛔ 许现（无例外）
STRICT_BANS = ((u"cross", u"\u26d4"), (u"star", u"**"), (u"btick", u"`"),
               (u"v9", u"/v9/"), (u"jsonl", u".jsonl"), (u"backend", u"\u540e\u7aef"))
#: ⭐ 端字段名 —— 平文 ⛔ 许现（承 pm_2095 §三.1；`title` ／ 折体 ／ 端给之真 id ⇒ 绿）
FIELDNAMES = (u"level", u"caps", u"invoke", u"cost", u"probe", u"paths", u"ids")
_FIELD_RE = re.compile(u"(?<![A-Za-z0-9_$])(" + u"|".join(FIELDNAMES) + u")(?![A-Za-z0-9_$])")
#: 白名单 —— 端给之真 id ／ 真件名 ／ 会话 id（照实之律 · 面 ⛔ 代端改名）
ALLOW = re.compile(u"(?:ds_chat|dsh_wsl|v9_agent|web_[A-Za-z0-9]+|\\.agent_state\\.json|pa_[A-Za-z0-9_]+)")
#: 命令行之旗（`--system-level` ／ `-background` 之族）＝ 端给之真值 ⇒ 白名单
_FLAG_RE = re.compile(u"(?<![A-Za-z0-9])-{1,2}[A-Za-z][-A-Za-z0-9_]*")


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _mask(t: str) -> str:
    u"""白名单之串 ⇒ 掩之（免得齿咬「端给之真 id」／命令行之旗）。"""
    t = _FLAG_RE.sub(lambda m: u"\u3000" * len(m.group(0)), t)
    return ALLOW.sub(lambda m: u"\u3000" * len(m.group(0)), t)


def _bad(t: str) -> list:
    out = [nm for (nm, pat) in STRICT_BANS if pat in t]
    if _FIELD_RE.search(_mask(t)):
        out.append(u"fieldname")
    if _DRIVE.search(_mask(t)):
        out.append(u"drive")
    if re.search(r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b", _mask(t)):
        out.append(u"underscore")
    return out


# ============================== 射程（本批之界） ==============================
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
    ign = [(_ANCHOR(self_src, u"      box.innerHTML = '<summary title=\"工程之据：真源",
                    u".jsonl（append-only）")),
           (_ANCHOR(self_src, u'<details class="eng" id="paAskStatBox">',
                    u"paSelfModeDiagHtml()\n    + '</div></details>'"))]
    return {"sys": sys_sp, "self": self_sp, "ign": ign}


def scan(src: str, spans: list, ign: list) -> dict:
    u"""纯扫（⛔ 触盘）：`{kept, hits}` —— `kept` ＝ scope 内之屏上字面。"""
    fns = _FUNCS(src)
    kept, hits = [], []
    for (pos, txt) in _LITS(src):
        if not any(a >= 0 and a <= pos < b for (a, b) in spans):
            continue
        if any(a >= 0 and a <= pos < b for (a, b) in ign):
            continue
        if not _CJK.search(txt):
            continue
        k = max(src.rfind(c, 0, pos) for c in _STMT_END)
        pre_raw = src[k + 1:pos]
        if pre_raw.count('"') % 2 == 1:
            continue
        pre = _STRIP(pre_raw)
        if re.search(r"\.title\s*=", pre):
            continue
        if re.search(r"setAttribute\(\s*['\"]title['\"]\s*,", pre):
            continue
        if _NEEDLE.search(pre.rstrip()):
            continue
        t = _ATTR_RE.sub(u"", _SCREENPART(txt))
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
    (u"title=\"真源：POST /v9/pa/deliver/mail 回执\">task_id ' + H(tid) + ' · 来源：对端回执",
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
  function isEng(k){ var c=' ' + String(k.className||'') + ' '; return c.indexOf(' eng ')>=0 || k.hasAttribute('data-engskip'); }
  var R = {cross:/\u26d4/g, star:/\*\*/g, btick:/`/g, tilde:/~~/g, v9:/\/v9\//g,
           jsonl:/\.jsonl/g, backend:/\u540e\u7aef/g,
           field:/(?<![A-Za-z0-9_$])(level|caps|invoke|cost|probe|paths|ids)(?![A-Za-z0-9_$])/g};
  var ALLOW = /(?:ds_chat|dsh_wsl|v9_agent|web_[A-Za-z0-9]+|\.agent_state\.json|pa_[A-Za-z0-9_]+)/g;
  var DRIVE = /[A-Za-z]:[\\\/]/g;
  var hits = [], flatLen = 0, texts = [];
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
  return JSON.stringify({n_roots: roots.length, flatLen: flatLen, hits: hits, text: texts.join(' | ')});
})()
"""

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