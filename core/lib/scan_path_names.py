# -*- coding: utf-8 -*-
r"""scan_path_names.py —— **名面之常闸**：扫一棵树，找「件名／目录名带**未展开变量** ∨ **DOS 保留名**」之处。

⭐ 为何须此器（PM b136893 令 2026-10-05 · `1193 §三.⑤`「准将其并入常闸」）：
  源 ＝ `11_实验室\探针_坑形扫描.py` 之 **N-6/N-7**（D16 探测器）—— ⚠ 彼为**事后探针**；
  ⇒ 承「**探针 ≠ 活闸**」⇒ 并入 `core/lib` 之常扫一族（与 `scan_subprocess_calls.py` 同族）。
  实证（2026-10-05 · B2）：`<main-repo>\%SystemDrive%\ProgramData\Microsoft\Windows\Caches\`
  —— `%SystemDrive%` **未展开**之环境变量被当作**逐字目录名**写在盘上 ⇒ 三 `.db`（988,256 B）
  ＝ **伪件污染真源**（⛔ 产品件 · ⛔ 宜入库）。

--- 域定义（逐字 · ⭐ 「何谓一处名面之坑」）---
  一处名面之坑 ＝ **相对 root 之路径**中**任一段**（件名 ∨ 目录名）命中下列**任一**：
    ⒜ `%VAR%` 形：正则 `%[A-Za-z_][A-Za-z0-9_]*%`（**未展开之环境变量**）—— 逐字同探针 **N-6**。
    ⒝ DOS 保留名：正则 `^(nul|con|aux|prn|com[1-9]|lpt[1-9])(\..*)?$`（大小写不感）—— 逐字同 **N-7**。
  ⚠ **⛔ 过杀之界**：`console.log` ／ `com10.txt` ／ `constitution.md` ／ `notes%20.md`
     （URL 转义）皆 **⛔ 命中**（锚定 ＋ 两 `%` 成对 ⇒ 非「见 con 即红」）。

--- 用法 ---
  python scan_path_names.py [--root <目录>] [--json] [--all] [--selftest]
    --root <目录>  要扫之根（默认：`.` 即当前目录）
    --json         机读（末行打 JSON）
    --all          含 `.git` 与 `__pycache__`（默认排除 · 彼等非「活件」之面）

--- 退出码（本器私有 · ⛔ 与 codex_guard 互换）---
  0 = 已扫且净（⛔ 无一处命中）
  2 = **有名面之坑**（判红 · 须改）
  3 = 用法／路径错（**闸没跑** · 与「判红」⛔ 同）
  4 = 闸未跑完（**坏件 > 0** ⇒ ⛔ 得报 0 · 承「不可达 ≠ 0」）
  5 = **无件可扫**（**件数 == 0** ⇒ ⛔ 得报 0 · 承「空 ≠ 缺」）
  优先级：3 > 5 > 4 > 2 > 0

唯读（⛔ 写任何件）· 附印（器印 ＋ 面之径 ＋ 取数刻）· 可唯读调。
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys

RE_VAR = re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%")
RE_RESERVED = re.compile(r"^(nul|con|aux|prn|com[1-9]|lpt[1-9])(\..*)?$", re.I)

SKIP_NAMES = (".git", "__pycache__")

RC_MEAN = {
    0: u"已扫且净",
    2: u"有名面之坑（判红）",
    3: u"用法／路径错（闸没跑）",
    4: u"闸未跑完（坏件>0）",
    5: u"无件可扫（件数==0）",
}
HERE = os.path.abspath(__file__)


def sha16(path):
    try:
        with io.open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None


def hit_segments(rel):
    u"""返：rel 中命中之名段（**逐段**判 ⇒ 目录名亦算）。"""
    out = []
    for seg in rel.replace(os.sep, "/").split("/"):
        if not seg:
            continue
        if RE_VAR.search(seg):
            out.append((u"%VAR%", seg))
        elif RE_RESERVED.match(seg):
            out.append((u"RESERVED", seg))
    return out


def walk_entries(root, all_):
    u"""返：相对径之列表（目录 ＋ 件 · ⛔ 唯件之面）。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        if not all_:
            dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES]
        for d in dirnames:
            out.append(os.path.relpath(os.path.join(dirpath, d), root))
        for f in filenames:
            out.append(os.path.relpath(os.path.join(dirpath, f), root))
    return out


def scan(root, all_):
    entries = walk_entries(root, all_)
    hits = []
    bad = []
    for rel in entries:
        try:
            segs = hit_segments(rel)
        except Exception as e:
            bad.append({"path": rel.replace(os.sep, "/"), "err": "%s" % e})
            continue
        if segs:
            hits.append({"path": rel.replace(os.sep, "/"),
                         "kinds": sorted(set(k for k, _ in segs)),
                         "seg": segs[0][1]})
    return entries, hits, bad


# ---------------- 自证（闸须有反控 · 承「⛔ 唯正控不成闸」）----------------
POS = [u"%SystemDrive%", u"CON", u"nul.txt", u"%TEMP%", u"a/lpt1/b"]
NEG = [u"constitution.md", u"console.log", u"com10.txt", u"notes%20.md",
       u"core/pa/gateway_routes.py"]


def selftest():
    bad = []
    for p in POS:
        if not hit_segments(p):
            bad.append(u"正控未中：%s" % p)
    for p in NEG:
        if hit_segments(p):
            bad.append(u"反控误中：%s" % p)
    print(u"[自证] 正控 %d ／ 反控 %d ⇒ %s" % (len(POS), len(NEG),
          u"PASS" if not bad else u"FAIL " + u" ／ ".join(bad)))
    return 0 if not bad else 1


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)

    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        sys.stderr.write(u"⛔ 路径不存在（闸没跑）：%s\n" % root)
        return 3

    entries, hits, bad = scan(root, a.all)
    rep = {
        u"器": HERE,
        u"器印": sha16(HERE),
        u"面之径逐字": root,
        u"取数刻": datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
        u"域定义": u"路径任一段命中 %VAR% 形（未展开变量）∨ DOS 保留名",
        u"件数": len(entries),
        u"命中数": len(hits),
        u"命中": hits,
        u"坏件": bad,
    }
    if rep[u"件数"] == 0:
        rc = 5
    elif bad:
        rc = 4
    elif hits:
        rc = 2
    else:
        rc = 0
    rep[u"rc"] = rc

    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(u"器: %s" % rep[u"器"])
        print(u"器印: %s" % rep[u"器印"])
        print(u"面之径逐字: %s" % rep[u"面之径逐字"])
        print(u"取数刻: %s" % rep[u"取数刻"])
        print(u"域定义: %s" % rep[u"域定义"])
        print(u"—— 件 %d ／ ⭐ 名面之坑 %d ／ 坏件 %d" % (rep[u"件数"], rep[u"命中数"], len(bad)))
        for h in hits:
            print(u"  ⚠ %-58s [%s] 段=%s" % (h["path"], u"／".join(h["kinds"]), h["seg"]))
        for b in bad:
            print(u"  ⚠ 坏件 %s: %s" % (b["path"], b["err"]))
        print(u"rc: %d ＝ %s" % (rep[u"rc"], RC_MEAN.get(rep[u"rc"], u"?")))
    return rc


if __name__ == "__main__":
    sys.exit(main())
