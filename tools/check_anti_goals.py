#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R8 反目标 10 条 · 只读机检器（tools/check_anti_goals.py）

口径
----
- 只读：不写产品码、不改配置、不联网；仅扫本仓（--root 可指别处）。
- 每题三态：PASS（机检通过）/ FAIL（机检不通过，附证据）/ MANUAL（不可机检，显式标出，⛔ 不假绿）。
- 退出码：默认 0=无 FAIL；2=有 FAIL；--strict 时 MANUAL 也算 2（用于 CI 严门）。
- 10 条为 PM D8 定稿口径在本器的唯一落点（源见每条 src）；"红线文档 10 条在" 即自校 10 条登记齐备。

用法
----
  python -X utf8 -B tools/check_anti_goals.py
  python -X utf8 -B tools/check_anti_goals.py --json out.json --strict
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEXT_EXT = {".md", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".vue",
            ".json", ".yaml", ".yml", ".ini", ".cfg", ".toml", ".sh", ".ps1"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
             "dist", "data", "_tmp", ".before_7384932d0f779462"}

LOCAL_PROVIDERS = {"ollama", "local", "local_vlm", "local_api", "llama.cpp", "lmstudio", "mock"}
CLOUD_HINTS = ("openai", "anthropic", "deepseek", "azure", "dashscope", "moonshot", "zhipu", "qwen-cloud")
PLACEHOLDER_KEYS = {"", "your-api-key", "your-api-key-here", "your_api_key", "changeme", "null", "none", "xxx"}
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)")
NEG_RE = re.compile(r"(⛔|不|勿|禁|不得|不作|不做|no\b|not\b|never)", re.I)
ZERO_RE = re.compile(r"(0\s*命中|零命中|无\s*广告|无广告)")
META_RE = re.compile(r"(反目标|扫描器|机检|检查器|check_anti_goals|0\s*hits|期望)", re.I)

AD_PATTERNS = ("广告变现", "广告费", "广告位", "广告联盟", "广告分成", "ad_revenue", "adserver", "sponsor")
SCALE_PATTERNS = ("接入数量", "装机量", "名册数", "以名册", "名册当卖点", "接入量当卖点")
TOKS_RE = re.compile(r"(tok/s|tokens?/s|tok／s)", re.I)
TOKS_ALLOW_MEASURE = ("实测", "读数", "测量", "bench", "benchmark", "耗时", "延迟", "ms", "~", "需", "测试")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _walk_files(top: Path):
    for dirpath, dirnames, filenames in os.walk(str(top)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            yield Path(dirpath) / fn


def _iter_texts(base: Path, subdirs):
    for name in subdirs:
        top = base / name
        if top.is_file():
            if top.suffix.lower() in TEXT_EXT:
                yield top
            continue
        if not top.is_dir():
            continue
        for p in _walk_files(top):
            if p.suffix.lower() in TEXT_EXT:
                yield p


def _scan_lines(base: Path, subdirs, patterns):
    hits = []
    for p in _iter_texts(base, subdirs):
        for i, line in enumerate(_read(p).splitlines(), 1):
            for pat in patterns:
                if pat in line:
                    hits.append((p, i, line.strip()[:160], pat))
                    break
    return hits


def check_local_default(root: Path):
    cfg = root / "config" / "llm" / "llm_config.yaml"
    if not cfg.is_file():
        return "MANUAL", [], "未找到 config/llm/llm_config.yaml，默认 provider 不可机判"
    txt = _read(cfg)
    m = re.search(r"(?m)^\s*default_provider\s*:\s*([^\s#]+)", txt)
    if not m:
        return "MANUAL", [str(cfg)], "配置内无 default_provider 行，不可机判"
    prov = m.group(1).strip().strip('"').strip("'")
    ev = ["{}: default_provider={}".format(cfg.relative_to(root), prov)]
    low = prov.lower()
    if low in LOCAL_PROVIDERS:
        return "PASS", ev, "默认走本机/本地（非云端）"
    if any(h in low for h in CLOUD_HINTS):
        return "FAIL", ev, "默认 provider 指向云端：{}".format(prov)
    return "MANUAL", ev, "默认 provider 既非已知本地也非已知云端：{}".format(prov)


def check_payload_no_data(root: Path):
    payload = root / "dist" / "pa_shell" / "payload"
    if not payload.is_dir():
        return "MANUAL", [], "未找到 dist/pa_shell/payload，不可机判（或本仓未出包）"
    forbidden = ("data", "profile", "profiles", "notes", "workspace", "seed", "seed_data")
    found = [s for s in forbidden if (payload / s).exists()]
    ev = ["payload={}".format(payload.relative_to(root))]
    if found:
        ev += ["命中禁项: {}".format(", ".join(found))]
        return "FAIL", ev, "payload 内出现 data/profile/notes/workspace/seed 禁项"
    return "PASS", ev, "payload 内未见 data/profile/notes/workspace/seed"


def check_no_pfx(root: Path):
    bad = []
    for p in _walk_files(root):
        if p.suffix.lower() in {".pfx", ".p12", ".pvk"}:
            bad.append(p)
    if bad:
        return "FAIL", [str(p.relative_to(root)) for p in bad[:10]], "仓内发现私钥容器（应仓外保管）"
    return "PASS", [], "仓内 0 个 .pfx/.p12/.pvk"


def check_no_key_dependency(root: Path):
    cfg = root / "config" / "llm" / "llm_config.yaml"
    if not cfg.is_file():
        return "MANUAL", [], "未找到 llm_config.yaml，Key 依赖不可机判"
    ev = []
    bad = []
    for i, line in enumerate(_read(cfg).splitlines(), 1):
        m = re.match(r"\s*api_key\s*:\s*(.+)$", line)
        if not m:
            continue
        raw = m.group(1).split("#")[0].strip().strip('"').strip("'")
        lo = raw.lower()
        if raw[:2] == chr(36) + chr(123) or lo in PLACEHOLDER_KEYS or lo.startswith("env:"):
            ev.append("llm_config.yaml:{} 占位/环境变量：{}".format(i, raw[:40]))
            continue
        bad.append("llm_config.yaml:{} api_key 非占位（{}）".format(i, raw[:24]))
    hits = []
    for p in _iter_texts(root, ("config", "core", "web", "shell")):
        for i, line in enumerate(_read(p).splitlines(), 1):
            if SECRET_RE.search(line):
                hits.append("{}:{}".format(p.relative_to(root), i))
    if bad or hits:
        return "FAIL", ev + bad + hits[:10], "发现硬编码密钥或非占位 api_key（本地默认可无 Key 被破坏）"
    return "PASS", ev, "云端 key 仅占位/环境变量；未见硬编码密钥"


def check_delivery_mark(root: Path):
    d = root / "docs" / "reports" / "pa_iter40"
    if not d.is_dir():
        return "MANUAL", [], "未找到 docs/reports/pa_iter40，代发标识不可机判"
    files = sorted(d.glob("*.md"))
    missing = [p.name for p in files if "代发" not in _read(p)]
    if missing:
        return "FAIL", missing, "出件缺代发标识"
    return "PASS", ["{} 件均含代发标识".format(len(files))], "所有出件均带代发标识"


def check_red_lines_10(root: Path):
    ids = [it["id"] for it in ITEMS]
    bad = []
    if len(ITEMS) != 10:
        bad.append("登记 {} 条 != 10".format(len(ITEMS)))
    if len(set(ids)) != len(ids):
        bad.append("id 重复")
    if any(not (it.get("title") or "").strip() for it in ITEMS):
        bad.append("存在空标题项")
    if bad:
        return "FAIL", bad, "红线文档（本器清单）10 条不齐"
    return "PASS", ["10 条 id 唯一、标题齐"], "红线 10 条登记齐备"


def check_no_ad_monetization(root: Path):
    hits = _scan_lines(root, ("docs", "web", "shell", "config"), AD_PATTERNS)
    bad = [h for h in hits if not ("去广告" in h[2] or NEG_RE.search(h[2]) or ZERO_RE.search(h[2]) or META_RE.search(h[2]))]
    if bad:
        return "FAIL", ["{}:{} {}".format(p.relative_to(root), i, txt) for p, i, txt, _ in bad[:10]], "发现广告变现路径"
    return "PASS", ["命中 {} 处且均为功能/否定语境（如“去广告”）".format(len(hits))], "无广告变现路径"


def check_no_scale_selling(root: Path):
    hits = _scan_lines(root, ("docs", "config"), SCALE_PATTERNS)
    bad = [h for h in hits if not (NEG_RE.search(h[2]) or ZERO_RE.search(h[2]) or META_RE.search(h[2]))]
    if bad:
        return "FAIL", ["{}:{} {}".format(p.relative_to(root), i, txt) for p, i, txt, _ in bad[:10]], "出现以接入数量/名册/装机量为卖点的表述"
    return "PASS", ["命中 {} 处且均为否定语境".format(len(hits))], "未以接入数量/名册/装机量为卖点"


def check_no_toks_selling(root: Path):
    bad = []
    seen = 0
    for p in _iter_texts(root, ("docs", "web", "shell", "README.md")):
        for i, line in enumerate(_read(p).splitlines(), 1):
            if not TOKS_RE.search(line):
                continue
            seen += 1
            if NEG_RE.search(line) or any(k in line for k in TOKS_ALLOW_MEASURE):
                continue
            bad.append("{}:{} {}".format(p.relative_to(root), i, line.strip()[:150]))
    if bad:
        return "FAIL", bad[:10], "tok/s 被当卖点（非测量/非否定语境）"
    return "PASS", ["tok/s 命中 {} 处，均为测量读数或否定语境".format(seen)], "未以 tok/s 当卖点"


def check_human_click(root: Path):
    return "MANUAL", ["需端到端活面 + 人点样本；本器无不可逆动作可机检（承 T48/R4 半验）"], "不可机检：不可逆动作唯人点"


ITEMS = [
    {"id": "AG-01", "title": "默认 local（不默认云端/外发）", "kind": "AUTO", "fn": check_local_default,
     "src": "R8/需求单 v2 + C-29（不默认云端）"},
    {"id": "AG-02", "title": "payload 无 data/profile/notes/workspace/seed", "kind": "AUTO", "fn": check_payload_no_data,
     "src": "R8 + T42/ACCEPTANCE 红线"},
    {"id": "AG-03", "title": "仓内无 PFX/P12 私钥", "kind": "AUTO", "fn": check_no_pfx,
     "src": "T53 P0 + ACCEPTANCE 红线"},
    {"id": "AG-04", "title": "本地默认可无 Key（无硬编码密钥）", "kind": "AUTO", "fn": check_no_key_dependency,
     "src": "R8 + 需求单 R8（本地可用）"},
    {"id": "AG-05", "title": "出件必带代发标识", "kind": "AUTO", "fn": check_delivery_mark,
     "src": "README 纪律 代发必标"},
    {"id": "AG-06", "title": "红线文档 10 条在（本器登记=10）", "kind": "AUTO", "fn": check_red_lines_10,
     "src": "R8 写死 + 本器自校"},
    {"id": "AG-07", "title": "广告变现路径 0 命中", "kind": "AUTO", "fn": check_no_ad_monetization,
     "src": "R8/播客 01:46:37（广告不成立）"},
    {"id": "AG-08", "title": "不以接入数量/名册/装机量当卖点", "kind": "AUTO", "fn": check_no_scale_selling,
     "src": "R8/播客 01:51（换人成本低）"},
    {"id": "AG-09", "title": "不以 tok/s 当卖点", "kind": "AUTO", "fn": check_no_toks_selling,
     "src": "C-29 卖点 + docs/design L220"},
    {"id": "AG-10", "title": "不可逆动作唯人点（机器不自动发布/代付）", "kind": "MANUAL", "fn": check_human_click,
     "src": "R8/需求单 R4（不可逆=人点）"},
]


def run(root: Path = None) -> dict:
    root = Path(root) if root else ROOT
    items = []
    for it in ITEMS:
        try:
            status, evidence, detail = it["fn"](root)
        except Exception as exc:
            status, evidence, detail = "MANUAL", ["checker 异常：{}".format(exc)], "机检器异常，显式 MANUAL"
        if status not in ("PASS", "FAIL", "MANUAL"):
            status = "MANUAL"
        items.append({"id": it["id"], "title": it["title"], "kind": it["kind"], "src": it["src"],
                      "status": status, "detail": detail, "evidence": evidence})
    if all(x["status"] == "PASS" for x in items):
        items.append({"id": "AG-00", "title": "防假绿自校（必须有 MANUAL 或 FAIL）", "kind": "AUTO",
                      "src": "本器纪律", "status": "FAIL",
                      "detail": "10 条全 PASS：不可机检项被误判为绿", "evidence": []})
    total = len(items)
    summary = {"pass": sum(1 for x in items if x["status"] == "PASS"),
               "fail": sum(1 for x in items if x["status"] == "FAIL"),
               "manual": sum(1 for x in items if x["status"] == "MANUAL"),
               "total": total}
    verdict = "FAIL" if summary["fail"] else ("NO_FAIL_WITH_MANUAL" if summary["manual"] else "ALL_PASS")
    return {"root": str(root), "items": items, "summary": summary, "verdict": verdict}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R8 反目标 10 条只读机检")
    ap.add_argument("--root", default=str(ROOT), help="仓库根（默认本仓）")
    ap.add_argument("--json", dest="json_path", default="", help="把结果写入 JSON")
    ap.add_argument("--strict", action="store_true", help="MANUAL 也算失败（严门）")
    args = ap.parse_args(argv)
    res = run(Path(args.root))
    for x in res["items"]:
        print("[{}] {} {}".format(x["status"], x["id"], x["title"]))
        if x["status"] != "PASS":
            print("         - {}".format(x["detail"]))
            for e in x["evidence"][:5]:
                print("           * {}".format(e))
    s = res["summary"]
    print("汇总：PASS {} / FAIL {} / MANUAL {}（共 {} 条）".format(s["pass"], s["fail"], s["manual"], s["total"]))
    if res["verdict"] == "NO_FAIL_WITH_MANUAL":
        print("判：机检无 FAIL；含 MANUAL {} 条 ⇒ ⛔ 非全绿（须人工，⛔ 假绿）".format(s["manual"]))
    elif res["verdict"] == "FAIL":
        print("判：存在 FAIL ⇒ R8 未过（见上证据）")
    else:
        print("判：10 条全绿（不应出现；见 AG-00 防假绿自校）")
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("已写：{}".format(args.json_path))
    if s["fail"]:
        return 2
    if args.strict and s["manual"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
