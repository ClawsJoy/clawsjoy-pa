# V9 Agent × Harness 差距分析（#100）

> 日期：2026-08-15
> 方法：以 DeepSeek Harness 执行纪律为基准，对照 V9 现有实现（agent_system.md / agent_gateway_enhanced.py / VerificationChain / os_event_logger）
> 依据：代码实证（非文档推断）
> 关联：#101 执行纪律（P1）、#102 第三方验证（P1）

---

## 一、Harness 执行纪律基准（5 项）

DeepSeek Harness 的核心纪律（从工具设计与运行约束提炼）：

| 纪律 | Harness 实现 |
|---|---|
| 1. 计划先行 | create_goal：长目标显式化、可跨轮次、可修订 |
| 2. 人类锚点 | ask_user_question（决策/确认/缺信息）、sandbox_permissions（越权审批）、edit/pause/resume 需 direct human request |
| 3. 执行可审计 | 每个动作是显式工具调用，全量可回溯（bash/job/subagent 均留痕） |
| 4. 验证闭环 | 结果回传、失败重试有界、todo_write 进度显式化 |
| 5. 第三方视角 | 上下文压缩/checkpoint 由 harness 管理，不依赖 Agent 自我报告 |

## 二、V9 现状自检（代码实证）

### 已具备（✅）

| 纪律 | V9 现状 | 证据 |
|---|---|---|
| 人类锚点 | 锚点A 写确认 + 锚点B 越权拦截 | agent_gateway_enhanced.py 桥接循环 + write_pending/escalation_blocked |
| 执行可审计 | tool_flow 421 条 + tool_steps 前端展示 + escalations 越权审计 | code_entities 表 |
| 验证闭环 | VerificationChain 5 项 checklist（写入/语法/导入/运行/内容核验）| config/prompts/agent_system.md 85-93 |
| 失败有界 | 3 次重试上限 + 失败出口（如实上报）| agent_system.md 119-123 |
| 防幻觉 | 假完成拦截（_check_recent_writes + commit_count 校验）+ 证据条款 | agent_system.md 113-118 |
| 过程透明 | tool_steps 每步回传前端展示 | #101 已验证 |

### 差距（🔴 / 🟡）

| # | 差距 | 现状 | 影响 | 严重度 |
|---|---|---|---|---|
| G1 | **无 todo 进度显式化** | 任务只有最终状态，无中间步骤清单 | 长任务老板看不到"进行到哪" | 🔴 |
| G2 | **计划确认不强制** | "复杂任务先列计划"是软约束（agent_system.md 68），无机制强制 | Agent 可跳过确认直接执行 | 🔴 |
| G3 | **无 ask 式提问通道** | 阻塞时只能输出文字"请求授权"，前端无结构化提问 UI | 老板难以快速决策 | 🟡 |
| G4 | **验证全自助** | 5 项 checklist 由 Agent 自己执行并报告，无第三方核验 | 自我报告不可靠（#102）| 🔴 |
| G5 | **OS 审计覆盖不全** | write_os_event 只在失败/拦截时写（2563/753），正常执行无审计事件 | 无全量操作审计链 | 🟡 |
| G6 | **目标无跨轮次持久** | 任务状态在 .agent_state.json，但无 goal 语义（完成/暂停/修订）| 长线任务缺上下文锚 | 🟡 |

## 三、差距详情（代码定位）

### G1：无 todo 进度显式化
- **证据**：前端只渲染 agentLog 文本行 + 最终完成；无"步骤 1/5 进行中"状态。
- **影响**：长任务（多文件修改）老板无法感知进度，只能等最终。
- **方案**：tool_steps 扩展为结构化进度（step/status/total），前端渲染进度条 + 步骤清单。

### G2：计划确认不强制
- **证据**：agent_system.md 68"复杂任务先列计划"为建议性；VerificationChain 只拦"假完成"，不拦"未确认直接执行"。
- **影响**：写操作有锚点A 兜底，但多文件改动的**方案级确认**缺失——Agent 可能按错误方案执行到底。
- **方案**：plan_status 机制（v5_execute 已有 discussing/confirmed）扩展到 V9 桥接：写前若检测多文件/多步骤 → 强制返回 PLAN_PENDING，老板确认后才执行。

### G3：无 ask 式提问通道
- **证据**：v9_agent_chat 无 ask 结构；阻塞时 Agent 输出文字，前端仅展示。
- **影响**：老板决策靠读文字 + 手动输入，无结构化选项。
- **方案**：桥接返回 status=ask + options[]，前端渲染选择按钮（复用 renderPlanButtons 模式）。

### G4：验证全自助（#102 核心）
- **证据**：VerificationChain 由 v9_agent_chat 内部调用（2416 行），执行与校验同一进程同一 Agent 视角。
- **影响**：Agent 可自证"已验证"，无独立核验（如：声称 py_compile 通过但实际未跑）。
- **方案**：OS 审计层（os_monitor）作为第三方：桥接循环每步写审计事件（工具名/参数/结果哈希），完成时审计层独立复核——若 Agent 报告与审计不符 → 判假完成。

### G5：OS 审计覆盖不全
- **证据**：write_os_event 调用仅 2563（元认知失败）、753（execute_agent_task 内）、chat_stream（讨论）——正常工具执行无审计。
- **影响**：无法回答"这个 Agent 刚才到底执行了什么"（除 tool_flow，但 tool_flow 是 Agent 视角记录）。
- **方案**：在 _execute_sandbox_tool 装饰器（_with_tool_flow）内同步写 OS 审计事件（独立于 tool_flow）。

### G6：目标无跨轮次持久
- **证据**：.agent_state.json 存 last_task/task_progress，但无 goal 生命周期（created/active/paused/complete）。
- **影响**：会话恢复只恢复 pending，不恢复"任务目标与进行中步骤"语义。
- **方案**：state 增加 goal 字段（goal_id/objective/status/plan[]），重启后注入。

## 四、优化方案（按优先级）

### P0：#102 第三方验证（G4 + G5）
1. **OS 审计全量覆盖**：_with_tool_flow 装饰器内写审计事件（tool/args_hash/result_hash/ts），独立于 tool_flow
2. **审计复核**：完成时 os_monitor 独立核对——Agent 报告的 5 项 vs 审计记录的 5 项，不符 → 假完成
3. **落地**：新增 core/gateway/audit.py（封装审计写入+复核），桥接循环调用

### P1：#101 执行纪律（G1 + G2）
4. **todo 进度显式化**：tool_steps 加 step_index/total_steps，前端渲染进度条
5. **计划确认强制**：多文件/多步骤任务 → 桥接返回 PLAN_PENDING（复用 plan_status 机制），老板确认后放行
6. **agent_system.md 强化**：新增"执行纪律"段（计划→确认→执行→验证 硬约束，参照 Harness）

### P1：G3 ask 通道
7. 桥接返回 status=ask + options[]，前端渲染选择按钮

### P2：G6 目标持久
8. state 增加 goal 字段，跨轮次恢复

## 五、落地清单

| # | 项 | 涉及 | 工作量 |
|---|---|---|---|
| 1 | audit.py 全量审计写入 | core/gateway/audit.py + tool_router | S |
| 2 | 审计复核假完成判定 | agent_gateway + os_monitor | M |
| 3 | tool_steps 进度结构化 | agent_gateway + workbench.html | M |
| 4 | PLAN_PENDING 强制确认 | agent_gateway + workbench.html | M |
| 5 | ask 选项通道 | agent_gateway + workbench.html | S |
| 6 | goal 持久化 | agent_gateway + state | S |
| 7 | agent_system.md 执行纪律段 | prompt | S |

## 六、风险
- **审计性能**：全量审计写 DB 增加 IO——用内存队列 + 批量落盘
- **假完成误判**：审计与 Agent 报告可能因时序差异不符——复核留 5s 窗口
- **PLAN_PENDING 影响**：多文件任务需老板确认可能降低自动化——仅"≥2 文件或 ≥3 修改意图"触发（复用现有复杂度预判）
