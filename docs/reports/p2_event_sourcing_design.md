# P2 #4 事件溯源会话日志 — 设计文档

> 日期：2026-08-18 | 状态：设计稿(只设计不实施)
> 依据：v9_pluginization_plan.md P2 方案 + Harness dsh-session(三根柱子之一)
> 目标：把"内存 messages 可变列表"升级为"append-only 事件日志 + derive_messages() 投影", 实现"模型可见=已落盘"不变量

---

## 0. 现状实证

| 项 | 数值 | 说明 |
|---|---|---|
| messages 消费方 | 12+ 文件 | shared_state.messages 全局单例 |
| messages 修改点 | **74 处**(51 bridge + 23 exec) | 6 类追加 + 1 处 `messages[:] = _shared_msgs` 同步 hack |
| 追加类型 | user/system/assistant/tool | 守卫注入/LLM 输出/工具结果/系统提示 |
| 最大问题 | 内存可变 + 无配对 | 无序号/无 turn-step 归属/不可重建/并发靠 hack |

---

## 1. 会话事件日志结构

### 1.1 事件类型(v1 范围)

```python
# core/gateway/session_log.py(设计)
EVENT_TYPES = {
    "session_start":   # 会话开始(用户/时间/种子)
    "turn_start":      # 一轮开始(LLM 调用前)
    "step_start":      # 一步开始(工具组前)
    "user_message":    # 用户/守卫注入消息
    "assistant_message": # LLM 输出(含 tool_calls)
    "tool_call":       # 工具调用(配对 tool_result)
    "tool_result":     # 工具结果(引用 tool_call 序号)
    "runtime_context": # 运行时上下文快照(策略/配额, 变化才写)
    "step_end":        # 一步结束
    "turn_end":        # 一轮结束(completed/max_tokens/error)
    "session_end":     # 会话结束
}
```

### 1.2 事件记录结构

```python
@dataclass
class SessionEvent:
    seq: int                    # 单调递增序号(进程内)
    ts: float                   # 时间戳
    session_id: str             # 会话标识(user:session 或含 sub_task)
    turn_id: int                # 轮次归属
    step_id: int                # 步次归属(0 = 轮次级)
    type: str                   # 事件类型(EVENT_TYPES)
    payload: dict               # 事件内容(不可变, json 可序列化)
```

### 1.3 存储

```python
# 每会话一个 JSONL 文件(append-only, 与 .task_state.json 同目录)
data/projects/{user_id}/{session_id}/session_log.jsonl
# 每行一个事件(JSON), 追加写; 崩溃恢复 = 读全量重放
```

### 1.4 关键约定
- **append-only**:事件只能追加, 不可修改/删除(篡改检测 = 重放校验 seq 单调)
- **模型可见 = 已落盘**:任何进入 LLM 请求的内容必须先 append 事件 → derive_messages() 从日志投影
- **配对**:tool_call 必须带 source_seq 引用, tool_result 带 call_seq(可重建调用-结果对应)
- **轻量**:单进程内存 dict + JSONL 落盘; 不引入 DB(与现有 .task_state.json 模式一致)

---

## 2. derive_messages() 设计

### 2.1 投影规则

```python
def derive_messages(events: List[SessionEvent]) -> List[dict]:
    """从事件日志投影 messages(替代内存可变列表)"""
    messages = []
    for ev in events:
        if ev.type == "user_message":
            messages.append({"role": "user", "content": ev.payload["content"], **ev.payload.get("extra", {})})
        elif ev.type == "assistant_message":
            m = {"role": "assistant", "content": ev.payload.get("content", "")}
            if ev.payload.get("tool_calls"):
                m["tool_calls"] = ev.payload["tool_calls"]
            if ev.payload.get("reasoning_content"):
                m["reasoning_content"] = ev.payload["reasoning_content"]
            messages.append(m)
        elif ev.type == "tool_result":
            # 按 call_seq 定位对应的 assistant tool_call
            messages.append({"role": "tool", "tool_call_id": ev.payload["call_id"],
                             "content": ev.payload["content"]})
        # 其他事件(step/turn/context)不投影为 message
    return messages
```

### 2.2 增量投影(性能)

```python
class SessionLog:
    """事件日志 + 派生消息(增量)"""
    def __init__(self, session_id, log_file=None):
        self.session_id = session_id
        self._events: List[SessionEvent] = []   # 内存(进程内事实源)
        self._last_derived_seq = 0              # 增量投影游标
        self._messages_cache: List[dict] = []   # 已投影消息缓存
        self._seq = 0
        self._load()                            # 崩溃恢复: 读 JSONL 重放

    def append(self, type_, payload, turn_id=0, step_id=0) -> SessionEvent:
        """追加事件: 内存 + 落盘(append-only)"""
        self._seq += 1
        ev = SessionEvent(seq=self._seq, ts=time.time(), session_id=self.session_id,
                          turn_id=turn_id, step_id=step_id, type=type_, payload=payload)
        self._events.append(ev)
        self._flush_one(ev)                     # 追加写 JSONL
        self._incrementally_derive(ev)          # 增量投影到消息缓存
        return ev

    def _incrementally_derive(self, ev):
        """只投影新事件(性能: 每轮 O(1), 不重扫全日志)"""
        if ev.type in ("user_message", "assistant_message", "tool_result"):
            self._messages_cache.append(self._to_message(ev))

    def derive_messages(self) -> List[dict]:
        """返回完整消息投影(可含截断/摘要标记)"""
        return list(self._messages_cache)

    def _to_message(self, ev): ...
```

### 2.3 与守卫注入的对接

```python
# 现状: messages.append({"role": "system", "content": "..."})
# 改为: session_log.append("user_message", {"content": "..."}, turn_id, step_id)
# (守卫注入的 system 消息在事件层记为 user_message + 来源标记, 投影时带 role)
```

---

## 3. 迁移范围与渐进策略

### 3.1 shared_state.messages 12+ 消费方

| 消费方 | 用途 | 迁移 |
|---|---|---|
| `execute_agent_task`(23 修改点) | LLM 循环/守卫注入/工具结果 | 核心改造(见 §4) |
| `agent_gateway_enhanced`(51 修改点) | bridge_loop 消息管理 | 核心改造 |
| `tool_router`/read_file/write_file 等 | 读取 messages 判定模式 | 改 `session_log.derive_messages()` |
| `sandbox_ops`/execute_command | 读 last user msg | 改投影 |

### 3.2 渐进三阶段(每阶段可独立提交/回滚)

```
P2a 日志骨架: 建 SessionLog 类 + 事件写入点(append 落盘), messages 仍内存(双写)
P2b 切换读取: derive_messages() 成为唯一读取入口, messages 从日志投影
P2c 删内存:   messages 单例移除, 全量改 session_log(12+ 消费方)
```

---

## 4. 分期实施方案

### P2a:日志骨架(双写, 行为零变化)

| 步骤 | 内容 |
|---|---|
| 1 | 新建 `core/gateway/session_log.py`: SessionLog 类 + 事件类型 + JSONL 落盘 |
| 2 | `shared_state` 增加 `_session_logs: Dict[str, SessionLog]` + `get_session_log(session_id)` |
| 3 | execute_agent_task 工具循环: tool_call/tool_result/assistant_message 写入点追加日志(保留 messages 双写) |
| 4 | 测试: 日志文件生成、事件序号单调、重放恢复 |

**验证**:全量 369 不降;日志文件存在且事件完整。

### P2b:切换读取(derive 为唯一入口)

| 步骤 | 内容 |
|---|---|
| 1 | execute_agent_task 循环内 `messages = session_log.derive_messages()` 替代传入的 messages 引用 |
| 2 | bridge_loop 同理: 每轮从日志投影(替代 `_bmsg` 手工拼接) |
| 3 | 守卫/工具经 `session_log.derive_messages()` 读(替代 shared_state.messages) |
| 4 | `messages[:] = _shared_msgs` hack 删除(投影天然一致) |
| 5 | 测试: 投影与双写 messages 逐事件对比一致; 模型可见=已落盘断言 |

**验证**:投影一致性测试(事件→messages 全等);并发子任务无串扰。

### P2c:删内存(12+ 消费方收尾)

| 步骤 | 内容 |
|---|---|
| 1 | `shared_state.messages` 全局单例移除 |
| 2 | 74 处修改点全部改 `session_log.append` / `derive_messages` |
| 3 | 残留消费方逐个迁移(工具/守卫/审计) |
| 4 | 全量回归 + 重放一致性(会话恢复 = 日志重放 = 消息完整) |

---

## 5. 写入点清单(74 处分类)

| 事件类型 | 触发位置 | 数量 |
|---|---|---|
| `turn_start` | execute_agent_task 循环开始 / bridge_loop 每轮前 | 2 |
| `assistant_message` | LLM 响应后(含 tool_calls) | 2(exec+bridge) |
| `tool_call` | 每工具调用前 | ~30 |
| `tool_result` | 工具返回后 | ~30 |
| `user_message`(守卫注入) | 递归暂停/审计复核/验证失败/提醒等 | ~10 |
| `runtime_context` | 策略/配额变化时(可选) | 0(预留) |
| `step_start/end` | 工具组边界 | 2 |

**替换映射**:
```python
messages.append({"role": "assistant", ...})  →  log.append("assistant_message", {...})
messages.append({"role": "tool", ...})        →  log.append("tool_result", {...})
messages.append({"role": "system", ...})      →  log.append("user_message", {"content": ..., "source": "guard"})
```

---

## 6. 风险与缓解

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| 1 | **74 处修改点改造回归**(P2c) | 高 | 三阶段渐进; P2b 投影一致性测试兜底; 每阶段独立回滚 |
| 2 | **性能**: 每事件 JSONL 落盘 IO | 中 | 增量投影 O(1); 批量 flush(每轮一次而非每事件); 可选内存优先+异步落盘 |
| 3 | **日志膨胀**: 长任务事件多 | 中 | 可选压缩(turn 级摘要, Harness compaction 模式); 保留原始日志可回溯 |
| 4 | **守卫注入时序**: 注入消息须在正确 turn/step 归属 | 中 | SessionLog 记录当前 turn/step 游标; 注入自动带归属 |
| 5 | **`messages[:] = _shared_msgs` hack**: 工具层改共享 dict | 高 | P2b 投影一致后此 hack 自然失效删除 |
| 6 | **并发**: 多线程同一 session 写日志 | 中 | per-session 文件锁(fcntl, 与 .agent_state.json 同模式) |
| 7 | **tool_calls 配对**: 投影需保持 assistant→tool 顺序 | 中 | 事件带 call_seq; derive 按 seq 有序投影 |

---

## 7. 收益(对齐 Harness 三根柱子)

1. **可重建**: 会话恢复 = 日志重放 = 消息完整(崩溃/重启不丢)
2. **可审计**: 工具调用/结果/守卫注入全部有序号可追溯(对齐 agent_actions)
3. **KV 缓存友好**: 投影稳定 → LLM 请求前缀稳定(与 Harness KV cache 优化一致)
4. **并发隔离**: per-session 日志替代全局 messages 单例 → 根治 `_shared_msgs` hack
5. **回放测试**: P2 #7 LLM 端到端回放的前置(事件日志是回放输入)

---

## 8. 里程碑

| 阶段 | 内容 | 预计 |
|---|---|---|
| **P2a** | SessionLog + 写入点(双写) | 1-2 天 |
| **P2b** | derive_messages 切换读取 + hack 删除 | 2-3 天 |
| **P2c** | 删 messages 单例 + 消费方收尾 | 2-3 天 |
| **P2 #7** | LLM 端到端回放(依赖事件溯源) | 后续 |

> 设计原则: 三阶段渐进, 每阶段可独立提交/回滚; P2a 行为零变化(双写), P2b 验证投影一致后再 P2c 删内存。与 Harness dsh-session 对齐: 事件是唯一事实来源, 消息是派生视图。
