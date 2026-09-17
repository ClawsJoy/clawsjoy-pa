# -*- coding: utf-8 -*-
"""ClawsJoy OS 执行上下文容器 — Cordis Context 的 Python 简化实现。

三层职责:
1. 服务容器: provide/get/has 按名存取服务(全局 + per-scope shadow)
2. 事件总线: on/emit(广播) + waterfall(可拒绝, 监听器返回非 None 短路)
3. 插件挂载: mount/unmount_all(逆序回滚, 模拟 reversible effects)

P0 边界: 只建骨架 + 收编引用, 不迁移守卫、不改执行语义、零行为变化。
"""
from __future__ import annotations
import threading
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class V9Scope:
    """per-session(或 per-agent) 作用域: 隔离的服务注册与事件监听。

    一个 scope 对应一个 session_key(如 "user:session" 或 "user:session:agent")。
    作用域内注册的服务/监听器在 dispose_scope 时整体清理 —— 模拟 Cordis
    reversible effects(注册随作用域销毁自动回滚)。
    """

    def __init__(self, key: str, parent: 'V9Context'):
        self.key = key
        self._parent = parent
        self._services: Dict[str, Any] = {}     # name -> service
        self._listeners: Dict[str, List[Callable]] = {}  # event -> [fn]
        self._plugins: List[Any] = []            # scope 内挂载的插件
        self._disposed = False

    # ---- 服务(作用域内注册, shadow 全局同名) ----
    def provide(self, name: str, service: Any) -> None:
        self._services[name] = service

    def get(self, name: str) -> Any:
        if name in self._services:
            return self._services[name]
        return self._parent.get(name)   # 未命中回退全局

    def has(self, name: str) -> bool:
        return name in self._services or self._parent.has(name)

    # ---- 事件(作用域内监听) ----
    def on(self, event: str, fn: Callable) -> None:
        self._listeners.setdefault(event, []).append(fn)

    def remove_listener(self, event: str, fn: Callable) -> bool:
        """移除作用域内监听器。返回是否移除。"""
        listeners = self._listeners.get(event)
        if not listeners:
            return False
        try:
            listeners.remove(fn)
            return True
        except ValueError:
            return False

    def dispose(self) -> None:
        """销毁作用域: 逆序卸载插件 → 清空服务与监听。幂等。"""
        if self._disposed:
            return
        for plugin in reversed(self._plugins):
            try:
                plugin.dispose()
            except Exception as e:
                logger.warning(f"[V9Scope:{self.key}] 插件 {getattr(plugin, 'name', type(plugin).__name__)} dispose 失败: {e}")
        self._plugins.clear()
        self._services.clear()
        self._listeners.clear()
        self._disposed = True


class V9Context:
    """进程级上下文容器(全局单例, 由 core.os 模块持有)。"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._listeners: Dict[str, List[Callable]] = {}
        self._scopes: Dict[str, V9Scope] = {}
        self._plugins: List[Any] = []
        self._scope_lock = threading.Lock()
        self._plugin_lock = threading.Lock()

    # ==================== 服务 ====================
    def provide(self, name: str, service: Any) -> None:
        """注册全局服务。同名重复注册抛 ValueError(防止静默覆盖)。"""
        if name in self._services:
            raise ValueError(f"service '{name}' 已注册")
        self._services[name] = service

    def provide_override(self, name: str, service: Any) -> None:
        """覆盖注册(测试/热替换用, 允许同名替换)。"""
        self._services[name] = service

    def get(self, name: str) -> Any:
        """取全局服务。未注册抛 KeyError。"""
        return self._services[name]

    def get_opt(self, name: str) -> Optional[Any]:
        """取全局服务, 未注册返回 None(可选依赖, 对齐 Harness ctx.get 可选语义)。"""
        return self._services.get(name)

    def has(self, name: str) -> bool:
        return name in self._services

    # ==================== 作用域 ====================
    def scope(self, key: str) -> V9Scope:
        """惰性获取/创建会话作用域。线程安全。"""
        with self._scope_lock:
            s = self._scopes.get(key)
            if s is None:
                s = V9Scope(key, self)
                self._scopes[key] = s
            return s

    def dispose_scope(self, key: str) -> bool:
        """销毁作用域: 插件回滚 + 服务/监听清理 + 从注册表移除。返回是否销毁。"""
        with self._scope_lock:
            s = self._scopes.pop(key, None)
        if s is None:
            return False
        s.dispose()
        logger.info(f"[V9Context] 作用域 {key} 已销毁(插件回滚/服务清理)")
        return True

    def list_scopes(self) -> List[str]:
        return list(self._scopes.keys())

    # ==================== 事件 ====================
    def on(self, event: str, fn: Callable, scope: Optional[str] = None) -> None:
        """注册监听器。scope 为空注册到全局, 否则注册到该作用域。

        fn 签名: fn(payload: dict) -> Any
          - emit 模式: 返回值忽略
          - waterfall 模式: 返回非 None 即短路(见 waterfall)
        """
        if scope is not None:
            self.scope(scope).on(event, fn)
            return
        self._listeners.setdefault(event, []).append(fn)

    def remove_listener(self, event: str, fn: Callable, scope: Optional[str] = None) -> bool:
        """移除监听器(插件 dispose 回滚用)。返回是否移除。"""
        if scope is not None:
            s = self._scopes.get(scope)
            if s is None:
                return False
            return s.remove_listener(event, fn)
        listeners = self._listeners.get(event)
        if not listeners:
            return False
        try:
            listeners.remove(fn)
            return True
        except ValueError:
            return False

    def emit(self, event: str, payload: Optional[dict] = None, scope: Optional[str] = None) -> None:
        """广播事件: 全局监听器 + (若有 scope)该作用域监听器。监听器异常相互隔离。"""
        payload = payload or {}
        listeners = list(self._listeners.get(event, []))
        if scope is not None:
            s = self._scopes.get(scope)
            if s is not None:
                listeners += list(s._listeners.get(event, []))
        for fn in listeners:
            try:
                fn(payload)
            except Exception as e:
                logger.warning(f"[V9Context] 事件 {event} 监听器异常(隔离): {e}")

    def waterfall(self, event: str, payload: Optional[dict] = None,
                  fallback: Optional[Callable] = None,
                  scope: Optional[str] = None) -> Any:
        """可拒绝瀑布: 按注册序执行监听器, 首个返回非 None 者短路并返回其值。

        对齐 Harness tools/pre-execute 语义:
          - 监听器返回 {"deny": True, "reason": ...} 即拒绝(后续监听器不再执行)
          - 返回 None 委托下一个(next() 语义)
          - 全部放行且提供 fallback 时执行 fallback
        """
        payload = payload or {}
        listeners = list(self._listeners.get(event, []))
        if scope is not None:
            s = self._scopes.get(scope)
            if s is not None:
                listeners += list(s._listeners.get(event, []))
        for fn in listeners:
            try:
                result = fn(payload)
            except Exception as e:
                logger.warning(f"[V9Context] 瀑布 {event} 监听器异常(视为放行): {e}")
                continue
            if result is not None:
                return result
        if fallback is not None:
            return fallback(payload)
        return None

    # ==================== 插件 ====================
    def mount(self, plugin: Any, scope: Optional[str] = None) -> None:
        """挂载插件: 调用 plugin.apply(ctx[, scope])。scope 非空时挂到该作用域。

        挂载后记录到插件表, 供 unmount/unmount_all 逆序回滚。
        """
        if scope is not None:
            s = self.scope(scope)
            plugin._ctx = self
            plugin._scope = s
            s._plugins.append(plugin)
            plugin.apply(self, s)
            return
        with self._plugin_lock:
            plugin._ctx = self
            plugin._scope = None
            self._plugins.append(plugin)
        plugin.apply(self)

    def unmount(self, plugin: Any) -> bool:
        """卸载单个插件: 调用 plugin.dispose() 并移出注册表。幂等。"""
        try:
            plugin.dispose()
        except Exception as e:
            logger.warning(f"[V9Context] 插件 {getattr(plugin, 'name', type(plugin).__name__)} dispose 失败: {e}")
        try:
            if plugin._scope is not None:
                plugin._scope._plugins.remove(plugin)
            else:
                self._plugins.remove(plugin)
            return True
        except ValueError:
            return False

    def unmount_all(self) -> int:
        """逆序卸载全部全局插件(scope 内插件随 scope.dispose 清理)。返回卸载数。"""
        count = 0
        with self._plugin_lock:
            for plugin in reversed(list(self._plugins)):
                try:
                    plugin.dispose()
                except Exception as e:
                    logger.warning(f"[V9Context] 插件 {getattr(plugin, 'name', type(plugin).__name__)} dispose 失败: {e}")
                count += 1
            self._plugins.clear()
        return count

    def reset(self) -> None:
        """完全重置(测试用): 卸载插件 + 销毁全部作用域 + 清空服务。"""
        self.unmount_all()
        for key in list(self._scopes.keys()):
            self.dispose_scope(key)
        self._services.clear()
        self._listeners.clear()


# ============ 全局单例(模块级, 供全仓库 import) ============
_v9ctx: Optional[V9Context] = None
_ctx_lock = threading.Lock()


def get_v9_context() -> V9Context:
    """进程级单例访问(延迟初始化, 避免 import 顺序问题)。"""
    global _v9ctx
    if _v9ctx is None:
        with _ctx_lock:
            if _v9ctx is None:
                _v9ctx = V9Context()
    return _v9ctx


# 兼容别名: OSContext == V9Context(P0 用 V9Context 命名落地, P3 升格 OSContext)
OSContext = V9Context
