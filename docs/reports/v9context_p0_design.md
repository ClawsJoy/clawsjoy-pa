# V9Context P0 详细设计文档

> 日期：2026-08-17 | 状态：设计确认稿（确认后实施）
> 依据：v9_pluginization_plan.md（三期方案）+ oscontext_evolution.md（OSContext 演化）
> 定位：P0 = 服务容器 + 事件总线 + 作用域 + 插件挂载的地基，**零行为变化**，全量 256 测试不降。

---

## 0. 设计原则

1. **零行为变化**：P0 只建骨架，不迁移守卫、不改执行语义；现有函数调用路径保持原样
2. **shim 兼容优先**：单例先收编进容器，业务代码通过 shim 层访问，分文件迁移到 `ctx.get`
3. **渐进替换**：`shared_state` 30+ dict 只收编"容器化无风险"的一批，其余留 P2
4. **命名定调**：类名 `OSContext`(核心) + `V9Context` 别名(兼容过渡)，模块落位 `core/os/`
5. **可测试**：每个机制(容器/作用域/事件/插件)有独立单元测试，全量回归兜底

---

## 1. 数据结构

### 1.1 `core/os/context.py` — V9Context（OSContext）主类

```python
# -*- coding: utf-8 -*-
"""ClawsJoy OS 执行上下文容器 — Cordis Context 的 Python 简化实现。

三层职责：
1. 服务容器: provide/get/has 按名存取服务(全局 + per-scope shadow)
2. 事件总线: on/emit(广播) + waterfall(可拒绝, 监听器返回非 None 短路)
3. 插件挂载: mount/unmount_all(逆序回滚, 模拟 reversible effects)
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
        self._plugins: List[V9Plugin] = []       # scope 内挂载的插件
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

    def dispose(self) -> None:
        """销毁作用域: 逆序卸载插件 → 清空服务与监听。幂等。"""
        if self._disposed:
            return
        for plugin in reversed(self._plugins):
            try:
                plugin.dispose()
            except Exception as e:
                logger.warning(f"[V9Scope:{self.key}] 插件 {plugin.name} dispose 失败: {e}")
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
        self._plugins: List[V9Plugin] = []
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
        """取全局服务, 未注册返回 None(可选依赖, 对齐 Harness 的 ctx.get 可选语义)。"""
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
    def mount(self, plugin: V9Plugin, scope: Optional[str] = None) -> None:
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

    def unmount(self, plugin: V9Plugin) -> bool:
        """卸载单个插件: 调用 plugin.dispose() 并移出注册表。幂等。"""
        try:
            plugin.dispose()
        except Exception as e:
            logger.warning(f"[V9Context] 插件 {plugin.name} dispose 失败: {e}")
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
                    logger.warning(f"[V9Context] 插件 {plugin.name} dispose 失败: {e}")
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
```

### 1.2 `core/os/plugin.py` — V9Plugin 基类

```python
# -*- coding: utf-8 -*-
"""插件基类 — 对齐 Cordis plugin.apply(ctx)。"""
from __future__ import annotations
from typing import Any, Optional


class V9Plugin:
    """所有插件基类。

    生命周期:
      apply(ctx[, scope])  挂载时调用: 注册服务/监听器/挂子插件
      dispose()            卸载时调用: 逆序回滚 apply 的注册(释放资源)

    约定:
      - apply 内通过 ctx.on/provide 注册的所有东西, dispose 必须撤销
      - 插件应保持无状态(状态放 ctx/scope)
    """

    name: str = ""

    def __init__(self):
        self._ctx: Any = None
        self._scope: Any = None

    def apply(self, ctx: Any, scope: Any = None) -> None:
        """挂载钩子。子类覆盖。ctx=V9Context, scope=V9Scope 或 None。"""
        raise NotImplementedError

    def dispose(self) -> None:
        """卸载钩子。子类覆盖(逆序回滚 apply 的注册)。默认空操作。"""

    def __repr__(self) -> str:
        return f"<V9Plugin {self.name or type(self).__name__}>"
```

### 1.3 模块布局

```
core/os/
  __init__.py        # 导出 V9Context/OSContext/V9Scope/V9Plugin/get_v9_context
  context.py         # V9Context + V9Scope
  plugin.py          # V9Plugin
  events.py          # (预留) 事件名常量表, P1 守卫插件用
  services.py        # (预留) 服务名常量表
```

---

## 2. 接口签名总表

### 2.1 V9Context

| 方法 | 签名 | 返回值 | 语义 |
|---|---|---|---|
| `provide` | `(name: str, service: Any) -> None` | None | 注册全局服务, 同名重复抛 ValueError |
| `provide_override` | `(name: str, service: Any) -> None` | None | 覆盖注册(测试/热替换) |
| `get` | `(name: str) -> Any` | 服务实例 | 取全局服务, 未注册抛 KeyError |
| `get_opt` | `(name: str) -> Optional[Any]` | 服务或 None | 可选依赖(对齐 Harness ctx.get 可选语义) |
| `has` | `(name: str) -> bool` | bool | 服务是否存在 |
| `scope` | `(key: str) -> V9Scope` | V9Scope | 惰性获取/创建会话作用域(线程安全) |
| `dispose_scope` | `(key: str) -> bool` | bool | 销毁作用域(插件回滚+清理), 返回是否销毁 |
| `list_scopes` | `() -> List[str]` | key 列表 | 存活作用域 |
| `on` | `(event: str, fn: Callable, scope: Optional[str]=None) -> None` | None | 注册监听器(全局或作用域) |
| `emit` | `(event: str, payload: Optional[dict]=None, scope: Optional[str]=None) -> None` | None | 广播, 监听器异常隔离 |
| `waterfall` | `(event: str, payload: Optional[dict]=None, fallback: Optional[Callable]=None, scope: Optional[str]=None) -> Any` | 首个非 None 返回值或 fallback 结果或 None | 可拒绝瀑布 |
| `mount` | `(plugin: V9Plugin, scope: Optional[str]=None) -> None` | None | 挂载插件(全局或作用域) |
| `unmount` | `(plugin: V9Plugin) -> bool` | bool | 卸载单个插件(幂等) |
| `unmount_all` | `() -> int` | int | 逆序卸载全部全局插件 |
| `reset` | `() -> None` | None | 完全重置(测试用) |

### 2.2 V9Scope

| 方法 | 签名 | 返回值 | 语义 |
|---|---|---|---|
| `provide` | `(name: str, service: Any) -> None` | None | 作用域内注册(同名覆盖全局 shadow) |
| `get` | `(name: str) -> Any` | 服务实例 | 先查作用域, 未命中回退全局 |
| `has` | `(name: str) -> bool` | bool | 作用域或全局存在 |
| `on` | `(event: str, fn: Callable) -> None` | None | 作用域内监听 |
| `dispose` | `() -> None` | None | 逆序卸载插件+清空(幂等) |

### 2.3 V9Plugin

| 方法 | 签名 | 返回值 | 语义 |
|---|---|---|---|
| `apply` | `(ctx: V9Context, scope: Optional[V9Scope]=None) -> None` | None | 挂载钩子(子类实现) |
| `dispose` | `() -> None` | None | 卸载钩子(子类实现, 默认空) |

---

## 3. 迁移清单

### 3.1 shared_state.py 30+ 全局 dict 收编优先级

| 优先级 | 变量 | 归属 | 理由 |
|---|---|---|---|
| **P0-收编(容器持有, 业务经 shim 访问)** | `_session_write_tracker` `_session_git_tracker` `_session_tool_tracker` | scope(key=session) | per-session 语义, 天然作用域化; P0 先收编到全局容器(session-keyed dict 不变), P2 迁入 V9Scope |
| **P0-收编(容器持有)** | `_consecutive_reads` `_consecutive_lists` `_consecutive_failures` `_paused_breakpoints` `_js_rollback_count` | scope(key=session) | 全部 session_id → dict, 同一模式 |
| **P0-收编(容器持有, 单值)** | `messages` `_round` `_task_name_async` `_code_indexer` | 全局 | 工具分发共享上下文; P0 保留原语义(P2 迁 scope) |
| **P0-收编(缓存类)** | `_search_file_cache` `_search_empty_cache` `_search_empty_task` `_sag_index_cache` `_auto_merge_cooldown` `_read_cache` `_intercept_cache` `_session_artifacts` `_content_hashes` `_recursion_tracker` `_query_melt_cache` `_query_empty_cache` `_query_cache` `_retry_cache` `_session_failed` | 全局 | 进程级缓存, 容器持有即可 |
| **P0-不动(常量/函数)** | `_SANDBOX_ENV` `_HEREDOC_MARKERS` `ALLOWED_COMMANDS` `_READ_CMDS` `_WRITE_CMDS` `_SAFE_EXEC_CMDS` `_PROJECT_ROOT` `_keyword_cache` `_layer_store` `_policy` `_EXECUTION_POLICY_CACHE` `_tracker_lock` `_get_tracker_lock` `_tracker_setdefault` `_load_v9_execution_policy` `_strip_quoted_and_comments` `_guard_log` | 原模块 | 常量无状态/纯函数/配置缓存, 容器化无收益 |
| **P0-不动(后台任务)** | `_background_tasks` `_fake_done_count` `_code_indexers` `_last_read_fingerprints` | 原模块 | 有专用管理逻辑, P2 再评估 |

**P0 收编方式**:在 `shared_state.py` 顶部 import `get_v9_context`, 进程启动时(`agent_gateway_enhanced.py` 模块加载处)把上述 dict 注册进容器:

```python
# shared_state.py 新增(保持现有 export 不变, 业务代码零改动)
from core.os.context import get_v9_context
_v9 = get_v9_context()
_v9.provide("shared_state", {
    "_session_write_tracker": _session_write_tracker,
    "_session_git_tracker": _session_git_tracker,
    "_session_tool_tracker": _session_tool_tracker,
    "_consecutive_reads": _consecutive_reads,
    "_consecutive_lists": _consecutive_lists,
    "_consecutive_failures": _consecutive_failures,
    "_paused_breakpoints": _paused_breakpoints,
    "_js_rollback_count": _js_rollback_count,
    "messages": messages,
    "_round": _round,
    "_task_name_async": _task_name_async,
    "_code_indexer": _code_indexer,
    # ... 缓存类
})
```

> 注意: dict 是引用, 业务代码仍直接操作原变量; 容器只是"持有引用"——P0 目标是建立"容器是状态唯一入口"的**结构**, 行为零变化。P2 才做真正的迁移(业务改为 `ctx.get`)。

### 3.2 单例 shim 兼容方式

**原则**:现有 `from core.lib.code_entity_extractor import extractor` 的 23 处 import **不改**;在 `code_entity_extractor.py` 模块级把 `extractor` 改为"延迟解析到容器":

```python
# core/lib/code_entity_extractor.py 尾部(替换直接构造)
from core.os.context import get_v9_context

def _get_extractor():
    """从容器取 extractor; 未注册时惰性构造并注册(兼容 import 即用)。"""
    ctx = get_v9_context()
    ext = ctx.get_opt("extractor")
    if ext is None:
        ext = CodeEntityExtractor()
        ctx.provide("extractor", ext)
    return ext

# shim: 保留模块级名字, 但改为属性访问(延迟解析)
class _ExtractorProxy:
    def __getattr__(self, name):
        return getattr(_get_extractor(), name)

extractor = _ExtractorProxy()   # 业务代码 from ... import extractor 零改动
```

**同法处理**:
| 单例 | 文件 | shim |
|---|---|---|
| `extractor` | `core/lib/code_entity_extractor.py` | `_ExtractorProxy` 延迟到 `ctx.get("extractor")` |
| `ledger` | `core/lib/v8/ledger.py` | `_LedgerProxy` 同上 |
| `roster_engine` | `core/lib/v8/roster_engine.py` | 同上 |
| `tool_executor` | `core/lib/tool_executor.py` | 同上 |
| `audit` 函数组 | `core/gateway/audit.py` | 模块对象整体注册 `ctx.provide("audit", audit_module)`, 消费方可选迁移 |

**测试隔离收益**:proxy 使测试可 `ctx.provide_override("extractor", fake)` 替换, 无需 monkeypatch sys.modules。

### 3.3 tool_router if/elif → 注册表查名迁移步骤

现状: `_execute_sandbox_tool` 内 6 个 `if/elif`(read_file/write_file/list_dir/search_files/execute_command/query_index)+ 2 特殊(sandbox_checkpoint/sandbox_rollback)。

**步骤(全部在 P0 内完成, 行为零变化)**:

1. **建注册表**: `ctx.provide("tool_registry", {})` + 注册函数
2. **注册 6 工具**: 模块加载时执行
   ```python
   def _register_tools(ctx):
       reg = ctx.get("tool_registry")
       reg["read_file"] = ReadFilePlugin
       reg["write_file"] = WriteFilePlugin
       reg["list_dir"] = ListDirPlugin
       reg["search_files"] = SearchFilesPlugin
       reg["execute_command"] = ExecuteCommandPlugin
       reg["query_index"] = QueryIndexPlugin
   ```
3. **改分发**: `_execute_sandbox_tool` 尾部查表
   ```python
   # 替换 if/elif 链(保留 sandbox_checkpoint/sandbox_rollback 两个特殊分支在前)
   _plugin_cls = _tool_registry.get(tool_name)
   if _plugin_cls is None:
       return {"success": False, "error": f"未知工具: {tool_name}"}
   _plugin = _plugin_cls()
   # 保留各工具原有 ctx 装配(从 if/elif 分支移出为通用装配 + 每工具差异段)
   return _plugin.execute(args, _ctx_for(tool_name, base, args))
   ```
4. **ctx 装配保留**: 各分支原有的 ctx 字段注入(read_ctx/write_ctx/exec_ctx 差异)抽为 `_ctx_for(tool_name, ...)` 辅助函数,**字段清单逐字保留**
5. **回归**: 6 工具各跑 1 次真实调用(或既有测试), 对比返回结构

> P0 阶段 `_with_tool_flow` 装饰器**保留不动**(它是 post-execute 的雏形, P1 才迁移为 AuditPlugin)。

---

## 4. 测试计划

### 4.1 新测试文件 `tests/unit/test_v9_context.py`(容器层)

| # | 用例 | 断言 |
|---|---|---|
| 1 | provide/get/has 基本 CRUD | get 返回原对象; has True/False |
| 2 | provide 重复注册抛 ValueError | pytest.raises(ValueError) |
| 3 | provide_override 覆盖生效 | 覆盖后 get 返回新对象 |
| 4 | get 未注册抛 KeyError / get_opt 返回 None | 两者语义 |
| 5 | scope() 惰性创建且幂等 | 同 key 返回同一实例 |
| 6 | scope shadow: 作用域 provide 同名 | scope.get 命中作用域, 全局 get 仍是全局 |
| 7 | scope 未命中回退全局 | scope.get(global_only) 返回全局服务 |
| 8 | dispose_scope 后服务消失 | has(scope 内)False; 全局不受影响 |
| 9 | dispose_scope 幂等 | 二次调用返回 False |
| 10 | list_scopes 返回存活 key | 创建/销毁后正确 |

### 4.2 事件总线测试(同文件)

| # | 用例 | 断言 |
|---|---|---|
| 11 | emit 广播到全部监听器 | 每个监听器收到 payload |
| 12 | emit 监听器异常隔离 | 一个抛异常, 其余仍执行 |
| 13 | waterfall 首个非 None 短路 | 后续监听器不执行, 返回短路值 |
| 14 | waterfall 全部放行走 fallback | 返回 fallback 结果 |
| 15 | waterfall 无 fallback 返回 None | 全放行 |
| 16 | scope 内监听器只收到本 scope emit | 全局 + scope 分发正确 |

### 4.3 插件生命周期测试(同文件)

| # | 用例 | 断言 |
|---|---|---|
| 17 | mount 调用 apply, unmount 调用 dispose | 顺序正确 |
| 18 | unmount_all 逆序卸载 | 后挂先卸(记录顺序断言) |
| 19 | scope 内 mount 随 dispose_scope 回滚 | scope 销毁后插件 dispose 被调 |
| 20 | reset 完全重置 | 服务/作用域/插件全清 |
| 21 | 插件 apply 注册监听器, dispose 撤销 | 卸载后 emit 不再触发 |

### 4.4 零行为变化验证

- **全量回归**: `tests/integration + tests/unit` ≥ 256 passed(现状基线)
- **专项**: `test_v9_stream.py`(bridge 循环 SSE)、`test_subtask_executor.py`(子任务链路)、`test_p2_failure_records.py`(失败路径)、`test_p3_structured_callback.py`(回调)——这些直接依赖 `_execute_sandbox_tool`/单例, 必须不降
- **shim 验证**: 新增 `test_v9_context_shim.py`: 断言 `from core.lib.code_entity_extractor import extractor` 仍可用且 proxy 转发正确; `ctx.provide_override("extractor", fake)` 后 proxy 返回 fake

---

## 5. 风险清单

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| 1 | **`_ExtractorProxy` 破坏既有调用**: 23 处 `extractor.xxx` 若 proxy 转发有遗漏(如模块级 `dir()`/`isinstance` 检查) | 高 | proxy 实现 `__getattr__` + `__dir__` + `__repr__`; 全量回归 + 专项测试覆盖 |
| 2 | **tool_router 查表改造回归**: 6 工具的 ctx 字段装配顺序/差异若抽错, 工具行为变化 | 高 | `_ctx_for` 逐字段对照原分支; 每工具真实调用对比返回; 保留装饰器 |
| 3 | **import 顺序**: `core/os/` 被 shared_state/extractor 在模块加载期引用, 可能循环 import | 中 | `core/os/` 零依赖(仅标准库); `get_v9_context` 延迟初始化; 必要时在函数内 import |
| 4 | **重复 provide 抛 ValueError 误伤**: 现有代码可能多处 provide 同一服务 | 中 | 提供 `provide_override` 逃生口; 启动注册集中到一处 `_register_services()` |
| 5 | **waterfall 语义误用**: 现有监听器若返回 dict(而非 None)会被误判为短路 | 中 | 文档明确"返回 None 才委托"; P1 守卫插件按此契约编写 |
| 6 | **scope 泄漏**: 会话结束未 dispose_scope → 内存增长 | 中 | `/v9/session/clean` 与子任务归档处接入 dispose_scope; P0 提供 list_scopes 便于巡检 |
| 7 | **shim 层掩盖真实迁移**: P0 后业务仍走原 import, 容器"有名无实" | 低 | 在 shared_state 顶部集中注册 + 文档标注"P2 迁移清单"; 提交时附迁移进度表 |
| 8 | **测试隔离污染**: 容器是进程级单例, 测试间状态残留 | 高 | 所有新测试用 `reset()` fixture(autouse); 既有测试不改(容器 P0 不侵入业务路径) |

---

## 6. P0 实施步骤(确认后执行)

1. 创建 `core/os/__init__.py` + `context.py` + `plugin.py`(按本文第 1 节)
2. 新增 `tests/unit/test_v9_context.py`(第 4 节 21 用例) + `test_v9_context_shim.py`
3. `shared_state.py` 顶部收编注册(第 3.1 节 P0 清单)
4. 单例 shim 化: extractor/ledger/roster_engine/tool_executor(第 3.2 节)
5. `tool_router.py` 注册表查名改造(第 3.3 节)
6. 全量回归(256 不降) + 专项验证
7. 提交 + 报告

> 实施边界: **不迁移守卫、不改执行语义、不动 _with_tool_flow、不动 shared_state 导出**——P0 只建骨架 + 收编引用, 为 P1 守卫插件化铺路。
