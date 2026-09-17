"""知识库模块 - 常用知识缓存"""

import json
import os
from typing import Optional

class KnowledgeBase:
    """本地知识库"""
    
    def __init__(self):
        self.knowledge = {}
        self._load_common_knowledge()
    
    def _load_common_knowledge(self):
        """加载常用知识"""
        self.knowledge = {
            "python": "Python 是一种高级编程语言，由 Guido van Rossum 创建，以简洁易读著称。",
            "ai": "人工智能（AI）是研究、开发用于模拟和扩展人类智能的理论与技术。",
            "机器学习": "机器学习是 AI 的分支，让计算机从数据中学习规律。",
            "深度学习": "深度学习使用多层神经网络进行特征学习。",
            "docker": "Docker 是容器化平台，用于打包和运行应用。",
            "git": "Git 是分布式版本控制系统。",
            "linux": "Linux 是开源操作系统内核。",
        }
    
    def get(self, topic: str) -> Optional[str]:
        """获取知识"""
        topic_lower = topic.lower()
        for key, value in self.knowledge.items():
            if key in topic_lower or topic_lower in key:
                return value
        return None
    
    def add(self, topic: str, content: str):
        """添加知识"""
        self.knowledge[topic.lower()] = content

knowledge_base = KnowledgeBase()
