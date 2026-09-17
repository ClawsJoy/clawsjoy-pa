# 四天分析完整过程

> 日期：2026-08-14 ~ 2026-08-17 | 主题：V9 可靠性工程 + Harness 架构借鉴 + 插件化改造推演
> 本文是四天"分析 → 设计 → 实施 → 验证"完整过程的顺序记录,含每步的输入证据、决策、结果与教训。

---

## Day 1（08-14）：V9 可靠性基础 + 双执行路径解剖

### 目标
对照 Harness 补齐 V9 执行框架的可靠性基座：结构化错误、失败审计、回调契约。

### 过程
1. **解剖 `_execute_agent_task`(1551 行)与 `_v9_bridge_loop`**:确认两条执行路径——`_execute_agent_task`(async 线程执行器,工具循环经 `_execute_sandbox_tool` + `sandbox_base` 覆盖)vs bridge_loop(`for _bridge_round in range(8)` + `on_round` SSE 回调)
2. **锚点定位**:锚点A(写审批 `_pending_writes`/`write_pending`)只存在于 bridge_loop;`_execute_agent_task`/`tool_router`/`write_file` 无审批逻辑 → 子任务写天然免审批(架构隔离,显式声明)
3. **锚点B 审计**:`_detect_sys_escape`/`_SYS_ESCAPE_PATTERNS` 模式 16 覆盖 `>/>>/1>/2>/&>/2>>`,豁免 `/dev/null|stdout|stderr`
4. **P1 结构化错误落地**:`_struct_error(code,message,detail)` + `_classify_exception` → NETWORK/LLM_API/TOOL_ARGS/UNKNOWN;LLM 失败透传 `[LLM_API]`,外层 except → `[CODE] msg` + preserve_error_context(commit `32d901e`)

### 关键决策
- V9 采用 Manus 模式(process 可视化/tool_steps)+ Harness 模式(锚点/安全/审计);后端执行工具,前端只展示
- 子任务审批固定 never(Harness 移植);delegation depth maxDepth=3;O1 防重复(bridge_exhausted + 前端 skip)

### 结果
- P1 提交后全量 174 passed
- 教训:结构化错误是"让失败可决策"的第一步,纯文本错误让上层无法按 code 重试/终止

---

## Day 2（08-15）：P1 收尾 + P2 失败记录 + 提醒机制

### 目标
完成 P1 剩余、落地 P2(失败进 SAG 审计表)、引入 repeat-tool-reminder。

### 过程
1. **repeat-tool-reminder 模块**(借鉴 Harness):`THRESHOLDS=[3,5,8]`、`canonicalize(arguments)`(sort_keys 深排序)、`observe/reset/configure`(include/exclude 通配符)、**永不否决**(只注入 system 提醒)
2. **集成 `_execute_agent_task`**:任务开始 `reset(sub_task_id or task_id)`;工具循环内 `_loop_detect`(固定 5 次)整体替换为 `observe(...)` + system 消息(commit `b5e7bbd`)
3. **P2 工具失败分类**:工具执行失败 → `[TOOL_EXEC] 前缀 + 工具名 + _struct_error(TOOL_EXEC, ..., {tool, error})` 进 error_context(commit `359ec46`)
4. **P2 agent_actions 失败记录**:新增 `_record_failure_action(code, message, detail_note)`——`tool_name="failed"`、`result={"code","message"}` JSON、`file_type="task_failure"`、内部 try/except 降级;三条失败路径调用(工具失败 TOOL_EXEC / API 失败 LLM_API / 外层兜底 `_classify_exception` 结果)
5. **P3 结构化回调**:`_notify_fail_impl` 注解判定兼容(`inspect.signature` 检查回调最后一个参数)——dict 注解收结构化,无注解/str 降级 `_notify_fail_to_text` → `[CODE] message`;5 处调用点全结构化(LLM_API/TOOL_ARGS/TOOL_EXEC/TIMEOUT/外层);`on_v9_fail` 加 `reason: dict` 注解 + 按 code 决策(NETWORK 重试/TIMEOUT 终止);kwargs 改直接传绑定方法(修 lambda 无注解陷阱)(commit `1f662c0`)

### 关键发现
- `task_orchestrator` 传入的是 `lambda _t,_u,_s,_r: self.on_v9_fail(...)`——lambda 无注解,注解判定看不到 → 必须改传绑定方法
- 测试隔离:on_v9_fail 测试需 stub `code_entity_extractor` 模块(import task_orchestrator 链式实例化 extractor 连 DB)

### 结果
- P3 测试 11 passed;全量 256 passed(245 + 新增 11)

---

## Day 3（08-16）：工作区漂移审查与处置

### 目标
审查 22 个漂移文件(21 已修改 + 4 未跟踪),判定保留/还原/删除,不执行先报告。

### 过程
1. **逐个 diff 审查**(文件清单与结论见下方表格)
2. **实测关键疑点**:
   - `pytest.ini` 单行 `--ignore=test_engine_interface.py` 覆盖整份配置 → 还原 HEAD 后 `--collect-only` 确认 collection error(engine.audit 缺失,纯 sandbox 环境问题)→ **覆盖非恶意**
   - `filter_net.json` used_count 84→767 + 新增 6 pattern → **正常自学习累计**(total_queries 6→0 疑点待查)
   - `smart_intent_router.py` 顶层 `from engine.semantic import semantic_engine` → **import 即崩**(engine.semantic 在 sandbox 和 live 均不存在)→ 最危险项
   - `route_handlers.py` 注释掉 do_anything 后残留 3 行 4 空格缩进代码 → 被 Python 吸入 `execute_skill` 函数尾(AST 证实 110-141),语法合法但引用未定义 `skill` → 死代码
   - `executor_agent/agent.py` return 后死代码(audit 引用未定义 `result`)→ 修复

### 处置执行(用户确认后)
| 处置 | 文件 |
|---|---|
| 还原 | pytest.ini(改 conftest 条件式 collect_ignore)、smart_intent_router.py、business_agent 裸 except ×2 |
| 修复 | executor_agent(重写 _execute_business 消除死代码)、route_handlers(删残留 3 行) |
| 保留 | filter_net.json、agent_intent_router、planner/service 的 agent_v4 迁移、calculator/analysis v4 重构、tests 适配组、sync_check.sh |
| 修复文档 | ISSUES.md(恢复第八轮内容 + 第九轮更新为 false positive 结论) |
| 删除 | _tmp_live_check.sh、_tmp_subtest5.sh、_tmp_*.bak |
| 提交 | FINAL_SUMMARY.md、test_long_loop.py(5 passed) |

### 提交
- `4b0537c`(FINAL_SUMMARY + test_long_loop)
- `5d81bd1`(漂移处置主体,19 文件)
- 验证:全量 245 passed 零回归

### 教训
- **"测试篡改"教训回顾**:4 个测试适配现存 API 是修复死测试非篡改(用户接受)
- 第九轮 4 处僵尸引用全部 false positive(agent.py vs agent_v4.py basename 碰撞/注释行/引用方不存在)——sync_check 改进点 1(排除注释行)落地,改进点 2(精确后缀匹配)待办

---

## Day 4（08-17）：Harness 自我认知 + V9 评估 + 插件化推演

### 目标
1. 基于 Harness 源码回答自我认知四问(元架构/核心优势/能力边界/移植三件事)
2. 评估 V9 执行能力(已具备/缺失/架构缺陷)
3. 设计 V9 插件化改造方案(借鉴 Cordis)+ V9Context → OSContext 调整方向

### 过程
1. **Harness 源码通读**:vendor Cordis 底座、packages/core(spine: session/system-prompt/tools/agent/agent-loop)、sandbox(sandbox/policy/local/bash-sandbox)、guard(repeat-tool-reminder/timeout-policy)、subagent(深度/委托策略)、goal/goal-round-driver、workflow/tool-workflow/tool-ralph、interaction(user-approval/ask-user)、code-runtime(worker 敌对方假设)、hooks、ACP、context、llm(adapter/retry)、compaction、docs/architecture.md、AGENTS.md
2. **关键代码实证**:`agent.ts`(turn/step 生命周期 + inbox + request-error 恢复)、`tool-calls.ts`(并行池 + 模型序提交)、`runtime-context.ts`(持久快照投影)、`system-prompt/index.ts`(分段注册 + toolOrder)、`tools/src/index.ts`(restrict 可见性组合)
3. **V9 三文件实证**:`execute_agent_task.py`(1551 行单函数)、`subtask_executor.py`(并发池+深度+归档)、`tool_router.py`(ToolPlugin + _ToolContext + _with_tool_flow);量化:extractor 23 文件散落 import、_execute_sandbox_tool 11 调用点、shared_state 12 消费方
4. **产出 4 份报告**(本文档同目录):
   - `harness_self_cognition.md` — 三根柱子(事件溯源/插件化接缝/结构化失败)
   - `v9_pluginization_plan.md` — V9 评估 + P0/P1/P2 三期方案
   - `oscontext_evolution.md` — V9Context → OSContext 调整方向
   - `four_day_analysis_log.md` — 本文

### 核心洞察
- Harness 的可靠性 = 可重建(事件日志)+ 可替换(插件接缝)+ 失败有 code(结构化错误)+ 守卫不可逆(单调 guard)
- V9 已具备:工具插件接口/ctx 注入/结构化错误/重复提醒/失败审计/子任务深度/沙箱锚定/验证链
- V9 缺失:事件溯源会话日志/工具流水线事件/作用域注册/插件生命周期/协作取消/运行时上下文投影/code-runtime/并行池
- V9 架构缺陷:双执行路径分叉(审批只在 bridge_loop)/970 行单函数/全局可变状态(30+ dict + messages 单例)/单例蔓延(extractor 23 文件)/守卫不可组合/工具结果非结构化

### 分期结论
- **P0(1-2 周)**:V9Context 容器(服务注册/作用域/事件/插件),零行为变化
- **P1(2-3 周)**:守卫插件化(10+ 散落 if → tools/pre-execute 监听器)+ 双路径共享 guard 框架(审批差异作用域化),风险最高
- **P2(3-4 周)**:作用域隔离(shared_state → per-session scope)+ 会话事件日志(可重建),工作量最大
- **P3(未来)**:多版本网关收敛到 OSContext

---

## 附录:四天数据汇总

| 指标 | 数值 |
|---|---|
| 新增测试 | P1 5 + P2 4 + P3 11 + reminder 7 + long_loop 5 = 32 |
| 提交数 | 8(32d901e / b5e7bbd / 359ec46 / 1f662c0 / 4b0537c / 5d81bd1 / +2 漂移前置) |
| 全量回归 | 256 passed(Day 2 末)/ 245 passed(Day 3 漂移后零回归)/ 250 collected |
| 审查文件 | 22 漂移(21 M + 4 ?? = 25 项,含遗留 .bak) |
| 报告产出 | 4 份(本目录) + ISSUES 更新 |

## 待办(遗留)

- [ ] filter_net.json `total_queries` 6→0 归零原因确认
- [ ] sync_check 改进点 2(agent.py vs agent_v4.py 精确后缀匹配)
- [ ] test_e2e.py 死代码清理
- [ ] P0 实施(需用户确认进入改造期)
- [ ] live 同步 + E2E(api-client.js/subtask_executor/execute_agent_task/agent_gateway_enhanced/repeat_tool_reminder/tests)
