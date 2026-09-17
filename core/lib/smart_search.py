#!/usr/bin/env python3
"""Smart Search - Smart Search 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""智能检索模块 - 配置驱动，优化检索准确性"""

import sys
from pathlib import Path
from typing import Dict, List

import yaml

from core.lib.unified_config import unified_config


class SmartSearch:
    """智能检索器 - 配置驱动"""

    def __init__(self):
        self._load_config()
        self._init_knowledge()

    def _load_config(self):
        """加载检索配置"""
        config_file = Path(__file__).parent.parent / "config/smart_search.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("smart_search", {})
        else:
            self.config = self._get_default_config()

    def _get_default_config(self):
        """默认配置"""
        return {
            "skill_categories": {
                "video": {
                    "keywords": [
                        "视频",
                        "video",
                        "制作",
                        "manju",
                        "漫剧",
                        "剪辑",
                        "合成",
                    ]
                },
                "image": {"keywords": ["图像", "image", "图片", "处理", "去背景"]},
                "math": {
                    "keywords": ["计算", "加法", "乘法", "除法", "平方", "绝对值"]
                },
                "text": {"keywords": ["文本", "处理", "转换", "大小写", "反转"]},
            },
            "skill_mapping": {
                "video": [
                    "manju_maker",
                    "complete_video_maker",
                    "video_uploader",
                    "video_composer",
                    "llm_video_maker",
                    "ffmpeg_video",
                ],
                "image": ["ai_image", "remove_bg", "image_slideshow"],
                "math": ["add", "sqrt", "abs", "mod", "divide", "power", "multiply"],
            },
        }

    def _init_knowledge(self):
        """初始化知识库连接"""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.lib.agent_knowledge import agent_knowledge

            self.agent_knowledge = agent_knowledge
            print("✅ 知识库连接成功")
        except Exception as e:
            self.agent_knowledge = None
            print(f"⚠️ 知识库不可用: {e}")

    def classify_query(self, query: str) -> str:
        """分类查询意图"""
        query_lower = query.lower()
        categories = self.config.get("skill_categories", {})

        for category, info in categories.items():
            for kw in info.get("keywords", []):
                if kw in query_lower:
                    return category
        return "general"

    def get_skills_by_category(self, category: str) -> List[str]:
        """获取指定分类的技能列表"""
        return self.config.get("skill_mapping", {}).get(category, [])

    def search(self, query: str, n: int = 5) -> List[Dict]:
        """智能检索"""
        category = self.classify_query(query)

        # 获取该分类的技能列表
        skills = self.get_skills_by_category(category)

        if skills:
            results = []
            for skill_name in skills[:n]:
                results.append(
                    {
                        "collection": "skills",
                        "content": f"技能: {skill_name}\n分类: {category}\n这是 {category} 类技能，用于相关任务",
                        "metadata": {"skill_name": skill_name, "category": category},
                    }
                )
            return results

        return []

    def search_skills(
        self, query: str = "", category: str = None, n: int = 5
    ) -> List[Dict]:
        """按分类检索技能"""
        if category:
            skills = self.get_skills_by_category(category)
            return [
                {
                    "collection": "skills",
                    "content": f"技能: {s}\n分类: {category}",
                    "metadata": {"skill_name": s, "category": category},
                }
                for s in skills[:n]
            ]

        return self.search(query, n)


smart_search = SmartSearch()
