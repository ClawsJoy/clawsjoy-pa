# -*- coding: utf-8 -*-
"""pm 2919 · PA 首屏占位「名实不符」之闸（2026-10-12 · CW b2a5182）。

病（PM 一手 · 两档宽 · soak 逐秒）：`#paSrcSum` 于开页首刻显
    `⚠ 无 JS：无读数（须运行期）` —— 而 **JS 明明在跑**（唯数未到）⇒ 名实不符 ∧ 措辞是对
    开发者说（⛔ 用户语）∧ 与同页已立四态（未接 ／ 不接 ／ 不可达 ／ 陈旧）不同族（无态可归）。

治：**二境分形** —— 首屏（JS 在 · 数未到）⇒ 中性「读中…」；真无 JS ⇒ 唯入 `<noscript>`。
    字号（承 §二）：顶栏 chip ／ 页签 ／ 汇总行 ⇒ `≥ 12px`（PM 一手：`11.5px` ／ `11.0px` 偏小）。
    ⚠ 字号之底为**裁**：若日后判「密度优先」而留小 ⇒ 本底须随裁而改（承 pm 2919 §二.3）。

判据皆机检（读真件 · ⛔ 复制代码）。
"""
from __future__ import annotations

import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "web" / "pa.html"
PA_CSS = ROOT / "web" / "pa" / "pa.css"
V3_CSS = ROOT / "web" / "pa" / "pa_v3.css"

OLD = "无 JS：无读数（须运行期）"


def _read(p: Path) -> str:
    return io.open(p, encoding="utf-8").read()


# ---- ① 病：旧字面 ⛔ 留在静壳（＝首屏之占位） ------------------------------

def test_static_has_no_wei_js_assertion():
    assert OLD not in _read(HTML), "静壳仍载旧字面：" + OLD


def test_srcsum_placeholder_is_neutral():
    assert '<b id="paSrcSum">读中…</b>' in _read(HTML), "首屏汇总占位须为中性「读中…」"


def test_all_five_placeholders_are_neutral():
    n = _read(HTML).count(">读中…<")
    assert n == 5, "占位之数须为 5（一处一行），实 " + str(n)


# ---- ② 真无 JS 之处 ⇒ 唯 noscript -----------------------------------------

def test_noscript_carries_the_no_js_wording():
    m = re.search(r"<noscript>(.*?)</noscript>", _read(HTML), re.S)
    assert m, "缺 <noscript>（真无 JS 之辞无处可落）"
    assert "无 JS" in m.group(1), "noscript 须载「无 JS」之辞"
    assert "nojs-note" in m.group(1), "noscript 之文须用定形类 nojs-note"


def test_nojs_note_is_styled_once():
    assert _read(V3_CSS).count(".nojs-note{") == 1, "nojs-note 之形须一处定形（pa_v3.css）"


# ---- ③ 字号之底（承 §二） -------------------------------------------------

def _fontsize(css: str, sel: str) -> float:
    i = css.index(sel)
    m = re.search(r"font-size:\s*([0-9.]+)px", css[i:i + 400])
    assert m, sel + " 无 font-size"
    return float(m.group(1))


def test_font_floor_top_bar_chips():
    assert _fontsize(_read(PA_CSS), ".top-right{") >= 12, "顶栏 chip 字号须 ≥ 12px"


def test_font_floor_face_tabs():
    assert _fontsize(_read(V3_CSS), ".mtabs button{") >= 12, "页签字号须 ≥ 12px"


def test_font_floor_srcsum():
    assert _fontsize(_read(V3_CSS), ".srcsum{") >= 12, "汇总行字号须 ≥ 12px"


# ---- 齿：改回旧字面 ⇒ 判红 ------------------------------------------------

def test_gate_has_teeth():
    h = _read(HTML)
    mutant = h.replace(">读中…</b>", ">" + OLD + "</b>")
    assert mutant != h, "变更点已漂（齿失效）"
    assert OLD in mutant, "齿失效：改回旧字面竟不成"
