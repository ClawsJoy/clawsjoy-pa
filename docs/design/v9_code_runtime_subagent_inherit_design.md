# V9 设计 — #3 Code Runtime 隔离 + #4 子代理上下文继承

- 日期: 2026-08-19
- 状态: 设计确认稿(待评审后实施)
- 现状基线:
  - execute_command: P1-2 超时已配置化(tool_timeout_ms); 危险命令守卫已接(_check_sandbox_read + EscapeGuard);
    缺 stdout/stderr 大小限制(命令 dump 大输出会爆上下文)
  - subtask_executor._run: 独立沙箱 subtasks/{task_id} + 独立会话 key {parent_sid}_{task_id}(_execute_agent_task L411);
    _write_exec_turn_end 已按 session 关联 goal, 但子会话查不到父 goal → 无关联

---

## 一、#3 Code Runtime 隔离(轻量)

### 1.1 现状盘点
| 能力 | 状态 |
|---|---|
| 超时 | ✅ P1-2: execution_policy.tool_timeout_ms 配置化(默认 30s) |
| 危险命令预检 | ✅ _check_sandbox_read + EscapeGuard(G3 高危命令/路径) |
| stdout/stderr 大小限制 | ❌ 缺失 — 命令输出原样回传, 大输出爆上下文 |
| 完整 worker 隔离 | ⏸ 明确不做(重, P3 后) |

### 1.2 新增: 输出大小限制(核心)
- **共享 helper** `_truncate_cmd_output(text, limit) -> str`(放 core/tools/execute_command.py 或 gateway_helpers):
  - text ≤ limit → 原样
  - 超限 → 保留头尾各一半 + `...[TRUNCATED] 原文 N 字符(超限 M)` 标记(与 P0-1 tool_result 截断同风格)
- **接入点**(execute_command.py):
  - 普通分支: `_stdout = _truncate_cmd_output(result.stdout, 8000)`; `stderr = _truncate_cmd_output(result.stderr, 4000)`
  - heredoc 分支: 同样截断 _res_h.stdout/stderr(该分支还有 SAG 追加, 截断在追加后)
  - 超时分支: 已是固定引导文案, 无需截断
- 尺寸常量集中: `_CMD_STDOUT_LIMIT = 8000`, `_CMD_STDERR_LIMIT = 4000`(可配置 execution_policy?)
  → 设计倾向: 先硬编码模块常量, 后续再配置化(最小变更)

### 1.3 边界
- 截断只影响返回给 LLM 的内容, 不落盘命令原始输出(无审计损失)
- 下游 P0-1 tool_result 截断(2000)仍生效, 双保险

---

## 二、#4 子代理上下文继承

### 2.1 现状
- subtask_executor._run 调 _execute_agent_task, 子任务会话 key = `{parent_sid}_{task_id}`(独立, 安全隔离 ✓)
- _write_exec_turn_end 按 _sid 找 goal → 子会话查无 → 子任务 turn_end 不关联任何 goal

### 2.2 设计: 继承父 goal_id + 简要上下文(不继承完整 messages)
1. **subtask_executor._run 入口**(_execute_agent_task 调用前):
   ```python
   _parent_goal = get_goal_by_session_id(session_id)   # 父任务 goal(父 bridge 已 create_goal)
   _parent_goal_id = _parent_goal.get("goal_id") if _parent_goal else None
   if _parent_goal:
       _inherit_ctx = f"[系统] 继承父任务目标：{str(_parent_goal.get('objective',''))[:200]}（goal_id={_parent_goal_id}）。请围绕该目标完成子任务。"
       messages.append({"role": "system", "content": _inherit_ctx})   # 仅 200 字摘要, 不传完整 messages
   ```
2. **_execute_agent_task 新增可选参 `parent_goal_id=None`**; _write_exec_turn_end 的 goal 关联:
   ```python
   _g_e = get_goal_by_session_id(_sid)
   if _g_e is None and parent_goal_id:
       _g_e = get_goal_by_id(parent_goal_id)   # 回退到父 goal
   # 更新走 goal 自带 user_id/session_id(父会话) → 父 goal 进度推进 + 事件落父会话日志
   ```
3. **子任务 turn_end 关联父 goal**: 现有 _write_exec_turn_end 的 progress_delta/complete_goal 逻辑复用 —
   _g_e 命中父 goal 后, update_goal_progress(父 user/session, ...) + reason=completed → complete_goal(父)
   → 事件带 goal_id + progress_delta ✓

### 2.3 隔离保障
- 不继承完整 messages(只注入 200 字目标摘要 + goal_id)
- 子任务仍独立会话 key(事件日志/审计隔离)
- 父 goal 无则静默跳过(子任务独立执行, 不报错)

---

## 三、实施清单(确认后执行)
1. execute_command.py: _truncate_cmd_output + 普通/heredoc 分支接入(模块常量限长)
2. execute_agent_task.py: _execute_agent_task 加 parent_goal_id 参; _write_exec_turn_end 回退 get_goal_by_id
3. subtask_executor.py: _run 入口查父 goal → 注入 200 字摘要 system 消息 + 传 parent_goal_id
4. 测试:
   - #3: 命令超长输出 → stdout/stderr 截断带标记; 短输出原样; heredoc 分支同样截断
   - #4: 父 goal 存在 → 子任务 messages 含继承摘要(≤200 字); _write_exec_turn_end 回退父 goal
     → 事件带父 goal_id + progress 推进; 父无 goal → 静默跳过(不报错)
   - 全量回归
5. 实机冒烟: 子任务带继承上下文执行; execute_command 大输出截断

## 四、验证
- #3: execute_command 输出 >8KB → 返回内容含 [TRUNCATED] 标记且 ≤ 限长; 短输出不变
- #4: 有父 goal 的子任务 turn_end 事件含父 goal_id + progress_delta; 无父 goal 时行为与现状一致
