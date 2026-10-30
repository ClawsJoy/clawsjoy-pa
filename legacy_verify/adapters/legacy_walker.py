# -*- coding: utf-8 -*-
u"""legacy_walker.py -- legacy v5 容错遍历（scandir 保已读 ＋ 错误入册 ＋ 可选清单补面）.

PD T106 条件：现役 precision_inject 无 last_walk_errors 等价 API（_walk_warn 仅 print；
os.walk(onerror) ⛔ 保已读条目）⇒ legacy 面无 C10 可 pass。本件在 legacy_verify/ 内
**自含重写**旧容错 walker（⛔ import 产品 · ⛔ 写产品 data · 唯读给定根）：

  · 递归 scandir；某目录/条目出 OSError ⇒ 记入 _LAST_WALK_ERRORS，**该目录已读之件保留**
    （继续兄弟条目；旧目录中途出错则保已得、停该目录）；
  · `last_walk_errors() -> list`（对外唯一留痕面；空 list 亦为合法读数）；
  · 可选 manifest 补面：清单列出而 walk 未得之件，仅当实际存在且非排除面 ⇒ 补入 files
    （记 `supplemented`；清单缺失不算错）。

只读；无产品 import；供 legacy 验器 C10 / 测试注入 OSError 之用。
"""
from __future__ import annotations

import os
from pathlib import Path

#: legacy v5 静态排除面（顶层段 · 与 precision_inject_v9.LEGACY_SKIP_TOP 同义）
DEFAULT_SKIP = (".obsidian", "Templates", "_垃圾箱", "_冷区")

WALKER_ID = "legacy_v5_tolerant"

_LAST_WALK_ERRORS = []


def reset_errors():
    u"""清空错误册（每次 walk 起手清；⛔ 跨 walk 串）。"""
    del _LAST_WALK_ERRORS[:]


def last_walk_errors():
    u"""上一次 walk 之错误册 ⇒ **list**（空 list ＝ 无错；⛔ None ／ ⛔ 静默吞）。"""
    return list(_LAST_WALK_ERRORS)


def _record_error(path, exc):
    _LAST_WALK_ERRORS.append({
        "path": str(path),
        "error": type(exc).__name__,
        "detail": str(getattr(exc, "strerror", "") or exc)[:200],
    })


def _rel(root, path):
    try:
        return Path(path).relative_to(root).as_posix()
    except Exception:
        return str(path).replace(chr(92), "/")


def _walk_dir(root, current, skip, files):
    u"""递归 scandir；出错记册且**保已读**（⛔ 整棵丢）。"""
    try:
        it = os.scandir(str(current))
    except OSError as exc:
        _record_error(current, exc)
        return
    try:
        while True:
            try:
                entry = next(it)
            except StopIteration:
                break
            except OSError as exc:
                _record_error(current, exc)
                break                     # 保已读：本目录先得之件已在 files
            try:
                name = entry.name
                if name in skip:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    _walk_dir(root, Path(entry.path), skip, files)
                elif entry.is_file(follow_symlinks=False) and name.endswith(".md"):
                    files.add(_rel(root, entry.path))
            except OSError as exc:
                _record_error(Path(getattr(entry, "path", current)), exc)
    finally:
        close = getattr(it, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


def _manifest_rel(line):
    rel = str(line or "").strip().replace(chr(92), "/")
    if not rel or rel.startswith("/") or ":" in rel:
        return ""
    parts = rel.split("/")
    if ".." in parts:
        return ""
    return rel


def _apply_manifest(root, files, skip, manifest):
    u"""清单补面：清单载而 walk 未得、且**实际存在**之件 ⇒ 补入；清单缺失 ⇒ 无补无错。"""
    supplemented = []
    mp = Path(manifest)
    if not mp.is_file():
        return supplemented, ""
    try:
        lines = mp.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        _record_error(mp, exc)
        return supplemented, "manifest_unreadable"
    for line in lines:
        rel = _manifest_rel(line)
        if not rel:
            continue
        if rel.split("/", 1)[0] in skip:
            continue
        if rel in files:
            continue
        p = root / rel
        try:
            if p.is_file():
                files.add(rel)
                supplemented.append(rel)
        except OSError as exc:
            _record_error(p, exc)
    return supplemented, ""


def walk(root, skip=None, manifest=None):
    u"""容错 walk ⇒ 报告 dict（files/supplemented/errors/...）；⛔ 抛（错入册）。"""
    root = Path(root)
    skip = set(skip if skip is not None else DEFAULT_SKIP)
    reset_errors()
    files = set()
    state = "ok"
    if not root.is_dir():
        _record_error(root, OSError("根不存在或非目录"))
        state = "unset"
    else:
        _walk_dir(root, root, skip, files)
    supplemented, manifest_note = [], ""
    if manifest is not None:
        supplemented, manifest_note = _apply_manifest(root, files, skip, manifest)
    errs = last_walk_errors()
    return {
        "walker": WALKER_ID,
        "state": state,
        "root": str(root),
        "skip": sorted(skip),
        "files": sorted(files),
        "file_count": len(files),
        "supplemented": sorted(supplemented),
        "supplemented_count": len(supplemented),
        "manifest": str(manifest) if manifest is not None else "",
        "manifest_note": manifest_note,
        "errors": errs,
        "error_count": len(errs),
    }


__all__ = [
    "DEFAULT_SKIP",
    "WALKER_ID",
    "reset_errors",
    "last_walk_errors",
    "walk",
]
