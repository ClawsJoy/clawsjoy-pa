# -*- coding: utf-8 -*-
u"""legacy v5 容错遍历之产品化副本（T125 · 只读 · ⛔ import 顶层 legacy_verify）.

旧容错语义：递归 scandir；目录/迭代中 OSError ⇒ 记错误册，**该目录已读之件保留**，
兄弟继续；last_walk_errors() -> list；可选 manifest 补面。唯 stdlib，⛔ 写盘。
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SKIP = (".obsidian", "Templates", "_垃圾箱", "_冷区")
WALKER_ID = "legacy_v5_tolerant"

_LAST_WALK_ERRORS = []


def reset_errors():
    del _LAST_WALK_ERRORS[:]


def last_walk_errors():
    u"""上一次 walk 之错误册 ⇒ list（空 list ＝ 无错；⛔ None ／ ⛔ 静默吞）。"""
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
        if not rel or rel.split("/", 1)[0] in skip or rel in files:
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
        "walker": WALKER_ID, "state": state, "root": str(root),
        "skip": sorted(skip), "files": sorted(files), "file_count": len(files),
        "supplemented": sorted(supplemented), "supplemented_count": len(supplemented),
        "manifest": str(manifest) if manifest is not None else "",
        "manifest_note": manifest_note,
        "errors": errs, "error_count": len(errs),
    }


__all__ = ["DEFAULT_SKIP", "WALKER_ID", "reset_errors", "last_walk_errors", "walk"]
