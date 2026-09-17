"""服务定位器 - 支持延迟初始化"""

import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class ServiceLocator:
    """服务定位器 - 支持延迟注册"""
    
    _instance: Optional['ServiceLocator'] = None
    _services: Dict[str, Any] = {}
    _factories: Dict[str, Callable] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
            cls._instance._factories = {}
        return cls._instance
    
    def register(self, name: str, service: Any, replace: bool = False):
        """注册服务实例"""
        if name in self._services and not replace:
            logger.warning(f"服务 {name} 已存在，跳过注册")
            return
        self._services[name] = service
        logger.debug(f"服务注册: {name}")
    
    def register_factory(self, name: str, factory: Callable):
        """注册服务工厂（延迟创建）"""
        self._factories[name] = factory
        logger.debug(f"服务工厂注册: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """获取服务"""
        # 先从已注册实例获取
        if name in self._services:
            return self._services[name]
        
        # 尝试从工厂创建
        if name in self._factories:
            try:
                service = self._factories[name]()
                self._services[name] = service
                logger.info(f"服务延迟创建: {name}")
                return service
            except Exception as e:
                logger.error(f"服务创建失败 {name}: {e}")
                return None
        
        return None
    
    def has(self, name: str) -> bool:
        """检查服务是否存在"""
        return name in self._services or name in self._factories
    
    def clear(self):
        """清空所有服务（用于测试）"""
        self._services.clear()
        self._factories.clear()
    
    def list_services(self) -> list:
        """列出所有服务"""
        return list(self._services.keys()) + list(self._factories.keys())


# 全局服务定位器实例
service_locator = ServiceLocator()
