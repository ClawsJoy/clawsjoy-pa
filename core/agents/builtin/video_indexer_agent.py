#!/usr/bin/env python3
"""Video Indexer Agent - Video Indexer Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from core.agents.base.smart_agent import SmartAgent


class VideoIndexerAgent(SmartAgent):
    """视频索引 Agent"""

    name = "video_indexer_agent"
    description = "视频关键帧提取和描述生成"
    version = "1.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._init_vision_skill()
        print("🎬 VideoIndexerAgent 初始化完成")

    def _init_vision_skill(self):
        """初始化视觉技能"""
        try:
            from skills.image.vision import VisionSkill

            self.vision_skill = VisionSkill()
            print("   ✅ 视觉技能已加载")
        except Exception as e:
            print(f"   ❌ 技能加载失败: {e}")
            self.vision_skill = None

    def extract_frames(
        self, video_path: str, interval: int = 10, max_frames: int = 5
    ) -> List[str]:
        """提取视频关键帧"""
        frames = []
        try:
            # 获取视频时长
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    video_path,
                ],
                capture_output=True,
                text=True,
            )
            try:
                duration = float(result.stdout.strip())
            except (ValueError, TypeError):
                duration = 30.0

            # 计算帧间隔
            step = duration / (max_frames + 1)

            with tempfile.TemporaryDirectory() as tmpdir:
                for i in range(max_frames):
                    timestamp = step * (i + 1)
                    frame_path = Path(tmpdir) / f"frame_{i}.jpg"

                    subprocess.run(
                        [
                            "ffmpeg",
                            "-ss",
                            str(timestamp),
                            "-i",
                            video_path,
                            "-vframes",
                            "1",
                            "-q:v",
                            "2",
                            str(frame_path),
                        ],
                        capture_output=True,
                    )

                    if frame_path.exists():
                        frames.append(str(frame_path))
        except Exception as e:
            print(f"   ⚠️ 帧提取失败: {e}")

        return frames

    def describe_video(self, video_path: str) -> Dict:
        """描述视频内容"""
        if not self.vision_skill:
            return {"success": False, "error": "Vision skill not available"}

        path = Path(video_path)
        if not path.exists():
            return {"success": False, "error": f"Video not found: {video_path}"}

        # 提取关键帧
        frames = self.extract_frames(video_path)

        if not frames:
            return {
                "success": True,
                "description": f"视频文件: {path.name} (无法提取帧)",
                "frames_analyzed": 0,
            }

        # 分析每一帧
        descriptions = []
        for frame_path in frames:
            result = self.vision_skill.execute(
                {"image_path": frame_path, "task": "describe"}
            )
            if result and result.get("success"):
                descriptions.append(result.get("description", ""))
            else:
                descriptions.append("无法识别该帧")

        return {
            "success": True,
            "description": " | ".join(descriptions),
            "frames_analyzed": len(frames),
        }

    def process(self, message: str, **kwargs) -> Dict:
        """处理请求"""
        if "描述" in message or "分析" in message:
            # 提取视频路径
            import re

            video_match = re.search(r"([^\s]+\.(mp4|avi|mov|mkv))", message)
            if video_match:
                return self.describe_video(video_match.group(1))
            return {"success": False, "error": "请提供视频文件路径"}
        return {"success": False, "error": "不支持的操作"}

    def can_handle(self, user_input: str) -> Dict:
        """判断是否能处理该请求"""
        keywords = ["视频", "分析", "描述", "识别", "帧", "index", "索引", "内容"]
        for kw in keywords:
            if kw in user_input.lower():
                return {"can": True, "confidence": 0.7}
        return {"can": False, "confidence": 0.0}

    # 全局实例


video_indexer_agent = VideoIndexerAgent()
