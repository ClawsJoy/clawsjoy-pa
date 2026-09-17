# ClawsJoy OS 问题清单

> 维护：按发现轮次汇总，标注状态与关联修复。最后更新 2026-08-15。

## 状态标记
- ✅ 已修复（含 commit）
- 🔧 已修复待线上验证
- ⏳ 待修复/待决策
- 👀 观察项

---

## 第一轮（agent 行为 + OS 分析）

| # | 问题 | 严重度 | 状态 |
|---|---|---|---|
| P0-1 | 假完成：任务 done 但无产物（agent 反问被当成功） | 🔴 | ✅ 806ca05 |
| P0-2 | 队列续跑断链：done 后不自动取下一个，pending 卡死 | 🔴 | ✅ 806ca05 |
| P0-3 | plan() 任务 output_file 未持久化 → 交付物校验失效 | 🔴 | ✅ 806ca05 |
| P1-1 | @提及名字不匹配（"编排Agent" vs 岗位名） | 🟠 | ✅ 27f86d0 |
| P1-2 | 写任务不触发工具（普通对话只聊天） | 🟠 | ✅ 3db903c |
| P1-3 | billing agent_name 缺失 | 🟠 | ✅ 复核为无问题（线上 53997 条全归因） |
| P1-4 | 脏数据：空标题/超龄 pending 永挂 | 🟠 | ✅ 27f86d0 |
| P2-1 | dependency_edge 数量不一致 | 🟡 | ✅ 复核为无问题（线上 8403=JSON） |
| P0-4 | v5_execute discussing 分支漏 return | 🔴 | ✅ b729e1d |
| P0-5 | V9 工具循环 4 层连锁 bug（true/false、reasoning_content、tracker、mkdir、_validate_messages） | 🔴 | ✅ 8b78376 |
| P0-6 | V9 执行卡死（LLM 慢响应/连接挂起） | 🔴 | ✅ 35fe78a |
| P0-7 | 主文件 5 处抽取断链（_archive_user_message 等 NameError） | 🔴 | ✅ aac8aa0 |

## 第二轮（V9 全链路验证）

| # | 问题 | 严重度 | 状态 |
|---|---|---|---|
| **#91** | **V9 工具循环无服务器端执行器**（桥接模式只返回 tool_calls 不执行） | 🔴 P0 | ✅ 8b78376 + 线上验证通过（2026-08-15：web_test/session_vfy9，8 轮桥接循环，29 条 tool_flow，vfy_demo.py 写入+验证） |
| **#92** | 沙箱路径重写规则三视图不一致（双重 clawsjoy_dev 前缀） | 🟠 | ✅ fbc7ae1（线上验证发现 _resolve_path 对带前缀路径双重拼接 → 剥离前缀 + uid/sid 推导修正 parts[-3]/[-2]） |
| **#93** | V9 端点 message vs messages 字段不一致 | 🟠 | ✅ bb4f2e7（v9_agent_chat 兼容单数 message 字段，curl 可直接触发） |
| **#94** | 桥接模式绕过防假完成和 tool_flow（v9_agent_chat 直连 adapter 不经执行器） | 🟠 P1 | ✅ 50ebf1b + 线上验证通过（v9_agent_chat 接入 _execute_sandbox_tool 真实执行 + 回传循环） |

## 第三轮（Manus 可视化 + Harness 锚点，浏览器端验证）

| # | 功能 | 严重度 | 状态 |
|---|---|---|---|
| **#101** | 工具步骤可视化（tool_steps 回传 + 前端渲染）| 🟡 | ✅ 后端收集+注入 + 前端渲染（浏览器验证：工具行 ✅/❌/⏳ 实时展示）|
| **#102** | 锚点A 写操作前确认（Write Approval Gate）| 🟠 | ✅ 桥接拦截 write_file/edit_file → pending 卡片 → 确认/拒绝（浏览器验证：卡片出现+确认写入+拒绝拦截）|
| **#103** | O1 防重复执行（bridge_exhausted）| 🟠 | ✅ 后端跑满 8 轮标记+清空 tool_calls + 前端跳过（正常路径无行为变化）|
| **#104** | 锚点B 越权拦截（路径逃逸/高危命令一律拒绝，无审批放行）| 🔴 | ✅ 路径越权+高危命令检测 → escalation_blocked → 拉回沙箱（单测 PASS + 浏览器验证：/etc 写入拦截）|
| — | agent_system.md 增补 5 段（写确认/工具归属/报告规范/花名册/预算）| 🟡 | ✅ 644ba4a |

## 第四轮（架构优化 — 基于 v9_arch_review.md 代码实证）

| # | 项 | 严重度 | 状态 |
|---|---|---|---|
| **C1** | 并发配额串扰（_consecutive_reads/_consecutive_lists 模块级整数）| 🔴 P0 | ✅ a0c7d35 + 474c82b + 38da103（改 per-session dict，修复 3 个连锁问题：sandbox_write 重置 / 插件整数比较 / tool_router 局部回传赋值 UnboundLocalError）|
| **C3** | v8 roster 蓝图双注册（213+639）| 🔴 P0 | ✅ 693b464（删 214 行重复，保留 639 统一区）|
| **C4** | 工具双实现行为漂移（router 插件 vs sandbox handler）| 🔴 P0 | ✅ d3e0c18（一致性测试固化路径解析共享；两层职责有意保留：HTTP 有配额/模式，桥接有连续失败暂停）|
| **C2** | sandbox_ops→agent_gateway 循环依赖 | 🟡 P2 | ✅ 227a0d3（越权检测移入 core/gateway/security.py，sandbox_ops 不再 import agent_gateway）|
| — | sandbox_ops 大杂烩（18 imports）| 🟡 P2 | ✅ f839e99（工具函数移入 sandbox_util.py，1437→1226 行 + 显式 re-export）|
| — | 前后端协议一致性 | 🟡 P2 | ✅ 2b68486（协议测试固化；executing 分支确认非死代码，为团队频道正确逻辑）|
| **C5** | _pending_writes 无锁无 TTL | 🟡 P1 | ✅ 69cfc75（_get_pending_lock + _pending_cleanup 60s TTL，拦截/放行/approve 加锁）|
| — | tracker dict 无锁（_session_write_tracker 等）| 🟡 P1 | ✅ 9f60059 + b8f7baf（_tracker_setdefault 加锁 setdefault，7 文件 10 处替换；批量脚本漏 import 已补）|
| — | 会话恢复（pending 落盘续跑）| 🔴 P0 | ✅ e137780 + 03d15ff（pending 落盘 .agent_state.json + 重启恢复 + 只保留 TTL 内有效项；Playwright 验证：不确认→落盘→文件不写→重启恢复）|

## 第五轮（上下文管理 + 检索熔断 + 数字资产完整性）

### 补充一：上下文管理（#41 未闭环）

| # | 问题 | 状态 |
|---|---|---|
| **#41** | V9 上下文超限第五次 400 | ✅ 阶段1 a3aa93c（token 预算驱动截断，动态 keep）|
| — | 骨架化 + 依赖链 + 过滤网根本方案 | ✅ 阶段3 45b5eab（变量驱动投喂：任务变量 → 资产裁剪，实测省 90% token）|
| — | tool 配对修复（_compress_messages）| ✅ 代码已含，待线上验证 |
| — | 三层滚动结构（不滚动/滚动/被挤入 SAG）| ✅ 阶段2 94eed9f（热窗口 + 语义摘要 + SAG 快照指针）|
| — | 变量驱动投喂（替代关键词匹配）| ✅ 45b5eab（task_vars.py：extract/filter + precision_feed 接入）|

### 补充二：检索熔断降级

| # | 问题 | 状态 |
|---|---|---|
| — | query_index 熔断后无强制降级指令 | ✅ 9bc6b23（3 次空熔断 + 熔断前"还剩 N 次"预警）|
| — | read_file 读取上限熔断后无降级 | ✅ 9bc6b23（>=max-1 预警 + 达上限熔断强制写入）|
| — | search_files 熔断后无降级 | ✅ 9bc6b23（插件路径新增连续空熔断，对齐 HTTP #192）|
| — | 熔断前无"还剩 N 次"预警 | ✅ 9bc6b23（三工具统一预警）|

### 补充三：数字资产与审计完整性

| # | 问题 | 状态 |
|---|---|---|
| **#83** | DATABASE_URL 缺失 → SAG/tool_flow 空转 | ✅ 已解决（DB连接正常，code_entities 28227 条 / tool_flow 421 条）|
| — | 锚点B 越权审计落盘（escalations）| ✅ 已做 |
| — | user_messages 归档双写沙箱镜像 | ✅ 已完成（未编号）|

### 补充四：V9 Agent 与 Harness 差距分析 — 落盘缺口

| # | 问题 | 状态 |
|---|---|---|
| **#100** | Harness 差距报告未落盘 | ✅ b54c91d（已输出 docs/reports/v9_vs_harness_gap_analysis.md：G1-G6 差距 + P0 审计复核/P1 执行纪律方案）|
| **#101** | V9 Agent 无 Harness 执行纪律 | ✅ G1-G6 全部落地：b8329af 执行纪律段（prompt）+ 297be04 G2 计划确认强制（plan_pending 卡片）+ 2c62239 G3 ask 提问通道（选项按钮）+ b8509c8 G1 进度条（progress）+ cb8e56d G6 目标跨轮次持久（goal_state.py 生命周期 + 重启恢复注入）|
| **#102** | V9 无第三方验证视角 | ✅ 8393084 G4 落地：core/gateway/audit.py（audit_tool_call 全量埋点 + 队列批量落盘 + verify_completion_report 5 项复核 + 5s 窗口）+ async/sync 两路径交叉核对拦截假完成 |

**关联**
- #101 → P1，System Prompt 增强
- #102 → P1，审计层扩展（从讨论场景扩展到 V9 工具循环）

> 注：Harness 差距报告输出后，将基于报告填充具体差距项。

## 第六轮（自检与设计报告 — 基于 code_health_check / engineering_retrospective / library_architecture_design）

### 补充五：代码健康检查（code_health_check.md 实证）

| # | 问题 | 严重度 | 状态 |
|---|---|---|---|
| H1 | v9_agent_chat 1981 行 + _execute_agent_task 1173 行（巨型函数，共 17 个 >100 行）| 🔴 | ⏳ 待拆分 |
| H2 | 延迟导入隐性耦合（execute_agent_task ↔ sandbox_ops ↔ tool_router 函数内互 import）| 🔴 | ⏳ 待加 CI 防线 |
| H3 | shared_state L182/L262 重复 import 块（psutil/flask/CORS/precision_feed/sandbox_tools 双份）| 🟠 | ⏳ 待合并 |
| H4 | v9_user_balance 与 v9_agent_chat 42 行重复 plan_status 逻辑 | 🟠 | ⏳ 待抽公共函数 |
| H5 | 10 处未使用 import（sandbox_git json/time/Path、sandbox_ops logging、sandbox_util 顶层死导入等）| 🟡 | ⏳ 待清理 |
| H6 | print 密集（execute_agent_task 66 处等 8 文件，应迁移 logging）| 🟡 | ⏳ 待迁移 |
| H7 | tool_audit.jsonl 未生成（audit 落盘路径待验证）| 🟠 | ⏳ 待验证 |
| H8 | 同步工具未覆盖"系统文件双写沙箱镜像"规则（说明书类改正本后沙箱读到旧版）| 🟠 | ✅ d6e9ad0（sync_check.sh 新增 SYS_FILES 双写检查：live正本→sandbox镜像，[MIRROR-NEW]/[MIRROR-DIFF] 检测 + 一键双写）|
| H9 | user_messages 沙箱镜像历史未回填（live 正本 16389 行 vs 沙箱镜像 405 行）| 🟠 | ⏳ 待回填（sync_check.sh 已覆盖检测：6a4a344 运行时双写检查）|

### 补充六：落盘检索体检（library_architecture_design.md 实证）

| # | 问题 | 严重度 | 状态 |
|---|---|---|---|
| R1 | 10 类落盘数据仅 2 类可检索（tool_flow + 代码实体），审计/越权/快照/goal/ISSUES/假完成日志 8 类"只落盘不可检索" | 🔴 | ✅ 2149b0b（sag_audit_bridge.py + 4 处注册）+ 0f37f66（query_index entity_type）；线上验证：audit_event 3 条 / goal 3 条已入库可查 |
| R2 | 无统一检索入口（query_index 不支持 entity_type 过滤）| 🟠 | ✅ 0f37f66（query_index(query, entity_type) 统一检索，source=sag）|
| R3 | 无独立工具说明书（agent_manual.md）| 🟠 | ⏳ 待 P2 |
| R4 | 说明书（BRIEF/agent_system/纪律段）分散，未注册为 manual 实体 | 🟡 | ⏳ 待 P2 |

### 补充七：工程化总结遗留（engineering_retrospective.md P2 清单）

| # | 问题 | 严重度 | 状态 |
|---|---|---|---|
| E1 | 前端页面迭代重构（workbench 内联 JS 290-2002 行拆分）| 🟡 | ⏳ 长期目标 |
| E2 | tool 配对修复线上验证（_compress_messages 代码已含）| 🟡 | ⏳ 待线上长任务 |
| E3 | 锚点B 误报边界（ls 等只读命令的 || 变体）| 🟡 | ⏳ 待评估 |
| E4 | 测试环境修复（test_concurrent_requests 耗时、test_v9_sandbox_search KeyError）| 🟡 | ⏳ 待修复 |
| E5 | 数字资产完整性（骨架/依赖链/过滤网一致性）| 🟡 | ⏳ 待细化 |

## 待办汇总（未闭环）

### 已完成（历史闭环）
- ✅ P0 全部清零（假完成/卡死/断链/越权/并发/会话恢复）
- ✅ P1 全部闭环（G1-G6 执行纪律+审计、检索熔断、#41 上下文三阶段）
- ✅ 发布流程（beea776 sync_check.sh）
- ✅ #100 差距报告 / #101 执行纪律 / #102 第三方验证

### 第六轮新增待办（来自三份自检报告）
| 优先级 | 编号 | 任务 |
|---|---|---|
| 🔴 P0 | R1 | 落盘检索编目（sag_audit_bridge.py：审计/越权/快照/goal 注册 SAG）|
| 🔴 P0 | H1 | 巨型函数拆分（v9_agent_chat 1981 行 / _execute_agent_task 1173 行）| ✅ 完成：_execute_agent_task 1173→约850行（13fb9ec/8a52fe4/1aecd7b/861d060 + a425193 修僵尸bug）；v9_agent_chat 1981→约650行（263eaec/ac4cc77/748292b/0d1ebc0/14f9cb6 提取5函数，含1200行桥接循环）+ 4轮审核/E2E抓出8个漏变量（tokens/model/plan_status/current_plan/_exec_tool_94/data/_task_start_ts/_ts_progress）全部修复；live E2E 5/5通过（无工具/read_file/tool_steps/ask/进程）|
| 🟠 P1 | R2 | query_index entity_type 过滤（统一检索入口）|
| 🟠 P1 | H2 | 延迟导入 CI 防线（禁止 core/gateway 顶层 import agent_gateway）|
| 🟠 P1 | R3/R4 | agent_manual.md 工具说明书 + 注册 manual 实体 |
| 🟠 P1 | H3/H4 | 重复代码收敛（shared_state import 块 / plan_status 公共函数）|
| 🟠 P1 | H7 | tool_audit.jsonl 落盘路径验证 |
| 🟡 P2 | H5 | 未使用 import 清理（10 处）|
| 🟡 P2 | H6 | print → logging 迁移（8 文件）|
| 🟡 P2 | E1-E5 | 前端重构 / tool 配对线上验证 / 锚点B 边界 / 测试环境 / 资产完整性 |

### 第六轮完成状态更新
- ✅ R1/R2（落盘检索编目 + 统一检索入口）：2149b0b + 0f37f66
- ✅ R3/R4（agent_manual.md + manual 实体）：27e941b
- ✅ H8（系统文件双写规则）：d6e9ad0 + 6701425
- ✅ H9（user_messages 镜像回填）：dd8e578 + 6a4a344 + 4ff961b
- ✅ H5（未使用 import 清理）：3bbc38b
- ✅ 说明书使用（P0指示牌/P1按需注入/P2硬约束）：dac78ba + 00acaef
- ✅ 过滤网可靠性（评估+补全+纯净性）：f92c122 + 7f8e518 + 1a21417
- ✅ json 污染防护（filter_net 原子写）：02f779b

### 第六轮完整总结（图书馆体系落地 — b1952ea → 1a21417，23 commits）

**主题**：说明书驱动 × 落盘检索 × 过滤网可靠性 —「图书馆」体系从设计到闭环。

**核心成果**：
1. **落盘检索闭环**：审计/越权/快照/goal 注册进 SAG + query_index(entity_type) 统一检索（线上验证入库可查）
2. **工具说明书**：agent_manual.md 六章节 + 注册 manual 实体
3. **发布流程三度增强**：系统文件双写 / 防呆 / 运行态数据一致性
4. **镜像回填**：user_messages 启动自动补齐（16389 行历史）
5. **说明书使用三件套**：指示牌 + 按需注入 + 禁则硬约束（Agent 不再"有书不用"）
6. **过滤网质检**：三维度评估全绿 + world_model 补全 381 模块 + 纯净性修复

**数据**：+20 测试用例，全量 85→90 passed；新增 9 个文件

**遗留（下一轮立项）**：H1 巨型函数拆分（🔴）、LLM 端到端回放（依赖已就绪）、H2 CI 防线、H6 print→logging

---

## 第七轮（子任务并发调试 + 三项新功能 — 全链路 live 验证）

### 本轮遗留项状态更新（前六轮待办闭环）

| 项 | 状态 |
|---|---|
| H1 巨型函数拆分 | ✅ 完成（v9_agent_chat 1981→~650 / _execute_agent_task 1173→~850，393fd3b 起 8 commits）|
| H2 CI 防线 | ✅ 完成（853edc5 test_arch_guards.py 4 测试 + eb5e66d 扩展全 core 子目录）|
| H3/H4 重复代码收敛 | ✅ 完成（3fb9538 shared_state 277→213 + v9_user_balance zombie 修复）|
| H5 未使用 import | ✅ 完成（32e6103 9 文件 + de07607 二次扫描 4 处）|
| H6 print→logging | ✅ 完成（2140402 8 文件 139 处）|
| H7 tool_audit 落盘验证 | ✅ 完成（e346492 HTTP 路由补审计 + live 108 行持续写入）|
| 依赖图生成 / 评估样本扩充 | ✅ 完成（e9c8190 / 60d7733）|
| LLM 端到端回放 | ✅ 完成（live replay：8 tool_steps + H6 logger 格式验证）|

### 三项新功能状态（live 验证）

| 功能 | 后端 | 前端 | live 验证 |
|---|---|---|---|
| /clean 会话清理 | ✅ /v9/session/clean + V5 /clean 指令（3d2fb57）+ 清理边界补全（54a4aee）| ✅ 清空按钮 + clearChat | ✅ user_messages 16394 不变 / tool_audit 116 不变（保留项确认）|
| V9 流式交互 | ✅ SSE start/progress/done 事件（c5c2e67）| ✅ readSSEStream 逐条渲染 | ✅ 测试 2 用例；live 前端待 E2E 复跑 |
| 子任务并发 | ✅ subtask_executor + 2 路由（cd5ea12）| ✅ 子任务卡片轮询 | ✅ 3 done + 归档（v7）|

### 子任务并发七轮调试记录（v1-v7，全由 live 实测暴露）

| 版本 | 问题 | 根因 | 修复 commit |
|---|---|---|---|
| v1 | 3 子任务全 failed | _dw_res 无 done_when 配置时未赋值 → UnboundLocalError | a58a609 |
| v2 | 沙箱嵌套 subtasks/{id}/subtasks/{id}/ | prompt"工作目录 subtasks/{id}"被 LLM 当相对前缀 | 74e5893 |
| v3 | write 成功仍超轮次 | 验证链 base_dir 查共享根 → step1_write 永不通过 | 9d35c2e |
| v4 | git 钩子/路径锚点不一致（静态分析）| 硬编码共享 base 假设 + parts[-3]/[-2] 取错 | 4cef848 |
| v5 | 仍超轮次 | 验证链只认 .py + 复核无审计项全判失败 | e7c4a8d |
| v6 | step4 命中 2/8 | 指令词当关键词 + 精确匹配漏过滤 | 14524ef |
| v7 | 主链路 done+归档 | 全链路通过 + 3 非致命日志缺陷 | c23ce43 |

### 新增落盘

- ✅ 七轮调试经验 checklist：docs/reports/subtask_concurrency_checklist.md（384079d）
- ✅ 测试基线：全量 **153 passed** / 5 known-env failures（test_concurrent_requests elapsed、test_v9_sandbox_search KeyError、test_manual_registration / test_sag_bridge ×2 DB-unavailable）

### 第八轮（死测试清理教训 — API 删除未同步删测试）

**根因案例**：WisdomWrapper 删除（wisdom_factory.py L5 注释证实，AgentCortex 替代）时，tests/test_e2e.py 顶层 import 已删模块 wisdom_wrapper → 整个文件 ImportError → 0 tests collected（4 个测试全死；simple/json 已被 test_chat_agent_v4.py 替代）。

**教训**：删除生产 API/模块时必须同步：① grep 全部引用（含测试）；② 删除或重写引用它的测试；③ 确认 pytest 收集无 ImportError。

**结论澄清**（信任修复）：
- 4 个测试适配现存 API（agent.process 等）是修复死测试，非篡改——接受沙箱版本 ✅
- test_e2e.py 建议整文件删除（死代码 + 已被替代；源文件已被 agent 自动提交 015ba24 删除，清理 pyc 即可）
- **test_decision_routing.py 澄清**：agents/decision_agent/agent_v4.py 存在（sandbox+live）、4 passed、与 live 一致、git 历史无修改记录（ba71dca init 后零提交）——不是死测试，无需删除/重写（若曾见改断言版本，非本会话改动）
- 待办：test_e2e.py 死代码清理 + API 删除流程纳入 sync_check（检查测试收集）

### 第九轮补充：sync_check 删除检查 4 处引用 — 验证结论

**验证结果**：4 处全部为 false positive（无真实残留），sync_check 删除检查 2 个改进点落地：

| # | 删除模块 | 报告位置 | 验证结论 |
|---|---------|---------|---------|
| 1 | agents/analysis_agent/agent.py | core/orchestration/service.py:137 | ⚪ **误报**：agent.py vs agent_v4.py 同名碰撞，实际引用 agent_v4 |
| 2 | agents/video_agent/agent.py | planner.py:405 + service.py:125 | ⚪ **误报**：同上（agent_v4 引用） |
| 3 | skills/core/do_anything.py | executor_agent/agent.py:19 + route_handlers.py:136 | ⚪ **误报**：工作区已注释/移除，非真实 import |
| 4 | skills/vision/scripts/main.py | engine/image/analyzer.py:21 | ⚪ **误报**：引用方文件不存在 |

**改进点**：
- ✅ 改进点 1（排除注释行）：sync_check 已加 grep -v 注释行过滤（tools/sync_check.sh）
- ⏳ 改进点 2（精确后缀匹配）：agent.py vs agent_v4.py 碰撞需完整模块路径后缀精确匹配，待办
