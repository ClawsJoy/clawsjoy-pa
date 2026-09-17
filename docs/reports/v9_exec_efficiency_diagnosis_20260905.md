---
type: diagnosis
tags: [V9, 效率, token, 上下文, 诊断]
created: 2026-09-05
---

# V9 执行效率诊断与根治方案（以 POC 516K 失控轮为样本）

> 样本: session_1783388196051 事件段 22800-22958（POC 任务 3 轮 / 23 次模型调用 / 37 工具调用 / 单任务累计 516,637 tokens ≥ 预算 500K 被截断）。

## 1. 量化：tokens 去哪了

| 环节 | 数据 | 占比估计 |
|---|---|---|
| 每调用上下文重发 | 516K / 23 调用 ≈ 22.4K/调用（输入+输出）；末轮 11 调用 ≈ 350K ≈ 31.8K/调用 | 主因 ~85% |
| 历史 reasoning(thinking) 回传 | 23 段共 88,711 字符 ≈ 26.6K tokens；每后序调用重发累积推理 | 输入侧放大 ~15-35%（随轮增长） |
| assistant 正文 | 全段累计仅 3.3K 字符 ≈ 1K tokens | <1% |
| 工具输出 | 全段 tool_result 仅 ~10KB ≈ 3K tokens（单条上限 2KB 已生效） | ~1-3% |
| 冗余/重复调用 | 跨轮同参重复 2；但「计划确认后整轮重侦察」×2 ≈ 14 步骤/次；空参 write_file ×2、语法回滚重写 ×4-6 | 次数侧 ~40% 浪费 |

结论：瓶颈是**把全量历史（含每段思考、每段助手正文、每轮注入）在每个工具调用都整包重发给模型**，且**调用次数被确认后重跑/失败重写放大**。工具输出本身不是大头。

## 2. 四个问题的代码级回答

1) 为什么每轮 18K+ 且增长：每次 adapter 调用发送 messages 全量列表（agent_gateway_enhanced.py 循环内 messages.append 后原样传参）。增长源 = (a) 每个 assistant 都带 reasoning_content 入库并入参（3545/3559 行），DeepSeek 只接受最近一段 thinking（5239-5245 注释明示，快照恢复时已剥离旧段——但常规循环未剥）；(b) 工具参数（模型自产的 JSON）计入下一轮输入；(c) 环境快照/目标/计划注入每轮重发；(d) 工具结果。不应重发：旧轮 reasoning、旧最终总结全文、>500 字符旧工具输出、已执行步骤细节（有 digest 清单可按需 read）。
2) derive_messages 全量投影：实现确为每次全扫事件重建（session_log.py derive_messages），last_task_only 已按真实 user 截断（R5）。CPU 非瓶颈；token 瓶颈在「投影结果每调用整包发送」。增量解法＝轮检查点：turn_end 折叠为 digest，下轮 messages = [checkpoint digest + 本调用增量]，事件层只取 last_seq 后增量。
3) 计划确认后为何重跑：确认路由（2228/5279）启动新执行，messages 从事件重投影（blocked 轮工具在事件层但未形成『已完成步骤』记忆），agent 又做整轮侦察。系统性解法＝步骤级断点记忆（plans/{task}：plan_steps + executed[{step, 工具, 结果摘要, 验证点}]），执行轮注入『已完成/待做』清单；已上线的 recon digest 是第一层。
4) 工具输出哪些可摘要/丢弃：现单条 2KB 截断已小。分类策略：read_file/execute 结果 >500 字符 → 落 data/computer_use/steps/{turn}.out，回传『摘要+path』；list/search → 计数+前 N；json/curl → 抽关键字段；浏览器/obsidian → 摘要。旧轮大结果随 checkpoint 折叠出上下文。

## 3. 系统性根治方案（分层，非补丁）

L0 已上线补丁（保留）：空回复摘要重试、继续复用 goal、新任务隔离、确认/续跑注入已执行工具 digest。

L1 推理剥离（收益最大、改动小）：发送前仅保留**最近一条** assistant 的 reasoning_content（DeepSeek 400 约束），其余剥离（仍入事件层/审计可查）。预期省输入 15-35%。

L2 轮检查点压缩（结构性）：每 turn_end 把该轮消息折叠为 compact digest（目标 + 步骤工具清单 + 各自 ≤120 字摘要 + 验证点），写入事件 checkpoint；下一轮 messages = [该 digest 作 system] + 当前 user + 增量（新工具结果仅保留最近 ≤6 条原文）。事件层全量保留供审计/复盘。

L3 步骤级断点记忆（消灭确认后重跑）：plans/{task_id}.json（复用 P4 cu_learning 同构）存 plan_steps + executed；blocked/ask/继续 后恢复注入『已完成 N/M：…；待做…』；执行与 CU-SOP 生成同源。

L4 工具输出策略（支撑 L2）：统一 _tool_result 后处理——长结果摘要化+落盘 path；list/search 计数化；重复同参调用在同一 check 内自动去重（返回缓存命中标记）。

L5 调用次数治理：write_file 空参在路由层拦截不计轮；语法自检前置（agent_system 已引导 py_compile 自查）；预算早期预警显示『预计还需 N 调用/成本』。

## 4. 预期消耗对比（POC 级任务算例）

| | 当前 | 优化后(估) | 说明 |
|---|---|---|---|
| 调用次数 | 23 | ~8-10 | 去重+确认不重跑+语法自检 |
| 平均输入/调用 | ~20K(末轮 31K) | ~5-7K | L1+L2：base digest ~2K + 最近 3-6 结果 ~3-5K |
| 单任务总 tokens | 516K | 60-90K | ≈ 6-8× 下降 |

假设：中文 1 token≈0.3 字符×；结果含敏感性。若再上 L4 去重与 L3 记忆，POC 级可再压到 ~40-60K。

## 5. 落地顺序与验收

1. L1（半天）：改一处发送前清洗 + 单测（旧 reasoning 剥离、最近一条保留）。验收：同任务 tokens 下降 ≥15%。
2. L2（1-2 天）：轮 checkpoint 数据结构 + 投影增量 + 单测 + 真实重放对比。验收：末轮输入不再超 10K，单任务总降 ≥40%。
3. L3（1 天）：plans executed 记忆接入确认/继续路径（取代 recon digest 的粗粒度）。验收：确认后不再重跑已执行步骤。
4. L4（1 天）：结果后处理管线 + 同参去重。验收：长输出摘要化、去重命中率记录。
5. L5（0.5 天）：空参拦截/预算预警。验收：POC 任务 <100K 完成。

每步均带 regress 全绿 + live 同步清单（agent_gateway_enhanced.py / session_log.py / 相关）。

## 附：证据文件
- 事件段: data/session_logs/session_1783388196051.jsonl 22800-22958
- POC goal: goals/.../goal_web_1783219071801_*.json (tokens 516637)
- 本文档 sandbox: docs/reports/v9_exec_efficiency_diagnosis_20260905.md
