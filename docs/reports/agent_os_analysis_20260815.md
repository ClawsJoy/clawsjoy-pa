# ClawsJoy OS 分析报告 — Agent 行为与系统问题（2026-08-15）

## 分析范围与方法
- 数据源：线上网关（5002）真实执行监督、PostgreSQL SAG（code_entities 27777 实体）、运行数据审计（billing/tasks/orchestrations/events）、沙箱代码核对
- 方法：API 触发真实 V9 执行 → 状态文件/日志/SAG 断言 → 根因代码定位

## 8 项发现与处理状态

| # | 发现 | 严重度 | 状态 |
|---|---|---|---|
| P0-1 | 假完成：任务 done 但无产物（agent 输出"请提供要审查的代码"被当成功） | 🔴 | ✅ 已修（806ca05） |
| P0-2 | 队列续跑断链：done 后不自动取下一个，pending 卡死 | 🔴 | ✅ 已修（806ca05） |
| P0-C | plan() 任务 output_file 未持久化 → 交付物校验失效 | 🔴 | ✅ 已修（806ca05） |
| P1-1 | @提及名字不匹配（"编排Agent" vs "计划经理"岗位） | 🟠 | ✅ 已修（27f86d0） |
| P1-2 | 写任务不触发工具（普通对话只聊天） | 🟠 | ⏳ 待决策（方案见下） |
| P1-3 | billing agent_name 缺失（'?'） | 🟠 | ✅ 修正：线上正常（53997 条全归因，初判误读沙箱旧数据） |
| P1-4 | 脏数据：空标题/超龄 pending 永挂 | 🟠 | ✅ 已修（27f86d0 启动清理） |
| P2-1 | dependency_edge 数量不一致 | 🟡 | ✅ 修正：线上 JSON(1441/8403) = SAG(8403)，初判误读沙箱旧 JSON |

## 修复提交
- 806ca05 fix(P0): 任务可靠性三连修复（假完成/队列续跑/output_file 持久化）
- 27f86d0 fix(P1): @提及岗位名兼容 + 启动脏数据清理

## 验证证据
- P0-A：execute_task mock 反问输出 → failed；_deliverable_ok 严格校验(标题路径不存在→False)；纯生成任务不误伤
- P0-B：review 空 → pending_review + start_next 队列继续；超时 120s×3→30s×2
- P0-C：plan() 后磁盘任务含 output_file
- P1-1：@编排Agent → 岗位匹配到"计划经理"(orchestration_agent)
- P1-4：空标题/超龄 → failed，新任务保留
- #88：HTTP /v9/sandbox/* 调用触发 record_tool_flow（mock 捕获 read_file/flow_p1）

## P1-2 待决策方案（写任务直达工具）
- 根因：v5_execute 无 @ 提及 → chat_agent 无工具执行能力
- A. 写意图自动转 plan()（推荐，改动小，误触发可由 #86 兜底）
- B. chat_agent 接工具循环（自然但改动大）
- C. 保持现状 + 回复提示"请 @计划经理"

## 发布流程缺口（新增发现）
线上网关（/home/flybo/clawsjoy_v5）与沙箱代码不同步：v5_execute.py / task_orchestrator.py / agent_gateway_enhanced.py 3 文件待同步；线上进程运行旧代码（探测：@编排Agent 返回旧错误）。
建议：建立同步脚本 + 重启验证流程（部署管道）。
