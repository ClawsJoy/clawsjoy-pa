#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""X-03 防复发扫描器（**只报不改**）：文件编码显式化债务。

为什么要有它:
  X-03 债务（`open()` / `read_text()` 不带 `encoding=`）在 Linux 上无害（默认 UTF-8），
  在 Windows 上默认 **locale 编码**（本机 cp936/GBK）⇒ 读中文文件直接 `UnicodeDecodeError`、
  写出的字节 Linux 侧再读即乱码。它是一条**跨平台一致性债务**，不是"少写一个参数"。
  修完存量后必须防**新增**：否则下一批代码又会重新长出同类债务。

口径（**用 AST，不用行正则** —— 行正则会把字符串/注释里的 `open(...)` 算成债务，
  2026-09-17 因此报出 125 处，其中 91 处（73%）是误报）:
  计入:
    1. 内建 `open(...)`：非二进制模式（mode 无 `b`）且调用内无 `encoding=`；
    2. 文本 IO 方法 `.read_text(...)` / `.write_text(...)`：调用内无 `encoding=`；
    3. 可证明为 pathlib 的 `.open(...)`（接收者是 `Path(...)` / `pathlib.Path(...)` 等）。
  不计入（**本仓实测 32 处，全部属此类**）:
    - 模块接收者的 `.open(...)`：`io.open` 21 / `Image.open` 4 / `os.open` 3 /
      `gzip.open` 2 / `tarfile.open` 1 / `_os_note.open`（`import os as _os_note`）1
      —— 其中 `io.open`/`gzip.open` 接受 `encoding`（本仓已带）、`os.open`/`Image.open`/`tarfile.open`
      **不接受** `encoding`（加了会 TypeError）；
    - 二进制模式（`rb`/`wb`/`ab`）—— `encoding` 不适用；
    - `data/`（gitignored 运行期/临时产物，非仓库产物）、`.git/`、`archive/`、虚拟环境等。

未判定（**如实标注的盲区**）: 接收者静态无法判定是否为 pathlib 的 `.open(...)`
  （如 `f.open(...)`）**不计入判据**，只在 `--explain` / JSON 里以 `unresolved_attr_open` 计数留痕。
  本仓当前为 0。

用法:
  python tools/check_encoding_explicit.py                # 扫描仓库根，只报
  python tools/check_encoding_explicit.py --json         # 机器可读
  python tools/check_encoding_explicit.py --explain      # 列出每个候选的判定与理由
  python tools/check_encoding_explicit.py --root <dir>   # 扫描任意目录（用于验证判据本身）
  python tools/check_encoding_explicit.py --strict        # 有新增债务时退出码 1（默认恒 0，只报）
退出码: 默认 **0**（报告器）；`--strict` 时发现「未在基线 allow 内」的债务 ⇒ 1。

证据等级: 【实测】D:\clawsjoy_v9 · Windows 11 + Python 3.12 · 2026-09-18。
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import sys

# 接收者「不是文本 IO」的模块（含 `import X as Y` 别名解析后的真名）
NON_TEXT_MODULES = {"os", "tarfile", "zipfile", "gzip", "bz2", "lzma", "io",
                    "mmap", "socket", "codecs", "Image", "PIL"}
# 可证明为 pathlib 的名字（用于把 `.open()` 纳入判据）
PATHLIB_NAMES = {"Path", "PurePath", "PosixPath", "WindowsPath", "PurePosixPath", "PureWindowsPath"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "archive", ".venv", "venv", "env",
             ".mypy_cache", ".pytest_cache", ".ruff_cache", "data", "build", "dist", ".idea"}
_REPO = pathlib.Path(__file__).resolve().parent.parent


def _aliases(tree):
    """模块级别名表: 本地名 -> 真名（`import os as _os_note` -> {"_os_note": "os"}）。"""
    alias = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                alias[a.asname or a.name.split(".")[0]] = a.name.split(".")[0]
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                if a.name != "*":
                    alias[a.asname or a.name] = (n.module or "") + "." + a.name
    return alias


def _is_builtin_open(func, alias):
    if isinstance(func, ast.Name):
        return func.id == "open" and alias.get("open") is None and "open" not in alias
    if isinstance(func, ast.Attribute) and func.attr == "open":
        return getattr(func.value, "id", None) == "builtins"
    return False


def _mode_binary(node):
    """None = 模式未知（非常量）；True/False = 是否二进制。"""
    mode = None
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
        mode = node.args[1].value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            mode = kw.value.value
    return None if mode is None else ("b" in mode)


def _has_encoding(node):
    return any(kw.arg == "encoding" for kw in node.keywords)


def _root_name(expr):
    while isinstance(expr, ast.Attribute):
        expr = expr.value
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Call):
        return _root_name(expr.func)
    return None


def _classify_attr_open(func, alias):
    """返回 (计入?, 理由)。"""
    recv = func.value
    root = _root_name(recv)
    real = alias.get(root) if root else None
    real_root = real.split(".")[0] if isinstance(real, str) else None
    if real_root in NON_TEXT_MODULES or root in NON_TEXT_MODULES:
        return False, "non-text-module:%s" % (real_root or root)
    if root in PATHLIB_NAMES or (real_root == "pathlib"):
        return True, "pathlib-open"
    return False, "unresolved-receiver:%s" % (root or type(recv).__name__)


def scan(root, explain=False):
    findings, skipped, unresolved = [], [], 0
    scanned = 0
    root = pathlib.Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = pathlib.Path(dirpath) / fn
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError as e:
                skipped.append(["%s" % rel, "syntax-error:%s" % e])
                continue
            scanned += 1
            alias = _aliases(tree)
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                f = n.func
                hit = None
                if _is_builtin_open(f, alias):
                    bm = _mode_binary(n)
                    if bm is True:
                        skipped.append(["%s:%d" % (rel, n.lineno), "binary-mode"])
                        continue
                    if _has_encoding(n):
                        skipped.append(["%s:%d" % (rel, n.lineno), "has-encoding"])
                        continue
                    hit = ("builtin-open", bm is None)
                elif isinstance(f, ast.Attribute) and f.attr in ("read_text", "write_text"):
                    if _has_encoding(n):
                        skipped.append(["%s:%d" % (rel, n.lineno), "has-encoding"])
                        continue
                    hit = (f.attr, False)
                elif isinstance(f, ast.Attribute) and f.attr == "open":
                    ok, why = _classify_attr_open(f, alias)
                    if not ok:
                        if why.startswith("unresolved-receiver"):
                            unresolved += 1
                        if explain:
                            skipped.append(["%s:%d" % (rel, n.lineno), why])
                        continue
                    if _has_encoding(n):
                        skipped.append(["%s:%d" % (rel, n.lineno), "has-encoding"])
                        continue
                    hit = ("attr-open", False)
                if hit:
                    findings.append({
                        "file": rel, "line": n.lineno, "kind": hit[0],
                        "mode_unknown": hit[1], "call": ast.unparse(n)[:140],
                    })
    return {"scanned_files": scanned, "count": len(findings), "findings": findings,
            "unresolved_attr_open": unresolved,
            "skipped_candidates": skipped if explain else []}


def _baseline_path():
    return _REPO / "tests" / "baseline" / "encoding_explicit_baseline.json"


def load_baseline(path=None):
    p = pathlib.Path(path) if path else _baseline_path()
    if not p.exists():
        return {"expected_count": None, "allow": [], "_missing": str(p)}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"expected_count": None, "allow": [], "_unreadable": repr(e)}


def _is_allowed(finding, base):
    for a in base.get("allow", []):
        if a.get("file") != finding["file"]:
            continue
        if a.get("line") in (None, finding["line"]):
            return True
    return False


def scan_summary(root=None, baseline=None):
    """给门禁调用: 返回带基线对照的摘要（**不抛异常**）。"""
    res = scan(root or _REPO)
    base = load_baseline(baseline)
    new = [f for f in res["findings"] if not _is_allowed(f, base)]
    return {
        "scanned_files": res["scanned_files"],
        "total": res["count"],
        "allowed": res["count"] - len(new),
        "new_findings": new,
        "unresolved_attr_open": res["unresolved_attr_open"],
        "expected_count": base.get("expected_count"),
        "baseline_state": ("missing" if base.get("_missing") else
                           ("unreadable" if base.get("_unreadable") else "ok")),
    }


def main():
    ap = argparse.ArgumentParser(description="X-03 防复发扫描（只报不改）")
    ap.add_argument("--root", default=str(_REPO), help="扫描根（默认仓库根）")
    ap.add_argument("--baseline", default=None, help="基线 JSON（默认 tests/baseline/encoding_explicit_baseline.json）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--explain", action="store_true", help="列出每个候选的判定与理由")
    ap.add_argument("--strict", action="store_true", help="有新增债务时退出码 1（默认恒 0）")
    a = ap.parse_args()
    res = scan(a.root, explain=a.explain)
    base = load_baseline(a.baseline)
    new = [f for f in res["findings"] if not _is_allowed(f, base)]
    summary = {
        "root": str(a.root), "scanned_files": res["scanned_files"], "total": res["count"],
        "allowed": res["count"] - len(new), "new_count": len(new), "new_findings": new,
        "unresolved_attr_open": res["unresolved_attr_open"],
        "expected_count": base.get("expected_count"), "findings": res["findings"],
    }
    if a.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1 if (a.strict and new) else 0
    print("[X03] 扫描 %d 个 .py | 计入口径命中 %d 处 | 基线 allow 内 %d 处 | 新增 %d 处"
          % (res["scanned_files"], res["count"], summary["allowed"], len(new)))
    print("[X03] 未判定(接收者非 pathlib，不计入判据) %d 处；基线 expected_count=%r"
          % (res["unresolved_attr_open"], base.get("expected_count")))
    for f in res["findings"]:
        mark = "NEW" if f in new else "allow"
        print("  [%s] %s:%d  [%s]%s  %s" % (mark, f["file"], f["line"], f["kind"],
                                            " mode?" if f["mode_unknown"] else "", f["call"]))
    if a.explain:
        print("---- 判定明细（含未计入）----")
        for k, why in res["skipped_candidates"]:
            print("  %s  %s" % (k, why))
    return 1 if (a.strict and new) else 0


if __name__ == "__main__":
    sys.exit(main())