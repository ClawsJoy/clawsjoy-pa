"""Stable Diffusion 图像生成 - 使用 diffusers"""

import base64
import io
from pathlib import Path

import torch
from PIL import Image


class SDGenerator:
    def __init__(self):
        self.pipe = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._init_pipeline()

    def _init_pipeline(self):
        """初始化 SD 管道"""
        try:
            print(f"加载 SD 模型... (设备: {self.device})")

            from diffusers import StableDiffusionPipeline

            self.pipe = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )

            if self.device == "cuda":
                self.pipe.enable_attention_slicing()
                self.pipe.vae.enable_slicing()
                self.pipe = self.pipe.to(self.device)

            print("✅ SD 模型加载成功")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            self.pipe = None

    def generate(self, prompt, negative="", width=384, height=384, steps=15):
        """生成图像"""
        if not self.pipe:
            return {"success": False, "error": "模型未加载"}

        try:
            print(f"生成: {prompt[:50]}...")

            # 禁用 NSFW 检测
            self.pipe.safety_checker = None

            with torch.no_grad():
                result = self.pipe(
                    prompt=prompt,
                    negative_prompt=negative,
                    width=width,
                    height=height,
                    num_inference_steps=steps,
                    guidance_scale=7.0,
                )

            image = result.images[0]
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            return {
                "success": True,
                "image_base64": img_base64,
                "prompt": prompt,
                "width": width,
                "height": height,
            }
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            return {"success": False, "error": "显存不足，请降低分辨率"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# 导出全局实例
sd_gen = SDGenerator()


if __name__ == "__main__":
    result = sd_gen.generate("a cute cat", steps=10)
    print(result)
