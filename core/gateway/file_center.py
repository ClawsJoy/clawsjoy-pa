# -*- coding: utf-8 -*-
"""文件中心路由 handler — 从 agent_gateway_enhanced.py 归位（2026-09-12）。

薄包装路由 → routes/files.py。这里放重逻辑：文件扫描 / 预览 / diff / 下载 / 截图 / 资料库保存。
"""

import datetime
import hashlib
import time
from pathlib import Path
from urllib.parse import quote

from flask import jsonify, request

import core.lib.gateway_helpers as _gh


def _scan_session_files(sandbox_base, ext=None, type_=None, limit=100, user_id="", session_id=""):
    """扫描 session 沙箱目录的任务产出文件(文件中心数据源)。

    范围: 沙箱 clawsjoy_dev/ 下全部文件
    排除: 隐藏文件/目录(.git/ 等)、goals/(目标记录)、data/v8/(内部数据)、内部状态文件
    排序: modified_at 倒序(最新在前); 上限 limit(默认 100)
    过滤: ?ext=.md,.txt(逗号分隔) / ?type=report|screenshot
    返回: [{id, name, path, size, modified_at, preview_url}]
    """
    _sb = Path(sandbox_base)
    if not _sb.exists():
        return []
    _exts = None
    if ext:
        _exts = {e.strip().lstrip(".").lower() for e in str(ext).split(",") if e.strip()}
    _type = (type_ or "").lower()
    _out = []
    try:
        for _p in _sb.rglob("*"):
            if not _p.is_file():
                continue
            try:
                _rel = _p.relative_to(_sb)
            except ValueError:
                continue
            _parts = _rel.parts
            # 排除隐藏/.git + 内部目录 + 内部状态文件
            if any(_seg.startswith(".") for _seg in _parts):
                continue
            if "goals" in _parts:
                continue
            if len(_parts) >= 2 and _parts[0] == "data" and _parts[1] in ("v8", "diffs"):
                continue
            if _rel.name in (".agent_state.json", ".task_state.json", ".progress_checkpoint.json"):
                continue
            _suffix = _p.suffix.lower().lstrip(".")
            # ext 过滤
            if _exts and _suffix not in _exts:
                continue
            # type 过滤
            if _type == "screenshot":
                _n = _rel.name.lower()
                if not (_n.startswith("screenshot") or "playwright" in _n or _suffix in ("png", "jpg", "jpeg", "webp")):
                    continue
            elif _type == "report":
                if _suffix not in ("md", "txt", "html", "htm"):
                    continue
            try:
                _st = _p.stat()
            except OSError:
                continue
            _rel_str = str(_rel)
            _fid = hashlib.md5(_rel_str.encode("utf-8")).hexdigest()[:16]
            _out.append(
                {
                    "id": _fid,
                    "name": _rel.name,
                    "path": _rel_str,
                    "size": _st.st_size,
                    "modified_at": _st.st_mtime,
                    "preview_url": f"/v9/files/content?user_id={user_id}&session_id={session_id}&id={_fid}",
                }
            )
    except Exception:
        pass
    _out.sort(key=lambda f: f["modified_at"], reverse=True)
    return _out[: limit if limit and limit > 0 else 100]


def v9_files_list_handler():
    _q = request.args or {}
    _uid = _q.get("user_id", "default")
    _sid = _q.get("session_id", "")
    if not _sid:
        return jsonify({"success": False, "error": "session_id 必填"})
    try:
        _files = _scan_session_files(
            _gh._get_sandbox_base(_uid, _sid),
            ext=_q.get("ext"),
            type_=_q.get("type"),
            limit=int(_q.get("limit") or 100),
            user_id=_uid,
            session_id=_sid,
        )
        return jsonify({"success": True, "files": _files})
    except Exception as _f_err:
        return jsonify({"success": False, "error": str(_f_err)[:300]})


def v9_files_content_handler():
    _q = request.args or {}
    _uid = _q.get("user_id", "default")
    _sid = _q.get("session_id", "")
    _fid = _q.get("id", "")
    if not _sid or not _fid:
        return jsonify({"success": False, "error": "session_id 与 id 必填"})
    try:
        _sb = Path(_gh._get_sandbox_base(_uid, _sid))
        if not _sb.exists():
            return jsonify({"success": False, "error": "沙箱不存在"})
        for _p in _sb.rglob("*"):
            if not _p.is_file():
                continue
            try:
                _rel = _p.relative_to(_sb)
            except ValueError:
                continue
            if hashlib.md5(str(_rel).encode("utf-8")).hexdigest()[:16] == _fid:
                _data = _p.read_bytes()[: 100 * 1024]
                return _data, 200, {"Content-Type": "text/plain; charset=utf-8", "Access-Control-Allow-Origin": "*"}
        return jsonify({"success": False, "error": "文件不存在"})
    except Exception as _fc_err:
        return jsonify({"success": False, "error": str(_fc_err)[:300]})


def v9_files_diffs_handler():
    _q = request.args or {}
    _uid = _q.get("user_id", "default")
    _sid = _q.get("session_id", "")
    _path = _q.get("path", "")
    if not _sid or not _path:
        return jsonify({"success": False, "error": "session_id 与 path 必填"})
    try:
        _sb = Path(_gh._get_sandbox_base(_uid, _sid))
        _bn = _path.split("/")[-1]
        _diff_dir = _sb / "data" / "diffs"
        _diffs = []
        if _diff_dir.exists():
            for _df in _diff_dir.glob(f"*_{_bn}.diff"):
                try:
                    _ts_str = "_".join(_df.name.split("_")[:2])
                    _ts = 0
                    try:
                        _ts = datetime.datetime.strptime(_ts_str, "%Y%m%d_%H%M%S").timestamp()
                    except ValueError:
                        pass
                    _diffs.append(
                        {
                            "ts": _ts,
                            "file": _bn,
                            "diff": _df.read_text(encoding="utf-8", errors="replace")[:20000],
                        }
                    )
                except Exception:
                    continue
        _diffs.sort(key=lambda d: d["ts"], reverse=True)
        return jsonify({"success": True, "diffs": _diffs})
    except Exception as _diff_err:
        return jsonify({"success": False, "error": str(_diff_err)[:300]})


def v9_files_download_handler():
    _q = request.args or {}
    _uid = _q.get("user_id", "default")
    _sid = _q.get("session_id", "")
    _fid = _q.get("id", "")
    if not _sid or not _fid:
        return jsonify({"success": False, "error": "session_id 与 id 必填"})
    try:
        _sb = Path(_gh._get_sandbox_base(_uid, _sid))
        for _p in _sb.rglob("*"):
            if not _p.is_file():
                continue
            try:
                _rel = _p.relative_to(_sb)
            except ValueError:
                continue
            if hashlib.md5(str(_rel).encode("utf-8")).hexdigest()[:16] == _fid:
                _data = _p.read_bytes()
                _fn = quote(_rel.name)
                return (
                    _data,
                    200,
                    {
                        "Content-Type": "application/octet-stream",
                        "Content-Disposition": f"attachment; filename*=UTF-8''{_fn}",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
        return jsonify({"success": False, "error": "文件不存在"})
    except Exception as _fd_err:
        return jsonify({"success": False, "error": str(_fd_err)[:300]})


def v9_media_handler():
    import os as _om

    _q = request.args or {}
    _uid = _q.get("user_id", "default")
    _sid = _q.get("session_id", "")
    _rel = _q.get("path", "")
    if not _sid or not _rel:
        return jsonify({"success": False, "error": "session_id 与 path 必填"})
    try:
        _sb = Path(_gh._get_sandbox_base(_uid, _sid)).resolve()
        if not _sb.exists():
            return jsonify({"success": False, "error": "沙箱不存在"})
        _target = (_sb / _rel).resolve()
        # 防穿越: 目标必须位于沙箱内
        if _target != _sb and not str(_target).startswith(str(_sb) + _om.sep):
            return jsonify({"success": False, "error": "非法路径"})
        if not _target.is_file():
            return jsonify({"success": False, "error": "文件不存在"})
        _suffix = _target.suffix.lower()
        _ctypes = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        _data = _target.read_bytes()
        return (
            _data,
            200,
            {
                "Content-Type": _ctypes.get(_suffix, "application/octet-stream"),
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except Exception as _m_err:
        return jsonify({"success": False, "error": str(_m_err)[:300]})


def v9_files_save_handler():
    try:
        _b = request.get_json(silent=True) or {}
    except Exception:
        _b = {}
    _uid = _b.get("user_id", "default")
    _sid = _b.get("session_id", "")
    _fname = str(_b.get("filename") or "").strip()
    _content = str(_b.get("content") or "")
    if not _sid:
        return jsonify({"success": False, "error": "session_id 必填"})
    if not _fname:
        return jsonify({"success": False, "error": "filename 必填"})
    _safe = Path(_fname).name  # 只取 basename(防 ../)
    if not _safe:
        return jsonify({"success": False, "error": "非法文件名"})
    if not _safe.lower().endswith(".md"):
        _safe = _safe.rsplit(".", 1)[0] if "." in _safe else _safe
        _safe += ".md"
    if len(_content) > 200 * 1024:
        return jsonify({"success": False, "error": "内容超限(≤200KB)"})
    try:
        _reports_dir = Path(str(_gh._get_sandbox_base(_uid, _sid))) / "data" / "reports"
        _reports_dir.mkdir(parents=True, exist_ok=True)
        _target = _reports_dir / _safe
        _target.write_text(_content, encoding="utf-8")
        print(f"[REPORTS] 已保存: {_safe} ({len(_content)} 字符)")
        return jsonify(
            {
                "success": True,
                "file": {
                    "id": f"save-{time.time():.0f}",
                    "name": _safe,
                    "path": f"data/reports/{_safe}",
                    "size": len(_content.encode("utf-8")),
                    "modified_at": time.time(),
                },
            }
        )
    except Exception as _s_err:
        return jsonify({"success": False, "error": str(_s_err)[:300]})
