# -*- coding: utf-8 -*-
u"""legacy_verify adapter · precision_inject v9（只读 · ⛔ 产品 import 本件）.

用途：为 legacy v5 验器（legacy_verify/core/pa/verify.py）之 C5/C6/C7/C10/C9 提供
**现役 v9 之等价适配面**；本件只被 legacy_verify/run_quick.py 与 legacy 测试 import，
⛔ 修改 core/，⛔ 成为产品运行时依赖。

规范化（T106 PD 裁）：
- C7 legacy _scan_excluded ＝ **顶层段 ＋ 静态四名 ＋ 反斜杠归一**（⛔ 现役 _rel_excluded 之任一段＋配置源）；
- C10 现役**无** last_walk_errors（_walk_warn 仅 print；os.walk(onerror) ⛔ 保已读条目）
  ⇒ 本层自含 legacy_walker（scandir 保已读 ＋ 错误入册 ＋ 可选清单补面）补此面，
    legacy_walk_errors() -> list；C10 因之可**真 PASS**（⛔ 伪空表假绿）；
- C6 sops_dir 取现役 _obsidian_cfg() 同键；空 _vault_path() ⇒ None（⛔ Path("")→CWD）；
- C9 base_url() 取现役真源（core.lib.port_config.gateway_base_url ⇒ 5102），PA_VERIFY_BASE 可覆。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: legacy v5 之静态排除名（顶层段 · 承旧 _SCAN_SKIP_TOP）
LEGACY_SKIP_TOP = (".obsidian", "Templates", "_垃圾箱", "_冷区")

#: legacy 验器默认端口（现役真源应解析为 5102）
LEGACY_BASE_PORT = 5102

#: C7 语义反例（PD T106 A1–A3）：顶层 vs 任一段 · 静态 vs 配置 · 反斜杠归一
LEGACY_SCAN_CASES = (
    ("_冷区/x.md", True),
    ("_垃圾箱/P/d.md", True),
    (".obsidian/x.md", True),
    ("Templates/t.md", True),
    ("工作区/SOPs/SOPs/a.md", False),
    ("dsh/a.md", False),
    ("工作区/_冷区/x.md", False),
    ("Templates" + chr(92) + "t.md", True),
)


def _pi():
    u"""惰引现役扫描模块（只读；⛔ 顶层 import ⇒ 免产品导入期副作用外溢）。"""
    from core.gateway import precision_inject as pi

    return pi


def legacy_scan_excluded(rel):
    u"""legacy 口径：反斜杠归一后取**顶层段**，静态四名命中即排除。"""
    top = str(rel).replace(chr(92), "/").split("/", 1)[0]
    return top in LEGACY_SKIP_TOP


def scan_excluded_cases():
    u"""C7 之逐一反例 ⇒ {rel: {expected, actual, ok}}（⛔ 现役 _rel_excluded 原样）。"""
    out = {}
    for rel, expected in LEGACY_SCAN_CASES:
        actual = bool(legacy_scan_excluded(rel))
        out[rel] = {"expected": bool(expected), "actual": actual,
                    "ok": actual == bool(expected)}
    return out


def all_scan_cases_ok():
    return all(x["ok"] for x in scan_excluded_cases().values())


def vault_root_or_none():
    u"""现役 vault 根 ∨ None（空串／"." ⇒ None；⛔ Path("")→CWD 之旧病）。"""
    s = str(_pi()._vault_path() or "").strip()
    if not s or s == ".":
        return None
    return Path(s)


def sops_dir():
    u"""现役 sops_dir（同件同键；缺省 SOPs）。"""
    return str((_pi()._obsidian_cfg() or {}).get("sops_dir") or "SOPs")


def base_url():
    u"""legacy C9/C3/C4 之基址：env PA_VERIFY_BASE > 现役真源（5102）> 5102。"""
    env = (os.environ.get("PA_VERIFY_BASE") or "").strip()
    if env:
        return env.rstrip("/")
    try:
        from core.lib.port_config import gateway_base_url

        return gateway_base_url()
    except Exception:
        return "http://127.0.0.1:%d" % LEGACY_BASE_PORT


def legacy_walk(root=None, skip=None, manifest=None):
    u"""跑**本层自含** legacy 容错 walker（只读）；root 缺 ⇒ 现役 vault 根。

    T112：⛔ 再借现役 os.walk(onerror)（不保已读）之面；本层实现 scandir 保已读 ＋ 错误入册
    ＋ 可选清单补面，C10 因之可**真 PASS**（⛔ 空表假绿）。
    """
    from legacy_verify.adapters import legacy_walker as W

    base = Path(root) if root is not None else vault_root_or_none()
    if base is None:
        return {"walker": W.WALKER_ID, "state": "unset", "root": None,
                "files": [], "file_count": 0, "supplemented": [],
                "supplemented_count": 0, "errors": [], "error_count": 0,
                "manifest": str(manifest or ""), "manifest_note": "vault 未接"}
    return W.walk(base, skip=skip if skip is not None else LEGACY_SKIP_TOP,
                  manifest=manifest)


def legacy_walk_errors():
    u"""上一次 legacy_walk 之错误册 ⇒ **list**（C10 之留痕面；空 list ＝ 无错）。"""
    from legacy_verify.adapters import legacy_walker as W

    return W.last_walk_errors()


def knowledge_files_ok():
    u"""C5：_KNOWLEDGE_FILES 逐键解析（兼容 schema：sandbox_rel ∨ rel）。

    优先现役 _resolve_knowledge_path(key)；无 / 失败 ⇒ 以 rel 或 sandbox_rel 对 vault 根拼。
    ⛔ 直接索引 info["rel"]（旧码 KeyError 之源）。
    """
    pi = _pi()
    root = vault_root_or_none()
    out = {}
    for key, info in (getattr(pi, "_KNOWLEDGE_FILES", {}) or {}).items():
        info = info if isinstance(info, dict) else {}
        path = None
        err = ""
        fn = getattr(pi, "_resolve_knowledge_path", None)
        if callable(fn):
            try:
                path = fn(key)
            except Exception as exc:                      # noqa: BLE001
                err = type(exc).__name__
        if path is None:
            rel = info.get("rel") or info.get("sandbox_rel")
            if root is not None and rel:
                path = root / str(rel)
        p = Path(str(path)) if path is not None else None
        out[key] = {
            "schema": sorted(str(k) for k in info.keys()),
            "path": str(p) if p is not None else "",
            "exists": bool(p is not None and p.is_file()),
            "resolve_error": err,
        }
    return out


def all_knowledge_ok():
    got = knowledge_files_ok()
    return bool(got) and all(x["exists"] for x in got.values())


__all__ = [
    "LEGACY_SKIP_TOP",
    "LEGACY_BASE_PORT",
    "LEGACY_SCAN_CASES",
    "legacy_scan_excluded",
    "scan_excluded_cases",
    "all_scan_cases_ok",
    "vault_root_or_none",
    "sops_dir",
    "base_url",
    "legacy_walk",
    "legacy_walk_errors",
    "knowledge_files_ok",
    "all_knowledge_ok",
]
