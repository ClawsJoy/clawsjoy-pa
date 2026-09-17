# V9 thinking 模式 400 系统性排查报告

> 状态: 排查完成 — 报告输出, 待确认修复方案后实施

## 1. 结论先行（实证）

**DeepSeek 400 的真正根因不是 reasoning_content，而是 tool_calls/tool 配对破坏与 tool_calls 结构缺失。**

用真实 DeepSeek API（config/.env key）对全部消息形态逐一实测：

| 场景 | 结果 | 说明 |
|---|---|---|
| A: 多历史 reasoning_content + thinking | 200 | 历史含多条 reasoning 完全合法 |
| B: tool_calls + reasoning + thinking | 200 | 桥接循环每轮形态 |
| D: content=None + reasoning + tool | 200 | 空 content 合法 |
| E: 两轮 reasoning+tool 交替 | 200 | 多轮 thinking 合法 |
| F: 纯 reasoning 无 content | 200 | |
| G: 空 assistant | 200 | |
| J: 空 reasoning_content 字段 | 200 | |
| H: 孤立 tool(无前置 assistant tool_calls) | **400** | tool 必须响应前置 tool_calls |
| I: tool_calls 无 tool 响应 | **400** | assistant tool_calls 必须被 tool 响应 |
| K: tool 在 assistant 之前(顺序颠倒) | **400** | 同上 |
| L: tool_calls 缺 type 字段 | **400** | messages[1]: missing field type |

## 2. 与设计文档的偏离

bridge_loop_extraction_plan.md 的 thinking 设计: thinking 只是 adapter 层布尔开关, tool 配对完整性由 SessionLog.derive_messages(P2b) 保证。

当前实现偏离:
- TOKEN_GUARD 硬截断在 retry 路径未过 _validate_messages (L3208→L3219 直接调 API) → 孤立 tool/未配对 → 400(实测 tail=4/6 均产生孤立 tool)
- _bassist(L2836)/事件双写(L2843) 未统一 tool_calls 结构: DeepSeek 响应自带 type 首轮 OK, 重建/回传路径可能丢 type(实测缺 type → 400)
- 此前三处 reasoning_content 补丁(压缩过滤/分层切点/快照恢复)非根因, 但方向无害, 可保留

## 3. 完整链路审计

```
v9_agent_chat (POST /v9/agent/chat)
 ├─ L4219 快照恢复: _snap_msgs + messages [已补: 剥离旧 reasoning]
 ├─ L4775 _thinking2 = len(.py 路径匹配)>=2   ← 动态开关
 ├─ L4784 _truncate_oversized_messages → _validate_messages OK
 ├─ L4799 _compress_messages → _hard_truncate → _validate_messages OK
 ├─ L4806 TOKEN_GUARD: sys[:2]+摘要+tail[-4:] → L4819 _validate_messages OK
 └─ _v9_bridge_loop
     for round in 8:
      ├─ L2713 messages = derive_messages()  [P2b 过滤未执行 tool_calls OK]
      ├─ L2776 execute_with_tools(thinking) → DeepSeek
      ├─ L2836 _bassist = {role,content,tool_calls}[+reasoning]
      ├─ L2843 事件双写 assistant_message
      ├─ 工具执行 → tool_result 事件
      └─ L3208-3219 [length retry] TOKEN_GUARD 截断 → 直接调 API, 未 validate ❌
_execute_agent_task:
 ├─ L1035 TOKEN_GUARD 截断 → L1055 _validate_messages OK
 └─ L1074 execute_with_tools(thinking)
```

## 4. 不一致点清单

| # | 位置 | 问题 | 影响 |
|---|---|---|---|
| 1 | L3208-3219 (retry 路径) | 截断后直接调 API, 未过 validate | 孤立 tool/未配对 → 400 |
| 2 | L2836/L2843 + exec L1316 | tool_calls 未统一补 type | 重建路径丢 type → 400 |
| 3 | exec L1055 | validate 在投影补记之后 | 截断残留孤立 tool 被写回日志 → 二次污染 |
| 4 | L4806 vs L3206 两处 TOKEN_GUARD | 主路径 validate, retry 不 validate | 行为分叉 |

## 5. 根因分析

截断(压缩)与配对修复(validate)职责分离, 但 retry 路径漏套 validate, 且 tool_calls 结构规范化(补 type)只在 ollama 适配器做, DeepSeek 路径无统一出口。
设计缺陷: 所有'修改 messages 后发往 DeepSeek'的路径必须经过同一配对+结构规范化出口。

## 6. 修复方案

### 方案 A: 统一消息出口(推荐)

message_assembler.py 新增 _finalize_messages(messages) = _normalize_tool_calls(_validate_messages(messages)):
- _normalize_tool_calls: 每个 assistant.tool_calls 补 tc.setdefault('type','function') + arguments dict→json 字符串
- 替换调用点: L4819 主路径 / L3213-3219 retry 路径(修复漏网) / exec L1055 / 压缩函数内部统一

### 方案 B: retry 路径最小修复

仅 L3213 后加 _validate_messages(messages) — 解决 400 主因, 但 type 风险仍在。

建议: 方案 A。

## 7. 验证计划

1. 单测: _finalize_messages 对 孤立tool/未配对/缺type/arguments dict 全部修复
2. 集成: retry 截断场景 → finalize 后无孤立/未配对
3. 真实 API: 修复后 messages 调 DeepSeek(thinking on) → 全部 200
4. 回归 + 浏览器验证

## 8. 已做与待做

已做: 链路图 / 不一致清单 / 根因 / 实证(真实 API 400 复现)
待做(待确认): 方案 A 实施 + 验证
