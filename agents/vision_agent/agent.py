#!/usr/bin/env python3
"""视觉智能体 - 图像理解、生成、全景"""

import base64
import importlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from core.agents.business.business_agent_v2 import BusinessAgentV2

# agents/vision_agent/agent.py
from core.lib.input_validator import input_validator


class VisionAgent(BusinessAgent):
    def handle(self, user_input: str, context: dict = None) -> dict:
        # 验证图像提示词
        validation = input_validator.validate_image_prompt(user_input)

        if not validation.valid:
            return {
                "success": False,
                "error": "提示词验证失败",
                "errors": validation.errors,
                "response": f"❌ {', '.join(validation.errors)}",
            }

        sanitized_prompt = validation.sanitized_value

        try:
            # 生成图像
            image_path = self._generate_image(sanitized_prompt)
            return {
                "success": True,
                "agent": self.name,
                "image_path": image_path,
                "response": f"🎨 图像已保存\n📁 路径: {image_path}\n提示词: {sanitized_prompt}",
            }
        except RecursionError:
            return {
                "success": False,
                "error": "递归深度超限",
                "response": "❌ 图像生成出现递归错误",
            }


class VisionAgent(BusinessAgentV2):
    name = "vision_agent"
    description = "智能视觉理解与图像生成"
    version = "3.8.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._init_skills()
        self.image_memory = {}
        self.last_generated = None
        self.output_dir = Path("downloads")
        self.output_dir.mkdir(exist_ok=True)
        print(f"👁️ 视觉智能体 v{self.version} 已上线")

    def _init_skills(self):
        self.skills = {}
        try:
            module = importlib.import_module("skills.vision.scripts.main")
            self.skills["vision"] = getattr(module, "execute")
            print("   ✅ 视觉理解技能已加载")
        except Exception:
            pass

        try:
            from engine.image.sd_generator import sd_gen

            self.sd_gen = sd_gen
            print("   ✅ SD 图像生成引擎已加载")
        except Exception as e:
            print(f"   ⚠️ SD 引擎加载失败: {e}")
            self.sd_gen = None

    def _save_image(self, image_base64: str, prefix: str = "image") -> str:
        """保存图片到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.png"
        filepath = self.output_dir / filename

        img_data = base64.b64decode(image_base64)
        with open(filepath, "wb") as f:
            f.write(img_data)

        return str(filepath)

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        if any(kw in user_input for kw in ["全景", "360", "panorama"]):
            return self._generate_panorama(user_input)

        if any(kw in user_input for kw in ["生成", "画", "绘制"]):
            return self._generate_image(user_input)

        if self._has_image_path(user_input):
            if any(q in user_input for q in ["什么", "多少", "哪里", "有没有"]):
                return self._ask_about_image(user_input)
            if "描述" in user_input:
                return self._describe_image(user_input)

        if "这张图片" in user_input:
            return self._understand_image(user_input)

        return self._help()

    def _generate_panorama(self, user_input: str) -> dict:
        # 提取提示词 - 保留数字
        prompt = user_input
        # 只移除动作词，不移除数字
        for kw in ["生成", "全景", "panorama", "一张"]:
            prompt = prompt.replace(kw, "")
        # 处理 "360度" 特殊处理
        prompt = prompt.replace("360度", "360度")
        prompt = prompt.strip()
        # 如果变成空，使用默认
        if not prompt or prompt in ["度", "的"]:
            prompt = "beautiful landscape"

        if not prompt:
            prompt = "beautiful landscape"

        full_prompt = f"{prompt}, 360 degree panorama, wide angle, seamless, spherical view"

        if not self.sd_gen:
            return {"success": False, "response": "SD引擎未就绪", "agent": self.name}

        result = self.sd_gen.generate(full_prompt, width=1024, height=512, steps=25)

        if result.get("success"):
            filepath = self._save_image(result.get("image_base64"), "panorama")
            self.last_generated = {
                "type": "panorama",
                "prompt": prompt,
                "file": filepath,
            }
            return {
                "success": True,
                "response": f"🌐 360°全景图已保存\n📁 路径: {filepath}\n提示词: {prompt}\n分辨率: 1024x512",
                "image_path": filepath,
                "panorama": True,
                "agent": self.name,
            }

        return {
            "success": False,
            "response": f"全景生成失败: {result.get('error')}",
            "agent": self.name,
        }

    def _generate_image(self, user_input: str) -> dict:
        prompt = user_input
        for kw in ["生成", "画", "绘制", "一张"]:
            prompt = prompt.replace(kw, "")
        prompt = prompt.strip()

        if not prompt:
            return {
                "success": False,
                "response": "请描述要生成的图片内容",
                "agent": self.name,
            }

        if not self.sd_gen:
            return {"success": False, "response": "SD引擎未就绪", "agent": self.name}

        result = self.sd_gen.generate(prompt, steps=20)

        if result.get("success"):
            filepath = self._save_image(result.get("image_base64"), "image")
            self.last_generated = {"type": "image", "prompt": prompt, "file": filepath}
            return {
                "success": True,
                "response": f"🎨 图像已保存\n📁 路径: {filepath}\n提示词: {prompt}",
                "image_path": filepath,
                "agent": self.name,
            }

        return {
            "success": False,
            "response": f"生成失败: {result.get('error')}",
            "agent": self.name,
        }

    def _understand_image(self, user_input: str) -> dict:
        image_path = self._get_last_image()
        if not image_path:
            return {"success": False, "response": "请先上传图片", "agent": self.name}

        question = user_input.replace("这张图片", "").replace("这张图", "").strip()
        if not question:
            question = "描述这张图片"

        if "vision" in self.skills:
            result = self.skills["vision"]({"image_path": image_path, "prompt": question})
            return {
                "success": True,
                "response": result.get("result", "无法识别"),
                "agent": self.name,
            }

        return {"success": True, "response": f"图片分析完成", "agent": self.name}

    def _describe_image(self, user_input: str) -> dict:
        image_path = self._extract_image_path(user_input)
        if not image_path:
            return {"success": False, "response": "请指定图片路径", "agent": self.name}

        self.image_memory["last"] = image_path

        if "vision" in self.skills:
            result = self.skills["vision"]({"image_path": image_path, "prompt": "详细描述这张图片"})
            return {
                "success": True,
                "response": f"🖼️ {result.get('result', '无法描述')}",
                "agent": self.name,
            }

        return {
            "success": True,
            "response": f"图片 {image_path} 的内容描述",
            "agent": self.name,
        }

    def _ask_about_image(self, user_input: str) -> dict:
        image_path = self._extract_image_path(user_input)
        if not image_path:
            image_path = self._get_last_image()
            if not image_path:
                return {
                    "success": False,
                    "response": "请指定图片路径",
                    "agent": self.name,
                }

        question = user_input.replace(image_path, "").strip()
        if not question:
            question = "这张图片里有什么"

        if "vision" in self.skills:
            result = self.skills["vision"]({"image_path": image_path, "prompt": question})
            return {
                "success": True,
                "response": result.get("result", "无法回答"),
                "agent": self.name,
            }

        return {"success": True, "response": f"关于图片的问答", "agent": self.name}

    def _help(self) -> dict:
        return {
            "success": True,
            "response": """👁️ 我能做什么：

🎨 **图像生成** → 保存到 downloads/
• 生成一只猫
• 画一张风景

🌐 **360°全景** → 保存到 downloads/
• 生成360度全景图
• 制作全景风景

📷 **图片理解**
• 描述图片 /path/to/image.jpg
• /path/to/image.jpg 里有什么""",
            "agent": self.name,
        }

    def _has_image_path(self, text: str) -> bool:
        return bool(re.search(r"[^\s]+\.(jpg|png|jpeg|webp|gif)", text, re.IGNORECASE))

    def _extract_image_path(self, text: str) -> str:
        match = re.search(r"([^\s]+\.(jpg|png|jpeg|webp|gif))", text, re.IGNORECASE)
        return match.group(1) if match else ""

    def _get_last_image(self) -> str:
        return self.image_memory.get("last", "")


def get_vision_agent(user_id: str = "default"):
    return VisionAgent(user_id)

    def handle(self, user_input: str, context: dict = None) -> dict:
        """统一入口"""
        return self._execute_business(user_input, context)
