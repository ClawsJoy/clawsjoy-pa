# -*- coding: utf-8 -*-
u"""pm_1691 之齿 —— 面内之「更新」按钮（`web/pa/faces/update.js` ＋ `pa.html` ＋ `faces.json`）。

一事：端已挂（`POST /v9/pa/update` · TD `c5a41ff`）⇒ 面内之按钮落面（契约承 pm_1685 §二.2 · 令承 pm_1691 §二）。

判据：
  B1 正控：`available === true` ⇒ 按钮**出**（`display:''`）∧ 文案含版本号 ＋ 大小（唯后端之数）。
  B2 反控：`available === false` ⇒ 按钮**⛔ 出**（⛔ 恒虚之支 —— 承「凡面之支须能真达」）。
  B3 点 ⇒ `POST /v9/pa/update` 体**逐字** `{"action":"start"}`（**唯由用户之点**）。
  B4 幂等：连点二次 ⇒ **唯 1 次** POST（⛔ 起第二支）。
  B5 轮询唯 `status`：`paUpdFetch` 之 POST 皆 `{"action":"status"}`（⛔ 副作用）。
  B6 读唯 `/health`（⛔ 第二读源）。
  R1 跑之三相（`running` ／ `done` ／ `failed`）：人话 ＋ 时长 ＋ 去处；`done` 须书「需重启」；`failed` **照书后端之辞**。
  R2 空 ／ 未答 ⇒ 明书（⛔ 充「已是最新」）。
  R3 `!o ∧ live`（服务自停之窗）⇒ 照实显「进行中」＋「本页会自动重试」（⛔ 充「已完成」）。
  R4 已终之跑逾窗（`PA_UPD_RECENT_S`）⇒ 归 `/health` 之真读数（⛔ 长挂「需重启」＝ 面之假）。
  R5 `idle` ⇒ 归可得性（= 未起过更新）。
  S1 结构：`/v9/pa/update` 字面**唯 1 处** ∧ `fetch(` **唯 2 处** ∧ ⛔ 硬编版号（承 1621 之 S2）。
  S2 面册闸：`update` 之 `requires` 含 `/v9/pa/update` ∧ `悬 == {}`。
  S3 页：`pa.html` 有 `#paUpdGo`（`button` · 初藏）∧ `faces.json` 之 `dom` 载之。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_update_face_1691.py -q
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
MAN = ROOT / "web" / "pa" / "faces.json"
SCRATCH = ROOT / "data" / "tmp" / "_cw_upd1691"

OUTLET = u"\u53bb\u5904"          # 去处


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _strip(t: str) -> str:
    u"""剔注（**承面册闸 `_ui_face_requires` 与 1621 之 S4 之同式**）。"""
    s = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    s = re.sub(r"(?m)^[ \t]*//[^\n]*$", "", s)
    s = re.sub(r"(?m)(?<![:/])//[^\n]*$", "", s)
    return s


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
    u"""取 `async function NAME(...)`（**含 `async`** —— ⛔ 丢，否则 `await` 不合法）。"""
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


def _parts(dom: bool = False) -> list:
    u"""从**真件**抽取（move 而非 retype）—— startup.js 之公器 ＋ update.js 之件。

    `dom=True` ⇒ 并取「轮询 ＋ 按钮」之一段（`paUpdApply` ／ `paUpdFetch` ／ `paUpdGo` …）。
    """
    s, t = _read(SU), _read(UJ)
    out = [
        _decl(s, u"const PA_PREP_POLL_MS"), _decl(s, u"const PA_PREP_TICK_MS"),
        _decl(s, u"const PA_PREP_WATCH_MS"), _decl(s, u"const PA_PREP_MAX_TRIES"),
        _block(s, u"const PA_PREP_PHASE = {", u"};"),
        _decl(s, u"const PA_PREP_NOTE_WAIT"), _decl(s, u"const PA_PREP_OUTLET"),
        _decl(s, u"const PA_PREP_ICON"), _decl(s, u"const PA_UPD_BUSY"),
        _fn(s, u"paPrepNum"), _fn(s, u"paPrepMB"), _fn(s, u"paPrepMeasuredNote"),
        _decl(t, u"const PA_UPD_SRC"), _decl(t, u"const PA_UPD_POST"),
        _decl(t, u"const PA_UPD_RECENT_S"), _block(t, u"const PA_UPD_PHASE = {", u"};"),
        _decl(t, u"const PA_UPD_LOG"), _decl(t, u"const PA_UPD_OUTLET"),
        _decl(t, u"const PA_UPD_OUTLET_SELF"),
        _fn(t, u"paUpdAgeS"), _fn(t, u"paUpdView"), _fn(t, u"paUpdVerText"),
    ]
    if dom:
        out += [
            _decl(t, u"const PA_UPD_POLL_MS"), _decl(t, u"const PA_UPD_BUSY_MS"),
            _fn(t, u"paUpdCurFromHealth"), _fn(t, u"paUpdVerRender"), _fn(t, u"paUpdBtnRender"),
            _decl(t, u"const paUpdRun"),
            _fn(t, u"paUpdApply"), _fn(t, u"paUpdSetInterval"), _fna(t, u"paUpdPost"),
            _fna(t, u"paUpdFetch"), _fna(t, u"paUpdGo"),
        ]
    return out


TS_AGO = u"""
function tsAgo(sec){
  const d = new Date(Date.now() - sec * 1000);
  const p = function(n){ return (n < 10 ? '0' : '') + n; };
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T'
       + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds()) + '+0800';
}
"""


def _harness_pure() -> str:
    u"""纯层：`paUpdView` ＋「跑」之相位（⛔ DOM）。"""
    cases = u"""
const AVAIL  = {available:true, current_version:'9.0.1', latest_version:'9.0.2', size_bytes:16978, files:5, channel:'internal', note:''};
const LATEST = {available:false, current_version:'9.0.2', latest_version:'9.0.2', size_bytes:0, note:'已是最新'};
const UNCH   = {available:false, current_version:null, latest_version:null, size_bytes:0, note:'取清单 \u26d4 得：http://x/update_manifest.json', note_why:'HTTPError'};
const out = {};
out.idle     = paUpdView(AVAIL, {elapsed_s:1, run:{ok:true, phase:'idle'}});
out.run      = paUpdView(AVAIL, {elapsed_s:1, run:{ok:true, phase:'running', started_at:tsAgo(42), from:'9.0.1'}});
out.run_page = paUpdView(AVAIL, {elapsed_s:7, run:{ok:true, phase:'running', from:'9.0.1'}});
out.done     = paUpdView(LATEST, {elapsed_s:1, run:{ok:true, phase:'done', from:'9.0.1', to:'9.0.2', note:'完成：9.0.1 \u21d2 9.0.2', ended_at:tsAgo(30)}});
out.failed   = paUpdView(AVAIL, {elapsed_s:1, run:{ok:true, phase:'failed', from:'9.0.1', to:'9.0.1', note:'未成（rc=2）—— 若已动盘 \u21d2 器已回滚至 9.0.1', ended_at:tsAgo(20)}});
out.done_old = paUpdView(LATEST, {elapsed_s:1, run:{ok:true, phase:'done', from:'9.0.1', to:'9.0.2', note:'完成', ended_at:tsAgo(7200)}});
out.fail_old = paUpdView(AVAIL, {elapsed_s:1, run:{ok:true, phase:'failed', from:'9.0.1', to:'9.0.1', note:'未成（rc=2）', ended_at:tsAgo(7200)}});
out.live_off = paUpdView(null, {elapsed_s:9, http_status:0, run:null, run_live:true});
out.noans    = paUpdView(null, {elapsed_s:9, http_status:404});
out.unchecked = paUpdView(UNCH, {elapsed_s:1, run:{ok:true, phase:'idle'}});
console.log(JSON.stringify(out));
"""
    return "\n".join(_parts()) + "\n" + TS_AGO + cases


def _harness_dom() -> str:
    u"""DOM 层：按钮之收放 ＋ 点（`start`）＋ 轮询（`status`）＋ 网之录（⛔ 真发）。"""
    cases = u"""
const NET = [];
const BTN = {style:{display:'none'}, disabled:true, textContent:'', title:''};
const document = {getElementById:function(id){ return (id === 'paUpdGo') ? BTN : null; }};
function setInterval(){ return 0; }
function clearInterval(){}
let QUEUE = [];
function fetch(u, o){
  NET.push({url:String(u), method:(o && o.method) || 'GET', body:(o && o.body) ? String(o.body) : ''});
  const c = QUEUE.length ? QUEUE.shift() : {data:{ok:true, phase:'idle'}};
  return Promise.resolve({status:(c.status == null ? 200 : c.status), ok:(c.ok !== false),
                          json:function(){ return Promise.resolve(c.data); }});
}
const out = {};
function paPrepFeedUpdate(v){ out.fed = v ? v.state : null; }
const AV = {version:'9.0.1', update:{available:true, current_version:'9.0.1', latest_version:'9.0.2', size_bytes:16978, files:5, note:''}};
const LT = {version:'9.0.2', update:{available:false, current_version:'9.0.2', latest_version:'9.0.2', note:'已是最新'}};
(async function(){
  QUEUE.push({data:AV}); QUEUE.push({data:{ok:true, phase:'idle'}});
  await paUpdFetch();
  out.btn_avail = {display:BTN.style.display, disabled:BTN.disabled, text:BTN.textContent, title:BTN.title};
  out.state_avail = paUpdRun.last.state;
  QUEUE.push({data:{ok:true, phase:'running', from:'9.0.1'}});
  await paUpdGo();
  out.after_go = {state:paUpdRun.last.state, display:BTN.style.display, disabled:BTN.disabled, live:paUpdRun.live};
  const n1 = NET.length;
  await paUpdGo();
  out.double_added = NET.length - n1;
  QUEUE.push({data:AV}); QUEUE.push({data:{ok:true, phase:'running', started_at:tsAgo(50), from:'9.0.1'}});
  await paUpdFetch();
  out.poll_state = paUpdRun.last.state;
  QUEUE.push({data:LT}); QUEUE.push({data:{ok:true, phase:'idle'}});
  await paUpdFetch();
  out.btn_latest = {display:BTN.style.display, disabled:BTN.disabled, state:paUpdRun.last.state};
  QUEUE.push({status:404, ok:false, data:null}); QUEUE.push({status:404, ok:false, data:null});
  await paUpdFetch();
  out.down = {state:paUpdRun.last.state, display:BTN.style.display};
  out.net = NET;
  console.log(JSON.stringify(out));
})();
"""
    return "\n".join(_parts(True)) + "\n" + TS_AGO + cases


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


_CACHE = {}


def _v() -> dict:
    if "v" not in _CACHE:
        _CACHE["v"] = _node(_harness_pure(), "face1691pure")
    return _CACHE["v"]


def _b() -> dict:
    if "b" not in _CACHE:
        _CACHE["b"] = _node(_harness_dom(), "face1691dom")
    return _CACHE["b"]


# ---------- B：按钮之正反控 ＋ 点 ＋ 轮询 ----------


def test_B1_available_则按钮出且文案唯后端之数():
    b = _b()["btn_avail"]
    assert b["display"] == "", b
    assert b["disabled"] is False, b
    assert u"9.0.2" in b["text"] and u"约" in b["text"], b
    assert u"9.0.2" in b["title"] or u"/v9/pa/update" in b["title"], b


def test_B2_非available_则按钮不出():
    b = _b()["btn_latest"]
    assert b["display"] == "none", b
    assert b["disabled"] is True, b
    assert b["state"] == "latest", b


def test_B3_点则start且唯由用户之点():
    d = _b()
    posts = [x for x in d["net"] if x["method"] == "POST"]
    starts = [x for x in posts if x["body"] == u'{"action":"start"}']
    assert len(starts) == 1, posts
    assert starts[0]["url"].endswith(u"/v9/pa/update"), starts[0]
    assert d["after_go"]["state"] == "running", d["after_go"]
    assert d["after_go"]["display"] == "none", u"在跑 ⇒ 按钮 ⛔ 出"


def test_B4_幂等_连点二次唯一次POST():
    assert _b()["double_added"] == 0, _b()["double_added"]


def test_B5_轮询唯status_无副作用():
    d = _b()
    posts = [x for x in d["net"] if x["method"] == "POST"]
    assert posts, u"无 POST"
    for x in posts:
        assert x["body"] in (u'{"action":"status"}', u'{"action":"start"}'), x
    assert sum(1 for x in posts if x["body"] == u'{"action":"start"}') == 1, \
        u"start 唯由用户之点（唯 1 次）"
    assert sum(1 for x in posts if x["body"] == u'{"action":"status"}') >= 3, posts


def test_B6_读唯health_不引第二读源():
    d = _b()
    gets = [x for x in d["net"] if x["method"] == "GET"]
    assert gets and all(x["url"].endswith(u"/health") for x in gets), gets


def test_B7_端未答则照实为未答且按钮不出():
    d = _b()["down"]
    assert d["state"] == "unanswered", d
    assert d["display"] == "none", d


# ---------- R：「跑」之三相 ＋ 空 ／ 逾窗 ----------


def test_R1_running_须有人话与已等与不可量():
    v = _v()["run"]
    assert v["state"] == "running" and v["can_start"] is False, v
    assert u"正在更新" in v["text"], v["text"]
    assert u"已等 42 秒" in v["text"], v["text"]
    assert u"进度不可量" in v["note"], v["note"]
    assert u"自动重试" in v["note"], v["note"]


def test_R1b_无起刻则回落本页计时照实():
    v = _v()["run_page"]
    assert v["state"] == "running", v
    assert u"本页计时" in v["text"] and u"已等 7 秒" in v["text"], v["text"]


def test_R2_done_须书已就绪与需重启与去处():
    v = _v()["done"]
    assert v["state"] == "done", v
    assert u"已就绪" in v["text"], v["text"]
    assert u"9.0.1 \u21d2 9.0.2" in v["text"], v["text"]
    assert u"需重启" in v["note"] and u"自动重试" in v["note"], v["note"]


def test_R3_failed_须照书后端之辞含回滚之数():
    v = _v()["failed"]
    assert v["state"] == "failed", v
    assert u"更新失败：" in v["text"], v["text"]
    assert u"器已回滚至 9.0.1" in v["text"], u"回滚之数唯后端之辞（⛔ 自造）：" + v["text"]
    assert OUTLET in v["note"], v["note"]


def test_R4_空与未答须明书不充已最新():
    v = _v()["noans"]
    assert v["state"] == "unanswered", v
    assert u"更新面未答" in v["text"] and u"不等于" in v["note"], v
    u2 = _v()["unchecked"]
    assert u2["state"] == "unchecked", u2
    assert u"已是最新" not in u2["text"], u2


def test_R5_服务自停之窗照实显进行中():
    v = _v()["live_off"]
    assert v["state"] == "running", v
    assert u"未答" in v["text"] and u"更新进行中" in v["text"], v["text"]
    assert u"已完成" not in v["text"], u"⛔ 充「已完成」：" + v["text"]
    assert u"自动重试" in v["note"], v["note"]


def test_R6_逾窗则归health真读数不挂旧事():
    d = _v()["done_old"]
    assert d["state"] == "latest", u"已终之跑逾窗 ⇒ ⛔ 长挂「需重启」（面之假）：" + str(d)
    f = _v()["fail_old"]
    assert f["state"] == "available" and f["can_start"] is True, \
        u"逾窗之败 ⇒ 归可得性（按钮回 ⇒ 可重试）：" + str(f)


def test_R7_idle_则归可得性且可起():
    v = _v()["idle"]
    assert v["state"] == "available" and v["can_start"] is True, v


# ---------- S：结构 ＋ 面册闸 ＋ 页 ----------


def test_S1_结构_唯动端可引且fetch唯二处且不硬编版号():
    t = _read(UJ)
    assert not re.search(r"\d+\.\d+\.\d+", t), u"update.js ⛔ 硬编版号（承 1621 之 S2）"
    src = _strip(t)
    pa = re.findall(r"/v9/pa/[A-Za-z0-9_/]*", src)
    assert pa == [u"/v9/pa/update"], u"唯「动」端可引（pm_1691）：" + repr(pa)
    assert src.count(u"fetch(") == 2, u"取数唯二处（读 /health ＋ 动 /v9/pa/update）：%d" % src.count(u"fetch(")
    assert u'{"action":"start"}' in src, u"体须逐字（契约 pm_1685 §二.2）"


def test_S2_面册闸_requires含update端且悬空():
    from core.pa import gateway_routes as G
    ro = G._ui_faces_readout()
    assert ro["悬"] == {}, ro["悬"]
    upd = {f["id"]: f for f in ro["faces"]}["update"]
    assert u"/v9/pa/update" in upd["requires"], upd


def test_S3_页有按钮且面册载之():
    h = _read(HTML)
    assert u'id="paUpdGo"' in h, u"pa.html 须有按钮位（pm_1691 §二.1）"
    assert u'onclick="paUpdGo()"' in h, u"点须接 paUpdGo（唯由用户之点）"
    assert u"display:none" in h.split(u'id="paUpdGo"')[1][:160], u"初藏（唯 available 时现）"
    j = json.loads(_read(MAN))
    upd = {f["id"]: f for f in j["faces"]}["update"]
    assert u"#paUpdGo" in upd["dom"], upd
