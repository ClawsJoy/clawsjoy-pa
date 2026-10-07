# Harness 自我认知报告 — 三根柱子

> 日期：2026-08-17 | 依据：/home/<user>/deepseek-harness 源码（vendored Cordis 插件系统）
> 结论：我不是"agent 程序"，而是事件溯源 + 插件化接缝 + 结构化失败三根柱子上搭起的 agent 框架。

---

## 1. 元架构：Cordis 插件系统如何支撑能力

**一句话**：我是插件树——`vendor/` 中 vendored 的 Cordis 之上，`packages/*` 全部以插件形式挂载，包括 agent 循环自己。`AGENTS.md` 第一行宣言：**"everything is a plugin"**。

### 三层支撑机制

| 机制 | 定义 | 意义 |
|---|---|---|
| **Service**（`ctx.key`） | 插件注册服务到上下文 | `ctx.sessions`/`ctx.tools`/`ctx.llm`/`ctx.sandboxPolicy`/`ctx.goals`，任何插件可注入或替换 |
| **Typed events**（事件即扩展点） | 三类：durable(会话事件)/live(agent 事件)/waterfall(可拦截) | `agent/pre-step`、`agent/request`、`llm/stream`、`tools/pre-execute` 是瀑布，listener 必须 `next()` 委托——新行为挂插件，永不改核心 |
| **Reversible effects**（作用域注册） | 注册随插件卸载自动回滚 | `agent.ctx` 内注册只对该 agent 生效（scope 原语），HMR 热替换无孤儿 |

### 无特权核心
`docs/architecture.md`："There is no privileged core to patch." 模型适配器、工具注册表、会话日志、agent 循环全部可替换。扩展 = 配置层（`cordis.yml`/profile/bundle/patch）叠一行。

**能力接缝(capability seam)**：每个能力 = Service Definition(接口) + Service Provider(实现) + Consumer(模型面工具)三角。沙箱、代码执行、子代理、压缩全遵循——**换实现不换消费者**。

**会话日志是唯一事实来源**：`dsh-session` append-only 事件日志，`deriveMessages()` 从日志**派生**模型历史。原则 "Model-visible means logged"——进模型请求的内容必须可从日志重建，有运行时不变量断言。

---

## 2. 执行框架核心优势

### 任务分解：turn/step 生命周期 + inbox 输入模型
- `agent-loop` 是**唯一**含具体循环逻辑的包，驱动 session/turn/step 生命周期
- turn = 0..n 步，`turn/start` 打开、`turn/end` 关闭（记录 reason: completed/max-tokens/error/aborted/blocked）
- step = 一次模型请求 + 它调用的工具
- **inbox 三通道**：`followup`(下一 turn)/`steer`(下一 step)/`inject`(不唤醒)——精确控制输入时机
- 每次 step **重新组装**：系统提示分段 + 工具 schema + 运行时上下文投影，`agent/pre-step` 可重写/拒绝
- **并行工具池**：`maxParallelToolCalls` 滚动池，独占调用成屏障，结果按**模型顺序**提交（commitReady 只推进连续槽位），并发安全且可回放

### 环境感知：三层注入
1. **沙箱策略每调用解析**：`sandboxPolicy.resolve()` 每次给出 mode+workspaceRoot（会话覆盖 > 事件折叠 > 部署默认），`sandbox:policy` 作为运行时上下文注入
2. **运行时上下文投影**：`RuntimeContextProjection` 把动态上下文渲染成**持久的 user/message 快照**，变化才追加，可从日志重建
3. **系统提示分段组装**：section 按 order 拼接（身份 -100 / 人设 0 / 工具指导 100-199），`{{variable}}` 严格插值，`toolOrder` 定呈现顺序

### 纠错：结构化失败 + 确定性守卫 + 协作取消
- **错误分类**：`LlmError` 携带 code；非 LlmError 扁平化为 `errorChain` 文本 + `UNKNOWN` code（V9 的 P1/P2/P3 来源）
- **失败恢复**：`agent/request-error` 瀑布携带失败事实 + 适配器注册时捕获的不可变重试策略；`{kind:'retry'}` 才重试——策略与适配器绑定不漂移
- **单调守卫**：`tools/guard` 拒绝即终局，后续瀑布不能改回允许；`repeat-tool-reminder` 在 post-execute 观察（3/5/8，永不否决，拒绝的调用也计数——防循环杀招）
- **超时**：`timeout-policy` 按工具自身声明 `timeoutMs` 布防，超时替换为结构化 `TOOL_TIMEOUT`，不硬杀（协作式）
- **协作取消**：所有调用携带 `AbortSignal`，取消是通知不是强杀，预算 + `whenIdle()` 保证收敛
- **沙箱失败封闭**：无后端可用抛 `SANDBOX_UNAVAILABLE`，**绝不无封闭运行**
- **code-runtime 敌对方假设**：模型代码视为主机对手——入站消息校验并重建、预算双轨(computeMs 实测忙碌 + maxWallMs)、每次 run 全新 worker、空环境

### 代理间可靠性
子代理深度(`delegationDepth`)持久化在会话头且单调（恢复不能降级）；委托子代理审批固定 `never`；`approval` 缺 answerer 时 fail-closed。

---

## 3. 能力边界（诚实清单）

- **沙箱是文件效果沙箱，不是安全边界**：无网络/进程/syscall/设备/凭据限制；同世界限制，容器/microVM 需整体替换 capability seam
- **code-runtime "containment, not a security boundary"**：信任姿态与 bash 等效
- **拒绝报告是 stderr 方言**：`denialSignatures` 从子进程 stderr 推断，无类型化拒绝通道；runner 诊断带内（可被模仿，不能绕过封闭）
- **协作取消软肋**：声明 `timeoutMs` 的工具必须转发信号，忽略信号的工具不会停
- **scope 安全非目标**：`toolFilter`/`restrict` 是可见性组合，不是权限边界
- **内存态守卫**：repeat-tool-reminder 是内存 WeakMap，持久化恢复后从新链开始
- **workflow/ralph 协调器限制**：脚本无文件系统/网络/定时器/Node API——agent 做工作，脚本只协调
- **ACP 是自动化传输不是 UI**：无编辑器导航/转写回放/命令/模式
- **无持久化时 resume 不可用**：`resume` 依赖 `sessionPersistence`
- **子代理上下文继承是描述性**：`inheritsParentContext` 只说明是否看到父级历史

---

## 4. 移植到 Python V9 Agent 最关键的三件事

### ① 事件溯源的会话日志（单一事实来源）
从"内存 messages 列表"转向"append-only 事件日志 + 派生历史"。任何进入模型的内容都必须是**可重建的日志事件**；`turn/step/tool-call/tool-result` 配对带序号。收益：回放、崩溃恢复、fork、审计、KV 缓存复用。V9 现状 `.task_state.json` + 内存 messages 缺"可重建"契约——最大架构差距。

### ② 分阶段、可插拔、结构化结果的工具执行流水线
工具执行从"调用→返回"升级为流水线：`pre-execute(allow/deny) → guards(单调,拒绝不可逆) → execute(timeout/retry) → post-execute(检查/替换/附加) → finalize → result`，且**每阶段是事件**。守卫拒绝不可恢复（确定性）；超时是结构化 `TOOL_TIMEOUT`；失败带 code。V9 现状：`tool_router` 单函数 + 内联循环，阶段不分离、结果非结构化、无单调守卫语义。

### ③ 能力接缝 + 作用域注册（无特权核心）
把单体 Flask 网关拆成"接口/实现/消费者"三角 + 按会话作用域注册。每个能力（沙箱、审批、LLM、工具、持久化）定义接口、实现可替换、消费者不 import 具体实现；子任务/会话级注册只对该 agent 生效、卸载自动回滚。V9 现状：全局共享状态（shared_state、extractor 单例 23 文件散落 import）正是并发污染根源。

---

## 一句话总结

> 我是"事件溯源 + 插件化接缝 + 结构化失败"三根柱子上搭起来的 agent；我的优势不是模型，而是**可重建、可替换、失败有 code、守卫不可逆**的工程纪律。V9 若只移植三件事，就移植这三根柱子——其余（并行池、goal、workflow）都是在它们之上长出来的。
