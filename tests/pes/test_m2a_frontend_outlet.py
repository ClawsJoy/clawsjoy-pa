# -*- coding: utf-8 -*-
"""M2-A · Step 2 前端统一展示出口验收（``web/pa.html``）。

设计稿：``codex/2026-09-17-v9pes-m2a-visibility-closure-design.md`` §2.4 / §6 Step 2。

三层判据，**都不靠自觉**：

1. **纯函数层**（node 跑从真实 pa.html 抽出的定义，**move 而非 retype**）：
   白名单过滤 / 未知字段上报名单 / 未知 kind 拒绝 / 缺必填拒绝 / 决策串白名单 / 转义；
2. **静态层**（读真实 pa.html 源码）：卡片只经 ``paRenderCard`` 进固定容器 ``#paCards``、
   **不写 #thread**、卡片模块内**无时间调用**（反例：前端造倒计时 / 撤销窗口）；
3. **边界层**：``PA_STATE_DEF`` 仍 9 键 —— Step 2 **不碰状态契约**（``blocked`` 键属 Step 3）。

独立运行的临时 js 走 ``tmp_path``，不落仓库；本文件不改任何产品代码。
"""
from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PA = ROOT / "web" / "pa.html"

#: 卡片模块区域（统一出口 + 迁移后的 renderPaWriteCard）
_MOD_START = "const PA_CARD_DEF = {"
_MOD_END = "async function paWriteDecide("

#: 前端禁止的时间调用（设计稿 §2.1 revoke_window 纪律：秒数只能由后端给）
_TIME_CALLS = ("Date.now(", "new Date(", "setInterval(", "getTime(")


def _src() -> str:
    return io.open(PA, encoding="utf-8").read()


def _card_module() -> str:
    s = _src()
    i = s.find(_MOD_START)
    j = s.find(_MOD_END, i)
    assert i > 0 and j > i, "未找到卡片模块区域（PA_CARD_DEF ~ paWriteDecide）"
    return s[i:j]


def _strip_comments(js: str) -> str:
    """去掉块注释与行注释后再判据（注释里写「禁止 Date.now()」是合法的）。"""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"^\s*//.*$", "", js, flags=re.M)


def _defs_for_node() -> str:
    """从真实 pa.html 抽定义（move 而非 retype）+ 最小 DOM stub（仅供 esc 用）。"""
    s = _src()
    out = []
    # esc：单行函数，取整行
    i = s.find("function esc(s){")
    assert i > 0, "未找到 esc"
    out.append(s[i : s.find("\n", i)])
    for head, tail in (
        ("const PA_CARD_DEF = {", "\n};"),
        ("function paCardFilter(kind, payload){", "\n}"),
        ("const PA_CARD_BODY={", "\n};"),
        ("const PA_CARD_ACTS={", "\n"),
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
    code = _defs_for_node() + "\n" + body
    probe = tmp_path / "probe_m2a_cards.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(code)
    return subprocess.run(
        ["node", str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


# ---------------------------------------------------------------- 纯函数层

def test_filter_keeps_whitelisted_and_reports_unknown(tmp_path):
    """白名单过滤：已知字段进 data，未知字段**进 unknown 名单**（不静默丢弃）。"""
    r = _run_node(
        tmp_path,
        """
const f = paCardFilter('approval', {id:'c1', tool:'write_file', target:'data/x.md',
                                   reason:'先看内容', hacker:'<img onerror=1>', admin:true});
if(!f.ok) throw new Error('应通过，理由=' + f.reason);
if(f.data.id !== 'c1' || f.data.target !== 'data/x.md') throw new Error('白名单字段丢失');
if('hacker' in f.data || 'admin' in f.data) throw new Error('未知字段进了 data（会被渲染）');
if(f.unknown.length !== 2 || f.unknown.indexOf('hacker') < 0 || f.unknown.indexOf('admin') < 0)
  throw new Error('未知字段未上报：' + JSON.stringify(f.unknown));
console.log('unknown=' + f.unknown.join(','));
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_unknown_kind_and_missing_required_are_rejected(tmp_path):
    """未知 kind / 缺必填 ⇒ **不渲染**，且拒绝必须带理由（不给默认值兜底）。"""
    r = _run_node(
        tmp_path,
        """
const cases = [['secret', {id:'x'}], ['approval', {tool:'write_file', target:'a.md'}],
               ['artifact', {}], ['block', {reason:'r'}]];
for(const [kind, payload] of cases){
  const f = paCardFilter(kind, payload);
  if(f.ok) throw new Error('应拒绝：' + kind + ' ' + JSON.stringify(payload));
  if(!f.reason) throw new Error('拒绝必须带理由：' + kind);
  if(f.data !== null) throw new Error('拒绝时不得产出 data：' + kind);
}
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_approval_body_renders_only_whitelisted_decisions(tmp_path):
    """决策按钮来自**常量白名单**：未知决策串不得进 DOM；文案必须转义。"""
    r = _run_node(
        tmp_path,
        """
const f = paCardFilter('approval', {id:'c1', target:'data/<x>.md', reason:'<b>危险</b>',
                                   decisions:['approve','reject','evil']});
if(!f.ok) throw new Error('应通过');
const html = PA_CARD_BODY.approval(f.data);
if(html.indexOf('data/&lt;x&gt;.md') < 0) throw new Error('target 未转义渲染：' + html);
if(html.indexOf('&lt;b&gt;危险') < 0) throw new Error('reason 未转义');
if(html.indexOf('evil') >= 0) throw new Error('未知决策串进了 DOM');
const acts = (html.match(/data-act=/g) || []).length;
if(acts !== 2) throw new Error('按钮数应为 2（approve/reject），实际 ' + acts);
console.log('ok acts=' + acts);
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_approval_body_missing_reason_uses_written_text(tmp_path):
    """reason 读不到 ⇒ **写死文案**「等待老板确认：」，不得留空、不得出现 undefined。"""
    r = _run_node(
        tmp_path,
        """
const html = PA_CARD_BODY.approval({target:'data/a.md', decisions:['approve']});
if(html.indexOf('等待老板确认：') < 0) throw new Error('缺 reason 未走写死文案：' + html);
if(html.indexOf('undefined') >= 0 || html.indexOf('null') >= 0)
  throw new Error('缺值被渲染成字面量：' + html);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


# ---------------------------------------------------------------- 静态层

def test_cards_go_to_fixed_container_never_thread():
    """卡片挂固定容器 #paCards；**不散挂 #thread**（批221：写 #thread 会被 renderThread 覆盖）。"""
    s = _src()
    mod = _card_module()
    assert '<div id="paCards" class="pa-cards"' in s
    # #thread 仍是**空容器**：卡片没被塞进去（塞进去就会被 renderThread 重画清掉）
    assert '<div class="thread-view" id="thread"></div>' in s
    assert "getElementById('paCards')" in mod, "必须只从固定容器取挂载点"
    for bad in ("getElementById('thread')", '$(\'thread\')'):
        assert bad not in mod, "卡片模块不得触碰 #thread（会被 renderThread 覆盖）"
    assert "host.appendChild(card)" in mod


def test_no_time_arithmetic_in_card_module():
    """反例钉死：卡片模块不得出现任何时间调用（防前端造倒计时 / 撤销窗口）。"""
    js = _strip_comments(_card_module())
    for bad in _TIME_CALLS:
        assert bad not in js, "卡片模块不得出现 %s（秒数只能由后端给）" % bad


def test_write_card_goes_through_the_single_outlet():
    """审批卡**迁移**（非重写）：renderPaWriteCard 只调 paRenderCard，不自建 DOM。"""
    mod = _card_module()
    i = mod.find("function renderPaWriteCard(pw, note){")
    assert i > 0, "未找到 renderPaWriteCard"
    fn = mod[i:]
    assert "paRenderCard('approval'" in fn, "审批卡未走统一出口"
    assert "appendChild" not in fn and "createElement" not in fn, "审批卡仍在自建 DOM（未迁移）"
    assert "'#thread'" not in fn


def test_unknown_field_is_warned_not_silent():
    """未知字段必须可见（console.warn），不静默丢弃。"""
    mod = _card_module()
    assert "console.warn" in mod
    assert "丢弃未知字段" in mod
    assert "拒绝渲染" in mod


def test_card_removal_syncs_hint_via_single_helper():
    """卡片移除走 paDismissCard（否则「不持久化」提示行会留在页面上）。"""
    s = _src()
    raw = "if(card&&card.parentNode) card.parentNode.removeChild(card);"
    assert s.count(raw) == 1, "原生移除只应出现在 paDismissCard 内（其余走 helper）"
    assert s.count("paDismissCard(card);") == 2, "paWriteDecide 两处移除都应走 helper"


def test_three_kinds_declared_and_non_persist_label_visible():
    """三张卡共用同一出口；「卡片不持久化」必须是**可见 DOM 文案**（不是注释）。"""
    s = _src()
    kinds = re.findall(r"^\s{2}(\w+):\s*\{cls:'pa-\w+-card'", _card_module(), re.M)
    assert kinds == ["approval", "artifact", "block"], "三种 kind 未齐：%r" % kinds
    html = s.split("<script>")[0]
    assert 'id="paCardsHint"' in html and "卡片不持久化" in html, "缺少可见的「不持久化」标注"


def test_pa_state_def_untouched_by_step2():
    """Step 2 边界：状态契约仍 9 键（``blocked`` 属 Step 3，只增不改）。"""
    m = re.search(r"const PA_STATE_DEF = \{(.*?)\n\};", _src(), re.S)
    assert m, "未找到 PA_STATE_DEF"
    keys = re.findall(r"^\s*(\w+):\s*\{ic:", m.group(1), re.M)
    assert len(keys) == 9, "既有 9 态被改动：%r" % keys
    assert "blocked" not in keys