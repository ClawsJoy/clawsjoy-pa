# -*- coding: utf-8 -*-
"""M2-A · Step 3.2 产物卡验收（``web/pa.html`` + 统一出口 host 参数）。

设计稿：``codex/2026-09-17-v9pes-m2a-visibility-closure-design.md`` §2.2 / §6 Step 3 / §15。

三层判据，**都不靠自觉**：

1. **纯函数层**（node 跑从真实 pa.html 抽出的定义，**move 而非 retype**）：
   探测负载 ⇒ 默认态「未经核验」+「来源：正文探测（非核验）」；未知来源**不猜**；
   未知 `exists` **不得**渲染成「不存在」；`claimed` **不得**升级；空 sha256/bytes **不显示该行**。
2. **静态层**：``renderOutputCard`` 只经 ``paRenderCard('artifact', …, host)`` 进 DOM（不再自建 DOM）；
   显式宿主只允许产物卡传给 ``#thread``（消息内联 + 批201 F5 重建语义）；
   ``.output-card`` alias 保留（CSS 与既有选择器不破）。
3. **契约层**：产物卡**不得**出现「已生成」这类完成断言 —— 完成只有后端 ``contract.verdict()`` 能给。

独立运行的临时 js 走 ``tmp_path``；本文件不改任何产品代码。
"""
from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 拆面（承 pm 1334 §三.1 · 惟改径 ＋ 并读 · §二.1「出处之判须以『其物在何处』为据 ⇒ 页面 ＝ 壳 ＋ 支」）：
#   卡块 ＝ faces/cards.js；容器 ／ 提示行 ＝ 壳 web/pa.html；`esc` ＝ faces/session.js；
#   旧选择器 `.output-card` ＝ faces/products.js；卡样式 ＝ pa.css。
PA = (ROOT / "web" / "pa.html",
      ROOT / "web" / "pa" / "faces" / "cards.js",
      ROOT / "web" / "pa" / "faces" / "session.js",
      ROOT / "web" / "pa" / "faces" / "products.js",
      ROOT / "web" / "pa" / "pa.css")

#: 卡片模块区域（统一出口 + 迁移后的卡）
_MOD_START = "const PA_CARD_DEF = {"
_MOD_END = "async function paWriteDecide("

#: 产物卡 body 的源码切片（静态判据用）
_ART_START = "  artifact:function(d){"
_ART_END = "  /* M2-A · Step 3.1：阻断卡"


def _src() -> str:
    return "\n".join(io.open(f, encoding="utf-8").read() for f in PA)


def _card_module() -> str:
    s = _src()
    i = s.find(_MOD_START)
    j = s.find(_MOD_END, i)
    assert i > 0 and j > i, "未找到卡片模块区域"
    return s[i:j]


def _artifact_body_src() -> str:
    s = _src()
    i = s.find(_ART_START)
    j = s.find(_ART_END, i)
    assert i > 0 and j > i, "未找到产物卡 body 区域"
    return s[i:j]


def _defs_for_node() -> str:
    """从真实 pa.html 抽定义（move 而非 retype）+ 最小 DOM stub（仅供 esc 用）。"""
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
    probe = tmp_path / "probe_artifact.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(code)
    return subprocess.run(
        ["node", str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


# ---------------------------------------------------------------- 纯函数层

def test_probe_payload_is_unverified_by_default(tmp_path):
    """探测负载（只有 path + 来源）⇒ 默认态「未经核验」；未知**不得**写成「存在」。"""
    r = _run_node(
        tmp_path,
        """
const f = paCardFilter('artifact', {path:'data/reports/a.md', reported_source:'text_probe'});
if(!f.ok) throw new Error('应通过：' + f.reason);
if(f.unknown.length) throw new Error('不该有未知字段：' + JSON.stringify(f.unknown));
const html = PA_CARD_BODY.artifact(f.data);
for(const s of ['未经核验','来源：正文探测（非核验）','磁盘实况：未核验','未经验证者签署',
                '没有契约，无法裁决完成','data/reports/a.md','a.md'])
  if(html.indexOf(s) < 0) throw new Error('缺事实：' + s + ' => ' + html);
for(const bad of ['已生成','存在','不存在','undefined','null'])
  if(html.indexOf(bad) >= 0) throw new Error('不得出现 ' + bad + '：' + html);
if(html.indexOf('内容指纹') >= 0) throw new Error('sha256/bytes 空 ⇒ 不该渲染指纹行：' + html);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_unknown_source_is_not_guessed(tmp_path):
    """来源缺失/未知 ⇒ 「未记录（按未经核验处理）」—— 受控词表，不猜、不美化。"""
    r = _run_node(
        tmp_path,
        """
const cases = [{path:'x.md'}, {path:'x.md', reported_source:'backend_says_ok'},
               {path:'x.md', reported_source:null}];
for(const p of cases){
  const f = paCardFilter('artifact', p);
  if(!f.ok) throw new Error('应通过：' + JSON.stringify(p) + ' / ' + f.reason);
  const html = PA_CARD_BODY.artifact(f.data);
  if(html.indexOf('来源：未记录（按未经核验处理）') < 0)
    throw new Error('未知来源未按未记录处理：' + JSON.stringify(p) + ' => ' + html);
  if(html.indexOf('正文探测') >= 0)
    throw new Error('未知来源被美化成正文明文探测：' + JSON.stringify(p));
}
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_backend_facts_rendered_and_claimed_not_upgraded(tmp_path):
    """后端事实原样渲染；``claimed`` 原样显示为「agent 自报，未验证」，**不得**升级。"""
    r = _run_node(
        tmp_path,
        """
const f = paCardFilter('artifact', {path:'data/reports/b.md', exists:true,
  sha256:'0123456789abcdef0123456789abcdef', bytes:1234, verified_by:'',
  done_when_status:'claimed',
  verdict:{state:'not_done', reason:'claimed_only', next_action:'由独立验证者写入 artifact_verified_by'}});
if(!f.ok) throw new Error('应通过：' + f.reason);
const html = PA_CARD_BODY.artifact(f.data);
for(const s of ['存在（后端 record_artifact 判定）','0123456789ab…','1234 字节',
                '未经验证者签署','agent 自报，未验证（claimed）','not_done（claimed_only）',
                '下一步：由独立验证者写入 artifact_verified_by','未经核验'])
  if(html.indexOf(s) < 0) throw new Error('缺事实：' + s + ' => ' + html);
if(html.indexOf('已生成') >= 0) throw new Error('出现完成断言「已生成」：' + html);
if(html.indexOf('已核验') >= 0) throw new Error('claimed 被升级成「已核验」：' + html);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_null_exists_is_unknown_not_absence(tmp_path):
    """``exists`` 显式 null（未知）⇒ 「未核验」，**不得**渲染成「不存在」（P1 未知即未知）。"""
    r = _run_node(
        tmp_path,
        """
const f = paCardFilter('artifact', {path:'x.md', exists:null});
if(!f.ok) throw new Error('应通过：' + f.reason);
const html = PA_CARD_BODY.artifact(f.data);
if(html.indexOf('磁盘实况：未核验') < 0) throw new Error('未知 exists 未写「未核验」：' + html);
if(html.indexOf('不存在') >= 0) throw new Error('未知 exists 被渲染成「不存在」：' + html);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_body_has_only_download_and_expand_no_inline_onclick(tmp_path):
    """产物卡按钮只有 下载/展开 两个，且**不带内联 onclick**（绑定走 PA_CARD_BIND）。"""
    r = _run_node(
        tmp_path,
        """
const html = PA_CARD_BODY.artifact({path:'data/reports/c.md', reported_source:'text_probe'});
const acts = html.match(/data-act="(\\w+)"/g) || [];
if(acts.length !== 2) throw new Error('按钮数应为 2，实际 ' + acts.length + '：' + html);
if(html.indexOf('data-act="download"') < 0 || html.indexOf('data-act="toggle"') < 0)
  throw new Error('缺下载/展开按钮：' + html);
if(html.indexOf('onclick') >= 0) throw new Error('产物卡出现内联 onclick：' + html);
for(const bad of ['重试','确认','approve','reject'])
  if(html.indexOf(bad) >= 0) throw new Error('产物卡不得带决策动作 ' + bad + '：' + html);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


# ---------------------------------------------------------------- 静态层

def test_render_output_card_goes_through_single_outlet():
    """产物卡**迁移**（非重写）：renderOutputCard 只调 paRenderCard，不自建 DOM。"""
    s = _src()
    i = s.find("async function renderOutputCard(path){")
    j = s.find("function downloadOutput(btn){", i)
    assert 0 < i < j, "未找到 renderOutputCard"
    fn = s[i:j]
    assert "paRenderCard('artifact'" in fn, "产物卡未走统一出口"
    for bad in ("createElement(", "appendChild(", "className='output-card'"):
        assert bad not in fn, "产物卡仍在自建 DOM（未迁移）：%s" % bad
    assert fn.count("$('thread')") == 2, "宿主读写各一次（显式传入 + 滚动到底）：%r" % fn
    assert "}, $('thread'))" in fn, "宿主未作为出口第三参显式传入：%r" % fn
    assert "/v9/sandbox/read" in fn, "正文读取接口被改动"
    assert "return renderPptWall(path)" in fn, "pptx 分流被改动（本步不迁 pptx 墙）"


def test_only_artifact_card_gets_explicit_host_and_default_is_paCards():
    """出口新增可选 host：默认仍是 #paCards；卡片模块自身**仍不得触碰 #thread**。"""
    mod = _card_module()
    assert "function paRenderCard(kind, payload, host){" in mod, "出口签名缺 host 参数"
    assert "document.getElementById('paCards')" in mod, "默认容器被改动"
    for bad in ("getElementById('thread')", "$('thread')"):
        assert bad not in mod, "卡片模块不得触碰 #thread"
    s = _src()
    host_calls = re.findall(r"paRenderCard\('artifact', \{[^\n]*", s)
    assert len(host_calls) == 1, "产物卡出口调用应恰好 1 处（非注释）：%r" % host_calls
    assert host_calls[0].rstrip().endswith("$('thread'));"), "产物卡未显式传宿主 #thread：%r" % host_calls[0]


def test_legacy_output_card_class_is_kept_as_alias():
    """兼容层：产物卡仍挂 ``.output-card``（CSS 与既有选择器不破）。"""
    s = _src()
    assert "alias:'output-card'" in s, "缺 alias，旧 CSS/选择器会断"
    assert "card.className=def.cls+(def.alias?(' '+def.alias):'');" in s, "出口未应用 alias"
    assert "btn.closest('.output-card')" in s, "downloadOutput 的旧选择器被改动"
    art = _artifact_body_src()
    for cls in ('class="oc-head"', 'class="oc-name"', 'class="oc-path"', 'class="oc-body"'):
        assert cls in art, "产物卡丢掉了既有 CSS 类名：%s" % cls


def test_hint_scopes_itself_to_paCards_family():
    """「不持久化」提示必须**只声明 #paCards 卡族**（产物卡是消息内联、F5 后重建）。"""
    s = _src()
    i = s.find('id="paCardsHint"')
    assert i > 0, "缺提示行"
    line = s[i : s.find("</div>", i)]
    assert "卡片不持久化" in line
    assert "此处" in line and "产物卡不在此列" in line, "提示行未按卡族分区（会误伤产物卡的 F5 语义）：%r" % line


def test_artifact_css_rules_present():
    """产物卡自有样式（核验徽标 / 事实行 / 正文说明）在位。"""
    s = _src()
    for rule in (".pa-artifact-card .oac-ver{", ".pa-artifact-card .oac-meta{",
                 ".pa-artifact-card .oac-note{"):
        assert rule in s, "缺 CSS：%s" % rule
