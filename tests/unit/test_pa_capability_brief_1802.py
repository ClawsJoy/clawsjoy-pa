# -*- coding: utf-8 -*-
u"""pm_1802 §一.1／§一.2／§一.3 ＋ pm_1804 §一 之齿：能力面清单**由路由表生成** ＋ 两轴分书。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_capability_brief_1802.py -q

判据：
  ⒜ **生成**（⛔ 手写）：清单之行集 ≡ 路由表之 `/v9/pa/` 集（条数亦同）。
  ⒝ 正控（**防复漂**）：新路由一上 ⇒ 清单**自跟**（加一临时路由 ⇒ 清单含之）。
  ⒞ 反控（**齿咬**）：路由表里没有 ⇒ 清单**必缺**（⛔ 生成器与表脱钩 ＝ 假绿）。
  ⒟ **旧病之钉**：清单**含** `/v9/pa/sys/snapshot` 与 `/v9/pa/sys/<panel>`（9.0.6 上新 · 旧手写表漏者）。
  ⒠ **⛔ 手写表**：本模块内 `PA_CAPABILITY_BRIEF` 唯一赋值处 ＝ 空占位（⛔ 手写接口表）。
  ⒡ **两轴正名**：`pa_system_for(mode)` 逐档含**页上之名**（陪伴 ／ 办事 · ⛔ 自造「聊天 ／ 工作模式」）。
  ⒢ **分书**：提示内「能力面（有哪些接口）」与「能不能动手（看轴）」**两段并存**；
  ⒣ **禁辞表在运行期提示内** ∧ **源内转义写**（⛔ 现字面 —— 承 L56-57）；
  ⒤ **去处逐字**：`切「办事」` ＋ `本机体检`；
  ⒥ ⒝ 之端到端：答体含禁辞 ⇒ 回执 `channel.untrue_wording` 逐条载之（⛔ 静默放行）＋ 反控空表。
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as GR  # noqa: E402

PREFIX = "/v9/pa/"


def _rules(url_map):
    return sorted(str(r.rule) for r in url_map.iter_rules() if str(r.rule).startswith(PREFIX))


def _app(name):
    a = Flask(name)
    GR.register_pa_routes(a)
    return a


# ---------- ⒜–⒠ 能力面清单 ----------

def test_brief_is_generated_from_route_table():
    u"""⒜：清单 ≡ 路由表（逐条在 ∧ 条数同 · ⛔ 手写常量）。"""
    a = _app("t1802a")
    rules = _rules(a.url_map)
    brief = GR.build_capability_brief(a.url_map)
    assert rules, u"路由表为空 ⇒ 判据无从谈起"
    for r in rules:
        assert r in brief, r
    assert brief.count("\n  [") == len(rules), (brief.count("\n  ["), len(rules))
    assert ("接口共 %d 条" % len(rules)) in brief


def test_brief_follows_new_route():
    u"""⒝ 正控：新路由一上 ⇒ 清单自跟（手写表无从跟）。"""
    a = Flask("t1802b")
    GR.register_pa_routes(a)
    assert "zzz_probe_1802" not in GR.build_capability_brief(a.url_map)
    a.add_url_rule(PREFIX + "zzz_probe_1802", "zzz_probe_1802", lambda: "ok", methods=["POST"])
    after = GR.build_capability_brief(a.url_map)
    assert "[POST] /v9/pa/zzz_probe_1802" in after, after[-300:]


def test_brief_missing_when_route_absent():
    u"""⒞ 反控：路由表里没有 ⇒ 清单必缺（齿能咬 ⇒ ⛔ 装饰层）。"""
    a = Flask("t1802c")
    a.add_url_rule(PREFIX + "only_1802", "only_1802", lambda: "ok", methods=["GET"])
    brief = GR.build_capability_brief(a.url_map)
    assert "[GET] /v9/pa/only_1802" in brief
    assert "/v9/pa/sys/snapshot" not in brief
    assert brief.count("\n  [") == 1


def test_brief_covers_sys_faces_added_in_906():
    u"""⒟：9.0.6 上新之七面**必在**（旧手写表漏之 ⇒ 模型照实回「不在授权面」之的）。"""
    brief = GR.build_capability_brief(_app("t1802d").url_map)
    assert "[GET] /v9/pa/sys/snapshot" in brief
    assert "[GET] /v9/pa/sys/<panel>" in brief


def test_no_handwritten_capability_table():
    u"""⒠：清单**唯**由生成器出（源内 ⛔ 手写接口表 · 唯一赋值处 ＝ 空占位）。"""
    src = io.open(GR.__file__, encoding="utf-8").read()
    assert len(re.findall(r"(?m)^PA_CAPABILITY_BRIEF = ", src)) == 1, u"赋值处须唯一"
    assert re.search(r'(?m)^PA_CAPABILITY_BRIEF = u""$', src), u"占位须为空（⛔ 手写表）"
    assert "def build_capability_brief" in src
    assert "_set_capability_brief(app)" in src


# ---------- ⒡–⒤ 提示词（pm_1804 §一） ----------

def test_prompt_names_match_the_page():
    u"""⒡：两态之**正名**与页上一致（页 ＝ 陪伴 ／ 办事 · selfdesc.js:2868-2869）。"""
    for mode in ("companion", "work"):
        s = GR.pa_system_for(mode)
        assert u"陪伴" in s and u"办事" in s, mode
    s = GR.pa_system_for("companion")
    assert u"切「办事」" in s
    assert u"工作模式" not in s, u"⛔ 自造一套辞（页曰「办事」）"


def test_prompt_separates_axis_from_capability():
    u"""⒢ ＋ ⒤：能力面 ⟷ 能不能动手 两段并存；去处逐字。"""
    s = GR.pa_system_for("companion")
    assert u"在能力面" in s and u"我现在能做" in s
    assert u"陪伴轴" in s and u"办事轴" in s
    assert u"本机体检" in s and u"切「办事」" in s
    assert u"只商量" in s and u"不出手" in s


def test_banned_wording_table_in_runtime_prompt_not_in_source():
    u"""⒣：禁辞表**在运行期提示内** ∧ 源内**转义写**（⛔ 现字面 · 承 L56-57）。"""
    prompt = GR.pa_system_for("companion")
    words = [u"已受理", u"已安排", u"已转办", u"正在处理"]
    for w in words:
        assert w in prompt, w
    src = io.open(GR.__file__, encoding="utf-8").read()
    for w in words:
        assert w not in src, u"字面须转义写（源内 ⛔ 现）：%s" % w


# ---------- ⒥ 回执之结构化据 ----------

def _client(tmp_path, monkeypatch, reply):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))

    def _fake_llm_brain(system_prompt=None, model=None, max_tokens=None):
        def _b(context_text):
            return reply

        _b._is_pa_brain = True
        return _b

    monkeypatch.setattr(GR, "llm_brain", _fake_llm_brain)
    a = Flask("t1802e")
    GR.register_pa_routes(a, brain=GR.llm_brain())
    return a.test_client()


def test_dialog_receipt_flags_untrue_wording(tmp_path, monkeypatch):
    u"""正控：答体含禁辞 ⇒ 回执 `channel.untrue_wording` 逐条载之（⛔ 静默放行）。"""
    c = _client(tmp_path, monkeypatch, u"已受理，我这就去看。")
    d = c.post("/v9/pa/dialog", json={"user_id": "u1", "session_id": "s1",
                                      "text": u"你能检查电脑吗"}).get_json()
    ch = d["channel"]
    assert ch["acts"] is False and ch["kind"] == "dialog"
    assert u"已受理" in ch["untrue_wording"], ch


def test_dialog_receipt_clean_when_no_untrue_wording(tmp_path, monkeypatch):
    u"""反控：如实之答 ⇒ 空表（⛔ 恒报 ⇒ 标不可用）。"""
    c = _client(tmp_path, monkeypatch, u"本通道只商量，不出手；要真跑请切「办事」。")
    d = c.post("/v9/pa/dialog", json={"user_id": "u1", "session_id": "s2",
                                      "text": u"你能检查电脑吗"}).get_json()
    assert d["channel"]["untrue_wording"] == []
