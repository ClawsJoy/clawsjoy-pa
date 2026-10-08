# -*- coding: utf-8 -*-
u"""pm_1635 五令 ＋ pm_1641 §二 之齿（CW b2a5182 · 2026-10-07）—— 留言板（丙-P0 之面 · 内测形）。

一事：`web/pa/faces/feedback.js`（纯函数 · 唯写 `#paFeedback`）＋ 页之骨 ＋ 面册之条。
  ⒜ 常驻明书唯取后端 `notice` ∧ 勾选唯取后端 `consent_buses` ∧ 默认全关 ∧ ⛔「在线客服」四字；
  ⒝ 读一处（`/health` 之 `feedback` 键）· 动分端（`/v9/pa/feedback`）—— 承 pm_1641 裁 ①；
  ⒞ 三面（起服 ／ 更新 ／ 反馈）⇒ **一幅横幅**（`paPrepMerge` 之末判 · 最低优先级 · ⛔ 三横幅）。

  F1  正控：`/health.feedback` 有 notice ⇒ 常驻明书 ＝ 本机之**逐字**（不自撰）；
      ⭐ pm_2061 §二.2：原字仍逐字（⇒ `title`）、屏上惟净形（`⛔` ⇒ 「不」＋剔饰四符）。
  F2  反控：无 `feedback` 键 ⇒ 明书「后端未给落点之声明」∧ **停发**。
  F3  反控：有 `feedback` 而 `notice` 空 ／ 白 ⇒ 明书「⛔ 自撰 ⇒ 停发」∧ **停发**。
  F4  正控：勾选逐项 ＝ 后端 `consent_buses` ∧ **默认全关**（⛔ 造项 ／ ⛔ 一个「全选」之便键）。
  F5  反控：`outbound=true` ⇒ 未勾「同意」即停发 ∧ 勾之则可发（③ 同意之口 其位先留）。
  F6  正控：题 ／ 文 缺 ⇒ 停发（**照后端 `feedback_store.submit` 之判**：题必填 ∧ 文必填）。
  F7  正控：发之三态 ⇒ 发送中 ／ 已成（落点之径 ＋ 后端 `hint`）／ 已败（因 ＋ 去处）。
  F8  正控：我之收件之痕 ⇒ 条数 ＋ 最近之刻 ＋ 落点之径（判据 ⛔ 造）。
  F9  正控：回话（黄框）⇒ 唯取后端 `reply`；无 ／ 空 ⇒ 空（⛔ 自造辞）。
  F10 结构齿：剔注后 ⛔「在线客服」∧ ⛔ `localStorage` ／ `sessionStorage` ∧ ⛔ `XMLHttpRequest`
      ／ `sendBeacon` ／ `WebSocket` ／ `EventSource`（出站之径皆无 · 唯 `fetch` 至本机）。
  F11 结构齿：取数唯 `'/health'`（⛔ 引 `/v9/pa/feedback/target`）∧ 所引 `/v9/pa/*` 唯本端二形。
  F12 结构齿（一处显 · ⛔ 三横幅）：本面 ⛔ 自渲横幅（⛔ `paPrepRender`）∧ 唯经 `paPrepFeedFeedback(`
      投入（唯 1 处）∧ `paPrepMerge` 唯 1 处 ∧ 反馈之判在更新之判**之后**（＝ 最低优先级）。
  F13 正控（横幅之最低优先级）：ready ＋ 反馈 ⇒ 反馈；starting ＋ 反馈 ⇒ starting（⛔ 凌于起服）；
      更新「失败」＋ 反馈 ⇒ 更新（⛔ 凌于更新）。
  F14 页之骨 ＋ 面册：`pa.html` 有 `#paFeedback` ∧ feedback.js 所读之**凡 id 皆在页** ∧ 载脚本 ∧
      「一步可达」之入口在顶栏（`#paFbBtn` → `paFbOpen()`）∧ `faces.json` 有本面之条（file ／ dom）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_feedback_1635.py -q
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
SU = ROOT / "web" / "pa" / "faces" / "startup.js"
HTML = ROOT / "web" / "pa.html"
MAN = ROOT / "web" / "pa" / "faces.json"
SCRATCH = ROOT / "data" / "tmp" / "_cw_fb1635"

NOTICE = u"内测版：留言只存在你这台机器上（⛔ 出机 · ⛔ 联网发送）"
CS = u"\u5ba2\u670d\u5e2d"            # 客服席


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


def _strip_js(t: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    s = re.sub(r"(?m)^[ \t]*//[^\n]*$", "", s)
    s = re.sub(r"(?m)(?<![:/])//[^\n]*$", "", s)
    return s


def _harness() -> str:
    s, su = _read(FB), _read(SU)
    parts = [
        _decl(s, u"const PA_FB_READ"), _decl(s, u"const PA_FB_SEND"), _decl(s, u"const PA_FB_LIST"),
        _decl(s, u"const PA_FB_ITEM"), _decl(s, u"const PA_FB_POLL_MS"), _decl(s, u"const PA_FB_OUTLET"),
        _decl(s, u"const PA_FB_BANNER_TTL_MS"), _decl(s, u"const PA_FB_BANNER_FAIL_MS"),
        _block(s, u"const PA_FB_BUS = {", u"};"),
        _fn(s, u"paFbBusLabel"), _fn(s, u"paFbTarget"),
        _fn(s, u"paFbHumanLine"), _fn(s, u"paFbNoticeText"), _fn(s, u"paFbNoticeRaw"),
        _fn(s, u"paFbGate"), _fn(s, u"paFbBusTags"), _fn(s, u"paFbItemsText"),
        _fn(s, u"paFbReplyText"), _fn(s, u"paFbSendText"), _fn(s, u"paFbBannerView"),
        _fn(s, u"paFbFeedBanner"),
        _decl(su, u"const PA_UPD_BUSY"), _fn(su, u"paPrepMerge"),
        u"let __fed = null;",
        u"function paPrepFeedFeedback(v){ __fed = v; }",
        u"const paFbRun = {send: null, t: null, bannerT: null, agreed: false};",
    ]
    cases = u"""
const N = "内测版：留言只存在你这台机器上（⛔ 出机 · ⛔ 联网发送）";
const T_OK = {state:"ok", notice:N, outbound:false, mode:"local", channel:"internal",
              dir:"data/pa/feedback", resolved_dir:"D:/clawsjoy_v9/data/pa/feedback",
              consent_buses:["health","logs","env","diag"], note:""};
const T_OUT = {state:"ok", notice:N, outbound:true, mode:"relay", channel:"beta",
               dir:"data/pa/feedback", resolved_dir:"D:/clawsjoy_v9/data/pa/feedback",
               consent_buses:["health","logs","env","diag"], note:""};
const H_OK = {status:"healthy", version:"9.0.0", feedback:T_OK};
const H_OUT = {status:"healthy", version:"9.0.0", feedback:T_OUT};
const H_NOFB = {status:"healthy", version:"9.0.0"};
const H_BLANK = {status:"healthy", feedback:{mode:"local", outbound:false, dir:"data/pa/feedback",
                 consent_buses:["health","logs"], notice:"   "}};
const H_NOB = {status:"healthy", feedback:{mode:"local", outbound:false, dir:"data/pa/feedback", notice:"x"}};
const out = {t:{}, nt:{}, g:{}, b:{}, s:{}, i:{}, r:{}, bv:{}, bb:{}, m:{}};
out.t.ok = paFbTarget(H_OK); out.t.noans = paFbTarget(H_NOFB);
out.t.blank = paFbTarget(H_BLANK); out.t.nob = paFbTarget(H_NOB); out.t.out = paFbTarget(H_OUT);
out.nt.ok = paFbNoticeText(out.t.ok); out.nt.ok_raw = paFbNoticeRaw(out.t.ok);
out.nt.noans = paFbNoticeText(out.t.noans);
out.nt.blank = paFbNoticeText(out.t.blank);
out.nt.marks = paFbHumanLine("**a** \u00b7 `b` \u00b7 ~~c~~");
out.nt.cross = paFbHumanLine("\u26d4 出机 \u00b7 \u26d4 联网发送");
out.g.ok = paFbGate(out.t.ok, false, false, {title:"t", body:"b"});
out.g.noans = paFbGate(out.t.noans, false, false, {title:"t", body:"b"});
out.g.blank = paFbGate(out.t.blank, false, false, {title:"t", body:"b"});
out.g.notitle = paFbGate(out.t.ok, false, false, {title:"   ", body:"b"});
out.g.nobody = paFbGate(out.t.ok, false, false, {title:"t", body:""});
out.g.out_off = paFbGate(out.t.out, false, false, {title:"t", body:"b"});
out.g.out_on = paFbGate(out.t.out, true, false, {title:"t", body:"b"});
out.g.sending = paFbGate(out.t.ok, false, true, {title:"t", body:"b"});
out.b.def = paFbBusTags(out.t.ok, {});
out.b.one = paFbBusTags(out.t.ok, {logs:true});
out.b.nob = paFbBusTags(out.t.nob, {});
out.s.sending = paFbSendText({state:"sending"}, out.t.ok);
out.s.ok = paFbSendText({state:"ok", id:"fb_x1", at:"2026-10-07T13:00:00+0800",
                         hint:"已存本机；内测期不联网发送"}, out.t.ok);
out.s.fail = paFbSendText({state:"fail", error:"请填「题目」"}, out.t.ok);
out.i.zero = paFbItemsText([], out.t.ok);
out.i.two = paFbItemsText([{id:"a", at:"2026-10-07T13:00:00+0800"}, {id:"b"}], out.t.ok);
out.r.has = paFbReplyText({reply:{by:"客服席", at:"2026-10-07T14:00:00+0800", text:"已收到，正在看"}});
out.r.none = paFbReplyText({reply:null});
out.r.empty = paFbReplyText({reply:{text:"   "}});
out.bv.sending = paFbBannerView({state:"sending"}, out.t.ok);
out.bv.ok = paFbBannerView({state:"ok", id:"fb_x1"}, out.t.ok);
out.bv.fail = paFbBannerView({state:"fail", error:"boom"}, out.t.ok);
out.bv.none = paFbBannerView(null, out.t.ok);
paFbRun.send = {state:"sending"}; paFbRun.t = out.t.ok;
out.bb.v = paFbFeedBanner(); out.bb.seen = __fed;
const READY = {state:"ready"}, START = {state:"starting"}, UPD_FAIL = {state:"failed"};
const FB_DONE = {state:"done", text:"留言已落本机：x"};
out.m.ready_fb = paPrepMerge(READY, null, FB_DONE);
out.m.ready_none = paPrepMerge(READY, null, null);
out.m.start_fb = paPrepMerge(START, null, FB_DONE);
out.m.updfail_fb = paPrepMerge(START, UPD_FAIL, FB_DONE);
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
    return _node(_harness(), "fb1635")


# ---------- F1 ～ F3：常驻明书（唯后端之辞 · ⛔ 自撰） ----------

def test_F1_明书唯取后端notice之逐字():
    u"""守原意（pm_1635 §二.2）不变：常驻明书 ＝ 取端之 `notice`（不自行编辞）。

    ⭐ pm_2061 §二.2（裁⒉ · 平文唯人话）之后：**原字仍逐字**（⇒ `title` · 可查 · 不丢），
    屏上之形唯净（剔饰四符 ＋ 我方内部记号 `⛔` ⇒ 「不」）。
    """
    v = _v()
    assert v["t"]["ok"]["state"] == "ok", v["t"]["ok"]
    assert v["nt"]["ok_raw"] == NOTICE, u"原字（真源 · 供 `title`）须逐字：" + v["nt"]["ok_raw"]
    assert u"⛔" not in v["nt"]["ok"], u"屏上之形不得载我方内部记号：" + v["nt"]["ok"]
    assert v["nt"]["ok"] == u"内测版：留言只存在你这台机器上（不出机 · 不联网发送）", v["nt"]["ok"]
    assert v["nt"]["marks"] == u"a · b · c", v["nt"]["marks"]
    assert v["nt"]["cross"] == u"不出机 · 不联网发送", v["nt"]["cross"]
    assert v["g"]["ok"]["ok"] is True, v["g"]["ok"]


def test_F2_无feedback键须明书且停发():
    v = _v()
    assert v["t"]["noans"]["state"] == "unanswered", v["t"]["noans"]
    assert u"本机还没给落点之声明" in v["nt"]["noans"], v["nt"]["noans"]
    assert v["g"]["noans"]["ok"] is False, v["g"]["noans"]


def test_F3_notice空须明书且停发():
    v = _v()
    assert v["t"]["blank"]["state"] == "ok" and v["t"]["blank"]["notice"] == "", v["t"]["blank"]
    assert u"不自行编辞" in v["nt"]["blank"] and u"停发" in v["nt"]["blank"], v["nt"]["blank"]
    assert v["g"]["blank"]["ok"] is False and u"明书" in v["g"]["blank"]["why"], v["g"]["blank"]


# ---------- F4 ～ F6：勾选 ／ 同意之口 ／ 形之判 ----------

def test_F4_勾选唯取后端之项且默认全关():
    v = _v()
    d = v["b"]["def"]
    assert [x["bus"] for x in d] == ["health", "logs", "env", "diag"], d
    assert all(x["on"] is False for x in d), u"默认须全关（红线四条）"
    assert all(u"（此项将随件）" in x["label"] for x in d), d
    one = v["b"]["one"]
    assert [x["on"] for x in one] == [False, True, False, False], one
    assert v["b"]["nob"] == [], u"后端 ⛔ 给项 ⇒ 空表（⛔ 前端造项）"


def test_F5_outbound真须同意之口():
    v = _v()
    assert v["g"]["out_off"]["ok"] is False, v["g"]["out_off"]
    assert u"同意出机" in v["g"]["out_off"]["why"], v["g"]["out_off"]
    assert v["g"]["out_on"]["ok"] is True, v["g"]["out_on"]
    assert v["g"]["sending"]["ok"] is False, u"发送中 ⛔ 二发"


def test_F6_题文缺须停发且照后端之判():
    v = _v()
    assert v["g"]["notitle"]["ok"] is False and u"题必填" in v["g"]["notitle"]["why"], v["g"]["notitle"]
    assert v["g"]["nobody"]["ok"] is False and u"说明必填" in v["g"]["nobody"]["why"], v["g"]["nobody"]


# ---------- F7 ～ F9：发之三态 ／ 收件之痕 ／ 回话 ----------

def test_F7_发之三态():
    v = _v()
    assert v["s"]["sending"] == u"发送中…", v["s"]["sending"]
    ok = v["s"]["ok"]
    assert u"D:/" not in ok, u"落点之绝对径 ⛔ 上屏（pm_2061 §二.2 之界）：" + ok
    assert u"fb_x1" in ok, ok
    assert u"已存本机；内测期不联网发送" in ok, ok
    fail = v["s"]["fail"]
    assert u"请填「题目」" in fail and u"去处" in fail, fail


def test_F8_我之收件之痕():
    v = _v()
    assert u"我之收件：0 条" in v["i"]["zero"], v["i"]["zero"]
    assert u"点「打开落点目录」可见其径" in v["i"]["zero"], v["i"]["zero"]
    assert u"D:/" not in v["i"]["zero"], u"落点之绝对径 ⛔ 上屏"
    two = v["i"]["two"]
    assert u"我之收件：2 条" in two and u"最近 2026-10-07T13:00:00+0800" in two, two


def test_F9_回话唯取后端reply():
    v = _v()
    assert CS in v["r"]["has"] and u"已收到，正在看" in v["r"]["has"], v["r"]["has"]
    assert v["r"]["none"] == "", u"无 reply ⇒ 黄框 ⛔ 显（⛔ 自造辞）"
    assert v["r"]["empty"] == "", u"reply 空 ⇒ ⛔ 显"


# ---------- F10 ～ F12：结构齿 ----------

def test_F10_剔注后无站外与出站之径():
    s = _strip_js(_read(FB))
    assert u"在线客服" not in s, u"内测期 ⛔ 书「在线客服」（承 pm_1635 §二.2 ⒞）"
    for bad in ("localStorage", "sessionStorage", "XMLHttpRequest", "sendBeacon",
                "WebSocket", "EventSource"):
        assert bad not in s, u"⛔ 出站 ／ 假态之径：" + bad
    assert u"fetch(" in s, u"唯 `fetch`（至本机之端）"


def test_F11_取数唯health且所引之端唯本端():
    s = _strip_js(_read(FB))
    assert u"'/health'" in s, u"读数之端唯 `/health`（承 pm_1641 裁 ①）"
    assert u"feedback/target" not in s, u"⛔ 引机器 ／ 运维之端（`/v9/pa/feedback/target`）"
    q = "'" + chr(34) + "`"
    lits = sorted(set(re.findall("[" + q + "](/v9/pa/[A-Za-z0-9_/]*)", s)))
    assert lits == ["/v9/pa/feedback", "/v9/pa/feedback/"], lits
    assert u"cache: 'no-store'" in s, u"取数须绕缓存（F5 之反：⛔ 前端缓存之假态）"


def test_F12_一幅横幅_本面不自渲且投入唯1处():
    s = _strip_js(_read(FB))
    assert u"paPrepRender" not in s, u"本面 ⛔ 自渲横幅（其渲唯 startup.js 一处）"
    assert s.count(u"paPrepFeedFeedback(") == 1, u"投于横幅须唯 1 处（一处定形）"
    su = _read(SU)
    assert su.count(u"function paPrepMerge(") == 1, u"三源合一之判须唯 1 处"
    body = _fn(su, u"paPrepMerge")
    assert body.index(u"if(u.state === 'done') return u;") < body.index(u"const f = (c &&"), \
        u"反馈之判须在更新之判之后（＝ 最低优先级）"
    assert u"a.state === 'ready'" in body, u"反馈唯占「起服已就绪」之本应收之横幅"
    assert u"paPrepMerge(v, paPrepUpd, paPrepFb, paPrepShu)" in _fn(su, u"paPrepPaint"), \
        u"四源须同投一处之判"


# ---------- F13：横幅之最低优先级（⛔ 三横幅） ----------

def test_F13_反馈之位为最低():
    v = _v()["m"]
    assert v["ready_fb"]["state"] == "done", v["ready_fb"]
    assert v["ready_none"]["state"] == "ready", v["ready_none"]
    assert v["start_fb"]["state"] == "starting", u"⛔ 反馈凌于起服之「准备中」"
    assert v["updfail_fb"]["state"] == "failed", u"⛔ 反馈凌于更新之「失败」"


# ---------- F14：页之骨 ＋ 面册 ----------

def test_F14_页之骨与面册与一步可达():
    h, s = _read(HTML), _read(FB)
    assert u'id="paFeedback"' in h, u"面之骨须静态在页（⛔ 白屏）"
    ids = sorted(set(re.findall(r"paFbEl\('([A-Za-z0-9_]+)'\)", s)))
    assert ids, u"器取须得 id 之集（⛔ 空）"
    for i in ids:
        assert (u'id="' + i + u'"') in h, u"feedback.js 所读之 id 不在页：" + i
    assert u'<script src="pa/faces/feedback.js"></script>' in h, u"未载 feedback.js"
    assert u"在线客服" not in re.sub(r"<!--.*?-->", "", h, flags=re.S), u"页之骨内 ⛔ 书四字"
    assert u'id="paFbBtn"' in h and u"paFbOpen()" in h, u"「一步可达」之入口须在顶栏"
    man = json.loads(_read(MAN))
    fb = [f for f in man["faces"] if f.get("id") == "feedback"]
    assert len(fb) == 1, u"面册须有本面之条（唯 1）"
    assert fb[0]["file"] == "faces/feedback.js", fb[0]
    # pm_1657 §二.2：壳之桥之页内侧（开「落点目录」）⇒ 其钮 ＋ 其态行亦归本面之 dom（⛔ 则关面时 ⛔ 收起）。
    assert fb[0]["dom"] == ["#paFeedback", "#paFbOpenDir", "#paFbDirState"], fb[0]
    assert fb[0].get("open") is True, fb[0]
