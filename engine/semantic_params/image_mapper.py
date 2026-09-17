"""图像生成的语义参数映射"""

import re


class ImageParamMapper:
    """自然语言到图像生成参数的映射"""

    STYLE_MAP = {
        "写实": "photorealistic",
        "动漫": "anime style",
        "卡通": "cartoon style",
        "油画": "oil painting",
        "水彩": "watercolor",
        "素描": "sketch",
        "像素": "pixel art",
        "赛博朋克": "cyberpunk",
        "水墨": "ink wash",
        "中国风": "chinese traditional",
        "梦幻": "dreamlike",
        "科幻": "sci-fi",
    }

    SIZE_MAP = {
        "方形": "512x512",
        "竖屏": "512x768",
        "横屏": "768x512",
        "壁纸": "1920x1080",
        "高清": "1920x1080",
        "4k": "3840x2160",
    }

    def parse(self, user_input: str) -> dict:
        """解析自然语言，返回参数"""
        original = user_input
        params = {
            "prompt": user_input,
            "style": None,
            "size": "512x512",
            "quality": "standard",
        }

        # 提取风格（不修改 prompt）
        for cn, en in self.STYLE_MAP.items():
            if cn in user_input:
                params["style"] = en
                break

        # 提取尺寸
        for cn, size in self.SIZE_MAP.items():
            if cn in user_input:
                params["size"] = size
                break

        # 清理 prompt：只移除动作词，保留所有描述
        prompt = user_input
        for kw in ["生成", "画", "绘制", "一张", "图片", "图像"]:
            prompt = prompt.replace(kw, "")
        prompt = prompt.strip()

        params["prompt"] = prompt if prompt else original

        return params


if __name__ == "__main__":
    mapper = ImageParamMapper()
    tests = [
        "生成一只写实风格的猫",
        "画一张动漫风格的美少女",
        "生成超清壁纸，赛博朋克城市",
    ]
    for test in tests:
        result = mapper.parse(test)
        print(f"{test}")
        print(f"  → prompt: {result['prompt']}")
        print(f"  → style: {result['style']}, size: {result['size']}\n")
