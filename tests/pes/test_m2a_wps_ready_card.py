# -*- coding: utf-8 -*-
"""M2A-07 ②-1 验收：WPS 就绪卡**并入统一出口**（``web/pa.html`` · DS 2026-09-18 拍）。

拍板要点：①pptx 墙宿主保持 ``#thread``（本次不迁）②先立口径「``PA_CARD_BODY`` 纯同步无时间 /
挂载可异步但不得造事实行与时间」（本步用不到）③缩略图产生链不动 ④去重键 = ``tool``
⑤保留「桥就绪 ⇒ 引导卡自动消失」语义、改由 ``paDismissCard`` 执行。

判据（**不靠自觉**）：

1. **不自建 DOM、不散挂 ``#thread``**：``paWpsReadyCardRender`` 只调 ``paRenderCard('wps_ready'``，
   且旧的 ``#paWpsCard`` 单例 DOM 已彻底移除；
2. **清除只走 helper**：``paWpsReadyCardClear`` 只调 ``paDismissCard``；全仓原生 ``removeChild(`` 仅一处；
3. **四处登记齐**：``PA_CARD_DEF`` / ``PA_CARD_BODY`` / ``PA_CARD_BIND`` / ``PA_CARD_PERSIST_NOTE``；
4. **白名单有牙**：未知字段 ⇒ ``unknown`` 非空且**不进** ``data``；缺 ``tool`` ⇒ 拒绝渲染；
5. **不代填**：无产物路径 ⇒ 「本次未取到产物路径」且**不得**出现「产物已生成」；有路径 ⇒ 原样显示；
6. **按钮不内联 onclick**：走 ``data-act="copy"`` + ``PA_CARD_BIND`` 绑定；
7. **反空转下限**（``L-18``）：步骤数 ≥3、模板必须产出 ``wpscard``/``wpssteps``/``wpscopy``/三态串；
8. **接线承重**：调用点必须传**真实工具名**（去重键）。

独立运行的临时 js 走 ``tmp_path``；本文件不改任何产品代码。
"""
from __future__ import annotations

import io
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 拆面（承 pm 1334 §三.1 · 惟改径 ＋ 并读）：批次块 ／ `esc` ／ 就绪卡渲染 ＝ faces/session.js；
#   四表（PA_CARD_DEF ／ BODY ／ BIND ／ PERSIST_NOTE）＝ faces/cards.js；
#   调用点（`paWpsReadyCardRender(s.tool, …)`）＝ faces/send.js。
PA = (ROOT / "web" / "pa" / "faces" / "session.js",
      ROOT / "web" / "pa" / "faces" / "cards.js",
      ROOT / "web" / "pa" / "faces" / "send.js")

_WPS_BLOCK_BEGIN = "批183 · C3/C1：WPS 灵犀未就绪的降级与引导（纯函数块 BEGIN"
_WPS_BLOCK_END = "批183 · 纯函数块 END"


def _src() -> str:
    return "\n".join(io.open(f, encoding="utf-8").read() for f in PA)


def _fn(name: str) -> str:
    s = _src()
    i = s.find("function %s(" % name)
    assert i > 0, "未找到函数 " + name
    j = s.find("\n}", i)
    assert j > i, "未找到函数 " + name + " 的结尾"
    return s[i : j + 2]


def _table(head: str) -> str:
    s = _src()
    i = s.find("const " + head)
    assert i > 0, "未找到 " + head
    j = s.find("\n};", i)
    assert j > i, "未找到 " + head + " 的结尾"
    return s[i:j]


def _defs_for_node() -> str:
    """从真实 pa.html 抽定义（move 而非 retype）+ 最小 DOM stub（仅供 esc 用）。"""
    s = _src()
    out = []
    i = s.find("function esc(s){")
    assert i > 0, "未找到 esc"
    out.append(s[i : s.find("\n", i)])
    i = s.find(_WPS_BLOCK_BEGIN)
    j = s.find(_WPS_BLOCK_END, i)
    assert i > 0 and j > i, "未找到批183 纯函数块（标记被改动？）"
    out.append(s[s.rfind("/*", 0, i) : s.find("\n", j)])
    for head, tail in (
        ("const PA_CARD_DEF = {", "\n};"),
        ("function paCardFilter(kind, payload){", "\n}"),
        ("const PA_CARD_BODY={", "\n};"),
        ("const PA_CARD_ACTS={", "\n"),
        ("const PA_CARD_PERSIST_NOTE = {", "\n};"),
    ):
        k = s.find(head)
        assert k > 0, "未找到 " + head
        m = s.find(tail, k)
        assert m > k, "未找到 " + head + " 的结尾"
        out.append(s[k : m + len(tail)])
    stub = (
        "global.document={createElement:function(){var o={_t:'',"
        "set textContent(v){this._t=String(v==null?'':v);},"
        "get innerHTML(){return this._t.replace(/&/g,'&amp;').replace(/</g,'&lt;')"
        ".replace(/>/g,'&gt;');}};return o;}};\n"
    )
    return stub + "\n".join(out)


def _run_node(tmp_path, body):
    code = _defs_for_node() + "\n" + body
    probe = tmp_path / "probe_wps_ready.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(code)
    return subprocess.run(
        ["node", str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


# ---------------------------------------------------------------- 静态层

def test_ready_card_goes_through_the_single_outlet():
    """就绪卡**迁移**（非重写）：只调 paRenderCard，不自建 DOM、不散挂 #thread。"""
    fn = _fn("paWpsReadyCardRender")
    assert "paRenderCard('wps_ready'" in fn, "就绪卡未走统一出口"
    for bad in ("createElement", "appendChild", "getElementById('thread')", "'#thread'"):
        assert bad not in fn, "就绪卡仍在自建 DOM / 散挂 #thread：%s" % bad
    assert "paWpsCard" not in _src(), "旧的 #paWpsCard 单例 DOM 未清除"


def test_clear_goes_through_shared_helper_and_no_raw_removal_left():
    """清除走 paDismissCard（否则「不持久化」提示行会留在页面上）。

    去重键是 ``tool`` ⇒ 同时**可能有多张**就绪卡（多个工具各一张）⇒ 清除必须**全清**
    （``querySelectorAll``）；只清第一张会留残卡，与「桥就绪 ⇒ 引导卡自动消失」语义不符。
    """
    fn = _fn("paWpsReadyCardClear")
    assert "paDismissCard(" in fn, "清除未走 helper"
    assert "removeChild" not in fn, "清除仍在自建移除"
    assert "querySelectorAll" in fn, "清除未全清（多工具各一张时会留残卡）"
    assert "querySelector(" not in fn, "仍在用单元素选择器（只清一张）"
    assert _src().count("removeChild(") == 1, "全仓原生移除只应出现在 paDismissCard 内"


def test_kind_is_registered_in_all_four_tables():
    """新增 kind ⇒ 四张表都必须登记（PERSIST_NOTE 那张由既有判据钉住键集一致）。"""
    s = _src()
    for head in ("PA_CARD_DEF = {", "PA_CARD_BODY={", "PA_CARD_BIND={", "PA_CARD_PERSIST_NOTE = {"):
        i = s.find("const " + head)
        assert i > 0, "未找到 " + head
        j = s.find("\n};", i)
        assert j > i
        assert "wps_ready" in s[i:j], head + " 未登记 wps_ready"


def test_dedup_key_is_tool():
    """DS 拍：去重键 = ``tool``（同名工具同时只该有一张就绪卡）。"""
    tbl = _table("PA_CARD_DEF = {")
    i = tbl.find("wps_ready:")
    assert i > 0, "PA_CARD_DEF 未登记 wps_ready"
    seg = tbl[i : tbl.find("}", i)]
    assert "required:['tool']" in seg.replace(" ", ""), "去重键必须恰好是 tool：%r" % seg


def test_call_site_passes_real_tool_name():
    """接线承重：调用点必须传真实工具名（否则去重键为空 ⇒ 卡片被拒）。"""
    assert "paWpsReadyCardRender(s.tool, _res.hint, _vis.artifact, _vis);" in _src(), "调用点未传工具名"


# ---------------------------------------------------------------- 纯函数层

def test_whitelist_has_teeth(tmp_path):
    r = _run_node(tmp_path, """
const f = paCardFilter('wps_ready', {tool:'wps_office', hint:'h', bogus:1, other:'x'});
if(!f.ok) throw new Error('合法载荷被拒：' + f.reason);
if(f.unknown.join(',') !== 'bogus,other') throw new Error('未知字段未如实报出：' + f.unknown.join(','));
if(f.data.hint !== 'h') throw new Error('白名单字段丢了');
if(f.data.bogus !== undefined || f.data.other !== undefined) throw new Error('未知字段混进了 data');
const bad = paCardFilter('wps_ready', {hint:'h'});
if(bad.ok) throw new Error('缺 tool 未拒绝渲染（去重键不可缺）');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_no_substitution_of_facts(tmp_path):
    r = _run_node(tmp_path, """
const none = PA_CARD_BODY.wps_ready({tool:'wps_office', hint:'h', artifact_path:''});
if(none.indexOf('本次未取到产物路径') < 0) throw new Error('未取到路径时未如实说明');
if(none.indexOf('产物已生成') >= 0) throw new Error('未取到路径却出现完成断言');
const has = PA_CARD_BODY.wps_ready({tool:'wps_office', artifact_path:'data/reports/x.pptx'});
if(has.indexOf('data/reports/x.pptx') < 0) throw new Error('有路径时未原样显示');
if(has.indexOf('产物已生成') >= 0) throw new Error('卡片出现完成断言（完成只有后端 verdict 能给）');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_button_is_bound_not_inline(tmp_path):
    r = _run_node(tmp_path, """
const html = PA_CARD_BODY.wps_ready({tool:'t', hint:'h'});
if(html.indexOf('onclick') >= 0) throw new Error('就绪卡按钮仍带内联 onclick（绑定必须走 PA_CARD_BIND）');
if(html.indexOf('data-act="copy"') < 0) throw new Error('复制按钮缺 data-act="copy"');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout
    seg = _table("PA_CARD_BIND={")
    i = seg.find("wps_ready:")
    assert i > 0, "PA_CARD_BIND 未登记 wps_ready"
    assert "addEventListener" in seg[i:], "PA_CARD_BIND.wps_ready 未绑定事件"


def test_no_air_spin_floor(tmp_path):
    """反空转下限（L-18）：步骤数 ≥3，且模板必须产出真实的就绪卡结构。"""
    r = _run_node(tmp_path, """
if(!(PA_WPS_STEPS.length >= 3)) throw new Error('步骤数异常（模板恐已空转）：' + PA_WPS_STEPS.length);
const html = PA_CARD_BODY.wps_ready({tool:'t', hint:'h', task_status:'BLOCKED',
  preview_status:'PENDING', completion_status:'NOT_COMPLETE'});
for(const need of ['wpscard','wpssteps','wpscopy','BLOCKED','PENDING','NOT_COMPLETE']){
  if(html.indexOf(need) < 0) throw new Error('模板缺少 ' + need + '（空转？）');
}
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_backend_hint_is_escaped(tmp_path):
    """后端 ``hint`` 是自由文本 ⇒ 必须转义后才进 HTML（不引入注入面）。"""
    r = _run_node(tmp_path, """
const html = PA_CARD_BODY.wps_ready({tool:'t', hint:'<img src=x onerror=alert(1)>'});
if(html.indexOf('<img') >= 0) throw new Error('hint 未转义（注入面）');
if(html.indexOf('&lt;img') < 0) throw new Error('hint 未按转义形态渲染');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout
