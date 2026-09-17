# -*- coding: utf-8 -*-
"""Video Studio API —— 视频工作室 Blueprint（/api/video-studio）。

重建说明
--------
!! 本文件是【重建版】，不是原文件 !! 请勿把它当作原 WSL 仓库的 video_studio_api.py。
本模块在原 WSL 仓库中存在（见 CHANGELOG「已拆分注册 Blueprint：
video_studio_bp（web/api/video_studio_api.py）」），但它既未被 git 跟踪，
也没有随 Windows 副本一起带过来 —— 整个 web/api/ 目录缺失。

缺失后果：agent_gateway_enhanced.py:240 的
`from web.api.video_studio_api import video_studio_bp` 直接 ImportError，
网关无法启动，且 tests/integration/test_gateway_routes.py 等模块无法收集。

本次按以下权威来源重建（接口字段、状态码、错误文案均对齐）：
  - docs/api_doc.md（Video Studio API 文档）
  - tests/integration/test_video_api_integration.py
  - tests/integration/test_timeline_export_integration.py
  - tests/integration/test_download_error_integration.py

原文件丢失证据（2026-09-17 核验）
  - `git ls-files 'web/api/*'` 输出为空 ⇒ 原文件从未被 git 跟踪；
    在 pristine HEAD 工作树里同样为空（web/api/ 整体为 untracked 目录）。
  - CHANGELOG.md:77 记载该文件曾存在：
    "video_studio_bp（web/api/video_studio_api.py）"。
  - 唯一可恢复源：D:\\WSL\\Ubuntu\\ext4.vhdx（139,610,554,368 bytes）。
    本重建版**未**从该镜像捞取，如需原文件须挂载该 vhdx 另行提取。
  - 台账：Obsidian codex 专栏 X-01（防"重建版被当原文件"）。

状态保存在进程内存中（默认项目 proj-001，进程重启后回到初始状态）。
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

video_studio_bp = Blueprint("video_studio", __name__, url_prefix="/api/video-studio")

# web/api/video_studio_api.py -> web/api -> web -> 仓库根
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = _PROJECT_ROOT / "data" / "videos"
EXPORT_DIR = _PROJECT_ROOT / "data" / "exports"

DEFAULT_PROJECT_ID = "proj-001"
DEFAULT_PROJECT_NAME = "默认项目"
DEFAULT_PROJECT_DURATION = 60.0
DEFAULT_FILENAME = "untitled.mp4"
DEFAULT_RESOLUTION = "1920x1080"
DEFAULT_BITRATE = "5M"
DEFAULT_FPS = 30
ALLOWED_FORMATS = ("mp4", "webm")
VALID_TRACK_TYPES = ("video", "audio", "text", "effect")
TRACK_TYPE_GROUP = {"video": "video", "audio": "audio", "text": "video", "effect": "video"}

_RESOLUTION_RE = re.compile(r"^\d{2,5}x\d{2,5}$")

_lock = threading.RLock()
_projects = {}
_tasks = {}
_counters = {"video": 0, "task": 0, "project": 0}


def _next_id(kind):
    """单调自增 ID 计数器（vid-1 / task-1 / proj-1001 ...）。"""
    with _lock:
        _counters[kind] += 1
        return _counters[kind]


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _as_str(value, default=""):
    if value is None:
        return default
    return str(value)


def _safe_filename(name):
    """只取基名，避免 ../ 或绝对路径写穿 VIDEO_DIR。"""
    base = Path(_as_str(name)).name
    return base or DEFAULT_FILENAME


def _default_timeline(duration=0.0):
    """默认时间线：一条视频轨 + 一条音频轨（与 docs/api_doc.md 示例一致）。"""
    return {
        "duration": float(duration),
        "tracks": [
            {"id": "t1", "type": "video", "clips": []},
            {"id": "t2", "type": "audio", "clips": []},
        ],
    }


def _normalize_timeline(timeline):
    """把外部传入的时间线规整为 {duration, tracks[]} 结构。"""
    if not isinstance(timeline, dict):
        return _default_timeline()
    tracks = []
    for index, track in enumerate(timeline.get("tracks") or []):
        if not isinstance(track, dict):
            continue
        track_type = track.get("type") or "video"
        if track_type not in VALID_TRACK_TYPES:
            track_type = "video"
        clips = []
        for clip in track.get("clips") or []:
            if not isinstance(clip, dict):
                continue
            try:
                start = float(clip.get("start") or 0.0)
            except (TypeError, ValueError):
                start = 0.0
            try:
                end = float(clip.get("end") or 0.0)
            except (TypeError, ValueError):
                end = 0.0
            clips.append(
                {
                    "id": _as_str(clip.get("id")) or "clip-%d" % (len(clips) + 1),
                    "video_id": _as_str(clip.get("video_id")),
                    "file_path": _as_str(clip.get("file_path")),
                    "start": start,
                    "end": end,
                }
            )
        tracks.append(
            {
                "id": _as_str(track.get("id")) or "t%d" % (index + 1),
                "type": track_type,
                "clips": clips,
            }
        )
    try:
        duration = float(timeline.get("duration"))
    except (TypeError, ValueError):
        duration = 0.0
    return {"duration": duration, "tracks": tracks}


def _project_view(project):
    """项目对外视图（不含完整时间线，避免列表接口过大）。"""
    timeline = project["timeline"]
    return {
        "id": project["id"],
        "name": project["name"],
        "duration": timeline["duration"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
        "tracks": len(timeline["tracks"]),
        "clips": sum(len(track["clips"]) for track in timeline["tracks"]),
    }


def _append_clip(project, video_id, file_path, duration, title):
    """把导入的视频追加到项目的第一条视频轨。"""
    timeline = project["timeline"]
    track = next((t for t in timeline["tracks"] if t["type"] == "video"), None)
    if track is None:
        track = {"id": "t%d" % (len(timeline["tracks"]) + 1), "type": "video", "clips": []}
        timeline["tracks"].append(track)
    try:
        end = float(duration)
    except (TypeError, ValueError):
        end = 0.0
    track["clips"].append(
        {
            "id": "clip-%d" % (len(track["clips"]) + 1),
            "video_id": video_id,
            "file_path": file_path,
            "start": 0.0,
            "end": end,
            "name": title,
        }
    )
    if end > timeline["duration"]:
        timeline["duration"] = end
    project["updated_at"] = _now()


def _seed_default_project():
    """预置默认项目：/projects 至少返回 1 条，且 /projects/proj-001 可取。"""
    _projects[DEFAULT_PROJECT_ID] = {
        "id": DEFAULT_PROJECT_ID,
        "name": DEFAULT_PROJECT_NAME,
        "created_at": _now(),
        "updated_at": _now(),
        "timeline": _default_timeline(DEFAULT_PROJECT_DURATION),
    }


_seed_default_project()


# ========== 导入 ==========

@video_studio_bp.route("/import", methods=["POST"])
def import_video():
    """导入视频（multipart 文件上传，或 JSON 元数据注册）。"""
    uploaded = request.files.get("file")
    payload = request.get_json(silent=True) or {}

    if uploaded is not None:
        filename = _safe_filename(uploaded.filename)
        project_id = _as_str(request.form.get("project_id")).strip()
        title = _as_str(request.form.get("title")).strip() or filename
        duration = _as_str(request.form.get("duration")).strip()
        tags = _as_str(request.form.get("tags")).strip()
        file_path = ""
    else:
        if not payload:
            return jsonify({"ok": False, "error": "请求体为空或格式错误"}), 400
        filename = DEFAULT_FILENAME
        project_id = _as_str(payload.get("project_id")).strip()
        title = _as_str(payload.get("title")).strip() or filename
        duration = _as_str(payload.get("duration")).strip()
        tags = _as_str(payload.get("tags")).strip()
        file_path = _as_str(payload.get("file_path")).strip()

    video_id = "vid-%d" % _next_id("video")

    if uploaded is not None:
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        saved = VIDEO_DIR / ("%s_%s" % (video_id, filename))
        uploaded.save(str(saved))
        saved_path = str(saved.relative_to(_PROJECT_ROOT)).replace(os.sep, "/")
        file_size = saved.stat().st_size
    else:
        saved_path = file_path
        file_size = 0
        if file_path:
            candidate = Path(file_path)
            if candidate.exists():
                try:
                    file_size = candidate.stat().st_size
                except OSError:
                    file_size = 0

    metadata = {
        "project_id": project_id,
        "title": title,
        "duration": duration,
        "tags": tags,
    }

    project = _projects.get(project_id) if project_id else None
    if project is not None:
        _append_clip(project, video_id, saved_path, duration, title)

    return jsonify(
        {
            "ok": True,
            "video_id": video_id,
            "filename": filename,
            "file_size": file_size,
            "saved_path": saved_path,
            "metadata": metadata,
            "project_id": project_id,
        }
    )


# ========== 项目 ==========

@video_studio_bp.route("/projects", methods=["GET"])
def list_projects():
    with _lock:
        projects = [_project_view(project) for project in _projects.values()]
    return jsonify({"ok": True, "projects": projects})


@video_studio_bp.route("/projects", methods=["POST"])
def create_project():
    payload = request.get_json(silent=True) or {}
    name = _as_str(payload.get("name")).strip()
    if not name:
        return jsonify({"ok": False, "error": "缺少必填参数: name"}), 400
    try:
        duration = float(payload.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0

    project_id = "proj-%d" % (1000 + _next_id("project"))
    project = {
        "id": project_id,
        "name": name,
        "created_at": _now(),
        "updated_at": _now(),
        "timeline": _default_timeline(duration),
    }
    with _lock:
        _projects[project_id] = project
    return jsonify({"ok": True, "project": _project_view(project)}), 201


@video_studio_bp.route("/projects/<project_id>", methods=["GET"])
def get_project(project_id):
    project = _projects.get(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "项目不存在"}), 404
    return jsonify({"ok": True, "project": _project_view(project)})


@video_studio_bp.route("/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    with _lock:
        project = _projects.pop(project_id, None)
    if project is None:
        return jsonify({"ok": False, "error": "项目不存在"}), 404
    return jsonify({"ok": True, "project_id": project_id})


# ========== 时间线 ==========

@video_studio_bp.route("/timeline/<project_id>", methods=["GET"])
def get_timeline(project_id):
    project = _projects.get(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "项目不存在"}), 404
    return jsonify({"ok": True, "timeline": project["timeline"]})


@video_studio_bp.route("/timeline/<project_id>", methods=["PUT"])
def update_timeline(project_id):
    project = _projects.get(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "项目不存在"}), 404
    payload = request.get_json(silent=True) or {}
    timeline = _normalize_timeline(payload.get("timeline"))
    project["timeline"] = timeline
    project["updated_at"] = _now()
    return jsonify({"ok": True, "timeline": timeline})


# ========== 导出 / 下载 ==========

def _encode_args(fmt, resolution, bitrate, fps):
    scale = resolution.replace("x", ":")
    if fmt == "webm":
        args = ["-c:v", "libvpx-vp9", "-b:v", bitrate]
    else:
        args = ["-c:v", "libx264", "-b:v", bitrate, "-pix_fmt", "yuv420p"]
    return ["-vf", "scale=%s" % scale] + args + ["-r", str(fps)]


def _build_export_command(project, output_path, fmt, resolution, bitrate, fps):
    """按项目时间线拼 ffmpeg 命令；无素材时渲染一段纯色占位片段。"""
    clips = [
        clip["file_path"]
        for track in project["timeline"]["tracks"]
        if TRACK_TYPE_GROUP.get(track["type"]) == "video"
        for clip in track["clips"]
        if clip.get("file_path")
    ]
    base = ["ffmpeg", "-y"]
    if clips:
        list_file = EXPORT_DIR / ("%s_concat.txt" % project["id"])
        list_file.write_text(
            "".join("file '%s'\n" % path.replace("'", "'\\''") for path in clips),
            encoding="utf-8",
        )
        inputs = ["-f", "concat", "-safe", "0", "-i", str(list_file)]
    else:
        duration = max(float(project["timeline"].get("duration") or 0.0), 1.0)
        inputs = ["-f", "lavfi", "-i", "color=c=black:s=%s:d=%s" % (resolution, duration)]
    return base + inputs + _encode_args(fmt, resolution, bitrate, fps) + [str(output_path)]


@video_studio_bp.route("/export", methods=["POST"])
def export_video():
    payload = request.get_json(silent=True) or {}

    project_id = _as_str(payload.get("project_id")).strip()
    if not project_id:
        return jsonify({"ok": False, "error": "缺少必填参数: project_id"}), 400

    project = _projects.get(project_id)
    if project is None:
        return jsonify({"ok": False, "error": "项目不存在"}), 404

    fmt = (_as_str(payload.get("format")).strip() or "mp4").lower()
    if fmt not in ALLOWED_FORMATS:
        return jsonify({"ok": False, "error": "不支持的格式: %s（仅支持 mp4 / webm）" % fmt}), 400

    resolution = _as_str(payload.get("resolution")).strip() or DEFAULT_RESOLUTION
    if not _RESOLUTION_RE.match(resolution):
        return jsonify(
            {"ok": False, "error": "无效的分辨率: %s（应为 宽x高，如 1920x1080）" % resolution}
        ), 400

    bitrate = _as_str(payload.get("bitrate")).strip() or DEFAULT_BITRATE
    try:
        fps = int(payload.get("fps") or DEFAULT_FPS)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "无效的帧率: %s" % payload.get("fps")}), 400

    task_id = "task-%d" % _next_id("task")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / ("%s.%s" % (project_id, fmt))

    status = "failed"
    error = None
    try:
        command = _build_export_command(project, output_path, fmt, resolution, bitrate, fps)
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        returncode = getattr(proc, "returncode", 1)
        stderr = _as_str(getattr(proc, "stderr", "")).strip()
        if returncode == 0 and Path(output_path).exists():
            status = "completed"
        else:
            error = stderr or "ffmpeg 渲染失败(退出码 %s)" % returncode
    except FileNotFoundError:
        error = "未找到 ffmpeg 可执行文件，请安装 ffmpeg 并加入 PATH"
    except Exception as exc:  # noqa: BLE001 - 兜底为可读错误，避免 500 堆栈外泄
        error = "导出失败: %s" % exc

    _tasks[task_id] = {
        "task_id": task_id,
        "project_id": project_id,
        "status": status,
        "output_path": str(output_path),
        "created_at": _now(),
        "error": error,
    }

    if status != "completed":
        return jsonify(
            {"ok": False, "task_id": task_id, "status": status, "error": error}
        ), 500

    return jsonify(
        {
            "ok": True,
            "task_id": task_id,
            "status": status,
            "message": "导出任务已完成",
            "output_path": str(output_path),
        }
    )


@video_studio_bp.route("/download/<task_id>", methods=["GET"])
def download_export(task_id):
    task = _tasks.get(task_id)
    if task is None:
        return jsonify({"ok": False, "error": "导出任务不存在"}), 404
    path = Path(_as_str(task.get("output_path")))
    if not path.name or not path.exists():
        return jsonify({"ok": False, "error": "导出文件不存在或尚未生成"}), 404
    return send_file(str(path), as_attachment=True, download_name=path.name)
