"""技能矩阵引擎 - 整合原有成熟系统"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.lib.logger import engine_logger


class SkillMatrixEngine:
    """技能矩阵引擎 - 整合原有 skill_loader, skill_matching"""

    def __init__(self):
        self.skills = {}
        self.skill_loader = None
        self.keyword_mapping = {}
        self._init_components()
        self._load_keyword_mapping()
        self._load_all_skills()
        engine_logger.get().info(f"🎯 技能矩阵引擎已初始化，管理 {len(self.skills)} 个技能")

    def _init_components(self):
        try:
            from core.lib.skill_loader_v3 import skill_loader

            self.skill_loader = skill_loader
        except Exception as e:
            engine_logger.get().warning(f"skill_loader 加载失败: {e}")

    def _load_keyword_mapping(self):
        """从统一配置加载关键词映射"""
        keyword_mapping = {}

        config_path = Path("config/keywords.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    import yaml

                    config = yaml.safe_load(f)
                    skills = config.get("intents", {})
                    for skill_name, skill_config in skills.items():
                        keywords = skill_config.get("keywords", [])
                        for keyword in keywords:
                            if keyword not in keyword_mapping:
                                keyword_mapping[keyword] = []
                            keyword_mapping[keyword].append(skill_name)
            except Exception as e:
                print(f"从统一配置加载关键词失败: {e}")

        self.keyword_mapping = keyword_mapping
        print(f"✅ 加载了 {len(keyword_mapping)} 个关键词映射")

    def _load_all_skills(self):
        if self.skill_loader:
            try:
                skills_dict = self.skill_loader.list_skills()
                for name in skills_dict:
                    self.skills[name] = {
                        "name": name,
                        "category": self._infer_category(name),
                        "source": "skill_loader",
                    }
            except Exception as e:
                pass

        skills_dir = Path("skills")
        if skills_dir.exists():
            for d in skills_dir.iterdir():
                if d.is_dir() and not d.name.startswith("_"):
                    if d.name not in self.skills:
                        self.skills[d.name] = {
                            "name": d.name,
                            "category": self._infer_category(d.name),
                            "source": "skills/",
                        }

    def _infer_category(self, skill_name: str) -> str:
        name_lower = skill_name.lower()
        category_map = {
            "code": ["code", "python", "编程"],
            "video": ["video", "视频"],
            "image": ["image", "图片"],
            "weather": ["weather", "天气"],
            "translate": ["translate", "翻译"],
        }
        for cat, keywords in category_map.items():
            if any(kw in name_lower for kw in keywords):
                return cat
        return "general"

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if isinstance(input_data, str):
            return self.search(input_data, kwargs.get("top_k", 5))
        return self.search(str(input_data))

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        query_lower = query.lower()
        scores = {}

        for keyword, agents in self.keyword_mapping.items():
            if keyword in query_lower or query_lower in keyword:
                for agent in agents:
                    scores[agent] = scores.get(agent, 0) + 10

        for name, info in self.skills.items():
            if query_lower in name.lower():
                scores[name] = scores.get(name, 0) + 5

        sorted_results = sorted(scores.items(), key=lambda x: -x[1])
        return [{"name": name, "score": score} for name, score in sorted_results[:top_k]]

    def search_skills(self, query: str, top_k: int = 5) -> List[Dict]:
        return self.search(query, top_k)

    def get_stats(self) -> Dict:
        return {"skills": len(self.skills), "status": "active"}

    def reload(self) -> Dict:
        if self.skill_loader and hasattr(self.skill_loader, "reload"):
            self.skill_loader.reload()
        self.skills = {}
        self._load_all_skills()
        return {"success": True, "message": f"Reloaded {len(self.skills)} skills"}

    def health_check(self) -> Dict:
        return {"name": "skill_matrix", "status": "healthy"}


skill_matrix_engine = SkillMatrixEngine()
