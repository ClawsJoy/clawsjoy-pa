# -*- coding: utf-8 -*-
u"""pm_1812 ／ pm_1813 之齿 —— 答体**去壳**（工程话 ⛔ 用户面）＋ 轴栏唯两态 ＋ 抽屉多条各一题。

事由（老板之屏 · PM 一手之证）：
  ⒜ 「云端之告」**每轮必现**（`🤖PA · 聊天 本轮经云端 · 内容将出机 · 模型 …`）⇒ 会脱敏（喊了等于没喊）；
  ⒝ 「走径（键 route · 采于 …）」与「源之分标（⛔ 非本机素材）」⇒ ⛔ 用户面；
  ⒞ 抽屉里**三条一模一样**的「来源 ／ 详情（抽屉之过程注记 · 原文照录）」⇒ 用户不知那是三条什么；
  ⒟ **轴栏**（老板一眼就看的那条）里带**内部读数**：会话 id ／「（继承）」／「回执 `mode`：—（尚未有本轮）」；
  ⒠ 抽屉首之 `（承 pm_裁_主面环≤5）`（**内部令号**）＋「`pane` 与 `data-face` 一字未删」（**实现细节**）。

判据（静态闸 · 与真 Chrome 之 CDP 证互补）：
  P1 **一处定形**：去壳之器唯 `more.js`（`paCloudBadge` ／ `paEngLines` ／ `paShellHtml` ／ `paCloudNotice`），
     且旧器 `paRouteHtml` ／ `paLeavesHtml` **已撤**（⛔ 载 —— 二处各拼必漂）；题 `PA_SHELL_SUM` 与
     `selfdesc.js` 之「来源 ／ 详情」**可辨**（一条答里可能有两处折叠）。
  P2 用户面 ⛔ 载工程话：`paShellHtml` 之**可见**串唯「常驻小标 ＋ 折叠之题」；工程行皆入 `.engbody`。
  P3 「云端之告」唯**首次 ∨ 切通道后**一次 ∧ 唯**远端**之轮（本机之轮喊「内容将出机」＝ 不实之辞）。
  P4 ⛔ 伪行：`paShellHtml` 载 `hasRoute` ／ `hasLeaves` 去重；`addMsg` 包装「无回执 ∧ 无存量工程行 ⇒ 原样」。
  P5 **反控**（真源 ⛔ 删）：`paRouteLine` 之「🔌 走径：」∧ `paLeavesLine` 之「本轮经云端 · 内容将出机 · 模型」仍在盘。
  P6 轴栏（pm_1813 §一）：`mount()` 之栏 **⛔ 载** `paModeSession` ／ `paModeReceipt`；其读数归诊断区
     （`paSelfModeDiagHtml` 在盘 ∧ 载「回执 mode」）⇒ ⛔ 丢真源。
  P7 抽屉（pm_1813 §二.3）：`paEngCleanDrawer` 载**一条定形**（既有则并 · ⛔ 二条）∧ 题随 件数 ／ 刻。
  P8 令号 ／ 实现细节 ⛔ 上屏（pm_1813 §二.1 ／ §二.2）：`paXMoreHost` ⛔ 载「承 pm_」∧「pane 与 data-face」。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_shell_1812.py -q
"""
from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MORE = ROOT / "web" / "pa" / "faces" / "more.js"
SELF = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
TASKS = ROOT / "web" / "pa" / "faces" / "tasks.js"


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _fn(src: str, sig: str) -> str:
    u"""取 `sig`（函数签名）之整段（配平花括号 · ⛔ 以缩进猜界）。"""
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


def test_P1_one_place_shell_and_old_ones_gone():
    s = _read(MORE)
    for sig in (u"function paCloudBadge(box){", u"function paEngLines(box){",
                u"function paShellHtml(box, engExtra){", u"function paCloudNotice(box){"):
        assert sig in s, u"去壳之器须在 more.js（一处定形）：" + sig
    assert u"function paRouteHtml(" not in s, u"旧器 paRouteHtml 须撤（否则二处各拼 · 必漂）"
    assert u"function paLeavesHtml(" not in s, u"旧器 paLeavesHtml 须撤（否则二处各拼 · 必漂）"
    assert u"window.paShellHtml = paShellHtml; window.paCloudNotice = paCloudNotice;" in s, \
        u"折叠壳 ／ 人话之器须出（供他件取 · ⛔ 各件自造）"
    assert u"const PA_SHELL_SUM = '本轮来源（技术细节）';" in s, \
        u"折叠之题须一处定形 ∧ 与「来源 ／ 详情」可辨（pm_1813 §二.3）"


def test_P2_visible_shell_holds_no_engineer_text():
    s = _read(MORE)
    b = _fn(s, u"function paShellHtml(box, engExtra){")
    ret = b[b.rindex(u"return "):]   # 唯取**末一 return**（其前之去重判里有「🔌 走径：」之逐字 —— 那是判据，⛔ 可见串）
    assert u"engbody" in ret and u"paEsc(body)" in ret, u"工程行须入 .engbody（折叠体）"
    assert ret.index(u"engbody") < ret.index(u"paEsc(body)"), u"工程行须在折叠体**之内**"
    assert u"🔌 走径：" not in ret, u"走径之逐字 ⛔ 得在此可见串（须由 paRouteLine 入折叠）"
    assert u"（键 " not in ret, u"「（键 route …）」⛔ 得入可见串"
    badge = _fn(s, u"function paCloudBadge(box){")
    assert u"paRouteIsRemote(L.kind)" in badge and u"'🔌 云端'" in badge, \
        u"常驻小标须唯远端之轮（⛔ 恒挂）"


def test_P3_cloud_notice_once_remote_only():
    s = _read(MORE)
    c = _fn(s, u"function paCloudNotice(box){")
    assert u"if(!box) return '';" in c, u"存量重渲（无本轮回执）⛔ 造此句（免一 F5 即冒一句）"
    assert u"if(now !== 'remote') return '';" in c, \
        u"本机之轮 ⛔ 喊「内容将出机」—— 喊之 ＝ 不实之辞入屏（pm_1812 §一.⒜）"
    assert u"paCloudSaid !== now" in c and u"paCloudSaid = now;" in c, \
        u"唯**首次 ∨ 通道切换后**一次（⛔ 每轮都喊 ⇒ 会脱敏）"
    assert u"return first ?" in c, u"唯首次方出此句"


def test_P4_no_fake_route_line():
    s = _read(MORE)
    b = _fn(s, u"function paShellHtml(box, engExtra){")
    assert u"hasRoute" in b and u"hasLeaves" in b, \
        u"存量重渲须去重（否则折叠里二条走径 ＋ `src: —（后端未给）` 伪行）"
    assert u"if(!hasRoute) lines.push(paRouteLine(box));" in b, u"走径唯缺时添"
    assert u"if(!box && !legEng.length) return orig.apply(this, arguments);" in s, \
        u"无回执 ∧ 无存量工程行 ⇒ **原样**（⛔ 伪行 · ⛔ 添字 · 承 pm_1076 §三）"


def test_P5_counter_control_raw_text_still_on_disk():
    s = _read(MORE)
    assert u"function paRouteLine(box){" in s and u"'🔌 走径：'" in s, u"反控：走径之**逐字**仍须在盘（唯位改）"
    assert u"function paLeavesLine(box){" in s and u"'本轮经云端 · 内容将出机 · 模型 '" in s, \
        u"反控：云端之告之**逐字**仍须在盘（⛔ 删真源 · 承 pm_1012 §二）"
    assert u"paRouteIsRemote(L.kind)" in s, u"反控：判「远端」之器仍须在盘"


def test_P6_axis_bar_carries_no_internal_readings():
    s = _read(SELF)
    m = _fn(s, u"function mount(){")
    assert u'"paModeBar"' in m and u'"paModeBtnCompanion"' in m and u'"paModeBtnWork"' in m, \
        u"轴栏唯两态之名与切换（两点：陪伴 ／ 办事）"
    assert u"paModeSession" not in m, u"轴栏 ⛔ 得载会话 id（pm_1813 §一 · 老板一眼就看的那条）"
    assert u"paModeReceipt" not in m, u"轴栏 ⛔ 得载「回执 mode」之内部读数（pm_1813 §一）"
    assert u'document.getElementById("paAxisBar")' in m, u"宿主须一处定形（#paAxisBar）"
    assert u"paModeSession" not in s and u"paModeReceipt" not in s, \
        u"该二读数须**尽出**本件（⛔ 另处再渲 ⇒ 二处各写）"
    assert u"function paSelfModeDiagHtml(){" in s and u"回执 mode" in s, \
        u"反控：原字仍须可达（诊断区 · ⛔ 丢真源）"


def test_P7_drawer_notes_are_one_titled_fold():
    s = _read(SELF)
    d = _fn(s, u"function paEngCleanDrawer(){")
    # ⭐ pm_2104 §四.4ⓠ：旧形以「任一 `data-engskip`」索之 ⇒ 首中者常为**他折**（「来源 ／ 详情」·无 `.engbody`）
    #   ⇒ 守卫落空 ⇒ 每跑一次新建一条（增生）。今改作固定 `id="paEngNote"`（一处定形）：
    #   **其意不变**（一条定形 · 既有则并）—— 唯其锚改为可定之 `id`（承 pm_2106 §三.1 之准）。
    assert u"document.getElementById('paEngNote')" in d \
        and u"d.id = 'paEngNote';" in d, \
        u"须**一条定形**（既有则并 · 固定 `id`）—— ⛔ 每次新建 ⇒ 三条同名之折"
    assert u"document.querySelector('#paMoreBody details[data-engskip=\"1\"]')" not in d, \
        u"反控：旧形（以任一 `data-engskip` 索之）⛔ 得回归（其守卫会落空 ⇒ 增生）"
    assert u"paEngSkipSum(d);" in s, u"题须随内容重算"
    k = _fn(s, u"function paEngSkipSum(d){")
    assert u"过程注记（抽屉内文之工程引用 · " in k, u"题须载**件数**（各条可辨 · 承 pm_1813 §二.3）"
    assert u"条 · 刻 " in k, u"题须载**刻**（照 pm_1797 ／ pm_1798 之族）"


def test_P8_order_number_and_impl_detail_not_on_face():
    s = _read(TASKS)
    f = _fn(s, u"function paXMoreHost(){")
    i = f.index(u"box.innerHTML = ")
    h = f[i:f.index(u"body.insertBefore(box", i)]   # 唯取**入 DOM 之串**（其前之注释载旧字 —— 那是判据，⛔ 屏上之文）
    assert u"承 pm_裁_主面环≤5" not in h, u"内部令号 ⛔ 上屏（pm_1813 §二.1）"
    assert u"承 pm_" not in h, u"内部令号 ⛔ 上屏（pm_1813 §二.1）"
    assert u"pane 与 data-face" not in h, u"实现细节（`pane` ／ `data-face`）⛔ 上屏（pm_1813 §二.2）"
    assert u"这两面不占主面环 ⇒ 收在此处" in h and u"功能一字未减" in h, \
        u"其义须以**人话**留（⛔ 丢信息）"