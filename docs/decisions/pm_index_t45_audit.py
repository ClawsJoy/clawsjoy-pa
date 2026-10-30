#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PA 迭代40 · T45 ④决策索引归类 —— pm_index_v0 可复算审计

代发: DSH（PA）· PM 席
写域: docs/decisions/（本脚本 + 产出 CSV/JSON）· docs/reports/pa_iter40/03_index.md

口径
----
索引      docs/decisions/pm_index_v0.csv（UTF-8/LF；表头 1 行 ＋ 数据 96 行）
代码域①   core/pa/*.py            —— 与 v0 自述口径一致（主口径）
代码域②   core/web/shell/scripts/tests/agents/api/routes/engine/clawsky/src/tools/config
          —— 仅作“扩表缺口”参考，不逐条下判
文档域    repo 外（v0 的 root 值 m 不到 repo 内文件）：
          _pm    = D:/paseo-workspace/_pm
          _auto  = D:/paseo-workspace/_auto（deliver/send，令/派件原件的投递副本）
          codex  = D:/Obsidian/ClawsJoy/ClawsJoy/codex
          信通    = D:/Obsidian/ClawsJoy/ClawsJoy/内容工坊/02_协作/信通
          paseo-pm = D:/Obsidian/ClawsJoy/ClawsJoy/paseo-pm

分类（每 id 恰一类）
----
留        指针可验 ＋ PM 件 ＋ 现仍被 core/pa 引用（根口径另由 R0 处理）
移-域     指针可验 ＋ PM 件，但现引用域已迁出 core/pa
移-归属   无 PM 件，仅他席件同号（索引不宜收为 pm 源件，候 PM 判）
补        原 missing 行，现有可验 PM 源件（补指针；另 3 条为代码新增 id，补行）
缺        无可验 PM 源件（缺口；旧指针误配者同时标“废旧指针”）
废        非 pm 号（年份/误配），条目移出

用法
----
  python docs/decisions/pm_index_t45_audit.py            # 生成 CSV/JSON 并打印汇总
  python docs/decisions/pm_index_t45_audit.py --check    # 只打印汇总，不写文件
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- constants
REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "docs" / "decisions" / "pm_index_v0.csv"
OUT_CSV = REPO / "docs" / "decisions" / "pm_index_v0_t45_classification.csv"
OUT_JSON = REPO / "docs" / "decisions" / "pm_index_v0_t45_summary.json"

DEFAULT_ROOTS = [
    ("_pm", r"D:/paseo-workspace/_pm"),
    ("_auto", r"D:/paseo-workspace/_auto"),
    ("codex", r"D:/Obsidian/ClawsJoy/ClawsJoy/codex"),
    ("信通", r"D:/Obsidian/ClawsJoy/ClawsJoy/内容工坊/02_协作/信通"),
    ("paseo-pm", r"D:/Obsidian/ClawsJoy/ClawsJoy/paseo-pm"),
]

# v0 root 值 -> 外部文档根（用于指针核验）
ROOT_VERIFY = {
    "_pm": [r"D:/paseo-workspace/_pm"],
    "codex": [r"D:/Obsidian/ClawsJoy/ClawsJoy/codex"],
}

ID_RE = re.compile(r"(?:PM|pm)[ _-]?(\d{3,4})\b")
DATE_RE = re.compile(r"^\s*-\s*\d{1,2}-\d{1,2}")
PM_HDR_RE = re.compile(r"自[：:]\s*项目经理|from[：:]\s*项目经理")

# 人工判据（有据，非编造）：脚本默认规则之外，仅 006 需要一句人判
OVERRIDE = {
    "006": (
        "缺",
        "旧指针 codex/_CEO送信_致秘书_20260930_006.md 可验但为 CEO 送信件（非 PM 件）；"
        "同号 PM 件为跨收件人流水（信通 6 件 + _auto 2 件，内容皆与代码『PM 006 拒答判据』不合），"
        "不能确认同源 ⇒ 废旧指针，挂缺口候 PM 判",
    ),
}

CODE_DIRS = [
    "core", "web", "shell", "scripts", "tests", "agents",
    "api", "routes", "engine", "clawsky", "src", "tools", "config",
]
CODE_EXTS = {".py", ".ts", ".js", ".mjs", ".cjs", ".vue", ".sh", ".ps1"}
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    "dist", "data", "tenants", "store-assets", "_pm", "codex",
    ".rollback_codex", ".rollback_dsh", ".before_7384932d0f779462", "_tmp", "archive",
}


def sha16(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def norm_id(raw: str) -> str:
    raw = (raw or "").strip()
    m = re.search(r"(\d{3,4})", raw)
    return str(int(m.group(1))) if m else ""


def read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", "replace")


def frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out = {}
    for line in text[3:end].split("\n"):
        m = re.match(r"^([^:#][^:]*):\s*(.*)$", line.rstrip("\r"))
        if m:
            key = m.group(1).strip()
            if key and key not in out:
                out[key] = m.group(2).strip()
    return out


def is_pm_doc(path: Path, fm: dict) -> bool:
    if "项目经理" in (fm.get("from") or ""):
        return True
    if "项目经理" in (fm.get("发") or ""):
        return True
    head = read_text(path)[:600]
    return bool(PM_HDR_RE.search(head))


def load_index(path: Path):
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.split("\n")
    body = [ln for ln in lines if ln.strip()]
    rows = list(csv.reader(body[1:]))
    return raw, lines, body, rows


def walk_md(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if not name.lower().endswith(".md"):
                continue
            p = Path(dirpath) / name
            try:
                st = p.stat()
            except OSError:
                continue
            if st.st_size > 4 * 1024 * 1024:
                continue
            yield p


def build_catalog(roots) -> dict:
    """id -> [doc dict]，doc: path/root/rel/bytes/sha16/fm/from_pm/seq"""
    cat = {}
    for label, path in roots:
        root = Path(path)
        if not root.is_dir():
            print(f"[skip] 文档根不存在: {label} {root}", file=sys.stderr)
            continue
        for p in walk_md(root):
            try:
                data = p.read_bytes()
            except OSError:
                continue
            text = data.decode("utf-8", "replace")
            fm = frontmatter(text)
            seq = norm_id(fm.get("序号", ""))
            if not seq:
                # 文件名兜底：仅认 pm_ 派件 / 投递 / _to_ 命名族
                m = re.match(r"^(?:_令_|_回_|_补_|_裁_|_派_|投递_|pm_|_to_)", p.name)
                mid = re.search(r"_(\d{3,4})(?:_|\.md$)", p.name)
                if m and mid:
                    seq = norm_id(mid.group(1))
            if not seq:
                continue
            cat.setdefault(seq, []).append({
                "path": p, "root": label,
                "rel": str(p.relative_to(root)).replace("\\", "/"),
                "bytes": len(data), "sha16": sha16(data),
                "fm": fm, "from": fm.get("from", ""),
                "pm": is_pm_doc(p, fm),
            })
    return cat


def scan_code():
    core, wide, dates = {}, {}, set()
    first_ctx = {}

    def take(target, path: Path, text: str):
        for m in ID_RE.finditer(text):
            tail = text[m.end():m.end() + 8]
            if DATE_RE.match(tail):
                dates.add(m.group(1))
                continue
            pid = norm_id(m.group(1))
            target[pid] = target.get(pid, 0) + 1
            key = "core:" if target is core else "wide:"
            if (key + pid) not in first_ctx:
                ln = text.count("\n", 0, m.start()) + 1
                start = text.rfind("\n", 0, m.start()) + 1
                end = text.find("\n", m.start())
                line = text[start:end if end >= 0 else len(text)].strip()
                first_ctx[key + pid] = f"{path.relative_to(REPO)}:{ln} {line[:150]}"

    pa = REPO / "core" / "pa"
    for p in sorted(pa.glob("*.py")):
        take(core, p, read_text(p))
    for d in CODE_DIRS:
        base = REPO / d
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS and not x.startswith(".before")]
            for name in filenames:
                if Path(name).suffix.lower() not in CODE_EXTS or ".before_" in name:
                    continue
                p = Path(dirpath) / name
                try:
                    if p.stat().st_size > 3 * 1024 * 1024:
                        continue
                except OSError:
                    continue
                take(wide, p, read_text(p))
    return core, wide, dates, first_ctx


def verify_row(row, roots_map):
    """返回 (status, detail)：status ∈ repo/root/…/missing；detail = 命中路径信息"""
    rid, root_name, rel, nbytes, sha = row[0], row[1], row[2], row[3], row[4]
    if not root_name or not rel:
        return "empty", ""
    for base in roots_map.get(root_name, []):
        p = Path(base) / rel
        if p.is_file():
            data = p.read_bytes()
            ok = (str(len(data)) == nbytes) and (sha16(data) == sha)
            return ("ok" if ok else "sha_mismatch"), str(p)
    return "missing", ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只算不写")
    ap.add_argument("--docs-roots", default=os.environ.get("PM_DOC_ROOTS", ""),
                    help="os.pathsep 分隔的 标签=路径 列表，覆盖默认文档根")
    ap.add_argument("--debug-id", default="", help="打印该 id 的全部候选文档（诊断用）")
    args = ap.parse_args(argv)

    roots = DEFAULT_ROOTS
    if args.docs_roots:
        roots = []
        for item in args.docs_roots.split(os.pathsep):
            if "=" in item:
                lbl, p = item.split("=", 1)
                roots.append((lbl, p))

    raw_index, lines, body, rows = load_index(INDEX)
    rows = [r for r in rows if r and r[0].strip()]
    ids = [r[0].strip() for r in rows]
    print(f"[index] {INDEX.name}: 字节 {len(raw_index)} · LF {raw_index.count(b'\n')} · "
          f"行 {len(lines)} · 非空 {len(body)} · 数据 {len(rows)}")

    core_refs, wide_refs, date_ids, first_ctx = scan_code()
    print(f"[code] core/pa ids {len(core_refs)} · 全域 ids {len(wide_refs)} · 年份假号 {sorted(date_ids)}")

    cat = build_catalog(roots)
    print(f"[docs] 目录根 {len(roots)} · 带号文档 {sum(len(v) for v in cat.values())} · 唯一 id {len(cat)}")

    if args.debug_id:
        for d in sorted(cat.get(norm_id(args.debug_id), []), key=lambda x: str(x["path"])):
            print(f"  - {d['root']}/{d['rel']} | pm={d['pm']} | from={d['from']} | "
                  f"date={d['fm'].get('date','')} | bytes={d['bytes']} | sha16={d['sha16']}")
        return 0

    # ---------------- classify v0 rows
    out = []
    counts = {}
    stat = {"repo_ok": 0, "ext_ok": 0, "xt_same_rows": 0, "ref_drift_rows": 0}
    # 信通 basename -> 同字节同 sha 判定用
    xt_root = Path(dict(roots).get("信通", ""))
    xt_map = {}
    if xt_root.is_dir():
        for p in walk_md(xt_root):
            try:
                data = p.read_bytes()
            except OSError:
                continue
            xt_map.setdefault(p.name, []).append(sha16(data))
    for r in rows:
        pid = norm_id(r[0])
        status, hit = verify_row(r, ROOT_VERIFY)
        if r[1] and r[2]:
            repo_p = REPO / r[1] / r[2]
            if repo_p.is_file():
                b = repo_p.read_bytes()
                if str(len(b)) == r[3] and sha16(b) == r[4]:
                    stat["repo_ok"] += 1
            if status == "ok":
                stat["ext_ok"] += 1
            if Path(r[2]).name in xt_map and r[4] in xt_map[Path(r[2]).name]:
                stat["xt_same_rows"] += 1
        v0_stat = r[6] if len(r) > 6 else ""
        if r[5].isdigit() and int(r[5]) != core_refs.get(pid, 0) and (r[1] or v0_stat == "missing"):
            stat["ref_drift_rows"] += 1
        v0_stat = r[6] if len(r) > 6 else ""
        pmdocs = [d for d in cat.get(pid, []) if d["pm"]]
        otherdocs = [d for d in cat.get(pid, []) if not d["pm"]]
        ref_core = core_refs.get(pid, 0)
        ref_wide = wide_refs.get(pid, 0)

        # 选择标准指针：PM 件优先 信通/_auto/_pm 顺序
        def rank(d):
            # 账本优先：v0 已核指针全在 _pm 账；投递副本在 _auto；信通 为跨收件人流水（同号多账）
            pref = {"_pm": 0, "_auto": 1, "信通": 2, "codex": 3, "paseo-pm": 4}.get(d["root"], 5)
            tdt = 0 if "_to_td_" in d["path"].name else (1 if "_to_cw_" in d["path"].name else 2)
            return (pref, tdt, str(d["path"]))
        pmdocs.sort(key=rank)
        pick = pmdocs[0] if pmdocs else None

        if r[0] in OVERRIDE:
            cat_name, reason = OVERRIDE[r[0]]
        elif pid in date_ids and not pmdocs:
            cat_name, reason = "废", "年份误配（PM 2026-10-05 式日期），非 pm 号"
        elif v0_stat == "missing" or not r[1]:
            if pick:
                cat_name = "补"
                reason = f"原行 missing；现有可验 PM 源件（{pick['root']}）"
            elif otherdocs:
                cat_name = "移-归属"
                reason = f"无 PM 件；同号件属他席（{otherdocs[0]['fm'].get('from','?')}）⇒ 移出 PM 索引（候 PM 判）"
            else:
                cat_name = "缺"
                reason = "文件名/序号级均无可验源件"
        elif status == "missing":
            cat_name = "缺"
            reason = "指针不可验（repo 与外部根均无）"
        elif not hit:
            cat_name = "缺"
            reason = "指针不可验"
        else:
            pm_ok = False
            data = Path(hit).read_bytes()
            text = data.decode("utf-8", "replace")
            fm = frontmatter(text)
            pm_ok = is_pm_doc(Path(hit), fm)
            if not pm_ok:
                cat_name = "缺"
                reason = "旧指针可验但非 PM 件（误配）" + ("；同号 PM 件未获" if not pick else f"；同号 PM 件= {pick['root']}/{pick['rel']}")
            elif ref_core == 0:
                cat_name = "移-域"
                reason = f"指针可验，但引用域已迁出 core/pa（全域引用 {ref_wide}）"
            else:
                cat_name = "留"
                reason = "指针可验 ＋ PM 件 ＋ core/pa 仍引用"
        counts[cat_name] = counts.get(cat_name, 0) + 1
        out.append({
            "id": r[0],
            "v0_status": v0_stat,
            "category": cat_name,
            "reason": reason,
            "v0_ref_count": r[5] if len(r) > 5 else "",
            "ref_core_pa_now": ref_core,
            "ref_wide_now": ref_wide,
            "v0_pointer": f"{r[1]}/{r[2]}" if r[1] else "",
            "verify_external": status,
            "pm_doc_count": len(pmdocs),
            "other_doc_count": len(otherdocs),
            "pm_doc_root": pick["root"] if pick else "",
            "pm_doc_rel": pick["rel"] if pick else "",
            "pm_doc_bytes": pick["bytes"] if pick else "",
            "pm_doc_sha16": pick["sha16"] if pick else "",
            "pm_doc_from": pick["from"] if pick else "",
            "first_ref": first_ctx.get("core:" + pid, first_ctx.get("wide:" + pid, "")),
        })

    # ---------------- 补行候选（core/pa 现引用、v0 无此 id）
    new_rows = []
    for pid in sorted(core_refs, key=lambda x: int(x)):
        if pid in {norm_id(i) for i in ids}:
            continue
        pmdocs = [d for d in cat.get(pid, []) if d["pm"]]
        def rank2(d):
            pref = {"_pm": 0, "_auto": 1, "信通": 2, "codex": 3, "paseo-pm": 4}.get(d["root"], 5)
            return (pref, str(d["path"]))
        pmdocs.sort(key=rank2)
        pick = pmdocs[0] if pmdocs else None
        counts["补行" if pick else "缺(新)"] = counts.get("补行" if pick else "缺(新)", 0) + 1
        new_rows.append({
            "id": pid, "v0_status": "(absent)", "category": "补行" if pick else "缺",
            "reason": "core/pa 现引用、索引无此行；有可验 PM 源件" if pick else "core/pa 现引用、无可验 PM 源件",
            "v0_ref_count": "", "ref_core_pa_now": core_refs[pid], "ref_wide_now": wide_refs.get(pid, 0),
            "v0_pointer": "", "verify_external": "n/a",
            "pm_doc_count": len(pmdocs), "other_doc_count": len([d for d in cat.get(pid, []) if not d["pm"]]),
            "pm_doc_root": pick["root"] if pick else "", "pm_doc_rel": pick["rel"] if pick else "",
            "pm_doc_bytes": pick["bytes"] if pick else "", "pm_doc_sha16": pick["sha16"] if pick else "",
            "pm_doc_from": pick["from"] if pick else "",
            "first_ref": first_ctx.get("core:" + pid, ""),
        })

    # ---------------- 全仓扩表口径
    wide_extra = sorted([i for i in wide_refs if i not in {norm_id(x) for x in ids}],
                        key=lambda x: int(x))
    wide_extra_doc = [i for i in wide_extra if any(d["pm"] for d in cat.get(i, []))]

    import datetime as _dt
    summary = {
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "generated_from": str(INDEX.relative_to(REPO)),
        "index_bytes": len(raw_index),
        "index_lf": raw_index.count(b"\n"),
        "index_data_rows": len(rows),
        "category_counts": counts,
        "v0_sum_check": sum(counts.get(k, 0) for k in ["留", "移-域", "移-归属", "补", "缺", "废"]),
        "code_ids_core_pa": len(core_refs),
        "code_ids_wide": len(wide_refs),
        "wide_ids_not_in_v0": len(wide_extra),
        "wide_ids_not_in_v0_with_pm_doc": len(wide_extra_doc),
        "date_false_ids": sorted(date_ids),
        "docs_roots": roots,
        "pointer_verify": dict(stat),
    }

    print("\n[分类] " + " · ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print("[校验] v0 六类合计 =", summary["v0_sum_check"], "（应 =", len(rows), "）")
    print("[扩表] 全域引用 id", len(wide_refs), "· v0 未覆盖", len(wide_extra),
          "· 其中有 PM 件候选", len(wide_extra_doc))

    if not args.check:
        fields = list(out[0].keys())
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            for rec in out + new_rows:
                w.writerow(rec)
        OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
        print(f"[write] {OUT_CSV.relative_to(REPO)} ({len(out) + len(new_rows)} 行)")
        print(f"[write] {OUT_JSON.relative_to(REPO)}")

    if summary["v0_sum_check"] != len(rows):
        print("[FAIL] 分类合计 != v0 行数", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
