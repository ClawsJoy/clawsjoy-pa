# -*- coding: utf-8 -*-
u"""齿：`/v9/pa/turn` 之**人话回执**（承 pm_2021 §五.1 · 承 pm_1012 §一 ／ P3）。

守（皆可机验 · 承「判据必须能红」）：
  ① **四键齐**：一句 ／ 做了什么 ／ 动了哪些件 ／ 可否退（P3 之三问 ＋ 一句结论）
  ② **三态**分明：成 ／ 读数不可得 ／ 未落 —— ⛔ 混（承 P9 BUG-1：查不到 ⛔ 说成已保存 ∧ ⛔ 说成没保存）
  ③ ⭐ **人话之律**：⛔ 数字（行数 ／ 枚数）／ ⛔ 径 ／ ⛔ 键名（`session_lines` 之族）
     —— 反例齿：以 pm_2021 §五.1 所逮之**真负例**（用户面上那一行）喂之 ⇒ **必咬**
  ④ **接线**：该字段真出于本路之响应（⛔ 前端自拟 ／ ⛔ 丢原字 —— 原字仍在，供工程注记）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.pa.gateway_routes import PA_TURN_HUMAN, pa_turn_human  # noqa: E402

GR = ROOT / "core" / "pa" / "gateway_routes.py"
KEYS = [u"一句", u"做了什么", u"动了哪些件", u"可否退"]
BS = chr(92)

#: pm_2021 §五.1 所逮之**真负例**（用户面上出现之纯工程回执 · 逐字 · 唯径以拼接免逃逸）
NEG = (u"💾 本轮已落盘（后端回执：会话 4→4 行 · events 588→589 行 · "
       + BS.join([u"data", u"v9", u"pa"]) + BS + u"sessions" + BS + u"session_pa_muymglcq.jsonl）")


def _viol(txt):
    u"""人话之律 ⇒ 违律之由（空串 ＝ 合规）。"""
    bad = []
    if any(ch.isdigit() for ch in txt):
        bad.append(u"数字")
    if (BS in txt) or (u"/" in txt):
        bad.append(u"径")
    for k in (u"session", u"events", u"jsonl", u"_readable"):
        if k in txt:
            bad.append(u"键名")
            break
    return u"／".join(bad)


def test_四键齐():
    for st in (u"done", u"unknown", u"miss"):
        assert sorted(PA_TURN_HUMAN[st]) == sorted(KEYS), (st, sorted(PA_TURN_HUMAN[st]))


def test_三态分明():
    u"""⭐ 承 P9 BUG-1：三态 ⛔ 混（读数不可得 ≠ 已保存 ≠ 没保存）。"""
    _d = pa_turn_human(True, True)[u"一句"]
    _u = pa_turn_human(False, False)[u"一句"]
    _m = pa_turn_human(False, True)[u"一句"]
    assert _d == u"✅ 已记下这一轮（可回看）"
    assert (u"查不到" in _u) and (u"✅" not in _u) and (u"没记下" not in _u)
    assert (u"没记下" in _m) and (u"✅" not in _m)
    assert len({_d, _u, _m}) == 3
    # 反控：读数不可得**优先**於 recorded=true（⛔ 报成「已记下」= 假绿 · 承 P9 BUG-1）
    assert pa_turn_human(True, False)[u"一句"] == _u


def test_人话之律_正负控():
    for st in (u"done", u"unknown", u"miss"):
        for k in KEYS:
            v = PA_TURN_HUMAN[st][k]
            assert v.strip(), (st, k)
            assert _viol(v) == u"", (st, k, _viol(v))
    # 反例齿（承「判据必须能红」）：真负例 ⇒ 必咬
    v = _viol(NEG)
    assert u"数字" in v, v
    assert u"径" in v, v


def test_接线_字段真出且原字未丢():
    src = GR.read_text(encoding="utf-8")
    assert u"def pa_turn_human(" in src
    assert u'"human": pa_turn_human(_recorded, _readable)' in src       # ⛔ 前端自拟
    for k in (u'"session_lines_before"', u'"events_lines_before"',
              u'"session_path"', u'"recorded"'):
        assert k in src, k    # ⛔ 丢原字（工程注记仍须可取）