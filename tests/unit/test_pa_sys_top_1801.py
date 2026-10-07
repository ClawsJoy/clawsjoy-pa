# -*- coding: utf-8 -*-
u"""pm_1801 之齿 —— 本机体检之**一步可达**（顶栏入口 ＋ 聊天面入口）。

事由：老板「**你能检查电脑吗**」⇒ 聊天四轮「已受理 ／ 待核实」而一事未成；真因之一 ＝
  **入口埋在「更多 ▾ → ③ 设」之内**（二级菜单）⇒ 老板「一头撞上（不知道它在）」
  ＝ `pm_1771 §二.2` 之 UX 债之活证（CW `1800 §二.3` 之查）。
  今：顶栏 `.top-right` 之**首**加 `#paSysTop`（＋ `sys.js` 之 `paSysTopOpen`：开更多 ⇒ 开 ③ 组 ⇒
  展面 ⇒ 滚入视口）∧ 聊天面加 `#paChatSysGo`（走**同一函数** ⇒ 一处定形）。

判据（静态闸 · 与真 Chrome 之几何证互补）：
  P1 分区（一步可达）：`#paSysTop` 于 `.top-right` 之内 ∧ **⛔** 于 `#paMorePanel` 之内 ∧ 居其首。
  P2 一点即开（⛔ 二跳）：`onclick="paSysTopOpen()"`；`sys.js` 定义之 ∧ 其内开更多 ＋ 开 ③ 组
     ＋ 展面（`paSysOpen`）＋ `scrollIntoView` ∧ 导出 `window.paSysTopOpen`。
  P3 辞守：`title` 含「唯本机」＋「只读」＋「取一次」（⛔ 因显眼而失其界）。
  P4 聊天面入口（并办）：`#paChatSysGo` 于 `.composer` 之内 ∧ 同一函数（一处定形）∧ 其行载「不出手」。
  P5 反控（⛔ 空闸）：**旧入口 `#paSysOpen` 仍在 `#paMorePanel` 之内** ⇒ 一步可达之判据对之必
     **False** ⇒ 证本判据**真能捕**「藏在二级菜单」之病（若把新钮挪回菜单 ⇒ P1 必败）。
  P6 旧闸仍立：`#paSysOpen` ／ `#paSys` ／ `#paSysWhen`（面册 `faces.json` 之 `dom` 所指）仍在
     ∧ `onclick="paSysOpen()"` 未改。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_sys_top_1801.py -q
"""
from __future__ import annotations

import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "web" / "pa.html"
SYS = ROOT / "web" / "pa" / "faces" / "sys.js"
FACES = ROOT / "web" / "pa" / "faces.json"


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _div_block(s: str, i: int) -> str:
    u"""自 `s[i]` 之 `<div` 起，配平取至其 `</div>`（含）—— 唯计 `<div` ／ `</div>`。"""
    j = s.index(">", i) + 1
    d = 1
    while d > 0:
        a = s.find("<div", j)
        b = s.find("</div>", j)
        assert b > 0, u"div 不配平"
        if a != -1 and a < b:
            d += 1
            j = a + 4
        else:
            d -= 1
            j = b + 6
    return s[i:j]


def _block_of(h: str, cls: str) -> str:
    i = h.index(u'class="' + cls + u'"')
    return _div_block(h, h.rindex("<div", 0, i))


def _one_step_reachable(h: str, eid: str) -> bool:
    u"""一步可达 ＝ 其标签**在盘上** ∧ **⛔ 在 `#paMorePanel` 之内**（二级菜单之判 · 一处定形）。"""
    if (u'id="' + eid + u'"') not in h:
        return False
    return (u'id="' + eid + u'"') not in _block_of(h, "more")


def test_P1_top_bar_not_in_menu():
    h = _read(HTML)
    assert u'id="paSysTop"' in h, u"#paSysTop 须在盘上（顶栏入口）"
    assert _one_step_reachable(h, "paSysTop"), \
        u"#paSysTop ⛔ 得在「更多」之内（那正是病 —— pm_1801 §一）"
    assert u'id="paSysTop"' in _block_of(h, "top-right"), u"#paSysTop 须在 .top-right 内"
    tr = _block_of(h, "top-right")
    assert tr.index(u'id="paSysTop"') < tr.index(u'id="paUpdGo"'), \
        u"#paSysTop 须居 .top-right 之**首**（左端永在视口内 · 承 pm_1792 之族律）"


def test_P2_one_click_opens_the_face():
    h = _read(HTML)
    assert u'onclick="paSysTopOpen()"' in h, u"点须接 paSysTopOpen"
    j = _read(SYS)
    assert u"function paSysTopOpen(" in j, u"paSysTopOpen 须定义于 faces/sys.js（一处定形）"
    seg = j[j.index(u"function paSysTopOpen("):]
    seg = seg[:seg.index(u"\n}")]
    for k, why in ((u"paMore(true)", u"须开「更多」（否则面在收起之菜单内 ＝ 点了像没点）"),
                   (u"paMoreGrpSet", u"须开 ③ 设 之组（其面在此组内 · 默认收起）"),
                   (u"paSysOpen()", u"须展面（⛔ 只翻菜单）"),
                   (u"scrollIntoView", u"须滚入视口（否则在菜单下方不可见）")):
        assert k in seg, k + u" —— " + why
    assert u"window.paSysTopOpen = paSysTopOpen" in j, u"须导出 window.paSysTopOpen（onclick 可达）"


def test_P3_boundary_words_kept():
    h = _read(HTML)
    tag = h[h.index(u'id="paSysTop"'):]
    tag = tag[:tag.index(u">")]
    for k in (u"唯本机", u"只读", u"取一次"):
        assert k in tag, u"#paSysTop 之 title 须载「" + k + u"」（⛔ 因显眼而失其界 · pm_1801 §一）"


def test_P4_chat_face_entry_same_function():
    h = _read(HTML)
    assert u'id="paChatSysGo"' in h, u"聊天面须有可点之入口（pm_1801 §一 并办）"
    assert u'id="paChatSysGo"' in _block_of(h, "composer"), u"#paChatSysGo 须在 .composer 之内"
    seg = h[h.index(u'id="paChatSysGo"'):]
    seg = seg[:seg.index(u">")]
    assert u'onclick="paSysTopOpen()"' in seg, u"须走**同一函数**（一处定形 · ⛔ 二套）"
    row = h[h.index(u'id="paChatNoHand"'):]
    row = row[:row.index(u"</div>")]
    assert u"不出手" in row, u"其行须明书「聊天不出手」（静态真话 · ⛔ 猜意图）"


def test_P5_control_old_entry_still_in_menu():
    h = _read(HTML)
    assert _one_step_reachable(h, "paSysOpen") is False, \
        u"反控：旧入口 #paSysOpen 仍须在「更多」之内 —— 否则本判据之分辨力已失（须重审）"
    assert u'id="paSys"' in _block_of(h, "more"), u"反控：承器 #paSys 仍在菜单内（面之所在）"


def test_P6_legacy_gates_still_hold():
    h = _read(HTML)
    assert u'onclick="paSysOpen()"' in h, u"旧入口之 onclick 未改（承 pm_1751／1753）"
    d = json.loads(_read(FACES))
    face = [f for f in d.get("faces") or [] if f.get("id") == "sys"]
    assert face, u"面册须仍载 sys 面"
    for pt in (face[0].get("dom") or []):
        assert pt.startswith(u"#") and (u'id="' + pt[1:] + u'"') in h, \
            u"面册 dom 指 " + pt + u" ⇒ ⛔ 得悬空（承 tests/unit/test_pa_ui_faces.py）"