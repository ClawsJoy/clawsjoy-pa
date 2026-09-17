---
type: audit
tags: [V9, 架构, 复杂度, 收敛, 审计]
created: 2026-09-05
status: 审计-待决策(不修复)
---

# V9 架构复杂度审计 — 停止补丁，系统性收敛

> 范围: 8-09 月 R1-R15 + L0-L5 + P/G/W/Q 系列共 20+ 轮修复的相互关系; 目标: 复杂度地图/冲突清单/冗余识别/真实任务回归门禁设计。本文档只审计不修复。

## 0. 量化基线(实测)

| 指标 | 值 |
|---|---|
| agent_gateway_enhanced.py | 6,580 行(单体路由+桥接+目标+审批+恢复全在一文件) |
| 单文件日期化补丁注释 | 08-注释 37 + 09-注释 20 = 57 处 |
| 守卫类(registry) | 12 个 Guard(Quota/Mode/Forced/Forbidden/Escape/Approval/Plan/Recursion/Reminder/Audit/FailurePause/WebFetch) |
| core/tools 模块 | 17 个(7 个为 09 新增 CU/效率体系) |
| 工具分发路径 | ≥3 套:_TOOL_HANDLERS + _TOOL_REGISTRY(plugin) + tool_router 手写 if/elif 老分支 |
| 测试 | 846 unit(大量为源码字符串断言, 无全链路 E2E) |

## 1. 复杂度地图(修复层与依赖)

### A. 写保护/审批链
- Phase1 heredoc 禁写(_SYS_ESCAPE) → EscapeGuard → R14 bash data/tmp 豁免(同一豁免面)
- R3 write_file reason+批量审批 → ApprovalGuard/PlanGuard(write_pending/plan_pending) → L5 空参拦截(新旁路)
- R6/R7 workspace guard 修复 → 读路径白名单/越权(registry)

### B. token/预算链
- R1 token 水位(max_bridge_rounds 护栏+水位) → P0/P1 空回复与 None 兜底 → P2a/b 事件溯源双写 → R12 超时 320s → 400KB 硬截断+_tg_estimate → L5 80% 预警 → R15.1 长文截断清洗
- L1 reasoning 剥离 → Q2 修正(thinking 工具轮必需段保留)——补丁链典型

### C. 上下文/记忆链(叠加最重)
- R2 读缓存 + R2-exec 读命令去重 → R5 任务隔离(last_task_only 投影) → 事件溯源 derive_messages(唯一入口)
- L0 recon-digest → L2 历史轮摘要 → L3 步骤断点 —— 三者同注入点做几乎同一件事
- L4 同参缓存(_L4_TOOL_CACHE) → 与 R2 缓存并存
- Q1 vault 引导 → R11 obsidian schema 只读声明

### D. 完成判定链(假完成防御叠加)
- P0 empty fallback → P1 empty_reply 标记 → R13 过渡语不 complete → R15 系统回声不 complete → R15.1 内容清洗/证据门禁 → cu_learning complete 证据 gate → L0 空回复摘要重试
- goal_state: complete_goal 幂等 + total 语义(240=48×5) + 多轮 continue/steer + goal_id 复用——状态机分散 bridge/_write_turn_end/goal_state/前端

### E. 工具能力面(CU 体系)
- P1-P5: a11y_dom → browser_hybrid(impl+plugin) → semantic_select(/api/chat) → cu_learning → 遥测/SOP
- 每新工具需 5 处接线: gateway_helpers schema + _TOOL_HANDLERS + plugin 文件 + tool_router import/registry/priority + shim 精确集合测试

## 2. 冲突清单

| # | 冲突 | 状态 |
|---|---|---|
| 1 | L1 只留最近 reasoning vs thinking 工具轮必需段(末位最终分析存在时误剥 → 400) | 已修(Q2: 保最近+全部 tool_calls 段) |
| 2 | R5 投影隔离 vs 多轮续跑记忆(事件投影 与 注入摘要 两套记忆语义并存) | 待收敛 |
| 3 | L0 recon-digest / L2 轮摘要 / L3 步骤断点 同点叠加注入 | 建议合并 |
| 4 | R2 读缓存 vs L4 同参缓存(两个 session 缓存) | 建议合并 |
| 5 | ApprovalGuard 空 path 报错 vs L5 空参前置拦截 | 建议单点 |
| 6 | R13/R15/R15.1/cu-evidence 四层假完成防御分散 | 建议完成判定单点化 |
| 7 | 工具分发 ≥3 路径(plugin vs elif vs _TOOL_HANDLERS) | 建议 plugin 单轨 |
| 8 | token 预算多实现(usage/_tg_estimate/400KB/R1水位/L5 80%) | 建议预算服务 |

## 3. 冗余识别

可合并(行为不变): 记忆三兄弟→round_checkpoint 单一服务; R2+L4→统一 read-cache 层; 空参→唯一 pre-validation; 完成判定→goal_state.complete 唯一入口。

可砍: R13 过渡语特殊分支(R15+cu-evidence 覆盖); 400KB 硬截断并入预算服务(保留为护栏); 观察类守卫并入统一审计钩子。

保留(短期不动): 写保护链、R5 事件溯源、goal 持久化、CU 工具面、_truncate 策略、SSRF/Escape。

## 4. 为什么 846 绿但真实任务失败(门禁缺失)

| 缺口 | 证据 |
|---|---|
| 无全链路黄金测试 | unit 多为源码断言+小单测, 不跑 网关→消息装配→守卫→工具→事件→完成判定 整链 |
| 无模型行为仿真 | 空回复/路径混乱只在真实多轮+长上下文出现 |
| 无 canary 任务集 | 改动只跑 unit; 封面生成等真实任务需 live 重启人工触发才发现 |
| 无预算/序列基线 | 无同任务 tokens/工具序列基准, 516K 类回归肉眼才发现 |

## 5. 真实任务回归套件设计(canary)

L0 进程内集成(每次改动必跑, 秒级): mock adapter 脚本化响应(含空回复/过渡语/系统回声/参数错误)驱动 _v9_bridge_loop; corpus 5 类 golden 任务(写 Obsidian 报告/浏览器 POC/本地小重构/封面生成/知识检索); 断言: reason 非 need_more(除非注入)、无重复侦察、预算阈值内、关键产物存在、无 data/vault、completion 无证据不 complete。

L1 live canary(发布后自动): 同 corpus 真跑, 记录 {tokens, reason, 工具序列 hash, 产物 md5} 与基线 diff; 写 data/computer_use/canary/{date}.json。

门禁: sandbox 全绿(unit+L0 canary)才允许出同步清单; live canary 绿才算发布成功。

## 6. 收敛路线(下一步再定实施)

| 阶段 | 内容 |
|---|---|
| S1 | 建 canary 套件(L0 进程内)给当前行为打基线(先测后改) |
| S2 | 记忆三兄弟 → round_checkpoint 单一服务 |
| S3 | 缓存合并 R2+L4; 空参 pre-validation 单点 |
| S4 | 工具分发 plugin 单轨(老 elif 迁 handler, 行为测试锁) |
| S5 | goal 完成判定单点化 + 预算服务 |

每阶段: unit+canary 全绿 → 单独同步/重启 → live canary 对比。禁止阶段内加新旁路补丁。
