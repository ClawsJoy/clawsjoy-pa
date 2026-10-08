# -*- coding: utf-8 -*-
"""编目「要」件入 SAG —— 长记忆之第三跳（**只读源** ｜ 一处定形）

承 `pm_1949 §一`（**正** `pm_1946 §一`）：老板之原则 ＝「**落盘是基础 · 必要是搜索引擎（SAG）·
摘要化结构化是关键**」⇒ 本器把「要」件 **先摘要化 ＋ 结构化**，再经
``core/lib/sag_audit_bridge.py``（**图书馆编目入口** · **一处定形**）注册进 SAG 之
``code_entities`` 表（Postgres `clawsjoy_dev` · 域 `default`）⇒ 使 ``query_index`` 可检索。

⭐ **幂等之基**：`code_entities` 之 ``UNIQUE(project_id, entity_name, file_path)``
＋ `upsert_entity` 之 ``ON CONFLICT DO UPDATE`` ⇒ 同件同段**天然不重复**（⛔ 自建去重）。

用法::

    python -X utf8 -B scripts/dev/编目_要件入SAG.py                     # 计划（⛔ 不写）
    python -X utf8 -B scripts/dev/编目_要件入SAG.py --go                # 真编目
    python -X utf8 -B scripts/dev/编目_要件入SAG.py --go --query "净机升号"
    python -X utf8 -B scripts/dev/编目_要件入SAG.py --json
    python -X utf8 -B scripts/dev/编目_要件入SAG.py --go --no-tools
    python -X utf8 -B scripts/dev/编目_要件入SAG.py --manifest <清单.txt> --go
    python -X utf8 -B scripts/dev/编目_要件入SAG.py --go --prune-stale
    python -X utf8 -B scripts/dev/编目_要件入SAG.py --self-test

守四条（`pm_1949 §一.4`）：⒜ **幂等**（键＝`UNIQUE(project_id, entity_name, file_path)`）
⒝ **只读源**（⛔ 动 vault 件）⒞ **可查**（件数／实体数／边数 ＋ `--query` 之召回）
⒟ **降级照实**（DB 不可用 ⇒ 桥自降级 ⇒ **须报**，⛔ 静默）。

⭐ **注销之处**：`--prune-stale`（件变后之**余段注销**）**唯走桥** ——
   `core/lib/sag_audit_bridge.unregister_stale`（一处定形 · 承 pm_1951 §二.1 裁⒝）；
   **默认关** ⇒ 须显式点名方动。⭐ 本器 ⛔ 自撰 SQL（昔之越桥一越已拆）。

退出码: 0 = 成 ｜ 1 = 库不可用（全败）｜ 2 = 入参错 ｜ 3 = 源全空 ｜ 4 = 自证败 ｜ 5 = 有降级
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys

BS = chr(92)
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HERE))     # scripts/dev/x.py ⇒ 仓根（⛔ 按 CWD）
#: 仓根入 `sys.path` ⇒ 本器**自足**（照抄即跑 · ⛔ 须先设 PYTHONPATH）。
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: 默认根（`tag` · 径）—— ⭐ **一处定形**：改此元组即改「源之根」。
DEFAULT_ROOTS = (
    ("vault", "D:" + BS + "Obsidian" + BS + "ClawsJoy" + BS + "ClawsJoy"),
    ("_pm", "D:" + BS + "paseo-workspace" + BS + "_pm"),
)

#: PM 要件之「格」＝（根之 tag · 其内相对径之前缀）。
_PM = (("vault", "paseo-pm/"), ("_pm", ""))
#: 我之白名单格（`07_SOP`）。
_SOP = (("vault", "内容工坊/07_SOP/"),)

#: 采集面（**一处定形**）：（分类 · 是否默认开 · 格 · 件名 glob 之元组）。
#: ⭐ **以格 ＋ 件名定域**（⛔ 全库子串法 —— 反例：`codex/…判据…md` 系长名之工程件）。
#: ⚠ 序即优先序（`PA-席位冻册` 先中「蓝图」⇒ 归蓝图）。
SPEC = (
    ("蓝图", True, _PM, ("PA-*.md",)),
    ("经验", True, _PM + (("vault", "codex/"), ("vault", "dsh/")),
     ("*经验库*.md", "_经验库.md")),
    ("判据", True, _PM, ("*判据*.md", "*边界清单*.md", "*人机分工*.md")),
    ("续接", True, _PM, ("*续接*.md",)),
    ("任务线", True, _PM, ("*任务线*.md",)),
    ("时间线", True, _PM, ("*时间线*.md",)),
    ("台账", True, _PM, ("*维护单*.md", "*冻册*.md", "*端口归属登记*.md",
                        "*全件索引*.md", "_规范/*.md")),
    ("工具", True, _SOP, ("SOP_*.md", "*SOP索引*.md", "评估单_*.md")),
)

#: 实体型前缀（**一处定形**）：件 ⇒ `vault_doc`；段 ⇒ `vault_<分类>`。
ENTITY_DOC = "vault_doc"
ENTITY_SEG_PREFIX = "vault_"

#: ⛔ 不入采之目录名（前缀即算）。
NOISE_DIRS = ("node_modules", "__pycache__", "收件箱", "邮局")
#: ⛔ 不入采之件名（存底 ／ 伴生 ／ 副本）。
NOISE_NAME = ("before_", ".bak", ".tmp", ".orig")
#: ⛔ 不入采之件名前缀 —— **临件**（承 `pm_1913 §四.3`）。
NOISE_PREFIX = ("_回_", "_令_", "_报_", "_请_", "_问_", "_批_", "_转令_",
                "_派_", "_派件_", "_请办_", "_稿_", "回件_", "回执_", "秘书_回")

#: 席名（结构化之「席」格 · 取不到即空 —— ⛔ 猜）。
SEATS = ("技术总监", "项目经理", "总经理CEO", "笔杆子", "导演", "秘书", "客服",
         "工作流实验室", "CodexWindows线")

#: 摘要所取之「规线」关键词（含之 ⇒ 入摘要）。
RULE_KEYS = (u"须", u"⛔", u"⇒", u"判据", u"结论", u"凭", u"禁", u"恒", u"必")

_HEAD = re.compile(r"^\s{0,3}(#{1,4})\s+(.+?)\s*$")


def prune_dir(name):
    """目录名 ⇒ 是否 ⛔ 走（点目录 · 下划线族（除 `_规范`）· 噪名）。"""
    if name.startswith("."):
        return True
    if name.startswith("_") and name != "_规范":
        return True
    for bad in NOISE_DIRS:
        if name == bad or name.startswith(bad):
            return True
    return False


def is_noise_name(name):
    """件名 ⇒ 是否 ⛔ 采（存底 ／ 伴生 ／ 副本 ／ 临件 ／ 隐件）。"""
    low = name.lower()
    if name.startswith("."):
        return True
    if low.endswith(".sha256") or low.endswith(".pyc"):
        return True
    for bad in NOISE_NAME:
        if bad in low:
            return True
    for pre in NOISE_PREFIX:
        if name.startswith(pre):
            return True
    return False


def build_rules(with_tools=True):
    """启之分类 ⇒ `[(分类, 格, 件名 glob 之元组)]`（序即优先序）。"""
    rules = []
    for cat, on, dirs, pats in SPEC:
        if not on:
            continue
        if cat == "工具" and not with_tools:
            continue
        rules.append((cat, dirs, pats))
    return rules


def match_category(tag, rel, rules):
    """（根之 tag · 根内相对径）⇒ 分类 ∨ `None`（**走盘**：唯认全键）。"""
    key = rel.replace(BS, "/").lower()
    for cat, dirs, pats in rules:
        for dtag, prefix in dirs:
            if dtag != tag:
                continue
            low = prefix.lower()
            if not key.startswith(low):
                continue
            inner = key[len(low):]
            for p in pats:
                if fnmatch.fnmatch(inner, p.lower()):
                    return cat
    return None


def match_basename(path, rules):
    """清单之径 ⇒ 分类 ∨ `None`（守「一行一径照抄即用」· ⚠ 唯清单用）。"""
    base = path.replace(BS, "/").rsplit("/", 1)[-1].lower()
    for cat, _dirs, pats in rules:
        for p in pats:
            tail = p.rsplit("/", 1)[-1].lower()
            if fnmatch.fnmatch(base, tail):
                return cat
    return None


def walk_files(root, max_depth=2):
    """根 ⇒ 件之全径之列（深 ≤ `max_depth` · 剪噪目）。"""
    root = os.path.abspath(root)
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirnames[:] = [d for d in dirnames if not prune_dir(d)]
        if depth >= max_depth:
            dirnames[:] = []
        for fn in filenames:
            out.append(os.path.join(dirpath, fn))
    return out


def _split_long(chunk, max_chars):
    """超长 ⇒ 按空行聚合 · 余者硬切 ⇒ 皆 ≤ `max_chars`。"""
    if len(chunk) <= max_chars:
        return [chunk] if chunk else []
    parts = []
    cur = ""
    for para in chunk.split("\n\n"):
        if cur and len(cur) + len(para) + 2 > max_chars:
            parts.append(cur)
            cur = para
        else:
            cur = (cur + "\n\n" + para) if cur else para
    if cur:
        parts.append(cur)
    final = []
    for piece in parts:
        while len(piece) > max_chars:
            final.append(piece[:max_chars])
            piece = piece[max_chars:]
        if piece:
            final.append(piece)
    return final


def segments(text, max_chars=900, max_seg=200):
    """正文 ⇒ 段之列 `[{"i", "head", "text"}]`（`#`–`####` 切 · 超长再切）。"""
    body = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    groups = []
    head = ""
    buf = []
    for line in body.split("\n"):
        m = _HEAD.match(line)
        if m:
            groups.append((head, "\n".join(buf)))
            head = m.group(2).strip()
            buf = []
        else:
            buf.append(line)
    groups.append((head, "\n".join(buf)))

    out = []
    for head, chunk in groups:
        for piece in _split_long(chunk.strip(), max_chars):
            if piece.strip():
                out.append({"i": len(out), "head": head, "text": piece.strip()})
            if len(out) >= max_seg:
                return out
    return out[:max_seg]


def digest(head, body, max_sig=800):
    """段 ⇒ **摘要**（**抽取式** · ⛔ LLM ⇒ 省成本 ∧ 可复算）：
    题 ＋ 规线（含 `RULE_KEYS` 之行 · 至多 6 条）＋ 首段。"""
    lines = [ln.strip() for ln in (body or "").split("\n")]
    pick = []
    for ln in lines:
        if not ln:
            continue
        if any(k in ln for k in RULE_KEYS):
            pick.append(ln[:160])
        if len(pick) >= 6:
            break
    first = ""
    for ln in lines:
        if ln:
            first = ln[:240]
            break
    out = []
    if head:
        out.append(u"《%s》" % head[:60])
    out.extend(pick)
    if first and first not in out:
        out.append(first)
    return u" ｜ ".join(out)[:max_sig]


def doc_digest(cat, rel, sha16, nseg, segs):
    """件 ⇒ 摘要（类 ＋ 面前数题 ＋ 段数 ＋ 印）。"""
    heads = [s["head"] for s in segs if s["head"]][:6]
    tail = u"／".join(heads) if heads else u"（无题）"
    return u"【%s】%s ｜ 段 %d ｜ 印 %s" % (cat, tail, nseg, sha16)


def fields(rel, text):
    """结构化之三格：`(席, 号, 到刻)` —— 取不到即空（**⛔ 猜**）。"""
    seat, num, day = u"", u"", u""
    head = (text or "")[:1500]
    m = re.search(r"^from:\s*(.+)$", head, re.M)
    if m:
        seat = m.group(1).strip()[:40]
    if not seat:
        for s in SEATS:
            if s in rel:
                seat = s
                break
    m = re.search(r"^date:\s*(20\d{2}-\d{2}-\d{2})", head, re.M)
    if m:
        day = m.group(1)
    if not day:
        m = re.search(r"(20\d{2})-?(\d{2})-?(\d{2})", rel)
        if m:
            day = u"%s-%s-%s" % m.groups()
    m = re.search(r"_(\d{3,4})(?=[_.])", rel)
    if m:
        num = m.group(1)
    return seat, num, day


def edges_of(cat, tag, head, seat, num, day, extra=None):
    """边（**动态超边**之形 · 采 `related_entities` 之机制）⇒ 至多 12 条。"""
    out = [u"类=%s" % cat, u"格=%s" % tag]
    if head:
        out.append(u"题=%s" % head[:40])
    if seat:
        out.append(u"席=%s" % seat)
    if num:
        out.append(u"号=%s" % num)
    if day:
        out.append(u"到刻=%s" % day)
    return (list(extra or []) + out)[:12]


def sha16_of(path):
    """件之 `sha16`（`sha256` 前 16 位 · 读字节）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:16]


def read_text(path):
    """件 ⇒ 正文（`utf-8` · 坏字节照实替之 · ⛔ 抛）。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def build_plan(roots, rules, max_chars, max_seg, manifest=None, depth=2):
    """源 ⇒ 计划（件 ⇒ 段之摘要 ＋ 边）。"""
    files = []
    skipped = []
    if manifest:
        for raw in manifest:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            cat = None
            if "|" in line:
                cat, line = line.split("|", 1)
                cat = cat.strip()
                line = line.strip()
            path = os.path.abspath(line)
            if not os.path.isfile(path):
                skipped.append((line, u"不在盘"))
                continue
            if not cat:
                cat = match_basename(path, rules)
            if not cat:
                skipped.append((line, u"无类可归（⛔ 猜）"))
                continue
            files.append((cat, "清单", os.path.basename(path), path))
    else:
        for tag, root in roots:
            if not os.path.isdir(root):
                skipped.append((root, u"根不在盘"))
                continue
            for path in walk_files(root, depth):
                if is_noise_name(os.path.basename(path)):
                    continue
                rel = os.path.relpath(path, os.path.abspath(root)).replace(os.sep, "/")
                cat = match_category(tag, rel, rules)
                if not cat:
                    continue
                files.append((cat, tag, rel, path))

    plan = []
    for cat, tag, rel, path in sorted(files, key=lambda x: (x[0], x[1], x[2])):
        text = read_text(path)
        allsegs = segments(text, max_chars, 10 ** 9)
        segs = allsegs[:max_seg]
        if not segs:
            skipped.append((rel, u"无正文（空件 ∨ 空段）"))
            continue
        seat, num, day = fields(rel, text)
        key = u"%s/%s" % (tag, rel)
        plan.append({
            "cat": cat, "tag": tag, "rel": rel, "path": path, "key": key,
            "sha16": sha16_of(path), "segs": segs, "segs_all": len(allsegs),
            "trunc": len(allsegs) > len(segs), "seat": seat, "num": num, "day": day,
            "doc_sig": doc_digest(cat, rel, u"", len(allsegs), segs),
        })
    return plan, skipped


def resolve_db_url():
    """DSN 之源：`env` ⇒ `config/.env`（**一处定形** ⇒ `local_env_files.ENV_REL`）。"""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url.strip(), "env"
    try:
        from core.lib.local_env_files import ENV_REL, read_lines
    except Exception:
        return "", ""
    p = os.path.join(ROOT, *ENV_REL.split("/"))
    for ln in read_lines(p):
        if ln.startswith("DATABASE_URL="):
            return ln.split("=", 1)[1].strip(), ENV_REL
    return "", ""


def catalog(plan, stream=None, prune_stale=False):
    """计划 ⇒ 真编目（经桥 `register_entity` · 幂等）。返 `(统计, 降级之数)`。"""
    stream = stream or sys.stdout
    from core.lib.sag_audit_bridge import register_entity   # ⭐ 惰引：唯真编目方引

    st = {"files": 0, "entities": 0, "edges": 0, "fail": 0, "seg": 0, "pruned": 0}
    for f in plan:
        doc_edges = edges_of(f["cat"], f["tag"], u"", f["seat"], f["num"], f["day"])
        ok = register_entity(ENTITY_DOC, f["rel"], f["doc_sig"], f["key"], doc_edges)
        st["files"] += 1
        st["entities"] += 1
        st["edges"] += len(doc_edges)
        if not ok:
            st["fail"] += 1
        for s in f["segs"]:
            sig = digest(s["head"], s["text"])
            seg_edges = edges_of(f["cat"], f["tag"], s["head"], f["seat"], f["num"], f["day"],
                                 extra=[u"件=%s" % f["rel"]])
            if register_entity(ENTITY_SEG_PREFIX + f["cat"], u"%s#%d" % (f["rel"], s["i"]),
                               sig, u"%s#%d" % (f["key"], s["i"]), seg_edges):
                st["entities"] += 1
                st["edges"] += len(seg_edges)
                st["seg"] += 1
            else:
                st["fail"] += 1
        if prune_stale:
            _n = prune_tail(f)
            if _n >= 0:
                st["pruned"] += _n
            else:
                st["fail"] += 1        # ⚠ 桥不可用 ⇒ 计降级（⛔ 静默 —— 承守⒟）
    return st, st["fail"]


def prune_tail(f):
    """件变后之**余段注销** —— ⭐ **唯走桥**（一处定形 · 承 pm_1951 §二.1）。

    ⚠ 昔为直 SQL（越桥之一处）；桥加 `unregister_stale` 后 ⇒ **已拆**（本器今 ⛔ SQL）。
    返 **注销数** ∨ `-1`（桥不可用 ⇒ 由 `catalog` 计降级 · ⛔ 静默）。
    """
    from core.lib.sag_audit_bridge import unregister_stale   # ⭐ 惰引：唯 `--prune-stale` 方引
    keep = [u"%s#%d" % (f["rel"], s["i"]) for s in f["segs"]]
    return unregister_stale(ENTITY_SEG_PREFIX + f["cat"], f["key"] + u"#%", keep)

def run_query(text, entity_type=None, n=5, stream=None):
    """`--query` 验召回（**唯读** · 走 `query_index` 之同一入口 `query_entities`）。"""
    stream = stream or sys.stdout
    from core.lib.sag_audit_bridge import query_entities

    rows = query_entities(entity_type=entity_type or None, query=text, limit=n)
    if not rows:
        stream.write(u"  （⛔ 无召回 —— 照实报）\n")
        return []
    for r in rows:
        stream.write(u"  [%s] %s ｜ %s ｜ %s\n" % (
            r.get("entity_type"), r.get("entity_name"),
            (r.get("signature") or "")[:80], r.get("file_path")))
    return rows


def _self_test(stream=None):
    """自证（纯逻辑 ＋ 源码之结构断言 · ⛔ 触库 · ⛔ 触网）。返 0/1。"""
    stream = stream or sys.stdout
    ok = []

    def ck(name, cond):
        ok.append((name, bool(cond)))

    ck(u"段空件 ⇒ 空列", segments("") == [])
    s = segments(u"# 一 甲\n甲之正文\n\n## 二 乙\n乙之正文\n")
    ck(u"标题切段", len(s) == 2 and s[0]["head"] == u"一 甲" and s[1]["head"] == u"二 乙")
    ck(u"段号自 0 连号", [x["i"] for x in s] == [0, 1])
    ck(u"超长必切（≤ 300）", all(len(x["text"]) <= 300 for x in
                                segments(u"# T\n" + u"甲乙" * 400, max_chars=300)))
    ck(u"段数上限", len(segments(u"# T\n" + u"甲乙" * 5000, max_chars=100, max_seg=7)) == 7)

    d = digest(u"净机升号", u"须先提交载荷。\n闲话一行。\n⛔ 静默装。")
    ck(u"摘要载题", d.startswith(u"《净机升号》"))
    ck(u"摘要取规线（须／⛔）", u"须先提交载荷。" in d and u"⛔ 静默装。" in d)
    ck(u"摘要封顶", len(digest(u"H", u"甲" * 3000, max_sig=120)) == 120)
    ck(u"件摘要载类与印", doc_digest(u"判据", u"a.md", u"abc", 3, s).startswith(u"【判据】"))

    ck(u"席取自 front matter", fields(u"paseo-pm/x.md", u"---\nfrom: 技术总监\n---\n")[0] == u"技术总监")
    ck(u"席之回退（件名）", fields(u"paseo-pm/说明_技术总监_出图链.md", u"无头")[0] == u"技术总监")
    ck(u"无席之件 ⇒ 空", fields(u"paseo-pm/_PM时间线_v1.md", u"无头")[0] == u"")
    ck(u"号取自件名", fields(u"paseo-pm/_令_TD_1946.md", u"")[1] == u"1946")
    ck(u"到刻取自件名", fields(u"paseo-pm/_续接_PM_20261008.md", u"")[2] == u"2026-10-08")
    ck(u"取不到 ⇒ 空（⛔ 猜）", fields(u"paseo-pm/PA-宏图之判_v1.md", u"无头")[0] == u"")

    rules = build_rules(with_tools=True)
    ck(u"走盘：蓝图 ✅ 归", match_category("vault", u"paseo-pm/PA-插件面之判_v1.md", rules) == u"蓝图")
    ck(u"走盘：判据 ✅ 归", match_category("vault", u"paseo-pm/_判据_留存与删除_v1.md", rules) == u"判据")
    ck(u"走盘：域外同名 ⛔ 归", match_category("vault", u"codex/2026-09-24-…判据….md", rules) is None)
    ck(u"走盘：08_工具散记 ⛔ 归", match_category("vault", u"内容工坊/08_工具/待落清单_技术总监.md", rules) is None)
    ck(u"清单：唯件名亦可归", match_basename(u"D:" + BS + "x" + BS + "PA-宏图之判_v1.md", rules) == u"蓝图")
    ck(u"临件 ⛔ 采", is_noise_name(u"_回_CW_1212_认翻判与答判据.md") is True)
    ck(u"存底 ⛔ 采", is_noise_name(u"投递台账.csv.before_abc") is True)
    ck(u"正件 ✅ 采", is_noise_name(u"_判据_留存与删除_v1.md") is False)
    ck(u"下划线族目 ⛔ 走", prune_dir(u"_冷区") is True and prune_dir(u"_老板") is True)
    ck(u"常态目 ✅ 走", prune_dir(u"paseo-pm") is False)

    e = edges_of(u"判据", u"vault", u"题", u"项目经理", u"1946", u"2026-10-08")
    ck(u"边载 类／格／席／号／到刻", u"类=判据" in e and u"席=项目经理" in e
       and u"号=1946" in e and u"到刻=2026-10-08" in e)
    ck(u"边封顶 12", len(edges_of(u"类", u"格", u"题", u"席", u"号", u"刻",
                                  extra=[u"件=x"] * 20)) == 12)

    src = read_text(os.path.abspath(__file__))
    for bad in ("shut" "il", "rm" "tree", "os.re" "move", "os.un" "link",
                "os.ren" "ame", "os.rep" "lace", "trunc" "ate"):
        ck(u"器只读（⛔ 无 %s）" % bad, bad not in src)
    ck(u"⛔ 无写模式开件", not re.search(r"open\([^)]*['\"][wa+]b?['\"]", src))
    ck(u"⛔ 无模块级引桥（惰引）", not re.search(r"^from core\.", src, re.M | re.U))
    ck(u"⛔ 无直写 SQL（注销已归桥）", src.count(u"DELETE" + u" FROM") == 0)
    ck(u"注销唯走桥 unregister_stale", u"unregister_stale" in src)
    ck(u"注销：须显式点名", u"prune_stale=args.prune_stale" in src)
    ck(u"注销：不得默认开", u"prune_stale=False" in src)

    bad_n = [n for n, c in ok if not c]
    for n, c in ok:
        stream.write(u"  %s %s\n" % (u"✅" if c else u"❌", n))
    stream.write(u"自证：%d/%d 过\n" % (len(ok) - len(bad_n), len(ok)))
    return 0 if not bad_n else 1


def _parse_roots(pairs):
    out = []
    for raw in pairs or ():
        if "=" in raw:
            tag, path = raw.split("=", 1)
            out.append((tag.strip(), path.strip()))
        else:
            out.append((os.path.basename(raw.rstrip(BS)) or "root", raw))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=u"编目「要」件入 SAG（长记忆第三跳 · 只读源）")
    ap.add_argument("--root", action="append", default=None, help=u"根（`tag=径` ／ 径 · 可多）")
    ap.add_argument("--manifest", default=None, help=u"待编目清单（一行一径 · `分类|径`）")
    ap.add_argument("--go", action="store_true", help=u"真编目（⛔ 无 ⇒ 唯计划）")
    ap.add_argument("--prune-stale", action="store_true", help=u"件变后注销余段（走桥 · 默认关）")
    ap.add_argument("--no-tools", action="store_true", help=u"⛔ 编 工具（SOP）族")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--max-chars", type=int, default=900)
    ap.add_argument("--max-seg", type=int, default=200)
    ap.add_argument("--query", default=None, help=u"编毕验召回（唯读）")
    ap.add_argument("--query-type", default=None, help=u"召回之实体型（如 `vault_判据`）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    out = sys.stdout
    if args.self_test:
        return _self_test(out)

    roots = _parse_roots(args.root) if args.root else list(DEFAULT_ROOTS)
    rules = build_rules(with_tools=not args.no_tools)
    manifest = None
    if args.manifest:
        if not os.path.isfile(args.manifest):
            out.write(u"入参错：清单不在盘 %s\n" % args.manifest)
            return 2
        manifest = read_text(args.manifest).split("\n")
    if args.max_chars < 80 or args.max_seg < 1:
        out.write(u"入参错：--max-chars ≥ 80 ／ --max-seg ≥ 1\n")
        return 2

    plan, skipped = build_plan(roots, rules, args.max_chars, args.max_seg, manifest, args.depth)
    nseg = sum(len(f["segs"]) for f in plan)
    if not plan:
        out.write(u"源全空：⛔ 无可编目之件（⛔ 以空跑充「已编」）\n")
        for rel, why in skipped[:20]:
            out.write(u"  跳 %s（%s）\n" % (rel, why))
        return 3

    dsn, dsn_src = resolve_db_url()
    if dsn:
        os.environ["DATABASE_URL"] = dsn      # 桥据 env 取 DSN（**一处定形**）

    if not args.json:
        out.write(u"根：%s\n" % u" ／ ".join(u"%s=%s" % r for r in roots))
        out.write(u"类：%s\n" % u" ／ ".join(sorted({c for c, _d, _p in rules})))
        out.write(u"计划：件 %d ／ 段 %d ｜ 截件 %d ｜ 跳 %d\n" % (
            len(plan), nseg, sum(1 for f in plan if f["trunc"]), len(skipped)))
        out.write(u"DSN：%s\n" % (u"已配（源 %s）" % dsn_src if dsn else u"未配（⛔ 桥必降级）"))
        for rel, why in skipped[:20]:
            out.write(u"  跳 %s（%s）\n" % (rel, why))

    st = {"files": 0, "entities": 0, "edges": 0, "fail": 0, "seg": 0, "pruned": 0}
    if args.go:
        if not dsn:
            out.write(u"库不可用：⛔ DSN 无（env ／ config/.env 皆无 DATABASE_URL）⇒ ⛔ 编目\n")
            return 1
        if not args.json:
            out.write(u"真编目：\n")
        st, fails = catalog(plan, stream=out, prune_stale=args.prune_stale)
    elif not args.json:
        out.write(u"（唯计划 —— ⛔ 未编目 · 加 --go 方真编目）\n")

    if args.json:
        out.write(json.dumps({
            "roots": roots, "dsn_source": dsn_src,
            "plan": [{"cat": f["cat"], "key": f["key"], "sha16": f["sha16"],
                      "segs": len(f["segs"]), "segs_all": f["segs_all"],
                      "trunc": f["trunc"], "seat": f["seat"], "num": f["num"],
                      "day": f["day"]} for f in plan],
            "skipped": skipped, "stat": st, "did_write": bool(args.go),
        }, ensure_ascii=False, indent=2) + "\n")
    else:
        out.write(u"件 %d ／ 段 %d ｜ 实体 %d ／ 边 %d ／ 注销 %d ｜ 降级 %d\n" % (
            st["files"], st["seg"], st["entities"], st["edges"], st["pruned"], st["fail"]))
    if args.query:
        if not args.go:
            out.write(u"（唯计划 —— 未编目 · 召回验之无义）\n")
        else:
            out.write(u"验召回：%s\n" % args.query)
            run_query(args.query, entity_type=args.query_type, stream=out)
    if args.go and st["fail"]:
        out.write(u"⚠ 降级照实：%d 条未入（DB 不可用 ∨ 键之冲突 —— 承 `sag_audit_bridge` 之自降级）\n" % st["fail"])
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())