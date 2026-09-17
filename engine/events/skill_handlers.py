"""技能事件处理器 - 复用系统 EventBus"""

import re
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)


class SkillEventHandlers:
    """技能事件处理器"""

    def __init__(self, skill_creator, skill_loader):
        self.skill_creator = skill_creator
        self.skill_loader = skill_loader
        self._query_counts = {}
        self._register_handlers()
        print("🎯 技能事件处理器已注册")

    def _register_handlers(self):
        """注册事件处理器到系统 EventBus"""
        from core.lib.event_bus import event_bus

        event_bus.on("skill:missing", self.on_skill_missing)
        event_bus.on("query:repeated", self.on_repeated_query)
        event_bus.on("skill:suggest", self.on_skill_suggest)
        event_bus.on("skill:created", self.on_skill_created)

        print(
            "   ✅ 已注册事件: skill:missing, query:repeated, skill:suggest, skill:created"
        )

    def on_skill_missing(self, event: str, data: Dict = None):
        if not data:
            return
        query = data.get("query", "")
        if self._should_create_skill(query):
            result = self._auto_create_skill(query)
            print(f"📢 自动创建技能: {result.get('skill_name', '')}")

    def on_repeated_query(self, event: str, data: Dict = None):
        if not data:
            return
        query = data.get("query", "")
        user_id = data.get("user_id", "")

        key = f"{user_id}:{query}"
        self._query_counts[key] = self._query_counts.get(key, 0) + 1

        if self._query_counts[key] >= 3:
            print(f"📊 重复查询 ({self._query_counts[key]}次): {query[:30]}...")
            self._auto_create_skill(query)

    def on_skill_suggest(self, event: str, data: Dict = None):
        if not data:
            return
        name = data.get("name", "")
        description = data.get("description", "")
        if name and description:
            result = self.skill_creator.create_from_description(name, description)
            print(f"📢 创建建议技能: {name}")

    def on_skill_created(self, event: str, data: Dict = None):
        if not data:
            return
        skill_name = data.get("skill_name", "")
        if self.skill_loader:
            self.skill_loader.reload()
        print(f"✨ 新技能已生效: {skill_name}")

    def _should_create_skill(self, query: str) -> bool:
        if len(query) < 5 or len(query) > 100:
            return False
        if self.skill_loader and query in self.skill_loader.skills:
            return False
        return True

    def _auto_create_skill(self, query: str) -> Dict:
        skill_name = self._generate_skill_name(query)
        category = self._infer_category(query)

        result = self.skill_creator.create_from_description(
            name=skill_name, description=f"自动生成: {query}", category=category
        )

        if result.get("success"):
            from core.lib.event_bus import event_bus

            event_bus.emit(
                "skill:created", {"skill_name": skill_name, "source_query": query}
            )

        return result

    def _generate_skill_name(self, query: str) -> str:
        import re

        words = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", query)
        if words:
            name = "_".join(words[:3])
        else:
            name = f"auto_{int(datetime.now().timestamp())}"
        return name[:50].lower()

    def _infer_category(self, query: str) -> str:
        categories = {
            "code": ["代码", "编程", "写", "python"],
            "weather": ["天气", "气温"],
            "translate": ["翻译"],
            "video": ["视频", "剪辑"],
            "image": ["图片", "图像"],
        }
        for cat, keywords in categories.items():
            if any(kw in query for kw in keywords):
                return cat
        return "general"


def init_skill_handlers(skill_creator, skill_loader):
    """初始化技能事件处理器"""
    return SkillEventHandlers(skill_creator, skill_loader)
