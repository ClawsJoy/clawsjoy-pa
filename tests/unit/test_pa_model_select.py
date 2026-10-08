# -*- coding: utf-8 -*-
u"""pm_1465 §一 ／ §二 之测：**前端模型名 ⛔ 硬编**（选单 ＋ 请求体皆「自后端之表出」）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_model_select.py -q

判据：
  ⒈ 正控（选单）：`web/pa.html` 之 `#cfgModel` ⛔ 硬编 <option>（注册表实名 ／ 别名 ／ 旧辞皆 ⛔ 现）。
  ⒉ 正控（请求体）：`web/pa/**` 之字面 `model:'<注册表名>'` 之数 ＝ 0（皆取 `paModelSel()`）。
  ⒊ 一处定形：`paModelSel` 唯定义于 `config.js`；三调用点 ＝ `sendPA` ／ `sendAgent` ／ `paWriteDecide`。
  ⒋ 说一用一：<option value> ≡ 后端表之行 `id`；且表之 id 集 ≡ `known_models()`（白名单）
     ⇒ 请求之所发 ≡ 选单之所立 ≡ 回执之实名（⛔ 四名流转）。
  ⒌ 本机 ／ 云端须入目：`paModelKindTxt` 之三态（local ⇒ 本机 ／ remote ⇒ 云端 ／ 余 ⇒ 种类未给）。
  ⒍ 三控（⛔ 静默回退）：四态（未应答 ／ ⛔ 200 ／ 键 ⛔ 在 ／ 0 行）皆入**显形** ∧ `paModelRows = null`
     ⇒ `paModelSel()` 返 ""（⇒ 请求体⛔ 带该键 ⇒ 后端落会话档 ∨ 默认 · ⛔ 以旧别名充选）。
  ⒎ 有齿（反控 · 内存改）：回填旧硬编 ／ 去一调用点 ／ 去一显形之清 ⇒ 闸须红。
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import providers as PV  # noqa: E402

WEB = ROOT / "web"
PA = WEB / "pa"
PA_HTML = WEB / "pa.html"
CONFIG_JS = PA / "faces" / "config.js"
SEND_JS = PA / "faces" / "send.js"
CARDS_JS = PA / "faces" / "cards.js"

# 注册表实名 ／ 别名 ／ 旧屏辞（一处出 · ⛔ 手拟第二表）
HARD = (u"deepseek-v4-flash", u"deepseek-flash", u"deepseek-v4-pro",
        u"qwen2.5:7b-instruct-q4_0-gpu", u"本地 7B")
# 「带引号」之字面 ✅ 逮；注内以 `` ` `` 裹之述（如 `deepseek-v4-flash` 旧名）⇒ ⛔ 逮（类「注」⛔ 上屏）
QUOTED_MODEL = re.compile(r"""['"](?:deepseek|qwen2\.5|glm-|anthropic|ollama)""", re.I)


def _pa_sources():
    out = []
    for p in sorted(PA.rglob("*")):
        if p.is_dir() or ".before_" in p.name:
            continue
        if p.suffix in (".js", ".html", ".json", ".css"):
            out.append(p)
    return out


def _lines(p):
    return p.read_text(encoding="utf-8").splitlines()


# ---------- ⒈ 正控（选单） ----------

def test_shell_select_options_are_not_hardcoded():
    s = PA_HTML.read_text(encoding="utf-8")
    for t in HARD:
        assert t not in s, u"web/pa.html 仍含硬编模型名：%s" % t
    m = re.search(r'<select id="cfgModel">(.*?)</select>', s, re.S)
    assert m, u"web/pa.html 未得 #cfgModel"
    opts = re.findall(r"<option[^>]*>", m.group(1))
    assert len(opts) == 1 and 'value=""' in opts[0], (u"静标须唯「载入中…」一格", opts)
    assert u"载入中…" in m.group(1), m.group(1)


# ---------- ⒉ 正控（请求体） ----------

def test_no_hardcoded_model_string_in_product_face():
    hits = []
    for p in _pa_sources():
        for n, l in enumerate(_lines(p), 1):
            if QUOTED_MODEL.search(l):
                # 请求体之显式硬编（⛔ 许）
                if re.search(r"model\s*:\s*['\"]", l):
                    hits.append(u"%s:%d 字面硬编" % (p.relative_to(ROOT), n))
    assert hits == [], u"请求体仍硬编模型名：%s" % hits


# ---------- ⒊ 一处定形 ----------

def test_pa_model_sel_single_definition_three_callers():
    defs = [p for p in _pa_sources() if re.search(r"function\s+paModelSel\s*\(", p.read_text(encoding="utf-8"))]
    assert [p.name for p in defs] == ["config.js"], [p.name for p in defs]
    callers = {}
    for p in _pa_sources():
        c = p.read_text(encoding="utf-8").count("paModelSel();")
        if c:
            callers[p.name] = c
    assert callers == {"send.js": 2, "cards.js": 1}, callers


# ---------- ⒋ 说一用一 ----------

def test_option_value_is_row_id_and_ids_are_whitelist():
    c = CONFIG_JS.read_text(encoding="utf-8")
    assert u"""const o = m || {}, id = String(o.id || '');""" in c
    assert re.search(r"""return '<option value="'\s*\+\s*paEsc\(id\)""", c), u"option value ⛔ 由行 id 出"
    v = PV.public_view()
    rows = v["models_table"]
    assert rows, u"models_table 为空"
    ids = [r["id"] for r in rows]
    assert set(ids) == set(PV.known_models()), (ids, PV.known_models())
    for r in rows:
        assert r["kind"] in ("local", "remote"), r
        assert "可用" in r and r["可用"], r
    # 择值之序：回填之请 ⇒ 后端 default.model ⇒ 首行（⛔ 前端自拟默认）
    assert u"""String(((d || {}).default || {}).model || '')""" in c


# ---------- ⒌ 本机 ／ 云端 须入目 ----------

def test_kind_is_visible_and_mapped():
    c = CONFIG_JS.read_text(encoding="utf-8")
    assert u"""return (k === 'local') ? '本机' : ((k === 'remote') ? '云端' : '种类未给');""" in c
    # 置首（窄格亦见）：kind 文本在 label 之前
    m = re.search(r"let t = (.*?)\+ ' · ' \+ String", c, re.S)
    assert m and "paModelKindTxt" in m.group(1), m


# ---------- ⒍ 三控（⛔ 静默回退） ----------

def test_three_states_no_silent_fallback():
    c = CONFIG_JS.read_text(encoding="utf-8")
    CLEAR = u"paModelRows = null; return paModelState("
    assert c.count(CLEAR) == 4, c.count(CLEAR)
    assert c.count("return paModelState(") == 4, c.count("return paModelState(")
    assert u"""if(!sel || !paModelRows) return '';""" in c
    assert u"sel.disabled = true;" in c
    assert u"照实 0 行" in c          # 0 行 ⇒ 照实报（⛔ 以 0 充未接）
    # ⭐ pm_1928 §一.1⒝（齿之钉正）：旧钉「明书其键」＝**钉了『键名上屏』**（键名在 `<option>` 之项文里 ⇒ 真在屏）——
    #    今唯钉「回退支（一处定形之器）在用 ∧ 键名可查（`title`）∧ 屏上 ⛔ 载」（详 test_pa_human_text_1928.py）。
    assert u"PA_GAP.fallback(" in c, u"键⛔ 在 ⇒ 回退支（一处定形之器 · ⛔ 自造一形）"
    assert u"PA_GAP.fallback('模型表')" in c and u"models_table" in c, \
        u"屏唯人话 ∧ 键名可查（title）"
    assert c.count(u"PA_GAP.down(") == 2, c.count(u"PA_GAP.down(")
    # 显形之态 ⛔ 存空值（存底 ⛔ 静默丢）
    assert u"model:(paModelSel()||paModelKept)" in c


# ---------- ⒎ 有齿（内存改 ⇒ 须红） ----------

def test_gate_has_teeth():
    # 齿一：回填旧硬编之请求体 ⇒ ⒉ 须红
    s = SEND_JS.read_text(encoding="utf-8")
    mut = s.replace(u"const _ab = {user_id:curUser(), session_id:t.id, messages:msgs, stream:true};",
                    u"const _ab = {user_id:curUser(), session_id:t.id, model:'deepseek-v4-flash', messages:msgs, stream:true};", 1)
    assert mut != s
    assert any(re.search(r"model\s*:\s*['\"]", l) for l in mut.splitlines()), u"齿一失"
    # 齿二：去 cards.js 之一调用点 ⇒ ⒊ 须红（3 ⇒ 2）
    ct = CARDS_JS.read_text(encoding="utf-8")
    assert "paModelSel();" in ct
    n = (s.count("paModelSel();") + ct.replace("paModelSel();", "", 1).count("paModelSel();"))
    assert n == 2, n
    # 齿三：去一「显形之清」⇒ ⒍ 须红（4 ⇒ 3）
    c = CONFIG_JS.read_text(encoding="utf-8")
    assert c.replace(u"paModelRows = null; return paModelState(", "", 1).count(u"paModelRows = null; return paModelState(") == 3
    # 齿四：选单静标若回填硬编项 ⇒ ⒈ 须红
    h = PA_HTML.read_text(encoding="utf-8")
    mh = h.replace(u'<option value="">载入中…</option>', u'<option>deepseek-flash</option>', 1)
    assert any(t in mh for t in HARD), u"齿四失"


# ---------- ⒏ 表 ⛔ 得之四态皆有辞（与「显形」同源） ----------

@pytest.mark.parametrize("needle", [u"未应答", u"未回 200", u"models_table", u"照实 0 行"])
def test_four_states_have_wording(needle):
    assert needle in CONFIG_JS.read_text(encoding="utf-8"), needle