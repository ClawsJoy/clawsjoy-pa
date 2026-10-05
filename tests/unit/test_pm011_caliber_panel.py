# -*- coding: utf-8 -*-
"""PM-011 · N1 接线（2026-09-30 · CW b2a5182）：**口径面板** 接上三个端点。

病（PM 裁定原文）：「该闸在场但没接线」—— `/v9/pa/caliber`(L0) ／ `/v9/pa/caliber/change`(L1)
／ `/v9/pa/caliber/check`(L2 门) 在后端**在场且有单测**，但 `web/pa.html` **0 命中** ⇒ 前端够不着。
（设计稿 v9_pa_frontend_refactor_design.md §4.3「新增 口径面板 … 待接」／§4.4 第 13–15 条。）

判据（逐条可机检）：
  J1  读不到 ⇒ 明说「读数不可得」，⛔ 不报 0、⛔ 不填占位符、⛔ 不说成「没有口径卡」；
  J1b 卡 status 缺失/不认识 ⇒ 明说「未知」，⛔ 不默认成 confirmed；
  J2  变更单缺 id/status/owner/why 任一项 ⇒ **一次 POST 都不许发**（⛔ 前端不代填默认值）；
  J2b 四项齐 ⇒ 提交**前**已渲染「改前值 → 改后值」两侧；
  J3  校验三态**两两不同**：命中 ／ 未命中 ／ 未取得回执；
  J5  接线自证：load ⇒ GET caliber；check ⇒ POST caliber/check（body.pages 契约）；change ⇒ POST caliber/change。
后端另有**命根子**一条：改一条口径 ⇒ `check()` 的命中集**必须跟着变**（⛔ 不变 ⇒ 口径外置是装饰层）。

本件**不复制代码**：前端判据从 `web/pa.html` 原文按标记抽出**整段**（含 const）用 node 真跑；
后端判据走**真路由**（Flask test_client ＋ 临时 PA_DATA_DIR），⛔ 不 mock 掉被审对象。
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
PA = ROOT / "web" / "pa.html"
SCRATCH = ROOT / "data" / "tmp" / "_pm011_caliber"

# 接线块自己的起止标记（⛔ 不是测试这边另加的锚）；用转义写死，免得任何一层的编码把标记改掉
START = "/* ---- PM-011 \u00b7 N1 \u63a5\u7ebf"        # /* ---- PM-011 · N1 接线
END = "/* ---- PM-011 \u00b7 N1 \u63a5\u7ebf END ---- */"


def _pa() -> str:
    return io.open(PA, encoding="utf-8").read()


def _region(src: str) -> str:
    """抽接线区整段：以 END 为界向前找最近的一处 START（CSS 注释里也有同前缀，别抽错）。"""
    j = src.find(END)
    assert j > 0, "找不到接线区止标记 END（pa.html 结构变了？）"
    i = src.rfind(START, 0, j)
    assert 0 < i < j, "找不到接线区起标记 START"
    return src[i:j + len(END)]


_STUB = r"""
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
const API='';
function curUser(){ return 'U'; }
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
    f = SCRATCH / "caliber_harness.js"
    io.open(f, "w", encoding="utf-8", newline="\n").write(jssrc)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-800:])
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert "__err" not in out, "harness 内异常：%s" % str(out.get("__err", ""))[:600]
    return out


# ============================ 前端：不吞／不造 ============================

def test_j1_unreadable_is_not_reported_as_zero():
    o = _run("""
      paCaliberCache={__loaded:true, __error:'HTTP 500'};
      renderCaliberPanel();
      return {html: __el('caliberPanel').innerHTML};
    """)
    h = o["html"]
    assert "读数不可得" in h, "读不到却不说「读数不可得」：%r" % h[:200]
    assert "HTTP 500" in h, "后端原文被吞掉了"
    assert "本库暂无可口径卡" not in h, "把「读数不可得」说成了「没有口径卡」"


def test_j1b_missing_status_is_unknown_not_confirmed():
    o = _run("return {a:paCaliberCardHtml({id:'#9'}), b:paCaliberCardHtml({id:'#4',status:'unverified'})};")
    assert "未知" in o["a"], "status 缺失竟不标「未知」：%r" % o["a"]
    assert "confirmed" not in o["a"], "status 缺失竟默认成 confirmed"
    assert "unverified" in o["b"]


def test_j1c_counts_unavailable_is_not_zero():
    o = _run("return {a: paCaliberCountsHtml({cards:[]}),"
             " b: paCaliberCountsHtml({counts:{confirmed:8,unverified:2,pending:1},source:'store'})};")
    assert "计数不可得" in o["a"], "没给 counts 却按 0 显示：%r" % o["a"]
    assert "unverified 2" in o["b"] and "源 store" in o["b"]


# ============================ 前端：必填四项 ＋ 改前值 ============================

def test_j2_missing_field_sends_nothing():
    o = _run("""
      __route=function(){ return {status:200, body:{ok:true}}; };
      const r=await paCaliberSubmit({id:'#4', status:'confirmed', owner:'', why:'x'});
      return {r:r, calls:__calls.length, prev:__el('cbPrev').innerHTML};
    """)
    assert o["calls"] == 0, "缺 owner 竟然仍发了 %d 次请求" % o["calls"]
    assert o["r"]["missing"] == ["owner"], o["r"]
    assert "owner" in o["prev"], "缺项没在页面上说清"


def test_j2b_all_four_renders_prev_then_posts_change():
    o = _run("""
      paCaliberCache={__loaded:true, source:'store', counts:{confirmed:8,unverified:2,pending:1},
        cards:[{id:'#4', status:'unverified', owner:'PM b136893', note:'N0'}]};
      __route=function(url){
        if(url.indexOf('/change')>=0) return {status:200, body:{ok:true, change:{id:'#4'}}};
        if(url.indexOf('/caliber?')>=0) return {status:200, body:{ok:true, cards:[], counts:{confirmed:0,unverified:0,pending:0}, source:'store'}};
        return {status:200, body:{ok:true}};
      };
      const p=paCaliberSubmit({id:'#4', status:'confirmed', owner:'PM b136893', why:'W1'});
      const prevMid=__el('cbPrev').innerHTML;
      const r=await p;
      const c=__calls[0];
      return {r:r, prevMid:prevMid, url:c.url, method:c.opt.method, sent:JSON.parse(c.opt.body)};
    """)
    assert "改前" in o["prevMid"] and "改后" in o["prevMid"], "提交前没渲染「改前值 → 改后值」"
    assert "unverified" in o["prevMid"] and "confirmed" in o["prevMid"], "改前/改后两侧没同时出现"
    assert o["url"] == "/v9/pa/caliber/change" and o["method"] == "POST"
    assert o["sent"] == {"id": "#4", "status": "confirmed", "owner": "PM b136893", "why": "W1"}


def test_j2c_prev_unavailable_is_not_invented():
    o = _run("""
      paCaliberCache={__loaded:true, cards:[], counts:{confirmed:0,unverified:0,pending:0}, source:'store'};
      __route=function(){ return {status:200, body:{ok:true}}; };
      await paCaliberSubmit({id:'#404', status:'confirmed', owner:'PM', why:'W'});
      return {prev:__el('cbPrev').innerHTML};
    """)
    assert "改前值不可得" in o["prev"], "id 不在现值里却造了一个「改前值」：%r" % o["prev"][:200]


def test_j2d_backend_rejection_is_surfaced_not_swallowed():
    o = _run("""
      paCaliberCache={__loaded:true, cards:[{id:'#4',status:'unverified'}], counts:{confirmed:0,unverified:1,pending:0}, source:'store'};
      __route=function(){ return {status:409, body:{ok:false, error:'caliber_store_corrupt', message:'store bad'}}; };
      const r=await paCaliberSubmit({id:'#4',status:'confirmed',owner:'PM',why:'W'});
      return {r:r, prev:__el('cbPrev').innerHTML};
    """)
    assert o["r"]["ok"] is False and o["r"]["status"] == 409
    assert ("caliber_store_corrupt" in o["prev"]) or ("store bad" in o["prev"]), "后端拒收原文被吞"


# ============================ 前端：校验三态 ============================

def test_j3_check_three_states_are_pairwise_distinct():
    o = _run("""
      return {hit: paCaliberCheckHtml({hits:[['P01','#4','OPC loan','unverified','300']],hit_count:1}),
              none: paCaliberCheckHtml({hits:[],hit_count:0}),
              noreceipt: paCaliberCheckHtml(null),
              errm: paCaliberCheckHtml({__error:'HTTP 500'})};
    """)
    assert "未取得回执" in o["noreceipt"]
    assert "未命中" in o["none"]
    assert "#4" in o["hit"] and "unverified" in o["hit"]
    assert len({o["hit"], o["none"], o["noreceipt"], o["errm"]}) == 4, "三态（＋读不到）有重合文案"
    assert "✅ 未命中" not in o["noreceipt"] and "未取得回执" in o["noreceipt"], "「未取得回执」被写成了「未命中」"


# ============================ 前端：接线自证（发了没发 ／ 发给谁） ============================

def test_j5_load_actually_calls_the_read_endpoint():
    o = _run("""
      __route=function(){ return {status:200, body:{ok:true,
        cards:[{id:'#4',status:'unverified',topic:'T',owner:'PM',updated:'2026-09-30 07:31:34'}],
        counts:{confirmed:8,unverified:2,pending:1}, source:'store'}}; };
      const d=await paCaliberLoad(true);
      return {urls:__calls.map(c=>c.url), method:(__calls[0].opt||{}).method||'GET',
              html:__el('caliberPanel').innerHTML, src:d.source};
    """)
    assert o["urls"] == ["/v9/pa/caliber?user_id=U"], "读端点没被调（就是「闸在场没接线」）"
    assert o["method"] == "GET"
    assert "#4" in o["html"] and "confirmed 8" in o["html"], "读数没进面板"


def test_j5b_check_posts_pages_contract():
    o = _run("""
      __route=function(){ return {status:200, body:{ok:true, hits:[['P01','#4','OPC loan','unverified','300']], hit_count:1}}; };
      const res=await paCaliberCheckText('dong 300');
      const c=__calls[0];
      return {url:c.url, method:c.opt.method, pages:JSON.parse(c.opt.body).pages, out:__el('cbCheckOut').innerHTML};
    """)
    assert o["url"] == "/v9/pa/caliber/check" and o["method"] == "POST"
    assert o["pages"] == [{"data": {"body": "dong 300"}}], "载荷没按 pages[].data.body 契约发"
    assert "#4" in o["out"]


def test_j5c_check_unreachable_says_no_receipt():
    o = _run("""
      fetch=function(){ return Promise.reject(new Error('Failed to fetch')); };
      const res=await paCaliberCheckText('x');
      return {out:__el('cbCheckOut').innerHTML, err:res.__error};
    """)
    assert "未取得回执" in o["out"] and "Failed to fetch" in o["out"]
    assert "Failed to fetch" in o["err"], "err 没把异常原文带出来"


def test_j5d_check_empty_text_does_not_invent_pages():
    o = _run("""
      const res=await paCaliberCheckText('   ');
      return {calls:__calls.length, out:__el('cbCheckOut').innerHTML};
    """)
    assert o["calls"] == 0, "没正文竟然还发了请求（凭空造 pages）"
    assert "没有可校验的正文" in o["out"]


def test_static_panel_is_reachable_from_page():
    src = _pa()
    assert '<div id="caliberPanel" class="cbpanel"></div>' in src, "面板容器没进页面"
    assert '_boot("renderCaliberPanel", renderCaliberPanel);' in src, "启动没接线（面板永不渲染）"
    for frag in ('onclick="paCaliberLoad(true)"', 'onclick="paCaliberSubmit()"', 'onclick="paCaliberCheck()"'):
        assert frag in src, "有函数但没 onclick ⇒ 用户够不着：%s" % frag


# ============================ 反例门（齿） ============================

def test_neg_teeth_removing_no_receipt_wording_is_caught():
    reg = _region(_pa())
    mutant = reg.replace("未取得回执", "未命中")
    assert mutant != reg, "改不动 ⇒ 这条齿是假的"
    o = _run("return {noreceipt: paCaliberCheckHtml(null)};", region=mutant)
    assert "未取得回执" not in o["noreceipt"], "齿失效：挖掉「未取得回执」J3 竟然还过"


def test_neg_teeth_removing_four_field_guard_is_caught():
    """齿：挖掉必填四项守卫 ⇒ 缺 owner 时**就会发 POST** ⇒ J2 必须判红。"""
    reg = _region(_pa())
    mutant = reg.replace("const miss=paCaliberMissingFields(f);", "const miss=[];")
    assert mutant != reg, "改不动 ⇒ 这条齿是假的"
    o = _run("""
      __route=function(){ return {status:200, body:{ok:true}}; };
      const r=await paCaliberSubmit({id:'#4',status:'confirmed',owner:'',why:'x'});
      return {sent:__calls.length, ok:r.ok};
    """, region=mutant)
    assert o["sent"] > 0, "齿失效：挖掉守卫，缺字段竟仍没发出请求（J2 没打在守卫上）"


# ============================ 后端：真路由（临时 PA_DATA_DIR） ============================

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    from core.pa.gateway_routes import register_pa_routes
    register_pa_routes(app)
    return app.test_client()


def test_route_caliber_read_source_seed_then_store(client):
    d = client.get("/v9/pa/caliber").get_json()
    assert d["ok"] is True and d["source"] == "seed", "无 store ⇒ source 必须如实报 seed"
    assert isinstance(d["cards"], list) and d["counts"]["unverified"] >= 2
    assert any(c["id"] == "#4" and c["status"] == "unverified" for c in d["cards"])


def test_route_caliber_check_hits_and_misses(client):
    hit = client.post("/v9/pa/caliber/check",
                      json={"pages": [{"data": {"body": "建行 OPC 专属贷 最高 300 万"}}]}).get_json()
    assert hit["ok"] is True and hit["hit_count"] >= 1
    assert any(h[1] == "#4" for h in hit["hits"]), "未核实口径没被拦：%r" % hit["hits"]
    miss = client.post("/v9/pa/caliber/check", json={"pages": [{"data": {"body": "weather is fine"}}]}).get_json()
    assert miss["hit_count"] == 0, "无关正文竟命中"
    bad = client.post("/v9/pa/caliber/check", json={"pages": "not-a-list"})
    assert bad.get_json()["ok"] is False, "pages 非列表竟静默通过"


def test_route_change_requires_four_fields(client):
    r = client.post("/v9/pa/caliber/change", json={"id": "#4", "status": "confirmed", "why": "no owner"})
    assert r.get_json()["ok"] is False, "缺 owner 后端竟放行"


def test_route_change_then_check_follows_the_new_caliber(client, tmp_path):
    """命根子：**改一条口径 ⇒ check 的命中集必须跟着变**；⛔ 不变 ⇒ 口径外置是装饰层。"""
    pages = {"pages": [{"data": {"body": "建行 OPC 专属贷 最高 300 万"}}]}
    assert client.post("/v9/pa/caliber/check", json=pages).get_json()["hit_count"] >= 1
    ok = client.post("/v9/pa/caliber/change",
                     json={"id": "#4", "status": "confirmed", "owner": "PM b136893", "why": "test: confirm"})
    body = ok.get_json()
    assert body["ok"] is True, body
    assert (tmp_path / "pa" / "caliber.json").is_file(), "变更单没落 store"
    assert client.get("/v9/pa/caliber").get_json()["source"] == "store", "store 落了但 source 没翻面"
    assert client.post("/v9/pa/caliber/check", json=pages).get_json()["hit_count"] == 0, \
        "改口径后命中集不变 ⇒ 这张闸是装饰层"
    client.post("/v9/pa/caliber/change",
                json={"id": "#4", "status": "unverified", "owner": "PM b136893", "why": "test: restore"})
    assert client.post("/v9/pa/caliber/check", json=pages).get_json()["hit_count"] >= 1, "改回后又不拦了"