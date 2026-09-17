#!/usr/bin/env python3
"""Center - Center 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from typing import Dict, List, Optional

"""私人管家俱乐部 - 智能驱动配置"""

import json
from datetime import datetime
from pathlib import Path

import yaml


class ButlerClub:
    """私人管家俱乐部"""

    def __init__(self):
        self.config = self._load_config()
        # 数据目录
        self.data_root = Path("data/butler_club")
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.stats_file = self.data_root / "stats.json"
        self._load_stats()
        print("✅ ButlerClub 初始化完成")

    def _load_config(self) -> Dict:
        """加载俱乐部配置"""
        config_path = Path("config/butler_club.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"加载配置失败: {e}")
        return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "membership_levels": [
                {"name": "bronze", "min_interactions": 0, "color": "#CD7F32"},
                {"name": "silver", "min_interactions": 100, "color": "#C0C0C0"},
                {"name": "gold", "min_interactions": 500, "color": "#FFD700"},
                {"name": "diamond", "min_interactions": 2000, "color": "#B9F2FF"},
            ],
            "settings": {
                "default_butler_name": "小管",
                "max_rename_history": 10,
                "auto_upgrade": True,
            },
        }

    def _load_stats(self):
        """加载统计数据"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    self.stats = json.load(f)
            except Exception as e:
                print(f"加载统计失败: {e}")
                self._init_stats()
        else:
            self._init_stats()

    def _init_stats(self):
        """初始化统计数据"""
        self.stats = {
            "total_members": 0,
            "total_butlers": 0,
            "total_interactions": 0,
            "level_distribution": {"bronze": 0, "silver": 0, "gold": 0, "diamond": 0},
            "most_popular_name": "小管",
            "updated_at": datetime.now().isoformat(),
        }
        self._save_stats()
        self._update_member_vector(user_id)
        self._add_member_vector(user_id)

    def _save_stats(self):
        """保存统计数据"""
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存统计失败: {e}")

    def get_stats(self) -> Dict:
        """获取俱乐部统计"""
        return self.stats

    def get_member(self, user_id: str) -> Optional[Dict]:
        """获取会员信息"""
        profile_file = self.data_root / f"members/{user_id}/profile.json"
        if profile_file.exists():
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def register_member(self, user_id: str, butler_name: str = None) -> Dict:
        """注册会员"""
        if butler_name is None:
            butler_name = self.config.get("settings", {}).get(
                "default_butler_name", "小管"
            )

        # 检查是否已存在
        if self.get_member(user_id):
            return {"success": False, "message": "会员已存在"}

        profile_dir = self.data_root / f"members/{user_id}"
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_file = profile_dir / "profile.json"

        profile = {
            "user_id": user_id,
            "joined_at": datetime.now().isoformat(),
            "membership_level": "bronze",
            "total_interactions": 0,
            "butler_name": butler_name,
            "rename_history": [],
            "achievements": [],
        }

        with open(profile_file, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        self.stats["total_members"] += 1
        self.stats["total_butlers"] += 1
        self.stats["level_distribution"]["bronze"] += 1
        self._save_stats()
        self._update_member_vector(user_id)
        self._add_member_vector(user_id)

        return {"success": True, "user_id": user_id, "butler_name": butler_name}

    def record_interaction(self, user_id: str):
        """记录交互"""
        member = self.get_member(user_id)
        if member:
            member["total_interactions"] += 1
            self._check_level_upgrade(member)
            profile_file = self.data_root / f"members/{user_id}/profile.json"
            with open(profile_file, "w", encoding="utf-8") as f:
                json.dump(member, f, indent=2, ensure_ascii=False)
            self.stats["total_interactions"] += 1
            self._save_stats()
            self._update_member_vector(user_id)
        self._add_member_vector(user_id)

    def _check_level_upgrade(self, member: Dict):
        """检查等级升级"""
        interactions = member["total_interactions"]
        current = member["membership_level"]

        levels = self.config.get(
            "membership_levels",
            [
                {"name": "bronze", "min_interactions": 0},
                {"name": "silver", "min_interactions": 100},
                {"name": "gold", "min_interactions": 500},
                {"name": "diamond", "min_interactions": 2000},
            ],
        )

        # 找到适合的等级（从高到低）
        new_level = current
        for level in reversed(levels):
            if interactions >= level.get("min_interactions", 0):
                new_level = level["name"]
                break

        if new_level != current:
            # 升级
            old_level = current
            member["membership_level"] = new_level
            member["achievements"].append(
                {
                    "name": f"upgrade_to_{new_level}",
                    "earned_at": datetime.now().isoformat(),
                }
            )
            # 更新统计
            if old_level in self.stats["level_distribution"]:
                self.stats["level_distribution"][old_level] -= 1
            if new_level in self.stats["level_distribution"]:
                self.stats["level_distribution"][new_level] += 1
            print(f"🎉 会员 {member['user_id']} 升级到 {new_level}！")

    # ==================== 向量服务集成 ====================

    def _init_vector_service(self):
        """初始化向量服务"""
        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center

            self.vector_service = vector_knowledge_center
            self.vector_enabled = True
            print(f"✅ 俱乐部向量服务已启用")
            # 统计现有会员向量
            stats = self.vector_service.get_member_vector_stats()
            if stats.get("count", 0) > 0:
                print(f"   📊 已有 {stats['count']} 个会员向量")
        except Exception as e:
            self.vector_enabled = False
            print(f"⚠️ 向量服务不可用: {e}")

    def _add_member_vector(self, user_id: str):
        """添加会员向量"""
        if not self.vector_enabled:
            return

        member = self.get_member(user_id)
        if not member:
            return

        # 准备会员特征
        metadata = {
            "butler_name": member.get("butler_name", "小管"),
            "level": member.get("membership_level", "bronze"),
            "interactions": member.get("total_interactions", 0),
            "achievements": len(member.get("achievements", [])),
            "tags": self._extract_member_tags(member),
        }

        self.vector_service.add_member(user_id, metadata)

    def _update_member_vector(self, user_id: str):
        """更新会员向量"""
        if not self.vector_enabled:
            return

        member = self.get_member(user_id)
        if not member:
            return

        metadata = {
            "butler_name": member.get("butler_name", "小管"),
            "level": member.get("membership_level", "bronze"),
            "interactions": member.get("total_interactions", 0),
            "achievements": len(member.get("achievements", [])),
        }

        self.vector_service.update_member(user_id, metadata)

    def _extract_member_tags(self, member: Dict) -> list:
        """从会员数据中提取标签"""
        tags = []

        # 基于等级
        level = member.get("membership_level", "bronze")
        tags.append(f"等级_{level}")

        # 基于交互次数
        interactions = member.get("total_interactions", 0)
        if interactions > 1000:
            tags.append("高频用户")
        elif interactions > 100:
            tags.append("活跃用户")
        else:
            tags.append("新用户")

        # 基于成就
        achievements = member.get("achievements", [])
        if len(achievements) >= 5:
            tags.append("成就达人")

        return tags

    def find_similar_members(self, user_id: str, top_k: int = 5) -> List[Dict]:
        """找到相似会员（基于向量相似度）"""
        if not self.vector_enabled:
            print("⚠️ 向量服务未启用")
            return []

        similar = self.vector_service.search_similar_members(user_id, top_k)

        # 补充会员详细信息
        for s in similar:
            member = self.get_member(s.get("user_id"))
            if member:
                s["butler_name"] = member.get("butler_name", "小管")
                s["level"] = member.get("membership_level", "bronze")
                s["joined_at"] = member.get("joined_at", "")

        return similar

    def search_members_by_query(self, query: str, top_k: int = 10) -> List[Dict]:
        """根据查询文本检索会员"""
        if not self.vector_enabled:
            return []

        return self.vector_service.search_members(query, top_k)

    def recommend_butler_style(self, user_id: str) -> str:
        """基于相似会员推荐管家风格"""
        similar = self.find_similar_members(user_id, 3)
        if not similar:
            return "小管"

        # 统计相似会员的管家名称偏好
        name_counts = {}
        for s in similar:
            name = s.get("butler_name", "小管")
            name_counts[name] = name_counts.get(name, 0) + 1

        if name_counts:
            return max(name_counts, key=name_counts.get)
        return "小管"

    def rebuild_all_member_vectors(self) -> Dict:
        """重建所有会员向量（用于初始化或修复）"""
        if not self.vector_enabled:
            return {"success": False, "error": "向量服务未启用"}

        # 获取所有会员
        members_dir = self.data_root / "members"
        if not members_dir.exists():
            return {"success": False, "error": "无会员目录"}

        success_count = 0
        fail_count = 0

        for member_dir in members_dir.iterdir():
            if member_dir.is_dir():
                user_id = member_dir.name
                try:
                    self._add_member_vector(user_id)
                    success_count += 1
                except Exception as e:
                    print(f"重建失败 {user_id}: {e}")
                    fail_count += 1

        return {
            "success": True,
            "total": success_count + fail_count,
            "success_count": success_count,
            "fail_count": fail_count,
        }

    # ==================== 向量服务集成 ====================

    def _get_vector_service(self):
        """获取向量服务"""
        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center

            return vector_knowledge_center
        except Exception:
            return None

    def add_member_vector(self, user_id: str):
        """添加会员向量"""
        svc = self._get_vector_service()
        if not svc:
            return

        member = self.get_member(user_id)
        if not member:
            return

        svc.add_member(
            user_id,
            {
                "butler_name": member.get("butler_name", "小管"),
                "level": member.get("membership_level", "bronze"),
                "interactions": member.get("total_interactions", 0),
                "achievements": len(member.get("achievements", [])),
            },
        )

    def find_similar_members(self, user_id: str, top_k: int = 5) -> list:
        """找相似会员"""
        svc = self._get_vector_service()
        if not svc:
            return []
        return svc.search_members(user_id, top_k)


# 全局实例
butler_club = ButlerClub()
