# -*- coding: utf-8 -*-
u"""pm_1492 §二 · Fork-2 改依键之测（承 pm_1490 §二 · pm_1491 §二 ／ §三 · CW b2a5182 · 2026-10-06）。

病（pm_1487 §一 ／ pm_1486 §二 · 一手）：Fork-2 以**模型之辞之词形**判果 ⇒ 同一「无据」之实 ⇒ 二果
（`paSelfRefusal(模型之答)` ⇒ 以「查不到」起首者弃、否则显「由模型作答」）。治法（pm_1492 §二）：
**唯自后端之键出**（`gate.display`）｜键 ⛔ 得 ⇒ **显形**（⛔ 词形兜底）。

判据（逐条 · ⛔ 复制被审之逻辑 —— 原文抽出 ＋ `node` 真跑）：
  K1 一处出：`paSelfFactFamily` 之定义唯 `1` 处（`selfdesc.js`）；三处调用（`status.js` ×2 ／
     `send.js` ×1）皆以 `typeof … === 'function'` 之门（知其实方传）；⛔ 二处各判
  K2 键之判三态：`paSelfGateSay` —— `refuse` ／ `model` ／ 键 ⛔ 得（note 逐字）
  K3 本机事实族之标：非是非问之事族（「台账里有哪些项目？」）⇒ 真（`paSelfFactYN` 为假 ⇒ 二判**必分**）
  K4 Fork-2 三处 ⛔ 以词形判：源之逐字（`_gSay` ／ `paSelfGateSay(fbf)` ／ `_gSay2`）
  K5 显形：字面逐字 ＋ `fbf` 在 ∧ 键 ⛔ 得 ⇒ note 非空（⛔ 静默）
  K6 `paSelfFb` 载 `gate`（一处定形）
  K7 齿：旧式（`paSelfRefusal` 之词形）vs 新式（键）喂**同一对** ⇒ 果**必不同**
     （即：挖掉键之判而回词形 ⇒ 旧病立现 —— ⛔ 挖了还能过）
  K8 不回归：`paSelfRefusal` 之本体**仍在**（`send.js` 之 `paRefusalStale` 尚倚之 ⇒ ⛔ 删）
  K9 pm_1524 §一.2（裁一 · 红线）：**该守之轴 ⇒ 改依 `paSelfFactFamily`** —— ⛔ 旧 `paSelfFactYN`
     （族 ∧ **是非问**）⇒ 非是非问之事实族问（「台账里有哪些项目？」）落回落 ⇒ **题文出机**。
     齿：该问 ⇒ `paSelfFactFamily` 真 ∧ `paSelfFactYN` 假 ⇒ **二轴必分**（挖掉本改 ⇒ 旧病立现）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_gate_key_judge.py -q
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FACES = ROOT / "web" / "pa" / "faces"
SD = FACES / "selfdesc.js"
SJ = FACES / "send.js"
ST = FACES / "status.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_1492"

NODATA = u"后端未给本轮判据 ⇒ 本条照实显（⛔ 判）"


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _fn(src: str, name: str) -> str:
    u"""按花括号配平抽出 `function name(...){...}` 原文（⛔ 复制）。"""
    i = src.find("function " + name + "(")
    assert i > 0, "未找到函数 " + name
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
    raise AssertionError("函数 " + name + " 花括号不配平")


def _js() -> str:
    u"""真源之三件：`PA_FACT_MARK` ／ `paSelfFactFamily` ／ `paSelfGateSay` ＋ `paSelfRefusal`（旧式之对照）。"""
    sd = _read(SD)
    m = re.search(r"const PA_FACT_MARK = .*?;", sd)
    assert m, "PA_FACT_MARK 未找到"
    m2 = re.search(r"const PA_GATE_NODATA = .*?;", sd)
    assert m2, "PA_GATE_NODATA 未找到"
    m3 = re.search(r"const PA_STATE_ASK = .*?;", sd)
    m4 = re.search(r"const PA_YN_MARK = .*?;", sd)
    assert m3 and m4, u"是非问之二字表未找到"
    return (m.group(0) + "\n" + m2.group(0) + "\n" + m3.group(0) + "\n" + m4.group(0) + "\n"
            + _fn(sd, "paSelfFactFamily") + "\n" + _fn(sd, "paSelfGateSay") + "\n"
            + _fn(sd, "paSelfFactYN") + "\n" + _fn(sd, "paSelfRefusal") + "\n")


def _run_node() -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    js = (_js()
          + u"const CASES = " + json.dumps([
              {"q": u"台账里有哪些项目？"},
              {"q": u"台账里的项目是不是都完成了？"},
              {"q": u"你好，今天天气怎么样？"},
              {"q": u""},
              {"q": None},
          ], ensure_ascii=False) + ";\n"
          + u"const GATES = " + json.dumps([
              {"gate": {"display": "refuse"}},
              {"gate": {"display": "model"}},
              {"gate": {}},
              {},
              None,
          ], ensure_ascii=False) + ";\n"
          + u"const o = {fam: [], yn: [], gate: [], old_vs_new: []};\n"
          + u"for(const c of CASES) o.fam.push(paSelfFactFamily(c.q));\n"
          + u"for(const c of CASES) o.yn.push(paSelfFactYN(c.q));\n"
          + u"for(const g of GATES) o.gate.push(paSelfGateSay(g));\n"
          + u"for(const p of [['查不到。', {gate:{display:'model'}}],"
            u" ['已完成。', {gate:{display:'refuse'}}], ['随便答一句。', {gate:{display:'model'}}]]){\n"
            u"  o.old_vs_new.push({raw: p[0], old: paSelfRefusal(p[0]), neu: paSelfGateSay(p[1]).refuse});\n"
            u"}\n"
            + u"console.log(JSON.stringify(o));\n")
    f = SCRATCH / "gate_judge.js"
    io.open(str(f), "wb").write(js.encode("utf-8"))
    r = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


OUT = _run_node()


# ---------------------------------------------------------------- K1 一处出
def test_k1_fact_family_one_source():
    n = 0
    for p in (SD, SJ, ST):
        n += _read(p).count("function paSelfFactFamily(")
    assert n == 1, u"`paSelfFactFamily` 之定义须唯 1 处（得 %d）" % n
    assert _read(SD).count("const PA_FACT_MARK = ") == 1
    assert _read(SJ).count("PA_FACT_MARK") == 0 and _read(ST).count("PA_FACT_MARK") == 0, \
        u"⛔ 二处各判（`PA_FACT_MARK` 之字面唯 `selfdesc.js` 一处）"
    for p, call in ((ST, "paSelfFactFamily(text)"), (ST, "paSelfFactFamily(userText)"),
                    (SJ, "paSelfFactFamily(text)")):
        s = _read(p)
        assert call in s, u"%s 未带 %s" % (p.name, call)
    g = u"try{ if(typeof paSelfFactFamily === 'function')"
    assert _read(ST).count(g) == 2 and _read(SJ).count(g) == 1, u"三处调用须皆带「知其实方传」之门"
    assert _read(SD).count("window.paSelfFactFamily = paSelfFactFamily;") == 1


def test_k1b_no_fact_family_hardcode():
    u"""⛔ 硬编之值（`fact_family:true/false` 之字面）—— 必自一处出。"""
    for p in (SD, SJ, ST):
        s = _read(p)
        for bad in ("fact_family: true", "fact_family: false", "fact_family = true", "fact_family = false"):
            assert bad not in s, u"%s 含硬编 %s" % (p.name, bad)


# ---------------------------------------------------------------- K2 ／ K3 键之判
def test_k2_key_three_states():
    g = OUT["gate"]
    assert g[0] == {"ok": True, "refuse": True, "note": ""}, u"display=refuse ⇒ 认（拒）"
    assert g[1] == {"ok": True, "refuse": False, "note": ""}, u"display=model ⇒ 认（显）"
    for x in g[2:]:
        assert x["ok"] is False and x["refuse"] is False and x["note"] == NODATA, \
            u"键 ⛔ 得 ⇒ 显形（逐字）：%r" % (x,)


def test_k3_fact_family_not_only_yn():
    fam = OUT["fam"]
    assert fam[0] is True, u"「台账里有哪些项目？」⇒ 本机事实族（⚠ 非是非问 —— 此正漏拦之例）"
    assert fam[1] is True
    assert fam[2] is False and fam[3] is False and fam[4] is False
    sd = _read(SD)
    assert u"PA_FACT_MARK.test(String(q == null ? '' : q))" in sd, u"事实族之判须唯 `PA_FACT_MARK`"
    m = re.search(r"function paSelfFactYN\(s\)\{(.*?)\n\}", sd, re.S)
    assert m and "PA_STATE_ASK" in m.group(1), u"`paSelfFactYN`（是非问）较窄 ⇒ 二判别"


# ---------------------------------------------------------------- K4 ／ K5 ／ K6 源之逐字
def test_k4_fork2_three_sites_key_only():
    sd = _read(SD)
    assert sd.count("paSelfRefusal(raw)") == 0, u"Fork-2 三处 ⛔ 得以模型之辞之词形判"
    assert "if(fbf && (fx || _gSay.refuse)){" in sd
    assert "if(aside && paSelfGateSay(fbf).refuse){" in sd
    assert "if(_gSay2.refuse){" in sd
    assert sd.count("const _gSay = paSelfGateSay(fbf);") == 1
    assert sd.count("const _gSay2 = paSelfGateSay(fbf);") == 1


def test_k5_nodata_visible():
    sd = _read(SD)
    assert (u"const PA_GATE_NODATA = '" + NODATA + u"';") in sd, u"显形之字面须逐字"
    assert u"((!_gSay.ok) ? ('⚠ ' + _gSay.note + '\\n') : '')" in sd, u"回落支须显形（键 ⛔ 得）"
    assert u"const _gateNote = (fbf && !_gSay2.ok) ? ('⚠ ' + _gSay2.note) : '';" in sd


def test_k6_fbf_carries_gate():
    sd = _read(SD)
    assert sd.count("gate:g.gate};") == 1, u"`paSelfFb` 载 `gate` ⇒ 一处定形"


def test_k8_selfrefusal_body_kept():
    u"""⛔ 删 —— `send.js` 之 `paRefusalStale`（第 4 读者）尚倚之（pm_1492 §二.3 之令）。"""
    assert _read(SD).count("function paSelfRefusal(s){") == 1
    sj = _read(SJ)
    assert "paSelfRefusal(t)" in sj and "function paRefusalStale(t){" in sj


# ---------------------------------------------------------------- K7 齿
def test_k7_teeth_wordform_vs_key_diverge():
    u"""齿：挖掉键之判（回词形）⇒ 果必变 —— 即「同一『无据』之实 ⇒ 二果」之旧病立现。"""
    rows = OUT["old_vs_new"]
    assert rows[0]["old"] is True and rows[0]["neu"] is False, \
        u"raw「查不到。」∧ 键 display=model ⇒ 旧判拒 ／ 新判⛔拒（必分）"
    assert rows[1]["old"] is False and rows[1]["neu"] is True, \
        u"raw「已完成。」∧ 键 display=refuse ⇒ 旧判⛔拒 ／ 新判拒（必分）"
    assert rows[2]["old"] is False and rows[2]["neu"] is False
    assert any(r["old"] != r["neu"] for r in rows), u"⛔ 无齿（二式果同 ⇒ 挖了还能过）"


# ---------------------------------------------------------------- K9 守之轴（pm_1524 §一.2）
def test_k9_guard_axis_is_fact_family():
    u"""pm_1524 §一.2（裁一 · 红线）：本守（`selfdesc.js` 保拒答支）之轴 ⇒ **唯 `paSelfFactFamily`**。

    病（我 `1523 §三` 一手）：旧轴 `paSelfFactYN`（族 ∧ 是非问）⇒ 「台账里有哪些项目？」（非是非问）
      ⇒ 支 ⛔ 取 ⇒ 回落模型 ⇒ **题文出机** ⇒ 而屏仍显 canonical 拒答 ⇒ 二事并立 ＝ 红线。
    """
    sd = _read(SD)
    assert u"if(paSelfFactFamily(lastQ)){" in sd, u"本守之轴须为 `paSelfFactFamily`"
    assert u"if(paSelfFactYN(lastQ)){" not in sd, u"⛔ 留旧轴（二轴并存 ⇒ 二源必漂）"
    # 齿（行为 · node 真跑）：该问 ⇒ 二轴**必分** ⇒ 用于守则果别
    fam, yn = OUT["fam"], OUT["yn"]
    assert fam[0] is True, u"「台账里有哪些项目？」⇒ 本机事实族（含非是非问）"
    assert yn[0] is False, u"同一问 ∧ 旧轴（是非问）⇒ 假 ⇒ 二轴必分（此即出机之因）"
    assert fam[0] != yn[0], u"⛔ 无齿（二轴同值 ⇒ 挖了还能过）"
    # 反控：是非问（族内）⇒ 二轴同真（故其非「守之轴改」之反例）
    assert fam[1] is True and yn[1] is True


# ---------------------------------------------------------------- K10 收窄之守（pm_1531 §一 ／ §二）
SCRATCH_B = ROOT / "data" / "tmp" / "_cw_1531"


def _js_assert() -> str:
    u"""pm_1531 之真源（⛔ 复制）：唯判辞之本体 ／ 开关 ／ 显形之果 ／ 触发之逐字 ／ 有据轮之渲之逐字。"""
    sd = _read(SD)
    m_fact = re.search(r"const PA_FACT_MARK = .*?;", sd)
    m_deny = re.search(r"const PA_DENY_WORD = .*?;", sd)
    m_grd = re.search(r"const PA_SELF_ASSERT_GUARD = .*?;", sd)
    m_say = re.search(r"const PA_SELF_ASSERT_SAY = .*?;", sd)
    m_sa = re.search(r"^ *const _sa = .*?;", sd, re.M)
    m_ful = re.search(r"^ *const full = \(hs \? \(hs \+ '\\n'\) : ''\) \+ \(_sa \? .*?;", sd, re.M)
    for nm, m in ((u"PA_FACT_MARK", m_fact), (u"PA_DENY_WORD", m_deny),
                  (u"PA_SELF_ASSERT_GUARD", m_grd), (u"PA_SELF_ASSERT_SAY", m_say),
                  (u"const _sa = …", m_sa), (u"const full = (hs ? …", m_ful)):
        assert m, u"未找到 " + nm
    decls = "\n".join(m.group(0) for m in (m_fact, m_deny, m_grd, m_say)).replace(
        u"const PA_SELF_ASSERT_GUARD = true;", u"let PA_SELF_ASSERT_GUARD = true;")
    sa_line = m_sa.group(0).strip()
    ful_line = m_ful.group(0).strip()
    cases = json.dumps([
        {"q": u"台账里有哪些项目？", "raw": u"已完成。"},
        {"q": u"你好，今天天气怎么样？", "raw": u"已完成。"},
        {"q": u"台账里有哪些项目？", "raw": u"据本机素材：见下。"},
        {"q": u"台账里有哪些项目？", "raw": None},
    ], ensure_ascii=False)
    return (decls + "\n" + _fn(sd, "paSelfFactFamily") + "\n" + _fn(sd, "paSelfModelAssertDenied") + "\n" + _fn(sd, "paSelfTagSay") + "\n"
            + u"const CASES = " + cases + ";\n"
            + u"function saOf(paSelfLastUser, raw){\n  " + sa_line + u"\n  return _sa; }\n"
            + u"function saOff(paSelfLastUser, raw){ PA_SELF_ASSERT_GUARD = false;\n  " + sa_line
            + u"\n  PA_SELF_ASSERT_GUARD = true; return _sa; }\n"
            + u"function screenOf(q, raw){\n  const paSelfLastUser = q;\n"
            + u"  const tag = " + json.dumps(u"【本机素材（据 3 条）】", ensure_ascii=False) + ";\n"
            + u"  const wa = function(s){ return s; };\n"
            + u"  const b = {u: " + json.dumps(u"本机素材（据 3 条）：台账.md ／ 决策.md", ensure_ascii=False) + "};\n"
            + u"  const _sa = saOf(paSelfLastUser, raw);\n"
            + u"  const hs = paSelfTagSay('local', 3);\n  " + ful_line + u"\n  return full; }\n"
            + u"const o = {sa: [], off: [], screen: '', screen_plain: ''};\n"
            + u"for(const c of CASES) o.sa.push(saOf(c.q, c.raw));\n"
            + u"o.off = CASES.map(function(c){ return saOff(c.q, c.raw); });\n"
            + u"o.screen = screenOf(CASES[0].q, CASES[0].raw);\n"
            + u"o.screen_plain = screenOf(CASES[1].q, CASES[1].raw);\n"
            + u"console.log(JSON.stringify(o));\n")


def _run_node_assert() -> dict:
    SCRATCH_B.mkdir(parents=True, exist_ok=True)
    f = SCRATCH_B / "assert_gate.js"
    io.open(str(f), "wb").write(_js_assert().encode("utf-8"))
    r = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


OUTB = _run_node_assert()


def test_k10_body_is_word_only():
    u"""pm_1531 §一.3：本体**收窄为「唯判辞」** —— ⛔ 轴判（旧 ⒜／⒝ 二死轴）／ ⛔ 旧名 ／ 判辞之施仍一处。

    ⚠ 扫**代码形**（⛔ 裸名）：本件之明书之注须引旧名 ／ `_canon` ⇒ 裸计数自伤（假红）。
    """
    sd = _read(SD)
    assert sd.count("function paSelfModelAssertDenied(a){") == 1
    for bad in (u"function paSelfModelAssertForbidden(", u"window.paSelfModelAssertForbidden =",
                u"paSelfModelAssertForbidden(fbf.q"):
        assert sd.count(bad) == 0, u"旧名之代码形仍存：" + bad
    assert sd.count("paSelfModelAssertDenied(") == 2, u"本体 1 ＋ 调用 1（有据支；无据支之恒假守已删 · pm_1533 §一.⒝）"
    assert sd.count("PA_DENY_WORD.test(") == 1, u"判辞之施（`PA_DENY_WORD.test`）唯此一处（⛔ 二源）"
    body = _fn(sd, "paSelfModelAssertDenied")
    assert u"function paSelfModelAssertDenied(a){" in body, u"签名唯（a）⇒ ⛔ 问之参（前提在调用处）"
    assert "PA_DENY_WORD.test(" in body
    assert "PA_FACT_MARK" not in body and "paSelfFactYN" not in body, u"本体唯判辞（⛔ 轴）"
    assert sd.count("PA_SELF_ASSERT_GUARD") == 2, u"开关之读者唯「定义 ＋ 触发」二处"
    assert sd.count("const PA_SELF_ASSERT_GUARD = true;") == 1


def test_k10_narrow_trigger_and_screen():
    u"""pm_1531 §一：触发**取窄**（族 ∧ 词形命中）⇒ 以**显形之果**易断言（⛔ `_canon`）。§二.2 正控 ＋ 三反控。"""
    o = OUTB
    assert o["sa"][0] is True, u"正控：族 ∧ 有据 ∧ 答含 deny 辞 ⇒ 触发"
    assert o["sa"][1] is False, u"反控一：非族 ⇒ ⛔ 触发（答照显）"
    assert o["sa"][2] is False, u"反控二：族 ∧ 有据 ∧ 答 ⛔ 含辞 ⇒ ⛔ 触发"
    assert o["sa"][3] is False, u"边界：辞 ⛔ 给（null）⇒ ⛔ 触发（⛔ 崩）"
    scr = o["screen"]
    assert u"已拦" in scr, u"正控：屏须显「已拦」之字"
    assert u"本机已得据" in scr and u"⛔ 采信" in scr, u"显形之果须含三义（已得据 ／ 已拦 ／ ⛔ 采信）"
    assert u"本机无据" not in scr, u"反控三：有据之轮 ⛔ 显「本机无据」（⛔ `_canon`）"
    assert u"据 3 条" in scr, u"贴据照旧（「据 N 条」仍在屏）"
    assert u"已完成。" in o["screen_plain"], u"反控一之屏：非族 ⇒ 模型之辞照显"
    assert o["off"][0] is False, u"可退之形（§二.4）：开关 false ⇒ 本守不触"
    assert any(a != b for a, b in zip(o["sa"], o["off"])), u"⛔ 无齿（开关无损 ⇒ 可退之形不立）"


def test_k10_gateinfo_branch_has_no_canon():
    u"""结构：有据轮之支（`gateInfo`）⛔ 引 `_canon`（其义为「本机无据」⇒ 以一不实易一不实）。"""
    sd = _read(SD)
    assert sd.count("if(gateInfo){") == 1
    i = sd.index("if(gateInfo){")
    d, j = 0, i
    while j < len(sd):
        if sd[j] == "{":
            d += 1
        elif sd[j] == "}":
            d -= 1
            if d == 0:
                break
        j += 1
    blk = sd[i:j + 1]
    assert "_canon" not in blk, u"`gateInfo` 支 ⛔ 引 `_canon`"
    assert "PA_SELF_ASSERT_SAY" in blk and "_sa" in blk
    assert "paSelfFactFamily(paSelfLastUser)" in blk and "paSelfModelAssertDenied(raw)" in blk
    assert "paSelfModelAssertForbidden(" not in sd


def test_k10_no_dead_guard_in_fbf_branch():
    u"""pm_1533 §一.⒝：无据支（`fbf`）之恒假守已删（死码之患）⇒ 该支恒取 `wa(raw)` · ⛔ 引 canonical。"""
    sd = _read(SD)
    assert "_forbid" not in sd, u"恒假守 `_forbid` 仍在（死码之患 · pm_1533 §一.⒝）"
    assert u"(_forbid ? _canon : wa(raw))" not in sd, u"旧三歧（`_forbid ? _canon : wa(raw)`）仍在"
    assert u"wa(raw) + '\\n' + paSelfScanSay(fbf)" in sd, u"无据支须恒取 `wa(raw)`（¬族 ∧ 无据 ⇒ 回落 ⇒ 显模型之答 · 正当）—— 唯接一行人话之检索摘要（pm_1822 §二.4⒟）"
    assert u"+ (_arcF ? '\\n（档案面另有旁证" in sd, u"档案面之旁证行仍须**据回执**（⛔ 恒挂 · ⛔ 无据而书有）"
