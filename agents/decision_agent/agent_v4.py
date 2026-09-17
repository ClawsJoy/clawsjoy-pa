#!/usr/bin/env python3
"""DecisionAgent v5.0 — 审查员 + 路由器双模式"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent
from core.lib.llm_client import llm_client


class DecisionAgentV4(BusinessAgent):
    """审查员 + 路由器"""

    name = "decision_agent_v4"
    description = "审查员与决策者"
    version = "5.0.0"

    AGENT_CAPABILITIES = {
        "chat_agent": ["聊天", "对话", "问答"],
        "code_agent": ["代码", "编程", "函数", "debug"],
        "analysis_agent": ["分析", "数据", "统计", "趋势"],
        "translate_agent": ["翻译"],
        "calculator_agent": ["计算", "数学"],
    }

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"🎖 DecisionAgent v{self.version} 启动")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    # ================================================================
    #  核心入口
    # ================================================================

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        # 审查模式：管理层传了 skip_intent + spec
        if context and context.get("skip_intent"):
            return self._review(user_input, context)

        # 路由模式：默认
        return self._route(user_input)

    # ================================================================
    #  审查模式
    # ================================================================

    def _review(self, user_input: str, context: Dict) -> Dict:
        """对照验收标准，逐项审查"""
        task_id = context.get("task_id", "")
        created_by = context.get("created_by", "")

        # 读 spec
        spec = ""
        try:
            spec_dir = Path(f"data/projects/{created_by}") if created_by else None
            if spec_dir and spec_dir.exists():
                for spec_file in spec_dir.rglob("*.md"):
                    spec += spec_file.read_text(encoding="utf-8") + "\n"
        except Exception:
            pass

        prompt = f"""你是 ClawsJoy 的审查员。

验收标准：
{spec if spec else "按通用质量标准审查"}

待审查内容：
{user_input[:2000]}

请逐项对照验收标准，只输出：

## 通过项
- （列出通过的标准）

## 修改项
- （列出未通过的标准及具体修改方向）

## 审查结论
（通过 / 需修改）

不要反问，不要建议过程。"""

        try:
            result = llm_client.generate(prompt, task_type="review", timeout=120)
            if result:
                # 写审查记录
                self._save_review(task_id, created_by, result)
                return self._resp(result)
        except Exception as e:
            return self._resp(f"审查异常: {e}")

        return self._resp("审查超时")

    def _save_review(self, task_id: str, created_by: str, content: str):
        """保存审查记录"""
        if not created_by or not task_id:
            return
        try:
            review_dir = Path(f"data/projects/{created_by}/reviews")
            review_dir.mkdir(parents=True, exist_ok=True)
            review_file = review_dir / f"{task_id}_review.md"
            review_file.write_text(content, encoding="utf-8")
            print(f"[Review] 审查记录已保存: {review_file}")
        except Exception as e:
            print(f"[Review] 保存审查记录失败: {e}")

    # ================================================================
    #  路由模式
    # ================================================================

    def _route(self, user_input: str) -> Dict:
        """关键词匹配路由"""
        result = self.decide(user_input)
        return self._resp(f"🎯 推荐: **{result.get('agent')}**\n理由: {result.get('reasoning', '')}")

    def decide(self, task: str, candidates: List[str] = None) -> Dict:
        scores = self._keyword_match(task)
        if candidates:
            scores = [s for s in scores if s["agent"] in candidates]
        if not scores:
            return {"agent": "chat_agent", "confidence": 0.5, "reasoning": "默认选择"}
        best = scores[0]
        return {
            "agent": best["agent"],
            "confidence": best["confidence"],
            "reasoning": best["reasoning"],
            "alternatives": [s["agent"] for s in scores[1:3]] if len(scores) > 1 else [],
        }

    def _keyword_match(self, task: str) -> List[Dict]:
        t = task.lower()
        results = []
        for agent, keywords in self.AGENT_CAPABILITIES.items():
            matched = [kw for kw in keywords if kw in t]
            score = min(len(matched) / 2, 1.0)
            results.append(
                {"agent": agent, "confidence": score, "reasoning": f"匹配: {', '.join(matched)}" if matched else "无关键词匹配"}
            )

        DISAMBIGUATION = {
            "code_agent": {"写诗": 0, "写歌": 0, "写小说": 0, "写文章": 0, "写剧本": 0, "写信": 0},
            "calculator_agent": {"日历": 0, "日期": 0, "星期": 0},
        }
        for r in results:
            agent = r["agent"]
            if agent in DISAMBIGUATION:
                for keyword, penalty in DISAMBIGUATION[agent].items():
                    if keyword in t:
                        r["confidence"] = penalty
                        r["reasoning"] = f"语义消歧: '{keyword}' 不应路由到 {agent}"

        return sorted(results, key=lambda x: x["confidence"], reverse=True)

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}
