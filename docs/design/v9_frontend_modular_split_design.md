# V9 前端模块化重构 — 拆分映射表 + 迁移顺序

- 日期: 2026-08-19
- 现状: workbench.html 2735 行(内联 JS L305-2715); api-client.js(258 行, UMD 挂 window.DSH_API)已存在未接线
- 目标: 按 7 模块拆 ES modules, 渐进迁移, 每拆一个浏览器验证, 不破坏现有功能

---

## 一、段落 → 模块映射表

| workbench 段落 | 行区间 | 目标模块 | 函数 |
|---|---|---|---|
| 全局状态 | 306-327 | __APP_STATE | userId/sessionId/currentThread/threads/agentRunning/agentAbort/planState/discussionHistory |
| 聊天 | 377-838 | discussion.js | send/addMessage/addDiscussBtn/clearChat/showAtList/hideAtList/insertAt/refreshDiscussionHistoryList |
| Agent Discussion 渲染 | 862-1151 | discussion.js | _displayDiscussionRecord/renderDiscussionDone/saveCurrentDiscussion/saveDiscussionRecordFromView/showDiscussionRecord/FromApi/_renderDiscussionList/_renderDiscussionListFromLocal |
| 时间线 | 1304-1323 | timeline.js | loadTimeline |
| #6 回放 | 1324-1355 | timeline.js | loadReplay |
| Agent 工作区(终端) | 1356-1410 | agent-terminal.js | agentLog/renderAgentOutput |
| Agent 工作区(循环) | 1411-1833 | chat.js | agentSend/runAgentLoop/readSSEStream/continuePausedTask/renderProgressBar/getProgressSummary |
| 方案按钮 | 1834-2116 | approval.js | renderWriteConfirmCard/renderPlanConfirmCard/renderAskCard/sendWriteApproval/sendPlanApproval/sendAskChoice/selectPlan/renderPlanButtons |
| 异步后台执行 | 2117-2412 | subtask-panel.js(+chat) | createSubtask/pollSubtasks/renderSubtasks/loadTasks/agentSendAsync/pollTaskResult |
| 通知铃铛 | 2575-2715 | notifications.js | pollNotifications/loadNotifList/toggleNotifPanel/markNotifRead/markAllRead/bellSetBadge |
| 侧边栏/导航/文件树/成员/招聘/账单/线程/Agent面板/初始化 | 328-376, 839-861, 1152-1303, 2413-2574 | 留内联(misc, 后续再拆) | — |

## 二、模块依赖 + 全局挂载

- notifications.js: DSH_API.notification.*(v8/notifications*), bell DOM; 零交叉依赖
- timeline.js: DSH_API.ledger.* + v9/replay, __APP_STATE.sessionId, escapeHtml
- agent-terminal.js: __APP_STATE.currentThread, agentTerminal DOM(localStorage agent_logs)
- chat.js: agent-terminal.agentLog, approval 渲染卡(留内联期), DSH_API.agent.*, __APP_STATE
- approval.js: chat.continuePausedTask, agentLog, escapeHtml
- subtask-panel.js: DSH_API.subtask.*, agentLog, __APP_STATE.sessionId
- discussion.js: agentLog/renderAgentOutput, escapeHtml, __APP_STATE.discussionHistory

内联 onclick 必须保持 window 可见(已盘点): openAgent/toggleNotifPanel/markAllRead/send/clearChat/loadReplay/doHire/switchThread/newThread/closeAgent/toggleFilePanel/agentSend/agentStop/agentSendAsync/createSubtask/insertAt/saveCurrentDiscussion/saveDiscussionRecordFromView/showDiscussionRecord/showDiscussionRecordFromApi/togglePause/editMember + 卡片动态按钮(sendWriteApproval/sendPlanApproval/sendAskChoice/selectPlan)
→ 每模块 IIFE 末尾显式 window.<fn> = fn(handler 所需), 其余仅模块内导出。

## 三、加载方式(非破坏)

- 顺序: api-client(UMD) → 模块(defer, 先于内联执行) → 内联余量(定义 __APP_STATE + 调模块 init)
- classic defer + IIFE(非 ES module 起步): 与内联 onclick handler 兼容(window 挂载), 后续可平滑切 type=module
- 每个模块: (function(global){ ...; global.fn = fn; })(window); 读 window.DSH_API / window.__APP_STATE
- 提取的函数必须从内联删除(防内联后定义覆盖模块)
- window.__APP_STATE(内联顶部初始化): 纯对象 + get/set; 内联余量改动状态时同步

## 四、迁移顺序(渐进 + 每步浏览器验证)

| 步骤 | 模块 | 理由 | 验证点 |
|---|---|---|---|
| 1 | notifications.js | 最自洽(独立段落, 仅 DSH_API + bell DOM) | 通知 badge/轮询 5s/SSE/标记已读 |
| 2 | timeline.js | 自洽(loadTimeline + loadReplay, 仅 sessionId) | 时间线 tab 加载/回放按钮 |
| 3 | agent-terminal.js | chat 的依赖地基(agentLog 全链路用) | 终端日志渲染 |
| 4 | chat.js | 核心循环(agentSend/runAgentLoop/SSE); 依赖 3 + 内联渲染卡 | 执行/流式/停止/续跑 |
| 5 | approval.js | 依赖 chat.continuePausedTask(已迁) | 写/计划/ask 审批卡 + 确认续跑 |
| 6 | subtask-panel.js | 依赖 agentLog + sessionId | 子任务创建/轮询/面板 |
| 7 | discussion.js | 交叉依赖最多, 最后拆 | 聊天/讨论/保存/回放记录 |

每步: 提取函数出内联 → 模块文件 + 挂载 → 浏览器刷新验证该模块功能 + 全站无 console 错误 → git 提交。

## 五、风险与兼容

| 风险 | 缓解 |
|---|---|
| 内联 handler 引用已迁函数 | 模块显式挂 window; 提取后删除内联定义 |
| __APP_STATE 与内联 let 双源 | 内联余量同步更新; 模块只读 __APP_STATE |
| defer 顺序(模块先于内联) | 模块只定义不 init; 内联调用 init(现状已如此) |
| api-client 未接线 | 步骤 0: workbench 引入 api-client.js, 模块用 DSH_API; 内联余量暂用裸 fetch(后续迁) |
| 重复定义覆盖 | 提取即删内联副本, 一个函数只存在于一个模块 |
