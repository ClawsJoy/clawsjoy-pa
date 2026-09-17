"""图片分析器 - 提取丰富的元数据（即梦风格）"""

import base64
import tempfile
from pathlib import Path
from typing import Dict


class ImageAnalyzer:
    """图片分析器 - 提取画质、风格、细节、构图等元数据"""

    def __init__(self):
        self._init_analyzer()

    def _init_analyzer(self):
        """初始化分析器（使用 vision 模型）"""
        try:
            import sys

            sys.path.insert(0, "/home/flybo/clawsjoy_v5")
            from skills.vision.scripts.main import execute as vision_execute

            self.vision_execute = vision_execute
            self.available = True
            print("✅ 图片分析器已初始化")
        except Exception as e:
            print(f"⚠️ 图片分析器初始化失败: {e}")
            self.available = False

    def analyze(self, image_base64: str) -> Dict:
        """分析图片，返回丰富的元数据"""
        if not self.available:
            return self._fallback_analysis()

        # 保存临时图片
        img_data = base64.b64decode(image_base64)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(img_data)
            temp_path = f.name

        try:
            # 多维度分析
            result = {
                "success": True,
                "quality": self._analyze_quality(temp_path),
                "style": self._analyze_style(temp_path),
                "subject": self._analyze_subject(temp_path),
                "composition": self._analyze_composition(temp_path),
                "color": self._analyze_color(temp_path),
                "details": self._analyze_details(temp_path),
                "summary": "",
            }
            result["summary"] = self._generate_summary(result)
            return result
        finally:
            Path(temp_path).unlink()

    def _analyze_quality(self, image_path: str) -> str:
        """分析画质"""
        prompt = (
            """分析这张图片的画质，只输出一个词：HD(高清)/SD(标清)/4K/8K/模糊/普通"""
        )
        result = self.vision_execute({"image_path": image_path, "prompt": prompt})
        return result.get("result", "普通")

    def _analyze_style(self, image_path: str) -> str:
        """分析风格"""
        prompt = """分析这张图片的风格，只输出风格名称：写实/动漫/油画/水彩/素描/像素/赛博朋克/中国风/科幻/梦幻"""
        result = self.vision_execute({"image_path": image_path, "prompt": prompt})
        return result.get("result", "写实")

    def _analyze_subject(self, image_path: str) -> str:
        """分析主体"""
        prompt = """分析这张图片的主体内容，用一句话描述（20字以内）"""
        result = self.vision_execute({"image_path": image_path, "prompt": prompt})
        return result.get("result", "未知主体")

    def _analyze_composition(self, image_path: str) -> str:
        """分析构图"""
        prompt = """分析这张图片的构图方式，只输出：居中/三分法/对称/对角线/引导线/框架/留白"""
        result = self.vision_execute({"image_path": image_path, "prompt": prompt})
        return result.get("result", "居中")

    def _analyze_color(self, image_path: str) -> str:
        """分析色调"""
        prompt = (
            """分析这张图片的色调，只输出：暖色调/冷色调/高饱和/低饱和/黑白/鲜艳/柔和"""
        )
        result = self.vision_execute({"image_path": image_path, "prompt": prompt})
        return result.get("result", "自然")

    def _analyze_details(self, image_path: str) -> str:
        """分析细节"""
        prompt = """分析这张图片的细节丰富程度，只输出：丰富/一般/简单"""
        result = self.vision_execute({"image_path": image_path, "prompt": prompt})
        return result.get("result", "一般")

    def _generate_summary(self, analysis: Dict) -> str:
        """生成摘要"""
        return f"{analysis['subject']}，{analysis['style']}风格，{analysis['quality']}画质，{analysis['composition']}构图，{analysis['color']}色调"

    def _fallback_analysis(self) -> Dict:
        """降级分析"""
        return {
            "success": False,
            "quality": "未知",
            "style": "未知",
            "subject": "未知",
            "composition": "未知",
            "color": "未知",
            "details": "未知",
            "summary": "分析器不可用",
        }


image_analyzer = ImageAnalyzer()
