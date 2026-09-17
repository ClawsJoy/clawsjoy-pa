#!/usr/bin/env python3
"""上下文引擎 - 按需检索、精准注入"""

from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


class ContextEngine:
    """上下文分类检索引擎"""
    
    # 上下文分类
    CATEGORIES = {
        "identity": ["名字", "姓名", "叫什么", "我是谁", "你叫什么"],
        "memory": ["记住", "记得", "回忆", "之前", "上次"],
        "task": ["继续", "完成", "写到", "进度", "状态"],
        "greeting": ["你好", "嗨", "在吗", "早上好", "晚上好"],
        "creative": ["小说", "剧本", "创作", "故事", "章节", "写"],
        "code": ["代码", "编程", "函数", "bug", "debug"],
        "data": ["分析", "数据", "统计", "报告", "趋势"],
        "general": [],
    }
    
    def __init__(self):
        # 短期记忆（当前会话，3轮）
        self.short_term: List[Dict] = []
        # 长期记忆（跨会话持久化）
        self.long_term: Dict[str, List[Dict]] = defaultdict(list)
        # 用户画像
        self.profile: Dict = {}
    
    def add_exchange(self, user_input: str, response: str, agents: List[str] = None):
        """记录一轮对话"""
        entry = {
            "user": user_input[:200],
            "assistant": response[:200],
            "agents": agents or [],
            "category": self._classify(user_input),
            "timestamp": datetime.now().isoformat(),
        }
        self.short_term.append(entry)
        if len(self.short_term) > 5:
            self.short_term = self.short_term[-3:]
    
    def _classify(self, text: str) -> str:
        """分类用户输入"""
        t = text.lower()
        for cat, keywords in self.CATEGORIES.items():
            if any(kw in t for kw in keywords):
                return cat
        return "general"
    
    def retrieve(self, user_input: str, max_items: int = 3) -> Dict:
        """根据当前输入检索相关上下文"""
        category = self._classify(user_input)
        result = {
            "category": category,
            "short_term": [],
            "long_term": [],
            "profile": {},
        }
        
        # 1. 短期记忆：同类别或最近1轮
        if category in ("greeting", "identity"):
            # 闲聊/身份类：只看最近1轮，不代入任务上下文
            if self.short_term:
                result["short_term"] = self.short_term[-1:]
        elif category in ("task", "creative", "code", "data"):
            # 任务类：看同类别历史
            result["short_term"] = [
                h for h in self.short_term[-3:]
                if h.get("category") == category
            ]
        else:
            result["short_term"] = self.short_term[-2:]
        
        # 2. 长期记忆：精准匹配
        if category == "identity":
            result["profile"] = dict(self.profile)
            result["long_term"] = self.long_term.get("identity", [])[:2]
        elif category == "memory":
            result["long_term"] = self.long_term.get("memory", [])[:3]
        elif category in ("task", "creative"):
            result["long_term"] = self.long_term.get("task", [])[:3]
        
        return result
    
    def remember(self, category: str, key: str, value: str):
        """存入长期记忆"""
        self.long_term[category].append({
            "key": key, "value": value,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.long_term[category]) > 20:
            self.long_term[category] = self.long_term[category][-20:]
    
    def update_profile(self, key: str, value: str):
        """更新用户画像"""
        self.profile[key] = value
    
    def inject(self, user_input: str) -> str:
        """按需注入上下文，返回结构化prompt片段"""
        ctx = self.retrieve(user_input)
        parts = []
        
        # 用户画像（仅在身份类时注入）
        if ctx["profile"]:
            profile_str = "; ".join(f"{k}={v}" for k, v in ctx["profile"].items())
            parts.append(f"【用户信息】{profile_str}")
        
        # 短期记忆（最近对话）
        if ctx["short_term"]:
            lines = []
            for h in ctx["short_term"]:
                lines.append(f"用户: {h['user'][:80]}")
                lines.append(f"系统: {h['assistant'][:80]}")
            parts.append("【当前对话】\n" + "\n".join(lines))
        
        # 长期记忆（仅在相关时）
        if ctx["long_term"]:
            lines = []
            for m in ctx["long_term"]:
                lines.append(f"{m['key']}: {m['value'][:100]}")
            parts.append("【相关记忆】\n" + "\n".join(lines))
        
        return "\n\n".join(parts) if parts else ""


# 全局实例
context_engine = ContextEngine()
