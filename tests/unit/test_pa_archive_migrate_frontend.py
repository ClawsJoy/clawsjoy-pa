# -*- coding: utf-8 -*-
"""X-11 层 1 步 2 · PA 前端**归档正文落服务端**（``web/pa.html`` · 老板/DS 2026-09-18 拍 A）。

背景：``pa_state`` 撑爆配额 ⇒ 归档正文搬到服务端，本地每条只留 5 键索引
（``id/title/archived_at/msg_count/server``）。Windows 线端口 5102（步 0）。

判据（**不靠自觉**）：

1. **只换正文、不删条目**：迁移后 ``state.archived`` **条目数不变**（批221·A「不裁剪、不丢数据」）；
2. **服务端确认读回才改本地**：``ok && written >= n`` 才替换；**失败/不足数 ⇒ 本地一字不改**；
3. **假成交防线**：服务端回 ``ok`` 但 ``written`` 少于应写条数 ⇒ **照样当失败**（不得假装成功）；
4. **先保底导出**：动数据**之前**先落回滚文件（上次教训：没有基线 ⇒ 无法判定丢没丢数据）；
5. **可回滚**：``PA_ARCHIVE_SERVER=false`` ⇒ 整个迁移不跑（零请求、零备份、零改动）；
6. **未知即未知**：``archived_at`` 取不到就留 ``null``，**不兜底**成「现在」；
7. **不自动删除**：迁移区不得出现 ``.splice(``／``.pop(``／``.shift(``／``removeItem``／``setItem(``
   —— 唯一落盘出口是 ``saveState()``。

独立运行的临时 js 走 ``tmp_path``；本文件**不改任何产品代码**。
"""
from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 拆面（承 pm 1334 §三.1 · 惟改径 ＋ 并读）：X-11 迁移区 ＝ web/pa/faces/archive.js ／ 启动序 ＝ web/pa/boot.js
PA = (ROOT / "web" / "pa" / "faces" / "archive.js",
      ROOT / "web" / "pa" / "boot.js")

_START = "/* ---- X-11 层 1：归档正文落服务端"
_END = "\n/* ---- W-08"


def _src() -> str:
    return "\n".join(io.open(f, encoding="utf-8").read() for f in PA)


def _region(server: bool = True) -> str:
    """抽迁移区（``X-11`` 区头 → 配额守卫区头）。

    注意：``_END`` 带前导换行 —— 区头注释里**不得复述**别的区块边界字面量，
    否则 ``find`` 会把起点提前到注释里（实测会让 6 条 W-08 判据变红）。
    """
    s = _src()
    i = s.find(_START)
    j = s.find(_END, i)
    # 哨兵之正（拆面之必然）：`find` 之「未找到」＝ `-1`；块今为面文件之首 ⇒ `i == 0` 合法
    #   ⇒ ⛔ 再以 `i > 0` 代「找到」（那会把「找到且在首位」误判成「未找到」）。判据 ⛔ 削：仍须「标记在」（`>= 0`）
    #   ＋ 下二行「区内容物 ＋ ⛔ 越界」照旧把守。
    assert i >= 0, "未找到 X-11 迁移区"
    assert j > i, "未找到迁移区结束锚点（配额守卫区头）"
    r = s[i:j]
    assert "paMigrateArchiveToServer" in r, "迁移区抽取不完整（锚点或注释被改动）"
    assert "paQuotaGuard" not in r, "迁移区抽取越界（把配额守卫区也框进来了）"
    if server:
        return r
    r2 = r.replace("const PA_ARCHIVE_SERVER = true;", "const PA_ARCHIVE_SERVER = false;")
    assert r2 != r, "回滚位常量未找到（PA_ARCHIVE_SERVER）"
    return r2


def _strip_comments(js: str) -> str:
    """去掉块注释与行注释后再判据（注释里写「不要写 #modeHint」是合法的）。"""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"^\s*//.*$", "", js, flags=re.M)


# 迁移区引用的既有符号由 stub 提供（产品代码里它们在别的区，不重复搬）。
_STUBS = """
global.localStorage = { _v:'', getItem:function(){return this._v;}, setItem:function(){}, removeItem:function(){} };
global.API = 'http://127.0.0.1:5102';
global.CALLS = { fetch:[], save:0, notice:[], msg:[], downloads:[] };
let state = { mode:'work', threads:[], activeThread:null, archived:[] };
function curUser(){ return 'web_test'; }
function saveState(){ global.CALLS.save++; }
function paQuotaNotice(t){ global.CALLS.notice.push(String(t)); return true; }
function addMsg(role, content){ global.CALLS.msg.push(role + ':' + content); return true; }
global.document = {
  createElement:function(){ const el = { download:'', click:function(){ global.CALLS.downloads.push(el.download); } }; return el; },
  body:{ appendChild:function(){ return true; } },
  getElementById:function(){ return null; }
};
URL.createObjectURL = function(){ return 'blob:probe'; };
URL.revokeObjectURL = function(){};
global.setTimeout = function(){ return 0; };
global.fetch = function(url, opt){
  global.CALLS.fetch.push({ url:url, opt:opt });
  return Promise.resolve({ ok:true, status:200, json:function(){ return Promise.resolve({ ok:true, written:999999 }); } });
};
"""


def _run_node(tmp_path, body, server: bool = True, name: str = "probe_migrate.js"):
    code = (_STUBS + "\n" + _region(server) + "\n(async function(){\n" + body
            + "\n})().catch(function(e){ console.error((e && e.stack) || String(e)); process.exit(1); });\n")
    probe = tmp_path / name
    io.open(probe, "w", encoding="utf-8", newline="\n").write(code)
    return subprocess.run(["node", str(probe)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- 纯函数层

def test_pending_picks_only_entries_with_body_and_not_yet_on_server(tmp_path):
    """待迁集合 = 「有正文」∩「未标 server」。空正文、已迁、无 msgs 键都不算。"""
    r = _run_node(tmp_path, """
state = { archived: [
  { id:'a', msgs:[1,2] },
  { id:'b', msgs:[1], server:true },
  { id:'c', msgs:[] },
  { id:'d', msgs:[], server:false },
  { id:'e' },
  { id:'f', msgs:[1,2,3] }
] };
const p = paArchivePending();
if(p.total !== 6) throw new Error('total 不对：' + p.total);
if(p.withBody !== 3) throw new Error('withBody 不对：' + p.withBody);
if(p.pending !== 2) throw new Error('pending 不对：' + p.pending);
const got = p.items.map(function(e){ return e.id; }).sort().join(',');
if(got !== 'a,f') throw new Error('待迁集合不对：' + got);
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_index_has_exactly_five_keys_and_makes_unknown_null(tmp_path):
    """索引**只有** 5 键（不含 msgs/plan/其它）；取不到的字段留 null（不兜底成「现在」）。"""
    r = _run_node(tmp_path, """
if(PA_ARCHIVE_INDEX_KEYS.length !== 5) throw new Error('键表不是 5 键：' + PA_ARCHIVE_INDEX_KEYS.length);
const WANT = ['id','title','archived_at','msg_count','server'].sort().join(',');
const idx = paArchiveIndex({ id:'x', title:'t', archived_at:111, msgs:[1,2,3], plan:{a:1}, extra:'z' });
const ks = Object.keys(idx).sort().join(',');
if(ks !== WANT) throw new Error('索引键不对：' + ks);
if(idx.msg_count !== 3) throw new Error('msg_count 未按正文实算：' + idx.msg_count);
if(idx.server !== true) throw new Error('未标 server');
if('msgs' in idx || 'plan' in idx || 'extra' in idx) throw new Error('索引混进正文/多余键');
const idx2 = paArchiveIndex({ id:'y', msgs:[1] });
if(idx2.archived_at !== null) throw new Error('archived_at 未留 null：' + idx2.archived_at);
if(idx2.title !== null) throw new Error('title 未留 null：' + idx2.title);
const idx3 = paArchiveIndex({ id:'z', msg_count:7, server:true });
if(idx3.msg_count !== 7) throw new Error('无 msgs 时未回落到 msg_count：' + idx3.msg_count);
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


# ---------------------------------------------------------------- 迁移主路径

def test_migrate_replaces_body_keeps_entry_count_and_sends_payload(tmp_path):
    """成功路径：上行只带有正文的条目；落地后**条目数不变**、迁走的只剩 5 键、未迁的逐字节不变。"""
    r = _run_node(tmp_path, r"""
const N = 1797;
state = { mode:'work', threads:[{ id:'t1' }], activeThread:'t1', archived: [] };
for(let i = 0; i < N; i++)
  state.archived.push({ id:'s'+i, title:'T'+i, archived_at:1000+i, msg_count:4, server:true });
state.archived.push({ id:'b1', title:'有正文1', archived_at:2001,
                      msgs:[{r:'u',c:'x'},{r:'a',c:'y'}], plan:{p:1} });
state.archived.push({ id:'b2', title:'有正文2', archived_at:2002, msgs:[1,2,3] });
const before = JSON.parse(JSON.stringify(state.archived));

const res = await paMigrateArchiveToServer();
if(res.migrated !== 2) throw new Error('迁移条数不对：' + res.migrated);
if(res.total !== N + 2) throw new Error('上报 total 不对：' + res.total);
if(state.archived.length !== N + 2) throw new Error('条目数变了（不许增删）：' + state.archived.length);
if(global.CALLS.save !== 1) throw new Error('落盘次数不对：' + global.CALLS.save);
if(global.CALLS.fetch.length !== 1) throw new Error('请求次数不对：' + global.CALLS.fetch.length);

const call = global.CALLS.fetch[0];
if(call.url !== 'http://127.0.0.1:5102/v9/pa/archive') throw new Error('端点不对：' + call.url);
if(call.opt.method !== 'POST') throw new Error('方法不对：' + call.opt.method);
const sent = JSON.parse(call.opt.body);
if(sent.user_id !== 'web_test') throw new Error('未带 user_id：' + sent.user_id);
if(sent.items.length !== 2) throw new Error('上行条数不对：' + sent.items.length);
if(sent.items[0].msgs.length !== 2) throw new Error('上行丢了正文');
if(sent.items[0].plan.p !== 1) throw new Error('上行丢了 plan');

const WANT = ['id','title','archived_at','msg_count','server'].sort().join(',');
const b1 = state.archived.filter(function(e){ return e.id === 'b1'; })[0];
const ks = Object.keys(b1).sort().join(',');
if(ks !== WANT) throw new Error('迁走后键不对：' + ks);
if(b1.msg_count !== 2) throw new Error('msg_count 未按正文实算：' + b1.msg_count);
if('msgs' in b1 || 'plan' in b1) throw new Error('正文没删干净');

const untouched = state.archived.filter(function(e){ return e.id.charAt(0) === 's'; });
const orig = before.filter(function(e){ return e.id.charAt(0) === 's'; });
if(JSON.stringify(untouched) !== JSON.stringify(orig)) throw new Error('未迁条目被改动');

if(global.CALLS.downloads.length !== 1) throw new Error('未先落回滚文件');
if(!/^pa_state_premigrate_[0-9]+\.json$/.test(global.CALLS.downloads[0]))
  throw new Error('回滚文件名不对：' + global.CALLS.downloads[0]);
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_migrate_keeps_local_untouched_when_written_is_short(tmp_path):
    """**假成交防线**：服务端回 ``ok:true`` 但 ``written`` 少于应写条数 ⇒ 当失败、本地一字不改。"""
    r = _run_node(tmp_path, """
global.fetch = function(url, opt){
  global.CALLS.fetch.push({ url:url, opt:opt });
  return Promise.resolve({ ok:true, status:200, json:function(){ return Promise.resolve({ ok:true, written:1 }); } });
};
state = { archived:[ { id:'b1', msgs:[1,2], archived_at:5 }, { id:'b2', msgs:[1], archived_at:6 } ] };
const before = JSON.stringify(state.archived);
const res = await paMigrateArchiveToServer();
if(!res.error) throw new Error('假成交未被判失败（假绿）');
if(res.error.indexOf('written=1') < 0) throw new Error('失败原因未带 written：' + res.error);
if(res.migrated !== 0) throw new Error('失败却报了迁移条数：' + res.migrated);
if(JSON.stringify(state.archived) !== before) throw new Error('本地被改了（一字不改破功）');
if(global.CALLS.save !== 0) throw new Error('失败却落盘了');
if(global.CALLS.downloads.length !== 1) throw new Error('失败前未先落回滚文件');
if(global.CALLS.notice.length !== 1) throw new Error('失败未进可见横幅');
if(global.CALLS.msg.length !== 1) throw new Error('失败未落 sys 消息');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_migrate_keeps_local_untouched_on_http_500(tmp_path):
    """服务端 500 ⇒ 本地**一字不改**、不落盘、报错带上游原因。"""
    r = _run_node(tmp_path, """
global.fetch = function(url, opt){
  global.CALLS.fetch.push({ url:url, opt:opt });
  return Promise.resolve({ ok:false, status:500, json:function(){ return Promise.resolve({ ok:false, error:'boom' }); } });
};
state = { archived:[ { id:'b1', msgs:[1,2], archived_at:5 } ] };
const before = JSON.stringify(state.archived);
const res = await paMigrateArchiveToServer();
if(!res.error) throw new Error('500 未判失败');
if(res.error.indexOf('boom') < 0) throw new Error('失败原因未带上游信息：' + res.error);
if(JSON.stringify(state.archived) !== before) throw new Error('本地被改了');
if(global.CALLS.save !== 0) throw new Error('失败却落盘了');
if(global.CALLS.downloads.length !== 1) throw new Error('失败前未先落回滚文件');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_migrate_keeps_local_untouched_when_fetch_rejects(tmp_path):
    """网络层直接 reject（断网/DNS）⇒ 同 500：本地一字不改、不落盘。"""
    r = _run_node(tmp_path, """
global.fetch = function(){ global.CALLS.fetch.push({ url:'(rejected)', opt:null });
  return Promise.reject(new Error('network down')); };
state = { archived:[ { id:'b1', msgs:[1,2], archived_at:5 } ] };
const before = JSON.stringify(state.archived);
const res = await paMigrateArchiveToServer();
if(!res.error) throw new Error('网络失败未判失败');
if(res.error.indexOf('network down') < 0) throw new Error('失败原因未带上游信息：' + res.error);
if(JSON.stringify(state.archived) !== before) throw new Error('本地被改了');
if(global.CALLS.save !== 0) throw new Error('失败却落盘了');
if(global.CALLS.downloads.length !== 1) throw new Error('失败前未先落回滚文件');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_migrate_is_skipped_when_rollback_switch_is_off(tmp_path):
    """``PA_ARCHIVE_SERVER=false`` ⇒ 零请求、零备份、零落盘、零改动（回滚位有效）。"""
    r = _run_node(tmp_path, """
state = { archived:[ { id:'b1', msgs:[1,2], archived_at:5 } ] };
const before = JSON.stringify(state.archived);
const res = await paMigrateArchiveToServer();
if(res.skipped !== 'switch_off') throw new Error('关闸未生效：' + JSON.stringify(res));
if(global.CALLS.fetch.length !== 0) throw new Error('关闸还在发请求');
if(global.CALLS.downloads.length !== 0) throw new Error('关闸还落回滚文件');
if(global.CALLS.save !== 0) throw new Error('关闸还落盘');
if(JSON.stringify(state.archived) !== before) throw new Error('关闸还改了本地');
console.log('ok');
""", server=False)
    assert r.returncode == 0, r.stderr + r.stdout


def test_migrate_without_body_is_a_noop_with_zero_requests(tmp_path):
    """无正文（全是索引/空正文）⇒ **零请求、零备份、零落盘**（不假装搬过）。"""
    r = _run_node(tmp_path, """
state = { archived:[
  { id:'s1', title:'a', archived_at:1, msg_count:0, server:true },
  { id:'s2', title:'b', archived_at:2, msg_count:0, server:true },
  { id:'e1', msgs:[] }
] };
const before = JSON.stringify(state.archived);
const res = await paMigrateArchiveToServer();
if(res.pending !== 0) throw new Error('pending 应为 0：' + res.pending);
if(res.migrated !== 0) throw new Error('无正文却报了迁移条数');
if(global.CALLS.fetch.length !== 0) throw new Error('无正文却发了请求');
if(global.CALLS.downloads.length !== 0) throw new Error('无正文却落了回滚文件');
if(global.CALLS.save !== 0) throw new Error('无正文却落盘');
if(JSON.stringify(state.archived) !== before) throw new Error('无正文却改了本地');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


def test_migrate_does_not_invent_missing_archived_at(tmp_path):
    """端到端：``archived_at``/``title`` 缺失 ⇒ 本地与上行都留 ``null``（**不**兜底成当前时间）。"""
    r = _run_node(tmp_path, """
state = { archived:[ { id:'b1', msgs:[1,2] } ] };
const res = await paMigrateArchiveToServer();
if(res.migrated !== 1) throw new Error('未迁移：' + JSON.stringify(res));
const e = state.archived[0];
if(e.archived_at !== null) throw new Error('archived_at 被兜底了：' + e.archived_at);
if(e.title !== null) throw new Error('title 被兜底了：' + e.title);
if(e.msg_count !== 2) throw new Error('msg_count 不对：' + e.msg_count);
if(e.server !== true) throw new Error('未标 server');
const sent = JSON.parse(global.CALLS.fetch[0].opt.body);
if(sent.items[0].archived_at !== null) throw new Error('上行把未知编成了值');
if(sent.items[0].title !== null) throw new Error('上行把未知标题编成了值');
if(sent.items[0].plan !== null) throw new Error('上行把缺失 plan 编成了值');
console.log('ok');
""")
    assert r.returncode == 0, r.stderr + r.stdout


# ---------------------------------------------------------------- 静态层

def test_migrate_region_never_deletes_and_has_single_persist_outlet():
    """**不自动删除/不裁剪**：迁移区不得出现删除动作；落盘出口**唯一**（``saveState()``）。"""
    js = _strip_comments(_region())
    for bad in (".splice(", ".pop(", ".shift(", "removeItem", "setItem(", "delete ", "length = 0"):
        assert bad not in js, "迁移区出现数据动作：%s" % bad
    assert js.count("saveState()") == 1, "迁移区落盘出口不唯一：%d 处" % js.count("saveState()")
    assert re.search(r"\(state\.archived \|\| \[\]\)\.map\(", js), "替换未走 map（可能增删条目）"
    assert not re.search(r"state\.archived\s*=\s*\[", js), "迁移区直接重建了 archived 数组"
    assert not re.search(r"state\.threads\s*=", js), "迁移区改写了 threads"
    assert not re.search(r"state\.activeThread\s*=", js), "迁移区改写了 activeThread"


def test_migrate_region_goes_through_api_base_and_path_constant():
    """端点 = ``API`` 基址 + 路径常量：迁移区**不得**硬编码主机/端口（``X-12`` 家族的静默跨树风险）。"""
    js = _strip_comments(_region())
    assert "API + PA_ARCHIVE_API" in js, "未走 API 基址 + 路径常量"
    for bad in ("5002", "5102", "localhost", "127.0.0.1", "http://", "https://"):
        assert bad not in js, "迁移区硬编码了地址：%s" % bad


def test_migrate_region_reports_through_existing_visible_channel():
    """失败/成功都要**可见**：走既有横幅（``paQuotaNotice``）＋ 控制台 ＋ sys 消息；不得写 ``#modeHint``。"""
    js = _strip_comments(_region())
    assert "paQuotaNotice(" in js, "提示未走既有可见横幅"
    assert "modeHint" not in js, "写了 #modeHint（会被 setMode 重画覆盖 ⇒ 等于静默）"
    assert "console.warn" in js and "console.log" in js, "未落控制台"
    assert "addMsg(" in js, "未落 sys 消息"


def test_rollback_switch_and_index_keys_are_named_constants():
    """回滚位与键表都是具名常量；索引**按键表构造**（键表本身是判据）。"""
    s = _src()
    assert "const PA_ARCHIVE_SERVER = true;" in s, "回滚位常量被改动"
    assert ("const PA_ARCHIVE_INDEX_KEYS = ['id', 'title', 'archived_at', 'msg_count', 'server'];"
            in s), "键表常量被改动"
    assert "PA_ARCHIVE_INDEX_KEYS.forEach(" in _region(), "索引未按键表构造"


def test_boot_runs_migration_after_quota_guard():
    """启动即接（fail-loud）：迁移挂在**配额守卫之后**的启动序列里。"""
    s = _src()
    # 随器（拆面）：启动序之家 ＝ web/pa/boot.js；调用已包 PA_FACES.guard（承 pm 1334 §三.1）
    g = '_boot("paQuotaGuard", PA_FACES.guard("archive", paQuotaGuard));'
    m = '_boot("paMigrateArchiveToServer", PA_FACES.guard("archive", paMigrateArchiveToServer));'
    assert m in s, "迁移未接入启动流程"
    i, j = s.find(g), s.find(m)
    assert 0 < i < j, "迁移应在配额守卫之后运行"
    k = s.find("function paCollapseToSingleThread(){")
    assert 0 < k < j, "迁移未接在启动序列（paCollapseToSingleThread）内"


def test_region_anchors_are_unique_and_not_restated_elsewhere():
    """锚点唯一性：迁移区**不得复述**别区边界字面量（复述会把测试抽取起点提前）。"""
    s = _src()
    assert s.count(_START) == 1, "X-11 区头不唯一"
    assert s.count("/* ---- W-08") == 1, "W-08 区头被复述（W-08 测试抽取会错位）"
    assert s.count("function saveState(){") == 1, "saveState 签名被复述（同上）"
    assert s.find(_START) < s.find("/* ---- W-08"), "迁移区应在配额守卫区之前"
