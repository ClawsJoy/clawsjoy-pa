#!/usr/bin/env python3
"""视觉智能体 - 统一入口"""

import sys

sys.path.insert(0, "/home/flybo/clawsjoy_v5")
import base64
from pathlib import Path

import requests


class VisionAgent:
    """视觉智能体 - 图像识别"""

    name = "vision_agent"
    description = "视觉智能体 - 图像识别与理解"
    version = "1.1.0"

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._init_skill()

    def _init_skill(self):
        try:
            from skills.image.vision import skill

            self.skill = skill
        except Exception as e:
            print(f"⚠️ 视觉技能加载失败: {e}")
            self.skill = None

    def describe_image(
        self, image_path: str, prompt: str = "描述这张图片的内容"
    ) -> dict:
        """描述图片 - 主动服务调用的方法"""
        if not self.skill:
            return {
                "success": False,
                "description": "视觉技能未加载",
                "error": "vision skill not available",
            }

        try:
            result = self.skill.execute({"image_path": image_path, "prompt": prompt})

            if result.get("success"):
                return {
                    "success": True,
                    "description": result.get("result", ""),
                    "image_path": image_path,
                }
            else:
                return {
                    "success": False,
                    "description": f"识别失败: {result.get('error', '未知错误')}",
                    "error": result.get("error"),
                }
        except Exception as e:
            return {
                "success": False,
                "description": f"识别异常: {str(e)}",
                "error": str(e),
            }

    def process(self, user_input: str, context: dict = None) -> dict:
        """处理图像识别请求"""
        if not self.skill:
            return {
                "success": False,
                "response": "视觉技能未加载，请安装 moondream 模型",
                "agent": self.name,
                "user_id": self.user_id,
            }

        import re

        path_match = re.search(r"(?:识别|描述|分析)[：:]?\s*(.+?)$", user_input)
        if not path_match:
            return {
                "success": False,
                "response": "请提供图片路径，例如：识别 /path/to/image.jpg",
                "agent": self.name,
                "user_id": self.user_id,
            }

        result = self.describe_image(path_match.group(1).strip())

        if result.get("success"):
            return {
                "success": True,
                "response": f"🖼️ {result.get('description', '识别完成')}",
                "agent": self.name,
                "user_id": self.user_id,
            }
        else:
            return {
                "success": False,
                "response": f"识别失败: {result.get('error', '未知错误')}",
                "agent": self.name,
                "user_id": self.user_id,
            }


vision_agent = VisionAgent()
