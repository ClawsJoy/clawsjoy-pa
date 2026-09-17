"""文生图模块 - 集成多种生成方式"""

import base64
from pathlib import Path
from typing import Dict, Optional

import requests


class ImageGenerator:
    """图像生成器"""

    def __init__(self):
        # 方案1: 使用 Ollama + 视觉模型（需要支持）
        self.ollama_url = "http://localhost:11434"

        # 方案2: 使用本地 Stable Diffusion API
        self.sd_url = "http://localhost:7860"

        # 方案3: 使用第三方 API（如 硅基流动、阿里通义）
        self.api_key = None

        self.enabled = False

    def generate_with_ollama(self, prompt: str) -> Optional[bytes]:
        """使用 Ollama 生成图像（需要支持多模态的模型）"""
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "llava:7b", "prompt": f"Generate an image: {prompt}", "stream": False},  # 需要支持图像生成的模型
                timeout=60,
            )
            if resp.status_code == 200:
                # 返回图像数据
                return resp.content
        except Exception as e:
            print(f"Ollama 图像生成失败: {e}")
        return None

    def generate_with_sd(self, prompt: str, negative_prompt: str = "") -> Optional[bytes]:
        """使用 Stable Diffusion API"""
        try:
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": 20,
                "width": 512,
                "height": 512,
                "cfg_scale": 7,
            }
            resp = requests.post(f"{self.sd_url}/sdapi/v1/txt2img", json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                images = data.get("images", [])
                if images:
                    return base64.b64decode(images[0])
        except Exception as e:
            print(f"SD 图像生成失败: {e}")
        return None

    def generate_simple(self, prompt: str) -> Dict:
        """简单占位图生成（当没有图像生成能力时）"""
        # 生成一个简单的 SVG 占位图
        svg = f"""<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
            <rect width="400" height="400" fill="url(#grad)"/>
            <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#6366f1;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:1" />
                </linearGradient>
            </defs>
            <text x="200" y="180" text-anchor="middle" fill="white" font-size="20" font-family="sans-serif">ClawsJoy AI</text>
            <text x="200" y="220" text-anchor="middle" fill="#ddd" font-size="14" font-family="sans-serif">生成: {prompt[:50]}</text>
        </svg>"""

        return {"success": True, "format": "svg", "data": svg, "message": "SVG 占位图（如需真实图像，请配置 Stable Diffusion）"}


image_generator = ImageGenerator()
