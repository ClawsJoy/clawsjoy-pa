#!/usr/bin/env python3
"""Smart Retriever - Smart Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""智能检索器 - 理解文档并生成丰富内容"""

import re
from pathlib import Path
from typing import Dict, List

import requests


class SmartRetriever:
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

    def read_doc(self, filename: str) -> str:
        """读取完整文档"""
        file_path = self.docs_dir / filename
        if file_path.exists():
            return file_path.read_text(encoding="utf-8", errors="ignore")
        return ""

    def extract_relevant_section(self, content: str, query: str) -> str:
        """提取相关章节"""
        lines = content.split("\n")
        relevant_lines = []
        in_section = False
        section_title = ""

        for i, line in enumerate(lines):
            # 检测章节标题
            if line.startswith("#") or line.startswith("##"):
                section_title = line
                if any(kw in line.lower() for kw in query.lower().split()):
                    in_section = True
                    relevant_lines.append(line)
                elif in_section and (
                    line.startswith("#") and not line.startswith("###")
                ):
                    break
            elif in_section:
                relevant_lines.append(line)

        if relevant_lines:
            return "\n".join(relevant_lines[:50])

        # 返回前500字符
        return content[:500]

    def summarize_with_llm(self, content: str, query: str) -> str:
        """让 LLM 理解并总结内容"""
        prompt = f"""根据以下文档内容，回答用户问题。

文档内容：
{content}

用户问题：{query}

要求：
1. 提取所有关键信息，不要遗漏
2. 用清晰的列表格式输出
3. 每个要点要有具体描述
4. 不要只输出标题

输出格式：
- 要点1：详细描述
- 要点2：详细描述
..."""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 1000},
                },
                timeout=config_helper.get_timeout("llm"),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            print(f"LLM 总结失败: {e}")
        return content[:300]

    def retrieve_and_summarize(self, query: str) -> Dict:
        """检索并总结"""
        # 1. 找到相关文档
        for md_file in self.docs_dir.glob("*.md"):
            content = self.read_doc(md_file.name)
            if any(kw in content.lower() for kw in query.lower().split()[:2]):
                # 2. 提取相关章节
                section = self.extract_relevant_section(content, query)

                # 3. 让 LLM 总结
                summary = self.summarize_with_llm(section, query)

                return {
                    "source": md_file.name,
                    "raw_content": section[:300],
                    "summary": summary,
                    "success": True,
                }

        return {"success": False, "summary": "未找到相关信息"}

    def generate_rich_description(self, query: str) -> str:
        """生成丰富的描述"""
        result = self.retrieve_and_summarize(query)

        if result["success"]:
            return f"""📚 信息来源: {result['source']}

{result['summary']}"""

        return "未找到相关信息"


if __name__ == "__main__":
    retriever = SmartRetriever()

    queries = [
        "ClawsJoy 有哪些 Agent？每个 Agent 的职责是什么？",
        "系统架构包含哪些层？",
        "svg-generator 技能有什么功能？",
    ]

    for q in queries:
        print(f"\n{'='*60}")
        print(f"问题: {q}")
        print(f"{'='*60}")
        result = retriever.retrieve_and_summarize(q)
        if result["success"]:
            print(f"来源: {result['source']}")
            print(f"\n总结:\n{result['summary'][:500]}")
        else:
            print("未找到")
