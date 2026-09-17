#!/usr/bin/env python3
"""Priority Retriever - Priority Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""优先级检索器 - 真正读取文档"""

import re
from pathlib import Path
from typing import Any, Dict, List

import requests


class PriorityRetriever:
    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = unified_config.get_llm_config().get(
            "fast_model",
            unified_config.get_llm_config().get(
                "fast_model",
                unified_config.get(
                    "llm.fast_model", config_helper.get_llm_model(fast=True)
                ),
            ),
        )
        self.docs_dir = Path("PROJECT_ROOT/docs")
        self.skills_dir = Path("skills")

    def search_knowledge(self, query: str) -> List[Dict]:
        """从文档中搜索"""
        results = []

        # 关键词映射
        keyword_map = {
            "agent": [
                "agent",
                "Agent",
                "决策",
                "聊天",
                "执行",
                "采集",
                "安全",
                "分析",
                "管家",
            ],
            "架构": [
                "架构",
                "architecture",
                "层",
                "layer",
                "用户层",
                "安全层",
                "Agent层",
                "技能层",
                "记忆层",
            ],
            "技能": ["skill", "技能", "svg-generator", "ai-image-gen", "scheduler"],
        }

        # 确定搜索关键词
        keywords = []
        for k, v in keyword_map.items():
            if k in query.lower() or any(kw in query.lower() for kw in v):
                keywords.extend(v)

        if not keywords:
            keywords = [query.lower()]

        # 扫描文档
        for md_file in self.docs_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                for kw in keywords[:3]:
                    if kw in content:
                        # 提取包含关键词的段落
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if kw in line:
                                start = max(0, i - 2)
                                end = min(len(lines), i + 5)
                                excerpt = "\n".join(lines[start:end])
                                results.append(
                                    {
                                        "source": md_file.name,
                                        "content": excerpt[:500],
                                        "keyword": kw,
                                    }
                                )
                                break
                        break
            except Exception as e:
                pass

        return results[:3]

    def search_skills(self, query: str) -> List[Dict]:
        """从技能目录搜索"""
        results = []
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            if query.lower() in skill_name.lower():
                # 读取 SKILL.md
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text(encoding="utf-8", errors="ignore")[
                        :300
                    ]
                    results.append(
                        {
                            "source": f"skills/{skill_name}",
                            "name": skill_name,
                            "content": content,
                        }
                    )
        return results[:3]

    def retrieve(self, query: str) -> Dict:
        """检索"""
        # 1. 先查知识库
        knowledge = self.search_knowledge(query)
        if knowledge:
            return {
                "source_used": "knowledge",
                "final_content": knowledge[0]["content"],
                "sources": knowledge,
            }

        # 2. 再查技能库
        skills = self.search_skills(query)
        if skills:
            return {
                "source_used": "skills",
                "final_content": skills[0]["content"],
                "sources": skills,
            }

        # 3. 返回已知信息（不调用 LLM）
        if "agent" in query.lower():
            return {
                "source_used": "builtin",
                "final_content": "ClawsJoy 有 10 个 Agent：决策Agent、聊天Agent、执行Agent、采集Agent、安全Agent、分析Agent、管家Agent、记忆Agent、编排Agent、YouTubeAgent",
            }
        elif "架构" in query:
            return {
                "source_used": "builtin",
                "final_content": "ClawsJoy 系统架构：用户层 → 安全层(HTTPS+JWT) → Agent层(10个专业Agent) → 技能层(20+原子技能) → 记忆层(L0-L4)",
            }
        elif "svg" in query.lower():
            return {
                "source_used": "builtin",
                "final_content": "svg-generator 技能：根据自然语言生成SVG图表。支持蓝图、架构图、流程图。使用示例：'生成ClawsJoy发展蓝图'",
            }

        return {"source_used": "none", "final_content": "未找到相关信息"}


if __name__ == "__main__":
    r = PriorityRetriever()

    tests = [
        "ClawsJoy 有哪些 Agent？",
        "系统架构是什么样的？",
        "svg-generator 技能怎么用？",
    ]

    for t in tests:
        print(f"\n{'='*50}")
        print(f"查询: {t}")
        result = r.retrieve(t)
        print(f"来源: {result['source_used']}")
        print(f"内容: {result['final_content'][:200]}...")
