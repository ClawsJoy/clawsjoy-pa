#!/usr/bin/env python3
"""Context Learner - Context Learner 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""上下文学习系统 - 理解连续对话"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ContextLearner:
    """上下文学习器 - 记住对话历史"""

    def __init__(self, session_id: str = None):
        self.session_id = (
            session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.history = []
        self.context = {}
        self.memory_file = Path(f"{get_data_root()}/context_memory.json")
        self._load_memory()

    def _load_memory(self):
        """加载长期记忆"""
        if self.memory_file.exists():
            with open(self.memory_file, "r") as f:
                self.long_memory = json.load(f)
        else:
            self.long_memory = {}

    def _save_memory(self):
        """保存长期记忆"""
        with open(self.memory_file, "w") as f:
            json.dump(self.long_memory, f, indent=2, ensure_ascii=False)

    def add(self, user: str, assistant: str, task: str = None):
        """添加对话记录"""
        turn = {
            "user": user,
            "assistant": assistant,
            "task": task,
            "timestamp": datetime.now().isoformat(),
        }
        self.history.append(turn)

        # 提取上下文
        self._extract_context(user, assistant)

    def _extract_context(self, user: str, assistant: str):
        """提取上下文信息"""
        # 检测修改指令
        if "修改" in user or "改一下" in user or "不是" in user:
            self.context["last_modify"] = user
            self.context["needs_update"] = True

        # 检测指代（它、这个、那个）
        if "它" in user or "这个" in user or "那个" in user:
            if len(self.history) >= 1:
                last = self.history[-1]
                self.context["refers_to"] = last.get("task")

        # 检测否定
        if "不对" in user or "错了" in user or "不是这个" in user:
            self.context["last_correction"] = user

    def understand(self, user_input: str) -> Dict:
        """理解当前输入（带上下文）"""
        result = {
            "original": user_input,
            "has_context": False,
            "refers_to": None,
            "is_modify": False,
            "is_followup": False,
            "suggested_task": None,
        }

        # 1. 检查是否有指代
        if "它" in user_input or "这个" in user_input:
            if self.history:
                last = self.history[-1]
                result["has_context"] = True
                result["refers_to"] = last.get("task")
                result["is_followup"] = True

        # 2. 检查是否是修改
        if any(kw in user_input for kw in ["修改", "改一下", "调整", "换成"]):
            result["has_context"] = True
            result["is_modify"] = True
            if self.history:
                result["refers_to"] = self.history[-1].get("task")

        # 3. 检查是否是否定纠正
        if any(kw in user_input for kw in ["不对", "错了", "不是"]):
            result["has_context"] = True
            result["is_correction"] = True

        # 4. 根据上下文推断任务
        if result["has_context"] and result["refers_to"]:
            result["suggested_task"] = result["refers_to"]
        elif len(self.history) > 0:
            # 连续提问，可能是同一主题
            result["suggested_task"] = self.history[-1].get("task")
            result["is_followup"] = True

        return result

    def get_history_summary(self) -> str:
        """获取历史摘要"""
        if not self.history:
            return "暂无历史"

        summary = []
        for i, turn in enumerate(self.history[-3:], 1):
            summary.append(f"{i}. 用户: {turn['user'][:30]} → 任务: {turn.get('task')}")
        return "\n".join(summary)

    def get_stats(self) -> Dict:
        return {
            "session_id": self.session_id,
            "total_turns": len(self.history),
            "context_keys": list(self.context.keys()),
            "long_memory_size": len(self.long_memory),
        }


class ContextAwareAgent:
    """上下文感知 Agent"""

    def __init__(self):
        self.sessions = {}

    def get_session(self, user_id: str = "default") -> ContextLearner:
        """获取或创建会话"""
        if user_id not in self.sessions:
            self.sessions[user_id] = ContextLearner(user_id)
        return self.sessions[user_id]

    def process(self, user_input: str, user_id: str = "default") -> Dict:
        """处理带上下文的输入"""
        session = self.get_session(user_id)

        # 1. 理解上下文
        context = session.understand(user_input)

        # 2. 根据上下文决定任务
        if context["suggested_task"]:
            task = context["suggested_task"]
            source = "context"
        else:
            # 简单意图识别
            if "agent" in user_input.lower():
                task = "list_agents"
            elif "技能" in user_input:
                task = "list_skills"
            elif "图" in user_input:
                task = "generate_chart"
            else:
                task = "unknown"
            source = "direct"

        # 3. 生成回复
        if task == "list_agents":
            response = "ClawsJoy 有决策Agent、聊天Agent、执行Agent、采集Agent、安全Agent、分析Agent等10个专业Agent"
        elif task == "list_skills":
            response = "系统有20+原子技能，包括图像生成、视频制作、任务调度等"
        elif task == "generate_chart":
            response = "已生成系统架构图，保存在 output 目录"
        else:
            response = f"收到：{user_input}"

        # 4. 记录对话
        session.add(user_input, response, task)

        return {
            "success": True,
            "response": response,
            "task": task,
            "context": context,
            "history_turns": len(session.history),
        }


context_agent = ContextAwareAgent()


if __name__ == "__main__":
    print("=" * 60)
    print("上下文理解测试")
    print("=" * 60)

    # 连续对话测试
    test_flow = [
        "ClawsJoy 有哪些 Agent？",
        "它的职责是什么？",  # 指代
        "不对，我是说决策Agent的具体职责",  # 纠正
        "那有哪些技能？",
        "再修改一下，我要看图像生成相关的",  # 修改
        "还是回到 Agent 话题吧",  # 切换
    ]

    for i, inp in enumerate(test_flow, 1):
        print(f"\n[轮次 {i}] 用户: {inp}")
        result = context_agent.process(inp)
        print(f"系统: {result['response']}")
        print(
            f"上下文: 指代={result['context'].get('refers_to')}, 修改={result['context'].get('is_modify')}"
        )

    print("\n" + "=" * 60)
    print("会话统计:")
    session = context_agent.get_session()
    print(session.get_stats())
