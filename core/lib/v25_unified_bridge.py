#!/usr/bin/env python3
"""
2.5 层 JSON 统一桥梁 - 集成所有核心能力 + Redis 持久化
整合: agent_capability_loader, decision_evaluator, memory_layers, capability_recommender
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# 导入 Redis 管理器
try:
    from core.lib.redis_manager import redis_manager
except ImportError:
    print("⚠️ redis_manager 导入失败，使用本地内存")
    redis_manager = None

class V25UnifiedBridge:
    """2.5 层 JSON 统一桥梁 - 集成所有核心能力 + Redis 持久化"""
    
    VERSION = "2.5"
    
    # 记忆默认 TTL（秒），1小时
    DEFAULT_MEMORY_TTL = 3600
    
    def __init__(self):
        print("🌉 2.5 层 JSON 统一桥梁初始化")
        self._memory = None
        self._capability_loader = None
        self._evaluator = None
        self._recommender = None
        
        # Redis 连接状态
        self._redis_enabled = redis_manager is not None
        
        # 本地内存缓存（作为 Redis 不可用时的降级）
        self._local_memory = {}
        
        # 记忆持久化文件（本地备份）
        self._memory_file = Path("data/memory.json")
        self._memory_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_memory_from_file()
        
        # 初始化所有子系统
        self._init_all()
    
    def _load_memory_from_file(self):
        """从文件加载记忆（本地备份）"""
        if self._memory_file.exists():
            try:
                with open(self._memory_file, 'r') as f:
                    self._local_memory = json.load(f)
                print(f"   ✅ 从文件加载了 {len(self._local_memory)} 个用户的记忆")
            except Exception as e:
                print(f"   ⚠️ 加载记忆失败: {e}")
                self._local_memory = {}
        else:
            self._local_memory = {}

    def _save_memory_to_file(self):
        """保存记忆到文件（本地备份）"""
        try:
            with open(self._memory_file, 'w') as f:
                json.dump(self._local_memory, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"   ⚠️ 保存记忆失败: {e}")
            return False
    
    def _init_all(self):
        """初始化所有子系统"""
        # 1. 记忆系统
        self._init_memory()
        # 2. Agent 能力加载器
        self._init_capability_loader()
        # 3. 决策评估器
        self._init_evaluator()
        # 4. 能力推荐器
        self._init_recommender()
    
    def _init_memory(self):
        """初始化记忆系统"""
        try:
            from core.lib.memory_layers import MemoryLayers
            self._memory = MemoryLayers()
            print("   ✅ MemoryLayers 记忆系统已加载")
        except Exception as e:
            print(f"   ⚠️ MemoryLayers 加载失败: {e}")
            self._memory = None
    
    def _init_capability_loader(self):
        """初始化 Agent 能力加载器"""
        try:
            from core.lib.agent_capability_loader import AgentCapabilityLoader
            self._capability_loader = AgentCapabilityLoader()
            self._capabilities = self._capability_loader.load_all()
            print(f"   ✅ AgentCapabilityLoader 已加载 ({len(self._capabilities)} 个能力)")
        except Exception as e:
            print(f"   ⚠️ AgentCapabilityLoader 加载失败: {e}")
            self._capability_loader = None
            self._capabilities = []
    
    def _init_evaluator(self):
        """初始化决策评估器"""
        try:
            from core.lib.decision_evaluator import decision_evaluator
            self._evaluator = decision_evaluator
            print("   ✅ DecisionEvaluator 已加载")
        except Exception as e:
            print(f"   ⚠️ DecisionEvaluator 加载失败: {e}")
            self._evaluator = None
    
    def _init_recommender(self):
        """初始化能力推荐器"""
        try:
            from core.lib.capability_recommender import CapabilityRecommender
            self._recommender = CapabilityRecommender()
            print("   ✅ CapabilityRecommender 已加载")
        except Exception as e:
            print(f"   ⚠️ CapabilityRecommender 加载失败: {e}")
            self._recommender = None
    
    def create_request(self, raw_input: str, action: str = "chat", 
                       target: str = "text", user_id: str = "default",
                       session_id: Optional[str] = None) -> Dict:
        """创建 2.5 层 JSON 请求"""
        return {
            "version": self.VERSION,
            "session_id": session_id or str(uuid.uuid4())[:8],
            "user_id": user_id,
            "thread_id": str(uuid.uuid4())[:8],
            "turn": 0,
            "raw_input": raw_input,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "keywords": [],
            "confidence": 0.85,
            "params": {"context": {}, "options": {}},
            "output_type": target,
            "output_content": "",
            "output_data": {},
            "status": "pending",
            "next": "continue"
        }
    
    def create_response(self, request: Dict, output_content: str,
                        status: str = "completed", output_data: Optional[Dict] = None) -> Dict:
        """创建 2.5 层 JSON 响应"""
        return {
            "version": self.VERSION,
            "session_id": request.get("session_id"),
            "user_id": request.get("user_id"),
            "thread_id": request.get("thread_id"),
            "turn": request.get("turn", 0) + 1,
            "raw_input": request.get("raw_input", ""),
            "timestamp": datetime.now().isoformat(),
            "action": request.get("action", "chat"),
            "target": request.get("target", "text"),
            "keywords": request.get("keywords", []),
            "confidence": request.get("confidence", 0.85),
            "params": request.get("params", {}),
            "output_type": request.get("output_type", "text"),
            "output_content": output_content,
            "output_data": output_data or {},
            "status": status,
            "next": "done"
        }
    
    # ========== 记忆相关 (Redis + 本地备份) ==========
    
    def _get_redis_key(self, user_id: str, key: str, session_id: Optional[str] = None) -> str:
        """
        生成 Redis 键
        包含 session_id 实现会话隔离
        """
        if session_id:
            return f"memory:{user_id}:{session_id}:{key}"
        return f"memory:{user_id}:{key}"
    
    def _get_redis_session_key(self, user_id: str, session_id: str) -> str:
        """获取会话的所有记忆键前缀"""
        return f"memory:{user_id}:{session_id}:"
    
    def _store_local(self, user_id: str, key: str, value: Any, session_id: Optional[str] = None):
        """
        存储记忆 (Redis + 本地备份)
        
        Args:
            user_id: 用户ID
            key: 记忆键
            value: 记忆值
            session_id: 会话ID（用于隔离）
        """
        # 1. 存到本地内存（包含 session_id 信息）
        memory_key = f"{session_id}:{key}" if session_id else key
        if user_id not in self._local_memory:
            self._local_memory[user_id] = {}
        self._local_memory[user_id][memory_key] = value
        
        # 2. 存到 Redis（如果可用）
        if self._redis_enabled:
            try:
                redis_key = self._get_redis_key(user_id, key, session_id)
                data = {
                    "value": value,
                    "user_id": user_id,
                    "key": key,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                # 设置 TTL（默认 1 小时）
                ttl = self.DEFAULT_MEMORY_TTL
                redis_manager.set(redis_key, data, ttl=ttl)
            except Exception as e:
                print(f"   ⚠️ Redis 存储失败: {e}")
        
        # 3. 保存到文件（备份）
        self._save_memory_to_file()
    
    def _get_local(self, user_id: str, key: str, session_id: Optional[str] = None) -> Optional[Any]:
        """
        读取记忆 (Redis 优先，本地内存降级)
        
        Args:
            user_id: 用户ID
            key: 记忆键
            session_id: 会话ID（用于隔离）
        """
        # 1. 先查 Redis
        if self._redis_enabled:
            try:
                redis_key = self._get_redis_key(user_id, key, session_id)
                data = redis_manager.get(redis_key)
                if data and isinstance(data, dict):
                    value = data.get("value")
                    if value is not None:
                        # 同步到本地内存
                        memory_key = f"{session_id}:{key}" if session_id else key
                        if user_id not in self._local_memory:
                            self._local_memory[user_id] = {}
                        self._local_memory[user_id][memory_key] = value
                        return value
            except Exception as e:
                print(f"   ⚠️ Redis 读取失败: {e}")
        
        # 2. 降级到本地内存
        memory_key = f"{session_id}:{key}" if session_id else key
        return self._local_memory.get(user_id, {}).get(memory_key)
    
    def _get_all_session_memories(self, user_id: str, session_id: str) -> Dict:
        """获取某个会话的所有记忆"""
        result = {}
        
        # 1. 从 Redis 获取
        if self._redis_enabled:
            try:
                prefix = self._get_redis_session_key(user_id, session_id)
                # Redis 不支持前缀扫描所有键，这里用本地内存降级
            except Exception as e:
                print(f"   ⚠️ Redis 会话扫描失败: {e}")
        
        # 2. 从本地内存获取
        prefix = f"{session_id}:"
        user_memories = self._local_memory.get(user_id, {})
        for k, v in user_memories.items():
            if k.startswith(prefix):
                key = k[len(prefix):]
                result[key] = v
        
        return result
    
    def remember(self, user_id: str, key: str, value: Any, session_id: Optional[str] = None) -> Dict:
        """记住信息 (Redis + 本地备份，支持会话隔离)"""
        request = self.create_request(f"记住 {key}", "memory", "text", user_id, session_id)
        self._store_local(user_id, key, value, session_id)

        try:
            if self._memory:
                session_id = session_id or str(uuid.uuid4())[:8]
                self._memory.add_session_memory(session_id, f"{key}: {value}", f"记住 {key}")
                self._memory.add_long_term_memory(f"{key}: {value}", importance=1)

                return self.create_response(
                    request,
                    f"已记住: {key}",
                    output_data={
                        "key": key, 
                        "value": value, 
                        "user_id": user_id, 
                        "session_id": session_id, 
                        "success": True,
                        "ttl_seconds": self.DEFAULT_MEMORY_TTL
                    }
                )
            else:
                return self.create_response(
                    request,
                    f"已记住: {key} (本地)",
                    output_data={
                        "key": key, 
                        "value": value, 
                        "user_id": user_id, 
                        "session_id": session_id,
                        "note": "本地存储"
                    }
                )
        except Exception as e:
            return self.create_response(
                request,
                f"已记住: {key} (本地)",
                output_data={
                    "key": key, 
                    "value": value, 
                    "user_id": user_id, 
                    "session_id": session_id,
                    "note": f"本地 (错误: {str(e)})"
                }
            )
    
    def recall(self, user_id: str, key: str, session_id: Optional[str] = None) -> Dict:
        """回忆信息 (Redis 优先，支持会话隔离)"""
        request = self.create_request(f"回忆 {key}", "memory", "text", user_id, session_id)

        try:
            # 1. 先从 Redis/本地读取（按 session 隔离）
            value = self._get_local(user_id, key, session_id)

            # 2. 如果本地没有，尝试从 MemoryLayers 读取
            if value is None and self._memory:
                memories = self._memory.get_long_term_memory(limit=20)
                for mem in memories:
                    if key in mem.get("content", ""):
                        value = mem.get("content", "").replace(f"{key}: ", "")
                        # 同步到 Redis/本地
                        if value:
                            self._store_local(user_id, key, value, session_id)
                        break

                if value is None and session_id:
                    session_memories = self._memory.get_session_memory(session_id, limit=10)
                    for mem in session_memories:
                        if key in mem.get("user_input", ""):
                            value = mem.get("user_input", "").replace(f"{key}: ", "")
                            if value:
                                self._store_local(user_id, key, value, session_id)
                            break

            if value is not None:
                return self.create_response(
                    request,
                    f"回忆 {key}: {value}",
                    output_data={"key": key, "value": value, "user_id": user_id, "session_id": session_id, "found": True}
                )
            else:
                return self.create_response(
                    request,
                    f"未找到: {key}",
                    status="failed",
                    output_data={"key": key, "user_id": user_id, "session_id": session_id, "found": False}
                )
        except Exception as e:
            return self.create_response(
                request,
                f"回忆失败: {str(e)}",
                status="failed",
                output_data={"error": str(e)}
            )
    
    # ========== Agent 能力相关 ==========
    def get_all_agents(self) -> List[Dict]:
        """获取所有 Agent 能力"""
        return self._capabilities
    
    def get_agent_capability(self, agent_name: str) -> Optional[Dict]:
        """获取特定 Agent 的能力"""
        for cap in self._capabilities:
            if cap.get("name") == agent_name or cap.get("agent_name") == agent_name:
                return cap
        return None
    
    # ========== 决策评估相关 ==========
    def evaluate_decision(self, suggestion: str) -> Dict:
        """评估决策风险"""
        if self._evaluator:
            try:
                return self._evaluator.evaluate(suggestion)
            except Exception as e:
                return {"error": str(e), "should_execute": False}
        return {"error": "评估器不可用", "should_execute": False}
    
    # ========== 能力推荐相关 ==========
    def recommend_agents(self, user_id: str, context: Dict = None) -> List[str]:
        """推荐 Agent"""
        if self._recommender:
            try:
                context = context or {}
                return self._recommender.recommend(user_id, context)
            except Exception as e:
                return [f"推荐失败: {e}"]
        return ["推荐器不可用"]
    
    # ========== 工具相关 ==========
    def execute_tool(self, user_id: str, tool_name: str, params: Dict, session_id: Optional[str] = None) -> Dict:
        """执行工具"""
        request = self.create_request(f"执行工具 {tool_name}", "tool", "text", user_id, session_id)
        
        try:
            from core.lib.tool_system import tool_system
            result = tool_system.execute(tool_name, params, user_id)
            if result.get("success"):
                return self.create_response(
                    request,
                    result.get("result", "执行成功"),
                    output_data=result
                )
            else:
                return self.create_response(
                    request,
                    result.get("error", "执行失败"),
                    status="failed",
                    output_data=result
                )
        except Exception as e:
            return self.create_response(
                request,
                f"执行工具失败: {str(e)}",
                status="failed"
            )
    
    # ========== 系统状态 ==========
    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "version": self.VERSION,
            "memory": "loaded" if self._memory else "disabled",
            "capability_loader": "loaded" if self._capability_loader else "disabled",
            "evaluator": "loaded" if self._evaluator else "disabled",
            "recommender": "loaded" if self._recommender else "disabled",
            "capabilities_count": len(self._capabilities),
            "memory_count": len(self._local_memory),
            "redis_enabled": self._redis_enabled,
            "default_ttl_seconds": self.DEFAULT_MEMORY_TTL
        }

# 全局实例
v25_bridge = V25UnifiedBridge()
