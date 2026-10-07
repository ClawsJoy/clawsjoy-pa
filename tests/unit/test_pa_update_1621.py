# -*- coding: utf-8 -*-
u"""pm_1621 四条 之齿（CW b2a5182 · 2026-10-07）—— 更新环节之可见之面。

一事：`web/pa/faces/update.js`（纯函数 `paUpdView`）＋ **一幅横幅显二源**（`paPrepMerge` · 一处定形）。
  承 pm_1621：令一（版本可见）／令二（全程可见：检查 ／ 下载 ／ 校验 ／ 备份 ／ 替换 ／ 重启 ／ 完成 ／ 失败）／
  令三（失败 ⇒ 因 ＋ 去处 ＋ 回滚之状 · ⛔ 原始异常入屏）／令四（与 1617 **一处显** · ⛔ 二套面）。

  U1 正控（下载中 · 有字节）⇒ 人话 ＋ 按字节之条 ＋ % ＋ 剩余秒。
  U2 正控（校验中 · 按件）⇒ 人话 ＋ 件数之条 ＋ 已等。
  U3 正控（备份中 · 无 done/total）⇒ 人话 ＋ 已等 ＋ **明书进度不可量**（⛔ 造数）。
  U4 正控（替换中）⇒ 其相之人话（逐态有别）。
  U5 正控（需重启）⇒ 明书 ＋ 去处（自动恢复）。
  U6 正控（完成）⇒ 新版本号 ＋ 去处（F5）。
  U7 正控（失败 ＋ 已回滚）⇒ 因逐字 ＋ 去处 ＋「已回滚至 <版本>」。
  U8 反控（失败而无回滚之标）⇒ 明书「回滚之状未给」（⛔ 冒「已回滚」）。
  U9 反控（失败而 rolled_back=false）⇒ 明书「未回滚」。
  U10 正控（有新版）⇒ 版本号 ＋ 大小之估。
  U11 正控（已是最新）。
  U12 反控（端未答）⇒ 明书「更新面未答」＋「⛔ 不等于已是最新」（⛔ 静默 ∧ ⛔ 充知）。
  U13 反控（缺 `available` 键）⇒ ⛔ 充「已是最新」。
  U14 反控（唯 `last_error` 有原始异常）⇒ ⛔ 入屏 ∧ ⛔ 当失败。
  M1–M5 **一幅横幅**（令四 · ⛔ 二套面）：更新进行中 ／ 更新失败 ／ 更新完成 ⇒ 皆占横幅；
     更新之「有新版 ／ 已是最新 ／ 未答」⇒ **⛔ 占**横幅（令一之版本归顶栏版行）。
  S1 一处定形：`paPrepMerge` 唯 1 处 ∧ 横幅之渲唯 `startup.js` 一处（update.js ⛔ 自渲）。
  S2 版本真源：`update.js` ⛔ 硬编版号字面（真源 ＝ /health.version）。
  S3 版行在页：`pa.html` 有 `#paVerRow` ∧ 载 `update.js`。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_update_1621.py -q
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SU = ROOT / "web" / "pa" / "faces" / "startup.js"
UJ = ROOT / "web" / "pa" / "faces" / "update.js"
HTML = ROOT / "web" / "pa.html"
SCRATCH = ROOT / "data" / "tmp" / "_cw_upd1621"

BUSY = u"\u6b63\u5728\u66f4\u65b0"          # 正在更新
WAIT = u"\u5df2\u7b49"                      # 已等
OUTLET = u"\u53bb\u5904"                    # 去处
NOQTY = u"\u8fdb\u5ea6\u4e0d\u53ef\u91cf"   # 进度不可量
RESTART = u"\u9700\u91cd\u542f"             # 需重启


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


def _harness() -> str:
    s, t = _read(SU), _read(UJ)
    parts = [
        # startup.js（起服之态 ＋ 二源合一之判）
        _decl(s, u"const PA_PREP_POLL_MS"), _decl(s, u"const PA_PREP_TICK_MS"),
        _decl(s, u"const PA_PREP_WATCH_MS"), _decl(s, u"const PA_PREP_MAX_TRIES"),
        _block(s, u"const PA_PREP_PHASE = {", u"};"),
        _decl(s, u"const PA_PREP_NOTE_WAIT"), _decl(s, u"const PA_PREP_OUTLET"),
        _decl(s, u"const PA_PREP_ICON"), _decl(s, u"const PA_UPD_BUSY"),
        _fn(s, u"paPrepNum"), _fn(s, u"paPrepMB"), _fn(s, u"paPrepView"), _fn(s, u"paPrepMerge"),
        # update.js（更新之态 ＋ 版行）
        _decl(t, u"const PA_UPD_SRC"), _decl(t, u"const PA_UPD_POLL_MS"),
        _decl(t, u"const PA_UPD_BUSY_MS"), _block(t, u"const PA_UPD_PHASE = {", u"};"),
        _decl(t, u"const PA_UPD_OUTLET"), _fn(t, u"paUpdView"), _fn(t, u"paUpdCurFromHealth"),
        _fn(t, u"paUpdVerText"),
        u"const paPrepRun = {h: null};",
    ]
    cases = u"""
const UC = [
 ["dl_bar",   {state:"running", phase:"downloading", done_bytes:262144, total_bytes:629145, eta_s:8.2, current:"1.0.0", latest:"1.0.1"}, {elapsed_s:3}],
 ["verify",   {state:"running", phase:"verifying", files_done:3, files_total:12, since_s:5}, {elapsed_s:9}],
 ["backup",   {state:"running", phase:"backing_up", since_s:2}, {elapsed_s:2}],
 ["replace",  {state:"running", phase:"replacing", since_s:1}, {elapsed_s:1}],
 ["restart",  {state:"restart"}, {elapsed_s:1}],
 ["done",     {state:"done", current:"1.0.0", latest:"1.0.1"}, {elapsed_s:1}],
 ["fail_roll",{state:"failed", error:"校验不符（第 3 件 sha256 不合）", rolled_back:true, rollback_to:"1.0.0"}, {elapsed_s:1}],
 ["fail_nor", {state:"failed", error:"下载失败（网络中断）"}, {elapsed_s:1}],
 ["fail_nofb",{state:"failed", error:"下载失败（网络中断）", rolled_back:false}, {elapsed_s:1}],
 ["avail",    {state:"idle", available:true, current:"1.0.0", latest:"1.0.1", total_bytes:629145, files_total:12}, {elapsed_s:1}],
 ["latest",   {state:"idle", available:false, current:"1.0.1"}, {elapsed_s:1}],
 ["noans",    null, {http_status:404, elapsed_s:1}],
 ["noavail",  {state:"idle", current:"1.0.0"}, {elapsed_s:1}],
 ["rawonly",  {state:"idle", available:false, current:"1.0.0", last_error:"Traceback (most recent call last)"}, {elapsed_s:1}],
 ["oddphase", {state:"running", phase:"weird_step", since_s:4}, {elapsed_s:4}]
];
const MC = [
 ["m_running",  {status:"starting", startup:{ready:false, status:"硬件检测"}}, {elapsed_s:5}, {state:"running", phase:"downloading", done_bytes:1, total_bytes:2}],
 ["m_failed",   {status:"healthy",  startup:{ready:true}},                     {elapsed_s:5}, {state:"failed", error:"boom"}],
 ["m_avail",    {status:"starting", startup:{ready:false, status:"硬件检测"}}, {elapsed_s:5}, {state:"available", latest:"1.0.1"}],
 ["m_latest",   {status:"starting", startup:{ready:false, status:"硬件检测"}}, {elapsed_s:5}, {state:"latest"}],
 ["m_noans",    {status:"starting", startup:{ready:false, status:"硬件检测"}}, {elapsed_s:5}, {state:"unanswered"}],
 ["m_done",     {status:"starting", startup:{ready:false, status:"硬件检测"}}, {elapsed_s:5}, {state:"done", latest:"1.0.1"}],
 ["m_ready",    {status:"healthy",  startup:{ready:true}},                     {elapsed_s:5}, {state:"latest"}]
];
const out = {u:{}, m:{}};
for (const c of UC) { out.u[c[0]] = paUpdView(c[1], c[2]); }
for (const c of MC) { out.m[c[0]] = paPrepMerge(paPrepView(c[1], c[2]), paUpdView(c[3], c[2])); }
out.ver = {avail: paUpdVerText(paUpdView({state:"idle", available:true, current:"1.0.0", latest:"1.0.1", total_bytes:629145}, {})),
           latest: paUpdVerText(paUpdView({state:"idle", available:false, current:"1.0.1"}, {})),
           noans: paUpdVerText(paUpdView(null, {http_status:404}))};
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
    return _node(_harness(), "upd1621")


# ---------- U1 ～ U6：全程可见（令二） ----------

def test_U1_下载中须有字节之条与剩余秒():
    v = _v()["u"]["dl_bar"]
    assert v["state"] == "running" and v["can_bar"] is True and v["pct"] == 41, v
    assert BUSY in v["text"] and u"正在下载增量包" in v["text"], v["text"]
    assert u"已下 0.3 MB / 0.6 MB（41%）" in v["text"], v["text"]
    assert u"约还需 8 秒" in v["text"], v["text"]


def test_U2_校验中须有按件之条():
    v = _v()["u"]["verify"]
    assert v["state"] == "running" and v["can_bar"] is True, v
    assert u"正在校验（逐件 sha256）" in v["text"], v["text"]
    assert u"已 3 / 12 件（25%）" in v["text"], v["text"]
    assert (WAIT + u" 5 秒") in v["text"], v["text"]


def test_U3_无字节须明书不可量():
    v = _v()["u"]["backup"]
    assert v["state"] == "running" and v["can_bar"] is False, v
    assert u"正在备份（可回滚）" in v["text"], v["text"]
    assert (WAIT + u" 2 秒") in v["text"] and NOQTY in v["text"], v["text"]


def test_U4_替换须有其相之人话():
    v = _v()["u"]["replace"]
    assert u"正在替换文件" in v["text"], v["text"]


def test_U4b_未知phase须照实():
    v = _v()["u"]["oddphase"]
    assert u"weird_step" in v["text"], v["text"]


def test_U5_需重启须明书与去处():
    v = _v()["u"]["restart"]
    assert v["state"] == "restart", v
    assert RESTART in v["text"], v["text"]
    assert u"自动恢复" in v["note"], v["note"]


def test_U6_完成须显新版本号():
    v = _v()["u"]["done"]
    assert v["state"] == "done", v
    assert u"更新完成：已升至 1.0.1" in v["text"], v["text"]
    assert u"F5" in v["note"], v["note"]


# ---------- U7 ～ U9：失败与回滚（令三） ----------

def test_U7_失败须因与去处与已回滚():
    v = _v()["u"]["fail_roll"]
    assert v["state"] == "failed", v
    assert u"更新失败：校验不符（第 3 件 sha256 不合）" in v["text"], v["text"]
    assert u"已回滚至 1.0.0" in v["note"] and OUTLET in v["note"], v["note"]


def test_U8_无回滚之标须明书不冒():
    v = _v()["u"]["fail_nor"]
    assert v["state"] == "failed", v
    assert u"回滚之状未给" in v["note"], v["note"]
    assert u"已回滚至" not in v["note"], v["note"]


def test_U9_未回滚须明书():
    v = _v()["u"]["fail_nofb"]
    assert u"未回滚" in v["note"], v["note"]


# ---------- U10 ～ U14：版本与「⛔ 充知」（令一） ----------

def test_U10_有新版须显版本与大小():
    v = _v()["u"]["avail"]
    assert v["state"] == "available", v
    assert u"有新版 1.0.1" in v["text"] and u"当前 1.0.0" in v["text"], v["text"]
    assert u"约 0.6 MB" in v["text"] and u"12 件" in v["text"], v["text"]


def test_U11_已是最新():
    v = _v()["u"]["latest"]
    assert v["state"] == "latest" and u"已是最新" in v["text"], v


def test_U12_端未答须明书不充知():
    v = _v()["u"]["noans"]
    assert v["state"] == "unanswered", v
    assert u"更新面未答" in v["text"] and u"HTTP 404" in v["text"], v["text"]
    assert u"不等于「已是最新」" in v["note"], v["note"]


def test_U13_缺available键须不充已最新():
    v = _v()["u"]["noavail"]
    assert v["state"] == "unanswered", v
    assert u"端之回缺" in v["text"], v["text"]
    assert u"available" in v["text"], v["text"]


def test_U14_原始异常须不入屏():
    v = _v()["u"]["rawonly"]
    assert v["state"] == "latest", v
    assert u"Traceback" not in v["text"] and u"Traceback" not in v["note"], v


# ---------- M：一幅横幅（令四） ----------

def test_M1_更新进行中须占横幅():
    v = _v()["m"]["m_running"]
    assert v["state"] == "running" and BUSY in v["text"], v


def test_M2_更新失败须占横幅_凌于起服之就绪():
    v = _v()["m"]["m_failed"]
    assert v["state"] == "failed", v


def test_M3_有新版不占横幅_让位起服之准备中():
    v = _v()["m"]["m_avail"]
    assert v["state"] == "starting", v
    assert u"正在准备" in v["text"], v["text"]


def test_M4_更新未答不占横幅():
    v = _v()["m"]["m_noans"]
    assert v["state"] == "starting", v


def test_M5_更新完成须占横幅():
    v = _v()["m"]["m_done"]
    assert v["state"] == "done", v


def test_M6_就绪且无更新事则收横幅():
    v = _v()["m"]["m_ready"]
    assert v["state"] == "ready", v


def test_ver_版行三态():
    v = _v()["ver"]
    assert u"版本 1.0.0" in v["avail"] and u"有新版 1.0.1" in v["avail"], v
    assert u"版本 1.0.1" in v["latest"] and u"已是最新" in v["latest"], v
    assert u"更新面未答" in v["noans"], v


# ---------- S：结构 ----------

def test_S1_一处定形_横幅之渲唯一处():
    s, t = _read(SU), _read(UJ)
    assert s.count("function paPrepMerge(") == 1, u"二源合一之判须唯 1 处"
    assert s.count("function paPrepRender(") == 1, u"横幅之渲须唯 1 处"
    assert "paPrepRender" not in t, u"update.js ⛔ 自渲横幅（承「⛔ 二套面」）"
    assert t.count("paPrepFeedUpdate(") == 1, u"更新之态须唯经一处投入"


def test_S2_版本真源不硬编():
    t = _read(UJ)
    assert not re.search(r"\d+\.\d+\.\d+", t), u"update.js ⛔ 硬编版号（真源 ＝ /health.version）"
    assert u"paUpdCurFromHealth" in t and u"version" in t, u"版本须取自后端"


def test_S3_版行在页且载脚本():
    h = _read(HTML)
    assert u'id="paVerRow"' in h, u"令一：页面须有版行"
    assert u'<script src="pa/faces/update.js"></script>' in h, u"update.js 未载"


def test_S4_取数唯health_不引未挂之端():
    t = _read(UJ)
    # 剔注（**承面册闸 `_ui_face_requires` 之式**）：注里述其病 ⛔ 算「引用」。
    src = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    src = re.sub(r"(?m)^[ \t]*//[^\n]*$", "", src)
    src = re.sub(r"(?m)(?<![:/])//[^\n]*$", "", src)
    assert u"'/health'" in src, u"更新之态须取既有之 /health（候 TD_1620 之端报）"
    assert u"/v9/pa/" not in src, u"⛔ 引未挂之 /v9/pa/*（面册闸 test_pa_ui_faces 必判「悬」）"
    assert u"cache:'no-store'" in src, u"取数须绕缓存"
