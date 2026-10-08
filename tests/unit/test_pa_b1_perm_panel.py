# -*- coding: utf-8 -*-
"""PA-B1 · 阶段 B1 接线（2026-10-03 · CW b2a5182）：**授权面板** + 权限档单源。

病（设计稿 v9_pa_frontend_refactor_design.md §4.3「新增 授权面板 … 待接」§4.4 第 11-12 条
／§6 阶段 B B1）：`/v9/pa/proxy/gate`(L0) 与 `/v9/pa/proxy/approve`(L2) 后端**在场**，
`web/pa.html` **0 命中** ⇒ 老板看不到「授了什么、还剩多久、怎么撤」⇒ 够不着的能力。
附逮（本刻一手读 L2897 原文）：配置 Tab 的权限下拉**有**写后端，但失败只 `console.warn`
⇒ 后端拒收（409 坏状态 / 非法档）时界面仍显示新值 ⇒ **假绿**（改了不生效，用户看不到）。

判据（逐条可机检）：
  J1  读数不可得 ⇒ 明说「读数不可得」，⛔ 不报成「未授权」（两态必须分得开）；
  J2  授权未授予 ⇒ 明说「未授予（默认档）」，⛔ 不把默认档当读数；
  J3  已授权 ⇒ `expires_in` 与 `paths` 是**后端给的读数**（面板只显示，⛔ 不造倒计时）；
  J4  授权**没点名 path** ⇒ **一次 POST 都不许发**（⛔ 前端不代填授权对象）；
  J5  `ttl_s` 非正数/非数 ⇒ 一次 POST 都不许发；
  J6  改档值不在白名单 ⇒ 一次 POST 都不许发；
  J7  接线自证：load ⇒ GET `proxy/gate`（带 user_id）；grant ⇒ POST `proxy/approve`（body.path）；
  J8  后端拒收（403）⇒ **原样可见**（status ＋ 原文），⛔ 不吞；
  J9  未取得回执 ⇒ 说「未取得回执」，⛔ 不说成「没授权」；
  J10 权限档单源：`pa_cfg` 不再存 perm（⛔ 第二真源）· 权限写失败不再静默（`console.warn` 已除）。

本件**不复制代码**：前端判据从 `web/pa.html` 原文按标记抽出**整段**用 node 真跑；
后端判据走**真路由**（Flask test_client），⛔ 不 mock 掉被审对象。
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
# 拆面（承 pm 1334 §三.1 · 惟改径 ＋ 并读；§二.1「出处之判须以『其物在何处』为据 ⇒ 页面 ＝ 壳 ＋ 支」）：
#   壳（容器 `<div id="permPanel">` ⇒ web/pa.html）＋ 块家（接线块 ⇒ faces/authz.js）＋ 启线（`_boot` ⇒ boot.js）。
PA = (ROOT / "web" / "pa.html",
      ROOT / "web" / "pa" / "faces" / "authz.js",
      ROOT / "web" / "pa" / "boot.js")
SCRATCH = ROOT / "data" / "tmp" / "_pa_b1_perm"

# 接线块自己的起止标记（⛔ 不是测试这边另加的锚）
START = "/* ---- PA-B1 \u00b7 \u6388\u6743\u9762\u677f \u63a5\u7ebf"
END = "/* ---- PA-B1 \u00b7 \u6388\u6743\u9762\u677f \u63a5\u7ebf END ---- */"


def _pa() -> str:
    """面集联文（径见 `PA` · 一处成）：壳 ＋ 支 并读 ⇒ ⛔ 唯读块家。"""
    return "\n".join(io.open(f, encoding="utf-8").read() for f in PA)


def _region(src: str) -> str:
    j = src.find(END)
    assert j > 0, "找不到接线区止标记 END（pa.html 结构变了？）"
    i = src.rfind(START, 0, j)
    assert 0 < i < j, "找不到接线区起标记 START"
    return src[i:j + len(END)]


_STUB = r"""
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
const API='';
function curUser(){ return 'U'; }
var paGrant=null, paGrantLevel=null, paGrantErr=undefined;
var fetchPaGrant=function(){ return Promise.resolve(); };
const __els={}; const __calls=[];
function __el(id){
  if(!__els[id]) __els[id]={id:id,innerHTML:'',value:'',attrs:{},open:true,
    getAttribute:function(k){ return (k in this.attrs)?this.attrs[k]:null; },
    setAttribute:function(k,v){ this.attrs[k]=v; },
    addEventListener:function(){}, querySelector:function(){ return null; }};
  return __els[id];
}
var document={ getElementById:function(id){ return __el(id); } };
var __route=function(){ return {status:200, body:{ok:true}}; };
var fetch=function(url,opt){ __calls.push({url:url,opt:opt||null}); var r=__route(url,opt);
  return Promise.resolve({status:r.status, json:function(){ return Promise.resolve(r.body); }}); };
"""


def _run(js_body: str, region: str = None) -> dict:
    src = _region(_pa()) if region is None else region
    jssrc = (_STUB + "\n" + src + "\n"
             + "(async function(){\n" + js_body + "\n})()\n"
             + ".then(function(o){ console.log(JSON.stringify(o)); })\n"
             + ".catch(function(e){ console.log(JSON.stringify({__err:String((e&&e.stack)||e)})); });\n")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / "perm_harness.js"
    io.open(f, "w", encoding="utf-8", newline="\n").write(jssrc)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-800:])
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert "__err" not in out, "harness 内异常：%s" % str(out.get("__err", ""))[:600]
    return out


def _panel(js_setup: str) -> str:
    """跑一段 setup 后取面板 innerHTML。"""
    o = _run(js_setup + "\n  paPermLoaded=true; renderPermPanel();\n  return {html: __el('permPanel').innerHTML};")
    return o["html"]


#: J1 判据正文只写一处（测试与齿共用，⛔ 不写两份 ⇒ 免漂移）
def _j1_ok(h: str) -> bool:
    return ("读数不可得" in h) and ("HTTP 500" in h) and ("未授权（后端 approved=false）" not in h)


# ============================ 前端：不吞 / 不造 ============================

def test_j1_gate_unreadable_is_not_shown_as_not_authorized():
    h = _panel("paPermGate={__error:'HTTP 500'};")
    assert _j1_ok(h), "J1：读不到却不说「读数不可得」（或被说成了「未授权」）：%r" % h[:300]


def test_j2_default_level_is_not_presented_as_a_reading():
    h = _panel("paGrant={pa:{path:'p',exists:false},pes:{path:'q',exists:false}};"
               "paGrantLevel='标准'; paGrantErr=null;"
               "paPermGate={approved:false,expires_in:0,paths:[]};")
    assert "未授予" in h and "默认档" in h, "J2：没授予文件却没明说「未授予（默认档）」"
    assert "未授权" in h and "空 ≠ 读数不可得" in h and "approved=false" in h, \
        "J2b：空 paths 与「读不到」必须分得开（且「未授权」之因（approved=false）须可查 · 承 pm_2095 §一.5 之净）"


def test_j3_approved_shows_backend_readings_not_frontend_countdown():
    h = _panel("paGrant={pa:{path:'D:/p.json',exists:true},pes:{path:'D:/b.json',exists:false}};"
               "paGrantLevel='只读'; paGrantErr=null;"
               "paPermGate={approved:true,expires_in:900,paths:['/kv/clear']};")
    assert "已授权" in h and "900" in h and "/kv/clear" in h, "J3：已授权的读数没显示出来"
    assert "setInterval" not in h and "不自行倒计时" in h, \
        "J3b：面板不许自造倒计时（须明说「不自行倒计时」· 且 ⛔ setInterval · 承 pm_2095 §一.5 之净）"


def test_j4_grant_without_named_path_sends_nothing():
    o = _run("""
      __route=function(){ return {status:200, body:{ok:true, paths:['/x']}}; };
      const r=await paPermGrant({path:'', ttl_s:'', note:''});
      return {sent:__calls.length, out:__el('ppGateMsg').innerHTML, ok:r.ok};
    """)
    assert o["sent"] == 0, "J4：没点名 path 竟然还发了请求（⛔ 前端不代填授权对象）"
    assert "未点名 path" in o["out"], "J4：拒发但没说理由"


def test_j5_bad_ttl_sends_nothing():
    o = _run("""
      __route=function(){ return {status:200, body:{ok:true, paths:['/x']}}; };
      const a=await paPermGrant({path:'/x', ttl_s:'abc', note:''});
      const n1=__calls.length;
      const b=await paPermGrant({path:'/x', ttl_s:'-5', note:''});
      return {n1:n1, n2:__calls.length, out:__el('ppGateMsg').innerHTML, ok:a.ok&&b.ok};
    """)
    assert o["n1"] == 0 and o["n2"] == 0, "J5：ttl 非数/非正数竟然还发了请求"
    assert "不是正数" in o["out"], "J5：拒发但没说理由"


def test_j6_level_outside_whitelist_sends_nothing():
    o = _run("""
      __route=function(){ return {status:200, body:{ok:true, level:'只读'}}; };
      const a=await paPermSetLevel('随便');
      const b=await paPermSetLevel('');
      return {sent:__calls.length, out:__el('ppLevelMsg').innerHTML, ok:a.ok||b.ok};
    """)
    assert o["sent"] == 0, "J6：档不在白名单竟然还发了请求"
    assert "白名单" in o["out"], "J6：拒发但没说理由"


def test_j7_wiring_load_and_grant_hit_the_right_endpoints():
    o = _run("""
      __calls.length=0;
      __route=function(){ return {status:200, body:{ok:true, approved:true, expires_in:60, paths:['/kv/clear']}}; };
      await paPermLoad(true);
      const gate=__calls.length;
      __route=function(){ return {status:200, body:{ok:true, paths:['/kv/clear']}}; };
      await paPermGrant({path:'/kv/clear', ttl_s:'', note:'n'});
      return {gate:gate, urls:__calls.map(function(c){ return c.url; }),
              m:__calls[0]?__calls[0].opt.method:null,
              b:__calls[1]?'':''};
    """)
    assert o["gate"] >= 1, "J7：load 没去读 proxy/gate"
    assert "/v9/pa/proxy/gate" in o["urls"][0] and "user_id=" in o["urls"][0], "J7：gate 读数缺 user_id"
    assert any("/v9/pa/proxy/approve" in u for u in o["urls"]), "J7：授权没打 POST proxy/approve"


def test_j7b_grant_body_carries_the_named_path():
    o = _run("""
      __calls.length=0;
      __route=function(){ return {status:200, body:{ok:true, paths:['/kv/clear']}}; };
      await paPermGrant({path:'/kv/clear', ttl_s:'', note:''});
      return {body:__calls[0].opt.body, url:__calls[0].url};
    """)
    assert "/v9/pa/proxy/approve" in o["url"], "打错了端点"
    assert "/kv/clear" in o["body"], "body 没带点名 path"


def test_j7c_revoke_posts_revoke_true():
    o = _run("""
      __calls.length=0;
      __route=function(){ return {status:200, body:{ok:true, revoked:true}}; };
      await paPermRevoke();
      return {url:__calls[0].url, body:__calls[0].opt.body, out:__el('ppGateMsg').innerHTML};
    """)
    assert "/v9/pa/proxy/approve" in o["url"] and "revoke" in o["body"], "撤销没走 approve 的 revoke 分支"
    assert "已撤销" in o["out"], "撤销成功没回执"


def test_j8_backend_rejection_is_visible_not_swallowed():
    o = _run("""
      __route=function(){ return {status:403, body:{ok:false, error:'endpoint_guard: 需在场授权'}}; };
      const r=await paPermGrant({path:'/kv/clear', ttl_s:'', note:''});
      return {out:__el('ppGateMsg').innerHTML, ok:r.ok, st:r.status};
    """)
    assert o["ok"] is False and o["st"] == 403
    assert "后端拒收" in o["out"] and "403" in o["out"] and "需在场授权" in o["out"], \
        "J8：后端拒收被吞了（原样可见是本条命根子）"


def test_j9_no_receipt_is_not_no_authorization():
    o = _run("""
      __route=function(){ throw new Error('Failed to fetch'); };
      const r=await paPermGrant({path:'/kv/clear', ttl_s:'', note:''});
      return {out:__el('ppGateMsg').innerHTML, sent:r.sent, ok:r.ok};
    """)
    assert "未取得回执" in o["out"] and "Failed to fetch" in o["out"], "J9：异常原文没带出来"
    assert "⛔ 不等于「没授权」" in o["out"], "J9：把「没回执」说成了「没授权」"


def test_j9b_set_level_rejection_reads_back_and_does_not_leave_a_fake_value():
    o = _run("""
      __route=function(url,opt){ if(String(url).indexOf('/v9/pa/permission')>=0)
          return {status:409, body:{ok:false, error:'pa_state_corrupt'}};
        return {status:200, body:{ok:true, approved:false, expires_in:0, paths:[]}}; };
      const r=await paPermSetLevel('只读');
      return {out:__el('ppLevelMsg').innerHTML, ok:r.ok, st:r.status,
              readback:__calls.filter(function(c){return String(c.url).indexOf('/v9/pa/proxy/gate')>=0;}).length};
    """)
    assert o["ok"] is False and o["st"] == 409
    assert "pa_state_corrupt" in o["out"] and "回读" in o["out"], "J9b：改档失败没明说、也没回读"
    assert o["readback"] >= 1, "J9b：失败后没回读后端真值（界面会留假值）"


def test_j10_static_panel_is_reachable_from_page():
    src = _pa()
    assert '<div id="permPanel" class="cbpanel"></div>' in src, "面板容器没进页面"
    assert '_boot("renderPermPanel", PA_FACES.guard("authz", renderPermPanel));' in src, "启动没接线（面板永不渲染）"
    for frag in ('onclick="paPermLoad(true)"', 'onclick="paPermGrant()"',
                 'onclick="paPermRevoke()"', 'onclick="paPermSetLevel()"'):
        assert frag in src, "有函数但没 onclick ⇒ 用户够不着：%s" % frag


def test_j10b_permission_has_a_single_source_and_no_silent_write():
    src = _pa()
    assert "perm:$('cfgPerm').value" not in src, "`pa_cfg` 还存 perm ⇒ 第二真源没消"
    assert "set('cfgPerm',c.perm)" not in src, "还从 `pa_cfg` 回填权限档 ⇒ 第二真源没消"
    assert "console.warn('permission 后端写入失败'" not in src, "改档失败还是静默（console.warn）"
    assert "console.warn('permission 后端不可达'" not in src, "改档不可达还是静默（console.warn）"
    assert "paPermEl('ppLevelMsg')" in src and "按后端真值回读（⛔ 界面不留假值）" in src, "改档失败没有可见通道（⛔ 静默）"


# ============================ 反例门（齿） ============================

def test_neg_teeth_removing_unreadable_wording_is_caught():
    reg = _region(_pa())
    mutant = reg.replace("读数不可得", "未授权")
    assert mutant != reg, "改不动 ⇒ 这条齿是假的"
    o = _run("paPermGate={__error:'HTTP 500'}; paPermLoaded=true; renderPermPanel();"
             " return {html: __el('permPanel').innerHTML};", region=mutant)
    assert not _j1_ok(o["html"]), "齿失效：挖掉「读数不可得」J1 竟然还过"


def test_neg_teeth_removing_path_guard_is_caught():
    reg = _region(_pa())
    mutant = reg.replace("if(!f.path){ say(", "if(false){ say(")
    assert mutant != reg, "改不动 ⇒ 这条齿是假的"
    o = _run("""
      __route=function(){ return {status:200, body:{ok:true, paths:['/x']}}; };
      const r=await paPermGrant({path:'', ttl_s:'', note:''});
      return {sent:__calls.length};
    """, region=mutant)
    assert o["sent"] > 0, "齿失效：挖掉守卫，没点名 path 竟仍没发请求（J4 没打在守卫上）"


# ============================ 后端：真路由 ============================

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    from core.pa.gateway_routes import register_pa_routes
    register_pa_routes(app)
    return app.test_client()


def test_route_gate_default_is_not_approved(client):
    d = client.get("/v9/pa/proxy/gate?user_id=U_b1_a").get_json()
    assert d["ok"] is True
    assert d["approved"] is False and d["paths"] == [] and d["expires_in"] == 0, \
        "默认就是「未授权」，面板必须靠这条读数说话"


def test_route_approve_then_gate_flips_and_revoke_flips_back(client):
    uid = "U_b1_b"
    r = client.post("/v9/pa/proxy/approve", json={"user_id": uid, "path": "/kv/clear", "ttl_s": 60}).get_json()
    assert r["ok"] is True and "/kv/clear" in r["paths"], "授权没落到 paths"
    g = client.get("/v9/pa/proxy/gate?user_id=" + uid).get_json()
    assert g["approved"] is True and "/kv/clear" in g["paths"] and g["expires_in"] > 0, "gate 没跟着翻面"
    rv = client.post("/v9/pa/proxy/approve", json={"user_id": uid, "revoke": True}).get_json()
    assert rv["ok"] is True and rv["revoked"] is True
    assert client.get("/v9/pa/proxy/gate?user_id=" + uid).get_json()["approved"] is False, "撤销后仍approved"


def test_route_permission_rejects_level_outside_whitelist(client):
    d = client.post("/v9/pa/permission", json={"level": "随便"}).get_json()
    assert d["ok"] is False, "白名单外的档竟然被接受"
    d2 = client.post("/v9/pa/permission", json={"level": "只读"}).get_json()
    assert d2["ok"] is True and d2["level"] == "只读"
    assert client.get("/v9/pa/permission").get_json()["level"] == "只读", "写进去了但读不回来"
