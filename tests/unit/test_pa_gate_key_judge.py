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
    assert u"+ ((!_gSay.ok) ? ('⚠ ' + _gSay.note + '\\n') : '')" in sd, u"回落支须显形（键 ⛔ 得）"
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
