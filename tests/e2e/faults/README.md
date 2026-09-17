# failure injection 清单（15 条）

纪律：**先能失败，再能通过**。每条都必须先证明「这个故障真的能被注入并观测到」，
再证明「系统把它带到 FAILED / RETRYING / NEEDS_REVIEW / CANCELLED 之一，而不是停在 Thinking」。

来源：《Codex机制移植P0_20260913.md》§七。本目录是它的可执行版本。

## 状态图例
- ✅ 已实现（有测试，本目录）
- 🟡 部分（已有等价断言在别处，但没按 fault 形态固化）
- ⬜ 未实现（已设计，见下表「注入手段」）

| # | 故障 | 状态 | 测试 / 位置 | 注入手段 | 期望状态 | 断言 |
|---|---|---|---|---|---|---|
| 1 | tool timeout | ⬜ | —— | monkeypatch `exec_tool_fn` 睡 >tool_timeout_ms | FAILED / RETRYING | 回执出现 timed_out，且不无限等 |
| 2 | malformed result | ⬜ | —— | `exec_tool_fn` 返回非 dict（如 None / str） | NEEDS_REVIEW | 不得抛未捕获异常；该步标失败 |
| 3 | SSE error | ✅ | `test_fault_backend_error_propagation.py` | 桥接函数抛异常 | FAILED | 流里出现 `type:"error"` + 原文 + `[DONE]` |
| 4 | model stops early | ⬜ | —— | 桥接返回空 content 且无 tool_calls 两次 | NEEDS_REVIEW | `reason=need_more`，不是静默成功 |
| 5 | output truncated | ✅ | `test_fault_truncated_output.py` | 源码契约 + 全仓遮蔽扫描 | 不崩 | `finish_reason=length` 分支无 UnboundLocalError |
| 6 | artifact missing | ✅ | `test_fault_artifact_placeholder.py` | 产物路径不存在 | FAILED | `verify_artifact` 判「产物不存在」 |
| 7 | **宣称 P1–P14 却缺 P11–P13** | ✅ | `test_fault_fake_completion.py` | agent 报告 + 68 字节占位产物 | RETRYING | 完成闸门返回 `verification_retry`，不落 completed |
| 8 | external tool unavailable | ⬜ | —— | `exec_tool_fn` 对 lingxi/ds_chat 直接 raise | NEEDS_REVIEW | 标「外部求助未果」并上报，不闷头硬试 |
| 9 | context compaction | ⬜ | —— | 构造超阈值 messages 触发 `rebuild_context` | 状态不丢 | 压缩后未完成步骤仍被认作未完成（unknown ≠ pending） |
| 10 | duplicate tool calls | 🟡 | `tests/unit/test_l4_output_policy.py`、`test_write_then_read_consistency.py` | 同参重复调用读类工具 | 去重命中 | 第二次命中缓存不重复执行 |
| 11 | turn silent for N 秒 | ✅ | `tests/unit/test_turn_lifecycle.py` | 桥接函数永久 sleep | CANCELLED | 超时 → `type:error(timeout:true)` + `[DONE]` + 置取消标志 |
| 12 | 写后读旧快照 | ✅ | `test_write_then_read_consistency.py` | 写成功后立即读同文件 | 读到新版本 | 缓存失效；命中带 `_cached_at` |
| 13 | 审批门重放 | ⬜ | —— | 对同一 `pending_id` 连续 approve 两次 | 幂等 | 第二次不得重复执行写入 |
| 14 | 重复事件刷屏 | 🟡 | 浏览器实测（`/tmp/fe_check.py`） | 连打 12 条交替 `addLog` | UI 折叠 | DOM 只剩 2 行 ×6；未固化为 pytest |
| 15 | **预算耗尽 → 回「继续」→ 任务链断（no_context）** | ✅ | `test_fault_budget_resume_no_context.py` | 假 adapter 打爆 token 预算触发预算收尾；再发「继续」 | 续跑 | 模型实际收到的 messages 含任务原文；`.agent_state.json` 有 last_task 且 BRIEF.md 存在；`inject_context_and_flags` 不返回 `no_context` |

**总计：7 条 ✅ / 2 条 🟡 / 6 条 ⬜**

## #15 备注（第三次同型：修好的东西在主路径上接不上）
1) `core/gateway/v9_chat/recovery.py` 的「继续」分支只查 BRIEF.md / `.agent_state.json` 的 `last_task` 两个源，两个都空就当场 `no_context`（当时的唯一产生点）；
2) BRIEF.md 只在 `execute_agent_task.py` 生成，PA 走 `/v9/agent/chat`，从不调用它；
3) `last_task` 的两个写入点在预算耗尽轮被 `_budget_limit_guard` 早退全部跳过；
4) 恢复层注入的上下文会被轮首 `rebuild_context` 的 derive 重建冲掉，且 derive 的任务边界会落在「继续」上、把任务原文整段切掉。

## 未实现 6 条的原因（诚实记录）
1/2/8/13 需要能替换 `exec_tool_fn` 的注入点 —— 它在 `_run_exec_phase` 内以参数传入，
单元级可注入，但要让「回执里出现 timed_out / status」成立，得先做 P0 表的 Q1 头号条目
（`tool_runner.py:_run_item` 外包 timeout + 回执补 `timed_out/exit_code`）—— **先有字段，才能断言**。
9 需要可构造的 compaction 场景 + 「unknown ≠ pending」的动作回执表（P0 表 Q2 新增行），
否则断言没有落点。4 需先确定「两次空回复」的终态定义。

## 与「防退化」的关系
本目录的每一条都是**回归护栏**：这批修过的 4 个真 bug（长输出崩溃 / SSE 吞错误 /
write_note 掉段 / 写后读旧快照）全部有对应条目，任何人碰到它们都会立刻红灯。
