# -*- coding: utf-8 -*-
"""M2-A · 卡片「不持久化」标注验收（``web/pa.html`` · 老板 2026-09-18 拍板）。

拍板原话要点：**卡片加「不持久化」标注（加标注，不加持久化）** —— 老板反馈「卡片刷新就消失」
是 Step 2 拍过的预期，但 UI 没标注 ⇒ 用户以为丢了数据。

判据（**不靠自觉**）：

1. **逐类如实**：宿主 ``#paCards`` 的卡（审批/阻断）＝老板给定原文；
   产物卡宿主是 ``#thread``（消息内联，批201 起 F5 后按**消息正文**重建）⇒ **不得**写「刷新后消失」
   （那是反的＝**假标注**）；但配额写失败时它会与消息一起消失 ⇒ 必须写清。
2. **标注由出口追加**（``paRenderCard`` · ``textContent``）：**不得**塞进 ``PA_CARD_BODY``
   —— 那是「事实行」区域，产物卡 body 另有「不得出现完成断言/存在」的判据。
3. **标注不是动作**：不带按钮、不带 onclick（阻断卡的「零按钮」纪律同源）。

独立运行的临时 js 走 ``tmp_path``；本文件不改任何产品代码。
"""
from __future__ import annotations

import io
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 拆面（承 pm 1334 §三.1 · 惟改径 ＋ 并读）：标注表 ＝ faces/cards.js；提示行 ＝ 壳 web/pa.html；
#   `esc` ＝ faces/session.js；`.pa-card-note` 样式 ＝ pa.css。
PA = (ROOT / "web" / "pa.html",
      ROOT / "web" / "pa" / "faces" / "cards.js",
      ROOT / "web" / "pa" / "faces" / "session.js",
      ROOT / "web" / "pa" / "pa.css")

_MOD_START = "const PA_CARD_DEF = {"
_MOD_END = "async function paWriteDecide("

#: 老板给定原文（宿主 #paCards 的卡族）
_BOSS_TEXT = "ⓘ 本卡片不持久化，刷新后消失；记录见消息日志。"


def _src() -> str:
    return "\n".join(io.open(f, encoding="utf-8").read() for f in PA)


def _card_module() -> str:
    s = _src()
    i = s.find(_MOD_START)
    j = s.find(_MOD_END, i)
    assert i > 0 and j > i, "未找到卡片模块区域"
    return s[i:j]


def _defs_for_node() -> str:
    s = _src()
    out = []
    i = s.find("function esc(s){")
    assert i > 0, "未找到 esc"
    out.append(s[i : s.find("\n", i)])
    for head, tail in (
        ("const PA_CARD_DEF = {", "\n};"),
        ("function paCardFilter(kind, payload){", "\n}"),
        ("const PA_CARD_BODY={", "\n};"),
        ("const PA_CARD_ACTS={", "\n"),
        ("const PA_CARD_PERSIST_NOTE = {", "\n};"),
    ):
        i = s.find(head)
        assert i > 0, "未找到 " + head
        j = s.find(tail, i)
        assert j > i, "未找到 " + head + " 的结尾"
        out.append(s[i : j + len(tail)])
    stub = (
        "global.document={createElement:function(){var o={_t:'',"
        "set textContent(v){this._t=String(v==null?'':v);},"
        "get innerHTML(){return this._t.replace(/&/g,'&amp;').replace(/</g,'&lt;')"
        ".replace(/>/g,'&gt;');}};return o;}};\n"
    )
    return stub + "\n".join(out)


def _run_node(tmp_path, body):
    head = "const _BOSS_TEXT=%s;\n" % json.dumps(_BOSS_TEXT, ensure_ascii=False)
    code = _defs_for_node() + "\n" + head + body
    probe = tmp_path / "probe_persist_note.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(code)
    return subprocess.run(
        ["node", str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


# ---------------------------------------------------------------- 纯函数层

def test_three_kinds_have_a_note_and_pa_cards_family_uses_boss_wording(tmp_path):
    """三类卡**都有**标注；``#paCards`` 卡族用老板给定原文（逐字）。"""
    r = _run_node(
        tmp_path,
        """
const kinds = Object.keys(PA_CARD_DEF).sort();
const notes = Object.keys(PA_CARD_PERSIST_NOTE).sort();
if(kinds.join(',') !== notes.join(','))
  throw new Error('标注表与卡片类型不一致（每类都必须有标注）：' + kinds + ' vs ' + notes);
for(const k of ['approval','block'])
  if(PA_CARD_PERSIST_NOTE[k] !== _BOSS_TEXT)
    throw new Error(k + ' 标注不是老板原文：' + PA_CARD_PERSIST_NOTE[k]);
console.log('ok ' + notes.join(','));
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_artifact_note_is_not_the_reverse_claim(tmp_path):
    """产物卡**不得**照抄「刷新后消失」——它 F5 后按消息正文重建；但必须写清配额写失败会一起消失。"""
    r = _run_node(
        tmp_path,
        """
const n = PA_CARD_PERSIST_NOTE.artifact;
if(n.indexOf('刷新后消失') >= 0)
  throw new Error('产物卡被写成「刷新后消失」＝假标注（它 F5 后重建）：' + n);
if(n.indexOf('重建') < 0) throw new Error('产物卡标注未说明「按消息正文重建」：' + n);
if(n.indexOf('本地写入失败') < 0 || n.indexOf('消失') < 0)
  throw new Error('产物卡标注未说明配额写失败时会同消息一起消失：' + n);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_note_is_not_baked_into_fact_rows(tmp_path):
    """分离纪律：标注**不得**进 ``PA_CARD_BODY``（事实行区域另有判据）。"""
    r = _run_node(
        tmp_path,
        """
const html = PA_CARD_BODY.artifact({path:'data/reports/a.md', reported_source:'text_probe'});
for(const bad of ['不持久化','刷新后消失','记录见消息日志'])
  if(html.indexOf(bad) >= 0) throw new Error('标注混进了事实行：' + bad);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


# ---------------------------------------------------------------- 静态层

def test_note_is_rendered_by_the_single_outlet_via_textcontent():
    """标注只由出口 ``paRenderCard`` 追加，且走 ``textContent``（不拼 HTML ⇒ 不注入）。"""
    mod = _card_module()
    i = mod.find("function paRenderCard(kind, payload, host){")
    assert i > 0, "未找到出口"
    fn = mod[i:]
    assert "PA_CARD_PERSIST_NOTE[kind]" in fn, "出口未按 kind 取标注"
    assert "card.appendChild(_n)" in fn, "标注未挂到卡片上"
    assert "_n.textContent=_note;" in fn, "标注未走 textContent（拼 HTML 会引入注入面）"
    assert "pa-card-note" in fn, "标注缺样式类 pa-card-note"


def test_note_has_no_action_and_css_exists():
    """标注**不是动作**（无 onclick/按钮）：与阻断卡「零按钮」纪律同源。"""
    s = _src()
    i = s.find("const PA_CARD_PERSIST_NOTE = {")
    j = s.find("};", i)
    assert 0 < i < j, "未找到标注表"
    table = s[i:j]
    for bad in ("onclick", "<button", "data-act"):
        assert bad not in table, "标注表里出现动作：%s" % bad
    assert ".pa-card-note{" in s, "缺 .pa-card-note 样式"
    assert s.count("const PA_CARD_PERSIST_NOTE = {") == 1, "标注表应只有一处定义（不散落）"


def test_pa_cards_hint_still_scopes_to_pa_cards_family():
    """既有提示行**不得**被本批改动（它已按卡族分区；本批只在卡上补标注）。"""
    s = _src()
    i = s.find('id="paCardsHint"')
    assert i > 0
    line = s[i : s.find("</div>", i)]
    assert "卡片不持久化" in line and "产物卡不在此列" in line, "提示行被改动：%r" % line
