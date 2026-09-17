# V9 Agent 执行能力评估与插件化改造方案

> 日期：2026-08-17 | 依据：core/gateway/execute_agent_task.py(1551行) + subtask_executor.py(224行) + tool_router.py(244行) 代码实证
> 方法：对照 Harness 执行框架（三根柱子），逐项核对已具备/缺失/架构缺陷。

---

## 一、V9 执行能力评估

### 已读文件证据

| 文件 | 规模 | 结构 |
|---|---|---|
| `execute_agent_task.py` | 1551 行 | `_execute_agent_task` 单函数约 970 行(预处理→LLM 循环→工具执行→验证→保存→回调全内联) |
| `subtask_executor.py` | 224 行 | 有界并发池(3)+ 深度预算(maxDepth=3)+ 独立沙箱 git 基线 + 归档 |
| `tool_router.py` | 244 行 | `_execute_sandbox_tool` 统一分发 + `_with_tool_flow` 装饰器 + `_ToolContext` 手动装配 |

### 1.1 已具备的能力（对照 Harness）

| V9 已有 | 对应 Harness 概念 | 证据 |
|---|---|---|
| 工具插件接口 | tools 注册的 ToolDefinition | `core/tools/base.py` ToolPlugin 基类,6 插件统一 `execute(args, ctx)` |
| ctx 依赖注入雏形 | scope/agent.ctx | `_ToolContext` 手动装配依赖 |
| 结构化错误 | LlmError + errorChain | P1-P3: `_struct_error`(code/message/detail)、`_classify_exception`、`[TOOL_EXEC]/[LLM_API]/[TIMEOUT]` 前缀、on_fail 带 `{code,message}` |
| 重复工具提醒 | repeat-tool-reminder | `repeat_tool_reminder.py` 3/5/8 阈值、canonicalize、永不否决 |
| 失败可审计 | 失败进 session log | `_record_failure_action` 写 agent_actions(tool_name=failed) |
| 工具追踪/熔断 | guard 家族 | consecutive_reads/lists/failures、query 空熔断、连续失败暂停 |
| 子任务委托深度 | subagent delegationDepth | `resolve_depth`/`check_depth`/`SubtaskDepthError`/持久化 |
| 沙箱路径锚定 | sandboxPolicy workspaceRoot | `sandbox_base` 贯穿 6 处 + `_resolve_path` data/projects 锚点 |
| 验证链+审计复核 | （Harness 无直接对应,更严格） | VerificationChain 五步 + `cross_check_completion` 防假完成 |
| 长线任务回调 | agent/request-error | on_done/on_fail 结构化回调(P3 完成) |
| 工具 flow 记录 | tools/result 通知 | `_with_tool_flow` 记录 tool_flow + audit_tool_call |

### 1.2 缺失的能力

| 缺失 | Harness 对应 | V9 现状 |
|---|---|---|
| 事件溯源会话日志 | session append-only log + `deriveMessages()` | messages 是内存可变列表,无"模型可见=已落盘"不变量 |
| 工具执行流水线事件 | pre-execute → guards → execute → post-execute → finalize → result | 检查全内联在循环 + 装饰器,守卫硬编码在函数体 |
| 作用域注册(per-agent) | scope + agent.ctx | 模块级单例:extractor 被 23 文件散落 import、ledger 7 处、shared_state 12 处 |
| 插件生命周期(卸载回滚) | reversible effects | 无卸载概念 |
| LLM 适配器可插拔+重试绑定 | llm registerAdapter + providerRetryPolicy | `DeepSeekAdapter` 函数内 import 硬编码,重试写死 |
| 协作取消(AbortSignal) | 全链 signal | 无取消通道,只有超时 break |
| 运行时上下文投影 | RuntimeContextProjection | 无策略快照注入 |
| code-runtime(模型写代码隔离执行) | worker-thread + 敌对方假设 | 仅 execute_command,无隔离/预算/防伪 |
| 并行工具池+模型序提交 | tool-calls.ts maxParallelToolCalls | 工具串行执行 |

### 1.3 架构性缺陷（实证）

1. **双执行路径分叉**：`_v9_bridge_loop`(锚点A 写审批/锚点B 越权/计划确认/ask)与 `_execute_agent_task`(无审批、独立沙箱)是两套工具循环；`_execute_sandbox_tool` 11 处调用点分散 4+ 文件——审批语义只在一条路径存在
2. **单体巨型函数**：`_execute_agent_task` 一个函数承担 LLM 调用/Token 截断/疲劳/注意力/验证链/审计复核/工具追踪/SAG 刷新/状态保存/回调——970 行内联
3. **全局可变状态**：`shared_state.py` 213 行 30+ 模块级 dict + 全局 `messages` 单例；并发隔离靠 `_shared_msgs[:] = messages` hack + fcntl 文件锁
4. **单例蔓延**：`extractor = CodeEntityExtractor()` 模块级构造(import 即连 DB),23 文件 import 同一实例
5. **事件系统缺失**：工具前后置只有装饰器(函数级),无 waterfall——守卫全是顺序 if,不可组合
6. **工具结果非结构化**：工具返回 `{"success": bool, "error": str}` 文本,无 code 分类,audit 只能存文本

---

## 二、插件化改造方案（借鉴 Cordis）

### 2.1 V9Context 全局容器

```python
# core/gateway/v9_context.py（设计草案）
class V9Context:
    """Cordis Context 的 Python 简化: 服务容器 + 事件总线 + 作用域注册"""

    def __init__(self):
        self._services: dict[str, object] = {}     # name -> service
        self._scopes: dict[str, V9Scope] = {}       # session_key -> 会话作用域
        self._plugins: list[V9Plugin] = []          # 已加载插件(逆序回滚)
        self._listeners: dict[str, list] = {}       # event -> [监听器]

    def provide(self, name, service, scope=None): ...
    def get(self, name, scope=None): ...
    def has(self, name, scope=None): ...

    def scope(self, session_key) -> V9Scope: ...    # 惰性创建
    def dispose_scope(self, session_key): ...       # 会话结束清理

    def on(self, event, fn, scope=None): ...        # 注册
    def emit(self, event, payload): ...             # 广播
    def waterfall(self, event, payload, fallback=None): ...  # 可拒绝

    def mount(self, plugin: V9Plugin): ...          # plugin.apply(ctx)
    def unmount_all(self): ...                      # 逆序回滚

ctx = V9Context()   # 进程级单例（替代 shared_state）
```

**作用域语义**：全局注册(extractor/ledger/audit)；会话注册(per-session trackers/pending_writes)同名 shadow 全局；`dispose_scope` 在 `/v9/session/clean` 和子任务归档时调用。

### 2.2 服务注册（现有单例收编）

| 现有单例 | 注册名 | 改造方式 |
|---|---|---|
| `extractor`(23 文件) | `ctx.provide("extractor", extractor)` | 延迟到进程启动;消费方改 `ctx.get("extractor")`(先提供 shim:模块级 get_extractor()) |
| `ledger`(7 处) | `ctx.provide("ledger", ledger)` | 同上 |
| `audit` 函数组 | `ctx.provide("audit", audit_module)` | 模块对象整体注册 |
| `roster_engine`/`tool_executor`/`code_indexer` | 各自注册 | 同上 |
| `ContextManager` | per-scope | 改 per-session scope,避免跨会话串 |

**兼容策略**：P0 保留 shim 层（属性延迟解析到 `ctx.get`），业务代码零改动先让容器持有实例；后续分文件迁移。

### 2.3 插件化（guard/审计/工具）

```python
class V9Plugin:                      # 对齐 Cordis plugin.apply(ctx)
    name: str = ""
    def apply(self, ctx: V9Context): ...   # 注册服务/监听器, 返回可选 dispose fn
```

**Guard 插件家族**（把散落 if 收编为 `tools/pre-execute` 监听器）：

| 现有逻辑（散落位置） | 收编为 |
|---|---|
| 锚点A 写审批(bridge_loop) | `WriteApprovalGuard`(仅主任务 scope;子任务 scope 不挂载=天然免审批) |
| 锚点B 越权拦截 | `PathEscapeGuard`(monotonic,拒绝不可逆) |
| 高危命令拦截 | `SysEscapeGuard`(复用 `_detect_sys_escape`/`_SYS_ESCAPE_PATTERNS`) |
| 配额/模式检查 | `QuotaGuard` + `ModeGuard` |
| 重复工具提醒 | `RepeatToolReminderPlugin`(观察者,永不否决) |
| 递归检测/连续失败暂停 | `RecursionGuard` + `FailurePauseGuard` |
| 禁则硬约束(write_file/execute_command 内嵌) | `ForbiddenPatternGuard`(从工具插件移到 guard 层) |

**工具插件**：沿用 ToolPlugin,注册进 `ctx.tools` 注册表（替代 if/elif 分发）：`ctx.tools.register("write_file", WriteFilePlugin)` → 循环按名查表 + 按 scope 过滤。

**审计插件**：`AuditPlugin` 挂 `tools/post-execute`,统一记录 tool_flow + audit_tool_call + agent_actions（替代 `_with_tool_flow` 装饰器）。

### 2.4 事件系统（工具前后置）

```python
# 工具生命周期事件（对齐 Harness tools/* waterfall）
"tools/pre-execute":   # waterfall, 监听器返回 {"deny": True, "reason": ...} 拒绝; None 放行
"tools/execute":       # around 包装(超时/重试/指标)
"tools/post-execute":  # waterfall, 可检查/附加上下文(reminder)
"tools/result":        # 广播, observe-only(审计)

# LLM 生命周期
"llm/before-request" / "llm/after-response"
# 会话生命周期
"session/start" / "session/end" / "task/complete" / "task/fail"
```

执行顺序（对齐 Harness tool pipeline）：
```
tools/pre-execute(guards 按注册序, 任一 deny 即终止, 后续不可恢复)
  → tools/execute(dispatch 工具插件)
  → tools/post-execute(reminder/上下文附加)
  → tools/result(审计观察)
```

### 2.5 生命周期管理

```python
# 进程启动 (agent_gateway_enhanced.py 模块加载处)
v9ctx = V9Context()
v9ctx.provide("extractor", ...); v9ctx.provide("ledger", ...); ...
v9ctx.mount(WriteApprovalGuard()); v9ctx.mount(PathEscapeGuard()); ...
# 会话结束 (/v9/session/clean / 子任务归档)
v9ctx.dispose_scope(session_key)
# 进程退出 / 测试 teardown
v9ctx.unmount_all()   # 逆序卸载插件, 恢复原状(测试隔离关键)
```

---

## 三、改造分期

### P0 — 容器与事件骨架（最小可验证,不改变执行语义）

| 项 | 范围 |
|---|---|
| 新增 | `core/gateway/v9_context.py`(V9Context + V9Scope + V9Plugin + 事件总线) |
| 改造 | `shared_state.py` 顶部创建全局 `v9ctx`,extractor/ledger 保持 shim 兼容同时注册进容器 |
| 改造 | `tool_router.py` 分发改查注册表(if/elif → 查名),**`_with_tool_flow` 保留** |
| 新增测试 | 容器 CRUD、scope shadow、waterfall 短路、unmount 回滚 |
| 验证 | 全量回归 256 passed 不降 |

**风险**：工具查表改造触及 11 处调用点需逐工具回归;P0 只做"查表"不做"事件化",守卫仍内联 → 行为零变化。

### P1 — 守卫插件化 + 双路径收敛

| 项 | 范围 |
|---|---|
| 改造 | 接通 `tools/pre-execute`:锚点A/B、配额、模式、禁则、递归、失败暂停**从内联 if 抽为 guard 插件** |
| 改造 | `execute_agent_task.py` 工具循环内联检查(约 8 处 if)替换为 `v9ctx.waterfall("tools/pre-execute", ...)`,循环体显著瘦身 |
| 改造 | `_with_tool_flow` → `AuditPlugin` 挂 `tools/post-execute` + `tools/result` |
| 关键 | **双路径收敛第一步**：两条循环共享同一套 guard 挂载(主任务 scope 挂 WriteApprovalGuard,子任务 scope 不挂)——审批差异由**作用域**表达而非代码分叉 |
| 验证 | 主任务写审批 E2E + 子任务免审批 E2E + 越权拦截回归 |

**风险**（最大风险期）：
- bridge_loop 有"确认后放行/plan_pending/ask"状态机,execute_agent_task 没有——guard 插件化必须保留 `write_pending`/`plan_pending` 等**返回状态透传**,否则前端卡死
- 守卫执行顺序敏感（配额先于越权？模式先于配额？）——需固化注册序
- 双路径强行统一会破坏子任务"审批固定 never"隔离——**P1 只共享 guard 框架,不强制合并两条循环**

### P2 — 作用域隔离 + 事件溯源会话日志

| 项 | 范围 |
|---|---|
| 改造 | `shared_state` 30+ 全局 dict 迁入 per-session `V9Scope`;`messages` 全局单例改 scope 内实例(消除 `_shared_msgs[:] = messages` hack) |
| 改造 | 引入轻量**会话事件日志**(`session/event` 序列号 + 工具调用/结果配对),`derive_messages()` 从日志投影 |
| 改造 | `_execute_agent_task` 拆解:LLM 调用/Token 截断/疲劳/注意力 → 各自 `llm/*` 事件监听器;循环体只留编排 |
| 改造 | 子任务状态从 `_subtasks` 全局 dict → 子会话 scope + 持久化 |
| 验证 | 并发子任务(3 路)无串扰 + 会话清理后 scope 释放 + 重放一致性 |

**风险**：
- `messages` 单例被 12+ 文件消费,迁 scope 需同步所有引用点（最大工作量）
- 事件日志引入"模型可见=已落盘"后,大量 `messages.append({"role": "system", ...})` 注入点都要改日志事件 → 回归面巨大
- fcntl 文件锁与内存 scope 的一致性

---

## 总结：三步走

- **P0（容器）**：零行为变化,建立"注册表 + 作用域 + 事件"地基,1-2 周
- **P1（守卫）**：10+ 散落守卫收编为插件,双路径共享 guard 框架、审批差异作用域化,2-3 周（风险最高,需 E2E 护航）
- **P2（溯源）**：全局状态作用域化 + 会话事件日志,根治并发污染与"无重放",3-4 周（工作量最大）

**最终形态**：`V9Context` ≈ Cordis Context,`V9Scope` ≈ agent.ctx,guard 插件 ≈ Harness guard 家族,事件总线 ≈ tools/* waterfall——三个 P 完成后,V9 具备与 Harness 同构的"可替换、可回滚、事件驱动"执行内核,现有业务(工具插件/验证链/子任务)保持兼容。
