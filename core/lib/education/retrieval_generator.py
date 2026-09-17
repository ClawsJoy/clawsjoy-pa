#!/usr/bin/env python3
"""Retrieval Generator - Retrieval Generator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""检索式生成 - 强制从文档读取，不允许编造"""

import json
from pathlib import Path
from typing import Dict, List

import yaml


class RetrievalGenerator:
    """强制从配置文件生成，不让 LLM 编造"""

    def __init__(self):
        self.config_file = Path("PROJECT_ROOT/config/agents.yaml")
        self.skills_dir = Path("skills")
        self.docs_dir = Path("PROJECT_ROOT/docs")

    def get_real_agents(self) -> List[Dict]:
        """从配置文件读取真实 Agent"""
        if not self.config_file.exists():
            return []

        with open(self.config_file, "r", encoding="utf-8") as f:
            data = unified_config.get("education", {})
            agents = data.get("agents", {})

        result = []
        for name, info in agents.items():
            result.append(
                {
                    "name": name,
                    "display_name": info.get("name", name),
                    "description": info.get("description", ""),
                    "type": info.get("type", "custom"),
                    "capabilities": info.get("capabilities", []),
                }
            )
        return result

    def get_real_skills(self) -> List[str]:
        """获取真实技能列表"""
        skills = []
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                skills.append(skill_dir.name)
        return sorted(skills)

    def generate_agent_text(self) -> str:
        """生成 Agent 文本（不依赖 LLM）"""
        agents = self.get_real_agents()

        if not agents:
            return "未找到 Agent 配置"

        lines = []
        for agent in agents:
            name = agent["name"]
            display = agent.get("display_name", name)
            desc = agent.get("description", "暂无描述")
            lines.append(f"{display}（{name}）：{desc}")

        return "\n".join(lines)

    def generate_skill_text(self, limit: int = 10) -> str:
        """生成技能文本"""
        skills = self.get_real_skills()
        return "\n".join([f"- {s}" for s in skills[:limit]])

    def generate_architecture_text(self) -> str:
        """从文档生成架构描述"""
        arch_file = self.docs_dir / "ARCHITECTURE.md"
        if arch_file.exists():
            content = arch_file.read_text(encoding="utf-8", errors="ignore")
            # 提取关键行
            lines = []
            for line in content.split("\n"):
                if "层" in line or "Layer" in line:
                    cleaned = (
                        line.replace("│", "")
                        .replace("─", "")
                        .replace("┌", "")
                        .replace("┐", "")
                    )
                    cleaned = cleaned.replace("└", "").replace("┘", "").strip()
                    if cleaned and len(cleaned) > 5:
                        lines.append(cleaned)
            if lines:
                return "\n".join(lines[:8])

        return "用户层 -> 安全层 -> Agent层 -> 技能层 -> 记忆层"

    def generate_svg_content(self) -> str:
        """生成 SVG 内容（完全基于真实数据）"""
        agents = self.get_real_agents()
        skills = self.get_real_skills()

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 700">
  <rect width="900" height="700" fill="#1a1a2e"/>
  <text x="450" y="40" text-anchor="middle" fill="#00d4f" font-size="22" font-weight="bold">ClawsJoy 真实系统数据</text>
  <text x="450" y="70" text-anchor="middle" fill="#888" font-size="12">信息来源：config/agents.yaml 和 skills/ 目录</text>
  
  <rect x="30" y="100" width="840" height="300" rx="10" fill="#0d1b2a" stroke="#2ecc71" stroke-width="1.5"/>
  <text x="50" y="130" fill="#2ecc71" font-size="16" font-weight="bold">Agent 清单（共 {len(agents)} 个）</text>
"""
        y = 165
        for agent in agents[:12]:
            name = agent.get("display_name", agent["name"])
            desc = agent.get("description", "")[:50]
            svg += f'  <text x="50" y="{y}" fill="#f39c12" font-size="12" font-weight="bold">{name}</text>\n'
            if desc:
                svg += f'  <text x="220" y="{y}" fill="#aaa" font-size="11">{desc}</text>\n'
            y += 28

        svg += f"""
  <rect x="30" y="420" width="840" height="160" rx="10" fill="#0d1b2a" stroke="#3498db" stroke-width="1.5"/>
  <text x="50" y="450" fill="#3498db" font-size="16" font-weight="bold">技能系统（共 {len(skills)} 个原子技能）</text>
"""
        y = 485
        for skill in skills[:15]:
            svg += (
                f'  <text x="50" y="{y}" fill="#aaa" font-size="11">● {skill}</text>\n'
            )
            y += 22

        svg += """
  <text x="450" y="680" text-anchor="middle" fill="#555" font-size="10">ClawsJoy 智能体操作系统 · 真实配置数据</text>
</svg>"""
        return svg


if __name__ == "__main__":
    rg = RetrievalGenerator()

    print("=" * 60)
    print("真实 Agent 列表（从 config/agents.yaml 读取）")
    print("=" * 60)
    print(rg.generate_agent_text())

    print("\n" + "=" * 60)
    print("真实技能列表（从 skills/ 目录读取）")
    print("=" * 60)
    print(rg.generate_skill_text())

    print("\n" + "=" * 60)
    print("生成 SVG")
    print("=" * 60)
    svg = rg.generate_svg_content()
    output_file = Path("PROJECT_ROOT/output/real_data_system.svg")
    output_file.write_text(svg, encoding="utf-8")
    print(f"✅ 已生成: {output_file}")
