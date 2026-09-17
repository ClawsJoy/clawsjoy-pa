"""Prompt 自动升级器 - 简化版"""

import json
import random
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict


class PromptUpgrader:
    """Prompt 自动升级器"""
    
    def __init__(self, agent_name: str = "chat_agent"):
        self.agent_name = agent_name
        self.data_dir = Path(f"data/prompt_evolution/{agent_name}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Prompt 版本
        self.prompt_versions = self._load_versions()
        self.current_version = self.prompt_versions.get("current", 1)
        
        # A/B 测试配置
        self.ab_test_ratio = 0.2
        self.test_version = None
        
        # 统计
        self.stats = defaultdict(lambda: {"success": 0, "total": 0, "scores": []})
        
        print(f"📈 Prompt升级器已启动: {agent_name}")
        print(f"   📚 当前版本: v{self.current_version}")
    
    def _load_versions(self) -> Dict:
        """加载 Prompt 版本"""
        version_file = self.data_dir / "versions.json"
        if version_file.exists():
            try:
                with open(version_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "current": 1,
            "history": [],
            "templates": {
                1: "你是{name}，{description}。请用中文回答，语气友好。",
                2: "你是{name}，{description}。\n\n【性格】{personality}\n\n请用中文回答，语气活泼友好。记住用户的名字和偏好。",
                3: "你是{name}，{description}。\n\n【性格】{personality}\n\n【记忆】{memory}\n\n【规则】1.用中文 2.语气友好 3.记住用户信息 4.不要自称AI\n\n请回答："
            }
        }
    
    def _save_versions(self):
        """保存版本"""
        with open(self.data_dir / "versions.json", 'w') as f:
            json.dump(self.prompt_versions, f, indent=2)
    
    def get_prompt(self, context: Dict) -> tuple:
        """获取 Prompt（简化版，避免 format 冲突）"""
        # A/B 测试
        if random.random() < self.ab_test_ratio and self.test_version:
            version = self.test_version
            is_test = True
        else:
            version = self.current_version
            is_test = False
        
        template = self.prompt_versions["templates"].get(version, self.prompt_versions["templates"][1])
        
        # 简单的字符串替换，避免 format 冲突
        prompt = template
        replacements = [
            ("{name}", context.get("name", "小爪")),
            ("{description}", context.get("description", "智慧聊天助手")),
            ("{personality}", context.get("personality", "活泼开朗，喜欢交朋友，有点皮")),
            ("{memory}", context.get("memory", "")),
        ]
        
        for key, value in replacements:
            prompt = prompt.replace(key, value)
        
        return prompt, version, is_test
    
    def record_feedback(self, version: int, user_input: str, response: str, 
                        user_rating: int = None, quality_score: float = None):
        """记录反馈"""
        if quality_score is None:
            quality_score = self._auto_evaluate(response)
        
        self.stats[version]["total"] += 1
        self.stats[version]["scores"].append(quality_score)
        
        if user_rating and user_rating >= 4:
            self.stats[version]["success"] += 1
    
    def _auto_evaluate(self, response: str) -> float:
        """自动评估响应质量"""
        score = 0.5
        if any('\u4e00' <= c <= '\u9fff' for c in response):
            score += 0.2
        if 20 < len(response) < 300:
            score += 0.1
        if "小爪" in response or "我是" in response:
            score += 0.1
        return min(score, 1.0)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        result = {}
        for version, data in self.stats.items():
            if data["scores"]:
                result[version] = {
                    "total": data["total"],
                    "avg_quality": sum(data["scores"]) / len(data["scores"]),
                }
        
        return {
            "current_version": self.current_version,
            "test_version": self.test_version,
            "stats": result,
        }


def get_prompt_upgrader(agent_name: str) -> PromptUpgrader:
    from core.lib.prompt_upgrader import prompt_upgraders
    if agent_name not in prompt_upgraders:
        prompt_upgraders[agent_name] = PromptUpgrader(agent_name)
    return prompt_upgraders[agent_name]


# 全局实例
prompt_upgraders = {}
