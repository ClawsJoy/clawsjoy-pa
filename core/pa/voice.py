# -*- coding: utf-8 -*-
"""PA 语音 P0：本地录音 → faster-whisper 转写 → note。

- 音频存 workspace/attachments/voice/；
- 默认本地 CPU int8，不上传；
- 模型：payload/models/whisper-small（可用 PA_WHISPER_DIR 覆盖）。
"""
from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from core.pa import notes as N

MAX_AUDIO = 100 * 1024 * 1024
_LOCK = threading.Lock()
_MODEL = None
_MODEL_ERR = ""


def _model_dir():
    env = os.getenv("PA_WHISPER_DIR", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "models" / "whisper-small"


def _model():
    global _MODEL, _MODEL_ERR
    if _MODEL is not None:
        return _MODEL
    if _MODEL_ERR:
        raise RuntimeError(_MODEL_ERR)
    with _LOCK:
        if _MODEL is not None:
            return _MODEL
        root = _model_dir()
        if not root.exists():
            _MODEL_ERR = "语音模型未装：%s" % root
            raise RuntimeError(_MODEL_ERR)
        try:
            # PyAV 19 去掉了 metadata_errors；faster-whisper 仍传该参 ⇒ 局部兼容。
            import av
            if not getattr(av, "_pa_open_patch", False):
                _orig_open = av.open

                def _open(*a, **kw):
                    kw.pop("metadata_errors", None)
                    return _orig_open(*a, **kw)
                av.open = _open
                av._pa_open_patch = True
            from faster_whisper import WhisperModel
            _MODEL = WhisperModel("small", device="cpu", compute_type="int8",
                                  download_root=str(root), local_files_only=True)
        except Exception as e:
            _MODEL_ERR = "语音模型加载失败：%s: %s" % (type(e).__name__, str(e)[:200])
            raise RuntimeError(_MODEL_ERR)
        return _MODEL


def _audio_path(data_dir, suffix):
    root = N.workspace_root(data_dir) / "attachments" / "voice" / datetime.now().strftime("%Y%m%d")
    root.mkdir(parents=True, exist_ok=True)
    suffix = (suffix or ".webm").lower()
    if suffix not in (".webm", ".wav", ".mp3", ".m4a", ".ogg", ".opus", ".mp4"):
        suffix = ".webm"
    p = root / (uuid.uuid4().hex[:12] + suffix)
    return p


def transcribe_audio(path, language="zh"):
    model = _model()
    segs, info = model.transcribe(str(path), language=language or None, vad_filter=True, beam_size=1)
    out, lines = [], []
    for s in segs:
        t = (s.text or "").strip()
        if not t:
            continue
        out.append(t)
        lines.append("[%05.1fs] %s" % (float(s.start or 0), t))
    return {"text": "".join(out).strip(), "lines": lines,
            "language": getattr(info, "language", "") or "",
            "duration": round(float(getattr(info, "duration", 0) or 0), 2)}


def voice_note(data_dir=None, filename="voice.webm", audio_bytes=None, language="zh"):
    raw = audio_bytes or b""
    if not raw:
        raise RuntimeError("空音频")
    if len(raw) > MAX_AUDIO:
        raise RuntimeError("音频过大（>100MB）")
    suffix = Path(filename or "voice.webm").suffix or ".webm"
    p = _audio_path(data_dir, suffix)
    p.write_bytes(raw)
    tr = transcribe_audio(p, language=language)
    text = (tr.get("text") or "").strip()
    if not text:
        raise RuntimeError("没有转写出文字（可能是静音或模型未识别）")
    now = datetime.now()
    title = "语音笔记 " + now.strftime("%m-%d %H:%M")
    body = text + "\n\n" + "\n".join(tr.get("lines") or [])
    rel = "attachments/voice/" + p.relative_to(N.workspace_root(data_dir) / "attachments" / "voice").as_posix()
    body += "\n\n[录音](" + rel + ")"
    note = N.create(title, body, ["语音"], data_dir=data_dir, source="voice", source_path=str(p))
    return {"note": note, "transcript": tr, "audio": str(p)}
