#!/usr/bin/env python3
"""VideoAnalyzer v8.0 — 视频逆向工程分析器"""

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional


class VideoAnalyzer:
    """视频逆向工程分析器 — 场景检测 + 帧分析 + 字幕对齐 + 制作手册"""

    def __init__(self):
        self.tmpdir = None

    def analyze(self, video_path: str, subtitle_path: str = None) -> dict:
        """完整分析流水线"""
        self.tmpdir = tempfile.mkdtemp()
        try:
            scenes = self._detect_scenes(video_path)
            if not scenes:
                return {"error": "未能检测到场景", "scenes": []}

            for scene in scenes:
                scene["frame_analysis"] = self._analyze_frame(scene["keyframe_path"])

            if subtitle_path and os.path.exists(subtitle_path):
                self._align_subtitles(scenes, subtitle_path)

            report = self._generate_report(scenes, video_path)
            return report
        finally:
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ========== 第一层：场景检测 ==========

    def _detect_scenes(self, video_path: str) -> List[dict]:
        """ffmpeg 场景检测 + 时间戳分组"""
        output_pattern = f"{self.tmpdir}/keyframe_%03d.jpg"

        # 用 ffmpeg 提取关键帧 + 时间戳信息
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            "select='gt(scene,0.4)',showinfo",
            "-vsync",
            "vfr",
            output_pattern,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")

        # 解析 stderr 中的 showinfo 时间戳
        timestamps = []
        for line in result.stderr.split("\n"):
            m = re.search(r"pts_time:([\d.]+)", line)
            if m:
                timestamps.append(float(m.group(1)))

        # 匹配关键帧文件
        frame_files = sorted([f for f in os.listdir(self.tmpdir) if f.startswith("keyframe_")])

        if not frame_files:
            return []

        # 帧 + 时间戳配对，按相邻 15 秒内分组
        scenes = []
        current_group = {"start": timestamps[0] if timestamps else 0, "frames": []}

        for i, fname in enumerate(frame_files):
            ts = timestamps[i] if i < len(timestamps) else current_group["start"] + i * 5
            fpath = f"{self.tmpdir}/{fname}"

            if current_group["frames"] and ts - current_group["frames"][-1]["timestamp"] > 15:
                # 新场景
                current_group["end"] = current_group["frames"][-1]["timestamp"]
                current_group["keyframe_path"] = current_group["frames"][len(current_group["frames"]) // 2]["path"]
                scenes.append(current_group)
                current_group = {"start": ts, "frames": []}

            current_group["frames"].append({"timestamp": ts, "path": fpath})

        # 最后一个场景
        if current_group["frames"]:
            current_group["end"] = current_group["frames"][-1]["timestamp"]
            current_group["keyframe_path"] = current_group["frames"][len(current_group["frames"]) // 2]["path"]
            scenes.append(current_group)

        return scenes

    # ========== 第二层：帧分析 ==========

    def _analyze_frame(self, frame_path: str, mode: str = "video") -> str:
        import time

        import requests

        with open(frame_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        if mode == "image":
            prompt = "分析这张图片的制作手法：" "1.视觉风格（色调、光影、构图）" "2.AI生成痕迹（如果有）" "3.可复现性（能否用AI工具做出类似效果）" "直接给出分析，用中文，50字以内。"
        else:
            prompt = (
                "分析这帧画面："
                "1.场景类型（演播室/动画/数据图表/实拍）"
                "2.视觉风格（色调、光影、构图）"
                "3.人物（如果有）的表情、动作、角色定位"
                "4.画面中的文字或数据"
                "直接给出分析结果，用中文，40字以内。"
            )

        result = ""
        for attempt in range(2):
            try:
                resp = requests.post(
                    "http://localhost:11435/api/generate",
                    json={"model": "llava:latest", "prompt": prompt, "images": [img_b64], "stream": False},
                    timeout=120,
                )
                if resp.status_code == 200:
                    result = resp.json().get("response", "")
                    break
            except Exception:
                if attempt == 0:
                    time.sleep(5)

        # 检测英文，自动翻译,重试机制
        if result and not any("\u4e00" <= c <= "\u9fff" for c in result[:30]):
            for tr_attempt in range(2):
                try:
                    tr = requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "qwen2.5:7b-instruct-q4_0-gpu",
                            "prompt": f"翻译成中文：{result[:500]}",
                            "stream": False,
                        },
                        timeout=30,
                    )
                    if tr.status_code == 200:
                        result = tr.json().get("response", result)
                        break
                except Exception:
                    time.sleep(3)

        return result or "[分析超时]"

    # ========== 第二层：字幕对齐 ==========

    def _align_subtitles(self, scenes: List[dict], subtitle_path: str):
        """把字幕按时间戳分配到对应场景"""
        with open(subtitle_path, encoding="utf-8") as f:
            lines = f.readlines()

        subtitles = []
        for line in lines:
            m = re.match(r"\[([\d.]+)s\]\s+(.+)", line)
            if m:
                subtitles.append({"timestamp": float(m.group(1)), "text": m.group(2).strip()})

        for scene in scenes:
            scene["subtitles"] = [s["text"] for s in subtitles if scene["start"] <= s["timestamp"] <= scene["end"]]

    # ========== 第三层：逆向总结 ==========

    def _generate_report(self, scenes: List[dict], video_path: str) -> dict:
        """LLM 生成制作手册"""
        # 构建场景摘要
        scene_summaries = []
        for i, scene in enumerate(scenes):
            duration = scene["end"] - scene["start"]
            frame_desc = scene.get("frame_analysis", "")
            subs = " ".join(scene.get("subtitles", [])[:5])[:200]
            scene_summaries.append(f"场景{i+1} [{duration:.0f}秒]: 画面={frame_desc[:100]}, 字幕={subs[:100]}")

        # 全片统计
        total_duration = sum(s["end"] - s["start"] for s in scenes)
        stats = {
            "场景数": len(scenes),
            "总时长": f"{total_duration:.0f}秒",
            "平均场景时长": f"{total_duration/len(scenes):.0f}秒" if scenes else "0",
        }

        # LLM 汇总
        summary_prompt = f"""你是一个视频制作分析师。请根据以下场景分析数据，逆向工程这个视频的制作手法：

文件名：{os.path.basename(video_path)}
统计：{json.dumps(stats, ensure_ascii=False)}
场景数：{len(scenes)}

场景列表：
{chr(10).join(scene_summaries[:20])}

请分析：
1. 剧本结构（分几个部分，每部分讲什么）
2. 场景设计（演播室/动画/数据图表各占多少，视觉风格）
3. 角色设计（主播形象、AI巨头角色如何呈现）
4. 转场手法（场景间怎么切换）
5. 叙事节奏（高潮在哪里）
6. AI制作痕迹（哪些是AI生成的）
7. 卡牌式叙事结构（每个角色像一张卡牌轮流出场）

400字以内。"""

        import requests as _r

        try:
            resp = _r.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b-instruct-q4_0-gpu",
                    "prompt": summary_prompt,
                    "stream": False,
                },
                timeout=120,
            )
            report_text = resp.json().get("response", "") if resp.status_code == 200 else ""
        except Exception as e:
            report_text = f"[汇总失败: {e}]"

        return {
            "file": os.path.basename(video_path),
            "stats": stats,
            "scenes": [
                {
                    "id": i + 1,
                    "start": s["start"],
                    "end": s["end"],
                    "duration": s["end"] - s["start"],
                    "frame_analysis": s.get("frame_analysis", ""),
                    "subtitles": s.get("subtitles", [])[:5],
                }
                for i, s in enumerate(scenes)
            ],
            "report": report_text,
        }
