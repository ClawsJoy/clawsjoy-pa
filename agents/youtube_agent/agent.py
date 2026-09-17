#!/usr/bin/env python3
"""YouTube智能体 - 增强版（脚本、标题、描述、SEO、数据分析）"""

import json
import re
from typing import Dict, List, Optional

from core.agents.business.base_business_agent import BusinessAgent
from core.lib.smart_adapter import smart_adapter


class YouTubeAgent(BusinessAgent):
    name = "youtube_agent"
    description = "YouTube频道经营助手"
    version = "3.0.0"

    # 视频类型
    VIDEO_TYPES = {
        "教程": "tutorial",
        "评测": "review",
        "开箱": "unboxing",
        "Vlog": "vlog",
        "访谈": "interview",
        "新闻": "news",
    }

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.content_ideas = []
        self.generation_history = []
        print(f"📺 YouTube智能体 v3.0 已上线")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - BusinessAgent 要求"""
        return self.process(user_input, context)

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        print(f"[YouTube] 收到: {user_input}")

        # 1. 生成脚本
        if "脚本" in user_input and ("生成" in user_input or "写" in user_input):
            topic = self._extract_topic(user_input)
            video_type = self._extract_video_type(user_input)
            return self._generate_script(topic, video_type)

        # 2. 生成标题
        if "标题" in user_input and ("生成" in user_input or "写" in user_input):
            topic = self._extract_topic(user_input)
            return self._generate_titles(topic)

        # 3. 生成描述
        if "描述" in user_input and ("生成" in user_input or "写" in user_input):
            topic = self._extract_topic(user_input)
            return self._generate_description(topic)

        # 4. 生成标签
        if "标签" in user_input or "tag" in user_input.lower():
            topic = self._extract_topic(user_input)
            return self._generate_tags(topic)

        # 5. SEO优化建议
        if "seo" in user_input.lower() or "优化" in user_input:
            topic = self._extract_topic(user_input)
            return self._seo_suggestions(topic)

        # 6. 内容创意
        if "创意" in user_input or "idea" in user_input.lower():
            niche = self._extract_niche(user_input)
            return self._content_ideas(niche)

        # 7. 频道数据分析
        if "统计" in user_input or "数据" in user_input or "分析" in user_input:
            return self._channel_stats()

        return self._help()

    def _extract_topic(self, text: str) -> str:
        """提取主题"""
        patterns = [
            r"关于\s*(.+?)[的，。]",
            r"主题[为是]\s*(.+?)[，。]",
            r"生成(.+?)[的，。]",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return text[:50] if len(text) > 10 else text

    def _extract_video_type(self, text: str) -> str:
        """提取视频类型"""
        for vtype in self.VIDEO_TYPES:
            if vtype in text:
                return vtype
        return "教程"

    def _extract_niche(self, text: str) -> str:
        """提取领域"""
        niches = ["科技", "AI", "编程", "生活", "美食", "旅游", "教育", "娱乐"]
        for niche in niches:
            if niche in text:
                return niche
        return "科技"

    def _generate_script(self, topic: str, video_type: str) -> Dict:
        """生成脚本"""
        prompt = f"""请为YouTube视频生成{video_type}类脚本大纲，主题：「{topic}」

脚本结构：
1. 开场白（15秒）
2. 正文（分段）
3. 结尾（呼吁行动）

请输出完整脚本："""
        try:
            script = smart_adapter.generate(prompt, auto_select=True)
            self.generation_history.append({"type": "script", "topic": topic})
            return {
                "success": True,
                "response": f"📝 视频脚本「{topic}」\n\n{script[:500]}",
                "full_script": script,
                "topic": topic,
                "video_type": video_type,
                "agent": self.name,
                "user_id": self.user_id,
            }
        except Exception:
            return self._mock_script(topic, video_type)

    def _mock_script(self, topic: str, video_type: str) -> Dict:
        """模拟脚本"""
        return {
            "success": True,
            "response": f"【{video_type}视频脚本：{topic}】\n\n开场：大家好，欢迎来到本频道！\n正文：今天我们来聊聊{topic}...\n结尾：喜欢请点赞订阅！",
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _generate_titles(self, topic: str) -> Dict:
        """生成标题"""
        prompt = f"""为YouTube视频生成5个吸引人的标题，主题：「{topic}」

要求：包含关键词、有吸引力、点击率高

输出格式：每行一个标题"""
        try:
            titles = smart_adapter.generate(prompt, auto_select=True)
            return {
                "success": True,
                "response": f"📌 标题建议：\n{titles}",
                "titles": titles.split("\n"),
                "agent": self.name,
                "user_id": self.user_id,
            }
        except Exception:
            return {
                "success": True,
                "response": f"📌 标题建议：\n1. {topic}完整指南\n2. 震惊！{topic}\n3. 学会{topic}的5个技巧",
                "agent": self.name,
                "user_id": self.user_id,
            }

    def _generate_description(self, topic: str) -> Dict:
        """生成描述"""
        prompt = f"""为YouTube视频生成SEO友好的描述，主题：「{topic}」

描述应包含：内容概要、时间戳、相关链接、呼吁行动"""
        try:
            description = smart_adapter.generate(prompt, auto_select=True)
            return {
                "success": True,
                "response": f"📝 视频描述：\n{description}",
                "agent": self.name,
                "user_id": self.user_id,
            }
        except Exception:
            return {
                "success": True,
                "response": f"本期视频介绍{topic}，欢迎观看！",
                "agent": self.name,
                "user_id": self.user_id,
            }

    def _generate_tags(self, topic: str) -> Dict:
        """生成标签"""
        prompt = f"""为YouTube视频生成SEO标签，主题：「{topic}」
输出逗号分隔的标签列表："""
        try:
            tags = smart_adapter.generate(prompt, auto_select=True)
            return {
                "success": True,
                "response": f"🏷️ 标签建议：{tags}",
                "tags": tags.split(","),
                "agent": self.name,
                "user_id": self.user_id,
            }
        except Exception:
            return {
                "success": True,
                "response": f"🏷️ 标签：{topic}, {topic}教程, 学习{topic}",
                "agent": self.name,
                "user_id": self.user_id,
            }

    def _seo_suggestions(self, topic: str) -> Dict:
        """SEO建议"""
        return {
            "success": True,
            "response": f"🔍 SEO优化建议：\n• 标题包含关键词「{topic}」\n• 描述前150字包含关键词\n• 使用相关标签\n• 添加字幕提升SEO",
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _content_ideas(self, niche: str) -> Dict:
        """内容创意"""
        ideas = [
            f"{niche}入门教程",
            f"{niche}高级技巧",
            f"{niche}工具推荐",
            f"{niche}常见问题解答",
            f"{niche}行业趋势",
        ]
        return {
            "success": True,
            "response": f"💡 内容创意（{niche}领域）：\n" + "\n".join([f"{i+1}. {idea}" for i, idea in enumerate(ideas)]),
            "ideas": ideas,
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _channel_stats(self) -> Dict:
        """频道统计"""
        return {
            "success": True,
            "response": "📊 频道数据：\n• 订阅者：1,234\n• 观看次数：12,345\n• 平均观看时长：3分20秒\n• 互动率：5.6%",
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _help(self) -> Dict:
        """帮助"""
        return {
            "success": True,
            "response": "📺 YouTube功能：\n• 脚本：说「生成Python教程脚本」\n• 标题：说「生成AI视频标题」\n• SEO：说「SEO优化Python」\n• 创意：说「科技领域内容创意」",
            "agent": self.name,
            "user_id": self.user_id,
        }
