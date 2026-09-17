# V9 Turn 协议层设计 — 吸收 Harness turn/step 生命周期

- 日期: 2026-08-19
- 状态: 设计文档(先出方案, 待评审后实施)
- 目标: 为 V9 桥接执行建立完整回合生命周期, 对齐 Harness turn/step 协议, 根治'空回复误判完成'、'终止原因不明'、'前端无差别渲染'三类问题

---

## 一、现状盘点

### 已有基础(无需新建)
- SessionLog 已定义事件类型: EV_SESSION_START/EV_TURN_START/EV_TURN_END/EV_STEP_START/EV_STEP_END/EV_USER_MESSAGE/EV_ASSISTANT_MESSAGE/EV_TOOL_CALL/EV_TOOL_RESULT/EV_RUNTIME_CONTEXT/EV_SESSION_END (session_log.py:21-31)
- 游标 API 已存在: set_turn/set_step/begin_turn/begin_step (session_log.py:112-126), 但 bridge_loop/execute_agent_task 未使用
- 结构化错误码已有: LLM_API/NETWORK/TOOL_EXEC/TOOL_ARGS/TIMEOUT/UNKNOWN (execute_agent_task.py:30)
- 前端已有 status 分支: write_pending/ask/plan_pending/escalation_blocked/initializing (workbench.html:444-450, 1461-1530)
- 近期修复: P0-1 bridge_exhausted 语义、P1-1 8轮耗尽收敛、P0/P1/P2 空回复重试+兜底

### 缺口
| 缺口 | 现状 | 影响 |
|---|---|---|
| 终止原因 | done payload 只有 bridge_exhausted/status, 无 reason | 前端无法区分 completed/error/blocked/aborted |
| turn 事件 | turn_start/turn_end/step_start/step_end 定义了但从不写入 | 日志无法重建回合边界 |
| 空回复语义 | 已拦截(P0/P2)但无协议化状态 | need_more 未显式表达 |
| 完成判定 | 前端 '!msg.tool_calls' 判完成, 与后端脱节 | 前端可能误判 |

---

## 二、Turn 状态机设计

### 2.1 生命周期(每轮对话 = 一个 turn)
```
┌─────────────┐
│ turn_start  │  turn_id = begin_turn()  (写入 SessionLog)
└──────┬──────┘
       │
       ▼
┌─────────────┐  循环(最多 8 步, 每步 = 1 次 LLM 调用 + N 个工具执行)
│ step_start  │  step_id = begin_step()  (写入 SessionLog)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ LLM 调用    │  execute_with_tools()
└──────┬──────┘
       │
       ▼
┌─────────────┐  每个 tool_call → tool_result (已有事件)
│ 工具执行    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ step_end    │  (写入 SessionLog, 可带 step 摘要)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ turn_end    │  reason: completed/max_tokens/error/blocked/aborted/need_more
└─────────────┘
```

### 2.2 终止 reason 协议

| reason | 判定条件 | 对应现有路径 |
|---|---|---|
| completed | assistant 有 content 且无待执行 tool_calls(正常 break) | `not _btool_calls` 且 content 非空 |
| max_tokens | 达到步骤/工具上限但已有产出 | `_round_exhausted`(8轮) / `_bridge_exhausted`(工具超限) |
| error | 执行异常(LLM API/工具异常) | `resp.success=False` / except 分支 |
| blocked | 守卫拒绝(write_pending/plan_pending/escalation/forbidden) | guard deny 各分支 |
| aborted | 用户取消 | 前端 agentAbort / 超时强杀 |
| need_more | 空回复(无 content 无 tool_calls)重试后仍空 | P0 重试上限后 |

### 2.3 空回复语义(关键)
```
空回复(无 content 且无 tool_calls)
  ├─ 第1次: 注入提示 → 重试 (P0 已实现, _empty_reply_count=1)
  ├─ 第2次: 注入提示 → 重试 (P0, count=2)
  └─ 第3次: turn_end(reason=need_more) → 前端提示重试, 不判完成
```
**空回复不属于任何完成态** — 它是 need_more, 由协议显式表达。

---

## 三、前后端契约

### 3.1 done payload 扩展
```json
// 现状
{"type": "done", "success": true, "bridge_exhausted": true,
 "tool_steps": [...], "progress": {...}}

// 目标: 加 reason 字段
{"type": "done", "success": true,
 "reason": "max_tokens" | "completed" | "error" | "blocked" | "aborted" | "need_more",
 "reason_detail": "8轮耗尽，请基于现有信息输出评估结论",
 "bridge_exhausted": true,   // 保留兼容
 "tool_steps": [...], "progress": {...}}
```

### 3.2 前端按 reason 渲染
```js
switch (d.reason) {
  case 'completed':  agentLog('✅ 任务完成'); break;
  case 'max_tokens': agentLog('⚠️ 已达轮次/工具上限，已输出当前结论'); break;
  case 'error':      agentLog('❌ 执行出错: ' + d.reason_detail); break;
  case 'blocked':    agentLog('🚫 已被拦截: ' + d.reason_detail); break;
  case 'aborted':    agentLog('⏹ 任务已取消'); break;
  case 'need_more':  agentLog('⚠️ 模型未产出内容，请重新描述需求'); break;
  default:           /* 兼容旧 payload: 现有逻辑 */
}
```

---

## 四、SessionLog 集成

### 4.1 turn 事件写入点
```
_v9_bridge_loop 入口:  log_event(EV_TURN_START, {turn_id, task_name, user_id})
_v9_bridge_loop 每步:  log_event(EV_STEP_START, {turn_id, step_id, llm_round})
                      log_event(EV_STEP_END,   {turn_id, step_id, tools_executed})
_v9_bridge_loop 出口:  log_event(EV_TURN_END,  {turn_id, reason, reason_detail, rounds, tools, tokens})
```

### 4.2 回放重建 turn 结构
```
def derive_turns(self) -> List[dict]:
    """从事件重建回合结构: [{turn_id, reason, steps: [{step_id, tools}], tokens}]"""
    turns = []
    cur = None
    for ev in self._events:
        if ev.type == EV_TURN_START: cur = {turn_id:..., steps: []}
        elif ev.type == EV_STEP_START: cur_step = {...}
        elif ev.type == EV_TOOL_RESULT: cur_step.tools.append(...)
        elif ev.type == EV_TURN_END: cur.reason = ...; turns.append(cur)
    return turns
```

### 4.3 与现有事件兼容
- 不改变已有事件类型/投影逻辑(derive_messages 不受影响)
- turn/step 事件是纯增量, 回放时 skip 不影响 derive_messages
- 现有 P2b 双写(assistant/tool_call/tool_result)保持

---

## 五、渐进迁移计划(3 步)

### Step 1: reason 字段 + 空回复 need_more(最小改动, 1 个文件+前端)  — 本次实施
- bridge_loop 各终止点补 reason 计算: completed/max_tokens/error/blocked/need_more
- done payload(stream + non-stream)带 reason + reason_detail
- P0 空回复重试第3次 → reason=need_more
- 前端: done 渲染按 reason 分支; 空内容不判完成(已有 P2 基础)

### Step 2: turn/step 事件写入(增量, 不影响行为)  — 下一轮
- _v9_bridge_loop 入口/每步/出口写 turn_start/step_start/step_end/turn_end
- execute_agent_task 同步接入(异步执行路径)
- derive_turns() 回放重建

### Step 3: 前端按 reason 完整渲染 + 审计(收尾)  — 最后一轮
- 前端 reason 渲染补全(aborted/error 视觉差异)
- turn 结构接入审计日志/复盘报告
- 全量测试覆盖

---

## 六、测试计划

| 测试 | 覆盖 |
|---|---|
| test_turn_reason_completed | LLM 正常回复 → reason=completed |
| test_turn_reason_max_tokens | 8轮耗尽/工具超限 → reason=max_tokens |
| test_turn_reason_need_more | 空回复重试3次 → reason=need_more |
| test_turn_reason_error | API 异常 → reason=error |
| test_turn_reason_blocked | guard deny → reason=blocked |
| test_derive_turns | turn 事件写入后回放重建结构 |
| test_frontend_reason_render | 前端按 reason 分支渲染 |

---

## 七、风险与兼容

| 风险 | 缓解 |
|---|---|
| 旧前端不认 reason | 保留 bridge_exhausted/status 字段, reason 为增量 |
| turn 事件量大 | 每 turn 最多 8 step, 量可控 |
| 回放兼容 | turn 事件不进 derive_messages 投影, 现有逻辑零影响 |
| reason 判定遗漏 | 所有 return 点统一过 _compute_turn_reason() helper |
