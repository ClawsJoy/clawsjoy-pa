# V9 缺失能力设计 — Goal 持久化 / inbox 三通道 / 并行工具池

- 日期: 2026-08-19
- 状态: 设计文档(基于 Harness 能力映射, 待评审后分期实施)
- 现状基线: goal_state.py 已有 Goal 骨架; inbox/并行工具池全新

---

## 一、Goal 持久化

### 1.1 现状盘点
- `core/gateway/goal_state.py` 已有: create_goal / get_goal / update_goal_status / goal_context_injection / complete_goal
- 存储: `.agent_state.json` 的 goal 字段 + 内存 `_goals` dict(带锁)
- 字段: goal_id/objective/status(active|paused|complete|failed)/plan[]/task_id/started_at/updated_at
- 已接入: bridge_loop 任务开始时 create_goal; write_pending 确认时写 plan
- **缺口**: 无 progress 字段、无独立 Goal 文件、无跨 session 读取、无 goal 事件进 SessionLog

### 1.2 Goal 实体结构(目标态)
```json
{"goal_id": "goal_<uid>_<ts>",
 "description": "完成 X 任务",        // 原 objective 改名, 语义更清
 "status": "active",               // active|paused|complete|failed|aborted
 "progress": {"done": 3, "total": 5, "completed_steps": ["s1","s2"], "pct": 60},
 "created_at": 1720000000, "updated_at": 1720000100,
 "plan": [{"step": "...", "done": false}],
 "session_id": "sess_x", "user_id": "u1",
 "source_turn": 3,                   // 最近推进该 goal 的 turn_id
 "history": [{"ts": ..., "delta": "完成 step2", "turn_id": 4}]}
```

### 1.3 存储位置: 双写(推荐)
| 层 | 位置 | 用途 |
|---|---|---|
| 权威 | `data/projects/{uid}/{sid}/clawsjoy_dev/goals/{goal_id}.json` | 独立 goal 文件, 跨进程可靠 |
| 事件 | SessionLog `goal_event`(新增事件类型) | 审计/回放 goal 生命周期 |
| 缓存 | 现有 `_goals` 内存 dict | 热路径读取 |

理由: 独立文件避免 .agent_state.json 单文件膨胀; SessionLog 事件与 turn 协议一致(goal 是 turn 的上层, 每个 turn_end 可带 goal_id); 内存缓存保持零 IO 读取。

### 1.4 接口(扩展现有)
```python
# 已有(保留签名兼容)
create_goal(user_id, session_id, objective, plan=None, task_id=None) -> dict
get_goal(user_id, session_id) -> dict | None
update_goal_status(user_id, session_id, status, note=None) -> dict

# 新增
update_goal_progress(user_id, session_id, done, total, step=None) -> dict   # progress 更新+落盘+事件
get_goal_by_id(goal_id) -> dict | None                                       # 跨 session 读取
list_goals(user_id, status=None, limit=20) -> list                          # 用户级目标列表
archive_goal(user_id, session_id) -> None                                    # complete 后归档(保留文件)
# 内部
_log_goal_event(session_id, goal_id, action, payload) -> None               # 写 SessionLog goal_event
```

### 1.5 跨轮次/跨 session 读取更新
- **跨轮次**: bridge_loop 每轮从 get_goal() 读取; turn_end 时按 reason 更新 progress(completed→complete, max_tokens→progress 保留 active)
- **跨 session**: goal_id 全局唯一, `get_goal_by_id` 扫 `data/projects/*/*/clawsjoy_dev/goals/*.json`; 供复盘/审计面板
- **恢复**: v9_agent_chat 启动时 goal_context_injection 已注入; 增强为注入 progress 摘要

### 1.6 与 turn 协议的关系
```
goal (长期目标, 跨多轮)                ← 上层
  └─ turn 1 (本轮执行, reason=completed) ← turn 协议
       └─ step 1..N (工具执行)
  └─ turn 2 (继续推进, reason=max_tokens)
turn_end 事件带 goal_id + progress delta → goal 事件聚合出目标生命周期
```

---

## 二、inbox 三通道

### 2.1 概念(映射 Harness inbox)
| 通道 | 语义 | 触发时机 | 是否唤醒 | 去向 |
|---|---|---|---|---|
| followup | 下一 turn 的输入(新任务/追问) | 用户提交新消息 | 是 | 作为下个 turn 的 user 消息 |
| steer | 下一 step 的指导(纠偏/提示), 不开启新 turn | turn 中途需要干预 | 否 | 注入下一轮 LLM 调用的 messages 尾部 |
| inject | 静默附加上下文(系统事实/状态), 不唤醒 | 任意时刻 | 否 | 注入 system 上下文, 不进对话流 |

### 2.2 与现有 messages.append 的替代关系
- **现状**: 所有通道都走 `messages.append(...)` 硬编码在调用点 → 无统一入口、无法区分来源、无法延迟生效
- **目标**: inbox 统一队列, 消费时机显式化:
```python
# 替代散落的 append
inbox.followup(user_id, session_id, content)   # → 下个 turn 首条 user
inbox.steer(user_id, session_id, content)      # → 下个 step 的 LLM 调用前注入
inbox.inject(user_id, session_id, content)     # → system 前缀(不进对话历史)
```

### 2.3 实现(挂到 SessionLog + 内存队列)
```python
# core/gateway/inbox.py(新)
class Inbox:
    def __init__(self): self._q = {}  # (uid:sid) -> {followup: [], steer: [], inject: []}
    def followup(self, uid, sid, content):  # 写 SessionLog EV_USER_MESSAGE + 队列
    def steer(self, uid, sid, content):     # 写 SessionLog EV_RUNTIME_CONTEXT(steer) + 队列
    def inject(self, uid, sid, content):    # 写 SessionLog EV_RUNTIME_CONTEXT(inject) + 队列
    def drain_followup(self, uid, sid) -> list   # 消费: 返回待处理的 followup
    def drain_steer(self, uid, sid) -> list      # 消费: 返回待注入的 steer
    def peek_inject(self, uid, sid) -> str       # 只读: 拼接 inject 上下文

inbox = Inbox()  # 模块级单例
```

### 2.4 bridge_loop 如何消费
```python
# 每轮循环内(LLM 调用前)
_steer_msgs = inbox.drain_steer(user_id, session_id)
if _steer_msgs:
    messages = messages + [{"role": "user", "content": s} for s in _steer_msgs]  # steer 进本轮

# 每 turn 开始(循环前)
_followups = inbox.drain_followup(user_id, session_id)
if _followups:
    messages.insert(0, {"role": "user", "content": _followups[0]})  # followup 作为本轮任务

# system 注入(调用前)
_inj = inbox.peek_inject(user_id, session_id)
if _inj:
    _inject_sys_content(messages, _inj)
```

### 2.5 迁移: 现有 append 点分类
| 现有 append 点 | 应归入通道 |
|---|---|
| 用户新消息(v9_agent_chat) | followup |
| 失败注入'已连续失败5次'(tool_router:52) | steer(下一轮) — **顺带修复 400 断点** |
| 越权拉回提示 | steer |
| 系统事实/项目树注入 | inject |
| 守卫 inject_message | steer |

---

## 三、并行工具池

### 3.1 设计目标
- 模型返回多个 tool_calls 时并行执行(读工具), 提升吞吐
- 写操作保持串行(exclusive barrier), 防竞态
- 结果按模型调用顺序提交, 保证 messages 顺序稳定

### 3.2 maxParallelToolCalls
```python
# execution_policy.yaml 新增
execution_budget:
  max_parallel_tools: 4    # 同轮并行工具上限(默认4, 0=禁用)
  exclusive_tools: ["write_file", "write_large", "edit_file", "execute_command"]  # 写/命令串行
```

### 3.3 执行模型
```python
def _execute_tools_parallel(tool_calls, ctx):
    """同轮工具并行执行, 结果按调用顺序提交"""
    from concurrent.futures import ThreadPoolExecutor
    exclusive = set(ctx.exclusive_tools)
    # 1. 分组: 非 exclusive 可并行, exclusive 串行
    parallel_group = [tc for tc in tool_calls if tc.fn not in exclusive]
    serial_group   = [tc for tc in tool_calls if tc.fn in exclusive]
    results = {}
    with ThreadPoolExecutor(max_workers=min(ctx.max_parallel, len(parallel_group))) as ex:
        futs = {ex.submit(_exec_one, tc, ctx): tc for tc in parallel_group}
        for f in futs: results[futs[f]["id"]] = f.result()
    # 2. 串行组按序执行(barrier)
    for tc in serial_group:
        results[tc["id"]] = _exec_one(tc, ctx)
    # 3. 按模型调用顺序提交结果(稳定顺序)
    ordered = [{"call_id": tc["id"], "result": results[tc["id"]]} for tc in tool_calls]
    return ordered
```

### 3.4 exclusive barrier 语义
- **exclusive 工具**(写/命令): 永不与其他工具并行 — 同一时刻最多 1 个在执行
- 非 exclusive 工具(read_file/list_dir/search_files): 可并行, 上限 max_parallel_tools
- 实现: 简单分组即可(先并行读, 再串行写), 无需信号量; 若需读写交错则用 threading.Lock 包 exclusive

### 3.5 与 guard 的交互(关键)
- **pre-execute guard 仍串行检查**: 所有工具在并行前逐个过 run_pre_guards(顺序执行, 与现状一致)
- 通过检查的非 exclusive 工具才进并行池; 被 deny 的工具直接收集 deny 结果
- **post guard 串行**: 结果提交后逐个 run_post_guards(保持失败计数/审计顺序稳定)
- 审批门(write_pending): exclusive 串行天然满足; 并行组不包含写工具, 无审批竞态

### 3.6 接入 bridge_loop
```python
# 现: for _btc in _btool_calls: 逐个执行+双写
# 改:
_pre_checked = [_exec_guard_pre(tc) for tc in _btool_calls]   # 1. 串行 guard
_ordered = _execute_tools_parallel(_pre_checked, ctx)          # 2. 并行/串行执行
for item in _ordered:                                          # 3. 按序双写+post guard
    log_event(tool_call); log_event(tool_result); run_post_guards(item)
```

---

## 四、优先级与分期

| 阶段 | 内容 | 工作量 | 依赖 |
|---|---|---|---|
| **P0(下一轮)** | inbox 三通道骨架 + failure_pause 注入改走 steer(修 400) + followup 消费 | 中 | 无 |
| **P1** | Goal: progress 字段 + 独立 goals/ 文件 + update_goal_progress + goal_event 进 SessionLog | 中 | P0 inbox? 无 |
| **P2** | Goal 跨 session 读取(list_goals/get_goal_by_id) + 复盘面板 | 中 | P1 |
| **P3** | 并行工具池(max_parallel_tools + exclusive barrier) | 大 | guard 串行检查先验证 |
| **P4** | steer 全量迁移(越权拉回/守卫提示走 inbox) + 移除散落 append | 中 | P0 |

### 推荐实施顺序
1. **P0**: inbox 骨架(3 接口 + SessionLog 事件) + failure_pause 改 steer → 立修 400 断点
2. **P1**: Goal progress/独立文件/事件 → 目标可观测
3. **P3**: 并行工具池(读并行+写串行) → 吞吐
4. **P2/P4**: 跨 session 面板 + 全量迁移

---

## 五、风险与兼容

| 风险 | 缓解 |
|---|---|
| inbox 引入新状态源 | drain 后即清, 不累积; SessionLog 事件可回放 |
| 并行工具结果乱序 | 按模型调用顺序提交(ordered dict) |
| 写并发竞态 | exclusive barrier 串行 |
| goal 文件增长 | 每 goal 一文件, complete 后归档 |
| 旧代码散落 append | P4 渐进迁移, 期间双通道并行 |

## 六、验证

- P0: 连续失败5次后不再 400(回归测试 tool_router:52 改 steer)
- P1: goal progress 随 turn_end 更新, goal_event 可回放
- P3: 4 读工具并行耗时 < 串行 4 倍; 写工具仍串行; guard 检查顺序不变
