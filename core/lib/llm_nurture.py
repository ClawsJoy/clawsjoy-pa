#!/usr/bin/env python3
"""LLM 养成管理器 - 自我进化闭环"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class LLMNurture:
    """LLM 养成管理器 - 闭环学习"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.data_dir = Path(f"data/nurture/{user_id}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.profile_file = self.data_dir / "profile.json"
        self.memory_file = self.data_dir / "memories.json"
        self.stats_file = self.data_dir / "stats.json"
        self.reflections_file = self.data_dir / "reflections.json"
        
        self._load()

    def _load(self):
        """加载所有数据"""
        if self.profile_file.exists():
            with open(self.profile_file, 'r') as f:
                self.profile = json.load(f)
        else:
            self.profile = {
                "created_at": datetime.now().isoformat(),
                "name": None,
                "preferences": {},
                "interaction_count": 0,
                "evolution_stage": 0
            }
        
        if self.memory_file.exists():
            with open(self.memory_file, 'r') as f:
                self.memories = json.load(f)
        else:
            self.memories = []
        
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                self.stats = json.load(f)
        else:
            self.stats = {
                "total_interactions": 0,
                "successful": 0,
                "failed": 0,
                "agent_usage": {},
                "skills_used": {},
                "evolution_count": 0
            }
        
        if self.reflections_file.exists():
            with open(self.reflections_file, 'r') as f:
                self.reflections = json.load(f)
        else:
            self.reflections = []

    def _save(self):
        """保存所有数据"""
        with open(self.profile_file, 'w') as f:
            json.dump(self.profile, f, indent=2, ensure_ascii=False)
        with open(self.memory_file, 'w') as f:
            json.dump(self.memories[-200:], f, indent=2, ensure_ascii=False)
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        with open(self.reflections_file, 'w') as f:
            json.dump(self.reflections[-50:], f, indent=2, ensure_ascii=False)

    def record_interaction(self, user_input: str, response: str, success: bool, agent: str = None):
        """记录交互"""
        self.stats["total_interactions"] += 1
        if success:
            self.stats["successful"] += 1
        else:
            self.stats["failed"] += 1
        
        if agent:
            self.stats["agent_usage"][agent] = self.stats["agent_usage"].get(agent, 0) + 1
        
        self.memories.append({
            "input": user_input[:200],
            "response": response[:200],
            "success": success,
            "agent": agent,
            "timestamp": datetime.now().isoformat()
        })
        
        self.profile["interaction_count"] += 1
        
        # 触发反思
        if self.stats["total_interactions"] % 10 == 0:
            self._trigger_reflection()
        
        self._save()

    def record_preference(self, key: str, value: str):
        """记录用户偏好"""
        self.profile["preferences"][key] = value
        self._save()

    def _trigger_reflection(self):
        """触发反思"""
        recent = self.memories[-20:] if self.memories else []
        if not recent:
            return
        
        # 分析最近交互
        success_rate = self.stats["successful"] / max(1, self.stats["total_interactions"])
        
        # 识别失败模式
        failure_patterns = []
        for m in recent:
            if not m.get("success"):
                failure_patterns.append(m.get("input", "")[:50])
        
        reflection = {
            "timestamp": datetime.now().isoformat(),
            "success_rate": success_rate,
            "total_interactions": self.stats["total_interactions"],
            "failure_patterns": failure_patterns[:5],
            "top_agents": sorted(
                self.stats["agent_usage"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        }
        
        self.reflections.append(reflection)
        
        # 如果成功率 < 0.5，触发进化
        if success_rate < 0.5 and self.stats["evolution_count"] < 3:
            self._trigger_evolution(success_rate)
        
        self._save()

    def _trigger_evolution(self, success_rate: float):
        """触发自我进化"""
        self.stats["evolution_count"] += 1
        self.profile["evolution_stage"] += 1
        
        evolution = {
            "stage": self.profile["evolution_stage"],
            "success_rate": success_rate,
            "action": "优化能力选择",
            "timestamp": datetime.now().isoformat()
        }
        self.reflections.append(evolution)
        
        # 生成优化建议
        suggestions = []
        if success_rate < 0.5:
            suggestions.append("建议增加 fallback 机制")
            suggestions.append("建议使用更简单的 Agent 处理复杂任务")
        
        self._save()
        print(f"[Nurture] 进化触发! 阶段 {self.profile['evolution_stage']}")

    def get_nurture_prompt(self) -> str:
        """生成养成提示词"""
        prefs = self.profile.get("preferences", {})
        pref_text = "\n".join([f"- {k}: {v}" for k, v in prefs.items()]) if prefs else "暂无"

        agent_usage = self.stats.get("agent_usage", {})
        top_agents = sorted(agent_usage.items(), key=lambda x: x[1], reverse=True)[:3]
        agent_text = ", ".join([f"{a}({c}次)" for a, c in top_agents]) if top_agents else "暂无"

        success_rate = self.stats.get("successful", 0) / max(1, self.stats.get("total_interactions", 1))

        return f"""
【用户画像】
- 名字: {self.profile.get('name', '未设置')}
- 交互次数: {self.stats.get('total_interactions', 0)}
- 成功率: {success_rate:.0%}
- 进化阶段: {self.profile.get('evolution_stage', 0)}
- 常用 Agent: {agent_text}

【用户偏好】
{pref_text}

【最近记忆】
{self._format_recent_memories(3)}
"""

    def _format_recent_memories(self, n: int) -> str:
        recent = self.memories[-n:] if self.memories else []
        if not recent:
            return "暂无"
        lines = []
        for m in recent:
            status = "✅" if m.get("success") else "❌"
            input_text = m.get("input", "")[:50]
            lines.append(f"- {status} {input_text}...")
        return "\n".join(lines)

    def get_stats(self) -> Dict:
        return {
            "total": self.stats.get("total_interactions", 0),
            "successful": self.stats.get("successful", 0),
            "failed": self.stats.get("failed", 0),
            "success_rate": self.stats.get("successful", 0) / max(1, self.stats.get("total_interactions", 1)),
            "evolution_count": self.stats.get("evolution_count", 0),
            "evolution_stage": self.profile.get("evolution_stage", 0),
            "top_agents": sorted(
                self.stats.get("agent_usage", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        }


_nurture_cache = {}

def get_nurture(user_id: str = "default") -> LLMNurture:
    if user_id not in _nurture_cache:
        _nurture_cache[user_id] = LLMNurture(user_id)
    return _nurture_cache[user_id]
