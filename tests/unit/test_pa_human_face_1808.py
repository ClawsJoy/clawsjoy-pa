# -*- coding: utf-8 -*-
u"""pm_1808 §二 之齿 —— **用户面之净化**（内部话 ⛔ 上首屏）＋ **横幅之自动退**。

事由（老板之令 ／ PM 一手 CDP）：老板开 PA 之第一屏 ＝ 一整版工程内部话
  （`PA_ORG_FACES` ／ `PA_WS_ROOT` ／ `PA_VAULT_DIR` ／ `core/lib/config_helper.py:get_data_root()`
   ／ `承 pm_1517 §一之裁` ／ 「弱保证」／「式：…」）—— ⛔ 陪伴 ∧ ⛔ 办事。
⭐ 我一手之数（CDP · `_pm/_cw_1808cdp.py`）：**用户面可见之内部话 ＝ 12 处**。

判据（静态闸 · 与 CDP 之计数互补）：
  P1 首启盒（`pa.html` 之 `box()`）：**人话在外** —— 须知之「话」／模型之路／数据目录之「值」上屏；
     其「据」／「义」／「口径」／`PA_*` 键 ⇒ 入 `details.eng`（`summary` 载「工程注记」）。
  P2 **反控（⛔ 删其数）**：上述之原字**仍须在盘**（唯去处改 —— 承 pm_1012 §二「⛔ 丢信息」）。
  P3 今日上下文之三行：`#paTodayWhen` ⛔ 载 `num_ctx`／`画像件刻`；`#paTodayProfile` ⛔ 载 `式：`／
     `GET /v9/`;`#paTodayNight` ⛔ 载 `承 pm`（工程话）—— 且原字折入**源行**（折叠处 · 仍可寻得）。
  P4 横幅：终态（`done`）须能**自退**（一处定形之阈）∧ 非终态须**撤钟**（⛔ 误隐在办之相）。
  P5 左栏摘要：**只留人话** ∧ **⛔ 数字墙**（pm_1822 §二.⒈ ＋ pm_1829 §二.2）—— 正控：静态引
     「素材 7 面 ⇒」已撤 ∧ 值内 ⛔ 载器之名；反控：逐面真数 ⇒ 仍在 `#paSrcList`（▾ · ⛔ 丢信息）。
     ⚠ `PA_UPD_RECENT_S`（`update.js` · 3600 · 承 pm_1693 §四.3）⛔ 本批 ⛔ 动（另一物：状态之窗）。

以何形调用：python -X utf8 -B -m pytest tests/unit/test_pa_human_face_1808.py -q
"""
from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "web" / "pa.html"
TODAY = ROOT / "web" / "pa" / "faces" / "today.js"
START = ROOT / "web" / "pa" / "faces" / "startup.js"
UPD = ROOT / "web" / "pa" / "faces" / "update.js"


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _box_src(h: str) -> str:
    u"""取 `pa.html` 之 `box(d)` 函数体（自 `function box(d){` 至其配平之 `}`）。"""
    i = h.index(u"function box(d){")
    j = h.index(u"\n  }", i)
    return h[i:j]


def _user_face_of_box(src: str) -> str:
    u"""首启盒之**用户面** ＝ 自 `function box(d){` 至 `var det=el('details','','')`（工程注记之前）。"""
    k = src.index(u"var det=el('details','','')")
    return src[:k]


def test_P1_first_run_box_puts_jargon_behind_a_fold():
    u"""⛔ 弃之形（pm_1808 §二.1 之原则**仍在**，唯**位**经 pm_2022 §二 ／ pm_2025 §二.3⒜ 改）：
    旧形＝人话**在外**（须知 ／ 模型之路 ／ 数据目录平铺首屏）⇒ pm_2022 逮「首屏工程墙占主区之半」
    ⇒ 今形＝首屏唯**一条可退之窄提示** ∧ 诸项（人话 ＋ 工程话）**皆入折**（折名人话「来源 ／ 详情」）。
    ⭐ 故本齿之正控改「人话之字**在盒内可渲**（折内亦可 · ⛔ 丢）」，反控照旧「工程话 ⛔ 得在折之前」。"""
    h = _read(HTML)
    src = _box_src(h)
    face = _user_face_of_box(src)
    # 正控：人话仍在（唯入折 —— ⛔ 丢信息 · ⛔ 删）
    for k, why in ((u"face(need[", u"须知之人话仍渲（唯入折）"),
                   (u"• 模型之路：", u"模型之路（人话）"),
                   (u"• 数据目录：", u"数据目录之值（唯入折 · ⛔ 丢）")):
        assert k in src, k + u" —— " + why
    # 反控：工程话 ⛔ 得在**折之前**（＝用户之屏 · pm_1808 §二.1 之原则）
    for bad in (u"['据']", u"['义']", u"['口径']", u"面之源（面数由三键定 · ⛔ 静默）"):
        assert bad not in face, bad + u" ⛔ 得在首启盒之用户面（pm_1808 §二.1）"
    # ⭐ 首屏唯窄提示（⛔ 诸项平铺 · pm_2022 §二.⒜）
    assert u"逐项在本行下方" in face, u"首屏须为一条可退之窄提示（pm_2022 §二.⒜）"
    assert u"PA_SELFDOUBT_WORD" in face, u"自我怀疑之辞须有面闸（pm_2022 §二.⒝ · ⛔ 上屏）"
    # 工程之折叠在此
    assert u"el('details'" in src and u"setAttribute('class','eng')" in src,         u"工程话须入 details.eng（折叠处 · ⛔ 删）"
    assert u"来源 ／ 详情" in src, u"折叠之 summary 须载**人话**之名（pm_2022 §二.⒞：⛔ 载「工程注记」）"
    # ⚠ 「⛔ 入首屏字面」之判**唯可取渲之字**（源码之注释亦载此四字 ⇒ 源码之判必假红）—— 见 test_pa_first_run_2022.py F1。


def test_P2_jargon_not_deleted_only_moved():
    h = _read(HTML)
    src = _box_src(h)
    tail = src[src.index(u"var det=el('details','','')"):]
    for k, why in ((u"need[i2]['据']", u"须知之「据」原字仍须在盘（唯去处改）"),
                   (u"kk['键']", u"面之源之键名仍须在盘"), (u"kk['义']", u"面之源之「义」仍须在盘"),
                   (u"['口径']", u"面之源之「口径」仍须在盘")):
        assert k in tail, k + u" —— " + why + u"（⛔ 丢信息 · 承 pm_1012 §二）"


def _stmt(s: str, a: str, b: str) -> str:
    u"""自 `a` 起至 `b` 止（含）—— ⛔ 以缩进猜界（那必漂）。"""
    i = s.index(a)
    k = s.index(b, i)
    return s[i:k + len(b)]


def test_P3_today_face_human_only_raw_folded():
    j = _read(TODAY)
    # ① 本屏读数：人话在外 ∧ `num_ctx`／`画像件刻` ⛔ 在其**值**中
    when = _stmt(j, u"paV3Txt('paTodayWhen'", u"天）') : ''));")
    assert u"'本屏读数 '" in when, u"本屏读数（人话）须上屏"
    assert u"num_ctx" not in when and u"画像件刻" not in when, \
        u"`num_ctx` ／「画像件刻」⛔ 得入用户面（pm_1808 §二.1）"
    raw = _stmt(j, u"var _whenRaw =", u"⛔ 编）');")
    assert u"num_ctx" in raw and u"画像件刻" in raw, u"反控：原字仍须在盘（折入源行 · ⛔ 丢信息）"
    # ② 画像：人话（已定 ／ 待你裁 ／ 摘要）∧ 工程话（「式：」／接口径）⛔ 在值中
    prof = _stmt(j, u"paV3Txt('paTodayProfile', brief", u"'未知（后端未应答 ／ 无读数）');")
    assert u"'已定 '" in prof and u"' ／ 待你裁 '" in prof, u"用户面须留「已定 ／ 待你裁」"
    assert u"式：" not in prof, u"「式：…」⛔ 得入用户面（pm_1808 §二.1）"
    assert u"GET /v9/" not in prof, u"接口径 ⛔ 得入用户面"
    praw = _stmt(j, u"var _profRaw =", u"· 单例（本机 1 个客户）');")
    assert u"式：" in praw and u"GET /v9/pa/profile" in praw, u"反控：原字仍须在盘"
    assert u"_whenRaw + ' ｜ ' + _profRaw" in j, u"原字须真折入**源行**（#paTodayProfileSrc）"
    # ③ 昨夜整合：`承 pm_*` ⛔ 入用户面（原字入 title）
    night = _stmt(j, u"paV3Txt('paTodayNight'", u"'暂无');")
    assert u"'暂无'" in night, u"用户面须留人话（pm_1822 §二.⒉「昨夜整合：暂无」）"
    assert u"承 pm" not in night, u"「承 pm_*」⛔ 得入用户面（pm_1808 §二.1）"
    assert u"_nightEl.title" in j and u"承 pm 18:00 批一" in j, u"反控：原字仍须可达（title）"


def test_P5_left_column_is_human_not_a_digit_wall():
    u"""pm_1822 §二.⒈ ＋ pm_1829 §二.2（要）：左栏摘要**只留人话** ∧ **⛔ 数字墙**。

    事由（PM 一手 · CDP）：左栏见「素材 7 面 · 全载 0 条 · 在办 217 件…」∧「(b) 未接（红线）」——
    我辈之缩写与编号 ⇒ 用户读之如乱码。
    正控：静态引「素材 7 面 ⇒」已撤 ∧ `paSrcSum` 之值 ⛔ 载器之名 ／ 数字墙；
    反控：逐面之真数 ／ 真源 ／ 取数刻 ⇒ 仍在其**源行**（`#paSrcList` · 一点「▾」即见 · ⛔ 丢信息）。"""
    h = _read(HTML)
    i = h.index(u'id="paSrcSummary"')
    line = h[i:h.index(u"</div>", i)]
    assert u"素材 7 面" not in line, u"「素材 7 面」为我辈之数 ⇒ ⛔ 上屏（pm_1829 §二.2）"
    assert u"paSrcToggle()" in line and u'id="paSrcSum"' in line, \
        u"摘要须仍可点开（▾ ⇒ 逐面之真读数）"
    j = _read(TODAY)
    sm = _stmt(j, u"paV3Txt('paSrcSum', '画像 1 位'", u"' · 平台：不会代你操作（这是红线）');")
    for bad in (u"PES", u"未接", u"运行中", u"台账 ", u"3 根", u"按目录聚合", u"素材 2 面", u"全载"):
        assert bad not in sm, u"左栏摘要 ⛔ 载：「" + bad + u"」（数字墙 ／ 器之名 —— pm_1822 §二.⒈）"
    for good in (u"在办 ", u"记忆 ", u"素材 "):
        assert good in sm, u"左栏摘要须留人话：「" + good + u"」"
    assert u'id="paSrcList" hidden' in h, u"反控：逐面之真数仍须在盘（折于 ▾ ⇒ ⛔ 丢信息）"


def test_P4_banner_terminal_state_auto_retires():
    s = _read(START)
    assert u"const PA_PREP_TERM_HOLD_MS" in s, u"须有一处定形之阈（终态自退）"
    r = s[s.index(u"function paPrepRender(v){"):]
    r = r[:r.index(u"\n}", r.index(u"paPrepTermT = setTimeout"))]
    assert u"v.state === 'done'" in r, u"唯**终态**（done）方自退（⛔ 误隐在办之相）"
    assert u"clearTimeout(paPrepTermT)" in r, u"非终态须撤钟（幂等 ／ ⛔ 误隐）"
    u_ = _read(UPD)
    assert u"const PA_UPD_RECENT_S = 3600;" in u_, \
        u"⚠ 本批 ⛔ 动 PA_UPD_RECENT_S（3600 · 承 pm_1693 §四.3 —— 另一物：状态之窗）"