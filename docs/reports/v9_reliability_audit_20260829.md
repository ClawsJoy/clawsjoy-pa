# V9 系统可靠性全面检查报告 + compaction 移植方案

**日期**: 2026-08-29 | **状态**: 已查实（未改代码）

---

## A. 已修项验证（全部确认生效）

| # | 项目 | 状态 | 证据 |
|---|---|---|---|
| 1 | DeepSeek 读超时 180s | ✅ | adapter L45/78/112 timeout=180 |
| 2 | 402 降级 7B(原生tools/干净流/结果注入) | ✅ | 14 处引用(_7b_last_result/7B_FAIL/连续失败3次停) |
| 3 | derive 过滤未知工具脏数据 | ✅ | session_log.py L174-175 过滤 |
| 4 | 审批 pending 清除(确认后彻底) | ✅ | 17 处 pop/write_confirmed/幂等 |
| 5 | 递归 action 维度计数 | ✅ | path_utils.py L44-50 browser_local:action |
| 6 | finalize 唯一出口 + reasoning_content 保留 | ✅ | message_assembler L344 |
| 7 | 工具结果截断 | ✅ | L2534 limit=2000 头尾各半+TRUNCATED |
| 8 | 正本vs副本同步 | ✅ | 4 关键文件 md5 一致 |
| 10 | 审批 pending TTL | ✅ | L42 _PENDING_TTL=60s + _pending_cleanup |
| 11 | 重试退避 | ✅ | llm_client Retry(total=3, backoff=2.0) + 线性退避 |

---

## B. 待修项 / 有隐患（按风险）

| # | 项目 | 风险 | 说明 |
|---|---|---|---|
| 9 | 会话消息并发 append 竞态 | P1 | 并行工具(ThreadPool)append 无锁; _pending_lock 只保护审批, 不保护 messages |
| 13 | 压缩与新消息并发冲突 | P1 | _compress_messages 无并发保护; 压缩期间新消息可能丢失/错位 |
| 12 | token 消耗日志 | P2 | 已有 COST_LOG(费用保护), 但 V9 无实时 usage 明细(仅记账) |

---

## C. 运行状态

| 项 | 状态 |
|---|---|
| 网关 | ✅ PID 2807(10:12) 含今天费用保护代码(6处 COST_GUARD) |
| 健康 | ✅ /health 正常 |
| DeepSeek 余额 | ✅ 289.27 元 |
| 测试基线 | ✅ 594 passed(费用保护修复后) |
| 7B 降级修复 | ✅ 原生tools+结果注入+失败3次停(14处) |
| derive 脏数据 | ⚠️ 历史会话有未知工具残留(旧数据), 新会话已过滤 |

---

## D. compaction 移植方案（V9 借鉴 Harness thresholdRatio=0.8）

### D.1 现状对比
| 维度 | V9 | Harness |
|---|---|---|
| 触发 | keep=N 固定(6/4/8), 硬编码阈值 0.8/0.9 | thresholdRatio=0.8 自动 |
| 预算基准 | _calc_token_budget(model, tools) 已有 | token-meter 压力投影 |
| 保留策略 | 最近 keep 条 + 前2 system + 尾部4条 | retention 配置化 |
| 摘要 | 单条巨型消息截断 50KB | 结构化压缩 |

### D.2 移植方案（不改代码, 设计）

**触发点**（bridge_loop 每轮 adapter 调用前, 复用 L3564 TOKEN_GUARD 处）:
```
① bridge_loop 每轮开头: est = _tg_estimate(messages, tools)
② budget = _calc_token_budget(model, tools)
③ if est > budget * thresholdRatio(0.8):  # 新增自动阈值
     keep = max(int(预算目标/平均每条约token), 4)  # 动态 keep(替代固定6/4/8)
     messages = _compress_messages(messages, user_id, session_id, keep=keep)
     messages = _finalize_messages(messages)  # 唯一出口, 保 reasoning_content
```

**保留策略**（对齐 Harness retention）:
- 保留: 前 2 条 system(任务目标) + 最近 keep 条 + 工具链依赖(tool_call/tool_result 配对)
- 摘要: 中间轮次 → 单条 system 摘要(带 [上下文摘要] 标记)
- 巨型消息: >50KB 截断(现有 _layered_compress 已做)

**与 derive_messages/finalize 衔接**:
- 压缩后必须过 _finalize_messages(唯一出口, 已有 reasoning_content 保留修复)
- derive_messages 每轮重建 → 压缩写入 .agent_state.json 前过 finalize

**风险**（防重蹈 reasoning_content 丢失/截断）:
- ⚠️ 压缩后的 system 摘要消息: 不能含 assistant.reasoning_content(否则 DeepSeek 400)
- ⚠️ tool_call/tool_result 配对: 压缩保留最近配对, 不能截断中间(否则 insufficient tool messages)
- ⚠️ 动态 keep 下限: 至少 4 条, 保证模型有足够上下文
- ✅ 复用现有 _finalize_messages(已修 reasoning_content/配对) 可规避大部分风险

---

## E. 合并完整问题清单

### E.1 已修项（本次+今天费用保护）
| 时间 | 项 | 验证 |
|---|---|---|
| 今天 | 费用保护 5 项(per_task 50万/daily 20元/thinking按需/max_tokens动态/成本日志) | 591 passed |
| 今天 | 审核修复 3 项(缓存增量/ledger公式/budget_limit success=False) | 594 passed |
| 今天 | Harness thinking off(settings.yaml) | reasoningEffort: off |
| 8/24 | B站校准 frames/evaluate/upload + profile 锁 | 真机验证 |
| 8/24 | 审批确认后反查完整参数(防500截断) | 验证通过 |
| 8/24 | 7B 降级修复(原生tools/结果注入/失败3次停) | 循环堵住 |

### E.2 待修项（P0/P1/P2）
| 优先级 | 项 | 工作量 |
|---|---|---|
| P0 | Harness maxTurns(源码只读, 需授权) | 0.5h |
| P1 | 会话消息并发锁(并行工具 append 竞态) | 1h |
| P1 | 压缩并发保护(_compress_messages 加锁) | 0.5h |
| P1 | V9 compaction thresholdRatio=0.8 移植 | 1.5h |
| P2 | Harness 费用可视化(与 V9 分开统计) | 2h |
| P2 | web-search 直连 DeepSeek(不走 V9 网关) | 1h |
| P2 | 会话 jsonl 清理(90MB) | 0.5h |

### E.3 新增发现
| 发现 | 说明 |
|---|---|
| Harness 与 V9 共用 key | 账单合并, 无法分开统计 |
| Harness 无费用换算 | 只记 usage, 不转金额 |
| Harness thinking 默认 high | 已改 off(settings.yaml) |
| V9 无自动压缩阈值 | 硬编码 0.8/0.9, 非配置化 |
| V9 并行工具无消息锁 | ThreadPool append 竞态隐患 |

---

## F. 建议下一步（3 项以内）

1. **P1: V9 compaction thresholdRatio=0.8 移植**——复用现有 _compress_messages/_finalize_messages, 只改触发为配置化阈值(0.8), 风险低收益大(自动控制上下文)
2. **P1: 会话消息并发锁**——并行工具 append 加锁, 防竞态(1h 工作量)
3. **P0: Harness maxTurns 授权实施**——源码只读需你授权, 补丁方案已出(30 轮上限)
