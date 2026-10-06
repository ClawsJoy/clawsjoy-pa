# -*- coding: utf-8 -*-
u"""scan_abs_paths.py —— **字面绝对径 + 组织物**之常扫（承 pm_1387 §三.1 ／ pm_1388 §三.2）。

其为「**产品 ⟷ 组织**」之切之器：净机必败之源 ＝ **字面绝对径**（含**我方组织物**
之径：`D:\\Obsidian\\...` ／ `D:\\paseo-*` ／ `D:\\npm-global` ／ `D:\\codex-home`）。

口径（⛔ 手拟 · 逐条附径:行）：
  · **类甲 绝对径**：`[A-Za-z]:[\\/]`（盘符 · ⛔ 误 `http://`）／ `/mnt/[a-z]/` ／ `\\\\srv\\`（UNC）／ `/home/`。
  · **类乙 组织物**（径中含）：`Obsidian/ClawsJoy` ／ `paseo-workspace` ／ `paseo-home` ／ `npm-global`
    ／ `codex-home` ／ `内容工坊` ／ `_tools` ／ `_auto` ／ `_交付` ／ `_老板` ／ `写小说专栏` ／ `dsh`。
  · **载**（活 ∨ 非活）：`.py` 之 **docstring**（`ast` 取）／ 行注（`#` `//` `*` `<!--`）⇒ **非活**；
    其余 ⇒ **活**（⚠ 只为**分流**，⛔ 不判「必需 ∨ 可选」—— 那须人读其上下文 · 见清册）。
  · **面**：`core` ／ `routes` ／ `scripts` ／ `web` ／ `config` ／ `tools`（`tools` ＝ 我方工具面 · 另栏）。
    ⛔ 剔 `*.before_*` ／ `__pycache__` ／ `node_modules` ／ `data` ／ `.rollback_codex`。

⭐ 并出（承 pm_1388 §三.2）：`--obsidian` ⇒ 「**Obsidian**」字面之射程，**分三栏**
  （代码标识符 ／ 提示词·文案 ／ 注·文档 ⇒ 供「重命名之界」之裁）。
"""
import argparse
import ast
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCAN_ROOTS = ("core", "routes", "scripts", "web", "config", "tools")
EXTS = (".py", ".js", ".json", ".yaml", ".yml", ".html", ".css", ".bat", ".ps1", ".cmd", ".txt", ".toml", ".md")
SKIP_DIRS = {"__pycache__", "node_modules", ".git", "data", ".pytest_cache", ".rollback_codex"}

PAT_DRIVE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])[^\s'\"\)\],;`]*")
PAT_MNT = re.compile(r"(?<![A-Za-z0-9])/mnt/[a-z]/[^\s'\"\)\],;`]*")
PAT_UNC = re.compile(r"(?<![\\\w])\\\\[A-Za-z0-9_.\-]+\\")
PAT_HOME = re.compile(r"(?<![A-Za-z0-9])/home/[A-Za-z0-9_.\-]+/")

ORG_MARKS = ("Obsidian/ClawsJoy", "Obsidian\\ClawsJoy", "paseo-workspace", "paseo-home",
             "npm-global", "codex-home", "内容工坊", "_tools", "_auto",
             "_交付", "_老板", "写小说专栏", "\\dsh", "/dsh")

_looks_comment = re.compile(r"^\s*(#|//|\*|/\*|<!--)")


def _docstring_lines(src):
    u"""`.py` 之 docstring 行号集（`ast` 取 · ⛔ 猜引号）。"""
    out = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                s = body[0].value.lineno
                e = getattr(body[0].value, "end_lineno", s)
                out.update(range(s, e + 1))
    return out


def _kind(rel, src, lineno, line):
    u"""载（活 ∨ 非活）之判（⚠ 只为分流 · ⛔ 判「必需 ∨ 可选」）。"""
    if rel.endswith(".md"):
        return "注·文档"
    if _looks_comment.match(line):
        return "注"
    if rel.endswith(".py") and lineno in _docstring_lines(src):
        return "docstring"
    return "活"


def scan(root=ROOT, roots=SCAN_ROOTS):
    rows = []
    for r in roots:
        base = os.path.join(root, r)
        if not os.path.isdir(base):
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in sorted(fns):
                if ".before_" in fn or not fn.lower().endswith(EXTS):
                    continue
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, root).replace("\\", "/")
                try:
                    src = io.open(p, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                for i, line in enumerate(src.splitlines(), 1):
                    for name, pat in (("盘符", PAT_DRIVE), ("WSL 挂载", PAT_MNT),
                                      ("UNC", PAT_UNC), ("本机绝对径", PAT_HOME)):
                        for m in pat.finditer(line):
                            lit = m.group(0)
                            rows.append({"file": rel, "line": i, "类": name, "径": lit,
                                         "组织物": any(k in lit for k in ORG_MARKS),
                                         "载": _kind(rel, src, i, line)})
    return rows


_OBS_REF = re.compile(r"Obsidian")
_OBS_IDENT = re.compile(r"(obsidian|OBSIDIAN)[A-Za-z_0-9]*")


def scan_obsidian(root=ROOT, roots=SCAN_ROOTS):
    u"""「Obsidian」字面之射程 —— 三栏：代码标识符 ／ 提示词·文案 ／ 注·文档。"""
    cols = {"代码标识符": [], "提示词·文案": [], "注·文档": []}
    for r in roots:
        base = os.path.join(root, r)
        if not os.path.isdir(base):
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in sorted(fns):
                if ".before_" in fn or not fn.lower().endswith(EXTS):
                    continue
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, root).replace("\\", "/")
                try:
                    src = io.open(p, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                for i, line in enumerate(src.splitlines(), 1):
                    if not _OBS_REF.search(line):
                        continue
                    k = _kind(rel, src, i, line)
                    _s = line.lstrip()
                    # 代码标识符：import/from 之模块名 · 标识符用于调用/下标/属性/赋值 · ⛔ 引号内之文案
                    ident = bool(
                        re.match(r"\s*(from|import)\b.*obsidian", line, re.I)
                        or re.search(r"(?<![\w'\"])(?i:obsidian)[A-Za-z_0-9]*\s*[\[.(]", line)
                        or re.search(r"OBSIDIAN[A-Z_0-9]*\s*=", line)
                        or re.search(r"[A-Za-z_]*[Oo]bsidian[A-Za-z_]*\s*=", line)
                    ) and not _looks_comment.match(line)
                    if k in ("注", "docstring", "注·文档"):
                        col = "注·文档"
                    elif ident:
                        col = "代码标识符"
                    else:
                        col = "提示词·文案"
                    cols[col].append({"file": rel, "line": i, "载": k,
                                      "文": line.strip()[:120]})
    return cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--obsidian", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.obsidian:
        cols = scan_obsidian(a.root)
        if a.json:
            print(json.dumps(cols, ensure_ascii=False, indent=1))
        else:
            print(u"「Obsidian」字面之射程 —— 三栏（⛔ 一刀切重命名 · 须先分栏再裁）")
            for k in ("代码标识符", "提示词·文案", "注·文档"):
                print(u"== %s：%d 处 ==" % (k, len(cols[k])))
                for x in cols[k]:
                    print(u"  %-44s:%-5d [%s] %s" % (x["file"], x["line"], x["载"], x["文"]))
        return 0

    rows = scan(a.root)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    print(u"字面绝对径之扫（面：%s · 剔 *.before_* ／ __pycache__ ／ data）" % " ／ ".join(SCAN_ROOTS))
    print(u"总 %d 处 ｜ 活 %d ｜ 非活 %d ｜ 组织物 %d"
          % (len(rows), sum(1 for r in rows if r["载"] == "活"),
             sum(1 for r in rows if r["载"] != "活"),
             sum(1 for r in rows if r["组织物"])))
    cur = None
    for r in sorted(rows, key=lambda x: (x["file"], x["line"])):
        if r["file"] != cur:
            cur = r["file"]
            print(u"\n=== %s" % cur)
        print(u"  :%-5d [%s%s] %s" % (r["line"], r["载"],
                                      u" · 组织物" if r["组织物"] else "", r["径"][:100]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
