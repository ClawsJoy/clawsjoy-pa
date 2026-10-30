# -*- coding: utf-8 -*-
"""PA 路由 · content_caliber 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 5 条路由）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import logging
import os
from pathlib import Path
from flask import jsonify, request
from core.lib.paths import path_forms, vault_root
logger = logging.getLogger(__name__)
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    _code_sha16, _core, _data_dir, err,
    ok,
)


KB_STATUS_MIRRORED = "已镜像"


KB_STATUS_STALE = "过期"


KB_STATUS_MISSING = "缺失"


KB_STATUS_UNMIRRORED = "未镜像"


KB_STATUS_UNKNOWN = "未知"


KB_STATUSES = (KB_STATUS_MIRRORED, KB_STATUS_STALE, KB_STATUS_MISSING, KB_STATUS_UNMIRRORED, KB_STATUS_UNKNOWN)


KB_MAPPING_DEFAULT_SCOPE = "收件箱"


KB_FINGERPRINT = "sha256_16"


KB_FINGERPRINT_MAX_BYTES = 32 * 1024 * 1024


def _kb_fingerprint(path, limit=KB_FINGERPRINT_MAX_BYTES):
    """内容指纹（验收-A）：sha256 前 16 位。取不到 / 超限 ⇒ None（判「未知」，不猜）。"""
    import hashlib

    h = hashlib.sha256()
    n = 0
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                n += len(b)
                if n > limit:
                    return None
                h.update(b)
    except Exception:
        return None
    return h.hexdigest()[:16]


def _kb_safe_rel(scope):
    """scope 必须是 vault 内的**相对**子路径（拒绝绝对路径 / .. 穿越 / 空字节）。"""
    s = str(scope or "").strip().replace(chr(92), "/").strip("/")
    if chr(0) in s:
        raise ValueError("scope 含非法字符")
    parts = [p for p in s.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError("scope 不允许 .. 穿越: %r" % scope)
    return "/".join(parts)


def build_kb_mapping(*, kb_root, sandbox_root, scope=KB_MAPPING_DEFAULT_SCOPE, limit=100, mirror_manifest=None):
    """知识库 ↔ 沙箱映射（批176 副指标 A）。**只读**：不写知识库、不写沙箱、不改 mtime。

    主语 = 知识库：kb_path（相对 kb_root）→ sandbox_path（沙箱内映射目标）→ status。
    状态判据（可机械复核）：
      已镜像 = 沙箱有副本，且大小相同、副本 mtime >= 源 mtime
      过期   = 沙箱有副本，但大小不同 或 副本更旧
      缺失   = 沙箱无副本，但**有镜像记录**（mirror_manifest；镜像功能落地后才可能出现）
      未镜像 = 沙箱无副本且无记录（默认态）
    """
    from datetime import datetime as _dt

    rel = _kb_safe_rel(scope)
    lim = max(1, min(int(limit or 100), 500))
    src_dir = (Path(kb_root) / rel) if rel else Path(kb_root)
    out = {
        "kb_root": str(kb_root),
        "kb_root_forms": list(path_forms(kb_root)),
        "sandbox_root": str(sandbox_root or ""),
        "scope": rel,
        "limit": lim,
        "readonly": True,
        "statuses": list(KB_STATUSES),
        "fingerprint": KB_FINGERPRINT,
        "rows": [],
        "counts": {s: 0 for s in KB_STATUSES},
        "total": 0,
        "truncated": False,
        "degraded": "",
        # 验收-B：判据跑没跑要能看出来 —— False 时上面那份 counts 不是读数（不适用 不等于 验过）
        "verified": True,
    }
    if not src_dir.is_dir():
        out["degraded"] = "知识库目录不存在: %s" % src_dir
        return out
    try:
        entries = [p for p in src_dir.iterdir() if p.is_file()]
    except Exception as _e_dir:
        out["degraded"] = "知识库目录不可读: %s" % _e_dir
        return out
    entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out["total"] = len(entries)
    if len(entries) > lim:
        entries = entries[:lim]
        out["truncated"] = True
    sb_root = Path(sandbox_root) if sandbox_root else None
    _sb_ok = bool(sb_root is not None and sb_root.is_dir())
    if not _sb_ok:
        # 验收-B：没有副本面 ⇒ 判「未知」（不适用），不许报「过期 0」（那是没验，不是 0）
        out["verified"] = False
        out["degraded"] = ("沙箱目录不存在（%s）⇒ 无法比对 ⇒ 状态判「%s」；"
                           "这份 counts 不是读数（不适用 不等于 验过）"
                           % (sandbox_root or "未提供", KB_STATUS_UNKNOWN))
    manifest = set()
    if isinstance(mirror_manifest, dict):
        _mf = mirror_manifest.get("files", mirror_manifest)
        manifest = set(_mf.keys()) if isinstance(_mf, dict) else set(map(str, _mf or []))
    elif isinstance(mirror_manifest, (list, tuple, set)):
        manifest = set(map(str, mirror_manifest))
    for p in entries:
        kb_rel = ("%s/%s" % (rel, p.name)) if rel else p.name
        sb_path = (sb_root / rel / p.name) if sb_root else (Path(rel) / p.name)
        _st = p.stat()
        row = {
            "name": p.name,
            "kb_path": kb_rel,
            "kb_abs": str(p),
            "sandbox_path": str(sb_path),
            "kb_bytes": _st.st_size,
            "kb_mtime": _dt.fromtimestamp(_st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "mirror_bytes": None,
            "mirror_mtime": None,
            "kb_sha16": None,
            "mirror_sha16": None,
            "status": KB_STATUS_UNMIRRORED,
            "reason": "沙箱无此副本",
        }
        if not _sb_ok:
            row["status"] = KB_STATUS_UNKNOWN
            row["reason"] = "沙箱目录不存在 ⇒ 无法比对（不适用；不是「未镜像」，也不是 0）"
        try:
            if not _sb_ok:
                pass
            elif sb_path.is_file():
                _sm = sb_path.stat()
                row["mirror_bytes"] = _sm.st_size
                row["mirror_mtime"] = _dt.fromtimestamp(_sm.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                # 验收-A：判据由「大小＋改时」改成「内容指纹 ＋ 非空」。
                # 为什么必须改：旧判据把这两种都判绿 ——
                #   ① 源与副本**都换成空件**（0 字节 == 0 字节）；② **等长换内容**（512 == 512）。
                #   ⇒ 这两条恰是「改名换姓的 exists-only」，比只看存在更难发现（PM 反例门实测 · 本线 P2 同一发现）。
                if _sm.st_size != row["kb_bytes"]:
                    row["status"] = KB_STATUS_STALE
                    row["reason"] = "大小不同（源 %d / 副本 %d 字节）" % (row["kb_bytes"], _sm.st_size)
                elif _sm.st_size == 0:
                    row["status"] = KB_STATUS_STALE
                    row["reason"] = "副本是空件（0 字节）⇒ 不算镜像（旧判据在此假绿）"
                else:
                    row["kb_sha16"] = _kb_fingerprint(p)
                    row["mirror_sha16"] = _kb_fingerprint(sb_path)
                    if row["kb_sha16"] is None or row["mirror_sha16"] is None:
                        row["status"] = KB_STATUS_UNKNOWN
                        row["reason"] = ("文件超指纹上限（%d MB）⇒ 无法比对（不适用）"
                                         % (KB_FINGERPRINT_MAX_BYTES // (1024 * 1024)))
                    elif row["kb_sha16"] != row["mirror_sha16"]:
                        row["status"] = KB_STATUS_STALE
                        row["reason"] = ("内容指纹不同（源 %s / 副本 %s）⇒ 字节数相同也不算镜像"
                                         % (row["kb_sha16"], row["mirror_sha16"]))
                    elif _sm.st_mtime < _st.st_mtime:
                        row["status"] = KB_STATUS_STALE
                        row["reason"] = ("指纹一致 %s 但副本比源旧（%s < %s）"
                                         % (row["kb_sha16"], row["mirror_mtime"], row["kb_mtime"]))
                    else:
                        row["status"] = KB_STATUS_MIRRORED
                        row["reason"] = "内容指纹一致 %s（非空 %d 字节）" % (row["kb_sha16"], row["kb_bytes"])
            elif kb_rel in manifest:
                row["status"] = KB_STATUS_MISSING
                row["reason"] = "有镜像记录但沙箱副本不存在"
        except Exception as _e_row:
            row["reason"] = "状态判定异常: %s" % _e_row
        out["counts"][row["status"]] = out["counts"].get(row["status"], 0) + 1
        out["rows"].append(row)
    return out


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
    @bp.route("/v9/pa/sediment", methods=["POST"])
    def pa_sediment():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        if not p.get("domain") or not p.get("value"):
            return err("sediment 需要 domain + value")
        r = pa.handle("profile_sediment", p)
        return ok(r) if r.get("ok") else err(r.get("error"))

    @bp.route("/v9/pa/caliber", methods=["GET"])
    def pa_caliber():
        from core.pa import caliber as C

        return ok({"cards": C.summary(), "counts": C.counts(), "source": C.source()}, 印=_code_sha16(pa_caliber, C))

    @bp.route("/v9/pa/caliber/change", methods=["POST"])
    def pa_caliber_change():
        """口径变更单（P7 · 2026-09-29）：把「改口径」从**改源码**变成**记一条**。
        必填 id/status/owner/why（缺一即拒，⛔ 不默认）；append-only 落
        data/v9/pa/caliber_changes.jsonl，**含改前值**；store 损坏 ⇒ 409（⛔ 不静默）。
        """
        from core.pa.caliber_store import CaliberStore, CaliberStoreCorrupt, CaliberStoreError

        try:
            p = request.json
        except Exception as _e_body:
            return err("caliber/change: body 不是合法 JSON（%s）" % type(_e_body).__name__)
        if not isinstance(p, dict):
            return err("caliber/change: body 需要 JSON 对象（拿到 %s）" % type(p).__name__)
        try:
            r = CaliberStore(_data_dir()).apply_change(p)
        except CaliberStoreError as _e:
            # PM 2026-09-30 裁「改」：域因原樣回，但**必帶路由定位**（與 caliber/check 同族）
            return err("caliber/change: %s" % _e)
        except CaliberStoreCorrupt as _c:
            return jsonify({"ok": False, "error": "caliber_store_corrupt",
                            "message": str(_c), "path": _c.path}), 409
        except Exception as _e:
            logger.error("caliber/change 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "caliber/change: 内部错误（已记日志）"}), 500
        try:
            _core(p.get("user_id")).events.append(
                "fact", "caliber_change", r.get("change") or {}, source="pa/caliber"
            )
        except Exception:
            pass
        return ok(r)

    @bp.route("/v9/pa/caliber/check", methods=["POST"])
    def pa_caliber_check():
        """口径预检（P7 · L2 门）。

        N2（2026-09-30 · PM 批）：**输入形状校到底** —— 错形状一律回可分辨的 ``err(...)``，
        ⛔ 不再 500 ＋ 内部文本（``AttributeError``），⛔ 也不再**假绿**。
        改前有三处会把「形状坏」说成「好读数」：
          · body 是 JSON 数组（``[]``）    ⇒ ``[] or {}`` 吞成 ``{}`` ⇒ ok ／ ``hit_count=0``
          · ``pages`` 是 falsy 非列表（``""``／``0``／``false``）⇒ ``or []`` 吞成 ``[]`` ⇒ ok ／ 0
          · 元素非对象 ／ ``data`` 非对象  ⇒ ``AttributeError`` ⇒ **500 ＋ 内部文本**
        （前两处与 437 假绿 ／ ``_jsonl_lines`` 的 ``0`` ／ 验收-B「过期 0」同族：**0 看起来像读数**。）

        判据（可机检）：① 任何形状错 ⇒ ``{"ok": false, ...}`` ＋ HTTP **400**（⛔ 非 500）；
        ② 错误文本**含出错位置**（``pages[1]``／``pages[0].data``／``body``）；③ 响应里 ⛔ 不得出现内部文本；
        ④ **正形状逐字不动**（与改前同答复）。
        ⚠ 本件只动**输入边界**：⛔ 不碰 ``C.check()`` 语义、⛔ 不碰 store、⛔ 不改返回字段。
        """
        from core.pa import caliber as C

        try:
            p = request.json
        except Exception as _e_body:
            return err("caliber/check: body 不是合法 JSON（%s）" % type(_e_body).__name__)
        if not isinstance(p, dict):
            return err("caliber/check: body 需要 JSON 对象（拿到 %s）" % type(p).__name__)
        pages = p.get("pages")
        if pages is None:
            pages = []
        if not isinstance(pages, list):
            return err("caliber/check: pages 需要列表（拿到 %s）" % type(pages).__name__)
        for i, pg in enumerate(pages):
            if not isinstance(pg, dict):
                return err("caliber/check: pages[%d] 不是对象（拿到 %s）" % (i, type(pg).__name__))
            data = pg.get("data")
            if data is not None and not isinstance(data, dict):
                return err("caliber/check: pages[%d].data 不是对象（拿到 %s）" % (i, type(data).__name__))
        hits = C.check(pages)
        return ok({"hits": hits, "hit_count": len(hits)})

    @bp.route("/v9/pa/kb_mapping", methods=["GET"])
    def pa_kb_mapping():
        """知识库 ↔ 沙箱映射（批176 副指标 A）：**只读**三列 + 状态枚举。

        只 stat，不写任何一侧（N1–N6 零噪音的前置约束）；镜像记录（若有）读沙箱 .kb_mirror.json。
        """
        import json as _json

        from core.lib.gateway_helpers import _get_sandbox_base as _gsb

        try:
            _uid = request.args.get("user_id")
            _sid = (request.args.get("session_id") or "").strip()
            _scope = request.args.get("scope") or KB_MAPPING_DEFAULT_SCOPE
            _limit = request.args.get("limit") or 100
            _vr = vault_root()   # ⚠ 可 None（未接）⇒ ⛔ str(None) 之假径
            _kb = os.getenv("PA_VAULT_DIR") or (str(_vr) if _vr is not None else "")
            _sb = ""
            _man = None
            if _sid:
                try:
                    _sb = str(_gsb(_uid or "default", _sid))
                except Exception:
                    _sb = ""
                _mf = (Path(_sb) / ".kb_mirror.json") if _sb else None
                if _mf is not None and _mf.is_file():
                    try:
                        _man = _json.loads(_mf.read_text(encoding="utf-8"))
                    except Exception:
                        _man = None
            return jsonify(
                {
                    "ok": True,
                    **build_kb_mapping(kb_root=_kb, sandbox_root=_sb, scope=_scope, limit=_limit, mirror_manifest=_man),
                    "印": _code_sha16(pa_kb_mapping, build_kb_mapping),
                }
            )
        except ValueError as _ve:
            return jsonify({"ok": False, "error": str(_ve)}), 400
        except Exception as _e:
            logger.error("kb_mapping 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "kb_mapping: 内部错误（已记日志）"}), 500

    return bp


register(bp)
