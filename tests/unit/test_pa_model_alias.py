# -*- coding: utf-8 -*-
u"""pm_1472 之测：**回填之别名归一 ＋ 未知名之显形 ＋ 存值唯实名**（CW b2a5182 · 2026-10-06）。

病（pm_1472 §一）：`pa_cfg.model` 存**别名**（老板之选 `deepseek-v4-flash`）⇒ 旧码 `id === want` 逐字比
  ⇒ ⛔ 命中 ⇒ **静默落 `default`（本机 7B）** ⇒ 老板之选被悄换且 **⛔ 显形**（注已书而码未做）。

判据（A1–A7）：
  A1 归一：别名 ⇒ **实名**（据**后端之响应**：行 `aliases[]` ／ 顶层 `model_aliases`）⇒ 选中该行；
     屏上有字（「原选…⇒ 已归正为…」）∧ `pa_cfg.model` 回写为**实名**（⛔ 落旧别名）。
  A2 未知名 ⇒ **显形**（「后端之表 ⛔ 含此名…⇒ 已按下之默认…」）∧ **⛔ 静默落默认**。
  A3 二态须别：「表未得」（`paModelState`）与「未知名」**⛔ 同形**（前者注空 ∧ select 显形；后者注有字）。
  A4 实名回填 ⇒ **无注**（⛔ 以注扰常例）。
  A5 存者唯实名：`saveCfg` 取 `paModelSel()`（实名 · 一处出）⇒ 别名 ⛔ 存底。
  A6 **⛔ 猜测**：归一只认后端所给之键值（⛔ 前缀剥 ／ ⛔ 模糊比）。
  A7 有齿：去归一（`paModelAliasMap` ⇒ `{}`）⇒ A1 须红（别名静默落默认 · 旧病重现）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_model_alias.py -q

本件**不复制代码**：config.js 之模型段（锚点定界）＋ tasks.js 之 `paEsc` 皆**抽原文**，以 `node` 真跑；
唯 `document` ／ `localStorage` ／ `fetch` ／ `PA_GAP` 为桩 —— 其 ＝ 本测之边界（⛔ 被审之逻辑）。
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import providers as PV  # noqa: E402

CONFIG_JS = ROOT / "web" / "pa" / "faces" / "config.js"
TASKS_JS = ROOT / "web" / "pa" / "faces" / "tasks.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_alias1472"

ANCHOR_A = u"var paModelRows = null;"
ANCHOR_B = u"function saveCfg(){"


def _fn(src: str, name: str) -> str:
    i = src.find("function " + name + "(")
    assert i > 0, "未找到函数 " + name
    d, opened, e = 0, False, i
    while e < len(src):
        c = src[e]
        if c == "{":
            d += 1
            opened = True
        elif c == "}":
            d -= 1
            if opened and d == 0:
                return src[i:e + 1]
        e += 1
    raise AssertionError("函数 " + name + " 花括号不配平")


def _config() -> str:
    return io.open(str(CONFIG_JS), encoding="utf-8").read()


def _block() -> str:
    s = _config()
    return s[s.index(ANCHOR_A):s.index(ANCHOR_B)]


def _payload() -> dict:
    return PV.public_view()


JS_HARNESS = u"""const window = {};
%s
const PA_GAP = { down: function(s){ return '\u672a\u63a5\uff1a' + s; },
                 fallback: function(k){ return '\u56de\u9000\u652f\uff1a' + k; } };
const API = '';
const LS = {};
const localStorage = { getItem: function(k){ return (k in LS) ? LS[k] : null; },
                       setItem: function(k, v){ LS[k] = String(v); } };
let RESP = null;
const fetch = function(u, o){ return Promise.resolve({ status: 200, json: function(){ return Promise.resolve(RESP); } }); };
let NOTE = null;
const SEL = { innerHTML: '', value: '', disabled: false, parentNode: { appendChild: function(n){ NOTE = n; } } };
const document = {
  getElementById: function(id){ if(id === 'cfgModel') return SEL;
    if(id === 'cfgModelNote') return NOTE; return null; },
  createElement: function(t){ return { id: '', style: {}, textContent: '', parentNode: null }; }
};
%s
let VIA = null;   /* pm_1504 §二：曝 paModelResolve 之 via（判「落默认之迹」· ⛔ 唯值比） */
const _paResolve0 = paModelResolve;
paModelResolve = function(rows, amap, want){ const r = _paResolve0(rows, amap, want); VIA = r.via; return r; };
const WANT = %s, PAYLOAD = %s;
(async function(){
  LS['pa_cfg'] = JSON.stringify({chan: 'x', model: WANT, appr: 'y', vault: true});
  RESP = PAYLOAD;
  await paModelFill(WANT);
  const opts = (SEL.innerHTML.match(/value="[^"]*"/g) || []).map(function(s){ return s.slice(7, -1); });
  console.log(JSON.stringify({sel: SEL.value, note: (NOTE ? NOTE.textContent : null),
    stored: JSON.parse(LS['pa_cfg']).model, disabled: SEL.disabled, opts: opts, via: VIA}));
})();
"""


def _run(want: str, payload=None, block: str = None) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    paesc = _fn(io.open(str(TASKS_JS), encoding="utf-8").read(), "paEsc")
    js = (JS_HARNESS % (paesc, (block if block is not None else _block()),
                        json.dumps(want, ensure_ascii=False),
                        json.dumps(payload if payload is not None else _payload(), ensure_ascii=False)))
    f = SCRATCH / "alias_harness.js"
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


ALIAS = u"deepseek-v4-flash"
REAL = u"deepseek-flash"


# ============================ A1 归一 ============================

def test_A1_别名归一为先实名且回写实名():
    out = _run(ALIAS)
    assert out["sel"] == REAL, u"别名 ⛔ 归一（选中＝%r）" % out["sel"]
    assert u"归正" in (out["note"] or ""), u"归正须有字（⛔ 静默）：%r" % out["note"]
    assert ALIAS in out["note"] and REAL in out["note"], out["note"]
    assert out["stored"] == REAL, u"存底须实名（⛔ 落旧别名）：%r" % out["stored"]


# ============================ A2 未知名 ============================

def test_A2_未知名须显形且不静默落默认():
    out = _run(u"glm-4-air")
    assert out["sel"] and out["sel"] != u"glm-4-air", u"未知名 ⛔ 得被选中：%r" % out["sel"]
    n = out["note"] or u""
    assert u"glm-4-air" in n, u"未知名须显其名（⛔ 静默）：%r" % n
    assert u"\u26d4 \u542b" in n, u"须明书「表 ⛔ 含此名」：%r" % n
    assert out["sel"] in n, u"须明书所按之默认：%r" % n


# ============================ A3 二态须别 ============================

def test_A3_表未得与未知名不同形():
    miss = _run(ALIAS, payload={"ok": True})          # ⛔ 带 models_table ⇒ 表未得之态
    unk = _run(u"glm-4-air")
    assert miss["disabled"] is True and len(miss["opts"]) == 1, miss
    assert (miss["note"] or u"") == u"", u"表未得之态 ⛔ 得留注（与未知名之别）：%r" % miss["note"]
    assert unk["disabled"] is False and len(unk["opts"]) > 1, unk
    assert (unk["note"] or u"") != u"", unk


# ============================ A4 实名回填无注 ============================

def test_A4_实名回填无注():
    out = _run(REAL)
    assert out["sel"] == REAL, out
    assert (out["note"] or u"") == u"", u"常例 ⛔ 得留注：%r" % out["note"]
    assert out["stored"] == REAL, out


# ============================ A5 存者唯实名 ============================

def test_A5_存者唯实名且一处出():
    c = _config()
    assert u"model:(paModelSel()||paModelKept)" in c, u"saveCfg 须取实名（一处出）"
    assert u"paModelKept = String(sel.value || '')" in c, u"kept 亦须实名"


# ============================ A6 ⛔ 猜测 ============================

def test_A6_归一只认后端所给之键值():
    c = _config()
    body = _fn(c, "paModelAliasMap")
    for bad in ("startsWith", "indexOf", "replace", "toLowerCase", "split"):
        assert bad not in body, u"归一则中见「%s」＝ 猜测之嫌（⛔ 前缀剥 ／ 模糊比）" % bad
    assert u"d.model_aliases" in body, u"顶层归一须自后端之响应出"
    assert u"r.aliases" in body or u".aliases" in body, u"行级 aliases 须用"


# ============================ A7 齿 ============================

def test_A7_齿_去归一则旧病重现():
    # 齿之的（pm_1504 §二）：⛔ 判「值 ⛔ 等」—— 默认已易为**云端实名**（pm_1471 ／ 1477 之裁）
    #   ⇒ 挖去归一后所落之默认**其值即实名** ⇒ 旧断言 `sel != REAL` 失据（值可同 ⇒ 判须另立）。
    #   改判**「落默认之迹」**：via（paModelResolve 之出）＋ 注 ＋ 存底 —— 三者共证（⛔ 以「值之异」为唯一据）。
    dft = str((_payload().get("default") or {}).get("model") or "")
    blk = _block()
    head = u"function paModelAliasMap(rows, d){"
    assert head in blk
    mutant = blk.replace(head, head + u"\n  return {};", 1)
    live = _run(ALIAS)                    # 活件（归一在）：别名 ⇒ 归正
    dead = _run(ALIAS, block=mutant)      # 挖归一：别名 ⇒ 未知名 ⇒ 按默认 ＋ 显形
    # 证一 · 活件之迹：via='alias' ＋ 归正之注 ＋ 存底回写实名。
    assert live["via"] == u"alias", u"有归一则 via 须为 alias：%r" % live
    assert u"已归正为" in (live["note"] or u""), live["note"]
    assert live["sel"] == REAL and live["stored"] == REAL, live
    # 证二 · 挖归一之迹：via=''（落默认）＋ 未知名之注（含其名）＋ 存底 ⛔ 改（未知名 ⛔ 回写）。
    assert dead["via"] == u"", u"挖归一 ⇒ via 须空（落默认之迹 · ⛔ 值之异）：%r" % dead
    assert u"⛔ 含此名" in (dead["note"] or u""), dead["note"]
    assert ALIAS in (dead["note"] or u""), u"未知名须显其名：%r" % dead["note"]
    assert dead["stored"] == ALIAS, u"挖归一 ⇒ 存底 ⛔ 得改：%r" % dead["stored"]
    # 其的（明书）：未知名 ⇒ **按默认** ＋ 显形 —— ⛔ 以「值之异」为唯一据（值可同 · 今即同）。
    assert dead["sel"] == dft, u"未知名 ⇒ 须按默认（%r）：%r" % (dft, dead["sel"])
    assert dead["note"] != live["note"], u"二路之迹须别：%r" % dead["note"]
