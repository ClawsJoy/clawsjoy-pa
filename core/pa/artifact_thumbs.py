# -*- coding: utf-8 -*-
"""PPT 缩略图落盘（2026-09-13 批73，C1）。

设计原点：**后端决定落盘位置，前端只用返回值拼 URL**。
历史上缩略图来自灵犀导出的 Windows 目录，前端若拼 UNC 路径，live 与 sandbox 路径不同就会写错地方。

三条已拍板前置：
  1) deck 清洗：**复用 core/gateway/security._is_path_escape**（不写第二套判据）
  2) 体积：单张 2MB / 总量 32MB
  3) 旧 deck 清理：**按 deck 覆盖**（同名目录先清后写）
"""
import base64
import json
import os
import shutil
import urllib.parse

MAX_ONE = 2 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024


def thumb_root():
    """以**本进程实际加载的代码根**为基准 —— live 进程 => /home/flybo/clawsjoy_v5，
    sandbox 进程 => .../clawsjoy_dev。两者各自落到自己的 web/ 下，互不干扰。"""
    here = os.path.abspath(__file__)  # core/pa/artifact_thumbs.py
    root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    return os.path.join(root, "web", "ppt_thumbs")


def _clean_deck(deck):
    """清洗 deck 名：**复用既有判据**，不写第二套。返回 (safe, err)。"""
    d = str(deck or "").strip()
    if not d:
        return "", "deck 不能为空"
    try:
        from core.gateway.security import _is_path_escape

        if _is_path_escape(d):
            return "", "deck 含路径逃逸（绝对路径/~）"
    except Exception:
        # 判据不可用时**保守拒绝**，不放行（宁可拒绝也不能漏）
        if d.startswith("/") or d.startswith("~") or ".." in d.split("/"):
            return "", "deck 含路径逃逸"
    if os.path.basename(d) != d or ".." in d or "/" in d or "\\" in d:
        return "", "deck 不得含路径分隔符"
    return d, None


def _clean_name(name):
    n = str(name or "").strip()
    if not n or os.path.basename(n) != n or "/" in n or "\\" in n or ".." in n:
        return ""
    return n


def save_thumbs(deck, files):
    """按 deck 覆盖写入缩略图。返回 dict；出错返回 {'ok': False, 'error': ...}。"""
    safe, err = _clean_deck(deck)
    if err:
        return {"ok": False, "error": err}
    if not isinstance(files, list) or not files:
        return {"ok": False, "error": "files 不能为空"}

    # 先全量校验体积（避免写一半才发现超限）
    total = 0
    decoded = []
    for f in files:
        if not isinstance(f, dict):
            return {"ok": False, "error": "files 元素必须是对象"}
        name = _clean_name(f.get("filename"))
        if not name:
            return {"ok": False, "error": "filename 非法: %r" % (f.get("filename"),)}
        try:
            raw = base64.b64decode(str(f.get("data_base64") or ""), validate=True)
        except Exception:
            return {"ok": False, "error": "data_base64 解码失败: %s" % name}
        if len(raw) > MAX_ONE:
            return {"ok": False, "error": "单张超限 %s: %d > %d" % (name, len(raw), MAX_ONE)}
        total += len(raw)
        if total > MAX_TOTAL:
            return {"ok": False, "error": "总量超限 %d > %d" % (total, MAX_TOTAL)}
        decoded.append((name, raw, f.get("page_index")))

    dest = os.path.join(thumb_root(), safe)
    # 按 deck 覆盖：同名目录先清后写
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)

    written = []
    for name, raw, page in decoded:
        with open(os.path.join(dest, name), "wb") as fh:
            fh.write(raw)
        written.append({"filename": name, "page_index": page, "bytes": len(raw)})

    manifest = {"deck": safe, "count": len(written), "pages": written}
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    # 相对 URL（**不含任何文件系统路径**）
    url_base = "/web/ppt_thumbs/" + urllib.parse.quote(safe) + "/"
    return {
        "ok": True,
        "count": len(written),
        "bytes_total": total,
        "url_base": url_base,
        "manifest_url": url_base + "manifest.json",
        "pages": written,
    }
