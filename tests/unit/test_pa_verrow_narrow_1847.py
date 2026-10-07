# -*- coding: utf-8 -*-
u"""pm_1847 §四 之齿 —— 1024 一族状态行逾槽（版行末字被裁 · 「点此更新」不可见）之**断源**。

事由：PM 令 1847 §四.1（认缺陷 · 归 9.0.9 · 即刻办）：1024 一族 `.statusline` 之内容逾其槽
  （一手：现值态 13.47 px ／ 「有新版」态 94.37 px）⇒ 版行末字被裁 ∧ 「点此更新」四字不可见。
⭐⭐ 我一手之**断源**（真 Chrome ＋ CDP）：病根在「**槽**」而**不在「件」** —— 入口侧之
  「⬆ 更新到 9.0.9（约 1.1 MB）」（`#paUpdGo` · 一手 211.34 px）一现 ⇒ 状态行所分得之槽唯
  `69.95 px`（真辞）／ `233.80 px`（无钮），而版行最长之辞 `247.42 px` ⇒ **槽 < 内容**
  ⇒ 与「件」无涉 ⇒ PM §四.2 之两法（收非必要子件 ∨ 令 `.verrow` 随宽收）**皆不足**
  （二者治件 · 而槽未动：纵尽收诸件，1024 之槽亦唯得 `233.80 px`）。
⇒ 本件之修（断源）：**顶栏容不下 ⇒ 状态行独占一行**（`.topbar` 于容不下时换行 ∧ `.statusline`
  立其最小内容宽 `460 px`）＋ 版行**去其 `max-width` 硬帽** ＋ 状态行内之**让位之序**
  （`#paUiStateRow` 占余量而 ⛔ 挤人 ／ `#runStateSrc` 末位让位）—— ⛔ 收版行 ／ ⛔ 收更新钮。
  一手（真 Chrome · 七档宽 × 四辞）：1440 ＝ **单行**（制高 `46 px` · 槽 `705.30` ／ `485.95`
  一字未变）；1024 ／ 1180 ＝ 状态行独占一行（槽 `881.77` ／ `1037.77` ⇒ 版行全字可见）。

判据（静态闸 · 与真 Chrome 之几何证互补）：
  P1 断源（槽）：`.topbar` 载换行（`flex-wrap:wrap`）∧ 用 `min-height`（⛔ `height` 硬高）；
     `.statusline` 载 `min-width:min(460px,100%)`。
  P2 ⛔ 收版行：`.verrow` 之规则**⛔ 载 `max-width`** ∧ 1180 之媒体块**⛔ 载 `.verrow`**
     （旧形之 `190 px` 硬帽 —— 那正是把「点此更新」裁没者）。
  P3 让位之序（一处定形）：`.statusline .uis` 载 `flex:1 1 0`（占余量 · ⛔ 以其内容挤人 ⇒ 否则
     同排紧张时它先取其内容宽而反逼末位子件被裁）∧ `.statusline .runstate-src` 载
     `flex:0 1 auto` ＋ `min-width:0`（末位让位 · 一手：1440 两态其宽皆 `130.64` **未缩**）。
  P4 旧闸仍立：`.statusline>*` 仍 `flex:0 0 auto`（版行恒**不让** ⇒ 唯它永不被裁）∧
     `.statusline` 仍 `overflow:hidden`（裁之器仍在 ⇒ 判据 ⛔ 因撤器而假绿）∧ `#paVerRow` ／
     `#paUpdGo` 仍在盘上 ∧ ≤1180 之 `#paUiStateRow{display:none}`（前件）仍在。
  P5 反控（本闸真能捕病）：以**旧形**（`_OLD` ＝ HEAD 之逐字五行）走**同一判据** ⇒ P1 ／ P2 必败。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_verrow_narrow_1847.py -q
"""
from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "web" / "pa" / "pa_v3.css"
HTML = ROOT / "web" / "pa.html"

# ⛔ 反控之料：**旧形**（＝ `git show HEAD:web/pa/pa_v3.css` 之逐字 —— 本件改前之形）。
_OLD = u"""
.topbar{height:46px;gap:12px}
.statusline{flex:1;min-width:0;display:flex;align-items:center;gap:7px;font-size:11px;color:var(--sub);
  white-space:nowrap;overflow:hidden}
.statusline .uis{flex:1 1 auto;min-width:0}
.statusline>*{flex:0 0 auto;white-space:nowrap}
.verrow{color:var(--sub);font-variant-numeric:tabular-nums;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;max-width:290px}
@media (max-width:1180px){ .verrow{max-width:190px} }
"""


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _strip_comments(css: str) -> str:
    u"""去 `/* … */` —— 本件之注**大段引其旧值**（`190 px` ／ `290 px`）⇒ ⛔ 不清则判据假阳。"""
    out = []
    i = 0
    while True:
        a = css.find(u"/*", i)
        if a < 0:
            out.append(css[i:])
            return u"".join(out)
        b = css.find(u"*/", a + 2)
        assert b > 0, u"CSS 注释不配平"
        out.append(css[i:a])
        i = b + 2


def _decls(body: str) -> dict:
    d = {}
    for part in body.split(u";"):
        if u":" not in part:
            continue
        k, v = part.split(u":", 1)
        d[k.strip().lower()] = v.strip()
    return d


def _rules(css: str, sel: str) -> list:
    text = _strip_comments(css)
    key = sel + u"{"
    out = []
    i = 0
    while True:
        a = text.find(key, i)
        if a < 0:
            return out
        b = text.index(u"}", a)
        out.append(text[a + len(key):b])
        i = b + 1


def _merged(css: str, sel: str) -> dict:
    d = {}
    for body in _rules(css, sel):
        d.update(_decls(body))
    return d


def _media_inners(css: str, cond: str) -> list:
    text = _strip_comments(css)
    key = u"@media (" + cond + u"){"
    out = []
    i = 0
    while True:
        a = text.find(key, i)
        if a < 0:
            return out
        j = a + len(key)
        depth = 1
        while depth > 0:
            c = text.find(u"{", j)
            e = text.find(u"}", j)
            assert e > 0, u"媒体块不配平"
            if c != -1 and c < e:
                depth += 1
                j = c + 1
            else:
                depth -= 1
                j = e + 1
        out.append(text[a + len(key):j - 1])
        i = j


def verdicts(css: str) -> dict:
    u"""**同一判据** —— 对任一 CSS 文本皆可判（反控即以此对旧形复核）。"""
    tb = _merged(css, u".topbar")
    sl = _merged(css, u".statusline")
    vr = _merged(css, u".verrow")
    ui = _merged(css, u".statusline .uis")
    rs = _merged(css, u".statusline .runstate-src")
    star = _merged(css, u".statusline>*")
    return {
        u"P1a_topbar_wrap": tb.get(u"flex-wrap") == u"wrap",
        u"P1b_topbar_auto_h": (tb.get(u"height") in (None, u"auto")) and (u"min-height" in tb),
        u"P1c_slot_min": sl.get(u"min-width", u"").startswith(u"min(") and (u"460px" in sl.get(u"min-width", u"")),
        u"P2a_verrow_no_cap": u"max-width" not in vr,
        u"P2b_narrow_no_verrow": not any(u".verrow" in b for b in _media_inners(css, u"max-width:1180px")),
        u"P3a_uis_flex0": ui.get(u"flex", u"").split() == [u"1", u"1", u"0"],
        u"P3b_rss_yield": (rs.get(u"flex", u"").split() == [u"0", u"1", u"auto"]) and (rs.get(u"min-width") == u"0"),
        u"P4a_star_noshrink": star.get(u"flex", u"").split() == [u"0", u"0", u"auto"],
    }


def test_P1_defect_root_slot():
    v = verdicts(_read(CSS))
    assert v[u"P1a_topbar_wrap"], u"顶栏须**容不下即换行**（`.topbar{flex-wrap:wrap}` · pm_1847 §四 之断源）"
    assert v[u"P1b_topbar_auto_h"], u"顶栏须以 `min-height` 立底（⛔ `height:46px` 硬高 ⇒ 换行必被裁）"
    assert v[u"P1c_slot_min"], u"`.statusline` 须立**最小内容宽**（`min-width:min(460px,100%)` · 槽之断源）"


def test_P2_version_row_not_clipped():
    v = verdicts(_read(CSS))
    assert v[u"P2a_verrow_no_cap"], u"版行 ⛔ 得载 `max-width` 硬帽（旧 `290px` ／ ≤1180 之 `190px` 即裁「点此更新」者）"
    assert v[u"P2b_narrow_no_verrow"], u"1180 之媒体 ⛔ 得再写 `.verrow`（⛔ 收版行）"


def test_P3_yield_order():
    v = verdicts(_read(CSS))
    assert v[u"P3a_uis_flex0"], u"`#paUiStateRow` 须 `flex:1 1 0`（占余量 · ⛔ 以其内容挤末位子件）"
    assert v[u"P3b_rss_yield"], u"`#runStateSrc` 须 `flex:0 1 auto` ＋ `min-width:0`（末位让位）"


def test_P4_old_guards_still_stand():
    css = _read(CSS)
    v = verdicts(css)
    assert v[u"P4a_star_noshrink"], u"`.statusline>*{flex:0 0 auto}` 仍须在（版行恒不让 ⇒ 唯它永不被裁）"
    assert _merged(css, u".statusline").get(u"overflow") == u"hidden", \
        u"`.statusline{overflow:hidden}` 仍须在 —— ⛔ 以**撤其裁器**充「未被裁」"
    narrows = _media_inners(css, u"max-width:1180px")
    assert any(u".statusline .uis" in b and u"display:none" in b for b in narrows), \
        u"前件仍在：≤1180 之 `#paUiStateRow{display:none}`（pm_1847 前之形 · ⛔ 被我撤）"
    h = _read(HTML)
    for eid in (u"paVerRow", u"paUpdGo"):
        assert (u'id="' + eid + u'"') in h, u"#" + eid + u" 须仍在盘上（⛔ 丢功能）"


def test_P5_control_old_form_fails():
    u"""反控：**旧形**走同一判据 ⇒ 必败（否则本闸无分辨力 ⇒ 须重审）。"""
    v = verdicts(_OLD)
    for k in (u"P1a_topbar_wrap", u"P1b_topbar_auto_h", u"P1c_slot_min",
              u"P2a_verrow_no_cap", u"P2b_narrow_no_verrow", u"P3b_rss_yield"):
        assert v[k] is False, u"反控：旧形之 " + k + u" 必为 False（本闸分辨力之证）"
    assert v[u"P4a_star_noshrink"] is True, u"反控：旧形之 `.statusline>*` 仍在 ⇒ 该判据 ⛔ 分辨此项（非本件之病）"