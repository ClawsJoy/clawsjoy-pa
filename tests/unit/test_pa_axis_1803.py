# -*- coding: utf-8 -*-
u"""pm_1803 之齿 —— PA 页两态「陪伴 ／ 办事」之**一眼可辨 ∧ 一键可换 ∧ 辞如实 ∧ 态真变**。

事由：老板之令（逐字）「**现在页面是陪伴和办事**」⇒ 判：PA 页 ＝ 两条轴 ——
  陪伴（`/v9/pa/dialog`：陪着 · 只商量 · ⛔ 替你动手）／ 办事（`/v9/agent/chat`：真动手 · 有交付 · 可验收）。
  旧形（一手 · `web/pa.html:136`）：`#modelText` 显「**⛔ 聊天（只商量 · 不出手）**」∧ `#chanSwitch` 钮
  显「切到工作模式（可执行）→」—— 三病：⒜ `⛔` 像故障、⛔ 像「态之名」；⒝ 两态之辞**不对称**；
  ⒞ **当前态**⛔ 一眼可辨（且此二者居「更多 ▾」＝二级菜单 ⇒ 首屏看不见）。

⭐ 落码之**关键一手**（我一手逮 · 报 PM）：本页**已有**一个两态控件 —— `#paModeBar`
  （`web/pa/faces/selfdesc.js` 之 `mount()` · 承 `pm_1100 §三`）⇒ 故本批 ⛔ **另立**控件（那正是
  「两处各写」／「两套辞」之病）；而是**升级**该控件 ⇒ 唯一一处。
⭐ 且技术总监 `core\\pa\\gateway_routes.py:75-79` 之**逐字**已定：「**正名之真源（页上之两名）**」
  ＝ `selfdesc.js` 之 `VAL` ⇒ 页上两名 ⛔ 得另立一套（旧书「聊天 ／ 工作」＝ `pm_1804 §一.1` 之
  「两套辞」）⇒ 故 `chat.js` 之两态之渲**唯转调** `selfdesc.js` 之 `paAxisRender`（一处定形）。

判据（静态闸 · 与真 Chrome 之几何证 ＋ 桩端之后端日志互补）：
  P1 唯一一处：两态之控件唯 `#paModeBar` 之两钮（`#paModeBtnCompanion` ／ `#paModeBtnWork`）
     ∧ `mount()` 以 `insertBefore(bar, c.firstChild)` 入 `.composer` 之**首**（首屏可辨 · 一步可达）
     ∧ 盘上（`pa.html`）**⛔ 载**第二套两态控件之 id（`paAxis` ／ `paSetAxis`）。
  P2 一键可换（⛔ 二步）：两钮之 click ⇒ `window.paAxisGo(...)`；`paAxisGo` 须**并办**：⒜
     `paSetChatMode(v)`（档 ⇒ 体之 `mode` ＋ 会话属性 ＋ 落盘）⒝ `setMode(...)`（通道 ⇒ **真发向之端**
     · PM §二.2）∧ ⚠ 已在同一轴 ⇒ ⛔ 再调 `setMode`（否则「办事」恒落 `work` ⇒ 降级用户所择之 `dev`）。
  P3 辞如实 ∧ 两名之一源：`VAL` 载 `label` 陪伴／办事 ∧ 其 `note` 载 PM 之逐字（只商量 ／ 替你动手 ／
     真动手 ／ 有交付 ／ 可验收）；`chat.js` 之 `setMode` **⛔ 造辞**（旧二处各写已拔）∧ ⛔ 载 `PA_AXIS`
     ／ `paSetAxis`（本批**已撤**之重复件）。
  P4 当前态显眼（一处定形）：`paint()` 载 `aria-selected` ＋ 实底着色 ＋ `●` 标记（⛔ 唯色差之辨 ⇒
     屏读器亦得）；`btn()` 载加大之形（`padding` ＋ 字号）。⛔ 减首屏控件数之律不适用（老板点名要它可辨）。
  P5 旧闸仍立：`#modelText` ／ `#chanSwitch` 仍在盘；`#chanSwitch` 之 `onclick` ＝ `paAxisGo('work')`
     （⛔ 旧 `setMode('work')` —— 那条路 ⛔ 经档 ⇒ 两态 ⛔ 同源）。
  P6 反控（本闸真能捕病）：`#modelText` ／ `#chanSwitch` **仍在** `#paMorePanel`（二级菜单）之内 ⇒
     首屏一步可达之判据对之必 **False**；且 `pa.html` ⛔ 载 `id="paAxis"`／`paSetAxis`（＝若有人把
     第二套控件搬回来 ⇒ P1 必败）。
  P7 ⛔ 说谎（通道为主）：`eff()` 之链首须为**通道**（`MODES[state.mode].chan === "agent"` ⇒ `work`）
     —— 否则「办事」态而仍发 `/v9/pa/dialog` ＝ 不实之辞入屏。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_axis_1803.py -q
"""
from __future__ import annotations

import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "web" / "pa.html"
CHAT = ROOT / "web" / "pa" / "faces" / "chat.js"
SELF = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
FACES = ROOT / "web" / "pa" / "faces.json"
SEND = ROOT / "web" / "pa" / "faces" / "send.js"
GW = ROOT / "core" / "pa" / "gateway_routes.py"


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
    u"""一步可达 ＝ 其标签**在盘上** ∧ **⛔ 在 `#paMorePanel`（二级菜单）之内**。"""
    if (u'id="' + eid + u'"') not in h:
        return False
    return (u'id="' + eid + u'"') not in _block_of(h, "more")


def _fn_body(js: str, sig: str) -> str:
    seg = js[js.index(sig):]
    return seg[:seg.index(u"\n  }")]


def test_P1_single_control_in_always_visible_axis_bar():
    h = _read(HTML)
    j = _read(SELF)
    # pm_1807 §一.1：控件之宿主 ＝ **常驻轴栏**（居顶栏之下 ∧ 主面之上）⇒ 首屏常驻 · ⛔ 藏于抽屉
    assert u'id="paAxisBar"' in h, u"须有常驻轴栏 #paAxisBar（pm_1807 §一.1 之宿主）"
    assert _one_step_reachable(h, u"paAxisBar"), \
        u"#paAxisBar ⛔ 得在「更多」之内（那正是病 —— pm_1807 §一.1）"
    assert u'id="paAxisBar"' not in _block_of(h, "composer"), \
        u"#paAxisBar ⛔ 得在 .composer 之内 —— 一手之证（CDP）：首次用之首启盒覆住 .composer ⇒ 其内诸件⛔可点"
    assert h.index(u'id="paAxisBar"') > h.index(u'id="paTop"'), u"轴栏须居顶栏**之下**"
    assert h.index(u'id="paAxisBar"') < h.index(u'class="main"'), u"轴栏须居主面**之上**"
    seg = j[j.index(u"function mount(){"):]
    seg = seg[:seg.index(u"\n  }")]
    assert u'document.getElementById("paAxisBar")' in seg, \
        u"mount() 须取槽 #paAxisBar（宿主一处定形 · ⛔ 另造控件）"
    for eid in (u"paModeBtnCompanion", u"paModeBtnWork"):
        assert (u'btn("' + eid + u'", ') in j, \
            eid + u" 须由 selfdesc.js 之 btn() 造（一处定形 · ⛔ 各写死 id）"
    assert "id=\"' + id + '\"" in j, u"btn() 之骨须以 id 参数造（一处定形）"
    for dead in (u"paAxis", u"paAxisChat", u"paAxisWork", u"paAxisNote", u"paSetAxis"):
        assert (u'id="' + dead + u'"') not in h, \
            dead + u" 之 id ⛔ 得在盘上 —— ⛔ 另立一套两态控件（那正是「两处各写」之病）"
    for dead in (u"PA_AXIS", u"paRenderAxis"):
        assert dead not in h, dead + u" 须**不在盘上** —— ⛔ 另立一套两态控件"
    _c = _read(CHAT)
    for dead in (u"paAxisChat", u"paAxisWork", u"paAxisNote", u"paSetAxis", u"PA_AXIS"):
        assert dead not in _c, dead + u" —— chat.js ⛔ 得载重复件（本批已撤）"


def test_P2_one_click_and_really_switches_channel():
    j = _read(SELF)
    seg = j[j.index(u"function mount(){"):]
    seg = seg[:seg.index(u"\n  }")]
    assert u"paAxisGo(b.getAttribute(\"data-pa-mode\"))" in seg, \
        u"两钮之 click 须走**唯一之切换出口** paAxisGo（一处定形 · ⛔ 各写）"
    body = _fn_body(j, u"window.paAxisGo = function(v){")
    assert u"paSetChatMode(v)" in body, u"须办①：档（体之 mode ＋ 会话属性 ＋ 落盘）"
    assert u"setMode(" in body, u"须办②：通道 ⇒ **真发向之端**（/v9/pa/dialog ⇄ /v9/agent/chat · PM §二.2）"
    assert u"curChan !== want" in body, \
        u"⚠ 已在同一轴 ⇒ ⛔ 再调 setMode（否则「办事」恒落 work ⇒ 降级用户所择之 dev ＝ 擅改）"
    assert u'companion") ? "chat" : "work"' in body, u"陪伴 ⇒ chat ／ 办事 ⇒ work（一处映射）"


def test_P3_honest_wording_single_source():
    j = _read(SELF)
    val = j[j.index(u"var VAL = {"):]
    val = val[:val.index(u"};")]
    assert u'label:"陪伴"' in val and u'label:"办事"' in val, u"两名须在 VAL（技术总监所定之**真源**）"
    for k, why in ((u"只商量", u"陪伴之实辞"), (u"替你动手", u"陪伴之界（⛔ 替你动手 —— PM §一 逐字）"),
                   (u"真动手", u"办事之实辞"), (u"有交付", u"办事之实辞"), (u"可验收", u"办事之实辞")):
        assert k in val, k + u" —— " + why
    assert u'chan:"pa"' in val and u'chan:"agent"' in val, u"两态各标其**通道**（⛔ 于轴外另断）"
    c = _read(CHAT)
    sb = _fn_body(c, u"function setMode(m){")
    for dead in (u"_mt.textContent", u"chanbadge", u"chanSwitch"):
        assert dead not in sb, \
            dead + u" ⛔ 得再自写于 setMode（旧病：两处各写 ⇒ 必漂）—— 唯转调 paAxisRender"
    assert u"paAxisRender()" in sb, u"setMode 须转调 **唯一渲出口** paAxisRender（一处定形）"
    assert u"⛔ 聊天（只商量 · 不出手）" not in _read(HTML), \
        u"旧「⛔ 聊天（…）」之字面须已拔（那个 ⛔ 像故障 · ⛔ 像态之名 —— pm_1803 §一.1）"
    assert u'label:"陪伴"' not in _read(HTML), u"盘上（静态骨）⛔ 得再载两名之源（⛔ 第二套辞）"


def test_P4_current_state_prominent_one_place():
    j = _read(SELF)
    p = _fn_body(j, u"function paint(){")
    for k, why in ((u"aria-selected", u"屏读器亦须得（⛔ 唯色差之辨）"),
                   (u'"#1f6feb"', u"当前态之实底着色"),
                   (u"boxShadow", u"当前态之描边（辨之一助）")):
        assert k in p, k + u" —— " + why
    assert u'"● "' in p, u"当前态须带 `●` 标记（⛔ 唯色差）"
    b = _fn_body(j, u"function btn(id, label){")
    for k in (u"padding:", u"font-size:", u"border-radius:"):
        assert k in b, k + u" —— 老板之令「**按钮可以明显一点**」（pm_1803 §一）"
    assert u"border-radius:999px" in b, u"分段控件之形（胶囊）"
    r = j[j.index(u"function paint(){"):]
    assert u"legacy(v)" in r[:r.index(u"\n  }")], \
        u"更多 ▾ 之模式条 ＋ 「不出手」行须**同源同渲**（⛔ 第二处渲染）"


def test_P5_legacy_row_still_on_disk_and_same_exit():
    h = _read(HTML)
    assert u'id="modelText"' in h and u'id="chanSwitch"' in h, u"旧两态之件仍须在盘上"
    assert u'onclick="paAxisGo(\'work\')"' in h, \
        u"#chanSwitch 须走**唯一之切换出口**（旧 `setMode('work')` ⛔ 经档 ⇒ 两态 ⛔ 同源）"
    assert u'onclick="setMode(\'work\')"' not in h, u"旧第二出口须已拔"


def test_P6_control_buried_row_is_not_one_step():
    h = _read(HTML)
    for eid in (u"modelText", u"chanSwitch"):
        assert _one_step_reachable(h, eid) is False, \
            u"反控：旧两态之件 " + eid + u" 仍须在「更多」之内 —— 否则本判据之分辨力已失（须重审）"
    assert u'id="modelText"' in _block_of(h, "more"), u"反控：承器 #modelText 仍在菜单内（旧处之所在）"
    assert u'id="paAxis"' not in h, u"反控：本批已撤之重复控件 ⛔ 得复活（若复活 ⇒ P1 必败 · 须重审）"


def test_P7_channel_governs_mode_no_lie():
    j = _read(SELF)
    seg = j[j.index(u"function chanMode(){"):]
    seg = seg[:seg.index(u"\n  }")]
    assert u'MODES[state.mode]' in seg and u'"agent"' in seg and u'"work"' in seg, \
        u"chanMode 须由**通道**定档（`MODES[].chan` · core.js 一处）"
    e = j[j.index(u"function eff(){"):]
    e = e[:e.index(u"\n")]
    assert e.index(u"chanMode()") < e.index(u"threadMode()"), \
        u"eff 之链首须为**通道** ⇒ 否则「办事」态而仍发 dialog ＝ 不实之辞入屏（pm_1803 §二.2）"
    d = json.loads(_read(FACES))
    for f in (d.get("faces") or []):
        if f.get("id") not in (u"chat", u"shell", u"selfdesc"):
            continue
        for pt in (f.get("dom") or []):
            assert pt.startswith(u"#") and (u'id="' + pt[1:] + u'"') in _read(HTML), \
                u"面册 " + f["id"] + u" 之 dom 指 " + pt + u" ⇒ ⛔ 得悬空"

def _pa_mode_name():
    u"""**器取**（⛔ 引 `core` 之重依赖）：自 `core/pa/gateway_routes.py` 取 `pa_mode_name` 之**原字** ⇒ `exec`。

    ⚠ 此为「一处定形」之取法：真源 ＝ 后端之函 ⇒ 齿 ⛔ 复写一张映射表（复写必漂）。
    """
    src = _read(GW)
    i = src.index(u"def pa_mode_name(")
    j = src.index(u"\ndef ", i + 1)
    ns = {}
    exec(compile(src[i:j], "gateway_routes.pa_mode_name", "exec"), ns)
    return ns["pa_mode_name"]


def test_P8_companion_path_carries_mode():
    u"""pm_1807 §一.3／§一.4（要 · 我域 · 一行）：**陪伴路之请求体须自带 `mode`**。

    病（技术总监一手逮 · pm_1805 §四.1）：`sendPA` 之体**无 `mode`** ⇒ 后端 `pa_mode_name(None)`
    ⇒ **`work`** ⇒ 陪伴通道拿到「**办事**」之场合栏 ＝ 「页曰『陪伴』而提示曰『办事』」之根。
    我裁：走**前端**（⛔ 改后端缺省 —— 「缺省 ＝ work」是已明书之契约 · 改之 ＝ 静默改所有旧调用者）。
    """
    s = _read(SEND)
    seg = _fn_body(s, u"async function sendPA(text, t, meta){")
    assert u"mode:" in seg, u"陪伴路之请求体须带 mode（pm_1807 §一.3）"
    assert u"paChatMode()" in seg, u"其值须取**一处之源** paChatMode()（⛔ 前端硬编字面）"
    # 正控（器取后端之归一函）：带 ⇒ companion
    fn = _pa_mode_name()
    assert fn(u"chat") == u"companion", u"正控：体带 mode:'chat' ⇒ 后端判 companion"
    assert fn(u"companion") == u"companion", u"正控：mode:'companion' ⇒ companion"
    # 反控：抽去该键 ⇒ 后端缺省 work ⇒ **齿必咬**（这正是旧病之形）
    assert fn(None) == u"work", u"反控：体**无** mode ⇒ 判 work（旧病 · 齿据此咬）"
    assert fn(u"") == u"work", u"反控：mode 空串 ⇒ 判 work"
