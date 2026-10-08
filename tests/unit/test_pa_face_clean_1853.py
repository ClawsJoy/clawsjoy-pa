# -*- coding: utf-8 -*-
u"""pm_1853 ＋ pm_1855（批 9.0.10）之**面齿** —— 用户面净化之第二批 ＋ 端／面**对拍**。

事由（老板之令 · PM 一手 CDP）：老板「你的验收标准就是用户的角度，用视觉和交互」（pm_1822 §〇）
⇒ PM 走毕全路逮**五件**（机器号上屏 ／ 1440 顶栏工程墙 ／ 会话面头之端名 ／ 回执之工单语 ／
首启盒之文案）＋ 老板复问 `👤 machine-id`（pm_1855）⇒ 本批落屏；另落端已齐之二件
（`sys/act` 之真去处 ／ 附件之本机端）。

判据（静态闸 ＋ 端／面对拍 · 与 PM 之 CDP 计数互补）：
  P1  首屏**静态文** ⛔ 载机器号（pm_1855 §三.1）。
  P2  运行期（node ＋ DOM 桩 · **真函数**）：`paSyncUserChip()` ⇒ `#uidText` ＝ 人话 ∧ 原值入 `title`（反控）。
  P3  正控：`ensureUserId()` 之行为**一字未动**（铸 ／ 存 ／ 取）∧ 已有 id **⛔ 新铸**（pm_1855 §二）。
  P4  对拍：前端二表（系统页 ／ 干净桶）须**逐值 ＝ 后端之白名单**（⛔ 前端自造字面 · pm_1853 §二.2ⓜ）。
  P5  器病之回归：回执之键 ＝ `撤之径`（后端 `sys_act.py`）—— 前端若书他字 ⇒ 撤之径**永 ⛔ 现**。
  P6  附件（pm_1853 §二.2ⓝ）：录之键 ＝ `落点`（对拍 `attach.save()` 之真回）∧ 缺省 ⛔ 出机 ∧ 逐件勾。
  P7  首屏 ⛔ 载端名（pm_1853 §一.2／§一.3）：状态行二件**两位皆收** ∧ 会话面头之端名入 `title`（反控）。
  P8  回执尽人话（pm_1853 §一.4）：用户面 ⛔ 载 `wall_s` ／ `bytes` ／ `tokens`；原键入 `title`（反控）。
  P9  首启盒之文案（pm_1853 §一.5）：机器码对译 ∧ `⛔ 假装能用` ⇒ `未验证` ∧ 盘符径 ⛔ 上屏。
  P10 左栏（pm_1853 §一.6）：`1 位`（⛔「1 个客户」）。
  P11 `sys/act` 之守（pm_1847 §一 ／ pm_1853 §二.2ⓜ）：缺省唯预案 ∧ 真跑须一次性 token ∧
      件入回收（⛔ 直删）∧ 幂等 ∧ 陪伴轴恒拒 ∧ 回执 ⛔ 载绝对径。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_face_clean_1853.py -q --basetemp=D:\\clawsjoy_v9\\_tmp\\pt1853
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "web" / "pa.html"
CSS = ROOT / "web" / "pa" / "pa_v3.css"
SESSION = ROOT / "web" / "pa" / "faces" / "session.js"
TODAY = ROOT / "web" / "pa" / "faces" / "today.js"
SELFDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
SYSJS = ROOT / "web" / "pa" / "faces" / "sys.js"
SEND = ROOT / "web" / "pa" / "faces" / "send.js"
PROFILE = ROOT / "web" / "pa" / "faces" / "profile.js"
SYS_FACE = ROOT / "core" / "pa" / "sys_face.py"

from core.pa import attach as _AT          # noqa: E402  —— 对拍之真源（唯 stdlib）
from core.pa import sys_act as _SA         # noqa: E402


def _read(p) -> str:
    return io.open(str(p), encoding="utf-8").read()


_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


def _de(s: str) -> str:
    u"""JS 之转义（反斜杠 ＋ u ＋ 四位十六进）⇒ 真字（面之文有两形：真字 ∧ JS 之转义 —— 断言须对**渲染之文**）。"""
    return _ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), s)


def _read_de(p) -> str:
    return _de(_read(p))


def _stmt(s: str, a: str, b: str) -> str:
    u"""自 `a` 起至 `b` 止（含）—— ⛔ 以缩进猜界（那必漂）。"""
    i = s.index(a)
    k = s.index(b, i)
    return s[i:k + len(b)]


# ============================== P1 ／ P2 ／ P3 · 身份 ==============================
def test_P1_首屏静态文不载机器号():
    u"""pm_1855 §三.1：`#uidText` 之静态初值须为人话 ∧ ⛔ 机器号之**前缀**。"""
    h = _read_de(HTML)
    i = h.index('<span id="uidText"')
    span = h[i:h.index("</span>", i) + len("</span>")]
    assert u"本机" in span, u"`#uidText` 之初值须为人话（「本机」）—— pm_1855 §三.1：" + span
    assert u">-<" not in span, u"⛔ 以 `-` 为初值（旧形）"
    assert "web_" not in span, u"⛔ 以机器号为初值（pm_1855 §三.4⒜）"
    c = h.index('id="uidChip"')
    chip = h[h.rindex("<", 0, c):h.index(">", c) + 1]
    assert u"title=" in chip and u"当前用户" in chip, u"`#uidChip` 须有 title（悬停可取 · pm_1855 §三.2）"
    assert "web_" not in chip, u"⛔ 以机器号入首屏之静态 `title`"


_ID_HARNESS = u"""
const fs=require('fs');
const src=fs.readFileSync(process.argv[2],'utf8');
const seed=process.argv[3]||'';
let store = seed ? {clawsjoy_user_id: seed} : {};
const calls = {set: 0};
global.localStorage = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(store,k) ? store[k] : null; },
  setItem: function(k,v){ calls.set += 1; store[k]=String(v); }
};
global.window = {__APP_STATE:{}};
const nodes = {uidText:{textContent:''}, uidChip:{title:''}};
global.document = {getElementById:function(id){ return nodes[id]||null; }};
eval(src);
try{ paSyncUserChip(); }catch(e){}
process.stdout.write(JSON.stringify({raw: paUserRaw(), disp: paUserDisplay(),
  uidText: nodes.uidText.textContent, title: nodes.uidChip.title,
  store: store.clawsjoy_user_id, sets: calls.set, inState: window.__APP_STATE.userId}));
"""


def _identity_src() -> str:
    u"""取 `session.js` 之身份段（真函数 · ⛔ 以源码字面代行）。"""
    s = _read(SESSION)
    i = s.index(u"/* PM-011")
    j = s.index(u"/* 批122")
    return s[i:j]


def _run_identity(tmp_path, seed):
    node = shutil.which("node")
    if not node:
        pytest.skip(u"node ⛔ 在 ⇒ 身份之真函数 ⛔ 得跑")
    (tmp_path / "id.js").write_text(_identity_src(), encoding="utf-8")
    (tmp_path / "h.js").write_text(_ID_HARNESS, encoding="utf-8")
    r = subprocess.run([node, str(tmp_path / "h.js"), str(tmp_path / "id.js"), seed],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    return json.loads(r.stdout)


def test_P2_人话在外原值入悬停(tmp_path):
    u"""pm_1855 §三.1／§三.2：显示名 ＝ 人话 ∧ 真身份唯入 `title`（⛔ 丢真源）。"""
    seed = u"web_1790773805388"
    o = _run_identity(tmp_path, seed)
    assert o["disp"] == u"本机", u"显示名须为「本机」（机器号 ⛔ 上屏）"
    assert o["uidText"] == u"本机", u"`#uidText` 须写人话：%r" % (o["uidText"],)
    assert seed in o["title"], u"反控：原身份须仍可**悬停**取得：%r" % (o["title"],)
    assert u"本机身份" in o["title"], u"`title` 须明书其为本机身份"


def test_P3_ensureUserId_一字未动(tmp_path):
    u"""pm_1855 §二／§三.4⒞（正控）：铸 ／ 取 ／ 存 之行为**一字未动** ∧ 有 id ⇒ ⛔ 新铸。

    事由：该 id 是本机线程之归属键（`data/v9/pa/threads_web_*.json`）∧ 有意之**安全设**
      （⛔ 静默回落 default ／ 他人 —— `session.js` 之 PM-011 · N9）。本批唯易其**显**。
    """
    o = _run_identity(tmp_path, u"web_1790773805388")
    assert o["raw"] == u"web_1790773805388" and o["sets"] == 0, \
        u"已有 id ⇒ 须原样取用（⛔ 新铸 ／ ⛔ 覆写）：%r" % (o,)
    assert o["inState"] == u"web_1790773805388", u"内存与落盘须同源（⛔ 分叉）"
    o2 = _run_identity(tmp_path, u"")
    assert re.match(r"^web_\d+$", o2["raw"]), u"无 id ⇒ 须铸一（形制 `web_<ms>`）：%r" % (o2["raw"],)
    assert o2["sets"] == 1 and o2["store"] == o2["raw"], u"铸出之 id 须落盘（同值）：%r" % (o2,)
    assert o2["uidText"] == u"本机", u"新铸之境，屏上仍唯人话"
    s = _read(SESSION)
    for k in (u"function ensureUserId(){", u"localStorage.getItem('clawsjoy_user_id')",
              u"localStorage.setItem('clawsjoy_user_id'", u"window.__APP_STATE.userId = _uid;"):
        assert k in s, k + u" —— `ensureUserId()` 须一字未动（pm_1855 §二）"
    assert u"function paUserRaw(){ return ensureUserId(); }" in s, u"真身份唯由一处取（⛔ 二写）"
    for f in (PROFILE, SELFDESC):
        assert u"paSyncUserChip()" in _read(f), \
            u"显示名须由**一处**（`paSyncUserChip`）写：%s" % (f.name,)


# ============================== P4 ／ P5 · 端／面对拍 ==============================
def test_P4_二表逐值对拍后端白名单():
    u"""pm_1853 §二.2ⓜ：前端之「可跑」二源须**逐值 ＝ 后端白名单**（⛔ 传字面 · ⛔ 各造一份）。"""
    js = _read(SYSJS)
    page = dict(re.findall(r"'([^']+)':\s*'([^']+)'",
                           _stmt(js, u"var PA_SYS_ACT_PAGE = {", u"};")))
    assert set(page) == set(_SA.SETTINGS_TARGETS.values()), u"系统页之字面 ⛔ 符后端：%r" % (page,)
    assert set(page.values()) == set(_SA.SETTINGS_TARGETS), u"系统页之端键 ⛔ 符后端"
    bucket = dict(re.findall(r"'([^']+)':\s*'([^']+)'",
                             _stmt(js, u"var PA_SYS_ACT_BUCKET = {", u"};")))
    names = set(n for n, _s, _l, _k in _SA.CLEAN_BUCKETS)
    labels = set(l for _n, _s, l, _k in _SA.CLEAN_BUCKETS)
    assert set(bucket) == labels, u"桶之「人话」⛔ 符后端 CLEAN_BUCKETS：%r" % (bucket,)
    assert set(bucket.values()) == names, u"桶之端名 ⛔ 符后端：%r" % (bucket,)
    # 快照（sys_face）须以**同一人话**为桶之标签 —— 否则前端之对表必空（器病）
    face = _read(SYS_FACE)
    for lab in labels:
        assert lab in face, u"快照（`sys_face.py`）须以同一「人话」为桶之标签：" + lab
    assert u"PA_SYS_ACT_BUCKET[String((it && it['人话']) || '')]" in js, \
        u"桶之判须以快照之「人话」为键（⛔ 另立判据）"


def test_P5_回执之键_撤之径():
    u"""器病之回归（本批一手所逮）：后端之键 ＝ `撤之径`（`sys_act.py:301`）——
    前端若书「撑之径」⇒ 回执之**撤之径永 ⛔ 现**（用户失去可撤之路 ⇒ 比不显示更坏）。"""
    a = _read(ROOT / "core" / "pa" / "sys_act.py")
    assert u'"撤之径"' in a, u"后端之键（真源）"
    js = _read_de(SYSJS)
    assert u"r['撤之径']" in js, u"前端须读**后端之键**（⛔ 各造一字）"
    assert u"撑之径" not in js, u"⛔ 书他字（键 ⛔ 符 ⇒ 其值恒 ⛔ 现）"
    assert u"要撤回" in js, u"须给出**去向**（人话）"


# ============================== P6 · 附件 ==============================
def test_P6_附件之本机端与逐件勾():
    u"""pm_1853 §二.2ⓝ：取件复用**原生** `<input type=file multiple>` ∧ 唯本机 ∧ 缺省 ⛔ 出机。"""
    h = _read_de(HTML)
    assert u'<input type="file" id="paAttachFiles" multiple' in h, u"取件须复用原生选件器（⛔ 桥）"
    assert u'id="paAttachBtn"' in h and u"📎 附件" in h, u"须有可见之入口"
    s = _read_de(SEND)
    assert u"var PA_ATTACH_URL = '/v9/pa/attach';" in s, u"须走本机端（一处定形）"
    assert u"fd.append('files'" in s, u"字面须为 `files`（后端 `request.files.getlist('files')`）"
    assert u"out: false" in s, u"**缺省 ⛔ 出机**（pm_1847 §三.2⒜）"
    assert u"return r.out === true && r.kind === '文';" in s, u"唯**逐件勾 ∧ 类为「文」**者入体"
    assert u"此件内容将随本轮出机" in s and u"只给本机指路" in s, u"须**明书**两种境（⛔ 静默出机）"
    assert u"_b.attachments = _ids; _b.attach_out = paAttachOutIds();" in s, \
        u"聊天体须携 `attachments`（全部）＋ `attach_out`（已勾）"
    assert u"a['落点']" in s, u"录之键须 ＝ 后端之 `落点`"
    assert u"a['点']" not in s, u"⛔ 用错键（后端为「落点」）—— 已一手核"


def test_P6b_附件录之键对拍真回(tmp_path):
    u"""对拍：以 `attach.save()` 之**真回**验前端所读之键（⛔ 以我以为之契约代真）。"""
    out = _AT.save(str(tmp_path / "pa"), [(u"a.txt", b"hello"), (u"b.png", b"\x89PNG")],
                   now=1759900000.0)
    assert out["ok"] is True and out[u"唯本机"] is True, out
    assert len(out[u"附件"]) == 2, out
    row = out[u"附件"][0]
    assert set(row) == {u"id", u"名", u"字节", u"sha16", u"类", u"落点"}, row
    assert row[u"类"] == _AT.KIND_TEXT == u"文", row
    assert out[u"附件"][1][u"类"] == _AT.KIND_IMAGE, out
    assert u"落点" in out, u"回之顶键"
    md = _read_de(SEND)
    assert u"String(a['名']" in md and u"a['字节']" in md and u"a['sha16']" in md and u"a['类']" in md, \
        u"前端所读之诸键须与真回同"


# ============================== P7 ／ P8 · 首屏净化 ==============================
def test_P7_状态行两宽皆收且会话头端名入悬停():
    u"""pm_1853 §一.2／§一.3：1440 反比 1024 吵 ⇒ 二件**两位皆收**；会话面头之端名 ⇒ `title`。"""
    c = _read(CSS)
    assert u"pm_1853 §一.2" in c, u"须留其由（可核）"
    media = c.index(u"@media (max-width:1180px){ .statusline .runstate-src{display:none} }")
    for sel in (u"\n.statusline .uis{display:none}\n", u"\n.statusline .runstate-src{display:none}\n"):
        assert sel in c, u"须有**无条件**之收（⛔ 唯窄宽之内）：" + sel.strip()
        assert c.index(sel) > media, u"其收须在窄宽块**之外**（⛔ 只得半个人看到）"
    t = _read_de(TODAY)
    seg = _stmt(t, u"paV3Txt('paChatHistSrc'", u"条'));")
    assert u"GET /api/v5/session/list" not in seg, u"端名 ⛔ 得入用户面（pm_1853 §一.3）"
    assert u"_hs.title = '源：GET /api/v5/session/list'" in t, u"反控：端名仍须可达（悬停）"
    y = _read_de(SYSJS)
    assert u"paSysFoldReadingsHtml" in y and u"runStateSrc" in y and u"paUiStateRow" in y, \
        u"被收之原字须有**去处**（体检面 · ⛔ 丢信息）"


def test_P8_回执尽人话而原键入悬停():
    u"""pm_1853 §一.4：用户面 ⛔ 载后端之键名（`wall_s` ／ `bytes` ／ `tokens`）∧ ⛔ 工单号（`pm_xxxx §x`）。"""
    s = _read_de(SELFDESC)
    for k in (u"wall_s:'用时(s)'", u"bytes:'数据(字节)'", u"tokens:'词元'", u"cost_cny:'费用(元)'"):
        assert k in s, u"须有「码 ⇒ 人话」之对译（一处定形）：" + k
    cost = _stmt(s, u"function costText(){", u"\n  }")
    assert u"未取得（本轮后端尚未回用时之数）" in cost, u"缺 ⇒ 须书**实**（⛔ 只书「未取得」）"
    for bad in (u"wall_s", u"bytes", u"tokens", u"pm_1115"):
        assert bad not in cost, bad + u" ⛔ 得入用户面（pm_1853 §一.4）"
    assert u"function costRaw()" in s and u"'｜后端用时之原键：'" in s, \
        u"反控：原键须仍可得（入 title · ⛔ 丢真源）"
    rc = _stmt(s, u"function rcLines(){", u"'· 谁批的：' + whoText(),")
    assert u"未取得（本轮未做本机检索 ⇒ 无此据）" in rc, u"缺据须书**因**（⛔ 只书「未取得」）"
    assert u"⛔ 前端不编" not in rc, u"我辈之约 ⛔ 得入用户面（是**我们**之语 · ⛔ 用户之语）"
    assert u"本轮回执" in s, u"回执之头须在（人话）"
    assert u"（人话版" not in s, u"头行 ⛔ 得自称「（人话版 ）」（吾辈之语 · ⛔ 用户之语）"
    assert u"承 pm_1115 §二.5" not in s, u"工单号 ⛔ 得入用户面"


def test_P9_首启盒之文案():
    u"""pm_1853 §一.5 ＋ pm_2022 §二 ／ pm_2025 §二.3⒜（首屏工程墙之撤）：机器码 ⇒ 人话 ∧
    「⛔ 假装能用」⇒「未验证」∧ 本机开发径 ⛔ 上屏 ∧ 首屏字面 ⛔ 载「工程注记」四字。
    ⚠ 首启卡之**字与位**（真函数 · node 桩 · 真渲之字）⇒ 另齿 test_pa_first_run_2022.py。"""
    h = _read_de(HTML)
    assert u"var PA_STATE_WORD={'未接':'没接上'," in h, u"机器码须对译（一处定形）"
    assert u"'在∧可用':'可用'" in h, u"「在∧可用」⇒ 人话（旧形之拼接错）"
    assert u"t=t.split('⛔ 假装能用').join('未验证');" in h, u"⛔ 读成「这是假的」⇒ 须书「未验证」"
    face = _stmt(h, u"function face(s){", u"return t;")
    assert u"[A-Za-z]" in face and u"t.replace(" in face, u"盘符径须于 face() 一处分（⛔ 各点各判）"
    assert u"（点开「来源 ／ 详情」即见其径）" in face, u"其去处（人话 · 折名 · pm_2022 §二.⒞）"
    assert u"face(need[" in h and u"['话']" in h, u"须知须经 face()（一处对译 · ⛔ 各处各判）"
    box = h[h.index(u"function box(d){"):]
    assert u"esc(dir['值']" not in box and u"+dir['值']" not in box, u"⛔ 直渲数据目录之值（＝本机开发径 · pm_1853 §一.5）"
    assert u"_elin(eng,'• 数据目录：'+String(dir['值']||'（未接）')" in box, u"反控：原值仍须有去处（⛔ 丢信息）"
    assert u"PA_SELFDOUBT_WORD" in box, u"自我怀疑之辞须有面闸（⛔ 上屏）"
    assert u"来源 ／ 详情" in box, u"折名须人话（pm_2022 §二.⒞：「工程注记」⛔ 入首屏字面）"


def test_P10_左栏一位():
    u"""pm_1853 §一.6：私人 PA ——「客户」二字不类。"""
    h = _read_de(HTML)
    assert u"本机画像 · 1 位" in h, u"用户面须为「1 位」"
    assert u"1 个客户" not in h, u"⛔ 以「客户」称本机主人（pm_1853 §一.6）"


# ============================== P11 · sys/act 之守（对拍真端） ==============================
def _fake_bucket(tmp_path):
    u"""临时之桶 —— ⚠ 真动之件**唯临时试件**（PM 之界）。"""
    d = tmp_path / u"装位" / "diag"
    d.mkdir(parents=True, exist_ok=True)
    for n in ("a.txt", "b.txt"):
        (d / n).write_bytes(b"x" * 10)
    return {u"装位/diag": {u"path": str(d), u"人话": u"诊断包", u"须留最近一份": False,
                          u"须管理员": False, u"去哪看": u"装位 → diag"}}


def test_P11a_缺省唯预案不动一物(tmp_path, monkeypatch):
    u"""pm_1847 §一.2⒜：`dry_run` 之缺省须**唯回预案**（缺参 ⇒ ⛔ 危险）。"""
    monkeypatch.setattr(_SA, "buckets", lambda: _fake_bucket(tmp_path))
    _SA.reset_tokens()
    r = _SA.act(act="clean", target=u"装位/diag", data_dir=str(tmp_path))
    assert r["ok"] is True and r.get("dry_run") is True, r
    assert r["ttl_s"] == _SA.TOKEN_TTL_S == 120 and r["token"] and r["印"], r
    p = r[u"预案"]
    for k in (u"人话", u"件数", u"逐条", u"合计人话", u"险级", u"须管理员", u"去哪看"):
        assert k in p, u"预案须载「数 ／ 源 ／ 去处」诸键：" + k
    assert p[u"件数"] == 2 and len(p[u"逐条"]) == 2, p
    assert (tmp_path / u"装位" / "diag" / "a.txt").exists(), u"预案 ⛔ 得动一物"
    assert not (tmp_path / u"装位" / "diag" / u"_trash").exists(), u"⛔ 直删"


def test_P11b_真跑须一次性token且件入回收(tmp_path, monkeypatch):
    u"""pm_1847 §一.2：真跑须**逐次** token（TTL 120 s）∧ 件入 `_trash`（**⛔ 直删**）∧ 回执示**撤之径**。"""
    monkeypatch.setattr(_SA, "buckets", lambda: _fake_bucket(tmp_path))
    _SA.reset_tokens()
    bad = _SA.act(act="clean", target=u"装位/diag", dry_run=False, data_dir=str(tmp_path))
    assert bad["ok"] is False and bad["code"] == 403, bad
    r0 = _SA.act(act="clean", target=u"装位/diag", data_dir=str(tmp_path))
    r = _SA.act(act="clean", target=u"装位/diag", dry_run=False, token=r0["token"], data_dir=str(tmp_path))
    assert r["ok"] is True, r
    assert r[u"回执"][u"果"] == u"成", r[u"回执"]
    assert r[u"撤之径"] and u"_trash" in r[u"撤之径"], u"回执须示**撤之径**：%r" % (r.get(u"撤之径"),)
    assert r[u"字节"] == 20, r
    assert not (tmp_path / u"装位" / "diag" / "a.txt").exists(), u"件须**入回收**（⛔ 直删）"
    assert (tmp_path / u"装位" / "diag" / u"_trash").is_dir(), u"须有回收处"
    assert u"C:\\" not in json.dumps(r, ensure_ascii=False), u"回执 ⛔ 载本机之绝对径"
    assert (tmp_path / "sys_act.jsonl").is_file(), u"须落审计（⛔ 静默）"


def test_P11c_幂等与陪伴轴(tmp_path, monkeypatch):
    u"""pm_1847 §一.2⒠：幂等（同 token 二跑 ⇒ 回首次之回执 · ⛔ 二动）∧ ⒢ 陪伴轴**恒拒**。"""
    monkeypatch.setattr(_SA, "buckets", lambda: _fake_bucket(tmp_path))
    _SA.reset_tokens()
    r0 = _SA.act(act="clean", target=u"装位/diag", data_dir=str(tmp_path))
    r1 = _SA.act(act="clean", target=u"装位/diag", dry_run=False, token=r0["token"], data_dir=str(tmp_path))
    r2 = _SA.act(act="clean", target=u"装位/diag", dry_run=False, token=r0["token"], data_dir=str(tmp_path))
    assert r1[u"幂等"] is False and r2[u"幂等"] is True, (r1.get(u"幂等"), r2.get(u"幂等"))
    assert r2[u"回执"] == r1[u"回执"], u"幂等 ⇒ 回**首次**之回执"
    ch = _SA.act(act="clean", target=u"装位/diag", axis="chat", data_dir=str(tmp_path))
    assert ch["ok"] is False and ch["code"] == 403, u"陪伴轴 ⛔ 触发动作（聊天 ＝ 只商量）"
    js = _read(SYSJS)
    assert u"paChatMode() === 'companion') ? 'chat' : 'sys'" in js, \
        u"前端须把陪伴轴之态送上（端亦拒 —— 双闸）"
    assert u"st.confirm = true" in js and u"paSysActGo" in js, u"红钮须**二次确认**"
    assert u"dry_run: true" in js and u"dry_run: false" in js, u"取预案之调用须明书 `dry_run: true`"
