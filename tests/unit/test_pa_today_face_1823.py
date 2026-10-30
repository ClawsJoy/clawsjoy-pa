# -*- coding: utf-8 -*-
u"""pm_1823 ＋ pm_1827 之齿 —— 「今日」一屏之**四行**（**面**之齿）。

事由：老板之屏（PM 一手 · CDP 真读 · 刻 02:06:39）见**三个空壳** —— 「🧠 画像 … ／ 📋 待你裁 0 件 ·
  后台任务 0 件 ／ 🕒 昨夜整合 未知 —— 这个还没接上…」⇒ **「今天干什么」无 ／「在等的」无**。
定义页：《「今日」一屏之定义 v1》§二（四行 · 序）／§三（每行必带 数 ／ 源 ／ 去处）／§四（⛔ 不做）。
取数：**唯走 `GET /v9/pa/today` 一处**（pm_1827 §一 —— ⛔ 前端自拼各端；四类之判据唯在
  `core/pa/today.py` 一处 · pm_1824 §二.1）。

判据（静态闸 · 与 CDP 真点之证互补）：
  P1 四行在盘 ∧ **按定义页 §二 之序**。
  P2 每行三物齐：**数**（`paToday<Cap>`）／**源**（`paToday<Cap>Where` · 行内＝**人话**
     （`paTodaySrcLabel` ⇒ `PA_TODAY_SRC_HUMAN`）∧ 真源之端名／径 ⇒ **详情**与悬停 `title`
     （`paTodaySrcEnd` ／ `paTodaySrcTip`）· pm_1829 §二.3「一名二形 ⇒ 统一」）／
     **去处**（`paToday<Cap>Go` ⇒ `paTodayGo('<kind>')`）。
  P3 画像**降位**（§二 ⚠）：`#paTodayProfile` 在四行**之下** ∧ 其行 `.sub`。
  P4 空态之人话：取**一处之源**（后端 `空态` 之键）—— 反控：该四句仍在 `core/pa/today.py`（⛔ 删真源）。
  P5 ⛔ 内部缩写 ／ ⛔ 自曝之辞：四行之作码与屏上段内命中 `0`（§四.2 ／ §四.3）。
  P6 一处定形：`paTodayGo` 全树唯一定义 ∧ 四支各到**办之处** ∧ `.go` 之钮**皆**有 `onclick`。
  P7 **反控**：旧形（「📋 待你裁 …」独立一行 ∧ `#paTodayPending` 在盘）**已撤** —— 若搬回 ⇒ P1 ／ P2 必败。
  P8 取数**一处**（pm_1827 §一）：`GET /v9/pa/today` 之取唯**一处**（⛔ 四行各拼各端）∧ 其 `缺` 之键
     ⇒ **人话**（⛔ 照抄内部径 ／ `file:line`）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_today_face_1823.py -q
"""
from __future__ import annotations

import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "web" / "pa.html"
TODAY = ROOT / "web" / "pa" / "faces" / "today.js"
CORE_TODAY = ROOT / "core" / "pa" / "today.py"

ROWS = [u"要我拍的", u"今天该做的", u"在等的", u"近来之痕"]           # 序不可易（定义页 §二）
EMPTY = [u"没有等你拍的事", u"今天没有非做不可的", u"手上没有在等的事", u"昨天没有可记之事"]
JARGON = [u"(b)", u"(bg)", u"PES", u"启核"]                          # 定义页 §四.2
SELF_EXPOSE = [u"未接", u"尚无后端读数", u"这个还没接上"]               # 定义页 §四.3


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _fn(src: str, sig: str) -> str:
    i = src.index(sig)
    j = src.index("{", i)
    d = 0
    for k in range(j, len(src)):
        c = src[k]
        if c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                return src[i:k + 1]
    raise AssertionError("unbalanced: " + sig)


def _today_block(h: str) -> str:
    u"""今日面之段（`#paToday` ⇒ 主面②之始）—— 唯此段是「今日一屏」。"""
    return h[h.index(u'<div class="today" id="paToday">'):h.index(u'id="paFaceChat"')]


def _rows_src(j: str) -> str:
    u"""四行之作码段（去处 ／ 取数 ／ 渲 ＋ 其调用处）—— 唯此段判「⛔ 内部缩写 ／ ⛔ 自曝之辞」。"""
    a = j.index(u"/* ⭐⭐ pm_1823 §二 ＋ pm_1827 §一.2（要）")
    b = j.index(u"function paSrcToggle(){", a)
    a2 = j.index(u"  /* ⭐⭐ pm_1823 §二 ＋ pm_1827 §一（要）")
    b2 = j.index(u"  /* ⭐ 素材七面之三改", a2)
    return j[a:b] + u"\n" + j[a2:b2]


def test_P1_four_rows_in_order():
    seg = _today_block(_read(HTML))
    assert u"🌤 今日" in seg, u"本面须自称「今日」（⛔ 自述 ／ ⛔ 仪表盘）"
    pos = [seg.index(u">" + r + u"<") for r in ROWS]
    assert pos == sorted(pos), u"四行须按定义页 §二 之序（要我拍的 ⇒ 今天该做的 ⇒ 在等的 ⇒ 近来之痕）"


def test_P2_each_row_has_count_src_go():
    seg = _today_block(_read(HTML))
    for cap, kind in ((u"Ask", u"ask"), (u"Do", u"do"), (u"Wait", u"wait"), (u"Trace", u"trace")):
        assert u'id="paToday' + cap + u'"' in seg, u"须有**数**之格：paToday" + cap
        assert u'id="paToday' + cap + u'Where"' in seg, u"须有**源**之格（行内）：paToday" + cap + u"Where"
        assert u'id="paToday' + cap + u'Go"' in seg, u"须有**去处**之钮：paToday" + cap + u"Go"
        assert u"paTodayGo('" + kind + u"')" in seg, u"去处须接线 paTodayGo('" + kind + u"')"
    j = _read(TODAY)
    assert u"+ 'Where', r ? ('源：' + paTodaySrcName(r))" in j, \
        u"每行之**源**须取后端 `源[].面`（⛔ 前端自说）"
    end = _fn(j, u"function paTodaySrcEnd(s){")
    assert u"['面']" in end, u"源之真形须取后端之「面」（一处定形）"
    assert u"GET\\s+" in end and u"本机档案" in end, \
        u"源之真形：唯**面里真带 `GET `** 者方书 `GET …`；余（读盘 ⇒ 无端）⇒「本机档案」\n"\
        u"        （⛔ 凭路径形状编出端名 —— 那不实之辞入屏 · 承 pm_1827 §一.3）"
    lbl = _fn(j, u"function paTodaySrcLabel(s){")
    assert u"PA_TODAY_SRC_HUMAN" in lbl and u"GET /v9" not in lbl, \
        u"行内之**源**＝**人话**（⛔ 端名上屏 —— pm_1829 §二.3「一名二形 ⇒ 统一」）；"\
        u"端名与径 ⇒ 唯入「详情」／悬停 `title`（反控 · ⛔ 删真源）"
    assert j.count(u"paTodaySrcEnd(") >= 3, u"源之真形须一处出（⛔ 各点各拼）"


def test_P3_profile_is_below_the_four_rows():
    seg = _today_block(_read(HTML))
    assert seg.index(u'id="paTodayProfile"') > seg.index(u'id="paTodayTrace"'), \
        u"「画像」（我是谁）⛔ 得占四行之位（定义页 §二 ⚠ ⇒ 降为第二屏）"
    mid = seg[seg.index(u'id="paTodayTrace"'):seg.index(u'id="paTodayProfile"')]
    assert u"mline sub" in mid, u"画像之行须为 .sub（四行之下）"


def test_P4_empty_state_is_from_one_source():
    j = _read(TODAY)
    assert u"r['空态']" in j, u"空态之人话须取**一处之源**（后端 `空态` 之键 · 承 pm_1827 §一）"
    assert u"n == null" in j and u"暂时读不到" in j, u"空 ⛔ 混 缺：数缺 ⇒ 明说（⛔ 落「空态」之人话）"
    c = _read(CORE_TODAY)                      # 反控：该四句仍在真源（⛔ 删真源）
    for s in EMPTY:
        assert s in c, u"反控：空态之人话须仍在真源 core/pa/today.py：" + s


def test_P5_no_jargon_no_self_expose_in_rows():
    seg = _rows_src(_read(TODAY))
    for k in JARGON + SELF_EXPOSE:
        assert k not in seg, u"四行之作码 ⛔ 载：" + k
    hseg = _today_block(_read(HTML))
    for k in JARGON + SELF_EXPOSE:
        assert k not in hseg, u"今日面之屏上段 ⛔ 载：" + k


def test_P6_go_one_place_and_all_buttons_wired():
    seg = _today_block(_read(HTML))
    btns = re.findall(r'<button[^>]*class="go"[^>]*>', seg)
    assert len(btns) >= 5, u"四行 ＋「去「任务」面逐条办」皆须有去处之钮（§三：缺去处 ＝ 未做完）"
    for bt in btns:
        assert u"onclick=" in bt, u"去处之钮须**真可点**（⛔ 空钮）：" + bt
    n = 0
    for p in (ROOT / "web").rglob("*.js"):
        if ".before_" in p.name:
            continue
        n += _read(p).count(u"function paTodayGo(")
    assert n == 1, u"`paTodayGo` 须**一处定形**（今之数 ＝ %d）" % n
    g = _fn(_read(TODAY), u"function paTodayGo(kind){")
    assert u"paTodayToggle(kind)" in g, u"要我拍的 ／ 近来之痕 ⇒ **就地展开**（后端 `端` 所标之 `#paToday`）"
    assert u"setFaceById('tasks')" in g, u"去办 ／ 看进度 ⇒「任务」面"
    assert u"kind === 'ask' || kind === 'trace'" in g, u"四支须各别判（⛔ 一锅）"


def test_P7_counter_control_old_shape_gone():
    seg = _today_block(_read(HTML))
    assert u'id="paTodayPending"' not in seg, \
        u"反控：旧形「📋 待你裁 0 件 · 后台任务 0 件」为独立一行（今已并入「要我拍的」／「在等的」）—— 若搬回 ⇒ P1 ／ P2 必败"
    assert u">待你裁<" not in seg, u"反控：旧行名「待你裁」⛔ 得再据主位"


def test_P8_one_place_fetch_and_missing_is_human():
    j = _read(TODAY)
    assert j.count(u"paGetJson(API + '/v9/pa/today')") == 1, \
        u"四行之取数须**唯一一处**（`GET /v9/pa/today` · ⛔ 前端自拼各端 · 承 pm_1827 §一）"
    d = _fn(j, u"function paTodayDetail(r){")
    assert u"['缺']" in d and u"这一项暂时读不到" in d, \
        u"后端 `缺` 之键 ⇒ **人话**（⛔ 照抄内部径 ／ `file:line` · 承 pm_1827 §一.1）"
    assert u"['因']" not in d and u"['据']" not in d, u"`缺` 之 `因` ／ `据`（内部径 ／ `file:line`）⛔ 上屏"