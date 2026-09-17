"""免费图片 API - 使用 Unsplash 开源图片 + 占位图"""

import urllib.parse
import random


class FreeImageAPI:
    def __init__(self):
        # 可爱的动物图片集合（Unsplash 开源图片）
        self.cat_images = [
            "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba",
            "https://images.unsplash.com/photo-1574158622682-e40e69881006",
            "https://images.unsplash.com/photo-1533743983669-94fa5c4338ec",
            "https://images.unsplash.com/photo-1495360010541-f04d4f5c5c6a",
        ]
        self.dog_images = [
            "https://images.unsplash.com/photo-1548199973-03cce0bbc87b",
            "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e",
        ]
    
    def get_image_url(self, prompt: str) -> dict:
        prompt_lower = prompt.lower()
        
        # 根据提示词返回相关图片
        if "猫" in prompt_lower or "cat" in prompt_lower:
            url = random.choice(self.cat_images)
        elif "狗" in prompt_lower or "dog" in prompt_lower:
            url = random.choice(self.dog_images)
        else:
            # 使用通用占位图
            encoded = urllib.parse.quote(prompt[:30])
            url = f"https://placehold.co/512x512/6366f1/white?text={encoded}"
        
        # 添加尺寸参数
        if "unsplash" in url:
            url = f"{url}?w=512&h=512&fit=crop"
        
        return {
            "success": True,
            "url": url,
            "response": f"![{prompt}]({url})"
        }


free_api = FreeImageAPI()
