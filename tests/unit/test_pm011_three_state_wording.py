# -*- coding: utf-8 -*-
"""PM-011 任务 1 · 前端三态话术门（2026-09-30）。

病：`web/pa.html` 旧写法 `if(!d.success){ '\U0001F635 '+(d.error||'服务暂不可用') }`
把**五种不同载荷**压成同一句（recovery.py:392 previous_done ／:129 executing ／
:91 预算超限 ／ entry.py:152 seed 门 block ／ entry.py:99 seed_failed）。

本文件**不复制代码**：从 `web/pa.html` **原文抽出**分型函数与判据块，用 node 真跑。
判据（承 PM 原文）：J1 block 文案**含后端 reason 原文**；J2 无回执文案**命中「未取得回执」**；
J3 两者**不相同**。反例门：无回执 ⇒ ⛔ 不得出现任何后端 reason 字样；block ⇒ **必须**出现。
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PA = ROOT / "web" / "pa.html"
SCRATCH = ROOT / "data" / "tmp" / "_pm011_threestate"

START = "/* PM-011-BLOCK-START */"
END = "/* PM-011-BLOCK-END */"

# 一手载荷（逐字取自后端代码）
REASON = "未 seed（.agent_state.json 无 seed.source_path）⇒ 不得盘点/修改/产出结论"
BLOCK_PAYLOAD = {"success": False, "blocked": True, "status": "blocked", "reason": REASON,
                 "seed_status": None, "sandbox": "x", "blocked_goal": "goal_blocked_1"}
SEEDFAIL_PAYLOAD = {"success": False, "status": "seed_failed", "seed_error": True,
                    "message": "会话 sandbox seed 失败：X（查 V9_SEED_SOURCE / 磁盘）"}
EXECUTING_PAYLOAD = {"status": "executing", "task_id": "t1", "message": "计划已确认，V9 异步执行已启动。"}
PREVDONE_PAYLOAD = {"reply": "上次任务已完成。请下达新指令。", "status": "previous_done"}
BUDGET_PAYLOAD = {"plan_status": "confirmed", "message": "今日 Token 预算已超限(10/10)，自动确认计划。"}


def _pa() -> str:
    return io.open(PA, encoding="utf-8").read()


def _fn(src: str, name: str) -> str:
    """按花括号配平抽出 `function name(...){...}` 原文。"""
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


def _block() -> str:
    src = _pa()
    i = src.find(START)
    j = src.find(END)
    assert i > 0 and j > i, "未找到 PM-011 判据块标记"
    blk = src[i + len(START):j].strip()
    assert blk.startswith("{") and blk.endswith("}")
    return blk


def _run(block_js: str, scenarios: dict) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    src = _pa()
    js = (_fn(src, "paRespReason") + "\n" + _fn(src, "paRespKind") + "\n"
          "function run(scen){\n  const calls=[];\n"
          "  function addMsg(role,txt){ calls.push({k:'msg', role:String(role), txt:String(txt)}); }\n"
          "  function paSetState(k,v){ calls.push({k:'st', st:String(k), v:(v===undefined?'':String(v))}); }\n"
          "  function decide(d){\n" + block_js + "\n    return null;\n  }\n"
          "  decide(scen);\n  return calls;\n}\n"
          "const SCEN=" + json.dumps(scenarios, ensure_ascii=False) + ";\n"
          "const out={}; for(const kk of Object.keys(SCEN)) out[kk]=run(SCEN[kk]);\n"
          "console.log(JSON.stringify(out));\n")
    f = SCRATCH / "harness.js"
    io.open(f, "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _text(calls):
    return " || ".join(c["txt"] for c in calls if c["k"] == "msg")


def _states(calls):
    return " ".join(c.get("v", "") for c in calls if c["k"] == "st")


# ---- J1 / J2 / J3 ---------------------------------------------------------

def test_j1_block_text_contains_backend_reason():
    out = _run(_block(), {"block": BLOCK_PAYLOAD, "seedfail": SEEDFAIL_PAYLOAD})
    assert REASON in _text(out["block"]), "J1：block 文案里没有后端 reason 原文"
    assert SEEDFAIL_PAYLOAD["message"] in _text(out["seedfail"]), "J1：seed_failed 原文也应出现"


def test_j2_noreceipt_says_wei_qu_de_hui_zhi():
    out = _run(_block(), {"empty": {}, "null": None})
    for k in ("empty", "null"):
        assert "未取得回执" in _text(out[k]), "J2：%s 未命中「未取得回执」" % k


def test_j3_two_texts_differ():
    out = _run(_block(), {"block": BLOCK_PAYLOAD, "empty": {}})
    a, b = _text(out["block"]), _text(out["empty"])
    assert a != b, "J3：两种情形还是同一句话（又是一句兜底）"


# ---- 反例门 -------------------------------------------------------------

def test_neg_noreceipt_must_not_leak_any_reason():
    """反例：**同一个 payload 只把 reason 拿掉** ⇒ 归「无回执」 ⇒ ⛔ 不得出现 reason 字样。"""
    stripped = dict(BLOCK_PAYLOAD)
    stripped["reason"] = None
    out = _run(_block(), {"block_no_reason": stripped})
    t = _text(out["block_no_reason"])
    assert "未取得回执" not in t or REASON not in t
    assert REASON not in t, "反例失效：没拿到 reason，页面却冒出了 reason 原文"
    assert "未取得回执" in t or "拒绝" in t


def test_neg_block_must_show_reason():
    out = _run(_block(), {"block": BLOCK_PAYLOAD})
    assert REASON in _text(out["block"]), "反例失效：block 场景竟没出 reason 原文"


# ---- 我加的：受理类（非失败）⛔ 不许报成失败 --------------------------------

def test_accepted_kinds_are_not_reported_as_failure():
    out = _run(_block(), {"exec": EXECUTING_PAYLOAD, "prev": PREVDONE_PAYLOAD, "budget": BUDGET_PAYLOAD})
    for k in ("exec", "prev", "budget"):
        t, st = _text(out[k]), _states(out[k])
        assert "未取得回执" not in t, "%s：受理类被说成了「未取得回执」" % k
        assert "failed" not in st, "%s：受理类被报成 failed（上线就是「服务暂不可用」那种假失败）" % k


# ---- 齿：把新口径改回旧兜底 ⇒ 必须判红 ---------------------------------

def test_gate_has_teeth_fallback_removed_is_caught():
    mutant = _block().replace("未取得回执", "服务暂不可用")
    assert mutant != _block()
    out = _run(mutant, {"empty": {}})
    assert "未取得回执" not in _text(out["empty"]), "齿失效：改回兜底了还能命中新口径"


def test_static_no_fallback_expression_left():
    src = _pa()
    assert "d.error||'服务暂不可用'" not in src, "兜底表达式还在"
    assert START in src and END in src, "判据块标记缺失"
    assert "paRespKind" in src and "paRespReason" in src
