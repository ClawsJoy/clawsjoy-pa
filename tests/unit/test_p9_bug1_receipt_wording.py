# -*- coding: utf-8 -*-
"""P9 · BUG-1 负例门：**没落盘时，前端不许说「已落盘」**。

病（PM 2026-09-29 007 实测）：旧前端在 ``finally`` 里**无条件**写
``addLog('💾 本轮已落盘（本地状态 + 会话日志）')``，而该分支只调了 ``saveState()``
（localStorage）⇒ 后端一个字节没动，界面照样显示「已落盘」= 假绿。

本件补的正是 182 申报 §六-4 **自报未实测**的那条负例 —— 补的是**话术的方向性**：
不只证「真落盘时会说已落盘」，还要证「**没落盘时不会说已落盘**」。

三层判据，都不靠自觉：

1. **执行层**：node 跑 **从真实 ``web/pa.html`` 原文抽出**的判据块（move 而非 retype；
   从 ``const rc = paRun.receipt;`` 起、按**花括号配平**切到闭合处，原文原样字节）；
2. **反例齿**：把同一份抽出的判据块里 ``if(rc && rc.recorded)`` 改成恒真 ⇒
   下面的负例断言**必须判红** —— 证明这把尺能失败，不是装饰层（承 C18：判据必须能红）；
3. **历史红对照**：改前存底件 ``.rollback_codex/pa.html.before_p9_20260929_0900``
   那句**无条件**「已落盘」放同一执行面 ⇒ 负例判红（这就是改前的病象）。

本文件不改任何产品代码；临时 js 落仓内 scratch（``data/tmp/_p9_bug1_negative/``），
且**保留**作判据现场证据（承 PM 2026-09-29 审核 §四：落痕优于干净）。
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PA = ROOT / "web" / "pa.html"
OLD_PA = ROOT / ".rollback_codex" / "pa.html.before_p9_20260929_0900"
SCRATCH = ROOT / "data" / "tmp" / "_p9_bug1_negative"

_BLOCK_START = "const rc = paRun.receipt;"
_BLOCK_TAIL = "'P9 BUG-1');"
_OLD_UNCOND = "本轮已落盘（本地状态 + 会话日志）"
_CLAIM = "已落盘"
_DENY = "未落盘"

#: 后端回执样本（字段与 core/pa/gateway_routes.py:659-671 的实际回执同构）
RECORDED = {"recorded": True, "session_lines_before": 4, "session_lines_after": 6,
            "events_lines_before": 126, "events_lines_after": 127, "session_path": "s.jsonl"}
NOT_RECORDED = {"recorded": False, "session_lines_before": 4, "session_lines_after": 4,
                "events_lines_before": 127, "events_lines_after": 127,
                "session_path": "s.jsonl", "error": "disk full"}


def _node() -> str:
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    assert exe, "找不到 node（本判据靠它执行抽出的前端原码）"
    return exe


def _src(p: Path = PA) -> str:
    assert p.is_file(), "缺件：%s" % p
    return io.open(p, encoding="utf-8").read()


def _block() -> str:
    """从真实 pa.html 抽「已落盘 / 未落盘」判据块（原文原样字节，move 而非 retype）。

    切法＝**花括号配平**（首版按行切，切在 ``else`` 半截 ⇒ node 语法错）。
    本块内无字符串字面量含花括号，故计数可靠；切完再自证分子两头齐。
    """
    s = _src()
    i = s.find(_BLOCK_START)
    assert i > 0, "未找到判据块起点：%s" % _BLOCK_START
    j = s.find(_BLOCK_TAIL, i)
    assert j > i, "未找到 ok 分支的 P9 BUG-1 标记"
    k = s.find(_BLOCK_TAIL, j + 1)
    assert k > j, "未找到 warn 分支的 P9 BUG-1 标记"
    depth = 0
    opened = False
    e = i
    while e < len(s):
        ch = s[e]
        if ch == "{":
            depth += 1
            opened = True
        elif ch == "}":
            depth -= 1
            if opened and depth == 0:
                # `}else{` 处也归零 ⇒ 须看后随词；否则会切在 if 分支末尾（首版即栽在这）
                if not s[e + 1:e + 41].lstrip().startswith("else"):
                    e += 1
                    break
        e += 1
    blk = s[i:e]
    assert opened and depth == 0, "判据块花括号未配平（切面有误）"
    assert k < e, "warn 分支在配平块之外 ⇒ 切面有误"
    assert "if(rc && rc.recorded)" in blk, "判据块里没有 recorded 守卫 ⇒ 负例门无从谈起"
    assert "}else{" in blk and blk.rstrip().endswith("}"), "判据块缺 else 闭合 ⇒ 切面有误"

    # 忠实性（承反例齿逮到的第一版缺陷）：真码里本块**包在 try/catch 内**⇒ 执行面须同构。
    # 否则 `rc=null` 时 `rc.session_lines_before` 抛未捕获异常 ⇒ 负例②假红（不是真红）。
    _t = s.rfind("try{", 0, i)
    assert _t > 0 and "saveState();" in s[_t:i], "判据块前应有 try{ ... saveState();（切面有误）"
    _c = s.find("}catch(e){}", e)
    assert 0 < _c < e + 40, "判据块后应紧跟 }catch(e){}（切面有误）"
    return blk


def _run(block_js: str, scenarios: dict) -> dict:
    """把抽出的判据块放进执行面跑（stub addLog/saveState/paRun），回各场景的调用记录。"""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    js = (
        "function run(receipt){\n"
        "  const calls=[];\n"
        "  function addLog(t,l){ calls.push({t:String(t), l:(l===undefined?'':String(l))}); }\n"
        "  function saveState(){}\n"
        "  const paRun={receipt:receipt};\n"
        "  try{\n"
        + block_js
        + "\n  }catch(e){}\n"
        "  return calls;\n}\n"
        "const out={};\n"
        "for (const k of Object.keys(SCEN)) out[k]=run(SCEN[k]);\n"
        "console.log(JSON.stringify(out));\n"
    )
    f = SCRATCH / "harness.js"
    io.open(f, "w", encoding="utf-8", newline="\n").write(
        "const SCEN=" + json.dumps(scenarios, ensure_ascii=False) + ";\n" + js
    )
    r = subprocess.run([_node(), str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 执行失败 rc=%s\n%s" % (r.returncode, r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _claims_landed(calls) -> bool:
    """这一轮**有没有**在界面上说「已落盘」（且不是否定式）。"""
    for c in calls or []:
        if _CLAIM in c["t"] and _DENY not in c["t"]:
            return True
    return False


def _warns_not_landed(calls) -> bool:
    for c in calls or []:
        if _DENY in c["t"] and c["l"] == "warn":
            return True
    return False


# ---- 判据 1：执行层（正例 + 两条负例） -------------------------------------

def test_positive_true_receipt_says_landed():
    out = _run(_block(), {"ok": RECORDED})
    assert _claims_landed(out["ok"]), "真落盘（recorded=true）时反而没说「已落盘」"
    assert any(c["l"] == "ok" for c in out["ok"]), "真落盘应记 ok 级"


def test_negative_not_recorded_must_not_claim_landed():
    """⭐ PM 要的那条负例①：后端说没记上 ⇒ 前端**不许**说已落盘。"""
    out = _run(_block(), {"bad": NOT_RECORDED})
    assert not _claims_landed(out["bad"]), "后端 recorded=false ⇒ 前端仍说「已落盘」（假绿复发）"
    assert _warns_not_landed(out["bad"]), "后端 recorded=false ⇒ 前端没说「未落盘」"


def test_negative_no_receipt_must_not_claim_landed():
    """⭐ PM 要的那条负例②：**未取得回执**（null，前端 sendPA 的 ``d.persisted || null``）⇒ 同上。"""
    out = _run(_block(), {"none": None})
    assert not _claims_landed(out["none"]), "未取得回执 ⇒ 前端仍说「已落盘」（假绿复发）"
    assert _warns_not_landed(out["none"]), "未取得回执 ⇒ 前端没说「未落盘」"


# ---- 判据 2：这把尺有齿（去掉守卫 ⇒ 必须判红） ------------------------------

def test_gate_has_teeth_mutant_guard_is_caught():
    real = _block()
    mutant = real.replace("if(rc && rc.recorded)", "if(true)")
    assert mutant != real, "变异没生效（判据块已换形，请同步本测试）"
    out = _run(mutant, {"bad": NOT_RECORDED, "none": None})
    assert _claims_landed(out["bad"]), "齿失效：去掉守卫后负例①仍判绿 ⇒ 这把尺是装饰层"
    # 负例②（无回执）另有 try/catch 兜底：mutant 下 `rc.session_lines_before` 先抛异常
    # ⇒ 连 ok 分支的 addLog 都到不了 ⇒ 仍**不**说已落盘（这也是真码的行为，非本测试的宽容）。
    assert not _claims_landed(out["none"]), "无回执在 mutant 下竟也说了已落盘 ⇒ 与 try/catch 语义不符"


# ---- 判据 3：历史红对照（改前那行无条件「已落盘」） -------------------------

def test_historical_red_old_unconditional_line_is_caught():
    old = _src(OLD_PA)
    hits = [ln.strip() for ln in old.splitlines() if _OLD_UNCOND in ln]
    assert hits, "改前存底件里应有无条件「已落盘」那行：%s" % OLD_PA
    out = _run("  " + hits[0], {"none": None})
    assert _claims_landed(out["none"]), "历史红对照失效：旧行在「无回执」时竟没说已落盘"


def test_current_file_has_no_unconditional_landed_string():
    """静态面：改前那句无条件文案**不许**再出现在现值里。"""
    s = _src()
    assert _OLD_UNCOND not in s, "现值仍有改前那句无条件「已落盘」：%s" % _OLD_UNCOND
    assert "if(rc && rc.recorded)" in s, "现值缺 recorded 守卫"