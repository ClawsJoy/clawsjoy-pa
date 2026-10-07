# -*- coding: utf-8 -*-
u"""pm_1792 之齿 —— 顶栏「更新」按钮之**可见性**（位置 ＋ 显眼形）。

事由：老板「**真按钮是同一行里那颗带框的「⬆ 更新」没发现这个按钮**」⇒ 病在**按钮不可见**。
  9.0.6 之原位 ＝ `.statusline` 之**末**；彼 `overflow:hidden` ⇒ 同排挤满时**末位子件被裁**
  （真 Chrome 之几何证：1024 CSS px 下其中心点之 `elementFromPoint` 命中「✉ 留言」⇒ 既不可见亦不可点）。
  今位 ＝ `.top-right` 之**首**（`flex:0 0 auto` ⇒ 左端永在视口内）＋ 显眼形一处定形於 `pa_v3.css`。

判据（静态闸 · 与真 Chrome 之几何证互补）：
  P1 分区：`#paUpdGo` 之标签于 `.top-right` 之内 ∧ **⛔** 于 `.statusline` 之内（其 div 块内 ⛔ 含其 id）。
  P2 不被压之因：`.top-right` 之开标签载 `flex:0 0 auto`（⛔ 无 ⇒ 会被 `.statusline` 之 `flex:1` 挤）。
  P3 显眼形（一处定形）：`web/pa/pa_v3.css` 之 `#paUpdGo{...}` 含 `background:` ＋ `border-color:`
     ＋ `font-weight:` ＋ 着色 `var(--amber)`（⛔ 唯默认 `.chip` 之灰）。
  P4 反控（**病之因仍在** ⇒ 本齿之前提 ⛔ 陈）：`.statusline` 之 CSS 仍含 `overflow:hidden`。
  P5 旧闸仍立（承 pm_1691 §二.1 之 S3）：`#paUpdGo` 仍为 `button` ∧ `onclick="paUpdGo()"` ∧ 初藏
     （唯 `available === true` ∧ ⛔ 在跑时现 —— 现隐由 `update.js` 之 `paUpdBtnRender` 收放）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_upd_btn_1792.py -q
"""
from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "web" / "pa.html"
CSS = ROOT / "web" / "pa" / "pa_v3.css"


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


def _rule(css: str, sel: str) -> str:
    i = css.find(sel + "{")
    assert i > 0, u"未找到规则 " + sel
    return css[i:css.index("}", i)]


def test_P1_btn_in_topright_not_statusline():
    h = _read(HTML)
    i_sl = h.index(u'class="statusline"')
    i_tr = h.index(u'class="top-right"')
    blk_sl = _div_block(h, h.rindex("<div", 0, i_sl))
    blk_tr = _div_block(h, h.rindex("<div", 0, i_tr))
    assert u'id="paUpdGo"' not in blk_sl, \
        u"#paUpdGo ⛔ 得在 .statusline 内（overflow:hidden ⇒ 挤满时被裁 —— pm_1792 §二.1）"
    assert u'id="paUpdGo"' in blk_tr, u"#paUpdGo 须在 .top-right 内"
    assert blk_tr.index(u'id="paUpdGo"') < blk_tr.index(u'id="paKeyBtn"'), \
        u"#paUpdGo 须居 .top-right 之**首**（其左端永在视口内）"


def test_P2_topright_does_not_shrink():
    h = _read(HTML)
    i_tr = h.index(u'class="top-right"')
    tag = h[h.rindex("<div", 0, i_tr):h.index(">", i_tr)]
    assert u"flex:0 0 auto" in tag, u".top-right 须 flex:0 0 auto（⛔ 则被 .statusline 之 flex:1 挤）"


def test_P3_prominent_style_one_place():
    c = _read(CSS)
    r = _rule(c, u"#paUpdGo")
    for k in (u"background:", u"border-color:", u"font-weight:", u"var(--amber)"):
        assert k in r, u"#paUpdGo 之显眼形须含 " + k + u"（一处定形於 pa_v3.css）"


def test_P4_control_statusline_still_clips():
    c = _read(CSS)
    seg = _rule(c, u".statusline")
    assert u"overflow:hidden" in seg, u"反控：.statusline 仍 overflow:hidden（病之因 —— 若改本齿须重审）"


def test_P5_legacy_button_gate_still_holds():
    h = _read(HTML)
    assert u'<button class="chip" id="paUpdGo"' in h, u"#paUpdGo 仍须为 button（承 pm_1691 S3）"
    assert u'onclick="paUpdGo()"' in h, u"点须接 paUpdGo（唯由用户之点）"
    assert u"display:none" in h.split(u'id="paUpdGo"')[1][:160], u"初藏（唯 available 时现）"