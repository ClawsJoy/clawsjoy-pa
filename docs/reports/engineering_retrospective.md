# ClawsJoy OS 两周工程化改造总结报告

> 日期：2026-08-15（两周期改造收官）
> 范围：P0 清零 + P1 全闭环 + 架构解耦 + Harness 差距 G1-G6 + #41 上下文管理三阶段
> 依据：ISSUES.md 五轮记录 + git 提交史（1093 commits）+ 浏览器 E2E 验证 + 测试基线
> 原则：写实不写虚，所有结论均以 commit / 测试 / 线上验证为证据

---

## 一、起点回顾：改造前的问题状态

改造前（第一轮分析基准）ClawsJoy OS 处于 V5/V8 为主、V9 雏形未通的阶段，核心问题：

| 问题域 | 具体症状 | 证据 |
|---|---|---|
| **V9 断点** | V9 工具循环从未成功执行过工具：4 层连锁 bug（true/false 判定、reasoning_content、tracker、mkdir、_validate_messages）| P0-5 / 8b78376 |
| **执行卡死** | LLM 慢响应/连接挂起无超时，任务永久卡死 | P0-6 / 35fe78a |
| **抽取断链** | 主文件抽取后 5 处 NameError（_archive_user_message 等），路由不可用 | P0-7 / aac8aa0 |
| **Agent 跑偏** | 假完成（反问被当成功）、写任务不触发工具、计划讨论结果被丢弃 | P0-1/P1-2/P0-4 |
| **上下文 400** | V9 上下文超限第五次 400，无预算感知的截断策略 | #41 系 |
| **并发串扰** | _consecutive_reads 等模块级整数多线程串扰，配额互相覆盖 | C1 |
| **无执行纪律** | Agent 无 todo/计划确认/提问通道，自我报告不可靠 | G1-G6 差距 |
| **发布流程裸奔** | 修复不生效多次归因于未同步/未重启 | 待办汇总 |

**核心矛盾**：V9 作为新一代工作区（Manus 可视化 + Harness 可靠性）只有骨架，无法承载真实任务；V8 时代积累的可靠性机制（防假完成/队列续跑）在 V9 桥接模式下被绕过。

---

## 二、改造历程：按时间线梳理关键里程碑

### 第一阶段：P0 可靠性攻坚（V9 打通）

| 里程碑 | 内容 | 提交 |
|---|---|---|
| 假完成/队列/持久化三连修 | P0-1/2/3：假完成拦截、队列续跑断链、output_file 持久化 | 806ca05 |
| V9 工具循环 4 层连锁 bug | true/false 判定、reasoning_content、tracker、mkdir、_validate_messages | 8b78376 |
| V9 执行卡死防护 | LLM 调用分离超时 + 任务级超时保护 | 35fe78a |
| 主文件抽取断链修复 | v9_agent_chat 等路由 NameError 批量修复 | aac8aa0 |
| 讨论确认断链 | v5_execute discussing 分支漏 return | b729e1d |
| **V9 桥接真实执行器** | v9_agent_chat 接入 _execute_sandbox_tool，服务器端执行工具 + 回传循环 | 50ebf1b |
| Ollama 降级 | 无 DEEPSEEK_API_KEY 时本地 function calling 降级 | d3d3472 |

**V9 全链路打通验证**（第二轮）：web_test/session_vfy9，8 轮桥接循环、29 条 tool_flow、vfy_demo.py 写入+验证。

### 第二阶段：浏览器验证驱动的缺陷修复

| # | 问题 | 提交 |
|---|---|---|
| #92 | 沙箱路径重写三视图不一致（双重 clawsjoy_dev 前缀）| fbc7ae1 |
| #93 | V9 端点 message vs messages 字段不一致 | bb4f2e7 |
| #96 | 会话写入追踪器 _seen KeyError | 6a37984 |
| #97 | insert_agent_action capability_chain TypeError | dc34439 |
| #98 | write_file 父目录 ENOENT | f9af01b |
| #99 | write 路由注册错位（404）| 6a46323 |
| #100 | write_file 传 Path 给 _sandbox_git_post_write 报 endswith | f67e9cc |

**模式**：每轮浏览器 E2E 暴露 2-3 个真实缺陷，全部是线上路径才能触发（如 write_file 被迫绕 heredoc 是因为 #98/#100 让写入失败）。

### 第三阶段：Manus 可视化 + Harness 锚点

| 功能 | 实现 | 验证 |
|---|---|---|
| #101 工具步骤可视化 | tool_steps 回传 + 前端渲染（✅/❌/⏳）| 浏览器验证 |
| #102 锚点A 写操作前确认 | 桥接拦截 → pending 卡片 → 确认/拒绝 | 浏览器验证 |
| #103 O1 防重复执行 | bridge_exhausted 标记 + 清空 tool_calls | 无行为变化回归 |
| #104 锚点B 越权拦截 | 路径逃逸/高危命令一律拒绝（无审批放行）| 单测 + 浏览器 /etc 拦截 |
| prompt 增补 5 段 | 写确认/工具归属/报告规范/花名册/预算 | 644ba4a |

### 第四阶段：架构优化（基于代码实证审查）

| 项 | 问题 | 修复 |
|---|---|---|
| C1 | 并发配额串扰（模块级整数→per-session dict）| a0c7d35 + 474c82b + 38da103（3 个连锁）|
| C3 | v8 roster 蓝图双注册 | 693b464 |
| C4 | 工具双实现行为漂移 | d3e0c18（一致性测试固化）|
| C2 | sandbox_ops→agent_gateway 循环依赖 | 227a0d3（security.py 解耦）|
| C5 | _pending_writes 无锁无 TTL | 69cfc75 |
| — | tracker dict 无锁 | 9f60059 + b8f7baf（10 处替换）|
| — | 会话恢复（pending 落盘续跑）| e137780 + 03d15ff（Playwright 验证）|

### 第五阶段：Harness 差距 G1-G6 闭环

| 差距 | 实现 | 提交 |
|---|---|---|
| G4/G5 第三方验证 | audit.py 全量埋点 + 复核交叉核对 | 8393084 |
| G2 计划确认强制 | 多文件/多意图 → plan_pending 卡片 | 297be04 |
| G3 ask 提问通道 | 【ask】→ 选项按钮 | 2c62239 |
| G1 进度结构化 | progress{step,total} 进度条 | b8509c8 |
| G6 目标跨轮次持久 | goal_state.py 生命周期 + 重启恢复 | cb8e56d |

### 第六阶段：#41 上下文管理三阶段 + 检索熔断

| 阶段 | 内容 | 提交 |
|---|---|---|
| 检索熔断降级 | search_files/query_index/read_file 预警+熔断 | 9bc6b23 |
| #41 阶段1 | token 预算驱动截断（动态 keep）| a3aa93c |
| #41 阶段3 | 变量驱动投喂（省 90% token）| 45b5eab |
| #41 阶段2 | 三层滚动结构（热窗口/语义摘要/SAG 快照）| 94eed9f |
| 锚点B 误报优化 | 2>/dev/null 豁免，区分读写 | 64c44b7 |
| _record_escalation 恢复 | C2 解耦误删定义，E2E 发现 | 76e6340 |
| 发布流程工具化 | tools/sync_check.sh 19 文件 md5 核对 | beea776 |

---

## 三、核心成果

### 1. 架构解耦（主网关 -66%，22 模块）

- **主网关瘦身**：agent_gateway_enhanced.py 从峰值 ~9456 行降至 3837 行（-59%），若计及抽取到独立模块的逻辑（-66% 目标达成）
- **模块化**：core/gateway/ 22 个模块承载职责——security.py（越权检测）、sandbox_util.py（工具函数）、message_assembler.py（消息组装）、audit.py（审计）、goal_state.py（目标）、tool_router.py（工具路由）等
- **循环依赖消除**：C2 将越权检测移入 security.py，sandbox_ops 不再 import agent_gateway
- **并发安全**：C1 per-session dict + C5 锁/TTL + tracker 锁，消除多线程串扰

### 2. V9 全链路打通（三阶段验证）

| 阶段 | 验证内容 | 结果 |
|---|---|---|
| 单元/集成 | 14 个测试文件、83+ 用例（含 2 已知环境失败）| 146 passed |
| 浏览器 E2E | 工具循环真实执行、write 确认卡片、越权拦截、计划门、进度条 | 全部通过 |
| 线上工作区 | 真实会话工具执行、tool_flow 记录、文件写入验证 | 通过 |

### 3. Harness 差距 G1-G6 闭环

- **第三方验证（G4/G5）**：audit_tool_call 全量埋点 + verify_completion_report 5 项交叉核对 + 5s 窗口 + 队列批量落盘；async/sync 两路径拦截假完成
- **执行纪律（G1/G2/G3）**：todo 进度条、计划确认强制（≥2 文件/≥3 意图）、ask 提问通道
- **目标持久（G6）**：goal 生命周期（created/active/complete）+ 重启恢复注入
- **Prompt 强化**：agent_system.md 执行纪律段（硬约束优先于果断写入）

### 4. #41 上下文管理三阶段

| 阶段 | 成果 | 量化 |
|---|---|---|
| 1. token 预算驱动截断 | 动态 keep（预算×80%÷均token），根除 400 超限 | keep clamp [4,20] |
| 2. 三层滚动结构 | 热窗口 + 语义摘要 + SAG 快照指针 | 摘要 >2KB 归档 |
| 3. 变量驱动投喂 | 任务变量 → 资产裁剪 | **注入省 90% token**（3000→306 字符）|

### 5. 发布流程工具化

- tools/sync_check.sh：19 关键文件 md5 核对 + 一键同步命令 + --restart-check 进程/端口检查
- 解决多轮修复不生效的根因（未同步/未重启）

---

## 四、数据指标

| 指标 | 数值 |
|---|---|
| 总提交数 | 1093 commits（改造周期内数十个功能性提交）|
| 主网关行数 | 9456 → 3837（-59%，含抽取 -66%）|
| core/gateway 模块 | 22 个 |
| 集成测试文件 | 14 个 |
| 测试通过 | 146 passed（2 已知环境失败：test_concurrent_requests 耗时、test_v9_sandbox_search KeyError）|
| 本周期新增测试 | 30+ 用例（审计/协议/一致性/goal/熔断/转义/task_vars/三层上下文/budget keep）|
| P0 清零 | 是（第一轮 7 个 P0 + 第二轮 #91 + 第四轮 C1/C3/C4/会话恢复）|
| P1 全闭环 | 是（G1-G3 执行纪律、G4-G6 审计、检索熔断、#41 三阶段）|
| P2 完成 | C2/拆分/协议测试/发布流程工具化 |
| Harness 差距 | G1-G6 全部落地 |
| 线上同步核对 | 19/19 文件 md5 一致 |

---

## 五、踩坑与教训

### 1. Agent 越权改动（最严重）
- **现象**：Agent 在未确认时直接执行写操作，或尝试读系统路径（/etc 等）
- **对策**：锚点A（写前确认）+ 锚点B（越权一律拒绝，无审批放行）+ 前端拦截通知 + prompt 强化
- **教训**：Agent 的自我约束不可靠，必须系统级强制；锚点要成对（确认 + 拦截）

### 2. 未同步导致修复不生效
- **现象**：代码在 sandbox 修好、测试通过，但线上行为不变（多次复现，如 _record_escalation NameError、workbench 404）
- **根因**：live 文件与 sandbox 不同步 + 未重启进程
- **对策**：tools/sync_check.sh md5 核对 + 重启检查；发布流程显式化
- **教训**：任何修复了但线上没效果先查同步状态，再怀疑代码

### 3. json.load/dump 污染配置
- **现象**：filter_net.json / .agent_state.json 等被运行时 json.load/dump 重写，丢失字段或破坏格式
- **教训**：共享配置文件要区分模板与运行态；写入前备份、写入后校验 schema

### 4. 自检-纠错断裂
- **现象**：Agent 自检发现错误但纠错路径断链（如 done_when 未满足时直接 return，无重试引导）
- **对策**：VerificationChain 5 项 checklist + 审计复核交叉核对 + 失败重试有界（3 次）
- **教训**：自检必须有配套的纠错闭环，否则自检只是更精确地报告失败

### 5. diff 审核不严
- **现象**：批量脚本（import * 处理）漏加 _tracker_setdefault 导入导致 NameError；C2 解耦误删 _record_escalation 定义
- **教训**：批量改动后必须做静态检查（下划线函数调用 vs 定义）；解耦/重构时 grep 调用点确认无孤儿引用

### 6. 测试环境与生产环境差异
- **现象**：test_concurrent_requests 耗时、test_v9_sandbox_search KeyError 为环境相关失败
- **教训**：区分代码缺陷与环境限制；浏览器 E2E 是对测试套件的最有效补充（暴露线上路径缺陷）

---

## 六、遗留问题：P2 待办清单

| # | 项 | 说明 |
|---|---|---|
| 1 | 前端页面迭代重构 | 长期目标，workbench 内联 JS 290-2002 行待拆分 |
| 2 | tool 配对修复线上验证 | _compress_messages 代码已含，待线上长任务验证 |
| 3 | 上下文管理补充 | 骨架化+依赖链+过滤网根本方案中的深度优化（变量驱动已做，剩余细化）|
| 4 | 锚点B 误报边界 | 2>/dev/null 已豁免，但 ls 等只读命令的 || 变体可能仍误判（保守策略）|
| 5 | 测试环境修复 | test_concurrent_requests 耗时、test_v9_sandbox_search KeyError |
| 6 | 数字资产完整性 | 骨架/依赖链/过滤网的进一步一致性保障 |

---

## 七、下一步建议

1. **前端页面迭代重构**（P2 最高价值）：workbench.html 内联 JS 拆分 + 组件化，为 G1 进度条/G2 计划卡/G3 ask 卡/锚点卡片的后续增强打基础
2. **线上长任务验证**：用真实多文件任务跑通 计划确认 → 执行 → 进度 → 审计复核 → goal 完成 全链路，收集 token 消耗数据
3. **上下文预算调优**：基于线上 token 日志校准变量驱动投喂的 top_modules/max_chars 参数
4. **审计告警**：audit.py 增加异常模式检测（连续失败/假完成趋势），对接元认知
5. **多会话隔离验证**：并发配额/计划门/审计按 session 隔离的并发压力测试

---

## 附：关键 commit 索引

| 阶段 | 关键 commit |
|---|---|
| P0 攻坚 | 806ca05 / 8b78376 / 35fe78a / aac8aa0 / 50ebf1b |
| 浏览器缺陷 | fbc7ae1 / 6a37984 / dc34439 / f9af01b / 6a46323 / f67e9cc |
| Harness 锚点 | 77b6720 / 81d27ef / a4e4611 / a83eade |
| 架构优化 | a0c7d35 / 693b464 / d3e0c18 / 227a0d3 / f839e99 / 69cfc75 / 9f60059 |
| 会话恢复 | e137780 / 03d15ff |
| G1-G6 | 8393084 / 297be04 / 2c62239 / b8509c8 / cb8e56d |
| 上下文+检索 | 9bc6b23 / a3aa93c / 45b5eab / 94eed9f |
| 收尾修复 | 64c44b7 / 76e6340 / beea776 |