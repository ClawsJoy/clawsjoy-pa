# -*- coding: utf-8 -*-
"""多模态学习管线 — 收件箱文件 → 转录/提取 → 笔记(2026-09-01)

设计: docs/reports/obsidian_learning_system_design_20260901.md
- 视频/音频: faster-whisper 转录(CPU int8, 中文) → LLM 总结
- PDF: PyPDF2 提取文本 → LLM 总结
- 图片: 复制原文件 + 占位描述(OCR 后续)
输出: vault/学习笔记/{类型}/笔记.md + 原文件复制到 vault/assets/
"""
from __future__ import annotations

import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _vault_root() -> Path:
    """vault 根(与 precision_inject._vault_path 一致)"""
    try:
        import yaml

        with open("config/v9/execution_policy.yaml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        p = (cfg.get("obsidian") or {}).get("vault_path", "")
        if p and Path(p).exists():
            return Path(p)
    except Exception:
        pass
    return Path("/mnt/d/Obsidian/ClawsJoy/ClawsJoy")


def _llm_summarize(text: str, max_chars: int = 3000) -> str:
    """用 LLM 总结要点(调 DeepSeek API)。失败时返回文本截断兜底。"""
    try:
        import os

        import requests

        _key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not _key:
            return _fallback_summary(text)
        _resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": "Bearer " + _key, "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是学习笔记助手。把输入内容提炼成结构化要点：用 ## 要点 开头, 每条要点用 - 开头, 简洁准确; 最后给 3 行总结。"},
                    {"role": "user", "content": text[:12000]},
                ],
                "max_tokens": 800,
                "temperature": 0.3,
            },
            timeout=60,
        )
        if _resp.status_code == 200:
            _d = _resp.json()
            return str((_d.get("choices") or [{}])[0].get("message", {}).get("content", "") or _fallback_summary(text))[
                :max_chars
            ]
    except Exception as e:
        print(f"[LEARN] LLM 总结失败(兜底截断): {e}")
    return _fallback_summary(text)


def _fallback_summary(text: str) -> str:
    """LLM 不可用时: 取前 N 行作为要点占位。"""
    _lines = [l.strip() for l in str(text or "").split(chr(10)) if l.strip()]
    _head = chr(10).join("- " + l[:80] for l in _lines[:8])
    return "## 要点" + chr(10) + (_head if _head else "- (无文本)") + chr(10) + chr(10) + "> 注: LLM 总结不可用, 以上为原文开头。"


def _transcribe_audio(file_path: Path) -> Dict[str, Any]:
    """faster-whisper 转录(CPU int8, 中文优先)。返回 {text, segments_count, model}。"""
    try:
        from faster_whisper import WhisperModel

        _t0 = time.time()
        _model = WhisperModel("base", device="cpu", compute_type="int8")
        _segs, _info = _model.transcribe(str(file_path), language=None, vad_filter=True)
        _parts = []
        _n = 0
        for _s in _segs:
            _parts.append(str(_s.text or "").strip())
            _n += 1
        _txt = " ".join(p for p in _parts if p)
        return {
            "text": _txt,
            "segments_count": _n,
            "model": "faster-whisper/base/int8",
            "lang": getattr(_info, "language", "auto"),
            "took_s": round(time.time() - _t0, 1),
        }
    except Exception as e:
        return {"error": "whisper 转录失败: " + str(e), "text": ""}


def _describe_image_llava(file_path: Path) -> Dict[str, Any]:
    """llava 读图(11435 /api/generate + base64)。返回 {description, model}。

    2026-09-01: vision_agent 配置已切 llava(moondream→llava, 11434→11435)。
    """
    try:
        import base64

        import requests
        import yaml as _y

        _model = "llava:latest"
        _endpoint = "http://localhost:11435"
        try:
            with open("config/agents/vision_agent/config.yaml", encoding="utf-8") as _f:
                _vc = (_y.safe_load(_f) or {}).get("vision") or {}
            _model = str(_vc.get("model") or _model)
            _endpoint = str(_vc.get("endpoint") or _endpoint)
        except Exception:
            pass
        with open(file_path, "rb") as _f:
            _b64 = base64.b64encode(_f.read()).decode()
        _resp = requests.post(
            _endpoint + "/api/generate",
            json={"model": _model, "prompt": "Describe this image in detail.", "images": [_b64], "stream": False},
            timeout=60,
        )
        if _resp.status_code == 200:
            return {"description": str(_resp.json().get("response") or ""), "model": _model}
        return {"error": "llava returned " + str(_resp.status_code)}
    except Exception as e:
        return {"error": "llava read image failed: " + str(e)}


def _extract_pdf(file_path: Path) -> Dict[str, Any]:
    """PyPDF2 提取文本(限 3 万字符防膨胀)。"""
    try:
        from PyPDF2 import PdfReader

        _r = PdfReader(str(file_path))
        _n = len(_r.pages)
        _parts = []
        for _pg in _r.pages[:20]:
            try:
                _parts.append(str(_pg.extract_text() or ""))
            except Exception:
                continue
        _txt = chr(10).join(_parts)[:30000]
        return {"text": _txt, "pages": _n}
    except Exception as e:
        return {"error": "PDF 提取失败: " + str(e), "text": ""}


def _youtube_url_from_text(text: str) -> str:
    """从文本提取 youtube URL(支持 watch?v= / youtu.be / shorts / 纯链接)。"""
    import re

    m = re.search(
        r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([\w-]{6,})",
        text or "",
    )
    if m:
        return "https://www.youtube.com/watch?v=" + m.group(1)
    return ""


def _has_transcript(note_text: str) -> bool:
    """判断笔记是否已有字幕/转录(transcript 章节或 frontmatter transcript: true)。"""
    if "transcript: true" in (note_text or ""):
        return True
    if "## 原文转录" in (note_text or "") or "## 字幕" in (note_text or ""):
        return True
    return False


def process_youtube(source_url: str, note_path: str = "", title: str = "") -> Dict[str, Any]:
    """处理 YouTube 剪藏/链接: 检测字幕 → yt-dlp 下载音频(绕死代理) → whisper 转录 → 写入笔记。

    2026-09-01: 当前环境 yt-dlp 可解析但音频下载被 YouTube 403(JS challenge/IP 风控),
    下载失败时降级标注「需手动下载视频」。用户放本地视频进收件箱 → process_media 转录可行。

    source_url: YouTube 链接; note_path: 对应剪藏笔记(vault 路径), 可选(无则新建笔记)。
    返回 {success, transcript, note_path, downloaded, degraded?}。
    """
    try:
        import os
        import shutil
        import subprocess
        from pathlib import Path

        root = _vault_root()
        note_dir = root / "学习笔记" / "视频"
        note_dir.mkdir(parents=True, exist_ok=True)
        _url = _youtube_url_from_text(source_url)
        if not _url:
            return {"success": False, "error": "未识别到 YouTube 链接"}
        # 定位笔记
        note_fp = None
        if note_path:
            np_ = Path(note_path)
            note_fp = np_ if np_.is_absolute() else (root / np_)
        # 已有字幕 → 跳过
        if note_fp and note_fp.exists():
            if _has_transcript(note_fp.read_text(encoding="utf-8", errors="ignore")):
                return {"success": True, "skipped": True, "reason": "已含字幕", "note_path": str(note_fp)}
        # yt-dlp 下载音频(绕死代理: 环境 HTTP_PROXY=127.0.0.1:7890 但代理未监听)
        _tmp_dir = Path("/tmp/yt_dl_" + str(int(time.time())))
        _tmp_dir.mkdir(parents=True, exist_ok=True)
        _audio_path = None
        _env = {
            k: v
            for k, v in os.environ.items()
            if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")
        }
        _env["XDG_CACHE_HOME"] = "/tmp/ytcache"
        _env["HOME"] = "/tmp/ytcache"
        _dl_cmd = [
            "yt-dlp",
            "--remote-components",
            "ejs:github",
            "-f",
            "140",
            "--max-filesize",
            "30M",
            "-o",
            str(_tmp_dir / "audio.%(ext)s"),
            _url,
        ]
        _dl = subprocess.run(_dl_cmd, capture_output=True, text=True, timeout=120, env=_env)
        _audio_cands = list(_tmp_dir.glob("audio.*"))
        if _dl.returncode == 0 and _audio_cands:
            _audio_path = _audio_cands[0]
        # 下载失败 → 降级标注
        if _audio_path is None or not _audio_path.exists():
            _degraded = (
                "需手动下载视频（yt-dlp 下载被 YouTube 403: 当前环境无法自动拉取。可用 yt-dlp 手动下载后放入 收件箱/ 或 data/videos/, 再调 process_media 转录）"
            )
            _note_txt = (
                "---"
                + chr(10)
                + "type: learning"
                + chr(10)
                + "source: video"
                + chr(10)
                + 'original: "'
                + _url
                + '"'
                + chr(10)
                + "transcript: false"
                + chr(10)
                + "youtube: "
                + _url
                + chr(10)
                + "tags: [学习, 视频, youtube]"
                + chr(10)
                + "created: "
                + datetime.now().strftime("%Y-%m-%d")
                + chr(10)
                + "---"
                + chr(10)
                + chr(10)
                + "# "
                + (title or "YouTube 视频")
                + chr(10)
                + chr(10)
                + "## 字幕补齐"
                + chr(10)
                + "- [ ] "
                + _degraded
            )
            _fname = datetime.now().strftime("%Y-%m-%d") + "-" + (title or "youtube")[:40] + ".md"
            # 2026-09-01 修复: 降级时**新建独立笔记**(学习笔记/视频/), 不覆盖原剪藏(note_fp)。
            # (E2E 发现: 带 note_path 时降级覆盖了 Clippings 原文件 → 原剪藏内容丢失)
            _note_path = note_dir / _fname
            _note_path.write_text(_note_txt, encoding="utf-8")
            return {"success": True, "degraded": True, "note_path": str(_note_path), "reason": _degraded}
        # 转录
        _tr = _transcribe_audio(_audio_path)
        if _tr.get("error"):
            return {"success": False, "error": "转录失败: " + _tr["error"]}
        _transcript = _tr.get("text", "")
        # 写入笔记(追加字幕章节 + frontmatter 标记)
        if note_fp and note_fp.exists():
            _note_txt = note_fp.read_text(encoding="utf-8")
            _note_txt = _note_txt.replace("transcript: false", "transcript: true")
            _note_txt = (
                _note_txt.rstrip()
                + chr(10)
                + chr(10)
                + "## 原文转录"
                + chr(10)
                + "<details>"
                + chr(10)
                + "<summary>展开全文转录</summary>"
                + chr(10)
                + chr(10)
                + _transcript[:20000]
                + chr(10)
                + "</details>"
            )
            _note_path = note_fp
        else:
            _fm = [
                "---",
                "type: learning",
                "source: video",
                'original: "' + _url + '"',
                "transcript: true",
                "youtube: " + _url,
                "tags: [学习, 视频, youtube]",
                "created: " + datetime.now().strftime("%Y-%m-%d"),
                "---",
            ]
            _fname = datetime.now().strftime("%Y-%m-%d") + "-" + (title or "youtube")[:40] + ".md"
            _note_path = note_dir / _fname
            _note_txt = (
                chr(10).join(_fm)
                + chr(10)
                + chr(10)
                + "# "
                + (title or "YouTube 视频")
                + chr(10)
                + chr(10)
                + _url
                + chr(10)
                + chr(10)
                + "## 要点"
                + chr(10)
                + "- (转录完成, 详见原文转录)"
                + chr(10)
                + chr(10)
                + "## 原文转录"
                + chr(10)
                + "<details>"
                + chr(10)
                + "<summary>展开全文转录</summary>"
                + chr(10)
                + chr(10)
                + _transcript[:20000]
                + chr(10)
                + "</details>"
            )
        _note_path.write_text(_note_txt, encoding="utf-8")
        # 清理临时音频
        try:
            shutil.rmtree(_tmp_dir, ignore_errors=True)
        except Exception:
            pass
        return {
            "success": True,
            "transcript": _transcript[:500],
            "note_path": str(_note_path),
            "downloaded": True,
            "chars": len(_transcript),
        }
    except Exception as e:
        return {"success": False, "error": "process_youtube 异常: " + str(e)}


def process_media(file_path: str, media_type: str = "", title: str = "") -> Dict[str, Any]:
    """处理媒体文件: 转录/提取 → 总结 → 写笔记 + 复制原文件到 assets/。

    file_path: vault 内或沙箱内路径(收件箱/xxx.mp4 或沙箱 data/tmp/xxx.mp4)
    media_type: 自动推断(auto)或显式 video/audio/image/pdf
    返回 {success, note_path, rel_path, media: {name, copied_to}, summary, error?}
    """
    try:
        root = _vault_root()
        inbox = root / "收件箱"
        assets = root / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        # 定位源文件
        src = Path(file_path)
        if not src.is_absolute():
            # 优先收件箱, 再沙箱当前目录
            cand = inbox / file_path
            if cand.exists():
                src = cand
            else:
                src = Path(file_path)
        if not src.exists():
            return {"success": False, "error": "文件不存在: " + str(file_path)}
        # 推断类型
        _suffix = src.suffix.lower()
        if not media_type or media_type in ("auto", ""):
            if _suffix in (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"):
                media_type = "video"
            elif _suffix in (".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".opus"):
                media_type = "audio"
            elif _suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
                media_type = "image"
            elif _suffix in (".pdf",):
                media_type = "pdf"
            else:
                return {"success": False, "error": "不支持的文件类型: " + _suffix}
        media_type = str(media_type).lower()
        _type_dir = {"video": "视频", "audio": "音频", "image": "图片", "pdf": "PDF"}.get(media_type, "视频")
        note_dir = root / "学习笔记" / _type_dir
        note_dir.mkdir(parents=True, exist_ok=True)
        # 复制原文件到 assets/(防 vault 引用断裂; 收件箱内文件不动)
        _media_name = src.name
        _assets_dst = assets / _media_name
        if not _assets_dst.exists():
            shutil.copy2(src, _assets_dst)
        # 提取内容
        _transcript = ""
        _has_transcript = False
        if media_type in ("video", "audio"):
            _r = _transcribe_audio(src)
            if _r.get("error"):
                return {
                    "success": False,
                    "error": _r["error"],
                    "media": {"name": _media_name, "copied_to": str(_assets_dst)},
                }
            _transcript = _r.get("text", "")
            _has_transcript = bool(_transcript.strip())
            _content_txt = _transcript
        elif media_type == "pdf":
            _r = _extract_pdf(src)
            if _r.get("error"):
                return {
                    "success": False,
                    "error": _r["error"],
                    "media": {"name": _media_name, "copied_to": str(_assets_dst)},
                }
            _transcript = _r.get("text", "")
            _has_transcript = True
            _content_txt = _transcript
        else:  # image — llava 读图(2026-09-01)
            _lr = _describe_image_llava(src)
            if _lr.get("error"):
                _content_txt = "(llava 读图失败: " + _lr["error"] + ". 原文件已复制到 assets/.)"
                print("[LEARN] llava 读图失败: " + _lr["error"])
            else:
                _content_txt = (
                    "## 图片描述"
                    + chr(10)
                    + _lr.get("description", "")
                    + chr(10)
                    + chr(10)
                    + "> llava 模型: "
                    + _lr.get("model", "")
                )
        # LLM 总结
        _summary = _llm_summarize(_content_txt) if _content_txt.strip() else "## 要点" + chr(10) + "- (未提取到文本)"
        # 写笔记
        _title = (title or src.stem)[:60]
        _fname = datetime.now().strftime("%Y-%m-%d") + "-" + _title + ".md"
        _note_path = note_dir / _fname
        _embed = "![[assets/" + _media_name + "]]"
        _fm = [
            "---",
            "type: learning",
            "source: " + media_type,
            'original: "' + _embed + '"',
            "transcript: " + ("true" if _has_transcript else "false"),
            'summary: "'
            + (_summary.split(chr(10))[0].replace("- ", "").replace('"', "'")[:100] if _summary else "")
            + '"',
            "tags: [学习, " + media_type + "]",
            "created: " + datetime.now().strftime("%Y-%m-%d"),
            "---",
        ]
        _note_txt = (
            chr(10).join(_fm)
            + chr(10)
            + chr(10)
            + "# "
            + _title
            + chr(10)
            + chr(10)
            + _embed
            + chr(10)
            + chr(10)
            + _summary
        )
        if _has_transcript and _transcript:
            _note_txt += (
                chr(10)
                + chr(10)
                + "## 原文转录"
                + chr(10)
                + "<details>"
                + chr(10)
                + "<summary>展开全文转录</summary>"
                + chr(10)
                + chr(10)
                + _transcript[:20000]
                + chr(10)
                + "</details>"
            )
        _note_path.write_text(_note_txt, encoding="utf-8")
        return {
            "success": True,
            "note_path": str(_note_path),
            "rel_path": str(_note_path.relative_to(root)),
            "media": {"name": _media_name, "copied_to": str(_assets_dst)},
            "summary": _summary,
            "media_type": media_type,
            "transcript_chars": len(_transcript),
        }
    except Exception as e:
        return {"success": False, "error": "process_media 异常: " + str(e)}
