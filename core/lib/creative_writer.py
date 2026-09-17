"""创意写作增强器"""

import random

class CreativeWriter:
    """增强创意写作能力"""
    
    # 故事模板
    STORY_TEMPLATES = {
        "friendship": {
            "characters": ["机器人", "小女孩", "老爷爷", "小动物"],
            "conflicts": ["孤独", "误解", "离别", "困难"],
            "resolutions": ["理解", "陪伴", "重逢", "成功"]
        },
        "adventure": {
            "characters": ["探险家", "魔法师", "少年", "骑士"],
            "conflicts": ["寻找宝藏", "拯救世界", "解开谜题", "战胜邪恶"],
            "resolutions": ["成功归来", "获得力量", "真相大白", "和平降临"]
        }
    }
    
    @staticmethod
    def enhance_story_prompt(theme: str, length: int = 200) -> str:
        """增强故事提示词"""
        prompt = f"""请写一个{theme}主题的微型小说，{length}字左右。

要求：
1. 开头要有悬念或吸引人的场景
2. 中间有转折或冲突
3. 结尾有反转或寓意
4. 人物形象生动
5. 语言简洁有力

故事结构：
- 开头（20%）：设置场景和人物
- 发展（50%）：冲突发展
- 高潮（20%）：关键转折
- 结尾（10%）：寓意升华

请开始创作："""
        return prompt
    
    @staticmethod
    def enhance_poetry_prompt(style: str, topic: str) -> str:
        """增强诗歌提示词"""
        prompt = f"""请写一首关于{topic}的{style}诗。

要求：
- 意境优美
- 押韵工整
- 情感真挚
- 意象独特

示例格式（五言绝句）：
____ ____ __
____ ____ __
____ ____ __
____ ____ __

请创作："""
        return prompt

creative_writer = CreativeWriter()
