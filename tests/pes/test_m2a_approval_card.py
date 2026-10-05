# -*- coding: utf-8 -*-
"""M2-A · Step 3.3 审批卡接线验收（方案 A · 后端快照，**前端不算时间**）。

设计稿：``codex/2026-09-18-m2a-step33-approval-card-plan.md``（老板/DS 拍 **A**）。
方案 A 的定义：**在响应组装点现算 `expires_in_s`**，前端只把后端给的数字转成文本。

判据（**不靠自觉**）：

1. **后端唯一时间源**：``expires_in_s = int(write_gate._PENDING_TTL - (now - ts))``，
   秒数**不得写死**（旧口径 60s 已作废，真值见常量）；
2. **未知即未知**：取不到 ts / ts 非法 ⇒ ``None``，**不得兜底成 0**
   （``0`` 会被读成「已过期」⇒ 用户放弃仍有效的审批 = **假拒绝**，与 X-08 同族）；
3. **零污染**：视图是**副本**，不改 ``_pending_writes`` 结构、不新增持久化字段
   （否则会进 ``.agent_state.json``）；
4. **撤销窗口只透传**：``HoldQueue.visibility()`` 今天恒 ``{show: False}``
   （写审批**未接 hold**，产品侧 0 调用点）⇒ 前端**只在 show=true 时**渲染，
   **不暗示一个不存在的窗口**；
5. **三选项按钮语义不动**（``PA_CARD_ACTS`` 原样）。

独立运行的临时 js 走 ``tmp_path``；本文件不改任何产品代码。
"""
from __future__ import annotations

import io
import json
import subprocess
import time
from pathlib import Path

from core.gateway.v9_bridge.tool_runner import _pending_card_view
from core.gateway.write_gate import _PENDING_TTL

ROOT = Path(__file__).resolve().parents[2]
# ⭐ 拆件（承 pm 18:08 §三 · 惟改径）：原 `web/pa.html` 单体已拆 ⇒
#   卡片模块之新家 ＝ `web/pa/faces/cards.js`；`esc()` 之新家 ＝ `web/pa/faces/session.js`。
#   —— 惟改「径」：⏔ 改断言 ／ ⏔ 改被测件以就测。
PA = (ROOT / "web" / "pa" / "faces" / "cards.js",
      ROOT / "web" / "pa" / "faces" / "session.js")
TOOL_RUNNER = ROOT / "core" / "gateway" / "v9_bridge" / "tool_runner.py"

_MOD_START = "const PA_CARD_DEF = {"
_MOD_END = "async function paWriteDecide("


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
    probe = tmp_path / "probe_approval_card.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(_defs_for_node() + "\n" + body)
    return subprocess.run(
        ["node", str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


# ---------------------------------------------------------------- 后端视图层

def test_expires_in_s_derives_from_the_ttl_constant():
    """剩余秒数来自 ``_PENDING_TTL``（唯一源），且随 ts 递减。"""
    now = time.time()
    fresh = _pending_card_view({"id": "tc1", "ts": now})
    half = _pending_card_view({"id": "tc2", "ts": now - 150})
    assert isinstance(fresh["expires_in_s"], int)
    assert _PENDING_TTL - 3 <= fresh["expires_in_s"] <= _PENDING_TTL, fresh["expires_in_s"]
    assert _PENDING_TTL - 153 <= half["expires_in_s"] <= _PENDING_TTL - 147, half["expires_in_s"]
    assert fresh["expires_in_s"] > half["expires_in_s"], "秒数未随时间递减"


def test_past_due_is_zero_and_unknown_is_none_never_zero():
    """已过期 ⇒ 真值 ``0``；**取不到 ⇒ ``None``**（0 会被读成「已过期」= 假拒绝）。"""
    now = time.time()
    assert _pending_card_view({"id": "tc", "ts": now - (_PENDING_TTL + 60)})["expires_in_s"] == 0
    for bad in ({}, {"id": "x"}, {"id": "x", "ts": 0}, {"id": "x", "ts": "abc"}, {"id": "x", "ts": None}):
        v = _pending_card_view(bad)["expires_in_s"]
        assert v is None, "未知必须显式 None（不得兜底）：%r -> %r" % (bad, v)


def test_view_is_a_copy_and_does_not_pollute_pending_state():
    """视图 = 副本：**不改** ``_pending_writes`` 结构（否则会进 ``.agent_state.json``）。"""
    src = {"id": "tc9", "ts": time.time(), "content": "x" * 20, "command": "rm -rf /tmp/x"}
    view = _pending_card_view(src)
    assert view is not src
    assert "expires_in_s" not in src and "revoke_window" not in src, "原 pending 结构被写入新键"
    assert view["content"] == "x" * 20 and view["command"] == src["command"], "视图丢了原有字段"


def test_revoke_window_is_read_only_passthrough_hidden_by_default():
    """撤销窗口**只透传**：写审批未接 hold ⇒ 恒 ``{show: False}``；且**读不建文件**。"""
    holds = ROOT / "data" / "v9" / "pes" / "holds.json"
    before = holds.exists()
    view = _pending_card_view({"id": "not-held", "ts": time.time()})
    assert view["revoke_window"].get("show") is False, view["revoke_window"]
    assert holds.exists() == before, "只读透传不得创建/改动 holds.json"


def test_assembly_wires_the_view_for_single_and_batch():
    """响应组装点两条分支都走视图，**不直接把状态字典交给前端**。"""
    s = io.open(TOOL_RUNNER, encoding="utf-8").read()
    assert s.count('_resp_wp["pending_write"] = _pending_card_view(_pending_writes[session_id])') == 1
    assert s.count('_resp_wp["batch_pending"] = _pending_card_view(_pending_writes[session_id])') == 1
    assert '_resp_wp["pending_write"] = _pending_writes[session_id]\n' not in s
    assert '_resp_wp["batch_pending"] = _pending_writes[session_id]\n' not in s


def test_view_helper_does_not_hardcode_seconds():
    """秒数**不得写死**（旧口径 60s 已作废）——只允许引用常量。"""
    s = io.open(TOOL_RUNNER, encoding="utf-8").read()
    i = s.index("def _pending_card_view(")
    fn = s[i : s.index("\ndef _run_approval_gate(", i)]
    assert "_PENDING_TTL" in fn, "未引用常量"
    for bad in ("300", "60"):
        assert bad not in fn.replace("_PENDING_TTL", ""), "疑似写死秒数：%s" % bad


# ---------------------------------------------------------------- 前端渲染层

def test_body_renders_backend_snapshot_and_hides_when_absent(tmp_path):
    """后端给了就显示；**没给就不出现**（不留 null/undefined/NaN）。"""
    r = _run_node(
        tmp_path,
        """
const withTtl = PA_CARD_BODY.approval({id:'c1', target:'data/a.md', expires_in_s:299});
if(withTtl.indexOf('剩余 299 秒') < 0) throw new Error('未渲染后端快照：' + withTtl);
const noTtl = PA_CARD_BODY.approval({id:'c2', target:'data/a.md'});
if(noTtl.indexOf('剩余') >= 0) throw new Error('后端没给却渲染了秒数：' + noTtl);
const nulTtl = PA_CARD_BODY.approval({id:'c3', target:'data/a.md', expires_in_s:null});
if(nulTtl.indexOf('剩余') >= 0) throw new Error('null 被渲染成秒数：' + nulTtl);
[withTtl, noTtl, nulTtl].forEach(function(h){
  if(h.indexOf('undefined') >= 0 || h.indexOf('null') >= 0 || h.indexOf('NaN') >= 0)
    throw new Error('出现字面量：' + h);
});
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_expired_zero_is_shown_as_zero_not_swallowed(tmp_path):
    """``0`` 是**真值**（已过期）⇒ 必须照实渲染；把 0 当「没给」隐藏 = 另一种撒谎。"""
    r = _run_node(
        tmp_path,
        """
const html = PA_CARD_BODY.approval({id:'c1', target:'data/a.md', expires_in_s:0});
if(html.indexOf('剩余 0 秒') < 0) throw new Error('0 被吞掉：' + html);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_revoke_window_only_rendered_when_show_is_true(tmp_path):
    """撤销窗口只在 ``show===true`` 且秒数可读时渲染（不暗示不存在的窗口）。"""
    r = _run_node(
        tmp_path,
        """
const hidden = PA_CARD_BODY.approval({id:'c1', target:'a.md', revoke_window:{show:false}});
if(hidden.indexOf('撤销窗口') >= 0) throw new Error('show=false 仍渲染了撤销窗口');
const shown = PA_CARD_BODY.approval({id:'c2', target:'a.md', revoke_window:{show:true, seconds_left:120}});
if(shown.indexOf('撤销窗口') < 0 || shown.indexOf('剩余 120 秒') < 0)
  throw new Error('show=true 未渲染：' + shown);
const partial = PA_CARD_BODY.approval({id:'c3', target:'a.md', revoke_window:{show:true}});
if(partial.indexOf('undefined') >= 0) throw new Error('缺 seconds_left 渲染成 undefined：' + partial);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_three_decision_buttons_unchanged(tmp_path):
    """三选项按钮**语义不动**（仅本次 / 一直允许 / 不允许），且仍只有 3 个。"""
    r = _run_node(
        tmp_path,
        """
if(Object.keys(PA_CARD_ACTS).join(',') !== 'approve,always,reject')
  throw new Error('决策串改动：' + Object.keys(PA_CARD_ACTS).join(','));
if(PA_CARD_ACTS.approve !== '\u2705 \u4ec5\u672c\u6b21' || PA_CARD_ACTS.always !== '\u267e\ufe0f \u4e00\u76f4\u5141\u8bb8' || PA_CARD_ACTS.reject !== '\u274c \u4e0d\u5141\u8bb8')
  throw new Error('按钮文案改动');
const html = PA_CARD_BODY.approval({id:'c1', target:'a.md', decisions:['approve','always','reject']});
const n = (html.match(/data-act=/g) || []).length;
if(n !== 3) throw new Error('按钮数应为 3，实际 ' + n);
console.log('ok buttons=' + n);
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_write_card_passes_backend_values_through_not_hardcoded_null():
    """``renderPaWriteCard`` 改**透传**（旧实现把两个字段写死 null ⇒ 后端给了也不显示）。"""
    mod = _card_module()
    i = mod.find("function renderPaWriteCard(pw, note){")
    assert i > 0, "未找到 renderPaWriteCard"
    fn = mod[i:]
    assert "expires_in_s:null, revoke_window:null" not in fn, "仍在写死 null"
    assert "pw.expires_in_s" in fn and "pw.revoke_window" in fn, "未透传后端快照"
