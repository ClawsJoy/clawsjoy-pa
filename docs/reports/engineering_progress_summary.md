# ClawsJoy 工程化进度总结

> 生成时间: 2026-08-16 06:01
> Git 基线: master @ `54a4aee`（/clean 清理边界补全）
> 测试基线: 全量 149 passed / 5 known-env failures（test_concurrent_requests elapsed、test_v9_sandbox_search KeyError、test_manual_registration / test_sag_bridge ×2 DB-unavailable 顺序污染）
> 工作区: 干净（运行态数据已 gitignore）

---

## 主线一：架构与技术债清理（H1-H7 全落地）

code_health_check 5 项建议 + gap 报告 G1-G7 全部完成：

| 项 | 成果 | Commit |
|---|---|---|
| H1 巨型函数拆分 | v9_agent_chat 1981→~650 行、_execute_agent_task 1173→~850 行；发现并修复 12 个被 except 吞掉的静默 bug | 393fd3b 起 8 个提交 |
| H2 架构防线 | test_arch_guards.py 4 测试（循环依赖 + 漏变量回归），抓到 import re / _file_retry_state 2 个真实 bug | 853edc5 |
| H3/H4 重复代码收敛 | shared_state 277→213 行（合并双份 import/函数）；修复 3 个 zombie（v9_user_balance 必 500、user_info_api NameError、get_keywords_from_sag 死代码） | 3fb9538 |
| code_health #3 未使用 import | 9 文件 AST 实证清理（保留外部 re-export 消费者） | 32e6103 |
| H6 print→logging | 8 文件 139 处迁移（保留 [V9]/[AUDIT] 标签），logger 整理 + chat_stream 重复 import 清理 | 2140402 |
| H6 后续二次扫描 | execute_agent_task/context_manager/tool_router/agent_gateway 4 处死导入（双验证） | de07607 |
| H7 HTTP 审计补全 | _with_http_tool_flow 补 audit_tool_call（此前 /v9/sandbox/* 零审计）+ 回归测试 | e346492 |
| P2 依赖图生成 | tools/backfill_dependency_graph.py（430 文件 AST 扫描，双写 core/lib + 沙箱 data/，426 条）| e9c8190 |
| P2 评估样本扩充 | 正样本 10→48 + 负样本 12（filter_reliability） | 60d7733 |

## 主线二：Manus 看齐三任务（排查 → 实现 → 验证）

### 排查（只读，three_issues_investigation.md）
确认三项现状：会话清理完全缺失（无按钮/无后端路由）、V9 非流式（等完整 JSON）、子任务零并发（#31 串行队列）。
Commit: `4130f97`

### 任务1：V8 频道会话清理
- 后端 POST /v9/session/clean（清 pending/plan/goal/快照 messages）
- 前端 V8 频道"🗑 清空对话"按钮 + clearChat()
- 测试 2 用例 → 全量 127 passed
Commit: `780f707`

### 任务2：V9 工作区流式交互
- 后端 _v9_bridge_loop 加 on_round 回调 + v9_agent_chat stream 分支（子线程 + queue SSE：start/progress/done 事件）
- 前端 agentSend 双模解析（SSE readSSEStream + JSON fallback），progress 逐条渲染 tool_steps 卡片 + 进度条
- 测试 2 用例（SSE 事件流 + 非流式 fallback）→ 全量 129 passed
Commit: `c5c2e67`

### 任务3：子任务并发（参照 V10 run.py）
- 新模块 core/gateway/subtask_executor.py：ThreadPoolExecutor(3) 有界并发 + 独立沙箱 + git 基线 + 审计归档/失败保留现场 + per-session 状态加锁
- _execute_sandbox_tool / _execute_agent_task 加 sandbox_base 可选参数（独立目录透传）
- 路由 /v9/subtask/create + /v9/subtask/status；前端子任务卡片（2s 轮询，⏳🔄✅❌ 状态）
- 测试 3 用例（成功归档/失败保留现场/路由）→ 全量 132 passed
Commit: `cd5ea12`

**七轮 live 调试链**（每轮实测暴露一层问题，全链路 v7 闭环）:

| 版本 | 问题 | 修复 commit |
|---|---|---|
| v1 | _dw_res UnboundLocalError（无 done_when 配置未赋值）| a58a609 |
| v2 | prompt 路径误导 → 嵌套沙箱目录 | 74e5893 |
| v3 | 验证链 base_dir 查共享根 → step1 永不通过 → 死循环 | 9d35c2e |
| v4 | git 钩子/路径锚点硬编码共享假设（静态分析）| 4cef848 |
| v5 | 验证链 .py 限制 + 复核无审计项 → 死循环 | e7c4a8d |
| v6 | step4 指令词当关键词 → 命中不足 | 14524ef |
| v7 | 全链路 done + 归档（3 子任务）+ 3 非致命日志缺陷 | c23ce43 |

经验固化: docs/reports/subtask_concurrency_checklist.md（384079d）

## 主线三：安全修复与防线加固

| 项 | 成果 | Commit |
|---|---|---|
| pattern 16 豁免扩展 | 2>/dev/null 后跟分号/管道/&& 误拦修复（豁免字符集 [\s;&|<>]）| eb5e66d |
| pattern 16 重定向符号 | (?:>|>>) → (?:[12]?>>?|&>)，覆盖 2>/1>/&> 形态；定向验证 13/13 | 45e3d5c |
| 全 core 反向依赖防线 | test_core_all_dirs_no_top_level_import_to_main（顶层禁 import agent_gateway，函数内允许）| eb5e66d |
| 运行态数据 gitignore | .agent_state/billing/chroma/skill_registry git rm --cached，根治 live agent 自动提交污染（2 次 rebase 清除）| ed3f4c8 |
| 前端 G1-G3 渲染修复 | renderProgressBar/PlanConfirmCard/AskCard 引用不存在的 term 元素（浏览器 E2E 实证 null appendChild）→ agentTerminal 兼容 | 85d718c |

## 主线四：/clean 指令链 + 验证治理

### /clean 完整链
| 步 | 成果 | Commit |
|---|---|---|
| 1 | 排查：/clean 被 V5 当普通消息（v5_execute L47 日志实证）| 3d2fb57 前 |
| 2 | 修复：方案 A（V5 入口拦截）+ 方案 B（前端 send() 检测）；抽出 _clean_session_context 公共函数；arch guard 文本检查→AST 修正 | 3d2fb57 |
| 3 | 边界排查：8 项应补清 / 3 项应保留清单 | d8e3ec7 |
| 4 | 补全：pending_writes 持久化字段 + 缓存前缀匹配 + 计数 + subtask done/failed | 54a4aee |

### 验证
- live LLM replay：8 tool_steps 桥接循环正常、H6 logger 格式正确（core.gateway.* - INFO）、审计 jsonl 持续写入（116+ 行）
- 浏览器 E2E（playwright）：tool_steps 渲染（✅/❌/⚠️ + 参数 + 错误）、Anchor B 拦截 + 拉回沙箱、find 2>/dev/null 放行
- H8 复核判定：假完成拒绝 / 真实通过 / 超窗拒绝（3 场景全对）
- /clean live 验证：user_messages 16394 不变、tool_audit 116 不变（保留项确认）

## 遗留项（优先级 + 工作量）

| # | 项 | 优先级 | 预计工作量 | 说明 |
|---|---|---|---|---|
| 1 | 同步后浏览器 E2E 复跑（任务2/3 前端 live 生效验证）| P1 | 1h | V9 流式逐条渲染 + 子任务卡片 + /clean 按钮全链路 |
| 2 | test_v9_stream 慢（40s+）| P2 | 0.5h | 流式测试 test client 读取耗时，可优化 heartbeat 等待/断言方式 |
| 3 | sandbox engine/ 目录残缺 | P2 | 环境修复 | sandbox 无法完整启动 gateway（engine.audit 缺失），live E2E 依赖 live 实例 |
| 4 | agent_gateway 20 处函数内延迟导入 | P3 | 评估已完成（保留）| 均为刻意架构决策（启动速度 + 循环规避），唯一反向依赖 engine_manager L84 函数内安全 |
| 5 | "彻底清理"选项（clean_all=true）| P3 | 1h | 可选：清 user_messages/tool_audit 该 session 行，需前端确认弹窗"不可恢复" |
| 6 | 子任务 LLM 并发限流 | P3 | 2h | v3-v6 实测多次 API 网络错误（Errno 101），3 并发加剧——加信号量限流（如 max 2）或指数退避重试 |

## 下一轮建议开工顺序

1. **P0 同步 + 重启**（用户手动）→ 运行 sync_check.sh 确认清零
2. **P1 同步后浏览器 E2E 复跑**：V9 流式 tool_steps 逐条渲染、子任务池卡片、/clean 按钮、G1-G3 进度条
3. **P2 流式测试提速**：test_v9_stream 从 40s 降到 <10s
4. **P2 子任务 live 实测**：发真实子任务验证独立沙箱 + git 基线 + 归档路径
5. **P3 可选**：clean_all 彻底清理选项
