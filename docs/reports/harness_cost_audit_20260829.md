# Harness 平台自身费用机制检查报告

**日期**: 2026-08-29 | **状态**: 已查实（未改代码）

---

## 一、Harness 自身 LLM 调用

### 模型与参数（~/.dsh/settings.yaml）
```
agent-default-model:
  provider: deepseek-official
  model: deepseek-v4-flash
  reasoningEffort: high      # thinking 默认 high(费用放大点!)
```

### 调用量（当前会话 8/29 实测, session.jsonl.zstd）
| 指标 | 数值 |
|---|---|
| 会话事件 | 191,131 条 |
| LLM 调用(usage) | 18,167 次 |
| 总 input | 1,387 万 tokens |
| 总 output | 1,038 万 tokens |
| **总 reasoning(thinking)** | **326 万 tokens** |
| 总 tokens(input+output+reasoning) | **2,752 万** |
| cache 命中 | 79 亿 tokens(缓存放大, 实际费用低) |

### Token 记录能力
- OK mapUsage(translate.ts) 完整映射 input/output/cache/reasoning tokens
- X 无费用换算(不把 tokens 转金额)
- X 无费用持久化(usage 只在会话 jsonl, 无 billing 文件)
- X 无 token 预算/费用上限

---

## 二、平台 Agent 任务（工作区）

### 上下文管理（Harness 优于 V9）
- OK compaction 自动压缩: thresholdRatio=0.8(上下文达窗口 80% 自动压缩)
- OK token-meter 服务(测量/投影上下文压力)
- OK maxTokens(每 agent 输出上限) + maxParallelToolCalls=10

### 循环保护（弱）
- agent 主循环 while(await this.turn()) (agent.ts L212)
- 终止靠 LLM 判断: completed / max-tokens / 无工具调用(L394)
- X 无显式轮次上限(无 maxTurns/stepLimit)
- 注意: 若 LLM 反复输出工具调用可能循环(DeepSeek 质量高实际风险低; 7B 降级场景无保护)

---

## 三、费用数据源（独立性）

### 账单合并（关键）
```
V9 key 和 Harness key 相同(sk-913c...)
→ 同一 DeepSeek 账号, 账单合并, 无法分开统计
```

### 占比估算（当前会话 vs V9）
| 来源 | tokens | 说明 |
|---|---|---|
| Harness 当前会话 | 2,752 万 | 含 reasoning 326 万, cache 79亿(费用低) |
| V9 8/26 单日 | 1.9 亿 | thinking 模式 + 不压缩为主因 |
| 比例 | 约 1:7 | Harness 约 V9 单日的 1/7 |

> 注意: web-search-deepseek 的 baseURL 指向 localhost:5002(V9 网关)——Harness 的 web 搜索可能经 V9 网关调用, 进一步混合

---

## 四、与 V9 类似的问题对比

| 问题 | V9 | Harness |
|---|---|---|
| 无费用预算 | 有(刚修: per_task 50万 + daily 20元) | X 无 |
| 上下文不压缩 | 有但非强制 | OK compaction 自动(0.8) |
| thinking 放大 | 已修(默认关, 按需开) | 注意 默认 high(放大) |
| 循环保护 | 7B 连续失败3次停 | X 无显式轮次上限 |
| token 日志 | OK ledger 记账 | OK usage 记录(无费用) |
| 费用换算 | OK ledger cost | X 无 |
| 账单独立 | - | X 与 V9 合并 |

---

## 五、结论与建议

### 结论
1. Harness 费用被 V9 账单掩盖: 同一 key 合并计费, Harness 的 2752 万 tokens(含 cache 79亿) 与 V9 的 1.9 亿/日 混在 1566 元里, 无法单独核算 Harness 实际花多少
2. Harness 有 V9 没有的机制: compaction 自动压缩(0.8 阈值) + token-meter——上下文管理比 V9 好
3. Harness 有 V9 已修的缺口: thinking 默认 high(放大) + 无费用预算 + 无轮次上限

### 建议（按优先级）
1. thinking 降级: settings 的 reasoningEffort: high 改为 off(普通对话不需要 thinking, 省 326 万 reasoning tokens)
2. 会话轮次上限: agent-loop 加 maxTurns(防 7B/异常场景循环)
3. 费用可视化: Harness 增加 tokens 到金额换算(按 deepseek 定价), 与 V9 分开统计, 才能知道各自占比
4. web-search 直连: web-search-deepseek 的 baseURL 改为直连 DeepSeek(不走 V9 网关), 减少混合
5. 会话清理: 90MB 会话文件(59MB 单会话), 建议定期归档
