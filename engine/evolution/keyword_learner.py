"""关键词自增量学习器 - 从用户交互中自动学习新关键词"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)


class KeywordLearner:
    """关键词自增量学习器"""

    def __init__(self):
        self.keyword_stats = defaultdict(
            lambda: {"count": 0, "last_seen": None, "context": []}
        )
        self.auto_keywords_file = Path("data/auto_learned_keywords.json")
        self.threshold = 3  # 出现3次自动学习
        self._load()
        print("🧠 关键词自增量学习器已初始化")

    def _load(self):
        if self.auto_keywords_file.exists():
            with open(self.auto_keywords_file, "r") as f:
                data = json.load(f)
                self.auto_keywords = data.get("learned_keywords", {})
                self.suggestions = data.get("suggestions", [])
        else:
            self.auto_keywords = {}
            self.suggestions = []

    def _save(self):
        with open(self.auto_keywords_file, "w") as f:
            json.dump(
                {
                    "learned_keywords": self.auto_keywords,
                    "suggestions": self.suggestions,
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def record_query(self, query: str, matched_skill: str, success: bool):
        """记录用户查询"""
        key = f"{query}|{matched_skill}"
        self.keyword_stats[key]["count"] += 1
        self.keyword_stats[key]["last_seen"] = datetime.now().isoformat()

        if success:
            self.keyword_stats[key]["context"].append({"query": query, "success": True})

        # 检查是否需要学习
        if self.keyword_stats[key]["count"] >= self.threshold:
            self._learn_keyword(query, matched_skill)

    def _learn_keyword(self, query: str, skill_name: str):
        """学习新关键词"""
        # 提取核心词
        words = self._extract_keywords(query)

        for word in words:
            key = f"{skill_name}:{word}"
            if key not in self.auto_keywords:
                self.auto_keywords[key] = {
                    "skill": skill_name,
                    "keyword": word,
                    "source_query": query,
                    "learned_at": datetime.now().isoformat(),
                    "hit_count": 0,
                }
                print(f"📚 自动学习关键词: '{word}' → {skill_name}")
            else:
                self.auto_keywords[key]["hit_count"] += 1

        self._save()

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 去除常见停用词
        stopwords = [
            "的",
            "了",
            "是",
            "在",
            "我",
            "有",
            "和",
            "就",
            "不",
            "也",
            "都",
            "说",
        ]
        words = []

        # 中文分词（简单实现）
        for i in range(len(text)):
            for j in range(i + 2, min(i + 5, len(text) + 1)):
                word = text[i:j]
                if len(word) >= 2 and word not in stopwords:
                    words.append(word)

        # 去重
        return list(set(words))[:5]

    def get_suggestions(self) -> List[Dict]:
        """获取建议添加的关键词"""
        suggestions = []
        for key, info in self.auto_keywords.items():
            if info.get("hit_count", 0) > 0:
                suggestions.append(
                    {
                        "skill": info["skill"],
                        "keyword": info["keyword"],
                        "source": info["source_query"],
                        "confidence": min(info["hit_count"] / 5, 1.0),
                    }
                )
        return suggestions

    def apply_to_engine(self, skill_matrix_engine):
        """将学习到的关键词应用到技能引擎"""
        applied = 0
        for key, info in self.auto_keywords.items():
            skill_name = info["skill"]
            keyword = info["keyword"]

            skill = skill_matrix_engine.skills.get(skill_name)
            if skill and keyword not in skill.keywords:
                skill.keywords.append(keyword)
                applied += 1

        if applied > 0:
            print(f"📚 应用了 {applied} 个自学习关键词到技能引擎")
        return applied


keyword_learner = KeywordLearner()
