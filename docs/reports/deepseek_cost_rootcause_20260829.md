# DeepSeek 费用超高根因检查报告

**日期**: 2026-08-29 | **状态**: 已查实（未改代码）

---

## 一、费用消耗构成（billing 数据实证）

数据源: `data/v8/billing_default.jsonl`（54,604 条记录，总计 1566.89 元）

### 关键日期费用
| 日期 | 请求数 | 费用 | 备注 |
|---|---|---|---|
| 8/24 | 117 | **267.34 元** | B站/小红书校准日（thinking 模式工具密集） |
| 8/26 | 47 | **190.99 元** | 抖音校准日 |
| 8/27 | 73 | **59.60 元** | 降级修复后仍高 |
| 8/23 | 91 | 55.21 元 | - |
| 8/07-13 | 2000-3300/日 | 40-75 元/日 | 高峰时期（8/9 单日 3319 次请求） |

### token 分布（8/26 实证）
- 47 条记录，**83% 单条 tokens > 10 万**
- 中位数 **301 万 tokens/条**，最大单条 **1522 万 tokens（15.23 元）**
- 8/26 合计 1.9 亿 tokens

---

## 二、根因链（完整）

```
V9 主路径(bridge_loop)每轮调用 DeepSeek:
  adapter.execute_with_tools(max_tokens=8000, thinking=true)   ← 每轮
    ↓
每轮 usage.total_tokens 包含完整消息历史(多轮后巨大)
    ↓
bridge_loop 内 tokens += resp.tokens 跨轮累计(L3066+L3530)
    ↓
一次 /v9/agent/chat = 一个完整 bridge_loop(多轮) → 记账 tokens=300万+
    ↓
ledger.record_cost(tokens, unit_price=0.001) → cost=tokens/1000*0.001
    ↓
8/26 单日 47 次任务 × 300万+ tokens = 1.9 亿 tokens = 190 元
```

**核心驱动因素**:
1. **thinking 模式 + max_tokens=8000**: 每次调用输出+推理 token 巨大（thinking 模式 DeepSeek 计费含推理 token）
2. **消息历史不压缩**: 多轮后 total_tokens 每轮都大（输入历史随轮次线性增长）
3. **高频工具任务**: 校准日（B站/抖音）大量多轮工具调用
4. **真实消耗非 bug**: 记账的 tokens = DeepSeek 实际计费的 total_tokens 之和，费用真实

---

## 三、手动修复（8/24）有效性评估

### ✅ 已堵住的循环
| 机制 | 位置 | 效果 |
|---|---|---|
| 402/Insufficient → 降级 Ollama | L2969 | 402 后不再走 DeepSeek |
| 7B 原生 tools API | L3021 | 不再正则猜 tool_calls |
| 干净消息流 + 结果注入 | L2995-3002 | 7B 知道工具已执行 |
| 连续失败 3 次强制停止 | L3208-3213 | 防 7B 死循环 |
| 工具成功注入 _7b_last_result | L3214-3216 | 防重复调工具 |

### ⚠️ 未堵住的费用
- **8/26-27 仍高费用（191+59 元）**：降级只发生在 402 时；余额充足时仍用 DeepSeek + thinking 模式 → 费用照涨
- **402 不扣费但频繁触发**：402 是余额不足被拒（不扣费），但每次请求都先打 DeepSeek 再降级 → 无谓的 API 往返（不计费但浪费）

---

## 四、费用保护机制缺口

| 保护项 | 现状 | 缺口 |
|---|---|---|
| token 日志 | ✅ ledger 记录每任务 tokens | 无（已记录）|
| 单任务 token 上限 | ❌ 无 | **bridge_loop 无 token 预算** |
| 单任务费用上限 | ❌ 无 | **无 cost cap** |
| 请求频率限制 | ⚠️ rate_limiter 存在 | 未验证覆盖 V9 主路径 |
| 每日费用上限 | ⚠️ _check_discuss_token_budget | **只覆盖 discuss 分支，不覆盖 V9 主路径** |
| 余额预警 | ❌ 无 | 无提前预警，靠 402 |
| 降级开关 | ⚠️ 代码硬编码 | 无 config fallback_model/开关 |

---

## 五、建议（需后续实施）

### 1. 费用/Token 上限（最高优先级）
- bridge_loop 加 **per-task token 预算**（如 100 万 tokens/任务，超限强制结束）
- 每日费用上限（如 20 元/日，超限自动切 Ollama 或拒绝）
- 复用 ledger 数据做实时累计

### 2. 降级策略完善
- config 加 `fallback_model: ollama/qwen2.5:7b` + 开关
- 402 前**余额预警**（余额 < 阈值提前降级，不等 402）
- 简单任务（摘要/标签/翻译）→ 7B；复杂任务（工具调用）→ 提示充值

### 3. 成本优化
- 消息历史**压缩**（已有 _compress_messages，但未强制用于每次调用）
- thinking 模式降为**按需**（非默认）
- 降低 max_tokens（8000 → 2000-4000 视任务）

### 4. 监控
- ledger 数据已够（tokens/cost/model/agent/日期）
- 加每日费用告警（>阈值 notify_boss）
