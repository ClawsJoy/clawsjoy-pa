# -*- coding: utf-8 -*-
u"""令 1789 之齿 —— 空窗期之相位（web/pa/faces/update.js）＋ 顶栏可动（web/pa.html）＋
「暂不可起」之显 ＋ 顺带（#paUiStateRow ⛔ 入 PA_STALE 射程 ／ paRefreshLive ⛔ 清全域）。

一事（老板逐字）：「本机浏览器上也是无效」＋「F5 是有效，但是版本更新无效」。
  PM 之实证：一键更新后端端到端**通**（9.0.4 ⇒ 9.0.6）；病在**空窗期页面无相位**
  （点后约 40 秒服死 ⇒ /health 连不上 ⇒ 昔退「更新面未答」⇒ 用户读成「更新无效」）。

判据：
  W1 正控：标记在（pending_since_s）∧ 服未答 ⇒ running ∧ 文含「服务正在重启」「已等 N 秒」
          ∧ **⛔ 含「更新面未答」**（按实显 · ⛔ 谎报）。
  W2 反控：⛔ 标记 ∧ 服未答 ⇒ 照实 unanswered（⛔ 冒「重启中」）。
  W3 逾时（pending_stuck）⇒ 文含「仍未起来」＋ 阈数 ∧ 注含「下一步」「重启服务」「.cmd」（给去处）。
  W4 恢复（recovered）⇒ done ∧ 文「已更新至 X」。
  W5 退避：重启之窗内之取数间隔 = 2→4→8 秒（上限 8）—— 唯此窗退避。
  W6 标记生命周期：起（成功之点）⇒ 写；服复答 ∧ 版前移 ⇒ 清；服复答 ∧ 版未动 ⇒ 清；服未答 ⇒ 留。
  W7 「暂不可起」：⛔ can_start ⇒ paUpdGo **⛔ 静默**（版行显「暂不可起（因：…）」）∧ ⛔ 增 POST。
  S1 结构：PA_UPD_PENDING_KEY 唯 1 处定义；fetch( 仍唯 2 处；⛔ 硬编版号。
  S2 页：#paUpdGo **在 .top-right 内**（⛔ 在 .statusline 内 —— 免被压 ／ 挤出）∧ 版行可点之支在。
  S3 顺带：#paUiStateRow ⛔ 入 PA_STALE 射程（more.js ⛔ PA_STALE.mark）∧
          paRefreshLive ⛔ PA_STALE.clear()（⛔ 清全域 · 免静默显旧数）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_update_window_1789.py -q
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SU = ROOT / "web" / "pa" / "faces" / "startup.js"
UJ = ROOT / "web" / "pa" / "faces" / "update.js"
HTML = ROOT / "web" / "pa.html"
MORE = ROOT / "web" / "pa" / "faces" / "more.js"
TODAY = ROOT / "web" / "pa" / "faces" / "today.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_upd1789"

KEY = u"paUpdPending"


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


def _parts() -> list:
    u"""从**真件**抽取（move 而非 retype）。"""
    s, t = _read(SU), _read(UJ)
    return [
        _decl(s, u"const PA_PREP_POLL_MS"), _decl(s, u"const PA_PREP_TICK_MS"),
        _decl(s, u"const PA_PREP_WATCH_MS"), _decl(s, u"const PA_PREP_MAX_TRIES"),
        _block(s, u"const PA_PREP_PHASE = {", u"};"),
        _decl(s, u"const PA_PREP_NOTE_WAIT"), _decl(s, u"const PA_PREP_OUTLET"),
        _decl(s, u"const PA_PREP_ICON"), _decl(s, u"const PA_UPD_BUSY"),
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
        _fn(t, u"paUpdAgeS"), _fn(t, u"paUpdView"), _fn(t, u"paUpdVerText"),
        _fn(t, u"paUpdCurFromHealth"), _fn(t, u"paUpdVerRender"), _fn(t, u"paUpdBtnRender"),
        _decl(t, u"const paUpdRun"),
        _fn(t, u"paUpdApply"), _fn(t, u"paUpdSetInterval"), _fna(t, u"paUpdPost"),
        _fn(t, u"paUpdMarkRead"), _fn(t, u"paUpdMarkWrite"), _fn(t, u"paUpdWhyRender"),
        _fna(t, u"paUpdFetch"), _fna(t, u"paUpdGo"),
    ]


TS_AGO = u"""
function tsAgo(sec){
  const d = new Date(Date.now() - sec * 1000);
  const p = function(n){ return (n < 10 ? '0' : '') + n; };
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T'
       + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds()) + '+0800';
}
"""

CASE_W = u"""
const AVAIL = {available:true, current_version:'9.0.1', latest_version:'9.0.2', size_bytes:16978, note:''};
const out = {};
/* W1 正控：标记在 ∧ 服未答 ⇒ 重启之相位（⛔ 退「更新面未答」） */
out.pend_live   = paUpdView(null, {elapsed_s:3,  run_live:true, run:null, pending_since_s:37});
/* W2 反控：⛔ 标记 ∧ 服未答 ⇒ 照实未答 */
out.no_mark     = paUpdView(null, {elapsed_s:5,  run_live:false, run:null, http_status:0});
/* W3 逾时（如 180 s 未起）⇒ 给下一步 */
out.pend_stuck  = paUpdView(null, {elapsed_s:4,  run_live:true, run:null, pending_since_s:201, pending_stuck:true});
/* W4 恢复（版前移）⇒ 已更新至 X */
out.recovered   = paUpdView(AVAIL, {elapsed_s:1, run:null, recovered:'9.0.3'});
/* 反控：既有之自停之窗（⛔ 标记）⇒ 保持原辞（承 1691 之 R5） */
out.live_off    = paUpdView(null, {elapsed_s:9,  http_status:0, run:null, run_live:true});
console.log(JSON.stringify(out));
"""

CASE_DOM = u"""
var STORE = {};
var window = { sessionStorage: {
  getItem: function(k){ return (k in STORE) ? STORE[k] : null; },
  setItem: function(k, v){ STORE[k] = String(v); },
  removeItem: function(k){ delete STORE[k]; } } };
const VER = {textContent:'', title:'', style:{}};
const BTN = {style:{display:'none'}, disabled:true, textContent:'', title:''};
const document = {getElementById:function(id){ return (id === 'paUpdGo') ? BTN : ((id === 'paVerRow') ? VER : null); }};
const SEEN = [];
function setInterval(fn, ms){ SEEN.push(ms); return SEEN.length; }
function clearInterval(){}
const NET = [];
let QUEUE = [], DOWN = false;
function fetch(u, o){
  NET.push({url:String(u), method:(o && o.method) || 'GET', body:(o && o.body) ? String(o.body) : ''});
  if(DOWN) return Promise.reject(new Error('ECONNREFUSED'));
  const c = QUEUE.length ? QUEUE.shift() : {data:null, ok:false, status:404};
  return Promise.resolve({status:(c.status == null ? 200 : c.status), ok:(c.ok !== false),
                          json:function(){ return Promise.resolve(c.data); }});
}
function paPrepFeedUpdate(){}
const H_NEW = {version:'9.0.2', update:{available:false, current_version:'9.0.2', latest_version:'9.0.2', note:'已是最新'}};
const H_OLD = {version:'9.0.1', update:{available:true, current_version:'9.0.1', latest_version:'9.0.2', size_bytes:16978, note:''}};
const ST_IDLE = {ok:true, phase:'idle'};
const ST_RUN  = {ok:true, phase:'running', from:'9.0.1'};
const out = {};
function markFrom(v){ return (v && typeof v.t0 === 'number') ? {from:String(v.from), to:String(v.to)} : null; }
(async function(){
  /* W6a：起（成功之点）⇒ 写标记（F5 亦存） */
  QUEUE.push({data:H_OLD}); QUEUE.push({data:ST_IDLE});
  await paUpdFetch();
  QUEUE.push({data:ST_RUN});
  await paUpdGo();
  out.mark_written = markFrom(('paUpdPending' in STORE) ? JSON.parse(STORE['paUpdPending']) : null);
  /* W6b：服未答 ⇒ 标记留 ∧ 相位为「重启中」（⛔ 未答）∧ 退避 2→4→8 */
  DOWN = true;
  const s0 = SEEN.length;
  await paUpdFetch(); await paUpdFetch(); await paUpdFetch(); await paUpdFetch();
  out.down_state = {state:paUpdRun.last.state, reconnecting:!!paUpdRun.last.reconnecting,
                    text:paUpdRun.last.text};
  out.backoff = SEEN.slice(s0);
  out.mark_kept = ('paUpdPending' in STORE);
  out.ver_window = {ver:VER.textContent};
  /* W6c：服复答 ∧ 版前移 ⇒ 已更新至 X ＋ 清标记 */
  DOWN = false; QUEUE.push({data:H_NEW}); QUEUE.push({data:ST_IDLE});
  await paUpdFetch();
  out.recovered = {state:paUpdRun.last.state, text:paUpdRun.last.text, cleared:!('paUpdPending' in STORE)};
  /* W6c2：恢复之显报**留窗**（⛔ 一闪即没）—— 再取一次（标记已清）仍显「已更新至 X」 */
  QUEUE.push({data:H_NEW}); QUEUE.push({data:ST_IDLE});
  await paUpdFetch();
  out.recovered_kept = {state:paUpdRun.last.state, text:paUpdRun.last.text};
  /* W6d：服复答 ∧ 版未动 ⇒ 清标记（回落可得性 · ⛔ 长挂「重启中」） */
  paUpdRun.recoveredTo = ''; paUpdRun.recoveredAt = 0;
  STORE['paUpdPending'] = JSON.stringify({t0:Date.now() - 4000, from:'9.0.1', to:'9.0.2'});
  QUEUE.push({data:H_OLD}); QUEUE.push({data:ST_IDLE});
  await paUpdFetch();
  out.not_moved = {state:paUpdRun.last.state, cleared:!('paUpdPending' in STORE)};
  /* W7：⛔ can_start ⇒ paUpdGo ⛔ 静默（版行显「暂不可起」）∧ ⛔ 增 POST */
  paUpdRun.last = {state:'latest', can_start:false, bnote:'已是最新', current:'9.0.2'};
  const n0 = NET.length;
  await paUpdGo();
  out.refuse = {ver:VER.textContent, posts_added:NET.length - n0};
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


def _w() -> dict:
    if "w" not in _C:
        _C["w"] = _node("\n".join(_parts()) + "\n" + TS_AGO + CASE_W, "win1789w")
    return _C["w"]


def _d() -> dict:
    if "d" not in _C:
        _C["d"] = _node("\n".join(_parts()) + "\n" + TS_AGO + CASE_DOM, "win1789dom")
    return _C["d"]


# ---------- W1 ～ W4：空窗之相位（纯层） ----------


def test_W1_标记在且服未答则显重启中而非未答():
    v = _w()["pend_live"]
    assert v["state"] == "running", v
    assert v["reconnecting"] is True, v
    assert u"服务正在重启" in v["text"], v["text"]
    assert u"已等 37 秒" in v["text"], v["text"]
    assert u"更新面未答" not in v["text"], u"空窗期 ⛔ 退「更新面未答」：" + v["text"]


def test_W1b_空窗之版行不冒未答():
    t = _d()["ver_window"]
    assert u"更新中" in t["ver"], t
    assert u"更新面未答" not in t["ver"], u"版行 ⛔ 冒「更新面未答」（陈病 · 我一手逮）：" + t["ver"]


def test_W2_反控无标记则照实未答不冒重启中():
    v = _w()["no_mark"]
    assert v["state"] == "unanswered", v
    assert u"更新面未答" in v["text"], v["text"]
    assert u"服务正在重启" not in v["text"], u"⛔ 无据冒「重启中」：" + v["text"]


def test_W3_逾时须给下一步():
    v = _w()["pend_stuck"]
    assert v["reconnect_stuck"] is True, v
    assert u"仍未起来" in v["text"] and u"180" in v["text"], v["text"]
    assert u"下一步" in v["note"], v["note"]
    assert u"重启服务" in v["note"] and u".cmd" in v["note"], v["note"]


def test_W4_恢复则显已更新至X():
    v = _w()["recovered"]
    assert v["state"] == "done", v
    assert u"已更新至 9.0.3" in v["text"], v["text"]


def test_W4b_反控自停之窗无标记仍照旧():
    v = _w()["live_off"]
    assert v["state"] == "running", v
    assert u"更新进行中" in v["text"] and u"未答" in v["text"], v["text"]
    assert u"已完成" not in v["text"], v["text"]


# ---------- W5 ～ W7：退避 ＋ 标记生命周期 ＋ 拒起（DOM 层） ----------


def test_W5_重启窗内之退避为二四八并封顶():
    b = _d()["backoff"]
    assert b == [2000, 4000, 8000], b


def test_W6a_起更新则写标记():
    m = _d()["mark_written"]
    assert m == {"from": "9.0.1", "to": "9.0.2"}, m


def test_W6b_服未答则标记留且相位为重启中():
    d = _d()
    assert d["mark_kept"] is True, d
    s = d["down_state"]
    assert s["state"] == "running" and s["reconnecting"] is True, s
    assert u"服务正在重启" in s["text"], s["text"]
    assert u"更新面未答" not in s["text"], s["text"]


def test_W6c_服复答且版前移则已更新并清标记():
    r = _d()["recovered"]
    assert r["state"] == "done", r
    assert u"已更新至 9.0.2" in r["text"], r["text"]
    assert r["cleared"] is True, u"恢复后须清标记：" + str(r)


def test_W6c2_恢复之显报留窗非一闪即没():
    r = _d()["recovered_kept"]
    assert r["state"] == "done", r
    assert u"已更新至 9.0.2" in r["text"], r["text"]


def test_W6d_服复答而版未动则清标记回落可得性():
    n = _d()["not_moved"]
    assert n["cleared"] is True, n
    assert n["state"] != "done", u"版未动 ⛔ 冒「已更新」：" + str(n)
    assert n["state"] in ("available", "latest"), n


def test_W7_不可起须显暂不可起且不发POST():
    r = _d()["refuse"]
    assert u"暂不可起" in r["ver"], r
    assert u"已是最新" in r["ver"], r
    assert r["posts_added"] == 0, u"⛔ 不可起 ⇒ ⛔ 发 POST：" + str(r)


# ---------- S：结构 ＋ 页 ＋ 顺带 ----------


def test_S1_结构_键唯一定义且fetch仍二处且无硬编版号():
    t = _read(UJ)
    assert not re.search(r"\d+\.\d+\.\d+", t), u"update.js ⛔ 硬编版号"
    assert t.count(u"const PA_UPD_PENDING_KEY") == 1, u"标记之键须唯 1 处定形"
    assert t.count(u"function paUpdMarkRead(") == 1, u"标记之读唯 1 处"
    assert t.count(u"function paUpdMarkWrite(") == 1, u"标记之写唯 1 处"
    src = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    assert src.count(u"fetch(") == 2, u"取数唯二处：%d" % src.count(u"fetch(")


def test_S2_页_按钮出状态行入右上且版行可点之支在():
    h = _read(HTML)
    a = h.index(u'class="statusline"')
    b = h.index(u'class="top-right"')
    i = h.index(u'id="paUpdGo"')
    assert b < i, u"#paUpdGo 须在 .top-right 之内（⛔ 在 .statusline —— 免被压 ／ 挤出）"
    assert u"paUpdGo" not in h[a:b], u"#paUpdGo ⛔ 仍在 .statusline 内：" + h[a:b][-120:]
    assert u"display:none" in h[i:i + 160], u"初藏（唯 available 时现）"
    t = _read(UJ)
    assert u"el.onclick = on ?" in t, u"版行可点之支须在（can_start 时）"
    assert u"点此更新" in t, u"版行文案须可辨（点此更新）"


def test_S3_顺带_ui_state不入射程且刷新不清全域():
    m = _read(MORE)
    assert u"PA_STALE.mark" not in m, u"#paUiStateRow ⛔ 入 PA_STALE 射程（启动快照 ⇒ 天生越旧）"
    assert u"服务启动时之快照" in m, u"须标其源之性（静态 · 非实时）"
    y = re.sub(r"/\*.*?\*/", "", _read(TODAY), flags=re.S)   # 剔注（注里述其病 ⛔ 算「引用」）
    assert u"PA_STALE.clear()" not in y, u"⛔ 清全域（未重取之面 ⇒ 静默显旧数）"
    assert u"服务启动时之快照" in _read(ROOT / u"web" / u"pa" / u"faces" / u"status.js")
