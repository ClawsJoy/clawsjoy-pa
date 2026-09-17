#!/usr/bin/env python3
"""Force Retriever - Force Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""强制检索器 - 必须引用原文"""

import re
from pathlib import Path
from typing import Dict, List


class ForceRetriever:
    def __init__(self):
        self.docs_dir = Path("PROJECT_ROOT/docs")

    def search_docs(self, query: str) -> List[Dict]:
        """搜索所有文档，返回匹配的内容"""
        results = []

        for md_file in self.docs_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="ignore")

            # 查找包含关键词的段落
            lines = content.split("\n")
            for i, line in enumerate(lines):
                # 跳过空行和装饰行
                if (
                    not line.strip()
                    or line.startswith("┌")
                    or line.startswith("├")
                    or line.startswith("└")
                ):
                    continue

                # 匹配查询关键词
                keywords = query.lower().split()
                matched = any(kw in line.lower() for kw in keywords[:3])

                if matched and len(line.strip()) > 10:
                    # 提取上下文
                    start = max(0, i - 1)
                    end = min(len(lines), i + 3)
                    context = "\n".join(lines[start:end])

                    # 清理特殊字符
                    context = re.sub(r"[│─┌┐└┘├┤┬┴┼]", "", context)

                    results.append(
                        {
                            "source": md_file.name,
                            "line": line.strip(),
                            "context": context[:300],
                        }
                    )

                    if len(results) >= 5:
                        break

            if len(results) >= 5:
                break

        return results

    def retrieve_agents(self) -> str:
        """专门检索 Agent 信息"""
        doc_file = self.docs_dir / "AGENT_COMPOSITION.md"
        if not doc_file.exists():
            return "未找到 Agent 文档"

        content = doc_file.read_text(encoding="utf-8", errors="ignore")

        # 提取 Agent 列表
        agents = []
        lines = content.split("\n")

        in_list = False
        for line in lines:
            # 检测 Agent 名称
            if "orchestrator" in line.lower():
                agents.append(
                    "orchestrator (决策Agent/编排器) - 任务规划、技能编排、工作流管理"
                )
            elif "code_agent" in line.lower():
                agents.append("code_agent (代码Agent) - 代码生成、代码审查、代码调试")
            elif "video_agent" in line.lower():
                agents.append("video_agent (视频Agent) - 视频创作、漫剧制作、字幕添加")
            elif "youtube_agent" in line.lower():
                agents.append(
                    "youtube_agent (YouTubeAgent) - 视频上传、频道分析、趋势检测"
                )
            elif "security_agent" in line.lower():
                agents.append(
                    "security_agent (安全Agent) - 安全检查、权限验证、审计日志"
                )
            elif "memory_manager" in line.lower():
                agents.append(
                    "memory_manager (记忆Agent) - 记忆存储、记忆回忆、向量搜索"
                )
            elif "decision_agent" in line.lower():
                agents.append("decision_agent (决策Agent) - 用户总管、任务调度")
            elif "chat_agent" in line.lower():
                agents.append("chat_agent (聊天Agent) - 话术生成、用户沟通")
            elif "personal_butler" in line.lower():
                agents.append("personal_butler (私人管家) - 用户数字分身、1对1服务")
            elif "analysis_agent" in line.lower():
                agents.append("analysis_agent (分析Agent) - 数据分析、优化建议")

        if agents:
            return (
                f"根据 `AGENT_COMPOSITION.md` 文档，ClawsJoy 包含以下 Agent：\n\n"
                + "\n".join([f"- {a}" for a in agents])
            )

        return "未找到 Agent 信息"

    def retrieve_architecture(self) -> str:
        """检索架构信息"""
        doc_file = self.docs_dir / "ARCHITECTURE.md"
        if not doc_file.exists():
            return "未找到架构文档"

        content = doc_file.read_text(encoding="utf-8", errors="ignore")

        # 提取架构层级
        layers = []
        keywords = ["用户层", "安全层", "Agent层", "技能层", "记忆层"]

        for layer in keywords:
            if layer in content:
                layers.append(layer)

        if layers:
            return f"根据 `ARCHITECTURE.md` 文档，系统架构包含：\n\n" + "\n".join(
                [f"- {layer}" for layer in layers]
            )

        return "未找到架构信息"

    def retrieve_skill(self, skill_name: str) -> str:
        """检索特定技能信息"""
        skill_dir = Path("skills") / skill_name
        if not skill_dir.exists():
            return f"未找到技能 {skill_name}"

        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            desc = ""
            for i, line in enumerate(lines):
                if "description" in line.lower():
                    desc = line.replace("description:", "").strip()
                    break
            return f"根据 `skills/{skill_name}/SKILL.md` 文档：\n- {desc if desc else content[:200]}"

        return "未找到技能描述"


if __name__ == "__main__":
    retriever = ForceRetriever()

    print("=" * 60)
    print("问题: ClawsJoy 有哪些 Agent？")
    print("=" * 60)
    print(retriever.retrieve_agents())

    print("\n" + "=" * 60)
    print("问题: 系统架构包含哪些层？")
    print("=" * 60)
    print(retriever.retrieve_architecture())

    print("\n" + "=" * 60)
    print("问题: svg-generator 技能有什么功能？")
    print("=" * 60)
    print(retriever.retrieve_skill("svg_generator"))
