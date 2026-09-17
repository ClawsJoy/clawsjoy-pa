#!/usr/bin/env python3
"""Thinker - Thinker 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""教 LLM 思考的系统 - LLM Education System"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


class LLMThinker:
    """教 LLM 如何思考"""

    VERSION = "1.0.0"

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
        self.think_history = []

    def teach(self, task: str, example: str, principle: str) -> str:
        """教 LLM 一个思考范式"""
        prompt = f"""你要学习如何思考和解决问题。

## 任务类型：{task}

## 思考原则：
{principle}

## 示例：
{example}

## 你的任务：
请根据以上原则，解决用户的下一个问题。
记住：不要直接输出答案，先输出你的思考过程，再输出结果。

格式：
【思考过程】...
【结果】...
"""
        return self._call_llm(prompt)

    def think(self, problem: str, context: str = "") -> Dict:
        """让 LLM 按步骤思考"""
        prompt = f"""请按以下步骤思考问题：

问题：{problem}
上下文：{context}

步骤1：理解问题 - 用户真正想要什么？
步骤2：拆解任务 - 需要完成哪些子任务？
步骤3：设计方案 - 用什么方法解决？
步骤4：执行方案 - 具体怎么做？
步骤5：验证结果 - 是否满足需求？

请输出你的思考过程。"""

        response = self._call_llm(prompt)

        # 记录思考历史
        self.think_history.append(
            {"problem": problem, "thinking": response, "timestamp": self._now()}
        )

        return {"thinking": response, "history_count": len(self.think_history)}

    def solve(self, problem: str, tools: List[str] = None) -> Dict:
        """让 LLM 思考后调用工具解决"""
        tools_desc = "\n".join([f"- {t}" for t in (tools or [])])

        prompt = f"""你是一个智能助手，可以调用以下工具来解决问题。

可用工具：
{tools_desc}

用户问题：{problem}

请按以下格式输出：
1. 分析：这个问题需要什么信息？
2. 决策：用什么工具？
3. 参数：工具需要什么参数？
4. 执行：调用工具

输出 JSON：
{{"analysis": "...", "tool": "工具名", "params": {{}}, "reasoning": "..."}}"""

        response = self._call_llm(prompt)

        try:
            # 提取 JSON
            import re

            json_match = re.search(r"\{[^{}]*\}", response)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            pass

        return {"analysis": response, "tool": None, "params": {}}

    def reflect(self, task: str, result: str, feedback: str) -> str:
        """让 LLM 反思并改进"""
        prompt = f"""你刚才完成了一个任务，现在收到反馈。

任务：{task}
你的结果：{result}
反馈：{feedback}

请反思：
1. 哪里做得好？
2. 哪里可以改进？
3. 下次遇到类似问题应该怎么做？

输出你的反思。"""

        return self._call_llm(prompt)

    def _call_llm(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=unified_config.get("timeouts.default", 30),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            print(f"LLM 调用失败: {e}")
        return ""

    def _now(self):
        from datetime import datetime

        return datetime.now().isoformat()


class ThinkingLesson:
    """思考课程 - 预定义的思考范式"""

    @staticmethod
    def lesson_svg_generation():
        """教 LLM 如何生成 SVG"""
        principle = """
1. 先理解用户要什么类型的图（架构图/蓝图/流程图）
2. 确定图的结构（横向/纵向/层次）
3. 设计颜色方案（深色背景 + 霓虹色点缀）
4. 用数学计算位置，不要写死坐标
5. 让内容有层次，信息丰富
"""
        example = """
用户说："生成一个3阶段的发展蓝图"
思考：
- 类型：蓝图，横向3列
- 阶段：阶段1、阶段2、阶段3
- 位置：每列宽250，间距30，起始x=50
- 内容：每个阶段有标题、时间、3个要点
- 颜色：#2ecc71, #3498db, #f39c12
"""
        return principle, example

    @staticmethod
    def lesson_problem_solving():
        """教 LLM 如何解决问题"""
        principle = """
1. 不要直接回答，先分析问题本质
2. 将大问题拆解成小问题
3. 按优先级排序子任务
4. 为每个子任务选择合适的方法
5. 验证结果是否符合预期
"""
        example = """
用户说："系统响应太慢了"
思考：
- 本质：性能问题
- 拆解：检查网络、检查数据库、检查代码
- 优先级：先查最简单的（网络），再查复杂的
- 方法：ping测试 → 数据库慢查询分析 → 代码 profiling
"""
        return principle, example


thinker = LLMThinker()


if __name__ == "__main__":
    print(f"LLM 思考系统 v{thinker.VERSION}")
    print("=" * 50)

    # 测试思考
    result = thinker.think("用户想生成一张ClawsJoy发展蓝图，但不知道包含哪些内容")
    print(result["thinking"][:500])

    # 测试解决
    print("\n" + "=" * 50)
    result = thinker.solve(
        "生成一张4阶段蓝图", tools=["svg-generator", "chart-builder"]
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
