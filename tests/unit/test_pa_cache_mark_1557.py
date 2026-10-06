# -*- coding: utf-8 -*-
u"""pm_1557 \u00a7\u4e8c.5 \u4e4b\u9f7f\uff08CW b2a5182 \u00b7 2026-10-06\uff09\u3002

\u4e00\u4e8b\uff1a\u590d\u7528\uff08\u540e\u7aef `/v9/pa/ask` \u4e4b `from_cache`\uff09\u21d2 \u5c4f\u4e0a\u300c\u91c7\u4e8e\u300d**\u5e76**\u4e66\u300c\u590d\u7528\u300d\uff08selfdesc.js `paSelfTag` \u00b7
\u5224\u4e00\u5904\uff08`paSelfJudgeRemember`\uff09\uff0f\u8f9e\u4e00\u5904\uff08`paSelfCacheMark`\uff09\uff09\uff1b\u7f3a\u952e \u21d2 \u2117 \u5192\u3002
  L1 \u6b63\u63a7\uff1a`from_cache=true` \u21d2 \u5176\u884c \u542b\u300c\u590d\u7528\u300d\u4e14 \u542b\u300c\u91c7\u4e8e\u300d\uff08\u4e14 \u300c\u590d\u7528\u300d\u552f 1\uff09\uff1b\u5e76 \u2014\u2014 \u65e0\u91c7\u6837\u523b \u21d2 \u2117 \u51fa\u590d\u7528\uff08\u4e8c\u7269\u4ff1\u987b\uff09\u3002
  L2 \u53cd\u63a7\uff1a`from_cache=false` \u21d2 \u2117 \u542b\u300c\u590d\u7528\u300d\u800c\u4ecd\u542b\u300c\u91c7\u4e8e\u300d\u3002
  L3 \u7f3a\u952e\u4e4b\u5b88\uff1a`from_cache` \u7f3a \u21d2 \u2117 \u5192\u300c\u590d\u7528\u300d \u2117 \u9759\u9ed8\uff08\u884c\u4ecd\u771f\u51fa\uff09\u3002
  L4 \u5e42\u7b49\u63a7\uff1a\u91cd\u6e32 \u21d2 \u9010\u5b57\u540c \u2117 \u500d\u589e\uff08\u300c\u590d\u7528\u300d\u4ecd\u552f 1\uff09\u3002
  " + chr(92) + u"u26a0 pm_1562 " + chr(92) + u"u00a7" + chr(92) + u"u4e8c.3（一处定形）：判 ／ 辞 今在 paSelfCacheStateOf ／ paSelfCacheMarkOf（本齿仍针 paSelfCacheMark 之旧径 · 行为一字不动）。

\u4ee5\u4f55\u5f62\u8c03\u7528\uff1apython -X utf8 -B -m pytest tests/unit/test_pa_cache_mark_1557.py -q
"""
from __future__ import annotations

import io, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDESC = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
SCRATCH = ROOT / "data" / "tmp" / "_cw_cache_mark1557"

MARK = u"\uff08\u590d\u7528 \u00b7 \u26d4 \u672c\u8f6e\u91cd\u626b\uff09"
REUSE = u"\u590d\u7528"
AT = u"\u91c7\u4e8e"
SNAP = u"2026-10-06 20:19:37"


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
__TAGFN__
var paSelfAskStat = {};
var O = {};
function run(g){ paSelfTagAt = ''; paSelfCacheReuse = null; paSelfJudgeRemember(g); return paSelfTag('fallback', null); }
var SNAP = '2026-10-06 20:19:37';
O.reuse    = run({from_cache:true,  judge:{face_snapshot_at:SNAP}});
O.hasAt    = paSelfTagAt.length > 0;
O.fresh    = run({from_cache:false, judge:{face_snapshot_at:SNAP}});
O.missing  = run({judge:{face_snapshot_at:SNAP}});
O.reuseB   = run({from_cache:true,  judge:{face_snapshot_at:SNAP}});
O.rerender = paSelfTag('fallback', null);
O.rerenderB = paSelfTag('fallback', null);
O.noAt = (function(){ paSelfTagAt = ''; paSelfCacheReuse = true; return paSelfTag('fallback', null); })();
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
                 .replace("__TAGFN__", _fn(s, "paSelfTag")))
    return _node(js, "mark")


def test_L1_pos_reuse_shows_both_at_and_reuse():
    o = _run()
    assert REUSE in o["reuse"], o["reuse"]
    assert AT in o["reuse"], o["reuse"]
    assert o["reuse"].count(REUSE) == 1, o["reuse"]
    assert o["reuse"].endswith(MARK), o["reuse"]
    assert SNAP in o["reuse"], o["reuse"]
    assert o["hasAt"] is True, o
    assert REUSE not in o["noAt"], o["noAt"]      # \u4e8c\u7269\u4ff1\u987b\uff1a\u65e0\u91c7\u6837\u523b \u21d2 \u2117 \u51fa\u590d\u7528
    assert AT not in o["noAt"], o["noAt"]


def test_L2_neg_fresh_has_no_reuse():
    o = _run()
    assert REUSE not in o["fresh"], o["fresh"]
    assert AT in o["fresh"], o["fresh"]


def test_L3_missing_key_guard_no_fabrication_no_silence():
    o = _run()
    assert REUSE not in o["missing"], o["missing"]
    assert AT in o["missing"], o["missing"]
    assert o["missing"] != "", o["missing"]


def test_L4_idempotent_rerender_no_doubling():
    o = _run()
    assert o["rerender"] == o["reuseB"], (o["rerender"], o["reuseB"])
    assert o["rerenderB"] == o["rerender"], (o["rerenderB"], o["rerender"])
    assert o["rerender"].count(REUSE) == 1, o["rerender"]
    assert o["rerender"].count(AT) == 1, o["rerender"]
