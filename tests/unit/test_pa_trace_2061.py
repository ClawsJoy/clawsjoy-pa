# -*- coding: utf-8 -*-
u"""pm_2061 §三 物⒈（真迹上屏）／物⒉（禁辞之显形 · 面侧）之齿（CW b2a5182 · 2026-10-08）。

一事：`web/pa/faces/chat.js`（语义表 ＋ 三步纯函）＋ `web/pa/faces/send.js`（二处接线）。

物⒈（真迹上屏 · pm_2061 §三.1）
  T1 本机族之口 ⇒ 人话名（`pa_read` ／ `note_kb` ／ `file_center`）∧ ⛔ 载裸工具名；
     **反控**：白名单外之工具 ⇒ 落兜底「执行操作」（三级兜底 ⛔ 动 · 钉 send.js）。
  T2 工具步之摘要 **唯取端之 `tool_steps[].result`**（端 ⛔ 给 ⇒ 空 ∧ 屏 ⛔ 载本机之径 ／ 件名）。
  T3 工具步之可否退 **唯照实**：只读之族 ⇒ 「未动你的件」；写类 ⛔ 许「可撤」之妄诺。
物⒉（禁辞之显形 · 面侧 · pm_2061 §三.1）
  T4 回执载 `channel.untrue_wording` ⇒ 一处人话块（命中词在 ∧ 键名唯入 `title`）；
     端 ⛔ 给 ／ 空表 ／ ⛔ 数组 ⇒ 一字 ⛔ 现（⛔ 自造辞）。
  T5 接线（源级 · ⛔ 丢）：`paUntrueWordingRender(d)` 在 `sendPA` 内 · `paStepSummary(s.result)` 谐调。
物⒊（轴之路由 · pm_2061 §三.1）
  T6 判据之牙（反控）：错态 ／ 错通道 ／ 错路 ／ 缺路 ⇒ **必咬**（防「以文案之别充路由之别」∧「永远绿」）。
  T7 环境之守：`5102` ⛔ 在 ∨ ⛔ chrome ／ ⛔ node ⇒ **skip**（⛔ 红）∧ ⛔ 触网。
  T8 真渲之路由（真 Chrome × CDP）：真点 `#paModeBar` 之二钮 ⇒ 断 `state.mode` ／ `MODES[].chan`
     ／ `paChatMode()` ／ **真发之 URL**（`fetch` 包装记 URL ∧ 拦之返伪 `Response` ⇒ ⛔ 出网）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_trace_2061.py -q
"""
from __future__ import annotations

import io
import json
import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHAT = ROOT / "web" / "pa" / "faces" / "chat.js"
SEND = ROOT / "web" / "pa" / "faces" / "send.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_trace2061"


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


def _block(src: str, head: str, stop: str) -> str:
    i = src.find(head)
    assert i >= 0, u"未找到块头 " + head
    j = src.find(stop, i)
    assert j > 0, u"未找到块末 " + stop
    return src[i:j + len(stop)]


def _parts() -> list:
    s = _read(CHAT)
    return [
        _block(s, u"const ACTION_SEMANTIC={", u"};"),
        _decl(s, u"const PA_STEP_SUM_MAX"),
        _block(s, u"const PA_STEP_RO_TOOLS = [", u"];"),
        _fn(s, u"paStepReadOnly"), _fn(s, u"paStepUndoText"), _fn(s, u"paStepSummary"),
        _fn(s, u"paUntrueWordingView"),
    ]


CASE = u"""
var out = {};
out.sem = {pa_read: ACTION_SEMANTIC['pa_read'], note_kb: ACTION_SEMANTIC['note_kb'],
           file_center: ACTION_SEMANTIC['file_center'], pa_audit: ACTION_SEMANTIC['pa_audit']};
out.fb = {known: (ACTION_SEMANTIC['read_file'] || '执行操作'),
          unknown: (ACTION_SEMANTIC['no_such_tool_xyz'] || '执行操作')};
out.sum = {none: paStepSummary(null), blank: paStepSummary('   '),
           plain: paStepSummary('取回三条结果'),
           pathy: paStepSummary('D:\\clawsjoy_v9\\data\\v9\\pa\\sessions\\session_pa_x.jsonl 已读'),
           long:  paStepSummary('一二三四五六七八九十一二三四五六七八九十一二三四五六七八九十'),
           head:  paStepSummary('第一行内容' + String.fromCharCode(10) + '第二行内容')};
out.undo = {ro: paStepUndoText('read_file'), wr: paStepUndoText('write_file'),
            ex: paStepUndoText('execute_command'), nk: paStepUndoText('note_kb')};
out.uw = {has: paUntrueWordingView({channel:{untrue_wording:['已受理']}}),
          two: paUntrueWordingView({channel:{untrue_wording:['已受理','已转办']}}),
          empty: paUntrueWordingView({channel:{untrue_wording:[]}}),
          nokey: paUntrueWordingView({channel:{kind:'dialog'}}),
          noreceipt: paUntrueWordingView({}),
          bogus: paUntrueWordingView({channel:{untrue_wording:'已受理'}})};
console.log(JSON.stringify(out));
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


V = None


def _v() -> dict:
    global V
    if V is None:
        V = _node("\n".join(_parts()) + "\n" + CASE, "trace2061")
    return V


# ---------- 物⒈ · 真迹上屏 ----------

def test_T1_本机族之人话名与兜底():
    u"""pm_2061 §三.1⒜：本机族之口 ⇒ 人话名 ∧ ⛔ 载裸工具名；反控：白名单外 ⇒ 兜底「执行操作」。"""
    v = _v()
    for k in ("pa_read", "note_kb", "file_center", "pa_audit"):
        h = v["sem"][k]
        assert h and isinstance(h, str), (k, h)
        assert u"_" not in h, u"人话名 ⛔ 载下划线（裸工具名之感）：%r" % h
        assert k not in h, u"人话名 ⛔ 载其裸工具名：%r" % h
    assert v["fb"]["known"] == u"读取文件", v["fb"]
    assert v["fb"]["unknown"] == u"执行操作", u"反控：白名单外 ⇒ 兜底（⛔ 裸名上屏）：%r" % v["fb"]


def test_T2_摘要唯取端之result():
    u"""pm_2061 §三.1⒝：端 ⛔ 给回 ⇒ 摘要段 ⛔ 现（⛔ 造辞）；端给 ⇒ 剔本机之径 ／ 件名 ∧ 唯首行。"""
    v = _v()
    assert v["sum"]["none"] == "" and v["sum"]["blank"] == "", v["sum"]
    assert u"取回" in v["sum"]["plain"], v["sum"]["plain"]
    p = v["sum"]["pathy"]
    assert p, u"端给回 ⇒ 摘要须现（⛔ 丢）：%r" % p
    assert u"D:" not in p and u"\\" not in p, u"屏上 ⛔ 载本机之径：%r" % p
    assert u".jsonl" not in p, u"屏上 ⛔ 载件名：%r" % p
    assert len(v["sum"]["long"]) <= 21, u"摘要须截（≤ 20 ＋ 尾）：%r" % v["sum"]["long"]
    assert v["sum"]["long"].endswith(u"…"), v["sum"]["long"]
    assert u"第一行内容" in v["sum"]["head"] and u"第二行内容" not in v["sum"]["head"], v["sum"]["head"]


def test_T3_可否退唯照实():
    u"""pm_2061 §三.1⒞：只读之族 ⇒ 「未动你的件」；写类 **⛔ 许「可撤」之妄诺**（只可书「动过」）。"""
    v = _v()
    u0 = v["undo"]
    assert u"未动你的件" in u0["ro"], u0
    for k in ("wr", "ex", "nk"):
        assert u"未动你的件" not in u0[k], (k, u0[k])
        assert u"可撤" not in u0[k], u"写类之步 ⛔ 许「可撤」之妄诺：%r" % u0[k]


# ---------- 物⒉ · 禁辞之显形（面侧） ----------

def test_T4_不实之辞标之人话块():
    u"""pm_2061 §三.1 物⒉（面侧）：载该键 ⇒ 一处人话块（命中词在 ∧ 键名唯入 `title`）；
    端 ⛔ 给 ／ 空表 ／ ⛔ 数组 ⇒ 一字 ⛔ 现（⛔ 自造辞）。"""
    v = _v()
    w = v["uw"]
    assert w["has"]["show"] is True, w["has"]
    assert u"已受理" in w["has"]["text"], w["has"]
    assert u"untrue_wording" not in w["has"]["text"], u"键名唯入 title（⛔ 上屏）：%r" % w["has"]["text"]
    assert u"channel.untrue_wording" in w["has"]["eng"], w["has"]
    assert u"已受理" in w["two"]["text"] and u"已转办" in w["two"]["text"], w["two"]
    for k in ("empty", "nokey", "noreceipt", "bogus"):
        assert w[k]["show"] is False and w[k]["text"] == "", (k, w[k])


def test_T5_接线不丢():
    u"""pm_2061 §三.1：二处接线须在（`sendPA` 之渲 ＋ 工具步之摘要 ／ 可否退）—— ⛔ 丢真源。"""
    s = _read(SEND)
    assert s.count(u"paUntrueWordingRender(d)") == 1, u"陪伴轴之渲唯 1 处"
    assert u"paStepSummary(s.result)" in s, u"摘要须**唯取端之 result**"
    assert u"paStepUndoText(s.tool)" in s, u"可否退须由工具名定"
    assert u"端之回（逐字" in s, u"端之逐字回须有去处（title · ⛔ 丢真源）"
    assert u"ACTION_SEMANTIC[s.tool]||'执行操作'" in s, u"三级兜底 ⛔ 动（pm_2061 §三.1）"
    c = _read(CHAT)
    assert u"ACTION_SEMANTIC[s.tool]" not in c, u"兜底仍在 send.js（⛔ 二份）"



# ------------------------- 物⒊ · 轴之路由（真渲之齿） -------------------------

GATEWAY = int(os.environ.get("PA_GATEWAY_PORT", "5102"))
#: 二态之期望（一处定形 · 与 `core.js` 之 `MODES` ／ `selfdesc.js` 之 `VAL` 同源）
ROUTE = {
    "companion": {"state": "chat", "chan": "pa", "chat": "companion",
                  "url": u"/v9/pa/dialog", "nurl": u"/v9/agent/chat"},
    "work":      {"state": "work", "chan": "agent", "chat": "work",
                  "url": u"/v9/agent/chat", "nurl": u"/v9/pa/dialog"},
}


def _health_ok(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=3) as r:
            return int(getattr(r, "status", 0) or 0) == 200
    except Exception:
        return False


def _free_port():
    sk = socket.socket()
    sk.bind(("127.0.0.1", 0))
    p = sk.getsockname()[1]
    sk.close()
    return p


def _reap():
    spec = importlib.util.spec_from_file_location(
        "cw_chrome_reap_2061", str(ROOT / "tests" / "unit" / "cw_chrome_reap.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _env_reason(R):
    u"""环境之守：三者 ⛔ 备 ⇒ skip 之由（⛔ 红 ∧ ⛔ 触网）。"""
    if not R.chrome_exe():
        return u"chrome.exe ⛔ 在"
    if not shutil.which("node"):
        return u"node ⛔ 在"
    if not _health_ok(GATEWAY):
        return u"活端（%d）⛔ 应" % GATEWAY
    return ""


def _route_verdict(case, want):
    u"""纯判（⛔ 触真机 ⇒ 供反控喂假扫）：一举之果 ⇒ 违者之列。"""
    bad = []
    if case.get("state_mode") != want["state"]:
        bad.append((u"状态 ⛔ 符（`state.mode`）", want["state"], case.get("state_mode")))
    if case.get("chan") != want["chan"]:
        bad.append((u"通道 ⛔ 符（`MODES[].chan`）", want["chan"], case.get("chan")))
    if case.get("chat") != want["chat"]:
        bad.append((u"`paChatMode()` ⛔ 符", want["chat"], case.get("chat")))
    urls = case.get("urls") or []
    hit = [x for x in urls if want["url"] in x]
    wrong = [x for x in urls if want["nurl"] in x]
    if not hit:
        bad.append((u"真发之径 ⛔ 现", want["url"], urls))
    if wrong:
        bad.append((u"真发之径落错路", want["nurl"], wrong))
    return bad


def _axis_verdict(case, want):
    u"""钮之文案之判（⛔ 以文案充路由 · 唯作旁证）：二钮须在 ∧ 该态之钮为按态。"""
    bad = []
    if case.get("paired") != ["paModeBtnCompanion", "paModeBtnWork"]:
        bad.append((u"轴栏二钮 ⛔ 齐", "paModeBtnCompanion/paModeBtnWork", case.get("paired")))
    return bad


def test_T6_路由判据有牙():
    u"""T6 反控：错态 ／ 错通道 ／ 错路 ／ 缺路 ⇒ 必咬（防「以文案之别充路由之别」∧「永远绿」）。"""
    ok = {"state_mode": "chat", "chan": "pa", "chat": "companion",
          "urls": [u"http://127.0.0.1:5102/v9/pa/dialog"]}
    assert _route_verdict(ok, ROUTE["companion"]) == [], u"正形须 ⛔ 咬"
    assert _route_verdict(ok, ROUTE["work"]), u"错态 ⇒ 必咬（⛔ 以文案之别充之）"
    assert _route_verdict(dict(ok, state_mode="work"), ROUTE["companion"]), u"状态 ⛔ 符 ⇒ 必咬"
    assert _route_verdict(dict(ok, chan="agent"), ROUTE["companion"]), u"通道 ⛔ 符 ⇒ 必咬"
    assert _route_verdict(dict(ok, chat="work"), ROUTE["companion"]), u"`paChatMode()` ⛔ 符 ⇒ 必咬"
    assert _route_verdict(dict(ok, urls=[]), ROUTE["companion"]), u"真发之径 ⛔ 现 ⇒ 必咬"
    assert _route_verdict(dict(ok, urls=[u"http://127.0.0.1:5102/v9/agent/chat"]),
                          ROUTE["companion"]), u"落错路 ⇒ 必咬"
    assert _axis_verdict({"paired": ["paModeBtnCompanion"]}, ROUTE["companion"]), u"轴栏二钮 ⛔ 齐 ⇒ 必咬"


def test_T7_env_guard_has_grounds(monkeypatch):
    u"""T7：探活败 ／ ⛔ chrome ／ ⛔ node ⇒ 必判不就绪（T8 走 skip 而非误红）；三者备 ⇒ 无因。"""
    R = _reap()
    mod = sys.modules[__name__]
    monkeypatch.setattr(mod, "_health_ok", lambda p: False)
    monkeypatch.setattr(R, "chrome_exe", lambda: r"C:\x\chrome.exe")
    monkeypatch.setattr(mod.shutil, "which", lambda n: r"C:\x\node.exe")
    assert _env_reason(R) != "", u"探活败 ⇒ 必判不就绪"
    monkeypatch.setattr(mod, "_health_ok", lambda p: True)
    assert _env_reason(R) == "", u"三者皆备 ⇒ 无因（⇒ T8 真跑）"
    monkeypatch.setattr(R, "chrome_exe", lambda: None)
    assert _env_reason(R) != "", u"⛔ chrome ⇒ 必判不就绪"
    monkeypatch.setattr(R, "chrome_exe", lambda: r"C:\x\chrome.exe")
    monkeypatch.setattr(mod.shutil, "which", lambda n: None)
    assert _env_reason(R) != "", u"⛔ node ⇒ 必判不就绪"


def test_T8_真渲之路由():
    u"""T8 真 Chrome × CDP：真点轴栏二钮 ＋ 真打一发 ⇒ 断 `state.mode` ／ `MODES[].chan` ／
    `paChatMode()` ／ **真发之 URL**（CDP `Fetch` 域在网络层取 `request.url` ⇒ ⛔ 靠页内包装器）。

    ⭐ 何以取网络层：页内 `window.fetch` 有**三处**包装（`more.js` 探针 ／ `selfdesc.js` 之 `wrapFetch`
      ／ `chat.js` 之渲）⇒ 页内替换**未必在最外**（我一手：真渲中 `window.fetch.__cwMine` 为 `false`
      ⇒ 页内拦截**不可靠**）。CDP `Fetch.requestPaused` 在**网络层**取 URL ⇒ 与页内包装无关。
    守：`/v9/pa/dialog` ／ `/v9/agent/chat` ⇒ **拦之 · 回桩体**（⛔ 触真模型 · ⛔ 落真库）；
      余 `/v9/*` ⇒ 照走（承「⛔ 改行为」）。
    环境不就绪 ⇒ **skip**（⛔ 红）；真跑毕 ⇒ 必收（`cw_chrome_reap`）∧ 入账 ∧ 落图。
    """
    R = _reap()
    reason = _env_reason(R)
    if reason:
        pytest.skip(u"环境不就绪：" + reason)
    cdp_port = _free_port()
    js = (_MJS.replace("ACK_LIT", "`" + _ACK + "`")
             .replace("FACE_LIT", "`" + _FACE + "`")
             .replace("CASE_LIT", "`" + _CASE + "`")
             .replace("WATCH_LIT", "`" + _WATCH + "`")
             .replace("READ_LIT", "`" + _READ + "`"))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / "route2061_scan.mjs"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    env = dict(os.environ)
    env["CW_CDP_PORT"] = str(cdp_port)
    env["CW_PAGE_URL"] = "http://127.0.0.1:%d/web/pa.html" % GATEWAY
    env["CW_OUT"] = str(SCRATCH)
    with R.run_headless(port=cdp_port, tag="cw2061", wait_s=15.0,
                        why=u"pm_2061 物⒊ 轴之路由（真渲之齿 · 网络层取径）"):
        r = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=300)
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, (r.stderr or "")[-1500:])
    res = json.loads(r.stdout.strip().splitlines()[-1])
    assert res.get("intercept") == "on", u"网络层之拦 ⛔ 成：%r" % res.get("intercept")
    assert int(res.get("paused") or 0) > 0, u"拦而未得任一请求（取法之病？）：%r" % res.get("paused")
    for mode in ("companion", "work"):
        one = res["cases"].get(mode)
        assert one and one.get("sent") == 1, u"第 %s 态 ⛔ 发：" % mode + repr(one)
        bad = _route_verdict(one, ROUTE[mode])
        assert bad == [], u"第 %s 态（轴之路由）见命中 %s" % (mode, bad[:6])
        assert _axis_verdict(one, ROUTE[mode]) == [], u"第 %s 态（轴栏）见命中 %s" % (
            mode, _axis_verdict(one, ROUTE[mode])[:4])
    # 停手卡（承 `selfdesc.js` 之 `stopAsk`）：办事轴 ⇒ **必挡一下**（ⓔ 直发）；
    # 陪伴轴 ⇒ **ⓔ 得现**（陪伴 ⓔ 出手 ⇒ 无需授权卡）。
    assert res["cases"]["work"].get("card") is True, u"办事轴 ⓔ 现停手卡（ⓔ 直发执行通道）"
    assert res["cases"]["companion"].get("card") is False, u"陪伴轴 ⓔ 得现停手卡（陪伴 ⓔ 出手）"
    shot = res.get("shot")
    assert shot and os.path.isfile(shot), u"图须落盘（跑毕必收 ∧ 入账）：%r" % shot


_MJS = r"""
import fs from 'node:fs';
const PORT = Number(process.env.CW_CDP_PORT || 0);
const PAGE = process.env.CW_PAGE_URL;
const OUT = process.env.CW_OUT || '';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const CANNED = JSON.stringify({reply:'（联调之桩 · 未触真模型）', status:'busy',
                               reason:'联调之桩', hint:'桩'});
/* ⭐ 拟计划之请求亦拦：真端 `/v9/pa/plan` 一手之读 **≈ 32 s**（源 `template`）⇒ 放它走
   ⇒ 本齿必超时（我一手之证：三轮不稳）。本齿所判者 ＝ **路由**（办事 ⇒ 走哪条端）
   ⇒ 拟其回（`steps` 空 ⇒ 页落默认五步）不动所判之据。 */
const CANNED_PLAN = JSON.stringify({ok:true, steps:[]});
class CDP {
  constructor(ws){ this.ws = ws; this.id = 0; this.pend = new Map(); this.ev = []; this.handlers = {};
    ws.addEventListener('message', (e) => { const m = JSON.parse(e.data);
      if(m.id && this.pend.has(m.id)){ const p = this.pend.get(m.id); this.pend.delete(m.id);
        if(m.error){ p.rej(new Error(JSON.stringify(m.error))); } else { p.res(m.result); } }
      else if(m.method){ this.ev.push(m);
        const h = this.handlers[m.method]; if(h){ try{ h(m.params); }catch(err){} } } }); }
  on(method, cb){ this.handlers[method] = cb; }
  send(method, params = {}, sessionId){ const id = ++this.id; const msg = {id, method, params};
    if(sessionId){ msg.sessionId = sessionId; }
    return new Promise((res, rej) => { this.pend.set(id, {res, rej}); this.ws.send(JSON.stringify(msg)); }); }
  async waitEvent(method, ms = 20000){ const t0 = Date.now();
    while(Date.now() - t0 < ms){ const i = this.ev.findIndex((e) => e.method === method);
      if(i >= 0){ return this.ev.splice(i, 1)[0]; } await sleep(60); }
    return null; }
}
const ACK = ACK_LIT, FACE = FACE_LIT, CASE = CASE_LIT, READ = READ_LIT, WATCH = WATCH_LIT;
const raw = async (cdp, S, expr) => (await cdp.send('Runtime.evaluate',
  {expression: expr, returnByValue: true, awaitPromise: false}, S)).result.value;
const jev = async (cdp, S, expr) => JSON.parse(await raw(cdp, S, expr));
const isTalk = (u) => (u.indexOf('/v9/pa/dialog') >= 0) || (u.indexOf('/v9/agent/chat') >= 0);
const main = async () => {
  const ver = await (await fetch('http://127.0.0.1:' + PORT + '/json/version')).json();
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  const cdp = new CDP(ws);
  const tg = await cdp.send('Target.createTarget', {url: 'about:blank'});
  const at = await cdp.send('Target.attachToTarget', {targetId: tg.targetId, flatten: true});
  const S = at.sessionId;
  await cdp.send('Page.enable', {}, S); await cdp.send('Runtime.enable', {}, S);
  const res = {browser: ver.Browser, intercept: null, paused: 0, cases: {}, shot: null};
  let seen = [];
  cdp.on('Fetch.requestPaused', (p) => {
    res.paused += 1;
    const u = String((p.request && p.request.url) || '');
    seen.push(u);
    const fulfill = (body) => cdp.send('Fetch.fulfillRequest', {requestId: p.requestId, responseCode: 200,
      responseHeaders: [{name: 'Content-Type', value: 'application/json; charset=utf-8'}],
      body: Buffer.from(body, 'utf8').toString('base64')}, S).catch(() => {});
    if (isTalk(u)) {
      res.paused_talk = (res.paused_talk || 0) + 1;
      fulfill(CANNED);
    } else if (u.indexOf('/v9/pa/plan') >= 0) {
      res.paused_plan = (res.paused_plan || 0) + 1;
      fulfill(CANNED_PLAN);
    } else {
      cdp.send('Fetch.continueRequest', {requestId: p.requestId}, S).catch(() => {});
    }
  });
  await cdp.send('Emulation.setDeviceMetricsOverride',
                 {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false}, S);
  await cdp.send('Page.navigate', {url: PAGE + '?t=' + Date.now()}, S);
  await cdp.waitEvent('Page.loadEventFired', 25000);
  await sleep(2600);
  await cdp.send('Runtime.evaluate', {expression: ACK, returnByValue: true}, S);
  await sleep(1000);
  await cdp.send('Runtime.evaluate', {expression: FACE, returnByValue: true}, S);
  await sleep(1600);
  const ready = await raw(cdp, S, "String(!!document.getElementById('paModeBar'))");
  if (ready !== 'true') { console.log(JSON.stringify({err: 'no-axis-bar'})); ws.close(); process.exit(0); }
  await cdp.send('Fetch.enable',
                 {patterns: [{urlPattern: '*://*/v9/*', requestStage: 'Request'}]}, S);
  res.intercept = 'on';
  await sleep(300);
  for (const mode of ['companion', 'work']) {
    seen = [];
    await raw(cdp, S, WATCH);
    const c1 = await jev(cdp, S, CASE.replace('MODE_LIT', JSON.stringify(mode)));
    const want = (mode === 'companion') ? '/v9/pa/dialog' : '/v9/agent/chat';
    let one = null;
    for (let i = 0; i < 24; i++) {
      await sleep(500);
      one = await jev(cdp, S, READ);
      const okUrl = seen.some((u) => u.indexOf(want) >= 0);
      const okCard = ((one.card === true) === (mode === 'work'));
      if (okUrl && okCard) { break; }
    }
    await sleep(600);
    one = await jev(cdp, S, READ);
    for (const k of Object.keys(c1)) { one[k] = c1[k]; }
    one.urls = seen.slice(0);
    res.cases[mode] = one;
  }
  await cdp.send('Fetch.disable', {}, S).catch(() => {});
  if (OUT) {
    const shot = await cdp.send('Page.captureScreenshot', {format: 'png'}, S);
    const p = OUT + '/route2061_w1440.png';
    fs.writeFileSync(p, Buffer.from(shot.data, 'base64'));
    res.shot = p;
  }
  console.log(JSON.stringify(res));
  ws.close();
  process.exit(0);
};
main().catch((e) => { console.error('FATAL ' + String((e && e.stack) || e));
  console.log(JSON.stringify({err: String((e && e.message) || e)})); process.exit(3); });
"""

_ACK = r"""
(function(){ var bs = document.querySelectorAll('button');
  for(var i = 0; i < bs.length; i++){
    if(String(bs[i].textContent || '').indexOf('知道了') >= 0){ bs[i].click(); return 1; } }
  return 0; })()
"""

_FACE = r"""
(function(){ try{ setFace(1); return 1; }catch(e){ return 'ERR ' + String(e); } })()
"""

_CASE = r"""
(function(mode){
  var b = document.querySelector('#paModeBar button[data-pa-mode="' + mode + '"]');
  if(!b) return JSON.stringify({mode:mode, err:'no-axis-button'});
  b.click();
  var o = {mode:mode, button:String(b.textContent || '').trim(), button_id:b.id};
  try{ o.state_mode = state.mode; }catch(e){ o.state_mode = null; }
  try{ o.chan = (MODES[state.mode] || {}).chan; }catch(e){ o.chan = null; }
  try{ o.chat = window.paChatMode(); }catch(e){ o.chat = null; }
  var T = ['记一笔就行', '随便聊两句', '今天先歇会儿'];
  var text = null;
  for(var i = 0; i < T.length; i++){
    try{ if(typeof paLooksLikeKnowledgeQuestion !== 'function'
            || !paLooksLikeKnowledgeQuestion(T[i])){ text = T[i]; break; } }catch(e){}
  }
  o.text = text;
  if(!text){ o.err = 'no-plain-text'; return JSON.stringify(o); }
  var inp = document.getElementById('input');
  if(!inp){ o.err = 'no-input'; return JSON.stringify(o); }
  inp.value = text;
  try{ paSend(); o.sent = 1; }catch(e){ o.sent = 'ERR ' + String(e); }
  return JSON.stringify(o);
})(MODE_LIT)
"""

_WATCH = r"""
(function(){
  window.__cwCard = {seen:false, clicked:0};
  try{ clearInterval(window.__cwIv); }catch(e){}
  var t0 = Date.now();
  window.__cwIv = setInterval(function(){
    try{
      var card = document.getElementById('paStopAsk');
      if(card){ window.__cwCard.seen = true; }
      var b = document.getElementById('paStopAskOk');
      if(b && !window.__cwCard.clicked){ b.click(); window.__cwCard.clicked = 1; }
      if(window.__cwCard.clicked || (Date.now() - t0) > 15000){ clearInterval(window.__cwIv); }
    }catch(e){}
  }, 150);
  return 'watch';
})()
"""

_READ = r"""
JSON.stringify({
  card: !!(window.__cwCard && window.__cwCard.seen),
  grant_clicked: (window.__cwCard || {}).clicked || 0,
  state_mode: (function(){try{return state.mode;}catch(e){return null;}})(),
  chan: (function(){try{return (MODES[state.mode] || {}).chan;}catch(e){return null;}})(),
  chat: (function(){try{return window.paChatMode();}catch(e){return null;}})(),
  axis_text: (function(){var e=document.getElementById('paModeBar');
    return e ? String(e.innerText || '').replace(/\s+/g, ' ').trim() : null;})(),
  hint: (function(){var e=document.getElementById('paModeHintText');
    return e ? String(e.textContent || '').trim() : null;})(),
  paired: (function(){var bs=document.querySelectorAll('#paModeBar button[data-pa-mode]');
    var a=[]; for(var i=0;i<bs.length;i++){ a.push(bs[i].id); } return a;})()
})
"""
