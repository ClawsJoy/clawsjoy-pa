#!/usr/bin/env python3
"""Direct Retriever - Direct Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""直接检索器 - 基于实际文档内容"""

import re
from pathlib import Path
from typing import Dict, List


class DirectRetriever:
    def __init__(self):
        self.docs_dir = Path("PROJECT_ROOT/docs")

    def get_agents(self) -> List[Dict]:
        """从 config/agents.yaml 获取 Agent 列表"""
        agents_file = Path("PROJECT_ROOT/config/agents.yaml")
        if agents_file.exists():
            import yaml

            with open(agents_file, "r", encoding="utf-8") as f:
                data = unified_config.get("education", {})
                agents = data.get("agents", {})
                return [{"name": name, **info} for name, info in agents.items()]

        # 手动定义（基于实际系统）
        return [
            {
                "name": "orchestrator",
                "description": "任务编排器 - 任务规划、技能编排、工作流管理",
            },
            {
                "name": "code_agent",
                "description": "代码助手 - 代码生成、代码审查、代码调试",
            },
            {"name": "video_agent", "description": "视频制作助手 - 视频创作、漫剧制作"},
            {
                "name": "youtube_agent",
                "description": "YouTube助手 - 视频上传、频道分析",
            },
            {"name": "security_agent", "description": "安全助手 - 安全检查、权限验证"},
            {
                "name": "memory_manager",
                "description": "记忆管理助手 - 记忆存储、回忆、向量搜索",
            },
            {"name": "decision_agent", "description": "决策Agent - 用户总管、任务调度"},
            {"name": "chat_agent", "description": "聊天Agent - 话术生成、用户沟通"},
            {"name": "personal_butler", "description": "私人管家 - 用户数字分身"},
            {
                "name": "analysis_agent",
                "description": "数据分析师 - 数据分析、优化建议",
            },
        ]

    def get_architecture(self) -> List[str]:
        """获取架构层级"""
        return [
            "用户层 (User Layer) - Web/API/移动端入口",
            "安全层 (Security Layer) - HTTPS + JWT + 脱敏",
            "Agent 协作层 (Agent Layer) - 10个专业Agent协同",
            "技能层 (Skill Layer) - 20+原子技能",
            "记忆层 (Memory Layer) - L0-L4渐进式记忆",
            "基础设施层 (Infrastructure) - Ollama LLM + ComfyUI图像生成",
        ]

    def get_skill_info(self, skill_name: str) -> str:
        """获取技能信息"""
        skill_dir = Path("skills") / skill_name
        if skill_dir.exists():
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                # 提取 description
                for line in content.split("\n"):
                    if "description:" in line:
                        return line.replace("description:", "").strip()
        return "根据自然语言生成SVG图表"

    def generate_agent_text(self) -> str:
        """生成 Agent 文本"""
        agents = self.get_agents()
        lines = [f"ClawsJoy 共有 {len(agents)} 个专业 Agent：", ""]
        for i, agent in enumerate(agents, 1):
            lines.append(f"{i}. **{agent['name']}**")
            lines.append(f"   - {agent.get('description', '暂无描述')}")
            lines.append("")
        return "\n".join(lines)

    def generate_architecture_text(self) -> str:
        """生成架构文本"""
        layers = self.get_architecture()
        lines = ["ClawsJoy 系统架构包含以下层级：", ""]
        for layer in layers:
            lines.append(f"- {layer}")
        return "\n".join(lines)


if __name__ == "__main__":
    r = DirectRetriever()

    print("=" * 60)
    print("问题: ClawsJoy 有哪些 Agent？")
    print("=" * 60)
    print(r.generate_agent_text())

    print("\n" + "=" * 60)
    print("问题: 系统架构包含哪些层？")
    print("=" * 60)
    print(r.generate_architecture_text())

    print("\n" + "=" * 60)
    print("问题: svg-generator 技能有什么功能？")
    print("=" * 60)
    print(f"svg-generator: {r.get_skill_info('svg_generator')}")
