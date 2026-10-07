# -*- coding: utf-8 -*-
u"""pm_1652 令一 之齿（CW b2a5182 · 2026-10-07）—— 密钥界面（模型供应商 · 唯落本机 · ⛔ 值入屏）。

一事：`web/pa/faces/keys.js`（纯函数 ＋ 唯写 `#paKeys`）＋ 页之骨 ＋ `boot.js` 之首载步 ＋ 面册之条。
  ⒜ 端（承 TD `50663ef` ／ TD_1639 §一）：领令牌 `GET /v9/pa/providers/key/token`（唯 Cookie · ⛔ 值）；
     落 ／ 清 `POST /v9/pa/providers/key`（`key` 空 ／ `null` ⇒ 清）；读数 `GET /v9/pa/providers`（唯一源）；
  ⒝ 守（pm_1652 §一.2 守四）：唯落本机唯一处 ∧ 界面唯布尔（⛔ 值 · ⛔ 掩码之首尾）∧
     ⛔ 值入屏 ／ 入 `console` ／ 入 `localStorage` ／ 入报错之文 ∧ 令牌唯 Cookie 走。

  K1  正控：三态之人话 ⇒ **唯取后端之布尔**（`key_configured` 胜 `key_state`）∧ 缺 ⇒ 「态未给」（⛔ 猜已配）。
  K2  正控 ＋ 反控：明书唯述「值之处」∧ 其 `env` 名取后端（`key_env`）∧ ⛔ 给名 ⇒ 照实「⛔ 需密钥」。
  K3  正控 ＋ 反控：形之判 —— ⛔ 选供应商 ⇒ 停 ／ `key_env` ⛔ 在 ⇒ 停 ／ 值空 ⇒ 停 ／ 有值 ⇒ 可。
  K4  正控：体之形 ⇒ `{provider, key}`；**清 ⇒ `key: null`**（承后端之判）。
  K5  结构齿（**值之径** · 要）：剔注后凡 `textContent` ／ `innerHTML` 之右值 ⛔ 含 `raw` ／ `.value`
      ∧ 值唯经 `paKeyBody` ⇒ `JSON.stringify`（入端）∧ 发毕 `el.value = ''`（⛔ 留屏 ／ ⛔ 留于 DOM）。
  K6  行为漏扫：以 sentinel 之值遍走「形之判」之诸支 ⇒ 其出 ⛔ 含 sentinel（⛔ 值入屏 ／ 入报错之文）。
  K7  结构齿：剔注后 ⛔ `localStorage` ／ `sessionStorage` ／ `document.cookie` ／ `console.`
      ∧ ⛔ `XMLHttpRequest` ／ `sendBeacon` ／ `WebSocket` ／ `EventSource`（唯 `fetch` 至本机）。
  K8  结构齿：所引 `/v9/pa/*` **唯三形**（providers ／ providers/key ／ providers/key/token）∧
      `credentials: 'same-origin'` ∧ 清 ⇒ `window.confirm(`（二次确认）。
  K9  页之骨 ＋ 面册 ＋ 面册闸：`pa.html` 有 `#paKeys` ∧ `type="password"` ∧ `autocomplete="off"` ∧
      凡 keys.js 所读之 id 皆在页 ∧ 载脚本 ∧ 顶栏入口（`#paKeyBtn` → `paKeyOpen()`）∧ `boot.js` 有首载步 ∧
      `faces.json` 有条 ∧ `_ui_faces_readout()` 之 `keys.requires` ＝ 三形 ∧ **悬 ＝ {}**。
  K10 用户面禁词 ＝ 0（承 pm_1012 §一 ／ §二）：本面凡**用户面之字**（三态 ／ 明书之四支 ／ 形之判之 `why`
      ／ 回执 ／ 失败面 ／ 读数面 ／ `paKeyPaint` 之「读数中」支 ／ 页之静态 `#paKeys`）
      ⇒ `PA_ENG_WORDS`（**逐字取 `selfdesc.js` 之定义**）之命中 ＝ 0；**反控**：旧串（含「承 pm_1652 §一.2 守四」）必命中。
  K11 抽屉之清洗器于本面**恒等**（承 `paEngStrip`）：`paEngStrip(s) === s` 逐字同 ⇒ 屏上之字 ⛔ 变
      ∧ ⛔ 留「（）」残；**反控**：旧串入清洗器 ⇒ 出「（）」（**此即本齿之证病在** · 2026-10-07 真活端所逮）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_keys_1652.py -q
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

KY = ROOT / "web" / "pa" / "faces" / "keys.js"
HTML = ROOT / "web" / "pa.html"
BOOT = ROOT / "web" / "pa" / "boot.js"
MAN = ROOT / "web" / "pa" / "faces.json"
SCRATCH = ROOT / "data" / "tmp" / "_cw_ky1652"

SECRET = u"sk-LEAKCANARY-0000"
ROUTES = [u"/v9/pa/providers", u"/v9/pa/providers/key", u"/v9/pa/providers/key/token"]


def _read(p):
    return io.open(str(p), encoding="utf-8").read()


def _fn(src, name):
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


def _decl(src, prefix):
    for ln in src.split("\n"):
        if ln.startswith(prefix):
            return ln
    raise AssertionError(u"未找到声明 " + prefix)


def _strip_js(t):
    s = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    s = re.sub(r"(?m)^[ \t]*//[^\n]*$", "", s)
    s = re.sub(r"(?m)(?<![:/])//[^\n]*$", "", s)
    return s


PURE = [u"paKeyEsc", u"paKeyStateText", u"paKeyNoticeText", u"paKeyOpts", u"paKeyWritable",
        u"paKeyGate", u"paKeyBody", u"paKeyMsgText", u"paKeyErrFace", u"paKeyReadFace"]


def _harness():
    s = _read(KY)
    parts = [_decl(s, u"const PA_KEY_READ"), _decl(s, u"const PA_KEY_TOKEN"),
             _decl(s, u"const PA_KEY_WRITE"), _decl(s, u"const PA_KEY_SKEW_MS"),
             _decl(s, u"const PA_KEY_OUTLET")]
    parts += [_fn(s, n) for n in PURE]
    cases = u"""
const P      = {id:'remote:deepseek', label:'DeepSeek', key_env:'DEEPSEEK_API_KEY',
                key_state:'missing', key_configured:false};
const P_OK   = {id:'remote:deepseek', label:'DeepSeek', key_env:'DEEPSEEK_API_KEY',
                key_state:'configured', key_configured:true};
const P_NR   = {id:'local:ollama', label:'本机 Ollama', key_env:'',
                key_state:'not_required', key_configured:false};
const SECRET = %(SECRET)s;
const out = {};
out.st = {ok: paKeyStateText('configured', true), missing: paKeyStateText('missing', false),
          nr: paKeyStateText('not_required', false), nr_noflag: paKeyStateText('not_required', null),
          bool_beats_state: paKeyStateText('missing', true), unknown: paKeyStateText('', null),
          state_only_ok: paKeyStateText('configured', null)};
out.nt = {sel: paKeyNoticeText(P), ok: paKeyNoticeText(P_OK), nr: paKeyNoticeText(P_NR),
          none: paKeyNoticeText(null)};
out.opts = paKeyOpts([P, P_NR, {id:''}, null, {id:'x', label:'X'}]);
out.w = {p: paKeyWritable(P), nr: paKeyWritable(P_NR), none: paKeyWritable(null)};
out.g = {nonsel: paKeyGate(null, 'k', false), nr: paKeyGate(P_NR, 'k', false),
         blank: paKeyGate(P, '   ', false), nul: paKeyGate(P, null, false),
         set: paKeyGate(P, 'k', false), clear: paKeyGate(P, '', true),
         clear_blankp: paKeyGate(P_NR, '', true)};
out.b = {set: paKeyBody(P, SECRET, false), clear: paKeyBody(P, SECRET, true),
         nosel: paKeyBody(null, SECRET, false)};
out.m = {set: paKeyMsgText({action:'set', key_state:'configured', key_configured:true,
                            provider:'remote:deepseek', key_env:'DEEPSEEK_API_KEY'}, P),
         clr: paKeyMsgText({action:'cleared', key_state:'missing', key_configured:false}, P)};
out.e = {t403: paKeyErrFace(403, ''), t0: paKeyErrFace(0, ''), t404: paKeyErrFace(404, ''),
         t400: paKeyErrFace(400, ''), t500: paKeyErrFace(500, '')};
out.rf = {down: paKeyReadFace(0, null), no: paKeyReadFace(200, {ok:true}),
          fine: paKeyReadFace(200, {ok:true, providers:[]}),
          badshape: paKeyReadFace(200, {ok:true, providers:'x'}), http: paKeyReadFace(500, {ok:false}),
          ni: paKeyReadFace(501, null)};
/* 漏扫：sentinel 唯入「值之径」（形之判 ＋ 体 ＋ 报错之文）⇒ 其出 ⛔ 含 sentinel */
function J(x){ try{ return JSON.stringify(x); }catch(e){ return 'ERR'; } }
out.leak = {
  gate_set: J(paKeyGate(P, SECRET, false)), gate_blank: J(paKeyGate(P, '   ', false)),
  gate_nr: J(paKeyGate(P_NR, SECRET, false)), gate_nonsel: J(paKeyGate(null, SECRET, false)),
  err400: paKeyErrFace(400, ''), err403: paKeyErrFace(403, ''), err0: paKeyErrFace(0, ''),
  st: paKeyStateText(SECRET, null), body_set_carries: (paKeyBody(P, SECRET, false).key === SECRET)
};
console.log(JSON.stringify(out));
""" % {"SECRET": json.dumps(SECRET)}
    return "\n".join(parts) + cases


def _node(js, tag):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, u"node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def v():
    return _node(_harness(), "ky1652")


# ---------- K1 ～ K2：三态 ＋ 明书 ----------

def test_K1_三态唯取后端之布尔(v):
    assert v["st"]["ok"] == u"已配", v["st"]
    assert v["st"]["missing"] == u"未配", v["st"]
    assert v["st"]["nr"] == u"不需（无密钥项）", v["st"]
    assert v["st"]["bool_beats_state"] == u"已配", u"布尔须胜 state（唯取后端之布尔）"
    assert v["st"]["unknown"] == u"态未给", u"皆缺须「态未给」（⛔ 猜「已配」）"
    assert v["st"]["state_only_ok"] == u"已配", u"唯 state ⇒ 仍可辨"


def test_K2_明书唯述值之处且env名取后端(v):
    assert u"DEEPSEEK_API_KEY" in v["nt"]["sel"], v["nt"]["sel"]
    assert u"唯落本机" in v["nt"]["sel"], v["nt"]["sel"]
    assert u"⛔ 上屏" in v["nt"]["sel"] and u"⛔ 掩码" in v["nt"]["sel"], v["nt"]["sel"]
    assert u"⛔ 需密钥" in v["nt"]["nr"], v["nt"]["nr"]
    assert u"先选供应商" in v["nt"]["none"], v["nt"]["none"]


# ---------- K3 ～ K4：形之判 ＋ 体之形 ----------

def test_K3_形之判(v):
    assert v["g"]["nonsel"]["ok"] is False and u"先选供应商" in v["g"]["nonsel"]["why"], v["g"]["nonsel"]
    assert v["g"]["nr"]["ok"] is False and u"⛔ 需密钥" in v["g"]["nr"]["why"], v["g"]["nr"]
    assert v["g"]["blank"]["ok"] is False and u"⛔ 空" in v["g"]["blank"]["why"], v["g"]["blank"]
    assert v["g"]["nul"]["ok"] is False, u"null ⇒ 与「空」同判（填 ／ 换）"
    assert v["g"]["set"]["ok"] is True and v["g"]["set"]["act"] == "set", v["g"]["set"]
    assert v["g"]["clear"]["ok"] is True and v["g"]["clear"]["act"] == "cleared", v["g"]["clear"]
    assert v["g"]["clear_blankp"]["ok"] is False, u"清 ⇒ 亦须可写之供应商"
    assert v["w"]["p"] is True and v["w"]["nr"] is False and v["w"]["none"] is False, v["w"]
    assert [x["id"] for x in v["opts"]] == ["remote:deepseek", "local:ollama", "x"], v["opts"]
    assert [x["need"] for x in v["opts"]] == [True, False, False], v["opts"]


def test_K4_体之形与清之null(v):
    b = v["b"]["set"]
    assert b["provider"] == "remote:deepseek" and b["key"] == SECRET, b
    assert v["b"]["clear"]["key"] is None, u"清 ⇒ key: null（承后端之判）"
    assert v["b"]["nosel"]["provider"] == "", v["b"]["nosel"]


# ---------- K5 ～ K6：值之径（要） ----------

def test_K5_结构齿_值之径(v):
    body = _fn(_read(KY), "paKeySend")
    assert re.search(r"el\.value\s*=\s*''", body), u"发毕须清框（⛔ 留屏）"
    assert "JSON.stringify(paKeyBody(" in body, u"值唯经 paKeyBody 入体"
    src = _strip_js(_read(KY))
    hits = re.findall(r"\.(?:textContent|innerHTML)\s*=\s*([^;]*);", src)
    assert hits, u"未寻得渲之赋（闸 ⛔ 空跑）"
    for rhs in hits:
        assert "raw" not in rhs, u"渲之右值 ⛔ 含 raw：%s" % rhs
        assert ".value" not in rhs, u"渲之右值 ⛔ 含 .value：%s" % rhs


def test_K6_行为漏扫_sentinel不入屏(v):
    lk = v["leak"]
    for k in ("gate_set", "gate_blank", "gate_nr", "gate_nonsel"):
        assert SECRET not in lk[k], (k, lk[k])
    for k in ("err400", "err403", "err0"):
        assert SECRET not in lk[k], (k, lk[k])
    assert SECRET not in lk["st"], lk["st"]
    assert lk["body_set_carries"] is True, u"正控：体须带值（⛔ 则 ⛔ 能落）"


# ---------- K7 ～ K8：结构齿 ----------

def test_K7_剔注后无存储无console无四出站途(v):
    src = _strip_js(_read(KY))
    for bad in ("localStorage", "sessionStorage", "document.cookie", "console.",
                "XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource"):
        assert bad not in src, u"剔注后仍见 " + bad
    assert "fetch(" in src, u"唯 fetch 至本机"


def test_K8_所引路由唯三形且同源与二次确认(v):
    src = _strip_js(_read(KY))
    got = sorted(set(re.findall(r"['\"](/v9/pa/[A-Za-z0-9_/]*)['\"]", src)))
    assert got == sorted(ROUTES), got
    assert src.count(u"credentials: 'same-origin'") == 2, u"领令牌 ＋ 落 ／ 清 皆须同源带 Cookie"
    assert "window.confirm(" in _fn(_read(KY), "paKeySend"), u"清 ⇒ 二次确认"
    assert u"刷新本页重试" in v["e"]["t403"], v["e"]["t403"]
    assert u"连不上本机后端" in v["e"]["t0"] and u"连不上本机后端" in v["rf"]["down"], (v["e"], v["rf"])
    assert u"⛔ 挂此端" in v["e"]["t404"], v["e"]["t404"]
    assert u"providers[]" in v["rf"]["no"], v["rf"]["no"]
    assert v["rf"]["fine"] == "", u"形正 ⇒ ⛔ 判（⛔ 假红）"
    assert u"⛔ 形" in v["rf"]["http"], v["rf"]["http"]


# ---------- K9：页之骨 ＋ 面册 ＋ 面册闸 ----------

def test_K9_页之骨与面册(v):
    h = _read(HTML)
    assert 'id="paKeys"' in h, u"缺 #paKeys"
    assert 'id="paKeyProv"' in h and 'id="paKeyVal"' in h, u"缺择单 ／ 密钥框"
    assert 'type="password"' in h and 'autocomplete="off"' in h, u"密钥框须 password ＋ ⛔ 自动填"
    assert 'id="paKeySet"' in h and 'id="paKeyClear"' in h, u"缺二动"
    assert u'id="paKeyBtn"' in h and "paKeyOpen()" in h, u"缺顶栏入口（一步可达）"
    assert '<script src="pa/faces/keys.js"></script>' in h, u"缺载脚本"
    assert u"留言 ／ 密钥 ／ 关于" in h, u"③ 设之 summary 须列密钥"
    # 凡 keys.js 所读之 id 皆在页
    ids = set(re.findall(r"paKeyEl\('([A-Za-z0-9_]+)'\)", _read(KY)))
    assert ids, u"未寻得 paKeyEl（闸 ⛔ 空跑）"
    for i in sorted(ids):
        assert ('id="%s"' % i) in h, u"页中缺 id：" + i
    b = _read(BOOT)
    assert "paKeyInit" in b and u'guard("keys"' in b, u"boot.js 缺首载步"
    m = json.load(io.open(str(MAN), encoding="utf-8"))
    ent = [f for f in m["faces"] if f.get("id") == "keys"]
    assert len(ent) == 1, u"faces.json 缺 keys 条（或重）"
    assert ent[0]["file"] == "faces/keys.js" and ent[0]["dom"] == ["#paKeys"], ent[0]
    assert ent[0]["boot"] == ["paKeyInit"], ent[0]


def test_K9b_面册闸_keys之requires与悬(v):
    from core.pa import gateway_routes as G

    ro = G._ui_faces_readout()
    assert ro[u"\u60ac"] == {}, ro[u"\u60ac"]
    row = [f for f in ro["faces"] if f["id"] == "keys"]
    assert len(row) == 1, u"面册读数缺 keys"
    assert sorted(row[0]["requires"]) == sorted(ROUTES), row[0]["requires"]
    assert ro[u"\u9762\u4e4b\u6570"] == len([p for p in (ROOT / "web" / "pa" / "faces").glob("*.js")
                                            if not p.name.startswith(".") and ".before_" not in p.name])


# ---------- K10 ～ K11：用户面禁词 ＝ 0 ／ 清洗器恒等（承 pm_1012 §一／§二）----------

SELF = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
OLD_CITED = (u"所填之密钥唯落本机（后端之 `.env` 之 `DEEPSEEK_API_KEY` 之行）· ⛔ 上屏 ／ ⛔ 掩码 ／ "
             u"⛔ 入日志 ／ ⛔ 出机（承 pm_1652 §一.2 守四）。")


def _decl_block(src, prefix):
    u"""取「自 prefix 之行列起 ⇒ 至首个以 `;` 讫之行」之整块（含 `const PA_ENG_SEG = [` 之多行数组）。"""
    lines = src.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith(prefix):
            if ln.rstrip().endswith(";"):
                return ln
            out = [ln]
            for j in range(i + 1, len(lines)):
                out.append(lines[j])
                if lines[j].rstrip().endswith(";"):
                    return "\n".join(out)
    raise AssertionError(u"未找到块声明 " + prefix)


def _unread_literal():
    for ln in _read(KY).split("\n"):
        if u"读数中" in ln:
            m = re.search(u"'([^']*)'", ln)
            if m:
                return m.group(1)
    raise AssertionError(u"未找到 paKeyPaint 之「读数中」支（闸 ⛔ 空跑）")


def _static_keys_text():
    u"""`#paKeys` 之静态用户面 —— 去注释（其内含源码引）∧ 去标之属（`title` ／ `placeholder` 非 innerText）。"""
    h = _read(HTML)
    i = h.find('id="paKeys"')
    assert i > 0, u"页中缺 #paKeys（闸 ⛔ 空跑）"
    j = h.find("</section>", i)
    assert j > i, u"#paKeys 之 </section> 未寻得"
    seg = re.sub(r"<!--.*?-->", "", h[i:j], flags=re.S)
    seg = re.sub(r"<[^>]*>", " ", seg)
    return re.sub(r"\s+", " ", seg).strip()


def _user_strings(v):
    S = {}
    for k in sorted(v["nt"]):
        S["nt." + k] = v["nt"][k]
    for k in sorted(v["st"]):
        S["st." + k] = v["st"][k]
    for k in sorted(v["g"]):
        S["gate." + k] = v["g"][k]["why"]
    S["msg.set"] = v["m"]["set"]
    S["msg.clr"] = v["m"]["clr"]
    for k in sorted(v["e"]):
        S["err." + k] = v["e"][k]
    for k in sorted(v["rf"]):
        S["read." + k] = v["rf"][k]
    S["paint.unread"] = _unread_literal()
    S["page.static"] = _static_keys_text()
    return S


def _node_eng(strings):
    s = _read(SELF)
    js = ("\n".join([_decl_block(s, u"const PA_ENG_WORDS"), _decl_block(s, u"const PA_ENG_SEG"),
                     _fn(s, "paEngStrip")])
          + u"\nconst S = " + json.dumps(strings, ensure_ascii=False) + u";\n"
          + u"const OLD = " + json.dumps(OLD_CITED, ensure_ascii=False) + u";\n"
          + u"""const out = {hits:{}, ident:{}};
Object.keys(S).forEach(function(k){
  out.hits[k] = PA_ENG_WORDS.test(S[k]);
  out.ident[k] = (paEngStrip(S[k]) === S[k]);
});
out.ctl = {old_hit: PA_ENG_WORDS.test(OLD), old_strip: paEngStrip(OLD)};
console.log(JSON.stringify(out));""")
    return _node(js, "kyeng")


@pytest.fixture(scope="module")
def veng(v):
    return _node_eng(_user_strings(v))


def test_K10_用户面禁词为零(veng):
    bad = sorted(k for k in veng["hits"] if veng["hits"][k])
    assert bad == [], u"用户面禁词命中须 0 ⇒ 见 %s" % (bad,)
    assert veng["ctl"]["old_hit"] is True, u"反控：旧串（含过程引）须命中 ⇒ 证病在"


def test_K11_抽屉清洗器于本面恒等(veng):
    bad = sorted(k for k in veng["ident"] if not veng["ident"][k])
    assert bad == [], u"paEngStrip 须于本面恒等（否则屏上之字会变 ／ 留残）⇒ 见 %s" % (bad,)
    st = veng["ctl"]["old_strip"]
    assert u"（）" in st, u"反控：旧串入清洗器须出「（）」残 ⇒ 证病在 · 得 %r" % st
    assert u"pm_1652" not in st, st
