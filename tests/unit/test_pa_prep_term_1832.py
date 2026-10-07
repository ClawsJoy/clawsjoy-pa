# -*- coding: utf-8 -*-
u"""令 1832 之齿 —— 横幅终态之判据（`web/pa/faces/update.js` ＋ `startup.js` ＋ `web/pa.html`）。

一事（PM 一手 · 刻 02:58–03:03 · 本机真走一次更新 9.0.8 ⇒ 9.0.8 ／ 重启）：
  ⒜ 横幅恒挂且**辞与真相反** —— 逐字「✅ 更新已完成 · 已就绪 已就位（9.0.8 ⇒ 9.0.8）·
     请关窗重开 ClawsJoy PA（∨ 菜单「重启服务」）以生效 ／ 若本页仍旧 ⇒ 需重启本页（按 F5 刷新）· 本页会自动重试」；
  ⒝ 该格内 `button` ／ `a` 计 `0`（无**可退之器**）。

判据：
  W1 正控（纯层）：本跑 done ∧ **活版 ＝ 目标版** ⇒ `state=done` ∧ 文 ＝ 「已更新到 9.0.8」
     ∧ 注 ⛔ 载「请关窗重开」∧ 文 ⛔ 载「⇒」（辞与真相反之治）。
  W2 反控：**活版 ≠ 目标版**（**真未生效**）⇒ 维持后端之辞（注含「请关窗重开」）∧ 文含「已就绪」。
  W3 幂等（`from == to`）⇒ 前端 ⛔ 画箭头（文 ⛔ 载「⇒」）。
  W4 活版之源：唯 `/health` 之**顶层** `version` —— 反控：`build.version`（读**盘**）虽已新而活版仍旧
     ⇒ **⛔ 判「已生效」**（用之必**假绿** · PM §二.2）。
  W5 终态之键：同一跑取二次 ⇒ **同键**；新一次跑 ⇒ 键变（一处定形 · `startup.js` 以其为记）。
  W6 正控（DOM）：终态入屏 ⇒ 现（`display=''`）∧ 逾 `PA_PREP_TERM_HOLD_MS`（20 s）⇒ 自退（`'none'`）。
  W7 反控（**病一之治**）：自退后 —— 中间来一次非终态（`ready`）∧ **同键**之 done 再现 ⇒ **仍 `'none'`**
     （旧形「非终态 ⇒ `paPrepTermAt = 0`」⇒ 复现 ⇒ 用户读成「退不掉」）。
  W8 反控：**键变**（新一次更新之终态）⇒ 复位起新钟 ⇒ 再现（`''`）∧ 再逾阈 ⇒ 自退。
  W9 反控：非终态（`running`）⇒ ⛔ 误隐（`''`）。
  W10 显式可退：`paPrepTermDismiss()` ⇒ `'none'` ∧ 同键再现 ⇒ 仍 `'none'`；
      `#paPrepX` 之收放（唯终态现）。
  S1 结构：`#paPrepX` 在 `pa.html` 之 `#paPrep` 格内 ∧ 样式**内联**（⛔ 改 `pa.css` ／ `pa_v3.css`）
     ∧ 点 ⇒ `paPrepTermDismiss()`。
  S2 结构：`paUpdView` 之活版唯取 `ctx.live_version` ／ `o.version`（⛔ `build.version`）∧ 阈唯 1 处。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_prep_term_1832.py -q
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UJ = ROOT / "web" / "pa" / "faces" / "update.js"
SU = ROOT / "web" / "pa" / "faces" / "startup.js"
HTML = ROOT / "web" / "pa.html"
SCRATCH = ROOT / "data" / "tmp" / "_cw_term1832"


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _fn(src: str, name: str) -> str:
    i = src.find("function " + name + "(")
    assert i > 0, u"未找到函数 " + name
    d, opened, e = 0, False, i
    while e < len(src):
        c = src[e]
        if c == "{":
            d += 1
            opened = True
        elif c == "}":
            d -= 1
            if opened and d == 0:
                return src[i:e + 1]
        e += 1
    raise AssertionError(u"函数 " + name + u" 花括号不配平")


def _fna(src: str, name: str) -> str:
    i = src.find("async function " + name + "(")
    assert i > 0, u"未找到 async 函数 " + name
    d, opened, e = 0, False, i
    while e < len(src):
        c = src[e]
        if c == "{":
            d += 1
            opened = True
        elif c == "}":
            d -= 1
            if opened and d == 0:
                return src[i:e + 1]
        e += 1
    raise AssertionError(u"函数 " + name + u" 花括号不配平")


def _decl(src: str, prefix: str) -> str:
    for ln in src.split("\n"):
        if ln.startswith(prefix):
            return ln
    raise AssertionError(u"未找到声明 " + prefix)


def _block(src: str, head: str, stop: str) -> str:
    i = src.find(head)
    assert i >= 0, u"未找到块头 " + head
    j = src.find(stop, i)
    assert j > 0, u"未找到块末 " + stop
    return src[i:j + len(stop)]


def _parts_view() -> list:
    t, s = _read(UJ), _read(SU)
    return [
        _fn(s, u"paPrepNum"), _fn(s, u"paPrepMB"), _fn(s, u"paPrepMeasuredNote"),
        _decl(t, u"const PA_UPD_SRC"), _decl(t, u"const PA_UPD_POST"),
        _decl(t, u"const PA_UPD_POLL_MS"), _decl(t, u"const PA_UPD_BUSY_MS"),
        _decl(t, u"const PA_UPD_RECENT_S"),
        _decl(t, u"const PA_UPD_PENDING_KEY"), _decl(t, u"const PA_UPD_WINDOW_S"),
        _decl(t, u"const PA_UPD_RETRY_MS"), _decl(t, u"const PA_UPD_RETRY_MAX_MS"),
        _decl(t, u"const PA_UPD_RECOVER_S"),
        _block(t, u"const PA_UPD_PHASE = {", u"};"),
        _decl(t, u"const PA_UPD_LOG"), _decl(t, u"const PA_UPD_OUTLET"),
        _decl(t, u"const PA_UPD_OUTLET_SELF"),
        _fn(t, u"paUpdAgeS"), _fn(t, u"paUpdView"), _fn(t, u"paUpdCurFromHealth"),
        _fn(t, u"paUpdVerText"), _fn(t, u"paUpdVerRender"), _fn(t, u"paUpdBtnRender"),
        _decl(t, u"const paUpdRun"), _fn(t, u"paUpdApply"), _fn(t, u"paUpdSetInterval"),
        _fna(t, u"paUpdPost"), _fn(t, u"paUpdMarkRead"), _fn(t, u"paUpdMarkWrite"),
        _fn(t, u"paUpdWhyRender"), _fna(t, u"paUpdFetch"),
    ]


def _parts_term() -> list:
    s = _read(SU)
    return [
        _decl(s, u"const PA_PREP_TERM_HOLD_MS"),
        _decl(s, u"const PA_PREP_ICON"),
        _decl(s, u"let paPrepTermT"), _decl(s, u"let paPrepTermAt"),
        _decl(s, u"let paPrepTermKey"), _decl(s, u"let paPrepTermGone"),
        _fn(s, u"paPrepEl"), _fn(s, u"paPrepTermDismiss"), _fn(s, u"paPrepRender"),
    ]


TS_AGO = u"""
function tsAgo(sec){
  const d = new Date(Date.now() - sec * 1000);
  const p = function(n){ return (n < 10 ? '0' : '') + n; };
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T'
       + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds()) + '+0800';
}
"""

NOTE_BE = u"已就位（%s ⇒ %s）· 请关窗重开 ClawsJoy PA（∨ 菜单「重启服务」）以生效"

CASE_VIEW = u"""
const HEALTH = {available:false, current_version:'9.0.8', latest_version:'9.0.8', note:'已是最新'};
const RUN1 = {phase:'done', from:'9.0.8', to:'9.0.8',
              note:'已就位（9.0.8 ⇒ 9.0.8）· 请关窗重开 ClawsJoy PA（∨ 菜单「重启服务」）以生效',
              started_at:tsAgo(60), ended_at:tsAgo(55)};
const RUN2 = {phase:'done', from:'9.0.7', to:'9.0.8',
              note:'已就位（9.0.7 ⇒ 9.0.8）· 请关窗重开 ClawsJoy PA（∨ 菜单「重启服务」）以生效',
              started_at:tsAgo(60), ended_at:tsAgo(55)};
const RUNIDEM = {phase:'done', from:'9.0.8', to:'9.0.8', note:'',
                 started_at:tsAgo(60), ended_at:tsAgo(55)};
const OLD = JSON.parse(JSON.stringify(RUN1)); OLD.ended_at = tsAgo(5);
const out = {};
/* W1 正控：活版 ＝ 目标版 ⇒ 该次更新已生效（PM 一手之态） */
out.effected = paUpdView(HEALTH, {live_version:'9.0.8', run:RUN1});
/* W2 反控：活版 ≠ 目标版（真未生效 · 重启前）⇒ 维持后端之辞 */
out.not_yet  = paUpdView(HEALTH, {live_version:'9.0.7', run:RUN2});
/* W3 幂等（from == to）∧ 活版仍旧 ⇒ ⛔ 画箭头 */
out.idem     = paUpdView(HEALTH, {live_version:'9.0.6', run:RUNIDEM});
/* W4 反控：活版唯自 ctx（＝顶层 version）—— `u` 内虽带 build.version（读盘 · 已新）⇒ ⛔ 判「已生效」 */
out.disk_new = paUpdView({available:false, current_version:'9.0.7', latest_version:'9.0.8',
                          note:'', version:'9.0.7', build:{available:true, version:'9.0.8'}},
                         {run:RUN2});
/* W5 键：同一跑取二次 ⇒ 同键；新一次跑 ⇒ 键变 */
out.key1  = paUpdView(HEALTH, {live_version:'9.0.8', run:RUN1}).term_key;
out.key1b = paUpdView(HEALTH, {live_version:'9.0.8', run:RUN1}).term_key;
out.key2  = paUpdView(HEALTH, {live_version:'9.0.8', run:OLD}).term_key;
console.log(JSON.stringify(out));
"""

CASE_DOM = u"""
var NOW = 1000000;
Date.now = function(){ return NOW; };
var TIMERS = [];
function setTimeout(fn, ms){ TIMERS.push({fn:fn, at:NOW + (ms || 0), dead:false}); return TIMERS.length; }
function clearTimeout(id){ if(id && TIMERS[id - 1]) TIMERS[id - 1].dead = true; }
function fire(){ var t = TIMERS.slice(); for(var i=0;i<t.length;i++){
  if(!t[i].dead && t[i].at <= NOW){ t[i].dead = true; t[i].fn(); } } }
var EL = {style:{display:''}, attrs:{}, setAttribute:function(k,v){ this.attrs[k]=v; }};
var XB = {style:{display:'none'}};
var document = {getElementById:function(id){ return (id === 'paPrep') ? EL : ((id === 'paPrepX') ? XB : null); }};
const T1  = {state:'done', term_key:'upd|A', text:'已更新到 9.0.8', note:''};
const T1b = {state:'done', term_key:'upd|A', text:'已更新到 9.0.8', note:''};
const T2  = {state:'done', term_key:'upd|B', text:'已更新到 9.0.9', note:''};
const out = {};
/* W6 正控：终态入屏 ⇒ 现 ∧ 逾阈 ⇒ 自退 */
paPrepRender(T1);  out.shown = EL.style.display; out.x_shown = XB.style.display;
NOW += 21000; fire(); out.hold_gone = EL.style.display;
/* W7 反控（病一之治）：中间来一次非终态 ∧ 同键再现 ⇒ 仍 'none'（⛔ 复现） */
paPrepRender({state:'ready'}); out.mid_ready = EL.style.display;
paPrepRender(T1b);             out.same_key = EL.style.display;
/* W8 反控：键变 ⇒ 复位起新钟 ⇒ 再现 ∧ 再逾阈 ⇒ 自退 */
paPrepRender(T2); out.new_key = EL.style.display;
NOW += 21000; fire(); out.new_key_gone = EL.style.display;
/* W9 反控：非终态（在办之相）⇒ ⛔ 误隐 */
paPrepRender({state:'running', text:'正在更新…'}); out.running = EL.style.display;
out.x_running = XB.style.display;
/* W10 显式可退（✕）⇒ 'none' ∧ 同键再现 ⇒ 仍 'none' */
var T3 = {state:'done', term_key:'upd|C', text:'已更新到 9.1.0', note:''};
paPrepRender(T3); out.x_done = XB.style.display;
paPrepTermDismiss(); out.dismissed = EL.style.display;
paPrepRender(T3); out.after_dismiss = EL.style.display;
console.log(JSON.stringify(out));
"""


CASE_E2E = u"""
var STORE = {};
var window = { sessionStorage: {
  getItem: function(k){ return (k in STORE) ? STORE[k] : null; },
  setItem: function(k, v){ STORE[k] = String(v); },
  removeItem: function(k){ delete STORE[k]; } } };
const VER = {textContent:'', title:'', style:{}};
const BTN = {style:{display:'none'}, disabled:true, textContent:'', title:''};
var document = {getElementById:function(id){ return (id === 'paUpdGo') ? BTN : ((id === 'paVerRow') ? VER : null); }};
function setInterval(){ return 0; }
function clearInterval(){}
function paPrepFeedUpdate(){}
const NET = [];
let QUEUE = [];
function fetch(u, o){
  NET.push({url:String(u), method:(o && o.method) || 'GET', body:(o && o.body) ? String(o.body) : ''});
  const c = QUEUE.length ? QUEUE.shift() : {data:null, ok:false, status:404};
  return Promise.resolve({status:(c.status == null ? 200 : c.status), ok:(c.ok !== false),
                          json:function(){ return Promise.resolve(c.data); }});
}
const out = {};
const UPD = {available:false, current_version:'9.0.7', latest_version:'9.0.8', note:''};
const RUN = {ok:true, phase:'done', from:'9.0.7', to:'9.0.8',
             note:'已就位（9.0.7 ⇒ 9.0.8）· 请关窗重开 ClawsJoy PA（∨ 菜单「重启服务」）以生效',
             started_at:tsAgo(60), ended_at:tsAgo(55)};
function snap(){ return {state:paUpdRun.last.state, text:paUpdRun.last.text,
                         note:paUpdRun.last.note, in_effect:!!paUpdRun.last.in_effect}; }
(async function(){
  /* W11 端到端 正控：**活版**（/health 之顶层 version）＝ 目标版 ⇒ 唯书「已更新到 X」 */
  QUEUE.push({data:{version:'9.0.8', update:UPD}}); QUEUE.push({data:RUN});
  await paUpdFetch();
  out.effected = snap();
  /* W12 端到端 反控：活版仍旧（顶层 version 未前移）∧ build.version 已新（读盘）⇒ 维持「请关窗重开以生效」 */
  QUEUE.push({data:{version:'9.0.7', build:{available:true, version:'9.0.8'}, update:UPD}});
  QUEUE.push({data:RUN});
  await paUpdFetch();
  out.not_yet = snap();
  console.log(JSON.stringify(out));
})();
"""


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-1200:])
    return json.loads(r.stdout.strip().splitlines()[-1])


_C = {}


def _v() -> dict:
    if "v" not in _C:
        _C["v"] = _node("\n".join(_parts_view()) + "\n" + TS_AGO + CASE_VIEW, "term1832v")
    return _C["v"]


def _e2e() -> dict:
    if "e" not in _C:
        _C["e"] = _node("\n".join(_parts_view()) + "\n" + TS_AGO + CASE_E2E, "term1832e2e")
    return _C["e"]


def _t() -> dict:
    if "t" not in _C:
        _C["t"] = _node("\n".join(_parts_term()) + "\n" + CASE_DOM, "term1832t")
    return _C["t"]


# ---------- W1 ～ W5：纯层（活版 vs 目标版 ＋ 键） ----------


def test_W1_活版等于目标版则唯书已更新到并撤请关窗重开():
    v = _v()["effected"]
    assert v["state"] == "done", v
    assert v["text"] == u"已更新到 9.0.8", v["text"]
    assert v["in_effect"] is True, v
    assert u"请关窗重开" not in v["note"], u"已生效 ⇒ ⛔ 载「请关窗重开」（辞与真相反 · pm_1832 §二.1）：" + v["note"]
    assert u"以生效" not in v["note"], v["note"]
    assert u"⇒" not in v["text"], u"⛔ 画箭头（from == to · §二.3）：" + v["text"]


def test_W2_反控活版不等于目标版则维持后端之辞():
    v = _v()["not_yet"]
    assert v["state"] == "done", v
    assert v["in_effect"] is False, v
    assert u"已就绪" in v["text"], v["text"]
    assert u"请关窗重开" in v["note"], u"真未生效 ⇒ 辞 ⛔ 改（照引后端 · §二.1）：" + v["note"]
    assert u"F5" in v["note"], v["note"]


def test_W3_幂等跑前端不画箭头():
    v = _v()["idem"]
    assert v["in_effect"] is False, v
    assert u"⇒" not in v["text"], u"from == to ⇒ ⛔ 画箭头（§二.3）：" + v["text"]


def test_W4_活版之源唯顶层version非build(): 
    v = _v()["disk_new"]
    assert v["in_effect"] is False, u"build.version（读盘）已新而活版仍旧 ⇒ ⛔ 判「已生效」（假绿）：" + str(v)
    assert u"请关窗重开" in v["note"], v["note"]


def test_W5_终态之键同跑稳定而新跑变():
    d = _v()
    assert d["key1"] and d["key1"] == d["key1b"], (d["key1"], d["key1b"])
    assert d["key2"] != d["key1"], u"新一次跑 ⇒ 键变（否则终态之记永不复位）：" + str(d)


def test_W11_端到端_活版自health之顶层version():
    u"""⭐ 真页一手逮之病之齿：活版 ⛔ 自 `u`（`/health.update` · 无 `version` 键）取 ——
    否则 `in_effect` 恒 `false` ⇒ 真页仍书旧辞（我之齿曾假绿 · 唯 `ctx` 覆写口被验）。"""
    d = _e2e()["effected"]
    assert d["state"] == "done", d
    assert d["text"] == u"已更新到 9.0.8", d["text"]
    assert d["in_effect"] is True, d
    assert u"请关窗重开" not in d["note"], d["note"]


def test_W12_端到端_反控build已新而活版仍旧则维持旧辞():
    d = _e2e()["not_yet"]
    assert d["in_effect"] is False, d
    assert u"已就绪" in d["text"], d["text"]
    assert u"请关窗重开" in d["note"], u"活版未动 ⇒ ⛔ 冒「已生效」（盘上之新版 ＝ 假绿）：" + d["note"]


# ---------- W6 ～ W10：DOM（自退 ＋ ⛔ 复现 ＋ 可退） ----------


def test_W6_终态逾阈自退():
    d = _t()
    assert d["shown"] == u"", d
    assert d["hold_gone"] == u"none", u"逾 PA_PREP_TERM_HOLD_MS ⇒ 自退：" + str(d)


def test_W7_反控已退之横幅同键不复现():
    d = _t()
    assert d["mid_ready"] == u"none", d
    assert d["same_key"] == u"none", u"中间来一次非终态 ∧ 同键再现 ⇒ ⛔ 复现（病一之治）：" + str(d)


def test_W8_反控键变则复位起新钟():
    d = _t()
    assert d["new_key"] == u"", u"新一次更新之终态 ⇒ 再现（复位）"
    assert d["new_key_gone"] == u"none", d


def test_W9_反控非终态不误隐():
    d = _t()
    assert d["running"] == u"", u"在办之相 ⛔ 误隐：" + str(d)
    assert d["x_running"] == u"none", u"✕ 唯终态现：" + str(d)


def test_W10_显式可退且同键不复现():
    d = _t()
    assert d["x_shown"] == u"", u"终态 ⇒ ✕ 现"
    assert d["x_done"] == u"", d
    assert d["dismissed"] == u"none", u"✕ ⇒ 退：" + str(d)
    assert d["after_dismiss"] == u"none", u"手动退后同键 ⇒ ⛔ 复现：" + str(d)


# ---------- S1 ～ S2：结构 ----------


def test_S1_paHtml之显式可退在格内且样式内联():
    h = _read(HTML)
    i = h.index(u'id="paPrep"')
    seg = h[i:h.index(u"</div>", i)]
    assert u'id="paPrepX"' in seg, u"可退之器须在 #paPrep 之格内"
    assert u'onclick="paPrepTermDismiss()"' in seg, u"点 ⇒ paPrepTermDismiss()"
    assert u"style=" in seg, u"样式须**内联**（⛔ 改 pa.css ／ pa_v3.css · 承 pm_1771 §二.3）"
    assert u"hidden" not in seg.split(">")[1], u"⛔ 以 hidden 充藏（收放归 paPrepRender）"
    # 样式二件 ⛔ 因本件而改（其字面 ⛔ 含 prep-x）
    for css in (ROOT / "web" / "pa" / "pa.css", ROOT / "web" / "pa" / "pa_v3.css"):
        assert u"prep-x" not in _read(css), u"样式须内联：⛔ 改 " + css.name


def test_S2_活版唯取顶层version且阈唯1处():
    t = _read(UJ)
    body = _fn(t, u"paUpdView")
    assert u"const lv = ss(c.live_version);" in body, \
        u"活版须唯取 `ctx.live_version`（⛔ 自 `u` 取 —— `u` ＝ /health.update 之子对象）"
    ap = _fn(t, u"paUpdApply")
    assert u"live_version:(_hh && _hh.version) ? String(_hh.version).trim() : ''" in ap, \
        u"活版之投须在 paUpdApply（一处 · ＝ /health 之顶层 version）"
    assert u"live_version" in body, u"活版须有覆写口"
    assert u".build.version" not in body.split(u"const lv =")[1], \
        u"⏔ 以 build.version（读盘）判「生效否」⇒ 假绿（pm_1832 §二.2）"
    assert t.count(u"h.version ? String(h.version).trim() : ''") == 1, \
        u"空窗之成判亦唯取**活版**（⛔ 盘 · 承 pm_1832 §二.2）"
    s = _read(SU)
    assert s.count(u"const PA_PREP_TERM_HOLD_MS") == 1, u"阈唯 1 处"
    assert s.count(u"getElementById('paPrep')") == 1, u"#paPrep 之取须一处"
    assert u"window.paPrepTermDismiss = paPrepTermDismiss;" in s, u"✕ 须可达（onclick）"
