# -*- coding: utf-8 -*-
"""PA 屏幕录播 P0：本地视频 → 转写＋关键帧 → note。"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from core.pa import notes as N
from core.pa import voice as V

MAX_SCREEN = 500 * 1024 * 1024
KEYFRAME_EVERY = 10.0
MAX_KEYFRAMES = 12


def _screen_path(data_dir, suffix):
    root = N.workspace_root(data_dir) / "attachments" / "screen" / datetime.now().strftime("%Y%m%d")
    root.mkdir(parents=True, exist_ok=True)
    suffix = (suffix or ".webm").lower()
    if suffix not in (".webm", ".mkv", ".mp4", ".mov"):
        suffix = ".webm"
    return root / (uuid.uuid4().hex[:12] + suffix)


def keyframes(video_path, out_dir, every=KEYFRAME_EVERY, max_n=MAX_KEYFRAMES):
    out = []
    try:
        import av
        if not getattr(av, "_pa_open_patch", False):
            _orig = av.open

            def _open(*a, **kw):
                kw.pop("metadata_errors", None)
                return _orig(*a, **kw)
            av.open = _open
            av._pa_open_patch = True
        c = av.open(str(video_path))
        try:
            st = c.streams.video[0]
            nxt = 0.0
            idx = 0
            for fr in c.decode(st):
                t = float(fr.time or 0)
                if t + 1e-6 < nxt:
                    continue
                p = out_dir / ("%02d_%05.1fs.jpg" % (idx, t))
                fr.to_image().save(p, "JPEG", quality=82)
                out.append({"at": round(t, 1), "path": str(p),
                            "name": p.name})
                idx += 1
                nxt = t + every
                if idx >= max_n:
                    break
        finally:
            c.close()
    except Exception:
        pass
    return out




def _ffmpeg():
    for c in (os.getenv("PA_FFMPEG", "").strip(), shutil.which("ffmpeg") or "",
              str(Path(__file__).resolve().parents[2] / "tools" / "ffmpeg.exe")):
        try:
            if c and Path(c).exists():
                return str(c)
        except Exception:
            pass
    return ""


def _ffprobe():
    f = _ffmpeg()
    if not f:
        return ""
    for name in ("ffprobe.exe", "ffprobe"):
        q = Path(f).with_name(name)
        if q.exists():
            return str(q)
    return shutil.which("ffprobe") or ""


def _probe_duration(path):
    try:
        fp = _ffprobe()
        if fp:
            r = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=nw=1", str(path)], capture_output=True, text=True, timeout=20)
            for line in (r.stdout or "").splitlines():
                if line.startswith("duration="):
                    return round(float(line.split("=", 1)[1]), 2)
    except Exception:
        pass
    try:
        import av
        c = av.open(str(path))
        try:
            return round(float(c.duration or 0) / float(av.time_base), 2)
        finally:
            c.close()
    except Exception:
        return 0


def _fix_webm(path):
    """MediaRecorder WebM 常缺 duration/cues：ffmpeg 无损重封装，便于拖动。"""
    ff = _ffmpeg()
    if not ff:
        return False
    tmp = Path(str(path) + ".fixed.webm")
    try:
        r = subprocess.run([ff, "-y", "-v", "error", "-i", str(path), "-c", "copy", "-map", "0", str(tmp)],
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            os.replace(str(tmp), str(path))
            return True
    except Exception:
        pass
    try:
        if tmp.exists():
            tmp.unlink()
    except Exception:
        pass
    return False

def screen_note(data_dir=None, filename="screen.webm", video_bytes=None, language="zh"):
    raw = video_bytes or b""
    if not raw:
        raise RuntimeError("空视频")
    if len(raw) > MAX_SCREEN:
        raise RuntimeError("视频过大（>500MB）")
    suffix = Path(filename or "screen.webm").suffix or ".webm"
    p = _screen_path(data_dir, suffix)
    p.write_bytes(raw)
    _fix_webm(p)
    dur = _probe_duration(p)
    tr = {"text": "", "lines": [], "language": "", "duration": 0}
    try:
        tr = V.transcribe_audio(p, language=language)
    except Exception:
        pass
    kdir = p.parent / (p.stem + "_frames")
    kdir.mkdir(parents=True, exist_ok=True)
    frames = keyframes(p, kdir)
    now = datetime.now()
    title = "录屏笔记 " + now.strftime("%m-%d %H:%M")
    text = (tr.get("text") or "").strip()
    base = N.workspace_root(data_dir) / "attachments" / "screen"
    vrel = p.relative_to(base).as_posix()
    body = []
    if text:
        body.append(text[:300])
        body.append("")
    body.append("时长：%s" % ("%d:%02d" % (int(dur // 60), int(dur % 60)) if dur else "未取到"))
    body.append("")
    body.append("转写：")
    body += (tr.get("lines") or ["（无转写）"])
    body.append("")
    body.append("关键帧：")
    for f in frames:
        rel = Path(f["path"]).relative_to(base).as_posix()
        body.append("![%s](attachments/screen/%s)" % (f["name"], rel))
    body.append("")
    body.append("[录屏](attachments/screen/%s)" % vrel)
    note = N.create(title, "\n".join(body), ["录屏"], data_dir=data_dir,
                    source="screen", source_path=str(p))
    return {"note": note, "transcript": tr, "frames": frames,
            "video": str(p), "duration": round(float(tr.get("duration") or 0), 2)}
