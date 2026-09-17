# V9 项目状态检查与建议书

> 日期：2026-08-15
> 对标：Manus（产品体验/可视化/人机协作）× Harness（系统可靠性/锚点/安全防线）
> 依据：最近三轮浏览器端到端验证（vfy_web3~6、gate1/2、b1、o1b、final）、#91-#105 修复历史、tool_flow 396 条记录

---

## 一、当前 V9 能力清单

### 1.1 已实现（✅ 已验证）

| 能力 | 说明 | 验证证据 |
|---|---|---|
| 服务端工具执行器 | v9_agent_chat 桥接循环（8 轮）执行 read/write/exec，回传 tool_calls+结果 | #94/#91，tool_flow 396 条 |
| 工具步骤可视化 | tool_steps 收集+注入，前端渲染 ✅/❌/⏳ 工具行 | #101，浏览器实测 vfy_web5/6 |
| 写操作确认（锚点A） | write_file/edit_file 拦截 → 确认卡片 → 确认/拒绝 | #102，实测 gate1 确认+gate2 拒绝 |
| 越权拦截（锚点B） | 路径逃逸/高危命令硬拒绝，拉回沙箱，无审批放行 | #104，实测 /etc 写入拦截 |
| 越权审计落盘 | escalations 字段幂等追加（timestamp/tool/target/reason/action） | #105，单测通过 |
| 防重复执行（O1） | bridge_exhausted 标记 + 清空 tool_calls + 前端跳过 | #103，跑满 8 轮场景 |
| Ollama 本地降级 | 无 DeepSeek Key 时走 qwen2.5:7b 本地 function calling | d3d3472 |
| 假完成拦截 | VerificationChain 5 项 checklist + 连续失败暂停 | 空工作区假宣告被正确拦截 |
| Agent 行为约束 | agent_system.md 增补 5 段（写确认/工具归属/报告/花名册/预算） | 644ba4a |

### 1.2 半实现（⚠️ 可用但有缺口）

| 能力 | 缺口 |
|---|---|
| 会话持久化/恢复 | 前端靠 localStorage，新浏览器会话看不到既有工作区；pending 写操作刷新即丢 |
| 桥接循环退出 | 8 轮上限无"继续下一批"机制，跑满即停（O1 缓解但未解决长任务） |
| 写确认上下文 | approve 依赖全局 __agentSendMessages，多标签页/多任务可能串 |
| 命令越权检测 | 覆盖主流系统目录操作，但新型绕法（env 变量、通配符）需持续补 |

### 1.3 未实现（❌）

| 能力 | 说明 |
|---|---|
| 截图可视化 | Manus 核心体验：agent 浏览器操作截图流，V9 无 |
| 任务队列/并行 | 单任务串行，无任务编排队列 UI |
| 审批记录前端查看 | 审计落盘了但前端无查看入口 |
| 会话恢复（pending 续跑） | 刷新/断线后 pending 写操作丢失 |
| 多 Agent 协作可视化 | 花名册/Agent@Agent 存在但工作台无协作视图 |

---

## 二、与 Manus 的体验差距

| 维度 | Manus | V9 现状 | 差距 | 优先级 |
|---|---|---|---|---|
| 过程可视化 | 左侧实时操作流 + 截图序列 | tool_steps 文本行 | 中（文本够用，缺截图） | P1 |
| 工作台布局 | 任务/文件/终端分区 | 单终端 + 文件树 | 中（已可用） | P2 |
| 展开/分呈式 | 结果折叠展开、报告卡片 | 纯文本 agentLog | 大（长任务难读） | P1 |
| 交互锚点 | 写操作确认 | ✅ 确认卡片（已做） | 无 | — |
| 异步任务 | 提交后离开，完成通知 | 前端循环阻塞 agentSend | 大（页面不可关） | P1 |
| 交付物呈现 | 独立文件/报告卡片 | 终端文本 + 文件树 | 中 | P2 |

**结论**：V9 已具备 Manus 式**过程透明度**（tool_steps + 锚点），但缺**截图流**和**异步任务**两大体验支柱。

---

## 三、与 Harness 的可靠性差距

| 维度 | Harness 设计 | V9 现状 | 差距 | 优先级 |
|---|---|---|---|---|
| 防重复 | 工具调用显式/原子 | ✅ O1 bridge_exhausted | 无 | — |
| 防越权 | 沙箱权限 + 升级审批 | ✅ 锚点B 硬拒绝 + 审计 | 无 | — |
| 审计 | 全操作可回溯 | ⚠️ tool_flow + escalations，但无前端查看 | 中 | P1 |
| 恢复 | 断点续跑/目标持久 | ⚠️ 无（刷新丢 pending） | 大 | P0 |
| 超时 | 每步+整体超时 | ✅ 任务级 600s + 连接 10s/读 60s | 无 | — |
| 幂等 | 重试安全 | ⚠️ approve 依赖内存 pending，重启丢 | 中 | P1 |
| 沙箱隔离 | 工作区只读+授权 | ⚠️ 工具层防线已补，但 /tmp 等边界需审视 | 低 | P2 |

**结论**：可靠性已大幅提升（#99-#105 修复 8 个真实 bug），**最大缺口是会话恢复**——断线/重启丢 pending 和进行中任务。

---

## 四、我们的独有优势（对比 Manus/Harness 通用 agent）

| 优势 | 说明 | 实证 |
|---|---|---|
| 花名册（roster） | Agent 身份/岗位/模型注册表，工作台可见 | 团队成员列表渲染 |
| Agent@Agent | 跨 Agent 指派任务 | 工作台 @提及 |
| 精准投喂 | 按意图注入世界模型/SAG/OS 事件 | agent_system.md 声明 |
| SAG 代码图谱 | code_entities 实体+依赖边（tool_flow 396 条入 SAG） | query_index 检索 |
| VerificationChain | 5 项写入验证 + 假完成拦截 | 空工作区拦截实证 |
| 锚点体系 | A 写确认 + B 越权拦截 + 审计（本轮新增） | gate/final 测试 |

**独特定位**：V9 不是通用 agent，而是**带组织结构的代码交付 agent**——花名册决定谁能做什么，SAG 让它懂代码库，锚点让老板掌控写入。

---

## 五、优先级建议

### P0（阻塞性，必须做）
1. **会话恢复**：pending 写操作 + 进行中任务落盘，刷新/重启后可续（对 Harness 可靠性锚点）
   - 方案：pending 写操作写入 .agent_state.json（同 escalations 模式），v9_agent_chat 入口检测恢复
2. **异步任务模式**：agentSend 改后台任务（async + task_id 轮询），页面可关，完成通知（对 Manus 体验）

### P1（高价值）
3. **审计前端查看**：escalations + tool_flow 在前端工作台可视化（老板可看 Agent 尝试过什么）
4. **长任务分页**：桥接 8 轮跑满 → 自动续下一批（带进度），而非停下
5. **结果展开/折叠**：长输出卡片化，可折叠（对标 Manus 分呈式）
6. **Ollama 路径端到端验证**：本地无网络完整跑通（已有降级，未做浏览器验证）

### P2（增强）
7. **截图流**：execute_command 产出截图附到 tool_steps（Playwright 已可用）
8. **命令越权检测持续加固**：env/通配符/编码绕法
9. **多 Agent 协作视图**：花名册成员 + Agent@Agent 任务流可视化
10. **工作台重构**：分区布局（终端/文件/审计/结果），当前单终端

---

## 六、风险与观察

1. **前端双重执行风险残余**：O1 已缓解，但 approve 后 agentSend 重进循环依赖全局 messages，多标签页可能串（建议 session 级 key）
2. **tool_flow 增长**：396 条已可观，SAG 查询性能需关注
3. **测试套件**：102 通过 + 2 环境失败（test_concurrent_requests 耗时、test_v9_sandbox_search KeyError）——后者值得查（疑似 mode 判定空结果）
4. **agent_system.md 与实现一致性**：已增补 5 段，但需随功能迭代持续同步

---

## 附：三轮验证实证

| 任务 | 结果 | 说明 |
|---|---|---|
| vfy_web3~6 | ✅ 全通过 | #99/#100 修复后 write_file 直写成功（不再 heredoc） |
| vfy_gate1 | ✅ 确认→写入 | 锚点A 卡片+approve 闭环 |
| vfy_gate2 | ✅ 拒绝→不写 | 锚点A reject 分支 |
| vfy_o1b | ✅ 确认→写入 | 锚点A+O1 共存 |
| /etc 越权写 | ✅ 拦截+审计 | 锚点B escalation_blocked + escalations 落盘 |
| vfy_final | ✅ 确认→写入 | 最终回归 |
| 写任务耗时 | 3-18s | write_file success 52-635ms，主要耗时在探测轮 |
