# -*- coding: utf-8 -*-
u"""scan_line_refs.py —— 仓内「手书行号引」之扫（承 pm_1425 §三.1 ／ pm_1427 §三.2）。

其为「引须可核」之器：凡注 ／ 文档以 `径:行`（`径:a-b`）引他档之位置者，其引有三命之一：
  · **界内**：所引之行号 <= 目标档今之总行数；
  · **越界**：> 之（引已失准）；
  · **⛔可寻**：所引之径 ⛔ 在仓（`git ls-files` 之面内）。

⚠ 器之限（**要紧 · ⛔ 掩** · 承 pm_1427 §二.3）：
  **「界内」⛔ ＝ 「准」** —— 本器**唯判「所引之行号是否在目标之界内」**，⛔ 判**语义**
  （该行今是否仍为所引之事）。**实证**：本批所修之 `web/pa/faces/products.js`
  旧引 `core/pa/env_face.py` 之手书行号 `157-174` ⇒ 本器判「**界内**」（`env_face.py` 今 1,037 行）
  而**实漂**（`render` 段今在 `173-188`）⇒ **「界内」之 `287` 条 ⛔ 可当「准」**（须目验 ∨ 加语义探针 · `v2`）。
  并：本器**⛔ 判「记史 ∨ 指现处」** —— 越界 ／ ⛔可寻者之治（记史 ⇒ 标其刻 ／ 指现处 ⇒ 改符号锚 ／
  引不可寻之物 ⇒ 附「过程之痕」之标）须**人判**（承 pm_1427 §二.1 ／ §二.2）。

⭐ **新引之式（律 · 承 pm_1431 §二.5 ／ pm_1435 §二.4）**：凡**新**书之引 ⇒ **用「符号之锚」**
  （函数名 ／ 键名 ／ 段名 · 如「`resolve_paths()` 之 `render` 键」）⇒ **⛔ 手书行号**
  —— ⭐ **由**：**行号 ＝ 时之快照**（**改即漂** ∧ **注中之漂无人觉**）。
  本器（及其 `probe_line_ref_semantics.py` 之探针）＝ **兜底**（治**存量**）⇒ **⛔ 以器代律**。

口径（逐条附径:行）：
  · **面** ＝ 仓内 `git ls-files` 之件（扩展名 ∈ SCAN_EXT）。
  · **式** ＝ `径:行`（含 `:a-b` 之段 · 半／全角冒号皆收）；**径解析** ＝ 绝对 ／ 本档相对 ／
    后缀唯一定 ⇒ 解（同后缀多命中 ⇒ `ambiguous` ⇒ ⛔ 定其指 ⇒ 判「⛔可寻」，
    **须人报其「指名之实」** —— 见 pm_1427 §二.2.⒝）。
  · **⛔ 及**：在仓外之件（信通之册 ／ `data/**` 之未跟件 ／ `data/tmp`）。

出口码：0 ＝ 扫毕（无论命中几何）；2 ＝ 用法错。
⭐ `--json` ⇒ 全录（供复算）；`--self-test` ⇒ 纯内存合成之反例门（⛔ 依仓之现状）。
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXT = r"(?:py|js|mjs|md|ya?ml|json|bat|ps1|psm1|html|css|toml|txt|cfg|ini|sh)"
REF = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_\-./\\]*\." + EXT + r")[:：](\d{1,5})(?:\s*[-\u2013\u2014~]\s*(\d{1,5}))?")
SCAN_EXT = {".py", ".js", ".mjs", ".md", ".yaml", ".yml", ".json", ".bat", ".ps1",
            ".psm1", ".html", ".css", ".toml", ".cfg", ".ini", ".sh"}

V_IN = u"界内"
V_OUT = u"越界"
V_MISS = u"⛔可寻"


def tracked_files(root=ROOT):
    u"""仓内 `git ls-files` 之件（本器之面）。"""
    r = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True)
    return [f for f in r.stdout.decode("utf-8", "replace").split("\n") if f.strip()]


def index(files):
    u"""(by_suffix, by_base)：径之索引。"""
    by_suffix, by_base = {}, {}
    for f in files:
        by_suffix[f] = f
        by_base.setdefault(os.path.basename(f), []).append(f)
    return by_suffix, by_base


def resolve(raw, cur, files, by_suffix, by_base):
    u"""(tgt, how)：径解析 —— 绝对 ／ 本档相对 ／ 后缀唯一定。⛔ 定指 ⇒ (None, how)。"""
    raw = raw.replace("\\", "/")
    for c in (raw, os.path.normpath(os.path.join(os.path.dirname(cur), raw)).replace("\\", "/")):
        if c in by_suffix:
            return c, "exact"
    hits = [f for f in files if f == raw or f.endswith("/" + raw)]
    if len(hits) == 1:
        return hits[0], "suffix"
    if len(hits) > 1:
        return None, "ambiguous:%d" % len(hits)
    b = os.path.basename(raw)
    if b in by_base:
        return None, "basename:%d" % len(by_base[b])
    return None, "missing"


def judge(raw, a, b, cur, files, by_suffix, by_base, nlines_fn):
    u"""{tgt, how, verdict, tgt_lines} —— 单引之判。nlines_fn 注入（供 --self-test 纯内存跑）。"""
    tgt, how = resolve(raw, cur, files, by_suffix, by_base)
    if tgt is None:
        return {"tgt": None, "how": how, "verdict": V_MISS, "tgt_lines": None}
    n = nlines_fn(tgt)
    end = b if b else a
    v = V_IN if (n > 0 and end <= n) else V_OUT
    return {"tgt": tgt, "how": how, "verdict": v, "tgt_lines": n}


def scan(root=ROOT):
    u"""全录：每命中一 dict（cite ／ at ／ ref ／ tgt ／ how ／ verdict ／ tgt_lines）。"""
    files = tracked_files(root)
    by_suffix, by_base = index(files)
    cache = {}

    def nlines_fn(rel):
        if rel not in cache:
            try:
                cache[rel] = len(io.open(os.path.join(root, rel), encoding="utf-8",
                                         errors="replace").read().split("\n"))
            except Exception:
                cache[rel] = -1
        return cache[rel]

    rows = []
    for f in files:
        if os.path.splitext(f)[1].lower() not in SCAN_EXT:
            continue
        try:
            t = io.open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for ln, line in enumerate(t.split("\n"), 1):
            for m in REF.finditer(line):
                raw = m.group(1)
                a = int(m.group(2))
                b = int(m.group(3)) if m.group(3) else None
                j = judge(raw, a, b, f, files, by_suffix, by_base, nlines_fn)
                rows.append({"cite": f, "at": ln, "ref": m.group(0),
                             "tgt": j["tgt"], "how": j["how"], "verdict": j["verdict"],
                             "tgt_lines": j["tgt_lines"]})
    return rows


def _self_test():
    u"""反例门（纯内存合成 · ⛔ 依仓之现状）：式 ／ 径解析 ／ 三命 逐格验。"""
    files = ["core/a.py", "pa.html", "web/pa.html", "core/pa/roster.py",
             "core/lib/v8/routes/roster.py"]
    by_suffix, by_base = index(files)
    ln = {"core/a.py": 1, "web/pa.html": 3, "pa.html": 2}
    fn = lambda rel: ln.get(rel, -1)

    bad = []
    cases = [
        # raw, a, b, cur, want_tgt, want_how, want_verdict
        ("core/a.py", 1, None, "docs/x.md", "core/a.py", "exact", V_IN),
        ("core/a.py", 2, None, "docs/x.md", "core/a.py", "exact", V_OUT),
        ("a.py", 1, None, "docs/x.md", "core/a.py", "suffix", V_IN),
        ("pa.html", 1, 2, "docs/x.md", "pa.html", "exact", V_IN),
        ("web/pa.html", 4, None, "docs/x.md", "web/pa.html", "exact", V_OUT),
        ("nope.py", 1, None, "docs/x.md", None, "missing", V_MISS),
        ("roster.py", 4, None, "docs/x.md", None, "ambiguous:2", V_MISS),
    ]
    for raw, a, b, cur, wt, wh, wv in cases:
        j = judge(raw, a, b, cur, files, by_suffix, by_base, fn)
        got = (j["tgt"], j["how"], j["verdict"])
        if got != (wt, wh, wv):
            bad.append("判据: %r => %r ／ 望 %r" % (raw, got, (wt, wh, wv)))

    # ⚠ 夹具之「行号」以 `%d` **占位**（—— 由：一处字面即为本器之真引 ⇒ 必自命中·假据）。
    #   夹具本非真引，故占位；装配后之字符串仍逐字同。
    line = u"见 core/a.py:%d ／ web/pa.html:%d-%d ／ core/a.py：%d ／ http://x:1 ／ v1.2 ／ nope.py:%d" % (1, 2, 3, 4, 9)
    got = [m.group(0) for m in REF.finditer(line)]
    want = [u"core/a.py:%d" % 1, u"web/pa.html:%d-%d" % (2, 3), u"core/a.py：%d" % 4, u"nope.py:%d" % 9]
    if got != want:
        bad.append(u"式: %r ／ 望 %r" % (got, want))

    if bad:
        for x in bad:
            print(u"FAIL " + x)
        print(u"self-test: %d 处败" % len(bad))
        return 1
    print(u"  ⭐ ⑦ 新引之式（提醒 · ⛔ 闸 ⇒ 唯显形）：凡新书之引 ⇒ 用「符号之锚」（函数名 ／ 键名 ／ 段名）· ⛔ 手书行号")
    print(u"self-test: %d 格 ＋ 式 1 格 · 皆过（⛔ 依仓之现状）" % len(cases))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=u"仓内「手书行号引」之扫（承 pm_1425 §三.1 ／ pm_1427 §三.2）")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--json", action="store_true", help=u"全录（供复算）")
    ap.add_argument("--self-test", action="store_true", help=u"纯内存合成之反例门")
    a = ap.parse_args(argv)

    if a.self_test:
        return _self_test()

    rows = scan(a.root)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0

    print(u"手书行号引之扫（面：git ls-files · 扩展名 %d 类 · ⛔ 及仓外件）" % len(SCAN_EXT))
    print(u"TOTAL %d ｜ verdict %s ｜ how %s"
          % (len(rows), dict(Counter(r["verdict"] for r in rows)),
             dict(Counter(r["how"].split(":")[0] for r in rows))))
    print(u"⚠ 「界内」⛔ ＝ 「准」（本器 ⛔ 判语义）⇒ 硬漂 ＝ 越界 ＋ ⛔可寻 ＝ %d"
          % sum(1 for r in rows if r["verdict"] != V_IN))
    for v in (V_OUT, V_MISS):
        hit = [r for r in rows if r["verdict"] == v]
        print(u"\n== %s：%d 处 ==" % (v, len(hit)))
        for r in hit:
            print(u"  %-58s:%-5d %-30s => %-34s [%s]"
                  % (r["cite"], r["at"], r["ref"], r["tgt"], r["how"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
