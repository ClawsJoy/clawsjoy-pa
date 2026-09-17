#!/usr/bin/env python3
"""Markdown Parser - Markdown Parser 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""Markdown 解析器 - 直接提取结构化内容"""

import re
from pathlib import Path
from typing import Dict, List


class MarkdownParser:
    def __init__(self):
        self.docs_dir = Path("PROJECT_ROOT/docs")

    def parse_agent_composition(self) -> Dict:
        """解析 Agent 组合文档"""
        file_path = self.docs_dir / "AGENT_COMPOSITION.md"
        if not file_path.exists():
            return {}

        content = file_path.read_text(encoding="utf-8", errors="ignore")

        agents = []
        current_agent = {}

        lines = content.split("\n")
        for i, line in enumerate(lines):
            # 提取 Agent 名称
            if "Agent" in line and ("orchestrator" in line.lower() or "决策" in line):
                agents.append(
                    {
                        "name": line.strip(),
                        "description": (
                            lines[i + 1].strip() if i + 1 < len(lines) else ""
                        ),
                    }
                )
            elif "code_agent" in line.lower() or "代码" in line:
                agents.append(
                    {
                        "name": line.strip(),
                        "description": (
                            lines[i + 1].strip() if i + 1 < len(lines) else ""
                        ),
                    }
                )
            elif "video_agent" in line.lower() or "视频" in line:
                agents.append(
                    {
                        "name": line.strip(),
                        "description": (
                            lines[i + 1].strip() if i + 1 < len(lines) else ""
                        ),
                    }
                )

        # 预定义的 Agent 信息
        if not agents:
            agents = [
                {
                    "name": "orchestrator (决策Agent)",
                    "description": "任务编排器，负责任务规划、技能编排、工作流管理",
                },
                {
                    "name": "code_agent (代码Agent)",
                    "description": "代码助手，负责代码生成、审查、调试",
                },
                {
                    "name": "video_agent (视频Agent)",
                    "description": "视频制作助手，负责视频创作、漫剧制作",
                },
                {
                    "name": "youtube_agent (YouTubeAgent)",
                    "description": "YouTube助手，负责视频上传、频道分析",
                },
                {
                    "name": "security_agent (安全Agent)",
                    "description": "安全助手，负责安全检查、权限验证",
                },
                {
                    "name": "memory_manager (记忆Agent)",
                    "description": "记忆管理助手，负责记忆存储、回忆、向量搜索",
                },
            ]

        return {"agents": agents, "total": len(agents)}

    def generate_rich_text(self, query: str) -> str:
        """根据查询生成丰富文本"""
        if "agent" in query.lower():
            data = self.parse_agent_composition()
            lines = [f"ClawsJoy 共有 {data['total']} 个专业 Agent：", ""]
            for i, agent in enumerate(data["agents"], 1):
                lines.append(f"{i}. **{agent['name']}**")
                lines.append(f"   - {agent['description']}")
                lines.append("")
            return "\n".join(lines)

        return "请指定查询内容"


if __name__ == "__main__":
    parser = MarkdownParser()
    result = parser.generate_rich_text("ClawsJoy 有哪些 Agent？")
    print(result)
