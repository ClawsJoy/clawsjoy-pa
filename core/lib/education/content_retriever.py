#!/usr/bin/env python3
"""Content Retriever - Content Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""内容检索器 - 让 LLM 主动获取内容"""

import json
from pathlib import Path
from typing import Any, Dict, List

import requests


class ContentRetriever:
    """让 LLM 主动检索内容"""

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
        self.knowledge_base = self._load_knowledge()

    def _load_knowledge(self) -> Dict:
        """加载知识库（可扩展）"""
        return {
            "ClawsJoy": {
                "description": "智能体操作系统",
                "agents": [
                    "决策Agent",
                    "聊天Agent",
                    "执行Agent",
                    "采集Agent",
                    "安全Agent",
                    "分析Agent",
                    "管家Agent",
                ],
                "skills_count": 20,
                "features": [
                    "隐私保护",
                    "数字分身",
                    "配置驱动",
                    "四层记忆",
                    "HTTPS安全",
                ],
            },
            "competitors": {
                "OpenClaw": "352k stars, 5700+ skills, 多渠道接入",
                "Hermes": "35.7k stars, 技能自动生成, 闭环学习",
            },
        }

    def search_knowledge(self, query: str) -> str:
        """检索知识库"""
        query_lower = query.lower()
        results = []

        for key, value in self.knowledge_base.items():
            if key.lower() in query_lower:
                results.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")

        if results:
            return "\n".join(results)
        return "未找到相关信息"

    def retrieve_content(self, topic: str) -> Dict:
        """让 LLM 规划需要什么内容，然后检索"""

        # 第一步：LLM 规划需要什么内容
        plan_prompt = f"""用户需要生成关于 "{topic}" 的 SVG 蓝图。

请分析：要生成完整蓝图，需要哪些数据？
输出 JSON 格式：
{{
  "needed_data": ["数据项1", "数据项2"],
  "questions": ["问题1", "问题2"]
}}"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": plan_prompt, "stream": False},
                timeout=unified_config.get("timeouts.default", 30),
            )
            if resp.status_code == 200:
                plan_text = resp.json().get("response", "")
                # 提取 JSON
                import re

                match = re.search(r"\{[^{}]*\}", plan_text)
                if match:
                    plan = json.loads(match.group())
                    needed = plan.get("needed_data", [])

                    # 第二步：检索内容
                    content = {}
                    for item in needed:
                        content[item] = self.search_knowledge(item)

                    return {
                        "success": True,
                        "content": content,
                        "needed": needed,
                        "plan": plan,
                    }
        except Exception as e:
            print(f"规划失败: {e}")

        return {"success": False, "content": {}, "needed": []}

    def generate_svg_with_content(self, topic: str) -> str:
        """基于检索到的内容生成 SVG"""

        # 先检索内容
        retrieval = self.retrieve_content(topic)

        if not retrieval["success"]:
            return ""

        content = retrieval["content"]

        # 加载示例模板
        example_file = Path(__file__).parent / "examples" / "roadmap.svg"
        example_svg = (
            example_file.read_text(encoding="utf-8") if example_file.exists() else ""
        )

        # 让 LLM 基于内容生成 SVG
        prompt = f"""参考 SVG 模板的结构，用以下真实数据填充。

模板：
{example_svg[:500]}...

真实数据：
{json.dumps(content, ensure_ascii=False, indent=2)}

用户需求：{topic}

要求：
1. 使用模板的布局和样式
2. 用真实数据替换占位文字
3. 每个阶段至少包含 3-4 个要点
4. 输出完整 SVG

SVG："""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 3000},
                },
                timeout=config_helper.get_timeout("llm"),
            )
            if resp.status_code == 200:
                svg = resp.json().get("response", "")
                if "<svg" in svg:
                    start = svg.find("<svg")
                    end = svg.rfind("</svg>") + 6
                    return svg[start:end]
        except Exception as e:
            print(f"生成失败: {e}")

        return ""


if __name__ == "__main__":
    retriever = ContentRetriever()

    # 测试：让 LLM 检索内容并生成 SVG
    topic = "ClawsJoy 4.0 系统架构和未来发展"
    svg = retriever.generate_svg_with_content(topic)

    if svg:
        output_file = Path("PROJECT_ROOT/output/content_based_roadmap.svg")
        output_file.write_text(svg, encoding="utf-8")
        print(f"✅ 生成成功！")
        print(f"📁 {output_file}")
        print(f"📏 大小: {len(svg)} 字符")
    else:
        print("❌ 生成失败")

    def search_docs(self, query: str) -> str:
        """从文档中检索内容"""
        docs_dir = Path("PROJECT_ROOT/docs")
        results = []

        for md_file in docs_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            if query.lower() in content.lower():
                # 提取相关段落
                lines = content.split("\n")
            for i, line in enumerate(lines):
                if query.lower() in line.lower():
                    context = "\n".join(lines[max(0, i - 2) : min(len(lines), i + 3)])
                    results.append(f"来源 {md_file.name}:\n{context[:300]}")
                    break

        return "\n---\n".join(results[:3]) if results else ""

    def search_vector_db(self, query: str) -> str:
        """从向量数据库检索"""
        try:
            from core.lib.memory_vector import vector_memory

            results = vector_memory.search(query, n=3)
            if results:
                return "\n".join([r.get("text", "")[:200] for r in results])
        except Exception as e:
            pass
        return ""
