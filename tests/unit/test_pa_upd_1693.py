# -*- coding: utf-8 -*-
u"""pm_1693 §四 之齿 —— 二小改（⒜ `running` 占横幅 ／ ⒝ 量级自适应）＋ ⒞ 之「一处定形」。

一事：pm_1693 §四 裁三件（另案一 **准改** ／ 另案二 **准改** ／ `PA_UPD_RECENT_S = 3600` 准）。

判据：
  M1 `paPrepMB` 量级自适应：`16978` ⇒ `17 KB` ∧ `1048576` ⇒ `1 MB` ∧ `512` ⇒ `512 B`。
  M2 `0` ∨ 非数 ⇒ 「未知」（**⛔ 书「0」**）。
  M3 `paPrepMB` 唯 1 处定义（`startup.js` —— ⛔ 二处各写 · 共用之函）。
  U1 正控：`running` ⇒ **占横幅**（`paPrepMerge` 归更新之对象 ∧ 文案含「正在更新」）。
  U2 反控：`idle` ／ `available` ／ `latest` ／ `unchecked` ⇒ **⛔ 占**（归起服之态 ⇒ 横幅 ⛔ 出）。
  U3 照旧：`done` ／ `failed` ／ `restart` 之占横幅 ＝ **既有之支**（pm_1693 §一.4 所认之七景 ⒟⒠）⇒ 本件 ⛔ 动。
  U4 二表 ⛔ 交（正反控 · **起服之相 ⛔ 受牵**）：`PA_UPD_BUSY` ∩ `PA_PREP_PHASE` ＝ 空 ∧ ⛔ 含 `idle` ／ `done` ／ `failed`。
  U5 面侧：按钮文案含「约 17 KB」∧ **⛔ 含「0 MB」**（昔之病之标本）。
  R1 `PA_UPD_RECENT_S` ＝ `3600` ∧ 剔注后**唯 1 处**（一处定形）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_upd_1693.py -q
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
SU = ROOT / "web" / "pa" / "faces" / "startup.js"
UJ = ROOT / "web" / "pa" / "faces" / "update.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_upd1693"

UNKNOWN = u"\u672a\u77e5"     # 未知


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _strip(t: str) -> str:
    u"""剔注（承面册闸与 1621 之 S4 之同式）。"""
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
    u"""从**真件**抽取（move 而非 retype）—— 起服之公器 ＋ 更新之件。"""
    s, t = _read(SU), _read(UJ)
    return [
        _block(s, u"const PA_PREP_PHASE = {", u"};"),
        _decl(s, u"const PA_UPD_BUSY"),
        _fn(s, u"paPrepNum"), _fn(s, u"paPrepMB"), _fn(s, u"paPrepMeasuredNote"),
        _fn(s, u"paPrepMerge"),
        _decl(t, u"const PA_UPD_SRC"), _decl(t, u"const PA_UPD_POST"),
        _decl(t, u"const PA_UPD_RECENT_S"),
        _decl(t, u"const PA_UPD_PENDING_KEY"), _decl(t, u"const PA_UPD_WINDOW_S"),
        _decl(t, u"const PA_UPD_RETRY_MS"), _decl(t, u"const PA_UPD_RETRY_MAX_MS"),
        _decl(t, u"const PA_UPD_RECOVER_S"),
        _block(t, u"const PA_UPD_PHASE = {", u"};"),
        _decl(t, u"const PA_UPD_LOG"), _decl(t, u"const PA_UPD_OUTLET"),
        _decl(t, u"const PA_UPD_OUTLET_SELF"),
        _fn(t, u"paUpdAgeS"), _fn(t, u"paUpdView"), _fn(t, u"paUpdVerText"),
        _fn(t, u"paUpdBtnRender"),
    ]


TS_AGO = u"""
function tsAgo(sec){
  const d = new Date(Date.now() - sec * 1000);
  const p = function(n){ return (n < 10 ? '0' : '') + n; };
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T'
       + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds()) + '+0800';
}
"""

CASES = u"""
function PA_PREP_READY_V(){ return {state:'ready'}; }
const AV = {available:true, current_version:'9.0.1', latest_version:'9.0.2', size_bytes:16978, files:5, note:''};
const LT = {available:false, current_version:'9.0.2', latest_version:'9.0.2', size_bytes:0, note:'已是最新'};
const UN = {available:false, current_version:null, latest_version:null, size_bytes:0,
            note:'取清单 \u26d4 得：http://x/update_manifest.json'};
const BTN = {style:{display:'none'}, disabled:true, textContent:'', title:''};
const document = {getElementById:function(id){ return (id === 'paUpdGo') ? BTN : null; }};
function paUpdCurFromHealth(){ return ''; }

const out = {};
out.mb = {k16978:paPrepMB(16978), mb1:paPrepMB(1048576), b512:paPrepMB(512),
          zero:paPrepMB(0), nul:paPrepMB(null), nan:paPrepMB('x'), neg:paPrepMB(-1)};
out.busy = Object.keys(PA_UPD_BUSY).sort();
out.prep = Object.keys(PA_PREP_PHASE).sort();
out.overlap = out.busy.filter(function(k){ return PA_PREP_PHASE[k] != null; });
const OWNS = function(o){ return !!(o && Object.prototype.hasOwnProperty.call(o, 'src')); };
const M = function(u, ctx){ const r = paPrepMerge(PA_PREP_READY_V(), paUpdView(u, ctx), null);
  return {state:r.state, text:r.text, owned:OWNS(r)}; };
out.m = {};
out.m.running   = M(AV, {elapsed_s:1, run:{phase:'running', started_at:tsAgo(42), from:'9.0.1'}});
out.m.live_off  = M(null, {elapsed_s:9, run:null, run_live:true});
out.m.idle      = M(AV, {elapsed_s:1, run:{phase:'idle'}});
out.m.available = M(AV, {elapsed_s:1, run:{phase:'idle'}});
out.m.latest    = M(LT, {elapsed_s:1, run:{phase:'idle'}});
out.m.unchecked = M(UN, {elapsed_s:1, run:{phase:'idle'}});
out.m.done      = M(LT, {elapsed_s:1, run:{phase:'done', from:'9.0.1', to:'9.0.2', ended_at:tsAgo(30)}});
out.m.failed    = M(AV, {elapsed_s:1, run:{phase:'failed', note:'未成（rc=2）', ended_at:tsAgo(20)}});
/* `restart` 乃旧形（`/health.update.state` 之遗留之面）—— 本件╔ 改其后端之面。 */
out.m.restart   = M({available:true, current_version:'9.0.1', state:'restart'}, {elapsed_s:1, run:null});
const v = paUpdView(AV, {elapsed_s:1, run:{phase:'idle'}});
paUpdBtnRender(v);
out.btn = {text:BTN.textContent, display:BTN.style.display, disabled:BTN.disabled};
out.ver = paUpdVerText(v);
console.log(JSON.stringify(out));
"""


def _node() -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / "upd1693.js"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(
        "\n".join(_parts()) + "\n" + TS_AGO + CASES)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


_D = None


def _d() -> dict:
    global _D
    if _D is None:
        _D = _node()
    return _D


# ---------- M：量级自适应（⒝） ----------


def test_M1_量级自适应():
    mb = _d()["mb"]
    assert mb["k16978"] == "17 KB", mb
    assert mb["mb1"] == "1 MB", mb
    assert mb["b512"] == "512 B", mb


def test_M2_零与非数皆未知_且不书零():
    mb = _d()["mb"]
    for k in ("zero", "nul", "nan", "neg"):
        assert mb[k] == UNKNOWN, (k, mb)
    assert "0" not in mb["zero"], mb


def test_M3_函唯一处定义():
    assert _read(SU).count(u"function paPrepMB(") == 1
    assert _read(UJ).count(u"function paPrepMB(") == 0


def test_U5_面侧按钮文案_17KB_而_非0MB():
    b = _d()["btn"]
    assert b["display"] == "" and b["disabled"] is False, b
    assert u"17 KB" in b["text"], b
    assert u"0 MB" not in b["text"], b
    assert u"0 MB" not in _d()["ver"], _d()["ver"]


# ---------- U：占横幅（⒜） ----------


def test_U1_正控_running_则占横幅():
    m = _d()["m"]["running"]
    assert m["owned"] is True, m
    assert m["state"] == "running", m
    assert u"正在更新" in m["text"], m


def test_U1b_正控_服务自停之窗_仍占():
    m = _d()["m"]["live_off"]
    assert m["owned"] is True and m["state"] == "running", m


def test_U2_反控_idle_available_latest_unchecked_皆不占():
    m = _d()["m"]
    for k in ("idle", "available", "latest", "unchecked"):
        assert m[k]["owned"] is False, (k, m[k])
        assert m[k]["state"] == "ready", (k, m[k])


def test_U3_既有之支_done_failed_restart_照旧():
    m = _d()["m"]
    for k in ("done", "failed", "restart"):
        assert m[k]["owned"] is True, (k, m[k])
        assert m[k]["state"] == k, (k, m[k])


def test_U4_二表不交_起服之相不受牵():
    d = _d()
    assert d["overlap"] == [], d["overlap"]
    assert u"running" in d["busy"], d["busy"]
    assert u"running" not in d["prep"], d["prep"]
    for k in ("idle", "done", "failed"):
        assert k not in d["busy"], (k, d["busy"])


# ---------- R：一处定形（⒞） ----------


def test_R1_逾窗之阈一处定形():
    t = _strip(_read(UJ))
    assert len(re.findall(r"\b3600\b", t)) == 1, re.findall(r"\b3600\b", t)
    assert u"3600" in _decl(_read(UJ), u"const PA_UPD_RECENT_S")
