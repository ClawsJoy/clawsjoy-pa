# V9 多线程（6501/3379）Agent 协作问题 — BUG 排查报告

**日期**: 2026-08-24
**现象**: ①两个线程 Agent 任务边界混乱（3379 在执行 6501 的任务）②write_file 审批重复触发 ③小红书发布 UI 卡死

---

## 一、已实证的核心 BUG（代码级，可复现）

### BUG-1【严重】审批确认后，写入内容被截断为 500 字符

**位置**: `core/gateway/guards/registry.py` ApprovalGuard（L244）+ `agent_gateway_enhanced.py` `_resume_bridge_after_approval`（L2203-2205）

**链路**:
1. Agent 发起 write_file(content=几千字符的 SOP/笔记)
2. ApprovalGuard 拦截 → 只保存 `content_preview = content[:500]`（500 字符截断）
3. 老板确认 → `_resume_bridge_after_approval` 用 `pending.get('content_preview')` 作为 content 重新执行写入
4. **实际写入的文件只有前 500 字符！** 长文档被静默截断

**实证**（已运行验证脚本）:
```
guard status: write_pending
pending_write.content_preview 长度: 500
确认后实际写入的 content 长度: 500   ← 原始 2400 字符 → 只写 500!
```

**后果**: 3379/6501 线程写 `client-startup-sop.md`、`note1.md` 等文档时，确认后文件不完整 → Agent 检查发现内容缺失 → 再次 write_file 同一路径 → **再次触发审批** → 用户看到“write_file 审批重复”无限循环！

### BUG-2【严重】edit_file / write_large 未注册却被当写工具审批

**位置**: `core/gateway/tool_router.py` `_TOOL_REGISTRY`（L130-141） vs `core/gateway/guards/registry.py` `_WRITE_TOOLS`

**实证**:
```
write_file -> registered
edit_file -> MISSING   ← 但 ApprovalGuard/EscapeGuard/PlanGuard 都拦截它
write_large -> MISSING ← 同上
```

**后果**: 若 Agent 调用 edit_file → 审批拦截 write_pending → 确认后 `_resume_bridge_after_approval` 执行 `_exec_wa('edit_file', ...)` → **返回“未知工具”**！且该函数只重建 path/content_preview/command 三个参数，**edit_file 的 `edits` 数组参数完全丢失** → 确认后执行必然失败。

### BUG-3【中】确认后参数重建丢失原始 tool_call 上下文

`_resume_bridge_after_approval` 从 pending 反查不到完整参数，注释也承认（L2200“从 pending 反查不到原始完整参数”）。
**已验证修复路径可行**: messages 中 assistant tool_calls 保留了完整 arguments（3000 字符），按 tool_call_id 反查可恢复完整 content（3000），无需依赖截断的 content_preview。

---

## 二、线程串扰（3379 执行 6501 的任务）— 非代码 bug，是任务设计+状态隔离问题

从日志看：
- 6501 线程：小红书完整工作流（写 note、xhs_cover、发布 SOP）
NaN
NaN

**根因**: 两个线程共用了同一个 user_id（`web_1783219071801`），且 3379 的会话上下文恢复（.task_state.json 快照）加载到了 6501 的任务消息 → 3379 以为自己在继续 6501 的工作。

`_pending_writes` 本身按 session_id 隔离（正确），但 **.task_state.json 快照恢复按 user_id 而非 session_id 隔离** —— 需要确认。

---

## 三、修复方案

### 修复 1（BUG-1+BUG-3 一起治）：确认后从 messages 反查完整参数
`_resume_bridge_after_approval` 增加一步：
```python
# 在构造 _bargs_wa 之前，先从 messages 反查完整 tool_call
for _m in messages:
    for _tc in (_m.get('tool_calls') or []):
        if _tc.get('id') == pending.get('id'):
            try:
                _bargs_wa = json.loads(_tc['function']['arguments'])
            except Exception:
                pass
            break
```
找不到时再 fallback 到当前 content_preview 逻辑。

### 修复 2（BUG-2）：_WRITE_TOOLS 与实际注册表对齐
- 若 edit_file/write_large 是遗留死工具 → 从三个 Guard 的 `_WRITE_TOOLS` 移除
- 若需要保留 → 在 `_TOOL_REGISTRY` 注册对应插件（需实现）

### 修复 3：线程串扰
- 确认 .task_state.json 快照按 (user_id, session_id) 双 key 隔离
- SOP 中明确：一个线程只做自己的任务，不操作另一线程的客户端进程（pkill/kill agent_client 禁止跨线程）

---

## 四、待确认项
- .task_state.json 快照恢复是否按 session_id 隔离（现场在 live 端，需要用户在 live 目录确认）
- 前端审批卡片展示用哪个字段（content_preview 还是完整 content）
---

## 五、BUG-3 后端兜底（已实施 2026-08-24）

### 新增: _resolve_v9_session_id(user_id, raw_session_id)

**位置**: agent_gateway_enhanced.py L153（模块顶层, _PROJECT_ROOT 之后）

**逻辑**:
- raw_session_id 非空且非 'default' → 原样返回（尊重前端显式会话）
- 缺省(''/"default") → 按 user_id 分配/复用稳定唯一 id（`v9auto_{uuid12}`，存 `data/projects/{uid}/.v9_default_session.json`）
- 同 user 缺省请求复用同一 id（会话稳定，跨请求上下文连续）
- 不同 user 天然隔离（不同映射文件）

**替换 7 处**: /v9/agent/chat、/v9/task/save_progress、/v9/task/status、/v9/sandbox/{checkpoint,rollback,list}

### 附带修复: pending_writes 双重序列化容错

**实证**: live 端 `.agent_state.json` 的 pending_writes 是**字符串化的 JSON**（旧版代码 bug）→ `_v9_restore_pending_writes` 的 `.get()` 抛异常被吞 → 审批状态永远恢复不了 → Agent 重提写入 → 重复审批卡片。

**修复**:
- `_v9_restore_pending_writes`：str 先 json.loads 解析回 dict 再 .get(session_id)
- `_persist_pending_writes`：读取时若 pending_writes 为 str 先解析再合并

**验证**: live 真实遗留数据（str pending）可正确恢复 ✅

### 新测试: tests/unit/test_v9_default_session.py（3 项）
- 缺省 session 自动分配稳定唯一 id（同 user 复用、非 default、显式尊重）
- 不同 user 缺省 → 不同 id（互不串扰）
- pending_writes 双重序列化 → 恢复容错不崩溃

### 回归: 573 passed, 0 failed ✅

### 待同步到线上（重启网关后生效）
- `agent_gateway_enhanced.py`（本次全部改动）
- `tests/unit/test_v9_default_session.py`

> 注意: live 端已存在的 `.agent_state.json` 中 str pending 会在新代码首次读取时自动解析修复；
> 两个线程若前端仍显式传同一 session_id，后端会尊重（无法区分）——根治需前端线程创建独立 session_id。
