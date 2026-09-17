# V9Context → OSContext 的调整方向

> 日期：2026-08-17 | 性质：设计推演（P0 之前的定位校准）
> 结论：V9Context 是"执行框架容器"（解决 gateway 内部混乱）；OSContext 是"ClawsJoy 操作系统内核"（承载 agent 生态）。前者是后者的第一层地基，命名与边界需在 P0 落地前定调。

---

## 1. 为什么调整：两个容器的边界

| 维度 | V9Context（当前设计） | OSContext（目标） |
|---|---|---|
| 定位 | 执行框架容器 | 操作系统内核 |
| 解决 | gateway 内混乱（单例/守卫/双路径） | 整个 ClawsJoy 的 agent 生态编排 |
| 服务 | extractor/ledger/audit/tools | + agents 注册表/skills 注册表/sessions store/planners |
| 作用域 | per-session | per-session + per-agent + per-user(多 session) + 全局 |
| 事件 | 工具生命周期 + 会话生命周期 | + 系统级(boot/shutdown/插件热插拔) + 领域级(计划/执行/验证) |
| 生命周期 | 进程启动/会话结束/卸载 | 完整的 OS 引导序列 + 优雅关闭 + 进程外组件挂载 |
| 形态 | Flask 内单例 | 可独立启动、可嵌入、可多实例 |

**关键判断**：V9Context 的设计（服务容器+作用域+事件+插件）在结构上**已经就是** OSContext 的内核雏形——P0 不需要发明两套东西，只需要在命名与边界上按 OSContext 的野心定调，避免 P2 之后重命名返工。

---

## 2. 调整方向

### 2.1 命名与模块位置

```
V9Context  →  core/os/context.py   (OSContext, 别名 V9Context 兼容)
V9Scope    →  core/os/scope.py     (OSScope)
V9Plugin   →  core/os/plugin.py    (OSPlugin, 基类)
事件总线   →  core/os/events.py    (waterfall/emit 原语)
```

理由：
- ClawsJoy 已有多版本网关(V5/V8/V9)与多 agent(11 个),"OS" 是跨越版本的统一底座,不应绑定 V9 命名
- `core/os/` 包在 future 容纳：context.py / scope.py / plugin.py / events.py / registry.py / lifecycle.py / boot.py

### 2.2 服务注册范围扩展

| 层级 | 服务 | 生命周期 |
|---|---|---|
| **内核层** | extractor / ledger / audit / roster_engine / tool_executor / code_indexer | 进程启动时注册,永不卸载 |
| **能力层** | sandbox / approval / quota / mode / context_manager / verifier / planner | 随能力插件挂载 |
| **生态层** | agent 注册表(11 agents) / skill 注册表 / session store / 任务队列 | 动态挂载/卸载(agent 可热插拔) |

### 2.3 作用域层级（OS 特有：per-user）

```python
ctx.global        # 内核服务（进程级）
ctx.user(user_id) # 用户级（多 session 共享的偏好/配额/roster）
ctx.session(sid)  # 会话级（trackers/messages/pending_writes）
ctx.agent(aid)    # agent 级（工具可见性/人设 shadow）—— 新增,对齐 Harness agent.ctx
```

V9 现在只有"进程全局 + 会话 key",缺 user 层与 agent 层。agent 层是 Harness 的灵魂（agent 内注册只对该 agent 生效）——OSContext 必须补上,否则多 agent 的工具可见性无法表达。

### 2.4 事件域扩展

```python
# V9Context 已有
"tools/pre-execute" / "tools/execute" / "tools/post-execute" / "tools/result"
"llm/before-request" / "llm/after-response"
"session/start" / "session/end" / "task/complete" / "task/fail"

# OSContext 新增
"os/boot" / "os/shutdown"                 # 引导序列 / 优雅关闭
"plugin/mounted" / "plugin/unmounted"     # 热插拔通知
"agent/registered" / "agent/unregistered" # agent 生态动态
"skill/loaded" / "skill/removed"
"user/created" / "user/suspended"         # 用户域
```

### 2.5 生命周期升级为 OS 引导序列

```python
# 当前 V9Context
v9ctx.mount(...)   # 平铺挂载

# OSContext（分层引导, 对齐 Harness app-boot settle-the-tree）
os = OSContext()
os.boot(
    core_services=True,      # 内核服务
    capabilities=True,       # 能力插件(sandbox/approval/quota)
    agents=True,             # 11 agents 注册
    skills=True,             # skill 目录
)
os.shutdown()   # 逆序: 停 agent → 卸能力 → 停内核服务 → flush 持久化
```

### 2.6 与 V9 网关的接入方式（渐进）

```python
# agent_gateway_enhanced.py 模块加载处
os = OSContext()
# V9 相关组件作为"能力插件"挂载, 而不是 OS 的特权部分
os.mount(V9GatewayCapability(approval=..., escape=..., bridge=...))
# 多版本共存: V5/V8 也挂为能力(V5GatewayCapability/V8GatewayCapability),
# 共享 extractor/ledger/audit 内核服务 —— 消除三版本各自的全局状态
```

---

## 3. 对现有分期的影响

| 分期 | V9Context 方案 | OSContext 调整后 |
|---|---|---|
| P0 | 容器 + 服务注册 + 事件骨架 | **不改范围**,但模块落位 `core/os/`,类名 `OSContext`(留 V9Context 别名);补 `core/os/boot.py` 引导骨架 |
| P1 | 守卫插件化 + 双路径收敛 | 不改;guard 插件即第一批"能力插件" |
| P2 | 作用域隔离 + 事件溯源 | **新增 agent 层作用域**(toolFilter/人设 shadow);`messages` 迁入 session scope 同时按 agent 呈现 |
| P3(新增) | — | 多版本网关收敛:V5/V8 共享内核服务,统一到 OSContext(彻底消除三版本全局状态分裂) |

---

## 4. 风险与权衡

- **命名过度设计**：如果 ClawsJoy 短期不打算统一 V5/V8/V9,OSContext 的"内核"定位会显得超前——至少 P0 阶段保留 V9Context 别名,让执行框架先行
- **agent 层作用域是最大新增量**：Harness 的 agent.ctx 是灵魂但也是最大复杂度,若 V9 多 agent 无差异化工具需求,可推迟到 P2 后
- **boot 序列耦合**：OS 引导顺序(内核→能力→agent)若设计错,插件间依赖会在启动时炸——需用"依赖声明 + 拓扑排序"(参考 Cordis 依赖注入)而非硬编码顺序
- **多版本收敛是政治问题**：V5/V8 网关是否值得收编取决于业务,OSContext 只提供"可收编"的能力,不强制

---

## 5. 建议

1. **P0 按 OSContext 定调命名**(`core/os/context.py` + `V9Context` 别名),避免 P2 后重命名返工
2. **P0 只做执行框架**,不碰多版本收敛;把"OS"当作未来兼容目标而非本期承诺
3. **P1 的第一批插件就是 OS 能力插件的模板**——guard 插件的注册/卸载契约直接复用为未来 V5/V8 能力插件契约
4. **P2 新增 agent 层作用域**作为可选里程碑,先完成 session 层隔离(解决并发污染)再谈 agent 差异化

> 一句话：V9Context 是 OSContext 的第一层地基——用 OS 的命名与边界定调，用 V9 的执行框架范围落地，用 P3 的多版本收敛兑现 OS 野心。
