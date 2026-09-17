# /clean 清理完整性排查 + 边界建议清单（只读）

> 排查日期: 2026-08-15 | 目标: _clean_session_context（/v9/session/clean + V5 /clean 指令共用）
> 原则: 审计/归档类保留（审计链完整性 + 镜像一致性），运行态清理（会话级内存状态/缓存/计数）

---

## 一、当前已清（4 项）

| 状态 | 存储 | 性质 |
|---|---|---|
| _pending_writes[session_id] | 内存 | 运行态（写审批流） |
| _plan_pending[session_id] | 内存 | 运行态（计划审批流） |
| goal_state._goals[user:session] | 内存 | 运行态（目标生命周期） |
| .task_state.json messages/task_name | 文件快照 | 运行态（上下文恢复） |

## 二、应补清（运行态，8 项）

| # | 状态 | 存储/位置 | 证据 | 清理粒度 |
|---|---|---|---|---|
| 1 | .agent_state.json 的 pending_writes 字段 | 文件 | _persist_pending_writes（agent_gateway L53-78）持久化到 .agent_state.json；当前只清内存，持久化残留会在会话恢复时复活 | 清 pending_writes 字段 |
| 2 | _query_cache[session] | 内存 | sandbox_ops L664 按 _sid setdefault（session 级） | pop 匹配 key（注意 key 可能是 {sid}_{sub_task_id}） |
| 3 | _search_empty_cache[session] | 内存 | sandbox_ops L381/453 按 session_id 计数（熔断） | pop(session_id) |
| 4 | _retry_cache[session] | 内存 | sandbox_ops L673 按 _retry_key（含 session/task） | 清该 session 条目 |
| 5 | _consecutive_reads[session] | 内存 | shared_state L69 per-session 读取配额 | pop(session_id) |
| 6 | _consecutive_lists[session] | 内存 | sandbox_ops L99 per-session list 配额 | pop(session_id) |
| 7 | _consecutive_failures[session] | 内存 | tool_router L31 已有 pop 先例（证明此类计数应随会话清理） | pop(session_id) |
| 8 | subtask_executor._subtasks[session] | 内存 | subtask_executor L21-46 per-session dict | 清 done/failed 条目；running/queued 保留（执行不中断，状态记录保留避免前端丢显示） |

## 三、应保留（归档/审计，3 项）

| # | 状态 | 存储 | 保留理由 |
|---|---|---|---|
| 1 | user_messages JSONL（data/v8/user_messages/{sid}.jsonl + 沙箱镜像） | 文件归档 | 历史对话归档（_archive_user_message 追加）；live↔沙箱双写 + H9 启动回填——清会破坏镜像一致性且被回填重建 |
| 2 | tool_audit.jsonl | 文件审计 | G4 第三方审计，verify_completion_report 复核（H8）依赖 read_audit_records 读它；清会破坏审计链 |
| 3 | tool_flow SAG 记录（DB code_entities entity_type=tool_flow, file_path=tool_flow/{sid}） | DB 审计 | 工具调用审计；DB 删除影响面大 + 审计性质 |

## 四、边界注意

1. _query_cache 的 key: {session_id}_{sub_task_id} 或纯 session_id（sandbox_ops _sid）——清理需按前缀匹配（k == sid or k.startswith(sid + "_")），否则子任务缓存残留
2. subtask running 任务不中断: 线程池继续执行；/clean 只清状态记录，任务产物仍会归档（audit 合格）或保留现场（失败）
3. user_messages 与 .task_state.json 的区别: 前者是归档（审计/回滚用，保留），后者是恢复上下文（已清）——两者语义不同，不要混淆
4. 若未来做"彻底清理"选项（可选参数 clean_all=true）: 可加清 user_messages 该 session 行 + tool_audit 该 session 行，但需前端确认弹窗提示"将删除历史归档，不可恢复"

## 五、建议实施（若采纳）

在 _clean_session_context 追加（约 25 行，全内存操作 + 1 个文件字段）:

1. 运行态缓存/计数（session 级前缀匹配）:
   - 对 _query_cache/_search_empty_cache/_retry_cache: 删除 k == sid 或 k.startswith(sid + "_") 的条目
   - 对 _consecutive_reads/_consecutive_lists/_consecutive_failures: pop(session_id)
2. .agent_state.json: _st.pop("pending_writes", None) 后原子写回
3. subtask 状态: 锁内删除 done/failed 条目（running/queued 保留）
