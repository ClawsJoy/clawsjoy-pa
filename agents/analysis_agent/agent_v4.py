#!/usr/bin/env python3
"""AnalysisAgent v5.0 - 数据分析助手

能力:
- 数据分析（提供数据则分析，无数据则引导）
- 文本总结
- 趋势识别
"""

import re
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class AnalysisAgentV4(BusinessAgent):
    name = "analysis_agent_v4"
    description = "智慧数据分析助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"📊 AnalysisAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if any(kw in t for kw in ["总结", "摘要", "概括"]):
            return self._summarize(user_input)
        else:
            return self._analyze(user_input)

    def _analyze(self, user_input: str) -> Dict:
        data = self._extract_data(user_input)

        if data:
            analysis_type = self._identify_type(user_input)
            prompt = f"""分析以下数据：

数据：{data}
类型：{analysis_type}

请输出：
## 📊 概览
## 📈 趋势
## ⚠ 异常
## 💡 洞察
## ✅ 建议"""
            result = self._call_llm(prompt, task_type="analysis")
            return self._resp(result if result else "分析完成，请查看结果")
        else:
            return self._resp(
                "📊 请提供需要分析的数据。\n\n"
                "示例：\n"
                "• 分析销售数据：1月100, 2月150, 3月120\n"
                "• 分析用户数据：```\\n日期,活跃用户\\n1/1,1000\\n```\n\n"
                "💡 也可以直接粘贴CSV、表格或数字序列"
            )

    def _summarize(self, user_input: str) -> Dict:
        content = re.sub(r'^(总结|摘要|概括)', '', user_input).strip()
        if not content:
            return self._resp("📝 请提供要总结的内容。例如：总结 + 一段文字")

        prompt = f"将以下内容总结为3-5个要点：\n\n{content}"
        result = self._call_llm(prompt, task_type="summary")
        return self._resp(f"📝 摘要\n\n{result}" if result else "总结生成失败，请重试")

    def _extract_data(self, text: str) -> str:
        # 代码块中的数据
        match = re.search(r'```(?:json|csv|table)?\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # key:value 或 key=value 格式
        match = re.search(r'数据[：:]\s*([^\n]+)', text)
        if match:
            return match.group(1).strip()

        # 数字序列
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        if len(numbers) >= 3:
            return f"数字序列: {', '.join(numbers)}"

        # 多行文本（可能是表格）
        lines = [l.strip() for l in text.split('\n') if l.strip() and not l.startswith(('分析', '统计', '帮'))]
        if len(lines) >= 3:
            return '\n'.join(lines[:20])

        return ""

    def _identify_type(self, text: str) -> str:
        t = text.lower()
        if any(kw in t for kw in ["销售", "销售额", "销量", "收入"]):
            return "销售数据"
        if any(kw in t for kw in ["用户", "客户", "活跃", "留存"]):
            return "用户数据"
        if any(kw in t for kw in ["财务", "成本", "利润", "支出"]):
            return "财务数据"
        if any(kw in t for kw in ["日期", "时间", "年月"]):
            return "时间序列"
        return "通用数据"

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = AnalysisAgentV4("test")
    print(agent.process("分析销售数据：1月100, 2月150, 3月120")["response"][:300])
