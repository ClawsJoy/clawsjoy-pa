#!/usr/bin/env python3
"""Skill Deps - Skill Deps 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

"""技能依赖关系 - 自动推断组合顺序"""
import json
from pathlib import Path


class SkillDependency:
    def __init__(self):
        self.deps_file = Path(f"{get_data_root()}/skill_stats/dependencies.json")
        self._load()

    def _load(self):
        if self.deps_file.exists():
            with open(self.deps_file, "r") as f:
                self.deps = json.load(f)
        else:
            # 预定义依赖关系
            self.deps = {
                # 数据处理流程
                "read_file": ["parse_csv", "filter_list", "sort_list"],
                "parse_csv": ["filter_list", "statistics"],
                "filter_list": ["sort_list", "statistics"],
                # 视频制作流程
                "manju_maker": ["add_subtitles", "video_uploader"],
                "complete_video_maker": ["add_subtitles"],
                "video_composer": ["ffmpeg_video"],
                # 文本处理流程
                "count_words": ["extract_keywords"],
                "split_text": ["filter_list"],
                # 日程管理流程
                "add_event": ["list_events", "set_reminder"],
                "add_todo": ["list_todos", "complete_todo"],
            }

    def get_dependencies(self, skill: str) -> list:
        """获取技能的前置依赖"""
        return self.deps.get(skill, [])

    def get_chain(self, target: str) -> list:
        """获取完整执行链"""
        chain = []
        deps = self.get_dependencies(target)
        for dep in deps:
            chain.extend(self.get_chain(dep))
            chain.append(dep)
        chain.append(target)
        return list(dict.fromkeys(chain))  # 去重保持顺序

    def learn_dependency(self, parent: str, child: str):
        """从执行历史学习依赖关系"""
        if parent not in self.deps:
            self.deps[parent] = []
        if child not in self.deps[parent]:
            self.deps[parent].append(child)
            self._save()

    def _save(self):
        self.deps_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.deps_file, "w") as f:
            json.dump(self.deps, f, indent=2)


skill_deps = SkillDependency()
