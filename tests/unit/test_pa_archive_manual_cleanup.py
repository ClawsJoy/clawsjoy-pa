# -*- coding: utf-8 -*-
"""W-09 · PA 归档**手动清理**入口验收（``web/pa.html`` · 老板 2026-09-18 拍板）。

拍板原话要点（DS 建议、老板同意）：**「不自动裁 + 手动清理入口 + 按条数提示 + 可导出回溯」**
—— 自动裁剪与批221·A「不裁剪、不丢数据优先」冲突，故裁剪只能由**老板主动点按钮**触发。

判据（**不靠自觉**）：

1. **唯一触发路径 = 按钮**：``paArchiveCleanup`` 除定义外**只能**被横幅 onclick 引用，
   **不得**出现在 boot / saveState / newThread / 配额守卫区域（＝不存在自动删除路径）；
2. **取消 ⇒ 零改动**：确认框返回 false ⇒ ``state.archived`` 原样、``saveState`` 未被调用；
3. **确认 ⇒ 只删最早 N 条**：不提供「全清」；顺序保持；删够即止；
4. **删了什么要留痕**且**不谎称可还原**：日志写明条数 + 「被删内容不可恢复」；
5. **守卫仍是只读**：配额守卫区域（W-08/W-10）**不得**出现删除动作（既有判据不破）。

独立运行的临时 js 走 ``tmp_path``；本文件不改任何产品代码。
"""
from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PA = ROOT / "web" / "pa.html"

_START = "/* ---- W-09 手动清理入口"
_END = "function paParseStateTolerant(raw){"
_GUARD_START = "/* ---- W-08"
_GUARD_END = "function saveState(){"


def _src() -> str:
    return io.open(PA, encoding="utf-8").read()


def _clean_region() -> str:
    s = _src()
    i = s.find(_START)
    j = s.find(_END, i)
    assert i > 0 and j > i, "未找到 W-09 手动清理区域"
    return s[i:j]


def _quota_region() -> str:
    s = _src()
    i = s.find(_GUARD_START)
    j = s.find(_GUARD_END, i)
    assert i > 0 and j > i, "未找到配额守卫区域"
    return s[i:j]


def _stub() -> str:
    return (
        "var state = { archived: [], threads: [], activeThread: null };\n"
        "var _saved = 0; function saveState(){ _saved++; }\n"
        "var _logs = []; function addLog(m, k, persist){ _logs.push({m:String(m), k:k, p:!!persist}); }\n"
        "var _guard = 0; function paQuotaGuard(){ _guard++; }\n"
        "var _answer = true, _confirmCalls = 0, _confirmMsg = '';\n"
        "global.window = { confirm: function(msg){ _confirmCalls++; _confirmMsg = String(msg); return _answer; } };\n"
        "function fill(n){ state.archived = []; for(var i=0;i<n;i++){ state.archived.push({id:'a'+i, archived_at:'t'+i}); } return state.archived.length; }\n"
    )


def _run_node(tmp_path, body):
    code = _stub() + _clean_region() + "\n" + body
    probe = tmp_path / "probe_archive_clean.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(code)
    return subprocess.run(
        ["node", str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def _hint_src() -> str:
    """只抽守卫区域里的「阈值常量 + 条数提示函数」（move 而非 retype）。"""
    region = _quota_region()
    i = region.find("const PA_ARCHIVE_HINT_COUNT")
    assert i > 0, "未找到阈值常量"
    const_line = region[i : region.find("\n", i)]
    j = region.find("function paArchiveHintText(n){")
    assert j > 0, "未找到条数提示函数"
    k = region.find("\n}", j)
    assert k > j, "未找到条数提示函数结尾"
    return const_line + "\n" + region[j : k + 2] + "\n"


def _run_hint_node(tmp_path, body):
    probe = tmp_path / "probe_archive_hint.js"
    io.open(probe, "w", encoding="utf-8", newline="\n").write(_hint_src() + "\n" + body)
    return subprocess.run(
        ["node", str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


# ---------------------------------------------------------------- 静态层（无自动删除路径）

def test_cleanup_has_exactly_one_trigger_the_button():
    """**唯一的删除入口**：除函数定义外，只有横幅 onclick 引用它。"""
    s = _src()
    assert s.count("paArchiveCleanup(") == 2, "引用数应为 2（定义 + 按钮 onclick）：%d" % s.count("paArchiveCleanup(")
    assert 'onclick="paArchiveCleanup()"' in s, "缺「手动清理归档」按钮"
    assert s.count('onclick="paArchiveCleanup()"') == 1, "按钮应只有一处"
    # 横幅里同时在位（导出 + 清理成对，先可回溯再删）
    i = s.find('id="paQuotaBanner"')
    j = s.find("</div>", i)
    banner = s[i:j]
    assert 'onclick="paExportArchive()"' in banner, "清理入口必须与导出入口同处（先备份再删）"
    assert 'onclick="paArchiveCleanup()"' in banner, "清理按钮不在横幅内"


def test_cleanup_is_never_automatic():
    """**不自动裁**：boot / saveState / newThread 均不得调用清理；守卫区域也不得引用它。"""
    s = _src()
    assert "paArchiveCleanup" not in _quota_region(), "配额守卫区域引用了清理（会变成自动删除）"
    assert "_boot(\"paArchiveCleanup\"" not in s and "_boot('paArchiveCleanup'" not in s
    # saveState / newThread 里也不得出现
    i = s.find("function saveState(){")
    j = s.find("function ", s.find("\n}", i))
    assert "paArchiveCleanup" not in s[i:j], "saveState 里出现清理调用"
    i2 = s.find("function newThread(")
    j2 = s.find("function ", s.find("\n}", i2))
    assert "paArchiveCleanup" not in s[i2:j2], "newThread 里出现清理调用（＝自动裁）"
    assert "setInterval(paArchiveCleanup" not in s.replace(" ", ""), "不得定时自动清理"


def test_archive_threshold_is_a_named_constant_used_everywhere():
    """条数阈值只以常量出现（守卫 + 线程提示共用），不散落魔数。"""
    s = _src()
    assert "const PA_ARCHIVE_HINT_COUNT = 100;" in s, "阈值常量缺失/被改"
    assert "PA_ARCHIVE_HINT_COUNT" in _quota_region(), "守卫未用常量"
    assert "state.archived||[]).length > 100" not in s, "仍存在写死的 100"
    assert "const PA_ARCHIVE_CLEAN_BATCH = 100;" in _clean_region(), "清理批量常量缺失"


def test_guard_region_still_read_only():
    """W-09 不得把守卫从「只读提示」变成「会删数据」。"""
    js = _quota_region()
    for bad in (".splice(", ".shift(", "removeItem", "state.archived ="):
        assert bad not in js, "守卫区域出现数据动作：%s" % bad


# ---------------------------------------------------------------- 行为层（node）

def test_cancel_changes_nothing(tmp_path):
    """**关键安全判据**：确认框取消 ⇒ 归档原样、未写盘、未记「已清理」。"""
    r = _run_node(
        tmp_path,
        """
fill(250);
_answer = false;
const ok = paArchiveCleanup();
if(ok !== false) throw new Error('取消却返回 true');
if(state.archived.length !== 250) throw new Error('取消却改了数据：' + state.archived.length);
if(_saved !== 0) throw new Error('取消却写盘了');
if(_confirmCalls !== 1) throw new Error('未弹确认框');
if(_logs.length !== 1 || _logs[0].m.indexOf('取消') < 0) throw new Error('未记录取消：' + JSON.stringify(_logs));
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_confirm_removes_only_the_earliest_batch(tmp_path):
    """确认 ⇒ **只删最早 N 条**、顺序保持、保留更新的一半，且清理清单记入日志。"""
    r = _run_node(
        tmp_path,
        """
fill(250);
_answer = true;
const ok = paArchiveCleanup();
if(ok !== true) throw new Error('确认却返回 false');
if(state.archived.length !== 150) throw new Error('删除条数不对：' + state.archived.length);
if(state.archived[0].id !== 'a100') throw new Error('删错了对象（应删最早 100 条）：' + state.archived[0].id);
if(state.archived[149].id !== 'a249') throw new Error('尾部被误删：' + state.archived[149].id);
if(_saved !== 1) throw new Error('清理后未写盘一次');
if(_guard !== 1) throw new Error('清理后未复算横幅');
const last = _logs[_logs.length - 1].m;
if(last.indexOf('100') < 0) throw new Error('日志未写删除条数：' + last);
if(last.indexOf('不可恢复') < 0) throw new Error('日志谎称可还原：' + last);
if(_confirmMsg.indexOf('导出归档 JSON') < 0) throw new Error('确认框未提示先导出备份');
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_confirm_dialog_states_the_real_count(tmp_path):
    """确认框必须写明「当前多少 / 删多少 / 留多少」——**不夸大也不隐瞒**。"""
    r = _run_node(
        tmp_path,
        """
fill(12);
_answer = false;
paArchiveCleanup();
for(const s of ['当前归档：12 条', '本次删除：最早的 12 条']){
  if(_confirmMsg.indexOf(s) < 0) throw new Error('确认框缺：' + s + ' => ' + _confirmMsg);
}
if(_confirmMsg.indexOf('全部归档') < 0) throw new Error('将清空归档时未显式说明：' + _confirmMsg);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_empty_archive_does_not_ask_for_confirmation(tmp_path):
    """空归档 ⇒ 不弹确认框（不打扰），并如实说明「0 条」。"""
    r = _run_node(
        tmp_path,
        """
fill(0);
const ok = paArchiveCleanup();
if(ok !== false) throw new Error('空归档应返回 false');
if(_confirmCalls !== 0) throw new Error('空归档却弹了确认框');
if(_saved !== 0) throw new Error('空归档却写盘');
if(_logs.length !== 1 || _logs[0].m.indexOf('0 条') < 0) throw new Error('未如实说明：' + JSON.stringify(_logs));
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_hint_text_has_count_and_no_estimates(tmp_path):
    """条数提示：含条数/阈值/两个出口，且**不推断**「还能撑多久」。"""
    r = _run_hint_node(
        tmp_path,
        """
const t = paArchiveHintText(180);
for(const s of ['180', '100', '导出归档 JSON', '手动清理归档', '不会自动删除'])
  if(t.indexOf(s) < 0) throw new Error('提示缺：' + s + ' => ' + t);
for(const bad of ['还能撑', '预计', '大约还能'])
  if(t.indexOf(bad) >= 0) throw new Error('提示出现推断：' + bad);
console.log('ok');
""",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_guard_shows_count_hint_when_archive_grows(tmp_path):
    """守卫：未超阈值但归档条数到线 ⇒ 出条数提示（原实现只在 console / 线程消息里）。"""
    s = _src()
    assert "if(u.archived >= PA_ARCHIVE_HINT_COUNT) return paQuotaNotice(paArchiveHintText(u.archived));" in s, \
        "守卫未接条数提示"
