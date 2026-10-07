# -*- coding: utf-8 -*-
u"""pm_1617 令一 ／ 令二 ／ 令四 ／ 令五 之齿（CW b2a5182 · 2026-10-07）。

一事：首屏之「准备中 ／ 不可用」之面 —— 真源 `GET /health`（**一处定形** · 纯函数 `paPrepView`）。
  L1 正控（有 done/total）⇒ 显「正在准备…」＋ 人话 ＋ **按字节之条**（含 % ／ MB）。
  L2 正控（无 done/total · 后端给 since_s）⇒ 显「已等 N 秒」（⛔ 死等无反馈）。
  L3 正控（页自计时之回落）⇒ **明书**「本页计时 · 后端未给已耗」（⛔ 造数）。
  L4 正控（唯 progress）⇒ 明书「字节不可量」（⛔ 以 % 充字节）。
  L5 就绪 ⇒ `state='ready'`（⇒ 横幅收 · 不遮面）。
  L6 失败 ⇒ **因（逐字）＋ 去处**（如 errors 逐字入屏）。
  L7 失败而无因 ⇒ 明书「后端未给因」（⛔ 空 ／ ⛔ 冒因）。
  L8 未答（门未开之极境）⇒ 「正在启动…」＋ 已重试 ／ 已等 ＋ 首启时长之预告。
  L9 未答至有界之末 ⇒ **出「去处」**（令四）。
  L10 曾就绪而后未答 ⇒ 明书「可能已停」＋ 去处（令二之「服务已停」）。
  L11 ⛔ 造相：`phase` 不在表 ⇒ **照实显原值**。
  L12 ⛔ 造相：无 `phase` ⇒ 明书「后端未给步骤」。
  L13 ⛔ 静默：非 200 ⇒ 显 HTTP 码（⛔ 当「就绪」）。
  L14 一处定形（结构）：`paPrepView` 定义唯 1 处 ∧ 其体 **⛔ DOM**（渲归 `paPrepRender` 一处）。
  L15 令一之反白屏（结构）：`web/pa.html` 之 `#paPrep` 为**静态可显之骨**（⛔ hidden ／ ⛔ 空）∧ 载 `startup.js`。
  L16 令五之 F5（结构）：⛔ `localStorage` ／ `sessionStorage` 之缓存 ∧ 取数带 `cache:'no-store'`。
  L17 正控（`/health.boot` · 有字节）⇒ 条 ＋ % ＋ 剩余秒 ＋ 步（**已对齐 TD_1616 之一处定形**）。
  L18 正控（`/health.boot` · 无字节）⇒ **步进度之条** ＋ 后端已耗 ＋ `download.note` 照实（⛔ 以 % 充字节）。
  L19 正控（`/health.boot` · `state=failed`）⇒ `failed.reason` 逐字 ＋ `failed.hint` 之去处。
  L20 正控（`/health.boot` · `state=ready`）⇒ `state='ready'`（横幅收）。
  L21 ⛔ 造相：`boot.phase` 不在表 ⇒ **照实显原值**。
  L22 一处定形（结构）：`boot` 唯 `paPrepView` 读（⛔ 渲点 ／ ⛔ 合一之判）。
  L23 正控（pm_1633 裁 ⒝）：`download.measured=true` ∧ `total_bytes=null` ∧ `done_bytes=0.3 MB` ⇒
      面须**显「已下 307 KB」**∧ 含「总长不可量」∧ 含「后端未给」（⛔ 静默略去已量之真读数 ∧ ⛔ 造数）。
 L24 反控（pm_1633 裁 ⒝）：`total_bytes` 有 ⇒ 面为「按字节之条」（**⛔ 含「总长不可量」**）；
     `measured=false`（done 为 null）⇒ 面 **⛔ 书「已下」**。
 L25 正控（pm_1638 裁 · 去重 · ⒜）：`measured ∧ ⛔total` 而**后端给 `note`** ⇒ 面含**后端 note 之逐字**
      且 **⛔ 含前端之回落辞**（`（总长不可量 —— 后端未给）`）—— **⛔ 二音**。
 L25b 反控（pm_1638 裁 · 去重 · ⒜）：后端之 `note` 为**他辞** ⇒ 面**照实**其辞 ∧ **⛔ 冒「后端未给」**。
 L26 反控（pm_1638 裁 · 去重 · ⒝）：后端 **⛔ 给 `note`**（空）⇒ 前端**补书**其由（回落 · ⛔ 无声）。
 L27 反控（pm_1638 裁 · 去重 · ⒞）：`total` 有 ⇒ 面为「X ／ Y（%）」之条 ∧ **⛔ 涉「不可量」**。
 L28 一处定形（结构）：回落辞**源中唯 1 处**（本函之内）∧ `update.js` **⛔ 自书其辞**。

  ╔╔ pm_1693 §四.2 裁（**量级自适应**）：`paPrepMB` 今为
     `≥ 1 MB` ⇒ `X.X MB` ／ `≥ 1 KB` ⇒ `N KB` ／ 否则 `N B`；`0` ∨ 非数 ⇒ 「未知」。
     ⇒ 本件之字面断言从新（昔为 `0.3 MB` · **已陈**）—— 载的仍是下游之真数。
以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_startup_prep_1617.py -q
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SU = ROOT / "web" / "pa" / "faces" / "startup.js"
HTML = ROOT / "web" / "pa.html"
SCRATCH = ROOT / "data" / "tmp" / "_cw_prep1617"

PREP = u"\u6b63\u5728\u51c6\u5907"          # 正在准备
BAR = u"\u5df2\u4e0b"                        # 已下
SEC = u"\u5df2\u7b49"                        # 已等
OUTLET = u"\u53bb\u5904"                     # 去处
START = u"\u6b63\u5728\u542f\u52a8"          # 正在启动


def _src() -> str:
    return io.open(str(SU), encoding="utf-8").read()


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


def _block(src: str, head: str, stop: str) -> str:
    i = src.find(head)
    assert i >= 0, u"未找到块头 " + head
    j = src.find(stop, i)
    assert j > 0, u"未找到块末 " + stop
    return src[i:j + len(stop)]


def _decl(src: str, prefix: str) -> str:
    for ln in src.split("\n"):
        if ln.startswith(prefix):
            return ln
    raise AssertionError(u"未找到声明 " + prefix)


def _harness() -> str:
    s = _src()
    parts = [
        _decl(s, u"const PA_PREP_POLL_MS"),
        _decl(s, u"const PA_PREP_TICK_MS"),
        _decl(s, u"const PA_PREP_WATCH_MS"),
        _decl(s, u"const PA_PREP_MAX_TRIES"),
        _block(s, u"const PA_PREP_PHASE = {", u"};"),
        _decl(s, u"const PA_PREP_NOTE_WAIT"),
        _decl(s, u"const PA_PREP_OUTLET"),
        _fn(s, u"paPrepNum"),
        _fn(s, u"paPrepMB"),
        _fn(s, u"paPrepMeasuredNote"),
        _fn(s, u"paPrepView"),
    ]
    cases = u"""
const CASES = [
 ["start_bar",   {status:"starting", startup:{ready:false, state:"starting", phase:"vector_model_download", done_bytes:12345678, total_bytes:83152000, eta_s:41.4}}, {elapsed_s:5}],
 ["start_secs",  {status:"starting", startup:{ready:false, status:"LLM就绪检查", since_s:12}}, {elapsed_s:99}],
 ["start_page",  {status:"starting", startup:{ready:false, status:"硬件检测"}}, {elapsed_s:7}],
 ["start_prog",  {status:"starting", startup:{ready:false, progress:40}}, {elapsed_s:3}],
 ["ready",       {status:"healthy",  startup:{ready:true, progress:100, status:"ready"}}, {elapsed_s:3}],
 ["failed",      {status:"starting", startup:{ready:false, state:"failed", errors:["联邦知识加载: boom"]}}, {elapsed_s:9}],
 ["failed_none", {status:"starting", startup:{ready:false, state:"failed"}}, {elapsed_s:9}],
 ["unreach",     null, {tries:5, elapsed_s:11}],
 ["unreach_out", null, {tries:90, elapsed_s:200}],
 ["unreach_was", null, {was_ready:true, elapsed_s:20}],
 ["phase_odd",   {status:"starting", startup:{ready:false, phase:"weird_phase"}}, {elapsed_s:1}],
 ["no_phase",    {status:"starting", startup:{ready:false}}, {elapsed_s:2}],
 ["http_503",    null, {http_status:503, tries:2, elapsed_s:3}],
 ["boot_bar",    {status:"starting", boot:{state:"starting", phase:"vector_model_download", since_s:23.4, phase_since_s:20.1, phases_done:4, phases_total:7, progress:57, failed:null, download:{measured:true, done_bytes:12345678, total_bytes:83152000, frac:0.1485, eta_s:41.4, note:""}}}, {elapsed_s:5}],
 ["boot_steps",  {status:"starting", boot:{state:"starting", phase:"kb", since_s:12.0, phase_since_s:12.0, phases_done:4, phases_total:7, progress:57, failed:null, download:{measured:false, done_bytes:null, total_bytes:null, frac:null, eta_s:null, note:"不可量（缓存件未见 ⇒ ⛔ 知进度）"}}}, {elapsed_s:99}],
 ["boot_fail",   {status:"starting", boot:{state:"failed", phase:"registries", since_s:9.0, phase_since_s:9.0, phases_done:2, phases_total:7, progress:28, failed:{reason:"重初始化失败（registry ／ 含向量模型准备）：boom", hint:"见 logs 之 gateway_<port>_console.log；若为向量模型下载失败（断网）⇒ 联网后重启"}, download:{measured:false, done_bytes:null, total_bytes:null, frac:null, eta_s:null, note:"不可量（缓存件未见 ⇒ ⛔ 知进度）"}}}, {elapsed_s:9}],
 ["boot_ready",  {status:"healthy", boot:{state:"ready", phase:"ready", since_s:41.0, phase_since_s:1.0, phases_done:7, phases_total:7, progress:100, failed:null, download:{measured:true, done_bytes:83152000, total_bytes:83152000, frac:1.0, eta_s:null, note:"已毕（缓存件齐）"}}}, {elapsed_s:3}],
 ["boot_odd",    {status:"starting", boot:{state:"starting", phase:"weird_phase", since_s:1.0, phase_since_s:1.0, phases_done:0, phases_total:0, progress:0, failed:null, download:{measured:false, done_bytes:null, total_bytes:null, frac:null, eta_s:null, note:""}}}, {elapsed_s:1}],
 ["boot_meas_nototal", {status:"starting", boot:{state:"starting", phase:"vector_model_download", since_s:23.4, phase_since_s:20.1, phases_done:4, phases_total:7, progress:57, failed:null, download:{measured:true, done_bytes:314572, total_bytes:null, frac:null, eta_s:null, note:""}}}, {elapsed_s:9}],
 ["boot_meas_nototal_note", {status:"starting", boot:{state:"starting", phase:"vector_model_download", since_s:23.4, phase_since_s:20.1, phases_done:4, phases_total:7, progress:57, failed:null, download:{measured:true, done_bytes:314572, total_bytes:null, frac:null, eta_s:null, note:"总长不可量（后端未给）"}}}, {elapsed_s:9}],
 ["boot_meas_nototal_note2", {status:"starting", boot:{state:"starting", phase:"vector_model_download", since_s:23.4, phase_since_s:20.1, phases_done:4, phases_total:7, progress:57, failed:null, download:{measured:true, done_bytes:314572, total_bytes:null, frac:null, eta_s:null, note:"总长不可量（HEAD 探不得）"}}}, {elapsed_s:9}],
 ["absent",      undefined, undefined]
];
const out = {};
for (const c of CASES) { out[c[0]] = paPrepView(c[1], c[2]); }
console.log(JSON.stringify(out));
"""
    return "\n".join(parts) + cases


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _v() -> dict:
    return _node(_harness(), "prep1617")


# ---------- L1 ～ L4：准备中之面（令一） ----------

def test_L1_正控_有字节则显条与百分比():
    v = _v()["start_bar"]
    assert v["state"] == "starting", v
    assert v["can_bar"] is True and v["pct"] == 14, v
    assert PREP in v["text"] and BAR in v["text"] and u"%" in v["text"], v["text"]
    assert u"MB" in v["text"] and u"约还需 41 秒" in v["text"], v["text"]
    assert u"向量模型" in v["text"], v["text"]


def test_L2_正控_无字节则显已等秒且源于后端():
    v = _v()["start_secs"]
    assert v["since_src"] == "backend" and v["since_s"] == 12, v
    assert PREP in v["text"] and (SEC + u" 12 秒") in v["text"], v["text"]
    assert u"本页计时" not in v["text"], v["text"]


def test_L3_正控_页自计时须明书_不冒后端之值():
    v = _v()["start_page"]
    assert v["since_src"] == "page" and v["since_s"] == 7, v
    assert (SEC + u" 7 秒（本页计时 · 后端未给已耗）") in v["text"], v["text"]


def test_L4_正控_唯进度则明书字节不可量():
    v = _v()["start_prog"]
    assert v["can_bar"] is False, v
    assert u"后端步进度 40%" in v["text"], v["text"]
    assert u"字节不可量" in v["text"], v["text"]
    assert u"MB" not in v["text"], v["text"]


# ---------- L5：就绪 ----------

def test_L5_就绪则收():
    v = _v()["ready"]
    assert v["state"] == "ready", v
    assert v["can_bar"] is False, v


# ---------- L6 ～ L7：不可用之面（令二） ----------

def test_L6_失败须显因与去处():
    v = _v()["failed"]
    assert v["state"] == "failed", v
    assert u"联邦知识加载: boom" in v["text"], v["text"]
    assert OUTLET in v["note"], v["note"]


def test_L7_失败无因须明书_不冒因():
    v = _v()["failed_none"]
    assert v["state"] == "failed", v
    assert u"后端未给因" in v["text"], v["text"]
    assert OUTLET in v["note"], v["note"]


# ---------- L8 ～ L13：极境与照实（令四 · 令一） ----------

def test_L8_未答须显正在启动与已重试():
    v = _v()["unreach"]
    assert v["state"] == "unreachable", v
    assert START in v["text"], v["text"]
    assert u"已重试 5 次" in v["text"] and (SEC + u" 11 秒") in v["text"], v["text"]
    assert u"2–4 分钟" in v["note"], v["note"]


def test_L9_未答至有界之末须出去处():
    v = _v()["unreach_out"]
    assert v.get("retry_out") is True, v
    assert OUTLET in v["note"], v["note"]


def test_L10_曾就绪而后未答须明书可能已停():
    v = _v()["unreach_was"]
    assert v["state"] == "unreachable", v
    assert u"可能已停" in v["text"], v["text"]
    assert OUTLET in v["note"], v["note"]


def test_L11_未知phase须照实显原值():
    v = _v()["phase_odd"]
    assert u"weird_phase" in v["text"], v["text"]


def test_L12_无phase须明书未给步骤():
    v = _v()["no_phase"]
    assert u"后端未给步骤" in v["text"], v["text"]


def test_L13_非200须显码_不当就绪():
    v = _v()["http_503"]
    assert v["state"] == "unreachable", v
    assert u"HTTP 503" in v["text"], v["text"]


def test_L13b_未给之入参不炸_且不当就绪():
    v = _v()["absent"]
    assert v["state"] == "unreachable", v


# ---------- L14 ～ L16：结构与令五（F5） ----------

def test_L14_一处定形_view唯一定义且不触DOM():
    s = _src()
    assert s.count("function paPrepView(") == 1, u"paPrepView 须唯 1 处"
    body = _fn(s, "paPrepView")
    assert "getElementById" not in body, u"判之函须纯（⛔ DOM）—— 渲归 paPrepRender 一处"
    assert s.count("function paPrepRender(") == 1, u"渲须一处"
    assert s.count("getElementById('paPrep')") == 1, u"#paPrep 之取须一处"


def test_L15_令一_静态骨可见且载脚本():
    h = io.open(str(HTML), encoding="utf-8").read()
    assert u'id="paPrep"' in h, u"首屏须有此骨"
    i = h.find(u'id="paPrep"')
    seg = h[i:i + 900]
    assert PREP in seg, u"静态骨须自带「正在准备…」（JS 未跑亦可见 · ⛔ 白屏）"
    assert u"hidden" not in seg.split(">")[0], u"静态骨 ⛔ 默认藏（藏则白屏复现）"
    assert u'<script src="pa/faces/startup.js"></script>' in h, u"startup.js 未载"


def test_L16_令五_状态唯自后端_无前端缓存():
    s = _src()
    assert u"localStorage" not in s and u"sessionStorage" not in s, u"⛔ 前端缓存之假态"
    assert u"cache:'no-store'" in s, u"取数须绕缓存"
    assert u"'/health'" in s, u"真源须为 /health"


# ---------- L17 ～ L22：`/health.boot`（TD_1616 之一处定形 · 已对齐） ----------

def test_L17_boot形_有字节则显条与剩余秒与步():
    v = _v()["boot_bar"]
    assert v["state"] == "starting", v
    assert v["can_bar"] is True and v["pct"] == 14, v
    assert PREP in v["text"] and BAR in v["text"] and u"%" in v["text"], v["text"]
    assert u"约还需 41 秒" in v["text"], v["text"]
    assert u"步 4/7" in v["text"], v["text"]
    assert u"向量模型" in v["text"], v["text"]


def test_L18_boot形_无字节则步进度与后端已耗与note照实():
    v = _v()["boot_steps"]
    assert v["can_bar"] is True and v["pct"] == 57, v
    assert v["since_src"] == "backend" and v["since_s"] == 12, v
    assert u"步 4/7（57%）" in v["text"], v["text"]
    assert (SEC + u" 12 秒") in v["text"], v["text"]
    assert u"MB" not in v["text"], u"⛔ 以 % 充字节（无字节则 ⛔ 书 MB）"
    assert u"不可量" in v["text"], u"download.note 须照实入屏"


def test_L19_boot形_失败须因之逐字与去处():
    v = _v()["boot_fail"]
    assert v["state"] == "failed", v
    assert u"重初始化失败（registry ／ 含向量模型准备）：boom" in v["text"], v["text"]
    assert u"gateway_<port>_console.log" in v["note"], v["note"]
    assert OUTLET in v["note"], v["note"]


def test_L20_boot形_就绪则收():
    v = _v()["boot_ready"]
    assert v["state"] == "ready", v


def test_L21_boot形_未知phase照实显原值():
    v = _v()["boot_odd"]
    assert u"weird_phase" in v["text"], v["text"]


def test_L22_一处定形_boot唯view读():
    s = _src()
    assert "boot" in _fn(s, "paPrepView"), u"`/health.boot` 须由 view 读（一处取）"
    assert "boot" not in _fn(s, "paPrepRender"), u"渲点 ⛔ 读 boot（承一处定形）"
    assert "boot" not in _fn(s, "paPrepMerge"), u"合一之判 ⛔ 读 boot（承一处定形）"


# ---------- L23 ～ L24：`measured ∧ ⛔ total`（pm_1633 裁 ⒝ · 「已量者须显」） ----------

def test_L23_裁B_已量而总长缺须显已下之真读数与不可量():
    v = _v()["boot_meas_nototal"]
    assert v["state"] == "starting", v
    assert u"已下 307 KB" in v["text"], v["text"]
    assert u"总长不可量" in v["text"], v["text"]
    assert u"后端未给" in v["text"], v["text"]
    assert u"步 4/7" in v["text"], v["text"]


def test_L24_裁B_反控_有总长则按字节条_未量则不书已下():
    bar = _v()["boot_bar"]
    assert u"总长不可量" not in bar["text"], bar["text"]
    assert u"已下 11.8 MB / 79.3 MB" in bar["text"], bar["text"]
    steps = _v()["boot_steps"]
    assert u"已下" not in steps["text"], steps["text"]
    assert u"总长不可量" not in steps["text"], steps["text"]


# ---------- L25 ～ L28：去重（pm_1638 裁 · 「由」归后端 note ／ 「读数」归前端 · 一处定形） ----------

FALLBACK = u"（总长不可量 —— 后端未给）"


def test_L25_裁去重_后端有note则前端不再书其由():
    v = _v()["boot_meas_nototal_note"]
    assert v["state"] == "starting", v
    assert u"已下 307 KB" in v["text"], v["text"]
    assert u"总长不可量（后端未给）" in v["text"], u"后端 note 之逐字须照实入屏"
    assert FALLBACK not in v["text"], u"⛔ 二音：后端已给其由 ⇒ 前端 ⛔ 再造"


def test_L25b_裁去重_后端之他辞亦照实且不冒后端未给():
    v = _v()["boot_meas_nototal_note2"]
    assert u"已下 307 KB" in v["text"], v["text"]
    assert u"总长不可量（HEAD 探不得）" in v["text"], v["text"]
    assert u"后端未给" not in v["text"], u"⛔ 冒「后端未给」（后端已给其辞 —— 承「未知 ⛔ 充知」）"
    assert FALLBACK not in v["text"], v["text"]


def test_L26_裁去重_后端未给note则前端补书其由():
    v = _v()["boot_meas_nototal"]
    assert u"已下 307 KB" in v["text"], v["text"]
    assert FALLBACK in v["text"], u"回落：后端 ⛔ 给其由 ⇒ 前端须补（⛔ 无声）"


def test_L27_裁去重_有总长则按字节条且不涉不可量():
    bar = _v()["boot_bar"]
    assert u"已下 11.8 MB / 79.3 MB（14%）" in bar["text"], bar["text"]
    assert u"不可量" not in bar["text"], bar["text"]


def test_L28_一处定形_回落辞唯源中一处且更新面不自书():
    s = _src()
    assert s.count(FALLBACK) == 1, u"回落辞须唯 1 处（一处定形）"
    assert _fn(s, u"paPrepMeasuredNote").count(FALLBACK) == 1, u"其辞须在本函之内"
    uj = io.open(str(ROOT / "web" / "pa" / "faces" / "update.js"), encoding="utf-8").read()
    while u"/*" in uj and u"*/" in uj:            # 剔注（注里述其病 ⛔ 算「自书」）
        a = uj.find(u"/*")
        b = uj.find(u"*/", a)
        if b < 0:
            break
        uj = uj[:a] + uj[b + 2:]
    assert u"总长不可量" not in uj, u"更新面 ⛔ 自书其辞（一处定形 · 二面共本函）"
