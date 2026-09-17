#!/usr/bin/env python3
"""Trainer - Trainer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""LLM 教育训练器 - 使用 qwen2.5:3b"""

import subprocess
from pathlib import Path
from typing import Dict

import requests


class LLMTrainer:
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
        )  # 使用 3B 模型，速度快
        print(f"🤖 使用模型: {self.model}")

    def teach(self, task: str, example_svg: str) -> str:
        prompt = f"""参考下面 SVG 的格式和样式，生成新的 SVG。

示例 SVG：
{example_svg}

用户需求：{task}

要求：
- 保持相同的结构和样式（深色背景 #1a1a2e、霓虹蓝 #00d4ff）
- 只修改文字内容匹配用户需求
- 不要改变布局结构
- 直接输出 SVG 代码，不要任何解释

SVG："""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 2000},
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
            print(f"LLM 调用失败: {e}")
        return ""

    def train(self, task: str, example_name: str) -> Dict:
        example_file = Path(__file__).parent / "examples" / f"{example_name}.svg"
        if not example_file.exists():
            return {"success": False, "error": f"示例不存在: {example_name}"}

        example_svg = example_file.read_text(encoding="utf-8")
        print(f"📚 教学: {task}")
        print(f"📖 参考示例: {example_name}")

        result_svg = self.teach(task, example_svg)

        if result_svg and result_svg.startswith("<svg"):
            return {"success": True, "svg": result_svg, "llm_generated": True}

        # 降级：修改示例文字
        print("⚠️ LLM 未响应，使用降级模式")
        modified = example_svg.replace("发展蓝图", task[:30])
        return {"success": True, "svg": modified, "llm_generated": False}


if __name__ == "__main__":
    trainer = LLMTrainer()
    result = trainer.train("生成ClawsJoy发展蓝图，包含4个阶段", "roadmap")

    if result["success"]:
        output_file = Path("PROJECT_ROOT/output/trained_roadmap.svg")
        output_file.write_text(result["svg"], encoding="utf-8")
        print(f"✅ 成功！")
        print(f"📁 {output_file}")
        print(f"🤖 LLM 生成: {result.get('llm_generated', False)}")
        print(f"📏 大小: {len(result['svg'])} 字符")
    else:
        print(f"❌ 失败: {result.get('error')}")
