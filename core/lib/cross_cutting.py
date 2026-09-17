"""横切层管理器 - 管理所有横切关注点"""

from typing import Dict, List, Any, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class CutPoint(Enum):
    """切入点点"""
    PRE_PROCESS = "pre_process"      # 处理前
    POST_PROCESS = "post_process"    # 处理后
    ON_ERROR = "on_error"            # 错误时
    ON_SUCCESS = "on_success"        # 成功时


@dataclass
class CrossCuttingHandler:
    """横切处理器"""
    name: str
    cut_point: CutPoint
    handler: Callable
    priority: int = 100
    enabled: bool = True


class CrossCuttingManager:
    """横切层管理器 - 管理所有横切关注点"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self._handlers: Dict[CutPoint, List[CrossCuttingHandler]] = {}
        for cp in CutPoint:
            self._handlers[cp] = []
        self._register_default_handlers()
        print("🔧 横切层管理器已初始化")
    
    def _register_default_handlers(self):
        """注册默认横切处理器"""
        from core.lib.security_hooks import SecurityHooks
        from core.lib.audit_hooks import AuditHooks
        
        # 安全处理器
        self.register(
            name="security_check",
            cut_point=CutPoint.PRE_PROCESS,
            handler=lambda ctx: SecurityHooks.check_dangerous_patterns(ctx.get("input", "")),
            priority=10
        )
        
        # 审计处理器
        self.register(
            name="audit_log",
            cut_point=CutPoint.POST_PROCESS,
            handler=lambda ctx: AuditHooks.log_end(
                ctx.get("user_id", "unknown"),
                ctx.get("response", ""),
                ctx.get("duration_ms", 0)
            ),
            priority=20
        )
        
        # 限流处理器
        self.register(
            name="rate_limit",
            cut_point=CutPoint.PRE_PROCESS,
            handler=lambda ctx: self._check_rate_limit(ctx.get("user_id", "")),
            priority=5
        )
    
    def register(self, name: str, cut_point: CutPoint, handler: Callable, priority: int = 100):
        """注册横切处理器"""
        h = CrossCuttingHandler(name=name, cut_point=cut_point, handler=handler, priority=priority)
        self._handlers[cut_point].append(h)
        self._handlers[cut_point].sort(key=lambda x: x.priority)
        print(f"  ✅ 注册横切处理器: {name} ({cut_point.value})")
    
    def execute(self, cut_point: CutPoint, context: Dict) -> Dict:
        """执行指定切入点的所有处理器"""
        result = {"success": True, "context": context}
        
        for handler in self._handlers.get(cut_point, []):
            if not handler.enabled:
                continue
            try:
                handler_result = handler.handler(context)
                if handler_result is not None:
                    if isinstance(handler_result, tuple) and len(handler_result) == 2:
                        success, msg = handler_result
                        if not success:
                            result["success"] = False
                            result["error"] = msg
                            return result
                    elif isinstance(handler_result, dict):
                        if not handler_result.get("success", True):
                            result["success"] = False
                            result["error"] = handler_result.get("error", "Unknown")
                            return result
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
                return result
        
        return result
    
    def _check_rate_limit(self, user_id: str) -> tuple:
        """频率限制检查"""
        from core.lib.security_hooks import SecurityHooks
        return SecurityHooks.check_rate_limit(user_id, {"max_requests_per_minute": 30})


cross_cutting = CrossCuttingManager()
