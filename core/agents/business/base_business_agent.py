#!/usr/bin/env python3
"""业务基类 - 所有业务 Agent 的统一基类"""

import time
import hashlib
from datetime import datetime
from abc import abstractmethod
from typing import Dict, Optional, Any
from core.agents.base.smart_agent import SmartAgent
from core.lib.safety_guard import set_safe_recursion_limit


class BusinessAgent(SmartAgent):
    """
    业务智能体统一基类
    
    所有业务 Agent (V4) 必须继承此类并实现 _execute_business 方法。
    ⚠️ 不要覆盖 process 方法，否则会破坏模板方法模式。
    """

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._cache = {}
        self._stats = {
            "total_processed": 0,
            "total_time_ms": 0
        }
        # 确保递归限制安全
        set_safe_recursion_limit()
    
    # ========== 统一入口（模板方法，子类不要覆盖） ==========
    
    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        统一入口 - 模板方法
        
        ⚠️ 子类不要覆盖此方法，请实现 _execute_business
        """
        start_time = time.time()
        
        # 缓存检查
        cache_key = hashlib.md5(f"{user_input}:{self.name}".encode()).hexdigest()
        if hasattr(self, '_cache') and cache_key in self._cache:
            return self._cache[cache_key]
        
        # 执行业务逻辑（子类实现）
        try:
            result = self._execute_business(user_input, context)
        except RecursionError as e:
            result = self._handle_recursion_error(e)
        except Exception as e:
            result = self._handle_error(e)
        
        # 确保结果包含必要字段
        if "success" not in result:
            result["success"] = True
        if "response" not in result:
            result["response"] = result.get("output_content", "处理完成")
        if "output_content" not in result:
            result["output_content"] = result.get("response", "")
        
        # 添加元数据
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["_meta"] = {
            "agent": getattr(self, 'name', 'unknown'),
            "elapsed_ms": elapsed_ms,
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存存储
        if not hasattr(self, '_cache'):
            self._cache = {}
        self._cache[cache_key] = result
        
        if not hasattr(self, '_stats'):
            self._stats = {}
        self._stats["total_processed"] = self._stats.get("total_processed", 0) + 1
        self._stats["total_time_ms"] = self._stats.get("total_time_ms", 0) + elapsed_ms
        
        return result
    
    # ========== 子类必须实现 ==========
    
    @abstractmethod
    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        业务逻辑实现 - 子类必须实现此方法
        
        ⚠️ 不要在此方法中调用 self.process()，否则会造成无限递归。
        """
        raise NotImplementedError("子类必须实现 _execute_business 方法")
    
    # ========== 可选覆盖的方法 ==========
    
    def _handle_error(self, error: Exception) -> Dict:
        """错误处理，子类可覆盖"""
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(error),
            "response": f"❌ 处理失败: {error}"
        }
    
    def _handle_recursion_error(self, error: Exception) -> Dict:
        """递归错误处理"""
        return {
            "success": False,
            "error": "递归深度超限",
            "response": "❌ 检测到递归调用，请检查 Agent 实现是否正确覆盖了 _execute_business"
        }
    
    # ========== 兼容性方法（保留旧接口） ==========
    
    def handle(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """兼容旧接口，内部调用 process"""
        return self.process(user_input, context)
    
    def handle_json(self, data: Dict) -> Dict:
        """处理 JSON 格式输入"""
        user_input = data.get("message", "") or data.get("raw_input", "")
        agent_name = data.get("agent")
        user_id = data.get("user_id", self.user_id)
        
        # 如果指定了其他 Agent，需要重新获取
        if agent_name and agent_name != self.name:
            from core.agents.wisdom.wisdom_factory import wisdom_factory
            other_agent = wisdom_factory.get_wisdom_agent(agent_name, user_id)
            if other_agent:
                return other_agent.process(user_input)
        
        return self.process(user_input)
