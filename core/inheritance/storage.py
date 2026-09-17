#!/usr/bin/env python3
"""Storage - Storage 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .models import Experience, ExperienceChain


class ExperienceStorage:
    """经验存储管理器"""

    def __init__(self, user_id: str = "default", agent_name: str = "base"):
        self.user_id = user_id
        self.agent_name = agent_name
        self.base_path = Path(
            f"{config_helper.get_data_root()}/users/{user_id}/inheritance/{agent_name}"
        )
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 文件路径
        self.experience_file = self.base_path / "experiences.json"
        self.chains_file = self.base_path / "chains.json"

        # 缓存
        self._experiences: Dict[str, Experience] = {}
        self._chains: Dict[str, ExperienceChain] = {}

        self._load()

    def _load(self):
        """加载数据"""
        # 加载经验
        if self.experience_file.exists():
            try:
                with open(self.experience_file, "r") as f:
                    data = json.load(f)
                    for exp_id, exp_data in data.get("experiences", {}).items():
                        self._experiences[exp_id] = Experience.from_dict(exp_data)
            except Exception as e:
                print(f"加载经验失败: {e}")

        # 加载传承链
        if self.chains_file.exists():
            try:
                with open(self.chains_file, "r") as f:
                    data = json.load(f)
                    for chain_id, chain_data in data.get("chains", {}).items():
                        self._chains[chain_id] = ExperienceChain(
                            root_id=chain_data.get("root_id", ""),
                            chain=chain_data.get("chain", []),
                        )
            except Exception as e:
                print(f"加载传承链失败: {e}")

    def _save(self):
        """保存数据"""
        # 保存经验
        with open(self.experience_file, "w") as f:
            json.dump(
                {
                    "user_id": self.user_id,
                    "agent_name": self.agent_name,
                    "updated_at": datetime.now().isoformat(),
                    "experiences": {
                        exp_id: exp.to_dict()
                        for exp_id, exp in self._experiences.items()
                    },
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        # 保存传承链
        with open(self.chains_file, "w") as f:
            json.dump(
                {
                    "user_id": self.user_id,
                    "agent_name": self.agent_name,
                    "updated_at": datetime.now().isoformat(),
                    "chains": {
                        chain_id: chain.to_dict()
                        for chain_id, chain in self._chains.items()
                    },
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

    def save_experience(self, experience: Experience):
        """保存经验"""
        self._experiences[experience.id] = experience
        self._save()

    def get_experience(self, exp_id: str) -> Optional[Experience]:
        """获取经验"""
        return self._experiences.get(exp_id)

    def list_experiences(
        self, exp_type: str = None, min_confidence: float = 0.0
    ) -> List[Experience]:
        """列出经验"""
        experiences = list(self._experiences.values())
        if exp_type:
            experiences = [e for e in experiences if e.type == exp_type]
        if min_confidence > 0:
            experiences = [e for e in experiences if e.confidence >= min_confidence]
        return sorted(experiences, key=lambda e: e.confidence, reverse=True)

    def delete_experience(self, exp_id: str):
        """删除经验"""
        if exp_id in self._experiences:
            del self._experiences[exp_id]
            self._save()

    def record_usage(self, exp_id: str, success: bool):
        """记录使用结果"""
        exp = self._experiences.get(exp_id)
        if exp:
            exp.use_count += 1
            if success:
                exp.success_count += 1
            else:
                exp.fail_count += 1
            exp.confidence = exp.success_rate
            exp.updated_at = datetime.now().isoformat()
            exp.last_used = datetime.now().isoformat()
            self._save()

    def create_chain(self, root_id: str) -> str:
        """创建传承链"""
        chain_id = f"chain_{root_id}"
        self._chains[chain_id] = ExperienceChain(root_id=root_id, chain=[root_id])
        self._save()
        return chain_id

    def add_to_chain(self, chain_id: str, experience_id: str):
        """添加到传承链"""
        if chain_id in self._chains:
            self._chains[chain_id].add_link(experience_id)
            self._save()

    def get_chain(self, chain_id: str) -> Optional[ExperienceChain]:
        """获取传承链"""
        return self._chains.get(chain_id)
