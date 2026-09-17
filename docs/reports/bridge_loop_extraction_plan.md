# 桥接循环提取方案分析（_v9_bridge_loop）

> 日期：2026-08-15
> 背景：H1 v9_agent_chat 拆分——用户提议提取桥接循环为 _v9_bridge_loop(messages, tools, user_id, thinking)。
> 目的：分析提前退出点的处理方案，评估可行性（先分析，未执行）。

---

## 〇、实测边界（代码实证，非推断）

| 项 | 实际值 |
|---|---|
| 循环起始 | L2354（for _bridge_round in range(8)）|
| 循环结束 | 约 L3566 |
| **循环实际长度** | **约 1200 行**（非 210 行）|
| 循环内 return jsonify | **6 个**（非 4 个）|
| 循环后最终 return | L3569 |
| 外层 except return | L3570-3571 |

**修正用户估计**：桥接循环是 v9_agent_chat 的主体（1200 行，占 65%），不是 210 行的小段。提取收益是**一次移走 1200 行（减 65%）**，但风险相应放大。

---

## 一、6 个提前退出点清单

| # | 行号 | 触发 | 当前行为 | 提取后返回值 |
|---|---|---|---|---|
| 1 | L2357 | API 调用失败 | return jsonify({success: False, error: ...}) | (None, steps, exhausted, {success:False...}) |
| 2 | L2384 | Agent 输出【ask】 | return jsonify({status: ask, ...}) | (None, steps, exhausted, {status:ask...}) |
| 3 | L2426 | 路径越权（锚点B）| return jsonify({status: escalation_blocked}) | (None, steps, exhausted, {...}) |
| 4 | L2470 | 计划确认（G2）| return jsonify({status: plan_pending}) | (None, steps, exhausted, {...}) |
| 5 | L2511 | 写确认（锚点A）| return jsonify({status: write_pending}) | (None, steps, exhausted, {...}) |
| 6 | L2543 | 高危命令拦截 | return jsonify({status: escalation_blocked}) | (None, steps, exhausted, {...}) |

---

## 二、提取签名与返回值约定

```python
def _v9_bridge_loop(messages, tools, user_id, session_id, thinking=False):
    """返回 (messages, tool_steps, bridge_exhausted, final_resp, tokens)
    final_resp: None=正常结束(走最终组装); 非None=提前退出(直接jsonify)"""
```

调用方：
```python
_m, _steps, _exh, _final, _tok = _v9_bridge_loop(messages, tools, user_id, session_id, _thinking2)
if _final is not None:
    return jsonify(_final)
```

---

## 三、关键难点与处理方案

### 难点1：tokens/data_resp 逃逸
- 循环内累计 tokens，循环后 L3569 用 tokens/data_resp 组装
- 方案：返回值加 tokens；data_resp 由 final_resp 带回或正常路径重取

### 难点2：提前退出的 _bmsg content 修改
- 部分提前退出前改了 _bmsg[content]（追加系统提示），未回写 messages
- 方案：提前退出不动 messages（前端用 final_resp 展示），保持现状

### 难点3：_ts_progress/_tool_steps 闭包
- _ts_progress 是循环外闭包（用 len(_tool_steps)）
- 方案：_tool_steps 由返回值带回，progress 逻辑内联

### 难点4：6 个 return 需逐一改写
- 每个 return jsonify({...}) → return (None, steps, exhausted, {...}, tokens)
- 这是提取不重写策略的边界——提前退出点必须重写（用户已识别）

---

## 四、风险评估

| 风险 | 等级 | 缓解 |
|---|---|---|
| 1200 行一次性提取 | 🔴 高 | 分两步：先循环骨架，再门控拦截 |
| 6 个 return 改写 | 🔴 高 | 每个 dict 逐字保留，只改返回载体 |
| 闭包变量逃逸 | 🟠 中 | 返回值显式化 |
| 装饰器/路由（已知坑）| 🟢 已解决 | 提取后验证路由 |

---

## 五、建议

**可以拆，但分两步降险**：
1. 第一步：提取纯循环骨架（LLM 调用+break+最终组装），门控暂留主函数
2. 第二步：门控拦截（6 个 return）随循环体提取，逐一改写返回值

**或更稳**：先提取单个门控（如 G3 ask 段，最小提前退出）验证模式，再推广。

**结论**：方向正确，但实际 1200 行/6 个退出点比预期大——建议先做最小门控提取验证模式，再全量提取。
