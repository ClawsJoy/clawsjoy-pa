#!/usr/bin/env python3
"""CollaborationAgent v5.0 - 多Agent协作编排"""

import re
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.agents.business.business_agent import BusinessAgent


class CollaborationAgentV4(BusinessAgent):
    name = "collaboration_agent_v4"
    description = "多Agent协作编排"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._tasks: List[Dict] = []
        print(f"🤝 CollaborationAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if any(kw in t for kw in ["分配", "指派", "交给"]):
            return self._assign(user_input)
        elif any(kw in t for kw in ["先用", "再用", "然后", "接着", "协作", "并行"]):
            return self._pipeline(user_input)
        elif any(kw in t for kw in ["委托", "调用"]) and "_agent" in t:
            return self._delegate(user_input)
        elif any(kw in t for kw in ["任务列表", "查看任务"]):
            return self._status()
        else:
            return self._help()

    def _assign(self, user_input: str) -> Dict:
        m = re.search(r'(?:分配|指派|交给)\s*(.+?)\s*(?:给|到)\s*(\w+)', user_input)
        if m:
            task, assignee = m.group(1).strip(), m.group(2).strip()
            self._tasks.append({"id": len(self._tasks)+1, "task": task, "assignee": assignee,
                               "status": "pending", "created_at": datetime.now().isoformat()})
            return self._resp(f"✅ 已分配: {task} → {assignee}")
        return self._resp("格式: 分配 写报告 给 code_agent")

    def _delegate(self, user_input: str) -> Dict:
        m = re.search(r'(\w+_agent)\s+(.+)', user_input)
        if not m:
            return self._resp("格式: 委托 code_agent 写排序函数")
        agent_name, task = m.group(1), m.group(2)
        return self._call_agent(agent_name, task)

    def _pipeline(self, user_input: str) -> Dict:
        """解析协作流水线并顺序执行"""
        tasks = self._parse_pipeline(user_input)
        if not tasks:
            return self._resp("格式: 先用 analysis_agent 分析数据，再用 code_agent 生成报表")

        results = []
        for step in tasks:
            r = self._call_agent(step["agent"], step["task"])
            results.append(r)

        lines = ["🤝 协作结果"]
        for r in results:
            status = "✅" if r.get("success") else "❌"
            lines.append(f"{status} {r.get('agent')}: {r.get('response', '')[:120]}")
        return self._resp("\n\n".join(lines))

    def _call_agent(self, agent_name: str, task: str) -> Dict:
        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory
            agent = wisdom_factory.get_agent(agent_name, self.user_id)
            if agent:
                result = agent.process(task)
                return {"agent": agent_name, "success": result.get("success", True),
                        "response": result.get("response", result.get("output_content", ""))}
            return {"agent": agent_name, "success": False, "response": f"Agent不可用"}
        except Exception as e:
            return {"agent": agent_name, "success": False, "response": str(e)}

    def _parse_pipeline(self, text: str) -> List[Dict]:
        tasks = []
        for pattern in [r'先用\s*(\w+_agent)\s*(?:做|执行|处理|分析|生成|写)?\s*([^，,。]+)',
                        r'再用\s*(\w+_agent)\s*(?:做|执行|处理|分析|生成|写)?\s*([^，,。]+)',
                        r'然后\s*(\w+_agent)\s*(?:做|执行|处理|分析|生成|写)?\s*([^，,。]+)']:
            for agent, task in re.findall(pattern, text):
                tasks.append({"agent": agent, "task": task.strip()})
        return tasks

    def _status(self) -> Dict:
        pending = [t for t in self._tasks if t.get("status") == "pending"]
        if not pending:
            return self._resp("📭 暂无待办任务")
        lines = ["📋 待办任务："]
        for t in pending:
            lines.append(f"  {t['id']}. {t['task']} → {t['assignee']}")
        return self._resp("\n".join(lines))

    def _help(self) -> Dict:
        return self._resp(
            "🤝 多Agent协作\n\n"
            "• 委托 code_agent 写排序函数\n"
            "• 先用 analysis_agent 分析数据，再用 code_agent 生成报表\n"
            "• 分配 写报告 给 writer_agent\n"
            "• 任务列表"
        )

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = CollaborationAgentV4("test")
    print(agent.process("委托 code_agent 写排序函数")["response"][:200])
