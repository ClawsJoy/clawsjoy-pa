# -*- coding: utf-8 -*-
u"""令 1886 ／ 1890 ／ 1897 之齿 —— 壳层（桌面程序本体）更新之面。

一事（老板之令「净机 desktop 版本更新升级」· pm_1886）：⭐「载荷有新版本」⛔ 等于「壳有新版本」
  ⇒ 用户面上**二路必分**（承「等待不可用必显形」＋「产出有痕有去处」）：
    ⒜ **内容版本**（载荷）⇒ `update.js` 之 `#paVerRow` ＋ `#paUpdGo`（既有 · 琥珀）；
    ⒝ **桌面程序（壳）** ⇒ 本件之 `#paShellUpdGo` ＋ 「更多 ▾ → 系统」之一行（蓝 · 一处定形）。

判据：
  S1 一处定形：`paPrepMerge` 唯 1 处 ∧ 横幅之渲唯 `startup.js` 一处（`shellupd.js` ⛔ 触 `#paPrep`）。
  S2 投口唯 1：本面之视图 ⇒ 渲 ＋ 投 唯 `paShuPublish` 一处（`paPrepFeedShell(` 唯 1）。
  S3 桥（**冻结** · pm_1897 §一.1）：名 ／ 态八 ／ 码七 —— 逐字（⛔ 二份字面 · 齿钉）。
  S3b 态与码之集：无重 ／ 无缺。
  S4 二路 ⛔ 混：`#paShellUpdGo` ⟂ `#paUpdGo`（各一函数 ∧ ⛔ 共用一句「已是最新」）。
  S4b 壳钮之文案与载荷可分（有新版 ≠ 已下好）。
  S5 无新版 ⛔ 占位：chip 唯「有新版 ∨ 失败 ∨ 在办」现；余入「更多 ▾ → 系统」之一行。
  S6 ⛔ 行话上屏（祖链判）：`electron-updater` ／ `NSIS` ／ `blockmap` ／ `quitAndInstall` ／ 端径 ／
     件号 —— **用户面之文**一字 ⛔ 载（唯**注释**可载 —— 工程之据）。
  S6b 注释可载工程之据（⛔ 丢真源）。
  S6c ⛔ 工程之饰上屏（`**` ⇒ 屏上照显 · 用户面之文一字 ⛔ 载）。
  S7 终态同尺：`PA_SHU_TERM_HOLD_MS` ＝ `startup.js` 之 `PA_PREP_TERM_HOLD_MS`（⛔ 二阈各说各话）。
  F3 `unsupported` 二判：⛔ `window.paShell` ⇒ `browser`；有壳而 ⛔ 带 `shellUpdateState` ⇒ `old-shell`。
  F4 拉为唯一真源（裁 ⒜）：`onShellUpdate` 唯登记「唤我再拉」（其回调**无参** ⇒ ⛔ 各自算态）。
  F4b 真点（唯由用户之点）＋ 幂等（⛔ 非「可点」⇒ ⛔ 发）。
  F4c 交出安装之投（终态 `term_key` ／ `term_deadline` ＝ at ＋ 20 s）。
  F4d 码可查（裁 ⒝）：屏 ⛔ 载码 ∧ `title` ＋ 工程注记载之。
  F5 态之映射 ＋ chip 之文（有新版 ⇒ 现 ／ 已下好 ⇒ 「重启并安装」／ 在办 ⇒ ⛔ 可点 ／ 已是最新 ⇒ ⛔ 现）。
  F5b 进度（`done` ／ `total` ⇒ `pct` ＋ 量级自适应）。
  F5d 可升态之 `title` 载「有新版本 X ⇒ 点一下 ⇒ 交桌面程序去下装」＋去处（pm_1909 §二.2 之一加）。
  F6 败 ⇒ 人话（含「没装坏 · 可重试」＋ 去处）∧ 未知码 ⇒ `unknown`。
  F7 交出安装 ⇒ 投横幅为 `done` ⇒ 现 ∧ 逾 20 s 自退（DOM）。
  F8 横幅之优先级：壳之「有新版 ／ 已下好」**⛔ 占**；壳之「在办 ／ 交出安装 ／ 败」占；
     反控：壳之源在**更新之四态之后**（既有之七景一字未动）∧ 在反馈之前。
  S8 界面之构：脚本一处（在 `update.js` ／ `startup.js` 之后）∧ 样式一处（蓝 · 与琥珀可分）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_shellupd_1897.py -q
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHU = ROOT / "web" / "pa" / "faces" / "shellupd.js"
SU = ROOT / "web" / "pa" / "faces" / "startup.js"
HTML = ROOT / "web" / "pa.html"
CSS = ROOT / "web" / "pa" / "pa_v3.css"
UPD = ROOT / "web" / "pa" / "faces" / "update.js"
FBS = ROOT / "web" / "pa" / "faces" / "feedback.js"
CFG = ROOT / "web" / "pa" / "faces" / "config.js"
ARC = ROOT / "web" / "pa" / "faces" / "archive.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_shu1897"

PHASES = ["unsupported", "idle", "checking", "available", "downloading",
          "downloaded", "installing", "failed"]
CODES = ["no-updater", "offline", "check-failed", "download-failed",
         "verify-failed", "install-failed", "unknown"]
JARGON = ["electron-updater", "NSIS", "blockmap", "quitAndInstall", "app-update.yml"]


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _strip_comments(s: str) -> str:
    u"""去注释（⛔ 去字面）—— 供「行话 ⛔ 上屏」之判（唯注释可载 · 用户面之文 ⛔ 载）。"""
    out, i, n = [], 0, len(s)
    while i < n:
        if s.startswith("/*", i):
            j = s.find("*/", i + 2)
            i = (j + 2) if j >= 0 else n
            out.append(" ")
        elif s.startswith("//", i):
            j = s.find("\n", i)
            i = j if j >= 0 else n
            out.append(" ")
        elif s[i] in "\"'":
            q = s[i]
            out.append(s[i])
            i += 1
            while i < n and s[i] != q:
                if s[i] == "\\":
                    out.append(s[i])
                    i += 1
                if i < n:
                    out.append(s[i])
                    i += 1
            if i < n:
                out.append(s[i])
                i += 1
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


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


def _read_n(src: str, prefix: str) -> int:
    ln = _decl(src, prefix)
    tail = ln.split(u"=", 1)[1].strip().rstrip(u";").strip()
    return int(tail)


def _parts_shu() -> list:
    s = _read(SHU)
    return [
        _decl(s, u"const PA_SHU_BRIDGE"),
        _decl(s, u"const PA_SHU_FN_STATE"),
        _decl(s, u"const PA_SHU_FN_GO"),
        _decl(s, u"const PA_SHU_FN_ON"),
        _decl(s, u"const PA_SHU_POLL_MS"),
        _decl(s, u"const PA_SHU_TERM_HOLD_MS"),
        _block(s, u"const PA_SHU_PHASES = [", u"];"),
        _block(s, u"const PA_SHU_CODES = [", u"];"),
        _block(s, u"const PA_SHU_PHASE_TXT = {", u"};"),
        _block(s, u"const PA_SHU_CODE_TXT = {", u"};"),
        _decl(s, u"const PA_SHU_OUTLET"),
        _decl(s, u"const PA_SHU_RESTART_NOTE"),
        _fn(s, u"paShuBridge"), _fn(s, u"paShuFn"), _fn(s, u"paShellUpdWhy"),
        _fn(s, u"paShellUpdSupported"), _fn(s, u"paShuNum"), _fn(s, u"paShuHas"),
        _fn(s, u"paShuMB"), _fn(s, u"paShuCanStart"), _fn(s, u"paShuChipTxt"),
        _fn(s, u"paShellUpdView"), _fn(s, u"paShellUpdRender"),
        _decl(s, u"const paShuRun"), _fn(s, u"paShuPublish"),
        _fna(s, u"paShellUpdFetch"), _fn(s, u"paShuSetInterval"),
        _fna(s, u"paShellUpdGo"), _fn(s, u"paShellUpdBegin"),
    ]


def _parts_term() -> list:
    s = _read(SU)
    return [
        _decl(s, u"const PA_PREP_TERM_HOLD_MS"),
        _decl(s, u"const PA_PREP_ICON"),
        _decl(s, u"let paPrepTermT"),
        _decl(s, u"let paPrepTermAt"),
        _decl(s, u"let paPrepTermKey"),
        _decl(s, u"let paPrepTermGone"),
        _fn(s, u"paPrepEl"),
        _fn(s, u"paPrepTermDismiss"),
        _fn(s, u"paPrepRender"),
    ]


def _parts_merge() -> list:
    s = _read(SU)
    return [
        _decl(s, u"const PA_UPD_BUSY"),
        _decl(s, u"let paPrepUpd"),
        _decl(s, u"let paPrepFb"),
        _decl(s, u"let paPrepShu"),
        _fn(s, u"paPrepFeedShell"),
        _fn(s, u"paPrepMerge"),
        _fn(s, u"paPrepPaint"),
    ]


CASE_VIEW = u"""
var window = {};
const NOW = 1000000;
const out = {};
function V(r, local, at){ return paShellUpdView(r, local, {now:((at == null) ? NOW : at)}); }
/* F3 unsupported 之二判 */
window.paShell = null;
out.no_bridge_why = paShellUpdWhy();
out.no_bridge = V(null, null);
window.paShell = {openFeedbackDir:function(){}};
out.old_shell_why = paShellUpdWhy();
window.paShell = {}; window.paShell[PA_SHU_FN_STATE] = function(){};
out.ok_why = paShellUpdWhy();
out.supported = paShellUpdSupported();
/* 冻结之集（逐字） */
out.phases = PA_SHU_PHASES;
out.codes = PA_SHU_CODES;
out.term_hold = PA_SHU_TERM_HOLD_MS;
out.poll_ms = PA_SHU_POLL_MS;
/* F5 态之映射 */
out.available = V({ok:true, phase:'available', current:'9.0.10', latest:'9.0.11'});
out.wait = V({ok:true, phase:'downloaded', current:'9.0.10', latest:'9.0.11'});
out.downloading = V({ok:true, phase:'downloading', current:'9.0.10', latest:'9.0.11',
                     progress:{done:1048576, total:2097152}});
out.installing = V({ok:true, phase:'installing', current:'9.0.10', latest:'9.0.11'});
out.idle = V({ok:true, phase:'idle', current:'9.0.10'});
out.checking = V({ok:true, phase:'checking', current:'9.0.10'});
out.junk = V({ok:true, phase:'zzz', current:'9.0.10'});
out.no_cur = V({ok:true, phase:'idle'});
out.unsupported_phase = V({ok:true, phase:'unsupported', current:'9.0.10'});
/* F6 败（码可查 · 人话 ＋ 去处） */
out.failed_offline = V({ok:false, code:'offline', message:'x'});
out.failed_weird = V({ok:false, code:'weird', message:'x'});
/* F7 交出安装（面之短告 · 终态） */
out.launching = V({ok:true, phase:'idle', current:'9.0.10'}, {kind:'launching', at:NOW}, NOW);
/* chip 之文（一处定形） */
out.chip = {};
['available','wait','running','failed','launching'].forEach(function(k){ out.chip[k] = paShuChipTxt(k); });
/* S6：用户面之辞 —— ⛔ 行话 */
out.txt = [];
[out.no_bridge, out.idle, out.checking, out.available, out.downloading, out.wait,
 out.installing, out.failed_offline, out.failed_weird, out.junk, out.launching,
 out.no_cur, out.unsupported_phase].forEach(function(v){ out.txt.push(v.text); out.txt.push(v.note); });
for(var k in out.chip) out.txt.push(out.chip[k]);
console.log(JSON.stringify(out));
"""

CASE_E2E = u"""
var window = {};
const NOW = 5000000;
Date.now = function(){ return NOW; };
function setInterval(){ return 0; }
function clearInterval(){}
function MK(id){ return {id:id, style:{display:''}, disabled:false, textContent:'', title:'',
                         attrs:{}, setAttribute:function(k,v){ this.attrs[k] = v; }}; }
var CHIP = MK('paShellUpdGo'), ROW = MK('paShellVer'), ENG = MK('paShellUpdEng');
var document = {getElementById:function(id){
  return (id === 'paShellUpdGo') ? CHIP : ((id === 'paShellVer') ? ROW
       : ((id === 'paShellUpdEng') ? ENG : null)); }};
var FEED = [];
function paPrepFeedShell(v){ FEED.push(v); }
const NET = {state:0, install:0, on:0, cb:null};
var BR = {phase:'available', current:'9.0.10', latest:'9.0.11'};
window.paShell = {};
window.paShell[PA_SHU_FN_STATE] = function(){ NET.state += 1;
  return Promise.resolve({ok:true, phase:BR.phase, current:BR.current, latest:BR.latest}); };
/* 壳之「触装」此刻 ⛔ 改相（真器或有迟）—— 以证「短告」之一支（真态未明）。 */
window.paShell[PA_SHU_FN_GO] = function(){ NET.install += 1; return Promise.resolve({ok:true}); };
window.paShell[PA_SHU_FN_ON] = function(cb){ NET.on += 1; NET.cb = cb; };
const out = {};
(async function(){
  paShellUpdBegin();
  for(var i = 0; i < 8; i++) await Promise.resolve();
  out.on_calls = NET.on;
  out.state_calls_1 = NET.state;
  out.chip_disp = CHIP.style.display;
  out.chip_txt = CHIP.textContent;
  out.chip_disabled = CHIP.disabled;
  out.chip_title = CHIP.title;
  out.row_txt = ROW.textContent;
  out.eng_txt = ENG.textContent;
  out.feed_n1 = FEED.length;
  out.feed_1 = FEED[0];
  /* 真点（壳尚未报相 ⇒ 面之交出安装之告现 ∧ ⛔ 可点） */
  await paShellUpdGo();
  out.install_calls = NET.install;
  out.launch_state = paShuRun.last.state;
  out.launch_chip = CHIP.textContent;
  out.launch_disabled = CHIP.disabled;
  out.launch_feed = FEED[FEED.length - 1];
  /* 幂等：短告现（⛔ 可点）⇒ ⛔ 再发 */
  await paShellUpdGo();
  out.install_calls_2 = NET.install;
  /* 壳报「在下」⇒ 真态压过短告（拉为唯一真源） */
  BR.phase = 'downloading';
  await paShellUpdFetch();
  out.state_after = paShuRun.last.state;
  out.chip_txt_after = CHIP.textContent;
  out.local_cleared = (paShuRun.local === null);
  /* F4：推 ⇒ 唯「唤我再拉一次」（回调无参 ⇒ ⛔ 各自算态） */
  out.cb_arity = NET.cb.length;
  var before = NET.state;
  NET.cb({phase:'installing', latest:'9.9.9'});
  for(var j = 0; j < 8; j++) await Promise.resolve();
  out.push_state_calls = NET.state - before;
  out.after_push = paShuRun.last.phase;
  out.after_push_latest = paShuRun.last.latest;
  /* 壳报 idle（装毕 ∨ 取消）⇒ 短告已清 ⇒ 静（终态 · ⛔ 长挂） */
  BR.phase = 'idle';
  await paShellUpdFetch();
  out.idle_state = paShuRun.last.state;
  out.idle_chip = CHIP.style.display;
  out.idle_feed = FEED[FEED.length - 1];
  /* F4d 码可查（裁 ⒝）：屏 ⛔ 载码 ∧ title ＋ 工程注记载之 */
  window.paShell[PA_SHU_FN_STATE] = function(){ NET.state += 1;
    return Promise.resolve({ok:false, code:'offline', message:'x'}); };
  await paShellUpdFetch();
  out.fail_chip_txt = CHIP.textContent;
  out.fail_row_txt = ROW.textContent;
  out.fail_chip_title = CHIP.title;
  out.fail_eng = ENG.textContent;
  out.fail_banner = FEED[FEED.length - 1];
  out.fail_state = paShuRun.last.state;
  out.fail_code = paShuRun.last.code;
  console.log(JSON.stringify(out));
})();
"""

CASE_MERGE = u"""
var NOW = 1000000;
Date.now = function(){ return NOW; };
var TIMERS = [];
function setTimeout(fn, ms){ TIMERS.push({fn:fn, at:NOW + (ms || 0), dead:false}); return TIMERS.length; }
function clearTimeout(id){ if(id && TIMERS[id - 1]) TIMERS[id - 1].dead = true; }
function fire(){ var t = TIMERS.slice(); for(var i = 0; i < t.length; i++){
  if(!t[i].dead && t[i].at <= NOW){ t[i].dead = true; t[i].fn(); } } }
function MK(){ return {style:{display:''}, attrs:{}, firstElementChild:{style:{}},
                       setAttribute:function(k,v){ this.attrs[k] = v; }}; }
var EL = MK(), XB = MK(), IC = MK(), TX = MK(), BAR = MK(), NOTE = MK();
var MAP = {'paPrep':EL, 'paPrepX':XB, 'paPrepIc':IC, 'paPrepTx':TX, 'paPrepBar':BAR, 'paPrepNote':NOTE};
var document = {getElementById:function(id){ return MAP[id] || null; }};
/* 桩：本横幅之基（起服已就绪 ⇒ 本应收）—— 唯测「合并 ＋ 投 ＋ 渲」之链。 */
function paPrepView(){ return {state:'ready', text:'已就绪（后端已可用）', note:''}; }
const paPrepRun = {h:null, t0:0, tries:0, http:null, wasReady:true, last:null};
const out = {};
/* F7 ／ F8：交出安装 ⇒ 投横幅 done ⇒ 现 ∧ 逾 20 s ⇒ 自退 */
paPrepFeedShell({state:'launching', text:'正在交给桌面程序安装 · 请不要关窗（本页会跟着重开）',
                 note:'点了之后：桌面程序会关掉并重开 · 本页会跟着重开（你的数据 ⛔ 动）',
                 term_deadline: NOW + PA_PREP_TERM_HOLD_MS});
out.launch_shown = EL.style.display;                  /* '' */
out.launch_state = EL.attrs['data-state'];            /* 'done' */
out.launch_icon = IC.textContent;                     /* '✅' */
out.launch_tx = TX.textContent;
out.launch_shu = paPrepShu;                           /* {state:'done', term_key:'shu|launching', ...} */
out.launch_x = XB.style.display;                      /* '' （终态 ⇒ 可退） */
NOW += PA_PREP_TERM_HOLD_MS + 1000; fire();
out.launch_gone = EL.style.display;                   /* 'none' */
/* F8 反控：壳之「有新版」／「已下好」⛔ 占横幅（其位 ＝ 顶栏 ＋ 「更多」之行） */
paPrepFeedShell({state:'available', text:'桌面程序有新版本'});
out.avail_shu = paPrepShu;                            /* null */
out.avail_banner = EL.style.display;                  /* 'none' （基 ＝ ready） */
paPrepFeedShell({state:'wait', text:'桌面程序之新版本已下好'});
out.wait_shu = paPrepShu;                             /* null */
/* F8 正控：壳之「在办」⇒ 占（⏳） */
paPrepFeedShell({state:'running', text:'正在更新桌面程序 · 正在下载新版本', note:'下载中 ⇒ 可继续用 · ⛔ 关窗'});
out.run_shu = paPrepShu;
out.run_banner = EL.style.display;                    /* '' */
out.run_state = EL.attrs['data-state'];               /* 'running' */
out.run_icon = IC.textContent;                        /* '⏳' */
/* F8 正控：壳之「败」⇒ 占（❌）＋ 明书 */
paPrepFeedShell({state:'failed', text:'更新没成 —— 没装坏 · 可重试 · 数据在', note:'本机 ⛔ 通网'});
out.fail_state = EL.attrs['data-state'];              /* 'failed' */
out.fail_icon = IC.textContent;                       /* '❌' */
/* F8 反控（既有之七景一字未动）：壳之源在**更新之四态之后** */
out.pr_upd_fail = paPrepMerge({state:'ready'}, {state:'failed', text:'更新没成'},
                              null, {state:'running', text:'壳'}).state;
out.pr_upd_restart = paPrepMerge({state:'ready'}, {state:'restart', text:'需重启'},
                                 null, {state:'running', text:'壳'}).state;
out.pr_upd_run = paPrepMerge({state:'ready'},
                             {state:'running', phase:'downloading', text:'更新中'},
                             null, {state:'done', text:'壳'}).state;
out.pr_upd_done = paPrepMerge({state:'ready'}, {state:'done', text:'已更新到 9.0.8'},
                              null, {state:'running', text:'壳'}).state;
/* 反控：壳之态压过**反馈**（最低） */
out.pr_shu_vs_fb = paPrepMerge({state:'ready'}, null, {state:'done', text:'留言回执'},
                               {state:'running', text:'壳'}).state;
/* 反控：无壳 ⇒ 照旧 */
out.pr_ready = paPrepMerge({state:'ready'}, null, null, null).state;
out.pr_fb = paPrepMerge({state:'ready'}, null, {state:'done', text:'留言回执'}, null).state;
out.pr_running = paPrepMerge({state:'ready'},
                             {state:'running', phase:'downloading', text:'更新中'},
                             null, null).state;
out.pr_unreach = paPrepMerge({state:'unreachable', text:'服务未答'}, null, null, null).state;
console.log(JSON.stringify(out));
"""


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


_C = {}


def _v() -> dict:
    if "v" not in _C:
        _C["v"] = _node("\n".join(_parts_shu()) + "\n" + CASE_VIEW, "shu1897v")
    return _C["v"]


def _e2e() -> dict:
    if "e" not in _C:
        _C["e"] = _node("\n".join(_parts_shu()) + "\n" + CASE_E2E, "shu1897e")
    return _C["e"]


def _m() -> dict:
    if "m" not in _C:
        _C["m"] = _node("\n".join(_parts_term() + _parts_merge()) + "\n" + CASE_MERGE, "shu1897m")
    return _C["m"]


# ---------- S1 ～ S2：一处定形 ----------

def test_S1_横幅之渲唯startup一处():
    su, code = _read(SU), _strip_comments(_read(SHU))
    assert su.count(u"function paPrepMerge(") == 1, u"多源合一之判须唯 1 处"
    assert su.count(u"function paPrepRender(") == 1, u"横幅之渲须唯 1 处"
    assert u"paPrepRender" not in code, u"shellupd.js ⛔ 自渲横幅（承「⛔ 二套面」）"
    assert u"paPrepPaint" not in code, u"shellupd.js ⛔ 直触横幅之重渲"
    assert u"paPrepEl" not in code and u"#paPrep" not in code, u"shellupd.js 之码 ⛔ 触横幅之 DOM"
    assert u"paPrepMerge" not in code, u"shellupd.js ⛔ 自持合一之判（其判唯 startup.js 一处）"
    assert set(re.findall(r"paPrep[A-Za-z_]*", code)) == {u"paPrepFeedShell"}, \
        u"凡提 `paPrep` ⇒ 唯投口（⛔ 多载）"
    assert code.count(u"paPrepFeedShell(") == 1, u"投口之**调用**唯 1 处"


def test_S2_投口唯1处():
    code, su = _strip_comments(_read(SHU)), _read(SU)
    assert code.count(u"paPrepFeedShell(") == 1, u"投横幅须唯 1 处（一处定形）"
    assert _read(SHU).count(u"paPrepFeedShell(") == 1, u"注释亦 ⛔ 多载（免歧）"
    assert code.count(u"function paShellUpdRender(") == 1, u"本面之渲须唯 1 处"
    assert code.count(u"paShellUpdRender(v)") == 2, u"渲之调用唯 1 处（＋ 其定义之形）"
    assert _fn(_read(SHU), u"paShuPublish").count(u"paShellUpdRender(v)") == 1, \
        u"渲之调用唯 paShuPublish 一处"
    body = _fn(_read(SHU), u"paShuPublish")
    assert u"paShellUpdRender(v)" in body and u"paPrepFeedShell(v)" in body, \
        u"渲 ＋ 投 须同出 paShuPublish"
    assert su.count(u"function paPrepFeedShell(") == 1, u"横幅之第四源须唯 1 个投口"
    assert u"paPrepMerge(v, paPrepUpd, paPrepFb, paPrepShu)" in _fn(su, u"paPrepPaint"), \
        u"四源须同投一处之判"


# ---------- S3：桥之冻结（名 ／ 态 ／ 码） ----------

def test_S3_桥之冻结():
    raw, code = _read(SHU), _strip_comments(_read(SHU))
    assert raw.count(u"const PA_SHU_BRIDGE = 'paShell';") == 1, u"桥名 ＝ paShell（一处字面 · ⛔ 二份）"
    assert raw.count(u"const PA_SHU_FN_STATE = 'shellUpdateState';") == 1, u"收态之函名（冻结）"
    assert raw.count(u"const PA_SHU_FN_GO = 'shellUpdateInstall';") == 1, u"触发装之函名（冻结）"
    assert raw.count(u"const PA_SHU_FN_ON = 'onShellUpdate';") == 1, u"推之函名（冻结）"
    assert not re.search(r"window\.paShell(?![A-Za-z0-9_])", code), \
        u"⛔ 直书 `window.paShell`（须经 PA_SHU_BRIDGE）"
    v = _v()
    assert v["phases"] == PHASES, v["phases"]
    assert v["codes"] == CODES, v["codes"]
    assert v["term_hold"] == 20000, v["term_hold"]


def test_S3b_态与码之集无重无缺():
    v = _v()
    assert len(v["phases"]) == 8 and len(set(v["phases"])) == 8, v["phases"]
    assert len(v["codes"]) == 7 and len(set(v["codes"])) == 7, v["codes"]


# ---------- S4：二路 ⛔ 混 ----------

def test_S4_二路分明():
    h, raw = _read(HTML), _read(SHU)
    assert h.count(u'id="paShellUpdGo"') == 1, u"顶栏须有壳层更新之钮（一处）"
    assert h.count(u'id="paUpdGo"') == 1, u"载荷更新之钮仍在（既有）"
    assert u'onclick="paShellUpdGo()"' in h, u"壳钮之点 ⇒ 本件之函"
    assert u"function paShellUpdGo(" in raw, u"本件自持其函（⛔ 借载荷之 paUpdGo）"
    shu_i, upd_i = h.find(u'id="paShellUpdGo"'), h.find(u'id="paUpdGo"')
    assert shu_i != upd_i and abs(shu_i - upd_i) > 200, u"二钮须各一件（⛔ 同格）"


def test_S4b_壳钮之文案与载荷可分():
    v = _v()
    assert v["available"]["text"].startswith(u"桌面程序有新版本"), v["available"]["text"]
    assert v["chip"]["available"] == u"\u2b06 桌面程序更新", v["chip"]["available"]
    assert v["chip"]["wait"] != v["chip"]["available"], u"已下好 ⇒ 别一辞"
    assert u"与内容之版本无关" in v["idle"]["text"], u"无新版之辞须与载荷之路**可分**"
    assert u"桌面程序（壳）版本" in v["idle"]["text"], v["idle"]["text"]


# ---------- S5：无新版 ⛔ 占位 ----------

def test_S5_无新版不占顶栏():
    body = _fn(_read(SHU), u"paShellUpdRender")
    assert u"v.state !== 'quiet' && v.state !== 'unsupported'" in body, \
        u"chip 唯「有新版 ∨ 失败 ∨ 在办」现（⛔ 常驻占位）"
    h = _read(HTML)
    assert u'id="paShellVer"' in h, u"无新版之读数须入「更多 ▾ → 系统」之一行（可查）"
    assert u'id="paShellUpdEng"' in h, u"码可查（工程注记之折叠）"
    seg = h[h.find(u'id="paMoreSys"'):h.find(u'id="paMoreSysFace"')]
    assert u'id="paShellVer"' in seg, u"该行须在「系统」段内（一步可达）"


# ---------- S6：⛔ 行话上屏（祖链判） ----------

def test_S6_行话不上屏():
    code = _strip_comments(_read(SHU))
    for t in JARGON:
        assert t not in code, u"用户面之文 ⛔ 载行话：" + t
    assert u"/v9/" not in code and u"/api/" not in code, u"⛔ 端点径"
    assert u"http" not in code.lower(), u"⛔ 网（桥 ⛔ 出网 · 本件 ⛔ 自取网）"
    assert not re.search(r"\d+\.\d+\.\d+", code), u"⛔ 硬编版号（真源 ＝ 桥之回）"
    v = _v()
    for t in v["txt"]:
        for j in JARGON:
            assert j not in t, u"面之辞 ⛔ 载行话：" + j + u" ｜ " + t
        assert u"D:\\" not in t and u"C:\\" not in t, u"面之辞 ⛔ 载本机之绝对径：" + t
        assert u"/v9/" not in t and u"/api/" not in t, u"面之辞 ⛔ 载端点径：" + t


def test_S6b_注释可载工程之据():
    assert u"electron-updater" in _read(SHU), u"工程之据（注释）宜在（⛔ 丢真源）"


def _no_comment(s: str) -> str:
    u"""去注释之**遮罩**形（⛔ 去其字）—— 供「饰之族 ⛔ 上屏」之判。

    由（一手 · 齿之器病 · pm_1909 之回）：`_strip_comments`（逐字之器）遇**正则中之引号**
    （如 `/'/g` ／ `/"/g`）即失准（其后之注释皆被吞 ⇒ 假红）⇒ ⛔ 用于本判 ⇒ 改**遮罩**
    （命中之区间置空 —— 同长 · 偏移不移）。

    ⚠ 器之限（照实）：`//` 之遮罩 ⛔ 辨「**串内之 `//`**」（如 `http://` ／ `POST /v9/…` 之后）
    ⇒ 其行之后半 ⛔ 判（**唯漏报 · ⛔ 误报** ⇒ 判「无」须先知此限）。
    """
    m = [True] * len(s)
    for pat in (r"<!--.*?-->", r"/\*.*?\*/", r"(?m)//[^\n]*"):
        for x in re.finditer(pat, s, flags=re.S):
            for i in range(x.start(), x.end()):
                m[i] = False
    return "".join((ch if m[i] else " ") for i, ch in enumerate(s))


_LIT = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"")


def _strings(s: str):
    u"""去注释后之**串内**（`'…'` ／ `"…"` · 单行）—— 供「饰之四符 ⛔ 入串」之判（pm_1923 §一.4 之一加）。

    ⚠ 由（器之限 · 照实）：源级之判**⛔ 分**「用户面之文」与「态之常量」（如 `'failed'`）
    ⇒ ⭐ 故本判唯钉「**串内 ⛔ 载饰之四符**」（`**` ／ `*` ／ `` ` `` ／ `~~`）——
      四符入串**必为**欲上屏之字（⛔ 有码之用法：本域 ⛔ 用指数运算符 ∧ ⛔ 以模板串拼字）；
      而「端字段名 ／ 端径 ／ 件号」之扫 ⇒ 归**祖链判**（真渲染 · ⛔ 源级 —— 承 `pa.html` 之
      `title` 本为「工程之据之地」· pm_1855 §三.2）。
    """
    return [m.group(0) for m in _LIT.finditer(_no_comment(s))]


def test_S6d_串内无饰之四符():
    u"""⭐ pm_1923 §一.4 之一加：凡用户面之文 ⇒ 扫「饰」四符（`**` ／ `*` ／ `` ` `` ／ `~~`）。

    由（一手 · 我自逮之第三 ／ 四例）：`feedback.js` 之「内容将出机（后端 `outbound=true`）⇒ …」
      ∧ `update.js` 之「…（端之回缺 `available`）」—— **反引号 ＋ 端字段名**上屏（＝写者之语误入用户之面，
      与「饰上屏」同源）⇒ 二处已清 ⇒ 本判钉之（⛔ 复归）。
    """
    for fp in (SHU, HTML, UPD, FBS, CFG, ARC):
        for lit in _strings(_read(fp)):
            for mark in (u"**", u"*", u"`", u"~~"):
                assert mark not in lit, (
                    u"串内 ⛔ 载 `%s`（屏上照显为字面）：%s ｜ %s" % (mark, str(fp), lit[:120]))


def test_S6c_用户面之文无markdown之饰():
    u"""⛔ 工程之饰上屏：`**`（markdown 之饰）屏上照显为字面 ⇒ 用户面之文**一字 ⛔ 载**。

    由（一手 · 我自逮）：`pa.html` 三处（首启盒之兜底 ／ 本机体检「模型之路」之对译表 ／ 留言之钮之
    `title`）＋ 本件新档二处（`chip.title` ／ 横幅之 `note`）—— 屏上读作「模型**没查成**（见其据）」。
    ⭐ 并（pm_1909 §三.2 之尺 · 一族）：**饰之族**（`**` ／ `~~`）我域**他面**尚有 —— 其「屏上之文 ＋
    `title`」之六处（`update.js` 之横幅二 ／ `feedback.js` 之钮 title ／ `config.js` 之讯 ／
    `archive.js` 之告二）于 pm_1909 之回中一并清之 ⇒ **此六档皆入本齿**（⛔ 复归）。
    判：先去 HTML 注释 ∧ 再去 JS ／ CSS 注释 ⇒ 所余（＝**用户面之文 ＋ 码**）一字 ⛔ 载（`**` ∧ `~~`）。
    """
    for fp in (SHU, HTML, UPD, FBS, CFG, ARC):
        t = _no_comment(_read(fp))
        assert u"**" not in t, u"用户面之文 ⛔ 载 `**`（屏上照显）：" + str(fp)
        assert u"~~" not in t, u"用户面之文 ⛔ 载 `~~`（同上）：" + str(fp)


# ---------- S7：终态同尺 ----------

def test_S7_终态之阈同尺():
    a = _read_n(_read(SHU), u"const PA_SHU_TERM_HOLD_MS")
    b = _read_n(_read(SU), u"const PA_PREP_TERM_HOLD_MS")
    assert a == b == 20000, (a, b)


# ---------- F3：unsupported 之二判 ----------

def test_F3_unsupported二判():
    v = _v()
    assert v["no_bridge_why"] == "browser", v["no_bridge_why"]
    assert v["old_shell_why"] == "old-shell", v["old_shell_why"]
    assert v["ok_why"] == "" and v["supported"] is True, v
    assert v["no_bridge"]["state"] == "unsupported", v["no_bridge"]["state"]
    assert v["no_bridge"]["can_start"] is False, v["no_bridge"]
    assert u"浏览器" in v["no_bridge"]["text"], v["no_bridge"]["text"]
    assert u"桌面程序" in v["no_bridge"]["note"], v["no_bridge"]["note"]


# ---------- F5：态之映射 ＋ chip ＋ 进度 ----------

def test_F5_态之映射():
    v = _v()
    assert v["available"]["state"] == "available" and v["available"]["can_start"] is True
    assert v["wait"]["state"] == "wait" and v["wait"]["can_start"] is True
    assert v["downloading"]["state"] == "running" and v["downloading"]["can_start"] is False
    assert v["installing"]["state"] == "running" and v["installing"]["can_start"] is False
    assert v["idle"]["state"] == "quiet" and v["idle"]["can_start"] is False
    assert v["checking"]["state"] == "quiet", v["checking"]["state"]
    assert v["junk"]["state"] == "quiet", u"不在集内之相 ⇒ 归 idle（⛔ 造态）"
    assert v["unsupported_phase"]["state"] == "unsupported", v["unsupported_phase"]["state"]


def test_F5b_进度与chip():
    v = _v()
    d = v["downloading"]
    assert d["can_bar"] is True and d["pct"] == 50, d
    assert u"1.0 MB" in d["text"] and u"2.0 MB" in d["text"], d["text"]
    assert v["chip"]["wait"] == u"\u27f3 重启并安装（桌面程序）", v["chip"]["wait"]
    assert v["chip"]["running"] == u"正在更新桌面程序…", v["chip"]["running"]
    assert v["chip"]["failed"].startswith(u"\u2b06 桌面程序更新"), v["chip"]["failed"]
    for k in ("available", "wait", "running", "failed", "launching"):
        assert u"桌面程序" in v["chip"][k], (k, v["chip"][k])


def test_F5d_可升态之title载下一步与去处():
    u"""pm_1909 §二.2 之一加（我之补 · 认）：**可升**态之 `title` 须载「有新版本 X ⇒ 点一下 ⇒
    交桌面程序去下装」＋**去处** ⇒ 使「点了会怎样」**可查**（承 pa.html:41 之律）。

    判：其数（版号）唯取自**桥之回**（`v.latest` ⇒ ⛔ 硬编 —— 见 `S6` 之 `\\d+\\.\\d+\\.\\d+` 之禁）
    ∧ **非**可升态 ⛔ 载此句（免各处一句话）。
    """
    e = _e2e()
    t = e["chip_title"]
    assert u"有新版本" in t, t
    assert u"9.0.11" in t, u"版号须取自桥之回（v.latest）：" + t
    assert u"点一下" in t, t
    assert u"交桌面程序" in t and u"下载并安装" in t, t
    assert u"去处" in t and u"更多" in t, u"去处须可查：" + t
    assert u"有新版本" not in e["fail_chip_title"], u"非可升态 ⛔ 载此句：" + e["fail_chip_title"]


def test_F5c_无当前版本之人话():
    v = _v()
    assert u"桌面程序未给" in v["no_cur"]["text"], v["no_cur"]["text"]


# ---------- F6：败之明书 ----------

def test_F6_败必明书():
    v = _v()
    f = v["failed_offline"]
    assert f["state"] == "failed" and f["can_start"] is True, f
    assert f["code"] == "offline", f["code"]
    assert u"没装坏" in f["text"] and u"可重试" in f["text"], f["text"]
    assert u"连不上网" in f["note"], f["note"]
    assert u"再点" in f["note"], u"去处（人话）：" + f["note"]
    assert v["failed_weird"]["code"] == "unknown", u"不在集内之码 ⇒ unknown（⛔ 造码）"


# ---------- F4：拉为唯一真源 ＋ 真点 ＋ 幂等 ----------

def test_F4_拉为唯一真源():
    e = _e2e()
    assert e["on_calls"] == 1, u"onShellUpdate 须唯登记一次（⛔ 二次起）"
    assert e["cb_arity"] == 0, u"回推之参 ⛔ 入算（拉为唯一真源 —— ⛔ 各自算态）"
    assert e["push_state_calls"] >= 1, u"推 ⇒ 唯「唤我再拉一次」"
    assert e["after_push"] == "downloading", u"态须取自**拉**之真源：" + str(e["after_push"])
    assert e["after_push_latest"] == "9.0.11", u"推之参 ⛔ 入算：" + str(e["after_push_latest"])
    assert e["feed_n1"] >= 1, u"取数 ⇒ 投横幅（一处）"
    assert e["feed_1"]["state"] == "available", u"本面之投须照实（占否 ⇒ 合一之判 · 见 F8）"


def test_F4b_真点与幂等():
    e = _e2e()
    assert e["state_calls_1"] == 1, e["state_calls_1"]
    assert e["chip_disp"] == "" and e["chip_txt"] == u"\u2b06 桌面程序更新", e
    assert e["chip_disabled"] is False, e
    assert u"9.0.10" in e["row_txt"] and u"有新版本" in e["row_txt"], e["row_txt"]
    assert u'桌面程序（壳）版本 <span id="paShellVer"' in _read(HTML), \
        u"其行之静件（「桌面程序（壳）版本」）须在页内 —— ⛔ 唯读数"
    assert e["install_calls"] == 1, u"真点 ⇒ 唯发一次"
    assert e["launch_state"] == "launching", e["launch_state"]
    assert e["launch_chip"] == u"已交给桌面程序安装…", e["launch_chip"]
    assert e["launch_disabled"] is True, u"短告现 ⇒ ⛔ 可点（免得交壳二回）"
    assert e["install_calls_2"] == 1, u"幂等：⛔ 可点 ⇒ ⛔ 再发"
    assert e["state_after"] == "running", u"真态（在下）压过短告"
    assert e["chip_txt_after"] == u"正在更新桌面程序…", e["chip_txt_after"]
    assert e["local_cleared"] is True, u"真态已明 ⇒ 短告退"


def test_F4c_终态之期与键():
    e = _e2e()
    lf = e["launch_feed"]
    assert lf is not None and lf["state"] == "launching", lf
    assert lf["term_key"] == "shu|launching", lf
    assert lf["term_deadline"] == 5000000 + 20000, lf["term_deadline"]
    assert u"桌面程序" in lf["text"], lf["text"]
    v = _v()
    lz = v["launching"]
    assert lz["state"] == "launching" and lz["can_start"] is False, lz
    assert lz["term_deadline"] == 1000000 + 20000, lz["term_deadline"]
    assert lz["term_key"] == "shu|launching", lz["term_key"]


def test_F4d_码可查而不上屏():
    e = _e2e()
    assert e["fail_state"] == "failed" and e["fail_code"] == "offline", e
    assert u"offline" not in e["fail_chip_txt"], u"屏上 ⛔ 载码：" + e["fail_chip_txt"]
    assert u"offline" not in e["fail_row_txt"], u"屏上 ⛔ 载码：" + e["fail_row_txt"]
    assert u"码：offline" in e["fail_chip_title"], u"title 载之（可查）：" + e["fail_chip_title"]
    assert u"码：offline" in e["fail_eng"], u"工程注记载之（可查）：" + e["fail_eng"]
    assert e["fail_banner"] is not None and e["fail_banner"]["state"] == "failed", e["fail_banner"]


def test_F4e_终态不占屏():
    e = _e2e()
    assert e["idle_state"] == "quiet", e["idle_state"]
    assert e["idle_chip"] == "none", u"终态 ⇒ chip ⛔ 常驻"
    assert e["idle_feed"]["state"] == "quiet", u"终态 ⇒ 面之投照实（quiet）"
    m = _m()
    assert m["avail_shu"] is None and m["wait_shu"] is None, u"横幅侧：quiet ⇒ 归 null（见 F8）"


# ---------- F7 ／ F8：横幅之投与自退 ----------

def test_F7_交出安装之横幅自退():
    m = _m()
    assert m["launch_shown"] == "", m
    assert m["launch_state"] == "done" and m["launch_icon"] == u"\u2705", m
    assert u"桌面程序" in m["launch_tx"], m["launch_tx"]
    assert m["launch_x"] == "", u"终态 ⇒ 显式可退（✕）"
    assert m["launch_shu"]["term_key"] == "shu|launching", m["launch_shu"]
    assert m["launch_gone"] == "none", u"逾 20 s ⇒ 自退（终态 ⛔ 长挂）"


def test_F8_有新版下好者不占横幅():
    m = _m()
    assert m["avail_shu"] is None and m["wait_shu"] is None, u"⛔ 无等待亦挂（其位 ＝ 顶栏 ＋ 更多）"
    assert m["avail_banner"] == "none", m["avail_banner"]


def test_F8b_在办与败者占横幅():
    m = _m()
    assert m["run_state"] == "running" and m["run_icon"] == u"\u23f3", m
    assert m["run_banner"] == "", m
    assert m["fail_state"] == "failed" and m["fail_icon"] == u"\u274c", m


def test_F8c_壳之源位与既有七景():
    m = _m()
    assert m["pr_upd_fail"] == "failed", u"壳之源在更新之「失败」之后"
    assert m["pr_upd_restart"] == "restart", u"壳之源在更新之「需重启」之后"
    assert m["pr_upd_run"] == "running", u"壳之源在更新之「在办」之后"
    assert m["pr_upd_done"] == "done", u"壳之源在更新之「完成」之后（既有之七景一字未动）"
    assert m["pr_shu_vs_fb"] == "running", u"壳之源在**反馈**（最低）之前"


def test_F8d_无壳照旧():
    m = _m()
    assert m["pr_ready"] == "ready", m
    assert m["pr_fb"] == "done", u"反馈之位（最低）一字未变"
    assert m["pr_running"] == "running", u"更新之「在办」一字未变"
    assert m["pr_unreach"] == "unreachable", u"起服之「未答」一字未变"


# ---------- S8：界面之构（页 ／ 样 ／ 脚本） ----------

def test_S8_页与样与脚本():
    h, c = _read(HTML), _read(CSS)
    assert h.count(u'<script src="pa/faces/shellupd.js"></script>') == 1, u"脚本须载（一处）"
    i_self = h.find(u'<script src="pa/faces/shellupd.js">')
    assert i_self > h.find(u'<script src="pa/faces/startup.js">'), u"须在 startup.js 之后（投口在彼）"
    assert i_self > h.find(u'<script src="pa/faces/update.js">'), u"须在 update.js 之后（二路各一）"
    assert c.count(u"#paShellUpdGo{") == 1, u"其形一处定形於 pa_v3.css"
    blk = _block(c, u"#paShellUpdGo{", u"#paShellUpdGo[disabled]")
    assert u"var(--blue)" in blk, u"取蓝 ⇒ 与琥珀之载荷钮可分"
    assert u"#paShellUpdGo{flex:0 0 auto" in blk, u"顶栏之件（⛔ 被压）"
    i_upd = c.find(u"#paUpdGo{")
    assert u"var(--amber)" in c[i_upd:i_upd + 260], u"载荷钮仍琥珀（既有）"


# ============ pm_2061 §三.1⒟（物 5 之二新齿 · CW b2a5182 · 2026-10-08） ============

CASE_2061 = u"""
var window = {paShell: {shellUpdateState: function(){ return Promise.resolve(null); }}};
var document = {getElementById: function(){ return null; }};
function paShuRenderSnap(r){
  var CHIP = {id:'paShellUpdGo', style:{display:''}, disabled:false, textContent:'', title:''};
  var ROW  = {id:'paShellVer',  style:{display:''}, disabled:false, textContent:'', title:''};
  var ENG  = {id:'paShellUpdEng', style:{display:''}, disabled:false, textContent:'', title:''};
  document.getElementById = function(id){
    return (id === 'paShellUpdGo') ? CHIP : ((id === 'paShellVer') ? ROW : ((id === 'paShellUpdEng') ? ENG : null));
  };
  var v = paShellUpdView(r, null, {now:1});
  paShellUpdRender(v);
  return {state:v.state, can_start:v.can_start, chip_disp:CHIP.style.display, chip_dis:CHIP.disabled,
          chip_txt:CHIP.textContent, chip_title:CHIP.title,
          row:ROW.textContent, row_title:ROW.title, eng:ENG.textContent, view_text:v.text};
}
var out = {};
out.dev   = paShuRenderSnap({ok:true, phase:'unsupported', current:'9.0.10'});
out.idle  = paShuRenderSnap({ok:true, phase:'idle', current:'9.0.10'});
out.avail = paShuRenderSnap({ok:true, phase:'available', current:'9.0.10', latest:'9.0.11'});
out.fail  = paShuRenderSnap({ok:false, code:'offline', message:'x'});
/* ⭐ pm_2074 物5 真联调（真壳一手）所逮：桥之**真形** —— 开发态回 ok:false ＋ phase:'unsupported'。 */
out.dev_real = paShuRenderSnap({ok:false, phase:'unsupported', current:'9.0.10', code:'no-updater',
                                message:'本壳不带更新器 ⇒ 请重新安装桌面程序'});
console.log(JSON.stringify(out));
"""


def _v2061() -> dict:
    if "v61" not in _C:
        _C["v61"] = _node("\n".join(_parts_shu()) + "\n" + CASE_2061, "shu2061")
    return _C["v61"]


def test_F3c_层一正控_开发态之chip与辞():
    u"""pm_2061 §三.1⒟（物 5 · 新齿一 · **层①正控**）：开发态（`phase=unsupported`）⇒
    ⒜ 顶栏 chip **⛔ 现**（`display:'none'` · `disabled:true` —— ⛔ 放占位 · ⛔ 假可点）；
    ⒝ `can_start === False`（装之门 ⛔ 供）；⒞ 其辞 ＝ pm_2061 §二.1 之逐字 ∧ ⛔ 载 `⛔`。"""
    d = _v2061()["dev"]
    assert d["state"] == "unsupported" and d["can_start"] is False, d
    assert d["chip_disp"] == "none", u"层① ⇒ chip ⛔ 现（⛔ 占位 · ⛔ 假可点）：%r" % (d,)
    assert d["chip_dis"] is True, u"层① ⇒ ⛔ 可点：%r" % (d,)
    assert u"⛔" not in d["row"], u"用户面 ⛔ 载 ⛔：%r" % d["row"]
    assert d["row"] == u"9.0.10 · 本机是开发态 ⇒ 此处装不上桌面程序的更新（装好的正式版才有此能）", d["row"]
    assert d["view_text"] == u"本机是开发态 ⇒ 此处装不上桌面程序的更新（装好的正式版才有此能）", d["view_text"]
    assert u"unsupported" in d["eng"], d["eng"]


def test_F3d_版本不重字():
    u"""pm_2061 §三.1⒟（物 5 · 新齿二 · **版本重字之扫**）：静件 `pa.html` 已书
    「桌面程序（壳）版本」⇒ 读数段 ⛔ 再书「版本 」。
    正控：四态之屏文 ⛔ 含「版本 版本」；反控：旧形（读数段自书「版本 」）⇒ 必咬。"""
    h = _read(HTML)
    assert u'桌面程序（壳）版本 <span id="paShellVer"' in h, u"其行之静件须在（承 F4b）"
    v = _v2061()
    for k in ("dev", "idle", "avail", "fail"):
        assert u"版本 版本" not in v[k]["row"], (k, v[k]["row"])
    for k in ("dev", "idle", "avail", "fail"):
        assert not v[k]["row"].startswith(u"版本 "), (k, v[k]["row"],
                u"读数段 ⛔ 以「版本 」起（静件「桌面程序（壳）版本」已书 ⇒ 屏成「版本 版本」）")
    s = _read(SHU)
    assert u"('版本 ' + (v.current" not in s, u"旧形（读数段自书「版本 」）⛔ 复归"
    mutant = u"桌面程序（壳）版本 " + u"版本 " + v["idle"]["row"]
    assert u"版本 版本" in mutant, u"反控：旧形（静件 ＋ 读数段自书「版本 」）⇒ 必咬（否则本齿为假）"


# ============ pm_2074 物5 真联调（真壳一手 · CW b2a5182 · 2026-10-09） ============

def test_F3e_二形同果_桥之真形非败():
    u"""pm_2074 物5 真联调所逮之**真根因** —— 桥之 `ok` ＝ `!(phase === 'failed' ∨
    phase === 'unsupported')`（`shell/shell_update.js` 之 `reply()`）⇒ 开发态回
    `ok:false ＋ phase:'unsupported' ＋ code:'no-updater'`。面若先论 `ok`
    ⇒ 把「本机无此能」误渲成「更新没成」（真壳之屏：chip 书「没成 · 可重试」，
    而折内自相矛盾书 `no-updater`）。
    制：相同的“无此能”二形 ⇒ 须同果；反控：真败（无 `phase` 之 `ok:false`）⇒ 仍须为败。"""
    v = _v2061()
    d = v["dev_real"]
    assert d["state"] == "unsupported", u"桥之真形（ok:false ＋ unsupported）⇒ ⛔ 成「败」：%r" % (d,)
    assert d["can_start"] is False, d
    assert d["chip_disp"] == "none", u"开发态 ⇒ chip ⛔ 现：%r" % (d,)
    assert u"没成" not in d["row"], u"开发态 ⛔ 书「没成」（旧病之形）：%r" % d["row"]
    assert d["row"] == v["dev"]["row"], u"真形与二形（ok:true）须同果（⛔ 二套面）"
    assert u"no-updater" in d["row_title"], u"码须可查（入 title）：%r" % d["row_title"]
    assert u"no-updater" in d["eng"], d["eng"]
    # 反控：真败 ⇒ 仍为败（本改 ⛔ 把真败也吨了）
    assert v["fail"]["state"] == "failed", v["fail"]
    assert u"没成" in v["fail"]["view_text"], v["fail"]
