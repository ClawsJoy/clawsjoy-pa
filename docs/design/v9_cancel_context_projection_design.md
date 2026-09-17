# V9 设计 — 协作取消 AbortSignal + 运行时上下文投影

- 日期: 2026-08-19
- 状态: 设计确认稿(待评审后实施)
- 现状基线: bridge_loop 已 8 轮 + P3 并行工具池; 前端仅客户端 agentAbort 标志(不通知服务端);
  derive_messages 已确立为 LLM 输入唯一入口

---

## 一、#1 协作取消(AbortSignal)

### 1.1 问题
- 前端 agentStop() 只置本地 agentAbort, 服务端 bridge_loop 继续跑完剩余轮次
  (LLM 调用 + 工具执行照常消耗), 无法真正停止
- 硬杀(线程/进程)会破坏 SessionLog 配对与写入一致性

### 1.2 机制: 协作取消(不硬杀, 标记后下轮退出)
- **shared_state 新增**:
  ```python
  _cancel_flags = {}            # {session_id: threading.Event}
  _cancel_lock = None
  request_cancel(session_id)    # set(): 请求取消
  reset_cancel(session_id)      # clear(): 新任务开始前清旧标记
  is_cancel_requested(session_id) -> bool  # is_set(), 每轮/每工具前检查
  ```
- **路由**: `POST /v9/cancel/<path:session_id>` → request_cancel(sid) → jsonify

### 1.3 bridge_loop 检查点(协作: 不硬杀)
1. **任务开始**(create_goal 后): `reset_cancel(session_id)` — 清陈旧标记, 防误杀新任务
2. **每轮开始**(LLM 调用前): is_cancel_requested → break
3. **P3 阶段2 前**(并行池执行前): is_cancel_requested → 跳过执行直接退出
   (并行中的工具自然跑完, 已执行结果仍提交保配对; 未执行工具丢弃)
4. **每轮工具循环后**: is_cancel_requested → break
- 退出语义: `_bridge_exhausted=True`, 新 reason **"cancelled"**, 写 turn_end(reason=cancelled)
  + ledger 审计; LLM 调用本身不可中断(API 无 abort), 取消在下一检查点生效

### 1.4 exec 路径(_execute_agent_task)
- 每轮循环前同样检查 is_cancel_requested → break, turn_end reason=cancelled(低成本保持一致)

### 1.5 前端
- 执行按钮旁加 **⏹ 停止**(agentRunning 时显示)
- `agentStop()` 三连: POST /v9/cancel/{sessionId}(服务端标记) + AbortController.abort()
  (切断 SSE fetch) + agentAbort=true(停客户端循环)
- runAgentLoop/continuePausedTask 的 fetch 挂 `signal: window.__agentAbort.signal`;
  abort 时 agentLog("⏹ 已取消"), 循环退出, 不再自动 continue
- readSSEStream 遇 abort → 返回; donePayload.reason="cancelled" → 前端 reason switch
  新增 cancelled 分支(渲染"已取消", 不进入 completed/error 处理)

### 1.6 兼容
- 新 reason "cancelled" 加入 turn 协议(审计/回放天然兼容); 无取消时行为零变化
- 取消后标志保留至下次任务开始 reset(前端不再 continue, 无复用风险)

---

## 二、#2 运行时上下文投影

### 2.1 目标
- 当前策略快照(沙箱模式/审批模式/工具指导)渲染为**持久 user 消息**注入 LLM,
  让模型感知实时环境(沙箱根/审批开关/读写指导/并行配置)
- **变化才追加, 不从日志重建**: 内容取自实时策略状态; 注入决策靠内存指纹缓存,
  不依赖 SessionLog 回放

### 2.2 新模块 `core/gateway/context_projection.py`
```python
_snapshot_cache = {}   # {session_id: fingerprint}

def render_policy_snapshot(user_id, session_id) -> dict:
    """实时策略快照(每次从 live 状态读取):
    - sandbox_mode: sandbox_base 根标记 + project_prefix/forbidden_prefix
    - approval_mode: write_pending 待确认状态 / plan_pending 状态
    - tool_guidance: read_policy(max_files/max_list_dir/prefer_query_index),
      write_policy(small_edit/large_edit/comment_style), forbidden[],
      exclusive_tools[], max_parallel_tools, task_types(deliverable/write_required)
    """

def project_runtime_context(session_id, snapshot: dict) -> str | None:
    """指纹(json.dumps sort_keys)比对: 变化 → 缓存并返回渲染文本(≤600字); 未变 → None"""

def reset_context_projection(session_id):
    """新任务开始清指纹缓存(强制首轮注入)"""
```

### 2.3 bridge_loop 注入点
- **每轮开始**(与 steer 消费同点, derive_messages 重建后):
  ```python
  _snap = render_policy_snapshot(user_id, session_id)
  _ctx = project_runtime_context(session_id, _snap)
  if _ctx:
      messages.append({"role": "user", "content": _ctx})
      log_event(session_id, "user_message",
                {"role": "user", "content": _ctx, "source": "runtime_context"})  # 持久化
  ```
- **持久性**: 注入时写 user_message 事件(轮起始位安全, 不破坏 assistant tool_call/tool_result 配对
  — 与 P0 steer 同理), derive_messages 后续轮次自然保留
- **不从日志重建**: 快照内容每次实时读取(沙箱/审批状态); 是否注入由内存指纹决定,
  不从日志推导

### 2.4 exec 路径
- 可选同步注入(同模式, 保持两路径上下文一致; 低成本)

### 2.5 兼容与风险
| 风险 | 缓解 |
|---|---|
| 快照注入 token 膨胀 | 仅变化时追加 + ≤600 字截断 |
| user 消息插入破坏配对 | 仅轮起始注入(工具结果之后, 与 steer 同安全位) |
| 审批状态变化频繁 | 指纹含 pending 状态, 确认/清除时自然触发一次注入 |
| 快照内容陈旧 | 每轮实时 render(内容源 live), 仅注入决策走缓存 |

---

## 三、实施清单(确认后执行)
1. shared_state: _cancel_flags + request_cancel/reset_cancel/is_cancel_requested
2. context_projection.py: render_policy_snapshot / project_runtime_context / reset_context_projection
3. agent_gateway_enhanced.py: /v9/cancel 路由 + bridge_loop 4 检查点 + 轮起始快照注入
   + reason="cancelled"(turn_end/返回值) + exec 路径同构
4. web/dashboard/workbench.html: ⏹ 停止按钮 + agentStop 三连 + AbortController
   + reason switch 加 cancelled 分支
5. 测试: test_cancel_cooperative.py + test_context_projection.py
   (取消标志语义/检查点源码/路由/前端; 快照渲染/变化驱动/持久 user 消息/一致性)
6. 全量回归 + 实机冒烟(运行中取消 → 下轮退出 reason=cancelled; 快照注入一次且持久)

## 四、验证
- #1: 任务运行中 POST /v9/cancel → 下轮(或并行池前)退出, turn_end reason=cancelled,
  前端停止按钮中断流; 无 400/配对破坏
- #2: 首轮注入快照 user 消息, 策略未变不再追加; 修改 execution_policy/审批状态 → 再次注入;
  derive_messages 保留注入消息, 与 LLM 输入一致
