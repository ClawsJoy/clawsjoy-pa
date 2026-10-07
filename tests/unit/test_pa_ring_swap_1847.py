# -*- coding: utf-8 -*-
u"""pm_1847 §二（采 ⒜ 换位）＋ §二.2（行 3 之「开机」去处）之齿。

事由：PM 令 1847 §二：**⒝「④ 面」之归位 —— 采 ⒜（换位）**：
  ① 产品线 ⇒ 入**主面环**（替「环境」之环位 —— 一手 `/v9/pa/lines ⇒ count:3` 有真数，老板之实用）；
  ② 环境 ⇒ 降「更多 ▾」之**首**（＝工程内部读数面 · 与 pm_1822 §二.1 之「左栏数字墙」同族）；
  ③ **环仍 `5`**（今日 ／ 会话 ／ 任务 ／ 产品线 ／ 收口）∧ `Alt+1…5` 不变 ∧ 环境面仍**一步可达**；
  ④ ⛔ 采 ⒝（环 7 破 ≤5 之裁）／ ⛔ 采 ⒞（仍二跳 · 违令）／ ⛔ 采 ⒟（顶栏无余量）。
  ＋ §二.2：行 3（在等的）落「开机 ›」之**去处钮**（其**数**入行 3 归 `9.0.10` —— 须 TD 于
  `core/pa/today.py` 增源 ⇒ ⛔ 我越域 ⇒ 本批唯落**去处**）。

判据（静态闸 · 与真 Chrome 之几何证互补）：
  P1 换位之实（一处定形）：`tasks.js` 之 `PA_XFACE` 之旗 —— `env === false` ∧ `lines === true`
     （旗为**唯一**之环内外之真源 ⇒ 环 ／ 抽屉之诸处皆自旗出）。
  P2 环仍 5 ∧ 两名：环内（旗 true）＝ 产品线 ／ 收口；环外（旗 false）＝ 环境 ／ 开机；
     `PA_V3_FACES`（今日 ／ 会话 ／ 任务）＋ 环内 2 ＝ **5**（⛔ 破 pm_裁_主面环≤5）。
  P3 名单**由旗处生**（⛔ 手搓）：`paXMoreHost()` 载 `PA_XFACE.filter(...f[3] === false)` ∧
     其 `summary` 由 `_out.join(' ／ ')` 出 ⇒ 盘上 ⛔ 载手搓之「④ 面 · 产品线」／「④ 面 · 环境」
     （换位后自跟 ⇒ 手搓必致辞与实不符）。
  P4 一步可达（⛔ 二跳）：`paXOpenFace(id)` ＝ `setFaceById(id)` ＋ `paMore(false)`（面开即收抽屉 ·
     ⛔ 挡面）∧ 环外之钮接之 ∧ `#paXMoreFaces` 注入 `#paMoreBody` 之**首**。
  P5 行 3 之「开机」去处：`pa.html` 载 `#paTodayWaitResume`（于「在等的」之 `.mline` 内 ∧
     `onclick="paTodayGo('resume')"` ∧ `title` 载「唯本机」）；`today.js` 之 `paTodayGo` 载
     `'resume'` 支且走 `paXOpenFace('resume')`；⚠ 且 `today.js` **⛔ 载** `/v9/pa/resume`
     （＝ ⛔ 前端自拼端 ⇒ 其数入行 3 归 `9.0.10` · 承 PM 之裁）。
  P6 旧闸仍立（⛔ 丢功能）：`PA_XFACE` 仍 **4** 面（env ／ lines ／ resume ／ receipt）∧
     环内 ／ 环外**皆建 pane**（`pane.setAttribute('data-face', id)` · `id = f[0]` 逐字不变）∧
     `paXFaceHooks` 之四钩仍在 ∧ `paV3Dom` 仍以 `data-face` 定 `aria-pressed`。
  P7 反控（本闸真能捕病）：以**旧旗**（`env:true` ／ `lines:false` 之逐字）走 P1 ／ P2 之判据 ⇒
     必败（⇒ 若有人换回旧位 ⇒ 齿必咬）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_ring_swap_1847.py -q
"""
from __future__ import annotations

import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "web" / "pa.html"
TASKS = ROOT / "web" / "pa" / "faces" / "tasks.js"
TODAY = ROOT / "web" / "pa" / "faces" / "today.js"

# ⛔ 反控之料：**旧旗**（＝ 本件改前之逐字四行 · env ／ lines 二者之旗互换）。
_OLD_FLAGS = u"""
  ['env',     '环境',   '环境感知面 · 四栏（agents ／ kb ／ tools ／ resources）· 源 GET /v9/pa/env', true],
  ['lines',   '产品线', '产品线面（线名 ／ 席 ／ 件集 ／ 状态 ／ 下一拍）· 源 GET /v9/pa/lines', false],
  ['resume',  '开机',   '开机面（断点续：上次断点 ／ 离线区间 ／ 攒件 ／ 续办 ／ 幂等跳过 ／ 失败件）· 源 GET /v9/pa/resume', false],
  ['receipt', '收口',   '收口面（四段 ＋ 回执四件（件号／席／果／印）＋ 催数 · 每件自带件之刻）· 源 GET ／ POST /v9/pa/dispatch/receipt', true]
"""


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _rows(src: str) -> list:
    u"""自 `PA_XFACE` 之数组字面取四行 ⇒ [(id, label, desc, ring_bool), …]。"""
    i = src.index(u"const PA_XFACE = [")
    j = src.index(u"];", i)
    seg = src[i:j]
    rows = []
    for m in re.finditer(
            r"\[\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*(true|false)\s*\]", seg):
        rows.append((m.group(1), m.group(2), m.group(3), m.group(4) == u"true"))
    return rows


def _split(rows: list) -> tuple:
    ring = [r for r in rows if r[3]]
    out = [r for r in rows if not r[3]]
    return ring, out


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


def test_P1_flags_swapped():
    rows = _rows(_read(TASKS))
    d = dict((r[0], r) for r in rows)
    assert u"env" in d and u"lines" in d, u"PA_XFACE 须仍载 env ／ lines"
    assert d[u"env"][3] is False, u"`env` 之旗须 `false`（环境 ⇒ 降「更多 ▾」之首 · pm_1847 §二.1）"
    assert d[u"lines"][3] is True, u"`lines` 之旗须 `true`（产品线 ⇒ 入主面环 · pm_1847 §二.1）"


def test_P2_ring_still_five():
    rows = _rows(_read(TASKS))
    ring, out = _split(rows)
    assert [r[1] for r in ring] == [u"产品线", u"收口"], u"环内（旗 true）须为 产品线 ／ 收口"
    assert [r[1] for r in out] == [u"环境", u"开机"], u"环外（旗 false）须为 环境 ／ 开机"
    j = _read(TODAY)
    i = j.index(u"const PA_V3_FACES = [")
    k = j.index(u"];", i)
    base = len(re.findall(r"\{id:", j[i:k]))
    assert base == 3, u"`PA_V3_FACES` 须仍 3（今日 ／ 会话 ／ 任务）"
    assert base + len(ring) == 5, u"环仍 5（⛔ 破 pm_裁_主面环≤5 · ⛔ 采 ⒝ 之环 7）"


def test_P3_list_born_of_flags():
    j = _read(TASKS)
    i = j.index(u"function paXMoreHost()")
    seg = j[i:i + 2200]
    assert u"PA_XFACE.filter" in seg, u"④ 面之名单须**由旗处生**（`PA_XFACE.filter` · ⛔ 手搓）"
    assert u"f[3] === false" in seg, u"须以**旗**取环外者（一处定形）"
    assert u"_out.join(" in seg, u"`summary` 须由所取之名单拼出（换位后自跟）"
    assert u"④ 面 · 产品线" not in j, u"⛔ 得手搓「④ 面 · 产品线」（换位后必致辞与实不符）"
    assert u"④ 面 · 环境" not in j, u"⛔ 得手搓「④ 面 · 环境」（同上）"
    assert u"<p class=\"mnote\">源：<code>GET /v9/pa/lines</code>" not in j, \
        u"旧之手搓「源：…」须已拔（今自 `f[2]` 之端名出）"


def test_P4_one_step_reachable():
    j = _read(TASKS)
    i = j.index(u"function paXOpenFace(id)")
    seg = j[i:j.index(u"\n}", i)]
    assert u"setFaceById(id)" in seg, u"paXOpenFace 须开其面"
    assert u"paMore(false)" in seg, u"面开须**收抽屉**（⛔ 挡面）"
    k = j.index(u"function paXMoreHost()")
    tail = j[k:k + 2600]
    assert u"body.insertBefore(box, body.firstChild)" in tail, \
        u"④ 面之组须注入 `#paMoreBody` 之**首**（环境 ⇒ 「更多 ▾」之首 · pm_1847 §二.1）"
    assert u"paXOpenFace(id)" in j, u"环外之钮须接**同一函数**（⛔ 二套开面之路）"


def test_P5_wait_row_resume_button():
    h = _read(HTML)
    assert u'id="paTodayWaitResume"' in h, u"行 3 须有「开机 ›」之去处钮（pm_1847 §二.2）"
    i = h.index(u'id="paTodayWait"')
    blk = _div_block(h, h.rindex(u"<div", 0, i))
    assert u'id="paTodayWaitResume"' in blk, u"#paTodayWaitResume 须在「在等的」之**同一行**内"
    assert u'id="paTodayWaitGo"' in blk, u"「看进度 ›」须仍在（⛔ 丢功能）"
    tag = blk[blk.index(u'id="paTodayWaitResume"'):]
    tag = tag[:tag.index(u">")]
    assert u'onclick="paTodayGo(\'resume\')"' in tag, u"点须接 `paTodayGo('resume')`"
    assert u"唯本机" in tag, u"title 须明书界（唯本机 · 只读）"
    j = _read(TODAY)
    k = j.index(u"function paTodayGo(kind)")
    seg = j[k:j.index(u"\n}", k)]
    assert u"'resume'" in seg, u"paTodayGo 须载 `'resume'` 支"
    assert u"paXOpenFace('resume')" in seg, u"该支须开**开机面**（一处定形）"
    assert not re.search(r"""['\"]/v9/pa/resume['\"]""", j), \
        u"⚠ today.js ⛔ 得**取**其端（`'/v9/pa/resume'` 之引号串）—— 其**数**入行 3 归 9.0.10" \
        u"（须 TD 于 core/pa/today.py 增源 ⇒ ⛔ 我越域）；注中提其端名（⛔ 引号）不犯"


def test_P6_old_guards_still_stand():
    j = _read(TASKS)
    rows = _rows(j)
    assert len(rows) == 4, u"PA_XFACE 须仍 4 面（⛔ 丢功能）"
    assert [r[0] for r in rows] == [u"env", u"lines", u"resume", u"receipt"], u"其 id 逐字不变"
    assert u"pane.setAttribute('data-face', id)" in j, u"环内 ／ 环外**皆建 pane**（⛔ 丢功能）"
    assert u"var id = f[0], label = f[1], title = f[2], ring = (f[3] !== false);" in j, \
        u"环内外之分唯由旗（一处定形）"
    for hook in (u"paXFaceHooks.env", u"paXFaceHooks.lines", u"paXFaceHooks.resume", u"paXFaceHooks.receipt"):
        assert hook in j, u"取数之钩须仍在：" + hook
    t = _read(TODAY)
    assert u"b.setAttribute('aria-pressed', String(b.getAttribute('data-face') === id));" in t, \
        u"paV3Dom 仍以 `data-face` 定当前态（环内外同源）"


def test_P7_control_old_flags_fail():
    u"""反控：**旧旗**走同一判据 ⇒ 必败。"""
    rows = _rows(u"const PA_XFACE = [" + _OLD_FLAGS + u"];")
    d = dict((r[0], r) for r in rows)
    assert d[u"env"][3] is True, u"反控：旧旗之 env 为 true ⇒ P1 之判据必败"
    assert d[u"lines"][3] is False, u"反控：旧旗之 lines 为 false ⇒ P1 之判据必败"
    ring, out = _split(rows)
    assert [r[1] for r in ring] == [u"环境", u"收口"], u"反控：旧形之环内为 环境 ／ 收口 ⇒ P2 之判据必败"
    assert [r[1] for r in out] == [u"产品线", u"开机"], u"反控：旧形之环外为 产品线 ／ 开机 ⇒ P2 之判据必败"