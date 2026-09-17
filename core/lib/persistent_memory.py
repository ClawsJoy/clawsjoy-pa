"""持久化记忆增强 - 跨会话保存用户记忆"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

class PersistentMemory:
    """持久化记忆管理器"""
    
    def __init__(self, storage_dir="data/memories"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}
    
    def _get_user_file(self, user_id: str) -> Path:
        """获取用户记忆文件路径"""
        return self.storage_dir / f"{user_id}.json"
    
    def save_memory(self, user_id: str, memory: Dict):
        """保存用户记忆"""
        # 更新缓存
        if user_id not in self._cache:
            self._cache[user_id] = {}
        self._cache[user_id].update(memory)
        
        # 保存到文件
        file_path = self._get_user_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self._cache[user_id], f, ensure_ascii=False, indent=2)
    
    def load_memory(self, user_id: str) -> Dict:
        """加载用户记忆"""
        # 先从缓存读取
        if user_id in self._cache:
            return self._cache[user_id]
        
        # 从文件读取
        file_path = self._get_user_file(user_id)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                self._cache[user_id] = memory
                return memory
        
        return {}
    
    def update_conversation(self, user_id: str, user_message: str, assistant_response: str):
        """更新对话历史（持久化）"""
        memory = self.load_memory(user_id)
        
        if 'conversations' not in memory:
            memory['conversations'] = []
        
        # 添加新对话
        memory['conversations'].append({
            'user': user_message[:200],
            'assistant': assistant_response[:200],
            'timestamp': __import__('time').time()
        })
        
        # 只保留最近 50 条
        if len(memory['conversations']) > 50:
            memory['conversations'] = memory['conversations'][-50:]
        
        # 提取用户信息
        self._extract_user_info(memory, user_message)
        
        self.save_memory(user_id, memory)
    
    def _extract_user_info(self, memory: Dict, message: str):
        """提取用户信息"""
        import re
        
        if 'profile' not in memory:
            memory['profile'] = {}
        
        # 提取名字
        name_match = re.search(r'我叫([^，,。]+)', message)
        if name_match:
            memory['profile']['name'] = name_match.group(1).strip()
        
        # 提取偏好
        pref_match = re.search(r'我喜欢([^，,。]+)', message)
        if pref_match:
            prefs = memory['profile'].get('preferences', [])
            pref = pref_match.group(1).strip()
            if pref not in prefs:
                prefs.append(pref)
                memory['profile']['preferences'] = prefs
    
    def get_conversation_context(self, user_id: str, last_n: int = 5) -> str:
        """获取最近的对话上下文"""
        memory = self.load_memory(user_id)
        conversations = memory.get('conversations', [])
        
        if not conversations:
            return ""
        
        context = "【历史对话】\n"
        for conv in conversations[-last_n:]:
            context += f"用户: {conv['user']}\n"
            context += f"助手: {conv['assistant']}\n"
        
        return context
    
    def clear_memory(self, user_id: str):
        """清除用户记忆"""
        if user_id in self._cache:
            del self._cache[user_id]
        file_path = self._get_user_file(user_id)
        if file_path.exists():
            file_path.unlink()

# 全局实例
persistent_memory = PersistentMemory()
