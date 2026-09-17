"""向量索引自增量同步器 - 自动同步技能到向量库"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class VectorSyncEngine:
    """向量索引自增量同步器"""

    def __init__(self):
        self.sync_log = Path("data/vector_sync_log.json")
        self.last_sync = None
        self._load_log()
        print("🔄 向量同步引擎已初始化")

    def _load_log(self):
        if self.sync_log.exists():
            with open(self.sync_log, "r") as f:
                data = json.load(f)
                self.last_sync = data.get("last_sync")
                self.synced_count = data.get("synced_count", 0)
        else:
            self.last_sync = None
            self.synced_count = 0

    def _save_log(self):
        with open(self.sync_log, "w") as f:
            json.dump(
                {
                    "last_sync": datetime.now().isoformat(),
                    "synced_count": self.synced_count,
                },
                f,
                indent=2,
            )

    def sync_skills_to_vector(self, skill_matrix_engine, vector_center):
        """同步技能到向量库"""
        if not vector_center:
            print("⚠️ 向量中心不可用")
            return 0

        synced = 0
        for skill_name, skill in skill_matrix_engine.skills.items():
            try:
                # 构建技能描述文本
                text = f"{skill_name} {skill.category} {' '.join(skill.keywords)}"

                # 检查是否需要更新
                doc_id = f"skill_{skill_name}"

                # 添加到向量库
                vector_center.add_document(
                    doc_id=doc_id,
                    content=text,
                    metadata={
                        "type": "skill",
                        "name": skill_name,
                        "category": skill.category,
                        "keywords": skill.keywords,
                        "updated_at": datetime.now().isoformat(),
                    },
                    collection="skills",
                )
                synced += 1
            except Exception as e:
                print(f"  同步 {skill_name} 失败: {e}")

        self.synced_count = synced
        self._save_log()
        print(f"✅ 已同步 {synced} 个技能到向量索引")
        return synced

    def incremental_sync(
        self, skill_matrix_engine, vector_center, new_skills: List[str]
    ):
        """增量同步新技能"""
        synced = 0
        for skill_name in new_skills:
            skill = skill_matrix_engine.skills.get(skill_name)
            if skill:
                try:
                    text = f"{skill_name} {skill.category} {' '.join(skill.keywords)}"
                    vector_center.add_document(
                        doc_id=f"skill_{skill_name}",
                        content=text,
                        metadata={
                            "type": "skill",
                            "name": skill_name,
                            "category": skill.category,
                            "keywords": skill.keywords,
                        },
                        collection="skills",
                    )
                    synced += 1
                except Exception as e:
                    pass

        print(f"✅ 增量同步 {synced} 个新技能")
        return synced


vector_sync = VectorSyncEngine()
