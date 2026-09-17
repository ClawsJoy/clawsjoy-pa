# 三项能力现状排查报告（只读）

> 排查日期: 2026-08-15 | 范围: workbench.html / agent_gateway_enhanced.py / core/gateway/chat_stream.py / execute_agent_task.py
> 性质: 只读排查，未改动任何代码

---

## 一、V9 工作区会话清理功能

### 现状

| 层面 | 是否有 | 详情 |
|---|---|---|
| 前端"清空对话"按钮 | ❌ 无 | grep button/onclick 无任何"清空/清除"按钮 |
| 前端指令 | ⚠️ 部分 | `/CLEAN`（agentSend L1202）：清 agentTerminal HTML + localStorage agent_logs；`/CLEAN_DISC`（send L390）：清 discussion-container DOM。**两者都只清前端显示，不清后端 session 上下文** |
| 后端路由 | ❌ 无 | 无 `/v9/clean` 或类似路由。`_pending_cleanup`（pending writes TTL）、`cleanup_inactive_goals`（goal 过期）均非会话清理 |
| V8 频道 | ❌ 完全缺失 | 无清空按钮；`/CLEAN_DISC` 只清聊天气泡 DOM，后端 messages/会话状态不受影响 |

### 影响

- Agent 工作区"对话历史"跨任务累积：agentSend 从 localStorage agent_history 恢复上下文 + 后端 session 的 messages 持续累积 → 上下文膨胀、token 浪费、任务间状态串扰
- 无后端级会话重置 → 用户无法开始"干净的新任务"

### 实施建议（优先级 P1）

1. **后端新增 `POST /v9/session/clean`**：清 session 的 messages（保留 system 首条）、pending writes、快照标记；返回确认
2. **前端加"清空"按钮**（Agent 工作区输入区旁）：点击 → 确认弹窗 → 调 /v9/session/clean + 清 localStorage agent_logs/agent_history + 终端重置（复用 /CLEAN 逻辑）
3. V8 频道复用同路由（聊天区清空按钮），或至少把 /CLEAN_DISC 升级为同时调后端
4. 改动量：后端 ~40 行 + 前端 ~60 行，低风险

---

## 二、V9 工作区流式交互

### 现状

| 项 | 状态 | 详情 |
|---|---|---|
| chat_stream SSE 分支 | ✅ 正常 | `/api/v5/chat/stream` → chat_stream_handler，yield `data: {chunk/done/plan_status}` 事件；前端 send() 用 `resp.body.getReader()` + TextDecoder 逐行解析，处理正确 |
| 前端 agentSend 流式 | ❌ 非流式 | `fetch /v9/agent/chat` + `await resp.json()`（L1237）——**等完整 JSON**（含 8 轮桥接循环）才渲染 |
| 延迟/缓冲 | ⚠️ 有 | ① V9 主路径：工具循环执行期间前端**完全空白**，直到 8 轮结束整体返回（G1 progress 也只能在响应后渲染）；② SSE 分支 `console.log('raw:', text)` 高频日志（每 chunk 一行，性能噪音）；③ SSE 本身 stream_with_context 无缓冲问题 |

### 影响

- V9 Agent 任务长任务（多轮工具调用）时，用户看到长时间"无输出"，体验差
- `console.log('raw:')` 在高频流下刷屏 devtools 并拖慢渲染

### 实施建议（按优先级）

1. **P1：V9 主路径中间态反馈**——后端 `/v9/agent/chat` 增加 `stream: true` 支持（或新端点 `/v9/agent/chat/stream`），逐轮桥接循环 yield 进度事件（round 完成/工具结果/最终内容）；前端 agentSend 检测流式响应，用 getReader 渲染中间进度。改动量：后端 ~80 行（改造 v9_agent_chat 返回流式生成器）+ 前端 ~50 行
2. **P2：移除/降级 `console.log('raw:')`**（SSE 解析处）——改为条件日志或删除，一行修复
3. **P2：SSE 心跳**——长流超 15s 无数据时前端假死风险，加注释心跳或前端超时重连

---

## 三、子任务并发能力

### 现状

| 项 | 状态 | 详情 |
|---|---|---|
| 子任务并发代码 | ❌ 无 | `sub_task_id` 仅作日志标签（[sub:xxx]）与 session key 后缀（_sid = session_id_sub_task_id），**无任何并发执行** |
| 任务线程 | ⚠️ 单任务 | L2949/L2980 两处 `Thread(target=_execute_agent_task)` 均为"计划确认后启动单个异步任务"，同一会话先后串行 |
| #31 长线循环 | ❌ 串行 | `for _round in range(max_rounds=100)`（L791）单线程串行；on_done 回调"驱动任务队列取下一个"——**串行队列**，完成一个才取下一个 |
| 并发基础设施 | ⚠️ 有部分 | `concurrent.futures.ThreadPoolExecutor(max_workers=3)` 仅用于 chat_stream.py L128 的 precision_feed 并行加载（与任务无关）；.agent_state.json 已有 `subtasks` 结构（_save_state 写子任务状态） |

### 加子任务并发的改动量评估

| 模块 | 内容 | 估计行数 |
|---|---|---|
| 任务分解 | LLM 把大任务拆成 N 个子任务（新提示词 + 解析），或在 /v9/agent/chat 计划确认时生成 | ~50 |
| 并发执行器 | ThreadPoolExecutor(max_workers=并发度) 管理子任务生命周期 + 结果收集 | ~120 |
| 状态隔离 | 每子任务独立 messages/tool_steps/tracker（现 _sid 已有基础）；.agent_state.json subtasks 写入（已有结构复用） | ~80 |
| 审计/SAG | audit_tool_call 带 sub_task_id（已支持）；tool_flow 隔离 | ~40 |
| 前端进度 | 子任务级进度展示（每子任务 tool_steps 流） | ~60 |
| 测试 | 并发执行器单测 + 集成 | ~80 |
| **合计** | | **~400-450 行 + 调试** |

### 关键风险

1. **共享 tracker 竞态**：`_session_write_tracker`/`_session_tool_tracker` 等 per-session dict 无并发锁（仅 `_tracker_setdefault` 加锁），并发子任务写 tracker 会串扰
2. **LLM 并发配额**：并发子任务同时调 LLM，需限流（模型 qps/余额）
3. **消息队列顺序**：on_done 回调聚合顺序 vs 子任务完成顺序，需按 task_id 归位
4. **模式限制/配额**：check_tool_quota 按 session 计数，并发子任务共享配额会被快速消耗

### 实施建议（按优先级）

1. **P2（可选先做）：串行队列 → 有界并发**——把现有"完成一个取下一个"改成 ThreadPoolExecutor 有界并发（max_workers=2~3），复用现有 on_done 回调驱动，改动量 ~150 行，风险可控
2. **P3（大改）：真子任务并行**——LLM 分解 + 并发执行器 + 状态隔离（~400 行），需先解决 tracker 锁（C1 已部分 per-session 化）与 LLM 配额

---

## 优先级总览

| 优先级 | 项 | 理由 |
|---|---|---|
| **P1** | 会话清理（后端 /v9/session/clean + 前端按钮） | 功能缺失，改动小（~100 行），体验/上下文卫生收益直接 |
| **P1** | V9 流式中间态反馈 | 长任务空白等待是当前最大体验短板，改动中等（~130 行） |
| **P2** | SSE console.log 噪音清理 | 一行修复 |
| **P2** | 串行队列 → 有界并发（2-3 workers） | 中等改动（~150 行），复用现有回调，风险可控 |
| **P3** | 真子任务并行 | 大改（~400 行），需先解决 tracker 锁 + LLM 配额 |
