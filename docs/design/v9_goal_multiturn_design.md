# Goal 驱动多 turn 执行循环 — 设计文档

> 前置: P1 Goal 持久化 + P2 跨 session 复盘 已完成。本文设计'一个 goal 拆多个 bridge turn 顺序执行'。

## 1. 问题与现状

| 现状 | 问题 |
|---|---|
| 单个 POST /v9/agent/chat → _v9_bridge_loop 一次跑满 8 轮 / max_total_tools=16 后 bridge_exhausted | 复杂任务(改多文件/长链验证)工具数不够 |
| 前端 runAgentLoop 收到 reason=max_tokens 直接 break(L323-333) | 任务未完成即停, 需用户手动'继续' |
| _write_turn_end 非 completed 时 done += tools_n, 完成时 done = total | progress 与'轮次'无语义对应, 前端进度条按单轮 tool 数显示(L380-382) |
| create_goal 每次 POST 都刷新 objective(L4164-4176) | 续跑时会覆盖目标文本 |

## 2. 目标形态（对齐 Harness）

```
用户任务 → goal(active, max_turns=5)
  ├─ turn 1: bridge_loop(8轮/16工具) → reason=max_tokens, done=16/80
  │     ├─ 注入 steer: '继续目标 X，已完成 16/80 步'
  │     └─ 前端显示 '第 2 轮继续执行…'
  ├─ turn 2: bridge_loop(8轮/16工具) → reason=max_tokens, done=32/80
  │     └─ …
  ├─ turn 4: bridge_loop → reason=completed 且 done>=total → complete_goal ✅
  └─ turn 5(上限): 仍未完成 → 停止自动续跑, 提示已达最大轮数
```

## 3. 核心机制

### 3.1 进度语义改为'goal 轮次驱动'

- goal.progress.total = max_total_tools × goal_max_turns（默认 16×5=80），goal 创建时写入（无 plan 时）。
- 每结束一个非 completed turn：done += 本轮实际工具数（沿用 _write_turn_end 现有逻辑，不再改）。
- 前端进度条显示 done/total（goal 级），并附 turn=N/max_turns 徽标 —— 替换现在按单轮 len(_tool_steps)/16 的 _ts_progress() 展示。

> 已有 plan 的 goal 保持 total=len(plan) 语义不变（plan 步数即 total）；无 plan 时退化为'工具预算×轮数'。

### 3.2 完成判定（goal 完成）

_write_turn_end 现有逻辑已满足大部分，补充'done>=total'守卫：

```python
# _write_turn_end 内 (agent_gateway_enhanced.py L1980-2007)
if reason == 'completed' and _g.get('status') in ('active', 'paused'):
    if _new_done >= _total:          # 新增守卫: done>=total 才算完成
        complete_goal(uid, sid)
    else:
        update_goal_progress(...)    # 完成了但步数未满 → 继续, 不 complete
```

显式 complete_goal（现有 /v9/agent/chat ✅ 路径 L2895 / 同步路径）保持不变，仍为第二个完成入口。

### 3.3 多 turn 循环（前端驱动续跑）

沿用前端已有循环骨架 runAgentLoop（maxLoops=200）+ continuePausedTask 的续传模式，**不在后端做长阻塞循环**（避免单请求超时、无法中途停止）：

**后端（v9_agent_chat）**：
1. 请求体新增 data.continue_goal=true（前端续跑时携带）。
2. continue_goal 时**跳过 create_goal 的 objective 覆盖**（L4164-4176 加判断：goal active 且 continue → 仅读取现有 goal）。
3. turn 开始注入 steer（走既有 add_steer 通道，复用 P4 成果）：
```python
'继续目标 {goal_id短}，已完成 {done}/{total} 步（第 {turn}/{max_turns} 轮）。请基于已有进度继续，不要重复已完成步骤。'
```
4. 响应新增字段：goal_status / goal_done / goal_total / turn / max_turns / goal_complete（从 goal_state 读，复用 get_goal_by_session_id）。

**前端（chat.js runAgentLoop max_tokens 分支）**：
```js
if (turnReason === 'max_tokens') {
  // P4 空产出修复: 摘要优先(已实现)
  // 新增: goal 驱动续跑
  const g = d.goal_info || {};
  if (g.goal_active && !g.goal_complete && g.turn < g.max_turns) {
    agentLog('🔄 第 ' + (g.turn + 1) + ' 轮继续执行（目标 ' + g.goal_done + '/' + g.goal_total + '）', '#d2991d');
    messages = messages.concat([{ role: 'user', content: '[系统] 继续执行当前目标' }]);
    continue;  // 复用现有 while 循环, 下一轮 POST 带 continue_goal
  }
  ...break;
}
```

### 3.4 循环上限（goal 级 max_turns）

- 配置：config/v9/execution_policy.yaml 新增 execution_budget.goal_max_turns: 5
- 读取：_load_v9_execution_policy().get('execution_budget', {}).get('goal_max_turns', 5)（与 max_total_tools 同模式）。
- 达到上限仍未完成：前端显示 '⚠️ 已执行 5 轮仍未完成，请重新描述或分步下达任务'，不自动续跑；goal 保持 active（用户可手动继续或改目标）。

### 3.5 turn 事件审计（复用现有）

- 每 turn 已写 turn_start/turn_end（SessionLog, _write_turn_end）—— 无需新事件。
- goal 层面新增语义：goal_event 已含 action=progress/status（goal_state.py L85-94）—— 多 turn 自然累积。
- P2 复盘面板已展示 goal 级 progress + turn 摘要 —— 多 turn 后天然可见'goal 拆了几轮'。

## 4. 复用清单

| 组件 | 复用点 |
|---|---|
| goal_state.py | create_goal(不覆盖) / get_goal_by_session_id / update_goal_progress / complete_goal |
| Turn 协议 | _write_turn_end(reason + turn_end 事件 + goal 关联) |
| SessionLog | turn_start/step_start/turn_end/goal_event 全链路已写 |
| add_steer 通道 | 每轮续跑注入'继续目标 X，已完成 a/b 步'(P4 成果) |
| 前端进度条 | renderProgressBar 改传 goal progress(done/total) + turn 徽标 |
| execution_policy.yaml | 新增 goal_max_turns(默认 5) |

## 5. 改动文件清单

| 文件 | 改动 |
|---|---|
| config/v9/execution_policy.yaml | +goal_max_turns: 5 |
| agent_gateway_enhanced.py | continue_goal 分支(跳过 objective 覆盖) + 每 turn 注入 steer + 响应加 goal_info + _write_turn_end done>=total 守卫 |
| web/static/js/chat.js | max_tokens 分支: goal 未完成且未达上限 → 自动续跑(continue) + '第 N 轮继续执行' + goal 进度条 |
| 测试 | tests/unit/test_goal_multiturn.py(源码+行为) + test_maxsteps_budget.py 兼容 |

## 6. 测试计划

1. 后端源码断言：continue_goal 分支存在、goal_max_turns 从配置读、_write_turn_end 有 done>=total 守卫、响应含 goal_info。
2. 行为测试（monkeypatch 桥接循环）：turn1 max_tokens → 注入 steer(peek_steer) + goal done 累积；turn2 completed 且 done>=total → complete_goal；turn 达上限 → 不再续跑标记。
3. 前端断言：chat.js 含'第 N 轮继续执行'文案 + continue_goal 字段 + 上限提示。
4. 浏览器验证：真实任务跑 2 轮（用低 max_total_tools 模拟收敛），观察进度条/继续提示。

## 7. 边界与风险

- stale messages 防重发：续跑复用 P0-1 bridge_exhausted break 语义 —— 仅在 reason=max_tokens 且 goal 未完成时 continue，且 messages 只追加'继续'指令（不含残留 tool_calls），防死循环。
- create_goal 覆盖：必须 continue_goal 时跳过 objective 更新，否则每轮目标被'继续执行'覆盖。
- 无 plan goal 的 total：默认 = max_total_tools×goal_max_turns；有 plan 仍用 len(plan)。
- 取消：agentAbort/取消标记在每 turn 每轮检查，用户可随时停止（现有能力）。
- 兼容：不带 continue_goal 的旧请求行为完全不变（单 turn 语义）。

## 8. 实施顺序

1. config + _write_turn_end 守卫 + continue_goal 分支 + steer 注入 + goal_info 响应（后端）
2. 后端单测（源码 + 行为）
3. chat.js 续跑分支 + goal 进度条
4. node --check + 浏览器验证 + 全量回归
5. diff 输出
