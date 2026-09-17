# -*- coding: utf-8 -*-
"""M2-A · Step 3.1 阻断卡验收（后端字段接线 + 前端渲染 + 语义修正）。

设计稿：``codex/2026-09-17-v9pes-m2a-visibility-closure-design.md`` §2.3 / §6 Step 3.1。

三层判据：

1. **后端（只读）**：``blocked.{layer,blocked_action,evidence_ref}`` 从注册表行 + audit 流**实测取到**；
   ``unblock_hint`` **只透传**来源写入值 —— **投影层不调 ``Authorizer.explain()``**
   （实测 ``CapabilityRegistry.ensure_seeded()`` 会写注册表 ⇒ 违反 P3），取不到即 ``null``（不代填）。
2. **前端**：阻断卡三不许 —— 不渲染成 ``tool`` 态 / 不给「重试」按钮 / 不隐藏 ``unblock_hint`` 缺失。
3. **契约**：``PA_STATE_DEF`` **只增** ``blocked``（既有 9 键顺序与取值**一字未改**）。
"""
from __future__ import annotations

import ast
import io
import re
import subprocess
from pathlib import Path

from core.pa.pes_projection import project_runs
from core.pes.audit import AuditLog
from core.pes.run_registry import RunRegistry

ROOT = Path(__file__).resolve().parents[2]
PA = ROOT / "web" / "pa.html"
_PROJ = ROOT / "core" / "pa" / "pes_projection.py"

#: 既有 9 键（Step 0/2 时的冻结值）——Step 3 只允许**追加**，不允许改名/改值/换序
_ORIGINAL_9 = [
    ("idle", "○", "就绪", "st-idle"),
    ("running", "▶", "正在执行", "st-run"),
    ("model", "⏳", "等待模型", "st-wait"),
    ("tool", "🔧", "等待工具", "st-wait"),
    ("approval", "✋", "等待审批", "st-appr"),
    ("verifying", "🔍", "验证中", "st-run"),
    ("done", "✅", "已完成", "st-ok"),
    ("failed", "❌", "已失败", "st-err"),
    ("stopped", "⏹", "已停止", "st-err"),
]


def _src() -> str:
    return io.open(PA, encoding="utf-8").read()


def _card_module() -> str:
    s = _src()
    i = s.find("const PA_CARD_DEF = {")
    j = s.find("function paDismissCard(card){", i)
    assert i > 0 and j > i, "未找到卡片模块区域"
    return s[i:j]


def _strip_comments(js: str) -> str:
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"^\s*//.*$", "", js, flags=re.M)


# ------------------------------------------------------------------ 后端

def _reg(pes_dir):
    return RunRegistry(pes_dir / "runs.jsonl")


def _blocked_row(pes_dir, run_id="run-b1", **last_error):
    reg = _reg(pes_dir)
    reg.register_run(run_id, session_id="s1", user_id="u1")
    reg.update_from_source(run_id, {"state": "blocked", "last_error": dict(last_error)})
    return reg


def _project(pes_dir, **kw):
    audit = AuditLog(pes_dir / "audit.jsonl")
    return project_runs(runs_path=pes_dir / "runs.jsonl", contracts_dir=pes_dir / "contracts",
                        audit=audit, **kw)


def test_blocked_fields_wired_from_row_and_audit(pes_dir):
    """注册表行 + audit 流 ⇒ 阻断卡字段实测取到；evidence_ref 用**审计链 seq**（不是行号）。"""
    _blocked_row(pes_dir, layer="Execution Contract", message="未 seed ⇒ 不得盘点",
                 tool="write_file")
    audit = AuditLog(pes_dir / "audit.jsonl")
    audit.record_for_run("pes.blocked", "run-b1", layer="Execution Contract")
    out = project_runs(runs_path=pes_dir / "runs.jsonl", contracts_dir=pes_dir / "contracts",
                       audit=audit)
    b = out["runs"][0]["blocked"]
    assert b["block_id"] == "run-b1"
    assert b["layer"] == "Execution Contract"
    assert b["reason"] == "未 seed ⇒ 不得盘点"
    assert b["blocked_action"] == "write_file"
    assert b["state_map_key"] == "blocked"
    assert b["evidence_ref"] == audit.path.as_posix() + "#seq=1"
    assert b["blocked_at"] is not None, "heartbeat_at 应被投影为 blocked_at"
    # **不代填**：来源没写 unblock_hint ⇒ 就是 null（不是默认文案）
    assert b["unblock_hint"] is None


def test_unblock_hint_is_passthrough_only(pes_dir):
    """``unblock_hint`` 只透传来源写入值（投影层不调 Authorizer.explain）。"""
    _blocked_row(pes_dir, message="需要老板授权", unblock_hint="在权限页授予 agent 级权限后重试")
    b = _project(pes_dir)["runs"][0]["blocked"]
    assert b["unblock_hint"] == "在权限页授予 agent 级权限后重试"


def test_blocked_absent_for_non_blocked_run(pes_dir):
    """非 blocked 的运行 ⇒ 没有阻断卡（宁缺勿假）。"""
    reg = _reg(pes_dir)
    reg.register_run("run-r1", session_id="s1")
    reg.update_from_source("run-r1", {"state": "running"})
    assert _project(pes_dir)["runs"][0]["blocked"] is None


#: 只读投影**禁止调用**的名字（ast 判据，不被注释/文档字符串误伤）
_BANNED_CALLS = {
    "explain", "ensure_seeded", "update_runtime", "record", "record_for_run", "register_run",
    "update_from_source", "verify_artifact", "record_artifact", "mark_claimed", "reduce",
    "reconcile", "hold", "release", "_append", "write_text", "write_bytes", "mkdir", "unlink",
    "touch", "rename", "save",
}


def test_projection_never_calls_hint_authority():
    """P3 加固：只读投影**不得**调 ``Authorizer.explain`` 或任何写接口（含 ``ensure_seeded``）。

    用 **AST** 而不是子串匹配 —— 模块 docstring 里**解释**「为什么不调 ``explain``」是合法的。
    """
    tree = ast.parse(_PROJ.read_text(encoding="utf-8"))
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
        if isinstance(node, ast.Name):
            assert node.id != "Authorizer", "只读投影不得引用 Authorizer"
    assert not (called & _BANNED_CALLS), "只读投影调用了越界函数：%r" % sorted(called & _BANNED_CALLS)


# ------------------------------------------------------------------ 前端（纯函数）

def _run_node(tmp_path, body):
    code = _defs()
    probe = tmp_path / "probe_block.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(code + "\n" + body)
    return subprocess.run(["node", str(probe)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _defs() -> str:
    s = _src()
    out = []
    i = s.find("function esc(s){")
    out.append(s[i : s.find("\n", i)])
    for head, tail in (("const PA_CARD_DEF = {", "\n};"),
                       ("function paCardFilter(kind, payload){", "\n}"),
                       ("const PA_CARD_BODY={", "\n};"),
                       ("const PA_CARD_ACTS={", "\n")):
        i = s.find(head)
        assert i > 0, "未找到 " + head
        j = s.find(tail, i)
        assert j > i
        out.append(s[i : j + len(tail)])
    stub = ("global.document={createElement:function(){var o={_t:'',"
            "set textContent(v){this._t=String(v==null?'':v);},"
            "get innerHTML(){return this._t.replace(/&/g,'&amp;').replace(/</g,'&lt;')"
            ".replace(/>/g,'&gt;');}};return o;}};")
    return stub + "\n" + "\n".join(out)


def test_block_body_renders_whitelisted_facts_without_actions(tmp_path):
    """阻断卡渲染白名单事实；**不带任何动作按钮**（不许把「重试」当万能解）。"""
    r = _run_node(tmp_path, """
const b = paCardFilter('block', {block_id:'run-b1', blocked_at:'2026-09-18 10:00:00',
  layer:'Execution Contract', reason:'未 seed ⇒ 不得盘点/修改/产出结论',
  blocked_action:'write_file data/x.md', evidence_ref:'audit.jsonl#seq=7',
  unblock_hint:'先 seed 再重试', state_map_key:'blocked', extra:'<b>注入</b>'});
if(!b.ok) throw new Error('应通过：' + b.reason);
if(b.unknown.length !== 1 || b.unknown[0] !== 'extra') throw new Error('未知字段未上报');
const html = PA_CARD_BODY.block(b.data);
for(const s of ['run-b1','Execution Contract','未 seed ⇒ 不得盘点/修改/产出结论',
                'write_file data/x.md','audit.jsonl#seq=7','先 seed 再重试','2026-09-18 10:00:00'])
  if(html.indexOf(s) < 0) throw new Error('缺事实：' + s);
if(html.indexOf('extra') >= 0) throw new Error('未知字段进了 DOM');
if(/<button|data-act/.test(html)) throw new Error('阻断卡不得带动作按钮：' + html);
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_block_body_speaks_missing_facts(tmp_path):
    """读不到就**明说**：原因未记录 / 无替代路径（未记录）；不得出现 undefined/null 字面量。"""
    r = _run_node(tmp_path, """
const html = PA_CARD_BODY.block({block_id:'b2'});
if(html.indexOf('原因未记录') < 0) throw new Error('缺原因未明说：' + html);
if(html.indexOf('无替代路径（未记录）') < 0) throw new Error('缺替代路径未明说：' + html);
if(html.indexOf('未知层') < 0) throw new Error('缺层未明说：' + html);
if(/undefined|null/.test(html.replace(/无替代路径（未记录）/g,''))) throw new Error('渲染出字面量：' + html);
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


# ------------------------------------------------------------------ 前端（静态）

def test_state_def_only_appended_blocked():
    """``PA_STATE_DEF``：既有 9 键**顺序与取值一字未改**，``blocked`` 追加在尾部（只增不改）。"""
    m = re.search(r"const PA_STATE_DEF = \{(.*?)\n\};", _src(), re.S)
    assert m, "未找到 PA_STATE_DEF"
    got = re.findall(r"(\w+):\s*\{ic:'([^']*)',\s*label:'([^']*)',\s*cls:'([^']*)'\}", m.group(1))
    assert got[:9] == _ORIGINAL_9, "既有 9 键被改动：%r" % (got[:9],)
    assert len(got) == 10, "应恰好新增 1 键：%r" % (got[9:],)
    assert got[9] == ("blocked", "⛔", "已阻断", "st-block")
    assert ".runstate.st-block{" in _src(), "st-block 样式缺失"


def test_blocked_state_not_rendered_as_tool():
    """语义修正：L4 拦截分支用 ``blocked`` 态，**不再借 tool 态**（设计稿 §2.3 之①）。"""
    s = _src()
    i = s.find("if(_res&&_res.blocked){")
    assert i > 0, "未找到 _res.blocked 分支"
    j = s.find("else if(_res&&_res.pending){", i)
    seg = s[i:j]
    assert "paSetState('blocked'" in seg, "阻断未进 blocked 态"
    assert "paSetState('tool'" not in seg, "阻断仍借 tool 态显示（§2.3 之①）"
    assert "paRenderCard('block'" in seg, "未渲染阻断卡"


def test_pes_block_loader_is_read_only_and_honest():
    """投影消费：只 GET /v9/pes/runs；取不到 ⇒ 只 warn（不渲染假卡、不冒充「无阻断」）。"""
    s = _src()
    i = s.find("async function paLoadPesBlocks(){")
    assert i > 0, "未找到 paLoadPesBlocks"
    j = s.find("function renderPaWriteCard(", i)
    fn = s[i:j]
    assert "/v9/pes/runs" in fn
    assert "method:'POST'" not in fn and "POST" not in fn, "只读消费不得有写请求"
    assert "getElementById('thread')" not in fn, "卡片不得写 #thread"
    assert "不渲染任何阻断卡" in fn and "不视为「全绿」" in fn, "缺「取不到/空库不当全绿」的诚实分支"
    assert 'console.warn' in fn
    assert '_boot("paLoadPesBlocks", paLoadPesBlocks);' in s, "未在启动流程注册"
    assert "deg.forEach" in fn, "降级信号未上报"


def test_block_module_has_no_time_calls():
    """卡片模块仍不得出现时间调用（阻断时刻只能来自后端）。"""
    js = _strip_comments(_card_module())
    for bad in ("Date.now(", "new Date(", "setInterval(", "getTime("):
        assert bad not in js, "卡片模块不得出现 %s" % bad