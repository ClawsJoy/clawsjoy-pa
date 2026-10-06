# -*- coding: utf-8 -*-
u"""probe_line_ref_semantics.py —— 「手书行号引」之**语义探针**（报器 · ⛔ 闸 · ⛔ 定红）。

承：pm_1431 §二.5（先作「报器」测假阳率 · 方升为闸）｜pm_1427 §二.3（界内 287 ⇒ 加「语义探针」之器）｜
    pm_1435 §二.2（准造 · 造毕先跑一次 ⇒ 报三类之计数 ＋ 疑漂抽样 30 之目验果）。

其的：`scan_line_refs.py` 唯判「所引之行号是否在目标之界内」⇒ **界内 287 条之语义未知**
      （其中「已写且漂」者 ⇒ **假据**）。本器**抽锚 ⇒ 取段 ⇒ 判**：所引之段是否仍含「所引之名」。

⚠ **四限（要紧 · ⛔ 掩）**：
  ① **抽锚为启发式** —— 唯取**反引号内**之标识符（∨ 径之末段之名）⇒ **⛔ 完备之词法**
     （自然语言之指代 ／ ⛔ 反引号之引 ⇒ 抽 ⛔ 得 ⇒ 判「无法判」· 单列）。
  ② **`k` 为经验值** —— 无 `b` 之引 ⇒ 取 `a ± k`（`k ＝ 3`）之窗 ⇒ **⛔ 必有据**。
  ③ **符号定义在段外而用于段内** ⇒ **假红之险**（段内用 `render` 而定义在别处 ⇒ 判「疑漂」而实非漂）。
  ④ **注中之引（害小）与判中之引（害大）本器 ⛔ 分** —— 二者之价 ⛔ 同。
⭐ **本器为「报器」**：**⛔ 定红**（⛔ 使 CI 红）⇒ 唯出三类之计数 ＋ 逐条（供人裁）。
⭐ 治本 ＝ **律（新引 ⇒ 用符号之锚）**（承 pm_1431 §二.5 ／ pm_1435 §二.4）；本器 ＝ **兜底**
   （治**存量**之「已写且漂」）⇒ **⛔ 以探针代律**。

出口码：0 ＝ 跑毕（无论「疑漂」几何 · **报器**）｜2 ＝ 用法错。
⭐ `--json` ⇒ 全录（供复算）；`--self-test` ⇒ 纯内存之反例门（含**反控三**）。
"""
import argparse
import importlib.util
import io
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCAN = os.path.join(ROOT, "scripts", "dev", "scan_line_refs.py")

V_OK = u"准"
V_DRIFT = u"疑漂"
V_NA = u"无法判"

BT = re.compile(u"`([^`]+)`")
IDENT = re.compile(u"^[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff.]*$")
K_DEFAULT = 3


def load_scan(path=SCAN):
    spec = importlib.util.spec_from_file_location("scan_line_refs", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def spans_of(text):
    u"""一行文本之反引号跨 ⇒ list（逐跨之原文）。"""
    return [m.group(1) for m in BT.finditer(text or u"")]


def anchor_of_span(s):
    u"""一跨 ⇒ 锚（∨ None）：径 ⇒ 末段之名（去扩展名）；标识符 ⇒ 其末点段；否则 None。"""
    s = s.strip().rstrip(u"()")
    s = re.sub(u"[:：]\\d+(\\s*[-~\u2013\u2014]\\s*\\d+)?$", u"", s).strip()
    if not s:
        return None
    if u"/" in s or u"\\" in s:
        base = re.split(u"[/\\\\]", s)[-1]
        return os.path.splitext(base)[0] or None
    s = s.split(u".")[-1] if u"." in s and IDENT.match(s) else s
    return s if (IDENT.match(s) and len(s) >= 3) else None


def anchors_of(text):
    u"""引处之锚集 S（反引号内之标识符 ∪ 径之末段之名）。"""
    out = set()
    for sp in spans_of(text):
        a = anchor_of_span(sp)
        if a:
            out.add(a)
    return out


def cite_window(root, cite, at):
    u"""引处之行 N ± 1（夹于档界）⇒ 其文。"""
    L = io.open(os.path.join(root, cite), encoding="utf-8", errors="replace").read().split("\n")
    i = at - 1
    return "\n".join(L[max(0, i - 1):i + 2])


def seg_window(root, tgt, a, b, k=K_DEFAULT):
    u"""目标之段 ⇒ (a2, b2, 文)（无 b ⇒ a ± k · 夹于档界）。"""
    L = io.open(os.path.join(root, tgt), encoding="utf-8", errors="replace").read().split("\n")
    n = len(L)
    if b:
        a2, b2 = a, b
    else:
        a2, b2 = a - k, a + k
    a2, b2 = max(1, a2), min(max(n, 1), b2)
    return a2, b2, "\n".join(L[a2 - 1:b2])


def judge_row(root, r, k=K_DEFAULT):
    u"""单引之判 ⇒ dict（anchors ／ seg ／ verdict）。"""
    mm = None
    m = None
    if r.get("ref"):
        m = re.match(u"^.*?[:：](\\d{1,5})(?:\\s*[-~\u2013\u2014]\\s*(\\d{1,5}))?$", r["ref"])
    a = int(m.group(1)) if m else 1
    b = int(m.group(2)) if (m and m.group(2)) else None
    S = anchors_of(cite_window(root, r["cite"], r["at"]))
    a2, b2, seg = seg_window(root, r["tgt"], a, b, k)
    if not S:
        v = V_NA
    elif any(s in seg for s in S):
        v = V_OK
    else:
        v = V_DRIFT
    return {"cite": r["cite"], "at": r["at"], "ref": r["ref"], "tgt": r["tgt"],
            "anchors": sorted(S), "seg": [a2, b2], "verdict": v}


def probe(root=ROOT, k=K_DEFAULT):
    u"""面 ＝ `scan_line_refs` 之**界内**（其越界 ／ ⛔可寻 已另定性 ⇒ ⛔ 入本器）。"""
    m = load_scan()
    rows = [r for r in m.scan(root) if r["tgt"] and r["verdict"] == m.V_IN]
    return [judge_row(root, r, k) for r in rows]


def _self_test():
    u"""反例门（临时夹具 · ⛔ 依仓之现状）：正控 ／ **反控三** ／ 无法判 逐格验。"""
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="probe_selftest_")
    ok, tot = 0, 0
    def rep(name, got, want):
        nonlocal ok, tot
        tot += 1
        hit = got == want
        ok += 1 if hit else 0
        print(u"  %s %s ⇒ %s（望 %s）" % (u"OK " if hit else u"✗ ", name, got, want))
    try:
        # 夹具：目标档 t.py（含 `resolve_paths` 段）；引档 c.py
        io.open(os.path.join(d, "t.py"), "w", encoding="utf-8", newline="\n").write(
            u"# 头\n\ndef other():        # 1:2\n    return 1\n\ndef resolve_paths():  # 5\n    return {'render': 1}\n")
        # 引处之三例：准（锚 `resolve_paths` 在段内）／疑漂（锚 `zzz_missing` ⛔ 在）／无法判（⛔ 反引号）
        io.open(os.path.join(d, "c.py"), "w", encoding="utf-8", newline="\n").write(
            u"# 见 t.py:%d 之 `resolve_paths()`\n" % 5 + u"\n" * 8 +
            u"# 见 t.py:%d 之 `zzz_missing()`\n" % 5 + u"\n" * 8 +
            u"# 见 t.py:%d（无反引号之引）\n" % 5)
        base = {"tgt": "t.py"}
        r1 = judge_row(d, dict(base, cite="c.py", at=1, ref="t.py:%d" % 5))
        r2 = judge_row(d, dict(base, cite="c.py", at=10, ref="t.py:%d" % 5))
        r3 = judge_row(d, dict(base, cite="c.py", at=19, ref="t.py:%d" % 5))
        rep(u"① 正控（已知准 ⇒ 判「准」· 防器死）", r1["verdict"], V_OK)
        rep(u"② 反控（已知漂 ⇒ 判「疑漂」· 有齿）", r2["verdict"], V_DRIFT)
        rep(u"③ 无法判（⛔ 反引号 ⇒ 单列 · ⛔ 计红 ∧ ⛔ 计绿）", r3["verdict"], V_NA)
        # ④ 坏口径对照（唯判「S 非空 ⇒ 准」）⇒ 对**已知漂亦放行** ⇒ 证本条有齿
        bad = [(V_OK if x["anchors"] else V_NA) for x in (r1, r2)]
        rep(u"④ 坏口径对照（唯判 S 非空 ⇒ 准 ⇒ 对已知漂**放行**）", bad, [V_OK, V_OK])
        rep(u"④b 本条 ⇒ 对已知漂**⛔ 放行**（有齿）", [r1["verdict"], r2["verdict"]], [V_OK, V_DRIFT])
        # ⚠ 夹具之「行号」以 `%d` **占位**（—— 一处字面即为本器之真引 ⇒ 必自命中·假据）
        rep(u"⑤ 锚之抽（`core/pa/roster.py:%d` ⇒ `roster`）" % 212,
            sorted(anchors_of(u"引 `core/pa/roster.py:%d` 之 `load()`" % 212)), sorted([u"roster", u"load"]))
        rep(u"⑥ ⛔ 反引号之引 ⇒ S ＝ ∅（无据 ⇒ 判「无法判」）", sorted(anchors_of(u'引 "core/lib/paths.py:%d" 而已' % 97)), [])
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print(u"  => self-test %s（%d/%d）" % (u"OK" if ok == tot else u"FAIL", ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=u"「手书行号引」之语义探针（报器 · ⛔ 闸）")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--k", type=int, default=K_DEFAULT)
    ap.add_argument("--json", action="store_true", help=u"全录（供复算）")
    ap.add_argument("--sample", type=int, default=0, help=u"抽样 N 条「疑漂」（逐条附锚 ＋ 段之首尾）")
    ap.add_argument("--self-test", action="store_true", help=u"反例门（含反控三）")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    rows = probe(a.root, a.k)
    cnt = Counter(r["verdict"] for r in rows)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    print(u"语义探针（报器 · ⛔ 定红 · 面 ＝ scan_line_refs 之「界内」%d 条）" % len(rows))
    print(u"三类 ｜ 准 %d ／ 疑漂 %d ／ 无法判 %d（k ＝ %d）"
          % (cnt.get(V_OK, 0), cnt.get(V_DRIFT, 0), cnt.get(V_NA, 0), a.k))
    print(u"⚠ 四限：抽锚启发式 ／ k 经验值 ／ 定义在段外而用于段内 ⇒ 假红之险 ／ 注中与判中之引 ⛔ 分")
    if a.sample:
        dr = [r for r in rows if r["verdict"] == V_DRIFT][:a.sample]
        print(u"\n== 疑漂抽样 %d 条（供目验 · 锚 ⇒ 段） ==" % len(dr))
        for r in dr:
            print(u"  %s:%d -> %s [段 %d-%d] 锚=%s" % (r["cite"], r["at"], r["ref"], r["seg"][0], r["seg"][1], u",".join(r["anchors"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
