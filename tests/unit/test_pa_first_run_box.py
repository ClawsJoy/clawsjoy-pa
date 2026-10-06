# -*- coding: utf-8 -*-
u"""pm_1499 之测：首启盒渲「义」＋ 未接态明书其果（唯改 web/pa.html · 一处定形）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_first_run_box.py -q

判据：
  ⒜ 面之源**逐键渲后端之「义」**（⛔ 唯「键＝今」· ⛔ 前端自造辞）⇒「未接（选目录）」四字得以上屏
  ⒝ **未接** ⇒ 加一条**明书其果**（检索为空 ⇒ 本机事实族之问拒答 ⇒ 余者由模型答 · 走云端则出机）
  ⒞ **已接** ⇒ 该条 ⛔ 现（⛔ 恒现）
  反控：banner ⛔ 载绝对径 ／ ⛔ `removeChild(` ／ ⛔ `paDismissCard(`
  器取：以 node 跑**真 banner 之 `box()`**（DOM 桩 · 真函数 ⇒ ⛔ 以源码字面代屏）
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: 屏文之必经之字（未接态）
MISS_WORDS = (u"未接（选目录）", u"资料目录", u"检索面为空", u"一律拒答", u"出机")

_HARNESS = u"""
const fs=require('fs');
const src=fs.readFileSync(process.argv[2],'utf8');
const payload=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
function Node(tag){this.tag=tag;this.children=[];this.attrs={};this.innerHTML='';}
Node.prototype.setAttribute=function(k,v){this.attrs[k]=String(v);};
Node.prototype.getAttribute=function(k){return this.attrs[k];};
Node.prototype.appendChild=function(c){this.children.push(c);return c;};
global.document={createElement:function(t){return new Node(t);},body:new Node('body')};
global.fetch=function(){return Promise.resolve({ok:true,json:function(){return Promise.resolve(payload);}});};
eval(src);
function walk(n,acc){acc.push(n.innerHTML||'');for(const c of n.children)walk(c,acc);return acc;}
setTimeout(function(){process.stdout.write(walk(document.body,[]).join(String.fromCharCode(10)));},60);
"""


def _banner():
    u"""`web/pa.html` 之首启引导**行内脚本**（`pa/boot.js` 之前那段）。"""
    s = (ROOT / "web" / "pa.html").read_text(encoding="utf-8")
    head = s[:s.index("pa/boot.js")]
    st = head.rindex("<script>")
    return head[st + len("<script>"):head.index("</script>", st)]


def _need():
    return [{"话": u"你的数据在这台电脑上", "据": u"config（弱保证 · 唯字面扫）"}]


def _keys(vault_now):
    return [
        {"键": "PA_ORG_FACES",
         "义": u"组织版开关（功能级 · 默认关）—— 开 ⇒ 并入组织面；关 ⇒ 唯产品面「死件账」",
         "今": u"关（默认）"},
        {"键": "PA_WS_ROOT",
         "义": u"工作区根（产品级）—— 组织面之根；缺 ⇒ 组织面 ⛔ 入表",
         "今": u"未接"},
        {"键": "PA_VAULT_DIR",
         "义": u"知识库根（用户自选；亦可指配置 paths.vault_root）—— 缺 ⇒ 显「未接（选目录）」",
         "今": vault_now},
    ]


def _payload(vault_now):
    return {"ok": True, "须知": _need(), "模型": {"态": u"未接", "因": u"127.0.0.1:11434 无应答"},
            "数据目录": {"值": "", "源": u"未接"},
            "面之源": {"口径": u"「面之数」由三键定 —— 缺则面减（照实 · ⛔ 静默）", "键": _keys(vault_now)},
            "缺": []}


def _render(tmp_path, vault_now):
    u"""以 node 跑真 `box()`（真函数 · DOM 桩）⇒ 屏文。"""
    node = shutil.which("node")
    if not node:
        pytest.skip("node ⛔ 在 ⇒ 屏文之器取 ⛔ 得跑")
    (tmp_path / "banner.js").write_text(_banner(), encoding="utf-8")
    (tmp_path / "payload.json").write_text(json.dumps(_payload(vault_now), ensure_ascii=False),
                                           encoding="utf-8")
    (tmp_path / "harness.js").write_text(_HARNESS, encoding="utf-8")
    r = subprocess.run([node, str(tmp_path / "harness.js"), str(tmp_path / "banner.js"),
                        str(tmp_path / "payload.json")], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    return r.stdout


def test_源之_义_悉渲上屏_未接态(tmp_path):
    out = _render(tmp_path, u"未接")
    for w in MISS_WORDS:
        assert w in out, (w, out)
    assert u"组织版开关" in out, u"三键之「义」须各渲（⛔ 唯末键）"


def test_未接态_明书其果(tmp_path):
    out = _render(tmp_path, u"未接")
    assert u"检索面为空" in out and u"一律拒答" in out, out
    assert u"模型" in out and u"出机" in out, out


def test_已接态_该条不现(tmp_path):
    out = _render(tmp_path, "D:/kb")
    assert u"PA_VAULT_DIR＝D:/kb" in out, out
    assert u"一律拒答" not in out, u"已接 ⇒ 该条 ⛔ 得恒现"
    assert u"资料目录" not in out, out


def test_无值态_仍明书其果(tmp_path):
    u"""键在而「今」空（⛔ 静默之别形）⇒ 亦认「未接」（⛔ 一名蔽二态）。"""
    out = _render(tmp_path, "")
    assert u"一律拒答" in out, out


def test_banner_非屏_之戒():
    b = _banner()
    assert re.search(r"[A-Za-z]:[\\/]", b) is None, re.findall(r"[A-Za-z]:[\\/]", b)
    assert "removeChild(" not in b
    assert "paDismissCard(" not in b
    assert "/v9/pa/first_run" in b
    assert u"没读成" in b
