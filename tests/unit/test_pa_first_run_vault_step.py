# -*- coding: utf-8 -*-
u"""pm_1518 §一：首启盒「选一个笔记目录」之步（契约 TD_1515 §六.1 —— 径 ／ 体 ／ 回 ／ 错唯取契约）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_first_run_vault_step.py -q --basetemp=<仓外>

判据：
  ⒜ 步现于「未接（no_root）／空库（empty）」· ⛔ 现于「已接（ok）」（态唯比机器码 · 承 pm_1504 §一）
  ⒝ 体唯 `{"path": "<所入>"}`（⛔ 自拟字段）· 清除之支 ⇒ `{"path": ""}`
  ⒞ 错 ⇒ 后端之 `error` **逐字**上屏（⛔ 前端自编）
  ⒟ 成 ⇒ 唯取后端之值（`vault_root_src`）· 并复取 `first_run`（刷新其面）
  ⒠ 跳过 ⇒ ⛔ 发请求
  反控：banner ⛔ 载绝对径 ／ ⛔ `removeChild(` ／ ⛔ `paDismissCard(`
  器取：以 node 跑**真 banner**（DOM 桩 · 真函数 ⇒ ⛔ 以源码字面代屏）
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_HARNESS = u"""
const fs=require('fs');
const src=fs.readFileSync(process.argv[2],'utf8');
const payload=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const setres=JSON.parse(fs.readFileSync(process.argv[4],'utf8'));
const action=process.argv[5]||'none';
const inputval=process.argv[6]||'';
const CALLS=[];
function Node(tag){this.tag=tag;this.children=[];this.attrs={};this.innerHTML='';this.value='';}
Node.prototype.setAttribute=function(k,v){this.attrs[k]=String(v);};
Node.prototype.getAttribute=function(k){return this.attrs[k];};
Node.prototype.appendChild=function(c){c.parentNode=this;this.children.push(c);return c;};
global.document={createElement:function(t){return new Node(t);},body:new Node('body')};
global.fetch=function(url,opt){
  var u=String(url), m=(opt&&opt.method)||'GET', b=(opt&&opt.body)||null;
  CALLS.push({url:u,method:m,body:b});
  if(u.indexOf('/v9/pa/vault/set')>=0){
    return Promise.resolve({ok:true,json:function(){return Promise.resolve(setres);}});
  }
  return Promise.resolve({ok:true,json:function(){return Promise.resolve(payload);}});
};
eval(src);
function walk(n,acc){acc.push(n);for(var i=0;i<n.children.length;i++)walk(n.children[i],acc);return acc;}
function all(){return walk(document.body,[]);}
function findBtn(t){var a=all();for(var i=0;i<a.length;i++){if(a[i].tag==='button'&&a[i].innerHTML===t)return a[i];}return null;}
function findInput(){var a=all();for(var i=0;i<a.length;i++){if(a[i].tag==='input')return a[i];}return null;}
setTimeout(function(){
  if(action==='set'){var i=findInput();if(i)i.value=inputval;var b=findBtn('\u7528\u6b64\u76ee\u5f55');if(b&&b.onclick)b.onclick();}
  if(action==='skip'){var b2=findBtn('\u8df3\u8fc7');if(b2&&b2.onclick)b2.onclick();}
  if(action==='clear'){var b3=findBtn('\u6e05\u9664\uff08\u56de\u9000\uff09');if(b3&&b3.onclick)b3.onclick();}
  setTimeout(function(){
    var a=all(), out=[];
    for(var i=0;i<a.length;i++){out.push(a[i].innerHTML||'');}
    process.stdout.write(JSON.stringify({parts:out,calls:CALLS,text:out.join(String.fromCharCode(10)),
      body:(document.body.children||[]).map(function(c){return c.innerHTML||'';}).join(String.fromCharCode(10))}));
  },150);
},90);
"""


def _banner():
    s = (ROOT / "web" / "pa.html").read_text(encoding="utf-8")
    head = s[:s.index("pa/boot.js")]
    st = head.rindex("<script>")
    return head[st + len("<script>"):head.index("</script>", st)]


def _payload(vault_now, vault_state):
    keys = [
        {"键": "PA_ORG_FACES", "义": u"组织版开关", "今": u"开", "源": u"env:PA_ORG_FACES", "态": u"ok"},
        {"键": "PA_WS_ROOT", "义": u"工作区根", "今": u"D:/ws", "源": u"env:PA_WS_ROOT", "态": u"ok"},
        {"键": "PA_VAULT_DIR", "义": u"知识库根", "今": vault_now, "源": u"env:PA_VAULT_DIR", "态": vault_state},
    ]
    return {"ok": True, "须知": [], "模型": {"态": u"在∧可用", "因": u"器取"},
            "数据目录": {"值": u"D:/data", "源": u"配置"},
            "面之源": {"口径": u"口径", "键": keys}, "缺": []}


def _run(tmp_path, vault_now, vault_state, setres=None, action="none", inputval="", extra_payload=None):
    node = shutil.which("node")
    if not node:
        pytest.skip("node ⛔ 在 ⇒ 屏文之器取 ⛔ 得跑")
    (tmp_path / "banner.js").write_text(_banner(), encoding="utf-8")
    (tmp_path / "payload.json").write_text(
        json.dumps(extra_payload or _payload(vault_now, vault_state), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "setres.json").write_text(json.dumps(setres or {"ok": False, "error": u"stub"}, ensure_ascii=False),
                                         encoding="utf-8")
    (tmp_path / "harness.js").write_text(_HARNESS, encoding="utf-8")
    r = subprocess.run([node, str(tmp_path / "harness.js"), str(tmp_path / "banner.js"),
                        str(tmp_path / "payload.json"), str(tmp_path / "setres.json"), action, inputval],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    return json.loads(r.stdout)


def test_步现于未接与空库_不现于已接(tmp_path):
    o1 = _run(tmp_path, u"未接", u"no_root")
    assert u"选一个笔记目录" in o1["text"], o1["body"]
    o2 = _run(tmp_path, u"D:/kb", u"empty")
    assert u"选一个笔记目录" in o2["text"], o2["body"]
    o3 = _run(tmp_path, u"D:/kb", u"ok")
    assert u"选一个笔记目录" not in o3["text"], u"已接 ⇒ 其步 ⛔ 强现"


def test_态未给_步不现(tmp_path):
    o = _run(tmp_path, u"未接", u"")
    assert u"选一个笔记目录" not in o["text"], u"态 ⛔ 给 ⇒ ⛔ 兜底（承 pm_1504 §一）"


def test_体唯path(tmp_path):
    o = _run(tmp_path, u"未接", u"no_root", action="set", inputval=u"D:/my_notes")
    posted = [c for c in o["calls"] if c["url"].endswith("/v9/pa/vault/set")]
    assert len(posted) == 1, o["calls"]
    assert posted[0]["method"] == "POST"
    assert json.loads(posted[0]["body"]) == {"path": u"D:/my_notes"}, posted[0]["body"]


def test_清除之支_体为空串(tmp_path):
    o = _run(tmp_path, u"D:/kb", u"empty", setres={"ok": True, "vault_root": u"", "vault_root_src": u"未接",
                                                    "state": u"no_root", "at": u"x", "changed": True},
               action="clear")
    posted = [c for c in o["calls"] if c["url"].endswith("/v9/pa/vault/set")]
    assert len(posted) == 1, o["calls"]
    assert json.loads(posted[0]["body"]) == {"path": u""}, posted[0]["body"]


def test_错_后端之字面逐字上屏(tmp_path):
    err = u"vault_set: 目录 ⛔ 可写：D:/ro（选一个可写之目录 ∨ 改权限）"
    o = _run(tmp_path, u"未接", u"no_root", setres={"ok": False, "error": err}, action="set", inputval=u"D:/ro")
    assert err in o["text"], o["text"]


def test_成_唯取后端之值_并复取首启(tmp_path):
    o = _run(tmp_path, u"未接", u"no_root",
             setres={"ok": True, "vault_root": u"D:/my_notes", "vault_root_src": u"配置:paths.vault_root",
                     "state": u"empty", "at": u"x", "changed": True},
             action="set", inputval=u"D:/my_notes")
    assert u"配置:paths.vault_root" in o["text"], o["text"]
    firsts = [c for c in o["calls"] if c["url"].endswith("/v9/pa/first_run")]
    assert len(firsts) >= 2, u"成 ⇒ 须复取首启之读数（刷新其面）"


def test_跳过_不发请求(tmp_path):
    o = _run(tmp_path, u"未接", u"no_root", action="skip")
    assert not [c for c in o["calls"] if c["url"].endswith("/v9/pa/vault/set")], o["calls"]


def test_banner_非屏_之戒():
    b = _banner()
    assert re.search(r"[A-Za-z]:[\\/]", b) is None, re.findall(r"[A-Za-z]:[\\/]", b)
    assert "removeChild(" not in b
    assert "paDismissCard(" not in b
    assert "/v9/pa/vault/set" in b


NOTE = u"本机之库根由环境变量 PA_VAULT_DIR 指定 ⇒ 你所选须清该变量方生效"


def test_note_env_override真_须现(tmp_path):
    u'''pm_1521 ⒈：回载 `env_override:true` ＋ `note` ⇒ 其字**唯取后端** ⇒ 须上屏（⛔ 自造辞）。'''
    o = _run(tmp_path, u"未接", u"no_root",
             setres={"ok": True, "vault_root": u"D:/my_notes", "vault_root_src": u"env:PA_VAULT_DIR",
                     "state": u"no_root", "at": u"x", "changed": False,
                     "env_override": True, "note": NOTE},
             action="set", inputval=u"D:/my_notes")
    assert NOTE in o["text"], o["text"]
    assert u"env:PA_VAULT_DIR" in o["text"], o["text"]


def test_note_缺_反控_不现(tmp_path):
    u'''pm_1521 反控：回**无** `note` ⇒ 屏上 ⛔ 得现其字（⛔ 以固定辞充后端之值）。'''
    o = _run(tmp_path, u"未接", u"no_root",
             setres={"ok": True, "vault_root": u"D:/my_notes", "vault_root_src": u"配置:paths.vault_root",
                     "state": u"empty", "at": u"x", "changed": True, "env_override": False},
             action="set", inputval=u"D:/my_notes")
    assert NOTE not in o["text"], o["text"]


def test_note_唯后端之字面_非硬编(tmp_path):
    u'''pm_1521 一处定形：`note` 之字唯自后端之回（⛔ 前端硬编其辞）—— 换一字 ⇒ 屏随变。'''
    alt = u"后端之别一字面（探）"
    o = _run(tmp_path, u"未接", u"no_root",
             setres={"ok": True, "vault_root": u"D:/n", "vault_root_src": u"env:PA_VAULT_DIR",
                     "state": u"no_root", "at": u"x", "changed": False,
                     "env_override": True, "note": alt},
             action="set", inputval=u"D:/n")
    assert alt in o["text"], o["text"]
    assert NOTE not in o["text"], u"⛔ 前端硬编其辞"
