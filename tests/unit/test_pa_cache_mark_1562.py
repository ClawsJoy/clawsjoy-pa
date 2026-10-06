# -*- coding: utf-8 -*-
u"""pm_1562 §二.5 之齿（CW b2a5182 · 2026-10-06）。

一事：`paSelfJudgeText`（判据行 · 「· 采于」支）亦须挂「复用」（逐字同辞）——
  判 ／ 辞 一处定形（`paSelfCacheStateOf` ／ `paSelfCacheMarkOf`）；判取**本轮之回** `g.from_cache`（⛔ 全局残）。
  L1 正控：`from_cache=true` ⇒ 判据行 含「复用」且 含「采于」（且「复用」唯 1）。
  L2 反控：`from_cache=false` ⇒ ⛔ 含「复用」而仍含「采于」。
  L3 缺键之守：`from_cache` 缺 ⇒ ⛔ 冒「复用」 ∧ ⛔ 静默（行仍真出）。
  L4 异轮之控：`g` 无 `from_cache` 而全局 `paSelfCacheReuse=true` ⇒ ⛔ 出「复用」（要二之据）；并控无 `g` ⇒ 取全局（paSelfTag 之径照旧）。
  L5 一处定形（结构）：全件 `from_cache === true` 之命中唯 1 ∧ 复用辞之字面唯 1（⛔ 二处各写）。

以何形调用：python -X utf8 -B -m pytest tests/unit/test_pa_cache_mark_1562.py -q
"""
from __future__ import annotations

import io, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_cache_mark1562"

MARK = u"\uff08\u590d\u7528 \u00b7 \u26d4 \u672c\u8f6e\u91cd\u626b\uff09"
REUSE = u"\u590d\u7528"
AT = u"\u91c7\u4e8e"
SNAP = u"2026-10-06 20:19:37"
TAIL = u"\uff5c\u6e90 /v9/pa/ask \u4e4b judge"


def _src() -> str:
    return io.open(str(SDESC), encoding="utf-8").read()


def _fn(src: str, name: str) -> str:
    i = src.find("function " + name + "(")
    assert i > 0, u"\u672a\u627e\u5230\u51fd\u6570 " + name
    d, opened, e = 0, False, i
    while e < len(src):
        c = src[e]
        if c == "{":
            d += 1; opened = True
        elif c == "}":
            d -= 1
            if opened and d == 0:
                return src[i:e + 1]
        e += 1
    raise AssertionError(u"\u51fd\u6570 " + name + u" \u82b1\u62ec\u53f7\u4e0d\u914d\u5e73")


def _decl(src: str, prefix: str) -> str:
    for ln in src.split("\n"):
        if ln.startswith(prefix):
            return ln
    raise AssertionError(u"\u672a\u627e\u5230\u58f0\u660e " + prefix)


def _node(js: str, tag: str) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    f = SCRATCH / (tag + ".js")
    io.open(str(f), "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node \u5931\u8d25 rc=%s\n%s" % (r.returncode, r.stderr[-900:])
    return json.loads(r.stdout.strip().splitlines()[-1])


HARNESS = u"""__DECL_AT__
__DECL_CACHE__
__JUDGEOFFN__
__JUDGEREM__
__STATEFN__
__MARKOF__
__MARKFN__
__JUDGETEXT__
var paSelfAskStat = {};
var PA_STAMP = {fmt:function(s){ return String(s == null ? '' : s); }};
var SNAP = '2026-10-06 20:19:37';
var O = {};
function mk(g){ paSelfCacheReuse = null; paSelfJudgeRemember(g); return g; }
O.pos   = paSelfJudgeText(mk({from_cache:true,  judge:{face_snapshot_at:SNAP}}));
O.neg   = paSelfJudgeText(mk({from_cache:false, judge:{face_snapshot_at:SNAP}}));
O.miss  = paSelfJudgeText(mk({judge:{face_snapshot_at:SNAP}}));
paSelfCacheReuse = true;
O.other = paSelfJudgeText({judge:{face_snapshot_at:SNAP}});
O.markGlobal = paSelfCacheMark();
console.log(JSON.stringify(O));
"""


def _run() -> dict:
    s = _src()
    js = (HARNESS.replace("__DECL_AT__", _decl(s, "let paSelfTagAt = "))
                 .replace("__DECL_CACHE__", _decl(s, "let paSelfCacheReuse = "))
                 .replace("__JUDGEOFFN__", _fn(s, "paSelfJudgeOf"))
                 .replace("__JUDGEREM__", _fn(s, "paSelfJudgeRemember"))
                 .replace("__STATEFN__", _fn(s, "paSelfCacheStateOf"))
                 .replace("__MARKOF__", _fn(s, "paSelfCacheMarkOf"))
                 .replace("__MARKFN__", _fn(s, "paSelfCacheMark"))
                 .replace("__JUDGETEXT__", _fn(s, "paSelfJudgeText")))
    return _node(js, "mark1562")


def test_L1_pos_judge_line_shows_both_at_and_reuse():
    o = _run()
    assert REUSE in o["pos"], o["pos"]
    assert AT in o["pos"], o["pos"]
    assert o["pos"].count(REUSE) == 1, o["pos"]
    assert o["pos"].endswith(MARK + TAIL), o["pos"]
    assert SNAP in o["pos"], o["pos"]


def test_L2_neg_fresh_has_no_reuse():
    o = _run()
    assert REUSE not in o["neg"], o["neg"]
    assert AT in o["neg"], o["neg"]


def test_L3_missing_key_guard_no_fabrication_no_silence():
    o = _run()
    assert REUSE not in o["miss"], o["miss"]
    assert AT in o["miss"], o["miss"]
    assert o["miss"] != "", o["miss"]


def test_L4_other_round_control_uses_g_not_global():
    o = _run()
    assert REUSE not in o["other"], o["other"]
    assert AT in o["other"], o["other"]
    assert REUSE in o["markGlobal"], o["markGlobal"]


def test_L5_single_definition_site():
    s = _src()
    assert s.count("from_cache === true") == 1, u"from_cache === true \u975e\u4e00\u5904"
    assert s.count(MARK) == 1, u"\u590d\u7528\u8f9e\u4e4b\u5b57\u9762\u975e\u4e00\u5904"