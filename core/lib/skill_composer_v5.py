#!/usr/bin/env python3
"""Skill Composer V5 - Skill Composer V5 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""技能组合指引器 v5.0.0 - 增强意图匹配"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SkillCapability:
    """技能能力描述"""

    name: str
    description: str
    use_when: List[str] = field(default_factory=list)
    not_for: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    security_grade: str = "A"


class SkillComposer:
    """技能组合指引器 - 增强意图匹配"""

    VERSION = "5.0.0"

    # 预定义的技能关键词映射
    SKILL_KEYWORDS = {
        "ai-image-gen": [
            "图片",
            "图像",
            "生成",
            "绘画",
            "画图",
            "image",
            "picture",
            "generate",
        ],
        "video": ["视频", "影片", "编辑", "剪辑", "video", "edit"],
        "scheduler": ["定时", "调度", "周期", "每天", "定时任务", "schedule", "cron"],
        "text": ["文本", "文字", "字符串", "处理", "text", "string"],
        "data": ["数据", "分析", "统计", "data", "analyze"],
        "memory": ["记忆", "存储", "回忆", "记住", "memory", "recall"],
        "network": ["网络", "请求", "http", "调用", "network", "request"],
        "file_service_skill": ["文件", "读写", "保存", "file", "read", "write"],
        "video_description": ["描述", "文案", "解说", "description"],
        "video_public": ["发布", "上传", "分享", "publish", "upload"],
        "check_video_status": ["状态", "检查", "就绪", "status", "check"],
        "improve_executor": ["优化", "性能", "提升", "improve"],
        "audio": ["音频", "声音", "语音", "audio", "voice"],
        "core": ["核心", "基础", "core"],
        "doc": ["文档", "报告", "doc", "document"],
        "image": ["图像", "图片处理", "image"],
        "math": ["数学", "计算", "math", "calculate"],
        "self_heal": ["修复", "自愈", "错误", "heal", "fix"],
        "tools": ["工具", "辅助", "tools"],
        "wrappers": ["包装", "适配", "wrapper"],
    }

    def __init__(self, skills_path: Path = None):
        self.skills_path = skills_path or Path("skills")
        self.skills: Dict[str, SkillCapability] = {}
        self._load_all_skills()

    def _load_all_skills(self):
        """加载所有技能的能力描述"""
        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("__"):
                continue

            # 获取预定义关键词
            keywords = self.SKILL_KEYWORDS.get(skill_dir.name, [skill_dir.name])

            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 2:
                            metadata = unified_config.get("skill_metadata", {})

                            use_when = metadata.get("use_when", "")
                            not_for = metadata.get("not_for", "")

                            # 从 use_when 中提取额外关键词
                            extra_keywords = []
                            if use_when:
                                for word in use_when.replace(",", " ").split():
                                    if len(word) > 1:
                                        extra_keywords.append(word.lower())

                            all_keywords = list(set(keywords + extra_keywords))

                            self.skills[skill_dir.name] = SkillCapability(
                                name=skill_dir.name,
                                description=metadata.get("description", "")[:200],
                                use_when=(
                                    [
                                        u.strip()
                                        for u in use_when.split("\n")
                                        if u.strip()
                                    ]
                                    if use_when
                                    else []
                                ),
                                not_for=(
                                    [
                                        n.strip()
                                        for n in not_for.split("\n")
                                        if n.strip()
                                    ]
                                    if not_for
                                    else []
                                ),
                                keywords=all_keywords,
                                dependencies=metadata.get("dependencies", []),
                                security_grade=metadata.get("security_grade", "A"),
                            )
                except Exception as e:
                    logger.warning(f"Failed to load {skill_dir.name}: {e}")
            else:
                # 没有 SKILL.md 时使用默认
                self.skills[skill_dir.name] = SkillCapability(
                    name=skill_dir.name,
                    description=f"{skill_dir.name} skill",
                    keywords=keywords,
                    security_grade="A",
                )

    def find_skills_for_intent(self, intent: str) -> List[tuple]:
        """根据意图匹配技能，返回 (技能名, 匹配分数)"""
        intent_lower = intent.lower()
        matches = []

        for name, skill in self.skills.items():
            score = 0

            # 检查关键词匹配
            for keyword in skill.keywords:
                if keyword.lower() in intent_lower:
                    score += 2
                elif keyword.lower() in intent_lower.split():
                    score += 3

            # 检查技能名匹配
            if name.lower() in intent_lower:
                score += 2

            # 检查描述匹配
            if skill.description.lower() in intent_lower:
                score += 1

            if score > 0:
                matches.append((name, score))

        # 按分数排序
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:10]

    def get_best_skill(self, intent: str) -> Optional[str]:
        """获取最匹配的技能"""
        matches = self.find_skills_for_intent(intent)
        if matches:
            return matches[0][0]
        return None

    def compose_workflow(self, intent: str) -> Dict:
        """自动组合工作流"""
        matches = self.find_skills_for_intent(intent)

        workflow = {"intent": intent, "steps": [], "estimated_success_rate": 0.8}

        for i, (skill_name, score) in enumerate(matches[:5]):
            skill = self.skills.get(skill_name)
            step = {
                "order": i + 1,
                "skill": skill_name,
                "confidence": score / 10,
                "description": skill.description if skill else "Unknown",
                "keywords": skill.keywords[:5] if skill else [],
            }
            workflow["steps"].append(step)

        return workflow

    def get_skill_guide(self) -> str:
        """获取技能指引"""
        guide = []
        guide.append("# Available Skills for Composition")
        guide.append("")
        guide.append("| Skill | Keywords | Security |")
        guide.append("|-------|----------|----------|")

        for skill in self.skills.values():
            keywords_str = ", ".join(skill.keywords[:5])
            guide.append(f"| {skill.name} | {keywords_str} | {skill.security_grade} |")

        return "\n".join(guide)

    def get_stats(self) -> Dict:
        return {
            "version": self.VERSION,
            "total_skills": len(self.skills),
            "skills": list(self.skills.keys())[:10],
        }


composer = SkillComposer()


if __name__ == "__main__":
    print(f"技能组合指引器 v{composer.VERSION}")
    print(f"已加载 {len(composer.skills)} 个技能")

    test_intents = [
        "生成一张图片",
        "制作视频并发布",
        "定时执行任务",
        "处理文本文件",
        "数据分析",
        "检查视频状态",
    ]

    for intent in test_intents:
        matches = composer.find_skills_for_intent(intent)
        print(f"\n意图: {intent}")
        if matches:
            for name, score in matches[:3]:
                print(f"   - {name} (匹配度: {score})")
        else:
            print(f"   - 无匹配")
