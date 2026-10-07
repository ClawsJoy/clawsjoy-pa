# -*- coding: utf-8 -*-
u"""pm_1657 §二.2 之齿（CW b2a5182 · 2026-10-07）—— **壳之桥之页内侧**（开「落点目录」）。

一事：`web/pa/faces/feedback.js` 之桥（`paFbShell` ／ `paFbDirText` ／ `paFbDirEnabled` ／ `paFbOpenDirClick`）
  ＋ `web/pa.html` 之 `#paFbOpenDir` ／ `#paFbDirState` ＋ `faces.json` 之 dom。

  ⭐ 其约（pm_1657 §二.2 · **一处定形**）：**名** ＝ `window.paShell.openFeedbackDir`｜**参** ＝ **无**（径由壳自算
     ⇒ 守「桥 ⛔ 触他径」）｜**返** ＝ `Promise<{ok,path}|{ok:false,code,message}>`｜**失败之面** ＝ **⛔ 静默**
     （明书「⛔ 开得（因）⇒ 去处：自行打开 <径>」）。

  B1 一处定形：`PA_SHELL_BRIDGE` 之字面唯 1 处 ∧ 其调唯 1 处 ∧ **⛔ 传参**（⛔ 触他径）。
  B2 ⛔ 出网：桥之诸函之体 ⛔ 含 `fetch` ／ `XMLHttpRequest` ／ `sendBeacon`。
  B3 一处渲：`#paFbOpenDir` ／ `#paFbDirState` 之写唯在 `paFbRender` 一处 ∧ `pa.html` 有其 id ∧ 其钮 ⛔ 内联 `onclick`。
  B4 面之册：`faces.json` 之 feedback 条之 `dom` 含此二 id（⛔ 则面册闸必判「悬」）。
  B5 附件之取（**报之证**）：`#paFbFiles` 仍为 `<input type=file multiple>` ∧ feedback.js ⛔ 自造「选附件」之桥法
     （⛔ 二源 —— 承 pm_1657 §二.2「回落 ∨ 并存」之问 ⇒ 取「一途通二处」）。
  B6 行为（Node 台架 · 纯函）：无桥 ⇒ 禁 ＋ 明书「⛔ 供此能」＋ 去处（⛔ 空 ／ ⛔ 静默）；有桥之 idle ／ opening ／
     ok（同径 ／ 异径 ／ 壳未回径）／ fail 之诸支 ⇒ 逐字。
  B7 实跑（Node 台架）：无桥 ⇒ `paFbRun.dir.state = 'fail'` ∧ `code = 'E_NO_BRIDGE'`；有桥 ⇒ `ok` ∧ `path` 逐字。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_shell_bridge_1657.py -q
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FB = ROOT / "web" / "pa" / "faces" / "feedback.js"
HTML = ROOT / "web" / "pa.html"
FACES = ROOT / "web" / "pa" / "faces.json"
SCRATCH = ROOT / "data" / "tmp" / "_cw_shell1657"

BRIDGE = u"openFeedbackDir"
NOBRIDGE = u"\u6b64\u58f3 \u26d4 \u4f9b\u6b64\u80fd"     # 此壳 ⛔ 供此能
OUTLET = u"\u53bb\u5904"                                    # 去处
OPENED = u"\u5df2\u5f00"                                    # 已开
FAILED = u"\u26d4 \u5f00\u5f97"                             # ⛔ 开得


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


def _decl(src: str, prefix: str) -> str:
    for ln in src.split("\n"):
        if ln.startswith(prefix):
            return ln
    raise AssertionError(u"未找到声明 " + prefix)


def _nocomment(src: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    s = re.sub(r"(?m)^[ \t]*//[^\n]*$", "", s)
    s = re.sub(r"(?m)(?<![:/])//[^\n]*$", "", s)
    return s


def _harness() -> str:
    t = _read(FB)
    parts = [
        _decl(t, u"const PA_SHELL_BRIDGE"),
        u"var window = {};",
        u"var paFbRun = {dir: null};",
        u"var RENDER_N = 0;",
        u"function paFbRender(){ RENDER_N += 1; }",
        _fn(t, u"paFbShell"), _fn(t, u"paFbDirText"),
        _fn(t, u"paFbDirEnabled"), _fn(t, u"paFbOpenDirClick"),
    ]
    cases = u"""
const DIR = 'D:\\\\clawsjoy_v9\\\\data/pa/feedback';
const res = {state: 'ok', resolved_dir: DIR};
const out = {u: {}};
const U = out.u;
U.no_bridge_idle   = paFbDirText(res, false, null);
U.no_bridge_after  = paFbDirText(res, false, {state:'fail', code:'E_NO_BRIDGE'});
U.bridge_idle      = paFbDirText(res, true, null);
U.bridge_opening   = paFbDirText(res, true, {state:'opening'});
U.bridge_ok_same   = paFbDirText(res, true, {state:'ok', path: DIR});
U.bridge_ok_diff   = paFbDirText(res, true, {state:'ok', path: 'D:\\\\x'});
U.bridge_ok_nopath = paFbDirText(res, true, {state:'ok'});
U.bridge_fail      = paFbDirText(res, true, {state:'fail', code:'E_OPEN', message:'拒绝'});
U.no_dir_bridge    = paFbDirText({state:'ok'}, true, null);
U.en_no_bridge     = paFbDirEnabled(res, false, null);
U.en_bridge        = paFbDirEnabled(res, true, null);
U.en_opening       = paFbDirEnabled(res, true, {state:'opening'});
U.shell_absent     = (paFbShell() === null);
U.bridge_name      = PA_SHELL_BRIDGE;
/* 实跑（无桥） */
paFbOpenDirClick();
U.click_no_bridge  = {dir: paFbRun.dir, renders: RENDER_N,
                      text: paFbDirText(res, false, paFbRun.dir)};
async function main(){
  /* 实跑（有桥 · 异步） */
  window.paShell = {openFeedbackDir: function(){ return Promise.resolve({ok: true, path: DIR}); }};
  paFbRun.dir = null; RENDER_N = 0;
  paFbOpenDirClick();
  U.click_bridge_now = {dir: paFbRun.dir, renders: RENDER_N};
  await new Promise(function(r){ setTimeout(r, 0); });
  U.click_bridge_end = {dir: paFbRun.dir, renders: RENDER_N,
                        text: paFbDirText(res, true, paFbRun.dir)};
  /* 实跑（有桥 · 拒） */
  window.paShell = {openFeedbackDir: function(){ return Promise.resolve({ok:false, code:'E_OPEN', message:'拒'}); }};
  paFbRun.dir = null;
  paFbOpenDirClick();
  await new Promise(function(r){ setTimeout(r, 0); });
  U.click_bridge_fail = {dir: paFbRun.dir, text: paFbDirText(res, true, paFbRun.dir)};
  console.log(JSON.stringify(out));
}
main();
"""
    return "\n".join(parts) + cases


_CACHE = {}


def _v() -> dict:
    if "v" not in _CACHE:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        f = SCRATCH / "harness.js"
        io.open(str(f), "w", encoding="utf-8", newline="\n").write(_harness())
        exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
        r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        assert r.returncode == 0, u"node rc=" + str(r.returncode) + u" :: " + (r.stderr or "")[:900]
        _CACHE["v"] = json.loads(r.stdout.strip().splitlines()[-1])
    return _CACHE["v"]


# ---------- B1 一处定形 ----------

def test_B1_桥名唯1处且调唯1处且不传参():
    t = _read(FB)
    assert t.count(u"'openFeedbackDir'") == 1, u"桥之名须唯 1 处字面（一处定形）"
    code = _nocomment(t)
    assert len(re.findall(r"const\s+PA_SHELL_BRIDGE\b", code)) == 1, u"其定义须唯 1 处"
    assert code.count(u"window.PA_SHELL_BRIDGE = PA_SHELL_BRIDGE;") == 1, u"其出（供齿）须唯 1 处"
    assert code.count(u"sh[PA_SHELL_BRIDGE](") == 1, u"其调须唯 1 处"
    assert not re.search(u"sh\\[PA_SHELL_BRIDGE\\]\\([^)]", code), u"⛔ 传参（径由壳自算 ⇒ 桥 ⛔ 触他径）"
    assert u"openPath" not in code, u"⛔ 直调壳之泛能（唯开「落点目录」一处）"


def test_B2_桥之诸函不出网():
    t = _read(FB)
    for nm in (u"paFbShell", u"paFbDirText", u"paFbDirEnabled", u"paFbOpenDirClick"):
        body = _fn(t, nm)
        for bad in (u"fetch(", u"XMLHttpRequest", u"sendBeacon", u"WebSocket"):
            assert bad not in body, u"桥之函 " + nm + u" ⛔ 得含 " + bad + u"（桥 ⛔ 出网）"


# ---------- B3 一处渲 ＋ B4 面之册 ＋ B5 附件之取 ----------

def test_B3_钮之写唯在渲一处且页有之且无内联():
    t = _read(FB)
    assert t.count(u"paFbEl('paFbOpenDir')") == 2, u"其取须唯 2 处（渲 ／ 拴）"
    assert t.count(u"getElementById('paFbOpenDir')") == 0, u"⛔ 绕 `paFbEl` 直取"
    body = _fn(t, u"paFbRender")
    assert u"paFbOpenDir" in body and u"paFbDirState" in body, u"其渲须在 `paFbRender` 一处"
    h = _read(HTML)
    assert u'id="paFbOpenDir"' in h, u"页须有 #paFbOpenDir"
    assert u'id="paFbDirState"' in h, u"页须有 #paFbDirState"
    m = re.search(u'<button[^>]*id="paFbOpenDir"[^>]*>', h)
    assert m, u"其钮须为 button"
    assert u"onclick" not in m.group(0), u"⛔ 内联 onclick（拴唯在 `paFbBoot` 一处）"
    bt = _fn(t, u"paFbBoot")
    assert bt.count(u"paFbOpenDirClick") == 1, u"其拴须唯 1 处"


def test_B4_面册之dom含此二id():
    j = json.loads(_read(FACES))
    fb = [f for f in j["faces"] if f["id"] == "feedback"]
    assert len(fb) == 1, u"feedback 面须唯 1 条"
    dom = fb[0].get("dom") or []
    assert u"#paFeedback" in dom, dom
    assert u"#paFbOpenDir" in dom and u"#paFbDirState" in dom, u"面册须收此二 id（⛔ 则关面时 ⛔ 收起）—— " + str(dom)


def test_B5_附件仍走原生input且不另造桥():
    h = _read(HTML)
    m = re.search(u'<input[^>]*id="paFbFiles"[^>]*>', h)
    assert m, u"须仍为原生 input"
    tag = m.group(0)
    assert u'type="file"' in tag and u"multiple" in tag, u"附件须仍为 <input type=file multiple>（一途通二处）"
    t = _read(FB)
    assert t.count(u"'openFeedbackDir'") == 1, u"⛔ 另造「选附件」之桥法（二源）"
    assert u"chooseFiles" not in t and u"pickFiles" not in t, u"⛔ 桥之第二法"


# ---------- B6 行为（纯函） ----------

def test_B6_无桥须禁且明书供能与去处():
    u = _v()["u"]
    assert u["shell_absent"] is True, u"无壳 ⇒ `paFbShell()` 须 null"
    assert NOBRIDGE in u["no_bridge_idle"], u["no_bridge_idle"]
    assert OUTLET in u["no_bridge_idle"], u["no_bridge_idle"]
    assert u"data/pa/feedback" in u["no_bridge_idle"], u"须现示落点之径（可自复制）—— " + u["no_bridge_idle"]
    assert NOBRIDGE in u["no_bridge_after"] and OUTLET in u["no_bridge_after"], u["no_bridge_after"]
    assert u["en_no_bridge"] is False, u"无桥 ⇒ 其钮禁（⛔ 死路之虚能）"


def test_B7_有桥之诸态逐字():
    u = _v()["u"]
    assert u["bridge_name"] == BRIDGE, u["bridge_name"]
    assert u"打开落点目录" in u["bridge_idle"] and u"data/pa/feedback" in u["bridge_idle"], u["bridge_idle"]
    assert u"正在打开落点目录" in u["bridge_opening"], u["bridge_opening"]
    assert u["en_opening"] is False, u"opening ⇒ 禁（⛔ 连点）"
    assert u["en_bridge"] is True, u"有桥 ∧ ⛔ opening ⇒ 可"
    assert OPENED in u["bridge_ok_same"] and u"data/pa/feedback" in u["bridge_ok_same"], u["bridge_ok_same"]
    assert u"⚠" in u["bridge_ok_diff"], u"壳回之径 ≠ 后端之落点径 ⇒ 须照实警（⛔ 掩）—— " + u["bridge_ok_diff"]
    assert OPENED in u["bridge_ok_nopath"], u["bridge_ok_nopath"]
    assert FAILED in u["bridge_fail"] and u"E_OPEN" in u["bridge_fail"], u["bridge_fail"]
    assert OUTLET in u["bridge_fail"], u"失败须有「去处」（承立规）—— " + u["bridge_fail"]
    assert u"径由壳自算" in u["no_dir_bridge"], u"后端 ⛔ 给径 ⇒ 照实 —— " + u["no_dir_bridge"]


def test_B8_实跑之落():
    u = _v()["u"]
    cb = u["click_no_bridge"]
    assert cb["dir"]["state"] == "fail" and cb["dir"]["code"] == "E_NO_BRIDGE", cb
    assert NOBRIDGE in cb["text"], u"⛔ 静默（无桥之点 ⇒ 明书）—— " + cb["text"]
    now = u["click_bridge_now"]
    assert now["dir"]["state"] == "opening" and now["renders"] >= 1, now
    end = u["click_bridge_end"]
    assert end["dir"]["state"] == "ok" and end["dir"]["path"] == "D:\\clawsjoy_v9\\data/pa/feedback", end
    assert OPENED in end["text"], end["text"]
    fail = u["click_bridge_fail"]
    assert fail["dir"]["state"] == "fail" and fail["dir"]["code"] == "E_OPEN", fail
    assert FAILED in fail["text"] and OUTLET in fail["text"], fail["text"]
