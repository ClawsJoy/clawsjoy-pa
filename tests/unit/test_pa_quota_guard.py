# -*- coding: utf-8 -*-
"""W-08/W-10 · PA 前端**产品侧配额守卫**验收（``web/pa.html`` · 老板 2026-09-18 拍板）。

现场根因（实测）：``pa_state`` 撑到配额上限 ⇒ ``setItem`` 抛 ``QuotaExceededError`` ⇒ 写入被拒
⇒ 刷新后读不到 ⇒ 用户看到的症状是「消息日志消失」。**W-08/W-09/W-10 三件提级、同批**。

判据（**不靠自觉**）：

1. **阈值是常量**（不散落魔数）；
2. **只提示不自动删**：老板 批221·A 已拍「归档不设上限、不裁剪（不丢数据优先）」
   ⇒ 裁剪规则（W-09）仍属老板判断 ⇒ 守卫**不得**出现任何删除/裁剪动作；
3. **提示进 UI**（W-10）：写专用横幅 ``#paQuotaBanner``，**不写** ``#modeHint``
   （会被 setMode 重画覆盖 ⇒ 等于静默）；
4. **不推断**：只报可从数据算出的数（字节、归档条数），不写「还能撑几天」这类估算。

独立运行的临时 js 走 ``tmp_path``；本文件不改任何产品代码。
"""
from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PA = ROOT / "web" / "pa.html"

_START = "/* ---- W-08"
_END = "function saveState(){"


def _src() -> str:
    return io.open(PA, encoding="utf-8").read()


def _quota_region() -> str:
    s = _src()
    i = s.find(_START)
    j = s.find(_END, i)
    assert i > 0 and j > i, "未找到配额守卫区域"
    return s[i:j]


def _strip_comments(js: str) -> str:
    """去掉块注释与行注释后再判据（注释里写「不要写 #modeHint」是合法的）。"""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"^\s*//.*$", "", js, flags=re.M)


def _save_state() -> str:
    s = _src()
    i = s.find(_END)
    j = s.find("async function syncThreads(", i)
    assert 0 < i < j, "未找到 saveState"
    return s[i:j]


def _defs_for_node() -> str:
    """抽取守卫代码（move 而非 retype）+ 最小 localStorage/document stub。"""
    return (
        "global.localStorage={ _v:'', getItem:function(){return this._v;}, setItem:function(){}, removeItem:function(){} };\n"
        "function mkEl(){ const el={ _t:'', _show:null };"
        "Object.defineProperty(el,'textContent',{get:function(){return el._t;},"
        "set:function(v){el._t=String(v==null?'':v);}});"
        "el.classList={toggle:function(c,on){ el._show=!!on; }}; return el; }\n"
        + _quota_region()
    )


def _run_node(tmp_path, body):
    code = _defs_for_node() + "\n" + body
    probe = tmp_path / "probe_quota.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(code)
    return subprocess.run(
        ["node", str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


# ---------------------------------------------------------------- 纯函数层

def test_usage_flags_over_threshold_and_counts_archived(tmp_path):
    """超阈值 ⇒ ``over=true``；归档条数从 ``state.archived`` 实算（不猜）。"""
    r = _run_node(
        tmp_path,
        """
if(PA_QUOTA_GUARD_BYTES !== 4 * 1024 * 1024) throw new Error('阈值被改动：' + PA_QUOTA_GUARD_BYTES);
state = { threads:[], activeThread:null, archived:[1,2,3] };
localStorage._v = 'x'.repeat(PA_QUOTA_GUARD_BYTES + 1);
let u = paQuotaUsage();
if(!u.over) throw new Error('超阈值未判为 over：' + JSON.stringify(u));
if(u.bytes < u.threshold) throw new Error('字节数不应小于阈值：' + JSON.stringify(u));
if(u.archived !== 3) throw new Error('归档条数未实算：' + u.archived);
localStorage._v = 'x'.repeat(1000);
u = paQuotaUsage();
if(u.over) throw new Error('小体积被误判为 over：' + JSON.stringify(u));
if(u.bytes !== 1000) throw new Error('小体积字节数不对：' + u.bytes);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_usage_never_throws_when_localstorage_is_unavailable(tmp_path):
    """localStorage 读失败 ⇒ 按空处理（守卫本身**不得**成为新的崩溃点）。"""
    r = _run_node(
        tmp_path,
        """
state = { threads:[], activeThread:null };
localStorage.getItem = function(){ throw new Error('SecurityError: blocked'); };
const u = paQuotaUsage();
if(u.over) throw new Error('读不到时不得报 over（未知即未知）：' + JSON.stringify(u));
if(u.bytes !== 0) throw new Error('读不到时字节数应为 0：' + u.bytes);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_notice_writes_dedicated_banner_not_mode_hint(tmp_path):
    """提示写 ``#paQuotaBanner``（专用元素）；空文本 ⇒ 收起（不留残影）。"""
    r = _run_node(
        tmp_path,
        """
const banner = mkEl(), span = mkEl();
global.document = { getElementById:function(id){
  return id === 'paQuotaBanner' ? banner : (id === 'paQuotaText' ? span : null); } };
if(paQuotaNotice('⚠ 测试') !== true) throw new Error('未写入横幅');
if(span.textContent !== '⚠ 测试') throw new Error('文案没进 span：' + span.textContent);
if(banner._show !== true) throw new Error('横幅未展开');
paQuotaNotice('');
if(banner._show !== false) throw new Error('空文本未收起横幅');
if(span.textContent !== '') throw new Error('空文本未清空：' + span.textContent);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_warn_text_has_required_wording_and_no_estimates(tmp_path):
    """W-10 文案：必须含「存储接近上限…你可以：① 归档旧会话；② 清理历史」＋「不会自动删除」；
    且**不得**出现「还能撑 N 天/次」这类推断。"""
    r = _run_node(
        tmp_path,
        """
state = { threads:[], activeThread:null, archived:new Array(836) };
const t = paQuotaWarnText(5000000);
for(const s of ['存储接近上限','新建会话/归档可能不生效','① 归档旧会话','② 清理历史',
                '不会自动删除','836'])
  if(t.indexOf(s) < 0) throw new Error('文案缺：' + s + ' => ' + t);
for(const bad of ['还能撑','预计','大约还能'])
  if(t.indexOf(bad) >= 0) throw new Error('文案出现推断：' + bad);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


# ---------------------------------------------------------------- 静态层

def test_threshold_is_named_constant_not_magic_number():
    """阈值只以常量出现（便于调），不散落魔数。"""
    s = _src()
    assert "const PA_QUOTA_GUARD_BYTES = 4 * 1024 * 1024;" in s, "阈值常量被改动"
    assert "4194304" not in s, "出现魔数 4194304（应走常量）"


def test_guard_never_deletes_or_trims_data():
    """**只提示不自动删**：守卫区域不得出现删除/裁剪/写入动作（W-09 裁剪规则待老板拍）。"""
    js = _strip_comments(_quota_region())
    for bad in (".splice(", ".pop(", ".shift(", "removeItem", "setItem(", ".concat(",
                "length = 0", "delete ", "write_text"):
        assert bad not in js, "守卫区域出现数据动作：%s" % bad
    assert not re.search(r"state\.archived\s*=[^=]", js), "守卫区域对 archived 赋值（＝裁剪/改写归档）"
    assert not re.search(r"state\.threads\s*=[^=]", js), "守卫区域改写 threads"
    assert "localStorage.getItem" in js, "守卫必须是只读的（getItem）"


def test_guard_does_not_write_mode_hint():
    """提示**不写 #modeHint**（会被 setMode 重画覆盖 ⇒ 等于静默）。"""
    region = _quota_region()
    assert "modeHint" not in _strip_comments(region), "守卫写了 #modeHint（会被 setMode 重画覆盖）"
    assert "'paQuotaBanner'" in region and "'paQuotaText'" in region, "未走专用横幅元素"
    assert "textContent" in region, "文案未走 textContent（拼 HTML 会引入注入面）"


def test_banner_element_and_export_button_exist_in_html():
    """横幅元素与「导出归档 JSON」按钮在位（导出是既有能力，只读、不删数据）。"""
    s = _src()
    assert 'id="paQuotaBanner"' in s, "缺横幅元素"
    assert 'id="paQuotaText"' in s, "缺横幅文案元素"
    assert 'onclick="paExportArchive()"' in s, "缺导出按钮（W-10 的自助动作）"
    assert s.count('id="paQuotaBanner"') == 1, "横幅元素应只有一处（不散落）"


def test_boot_runs_guard_after_collapse():
    """启动即测（W-08：**提前告警**，不等撞上）：收敛之后跑，且走 _boot（fail-loud）。"""
    s = _src()
    assert '_boot("paQuotaGuard", paQuotaGuard);' in s, "守卫未接入启动流程"
    i = s.find("  paCollapseToSingleThread();")
    j = s.find('_boot("paQuotaGuard", paQuotaGuard);')
    assert 0 < i < j, "守卫应在会话收敛之后运行"


def test_save_state_reports_quota_in_ui_and_prefilters():
    """写入路径两条：① 失败 ⇒ 提示进 UI；② 接近阈值 ⇒ 提前告警。且**先廉价预筛**再算字节。"""
    fn = _save_state()
    assert "paQuotaNotice(" in fn, "写失败未进 UI（W-10）"
    assert "PA_LAST_SAVE_BYTES" in fn, "未记录写盘体积"
    assert "_j.length * 3 >= PA_QUOTA_GUARD_BYTES" in fn, "缺廉价预筛（热路径会每次全量编码）"
    assert "paQuotaWarnText(PA_LAST_SAVE_BYTES)" in fn, "接近阈值未提前告警"
    # 既有批219 行为不得被本批改掉
    assert "localStorage.setItem('pa_state'" in fn, "写盘口径被改动"
    assert "state._saveError=String(e).slice(0,140);" in fn, "既有失败上报被改动"
