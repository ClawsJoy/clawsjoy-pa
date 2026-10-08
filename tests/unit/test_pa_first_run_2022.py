# -*- coding: utf-8 -*-
u"""pm_2022 §二 ／ pm_2025 §二.3⒜ ／ pm_2028 §三・§四.1 之齿 —— **初访态之首启卡**（字与位）。

一事（pm 一手 · 截图 _pm/_accept_9011/01 ／ _accept_9011_w1024/01）：初访之「第一次用」卡
  **展开（八行）**⇒ **占主区之半**，其体含「缺什么，上面就写什么 —— 未验证」（**自我怀疑之辞** ·
  违 P1 ／ §三 不该有 #4）＋ 二处「**工程注记**」之字面。⇒ 三修（唯初访态为据 · ⛔ 以现行折叠态充之）：
  ⒜ 首屏唯**一条可退之窄提示**（诸项入折 · ⛔ 占主区）⒝ 自我怀疑之辞**面闸**（⛔ 上屏）
  ⒞ 折名改**人话**「来源 ／ 详情」（「工程注记」四字 ⛔ 入首屏字面）。

判据（**渲之字** · 非源码字面 —— 承 pm_2028 §一 之「取样法之戒」）：
  F1 首屏（**祖链判**：未开之 details 内者 ⛔ 计）⛔ 载「缺什么」／「未验证」／「工程注记」。
  F2 首屏载窄提示 ＋ 折名「来源 ／ 详情」∧ 折标可见（祖链判：summary 计）。
  F3 正控：同一次渲之**全部**之字（含折内）**必含**被移之项（「模型之路」／「依据：」／「缺什么」）
     ⇒ 证「⛔ 在首屏」非因「字 ⛔ 在」（免「空断言」之假绿）。
  F4 位：首启盒之直子 ≤ 4（头 ／ 提示 ／ 折 ／ 收）—— ⛔ 诸项平铺首屏。
  F5 反控（⛔ 丢信息）：被闸之项之「据」仍在盒内（折中「依据：」列）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_first_run_2022.py -q --basetemp=D:/clawsjoy_v9/data/tmp/_pt2022
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: 首屏（祖链判）⛔ 得见者
BAN = (u"缺什么", u"未验证", u"工程注记", u"⛔ 假装能用")
#: 首屏须见者（窄提示 ＋ 折名）
NEED = (u"第一次用", u"点开即见", u"来源 ／ 详情")
#: 折内须在者（＝被移之项 · 正控之证）
INFOLD = (u"• 模型之路：", u"• 依据：")

_HARNESS = u"""
const fs=require('fs');
const src=fs.readFileSync(process.argv[2],'utf8');
const payload=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
function N(tag){this.tag=tag||'';this.children=[];this.attrs={};this.innerHTML='';}
N.prototype.setAttribute=function(k,v){this.attrs[k]=String(v);};
N.prototype.getAttribute=function(k){return this.attrs[k];};
N.prototype.appendChild=function(c){this.children.push(c);return c;};
global.document={createElement:function(t){return new N(t);},body:new N('body')};
global.fetch=function(){return Promise.resolve({ok:true,json:function(){return Promise.resolve(payload);}});};
eval(src);
/* 首屏之字（祖链判）：凡入未开之 details 者 ⛔ 计（唯其 summary 计）；余皆计 innerHTML ＋ 递归。 */
function screen(n,acc){acc.push(n.innerHTML||'');
  for(const c of n.children){ if(c.tag==='details'){ for(const s of c.children){ if(s.tag==='summary'){acc.push(s.innerHTML||'');} } } else { screen(c,acc); } }
  return acc;}
function all(n,acc){acc.push(n.innerHTML||''); for(const c of n.children){all(c,acc);} return acc;}
setTimeout(function(){
  const box=document.body.children[0]||new N('none');
  const out={screen:screen(box,[]).join(String.fromCharCode(10)),
             all:all(box,[]).join(String.fromCharCode(10)),
             kids:box.children.map(function(c){return c.tag;})};
  process.stdout.write(JSON.stringify(out));
},80);
"""


def _banner():
    s = (ROOT / "web" / "pa.html").read_text(encoding="utf-8")
    head = s[:s.index("pa/boot.js")]
    st = head.rindex("<script>")
    return head[st + len("<script>"):head.index("</script>", st)]


def _payload():
    u"""照本机后端  之真形（须知含「缺什么…」那一项 —— 即被闸者）。"""
    return {"ok": True,
            "须知": [
                {"话": u"你的数据在这台电脑上：D:/kb", "据": u"config"},
                {"话": u"本产品**不自动上传**你的数据，也**没有**遥测。", "据": u"器核（弱保证 · 唯字面扫）：0 处"},
                {"话": u"AI 走**本机**模型 —— 现在：**未接**。", "据": u"127.0.0.1:11434 无应答"},
                {"话": u"云端密钥：本机**未配**（正常 —— 交付包里本来就没有这一件）。", "据": u"未核：无"},
                {"话": u"缺什么，上面就写什么 —— ⛔ 假装能用。", "据": u"「缺」列 0 项"}],
            "模型": {"态": u"未接", "因": u"127.0.0.1:11434 无应答"},
            "数据目录": {"值": u"D:/clawsjoy_v9/data/v9", "源": u"env:PA_WS_ROOT"},
            "面之源": {"口径": u"「面之数」由三键定", "键": [
                {"键": "PA_ORG_FACES", "义": u"组织版开关", "今": u"关（默认）", "态": u"empty"},
                {"键": "PA_VAULT_DIR", "义": u"知识库根（用户自选）", "今": u"D:/kb",
                 "源": u"env:PA_VAULT_DIR", "态": u"ok"}]},
            "缺": []}


def _render(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node ⛔ 在 ⇒ 栅之字 ⛔ 得取")
    (tmp_path / "b.js").write_text(_banner(), encoding="utf-8")
    (tmp_path / "p.json").write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "h.js").write_text(_HARNESS, encoding="utf-8")
    r = subprocess.run([node, str(tmp_path / "h.js"), str(tmp_path / "b.js"), str(tmp_path / "p.json")],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_F3_正控_全字含被移之项(tmp_path):
    u"""正控（先跑）：同一次渲之**全部**之字须含被移之项 —— 否则 F1 之「⛔ 在首屏」为空断言。
    ⚠ 「缺什么」一项系**奉命而删**（pm_2022 §二.⒝ 逐字「删」）⇒ 其**句**全盒皆无（本齿一并钉之），
      而其**事**仍在（「据」入折中「依据：」列 ⇒ F5 之反控）。"""
    o = _render(tmp_path)
    for k in INFOLD:
        assert k in o["all"], u"正控：被移之项须**在盒内**（否则 F1 假绿）：" + k

    assert u"缺什么" not in o["all"], u"奉命而删（pm_2022 §二.⒝）：其句全盒皆无（其事见 F5）"


def test_F1_首屏_勿载自我怀疑与工程字(tmp_path):
    u"""F1 首屏（祖链判）⛔ 载「缺什么」／「未验证」／「工程注记」／「⛔ 假装能用」。"""
    o = _render(tmp_path)
    for bad in BAN:
        assert bad not in o["screen"], u"首屏 ⛔ 得见：" + bad + u"\n首屏 ＝ " + o["screen"][:400]


def test_F2_首屏_窄提示与折名(tmp_path):
    u"""F2 首屏载窄提示 ＋ 折名「来源 ／ 详情」（折标可见 ⇒ 祖链判之 summary 计入）。"""
    o = _render(tmp_path)
    for k in NEED:
        assert k in o["screen"], u"首屏须见：" + k + u"\n首屏 ＝ " + o["screen"][:400]


def test_F4_位_首启盒直子不逾四且屏文唯头与提示(tmp_path):
    u"""F4 位：盒之直子 ≤ 4（头 ／ 提示 ／ 折 ／ 收）—— ⛔ 诸项平铺首屏（pm_2022 §二.⒜）。"""
    o = _render(tmp_path)
    assert len(o["kids"]) <= 4, o["kids"]
    assert o["kids"].count("details") == 1, o["kids"]
    assert u"每次" not in o["screen"] and u"• 你的数据" not in o["screen"],         u"首屏 ⛔ 得平铺须知（诸项入折）：" + o["screen"][:400]


def test_F5_反控_被闸之项之据仍在盒内(tmp_path):
    u"""F5 反控（⛔ 丢信息）：被闸之项之「据」（）仍在折中「依据：」列。"""
    o = _render(tmp_path)
    assert u"• 依据：「缺」列 0 项" in o["all"], o["all"][:400]
