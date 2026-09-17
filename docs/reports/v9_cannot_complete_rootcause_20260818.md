# V9 无法完成任务 退步根因报告

- 日期: 2026-08-18
- 方式: 只读排查(不改代码)
- 证据源: live session_log (71 事件) + 代码路径逐段核对 + 工具调用时间线

---

## 一、结论速览

| # | 现象 | 根因 | 类别 |
|---|---|---|---|
| 1 | 之前能完成(hello.txt 11.2s 闭环), 现在 15/16 说无法完成 | 8轮自然耗尽后 bridge_exhausted=True + 最后 assistant 残留未执行 tool_calls, 前端 stale messages continue 死循环 | 前端-后端契约断裂 |
| 2 | 一半步骤花在 sleep 轮询 pytest | pytest 30s 超时(工具层) + agent 改 nohup 后台+轮询, 但 bridge 每次只给 execute_command | 任务策略 + 工具超时 |
| 3 | 最终无评估报告 | 工具预算被轮询耗尽, 从未走到报告写入 | 预算分配 |

---

## 二、执行时间线实证(71 事件)

### 第一段(seq 3-32): bridge_loop 第 1 次调用
```
[3] ASSIST tc=2 (list_dir, execute_command)
[4-7] list_dir + git log 执行成功 (git log 结果 2000 截断)
[8-12] ASSIST tc=2 (execute_command, list_dir) <- 重复执行
[13-17] ASSIST tc=2 (execute_command, read_file AUDIT_REPORT.md)
[18-22] ASSIST tc=2 (cd /root pytest 失败; ls data/v8)
[23-25] ASSIST tc=1 (pwd; pytest --collect-only)
[26-28] ASSIST tc=1 (pytest -q) -> 30s 超时 success=False
[29-31] ASSIST tc=1 (timeout 280 pytest) -> 30s 超时 success=False
[32] ASSIST tc=1 (execute_command) <- 8轮耗尽, 未执行, 残留 tool_calls
```
**第一段工具数: 11 个**(未达 16 上限), 8 轮**自然耗尽** → `_bridge_exhausted=True`(初始值)

### 关键断层: seq32 -> seq34 间隔 +1439.2 秒(24 分钟)
```
[33] USER: '👤 检查项目状态...' <- 前端 agentSend 重发(带 👤 前缀)
[34+] ASSIST tc=2 (execute_command x2) ... 又 7 轮, 15 个 execute_command
[57-71] 轮询 logs/test_run_*.log (nohup pytest 后台) + git log + sleep 30
```

---

## 三、根因链(逐条对照排查方向)

### 排查1: P2b 投影让它忘事? 结论: 不是主因, 但加重
- session_log 完整(71 事件全在), derive_messages 不丢历史。
- 但 P2b 切换后: bridge_loop 每轮从日志重建 messages, **前端的 messages 数组(含本轮 tool results)与后端投影不同步**。
- 第 8 轮自然耗尽时, 最后 assistant(seq32) 的 execute_command **没有 tool_result**(P2b 修复只过滤投影, 但**前端拿到的 done payload 里 msg.tool_calls 仍在**)。

### 排查2: guard 消费(P0-2)过度干扰? 结论: 不是
- 本 run 无 GUARD_PAUSE/GUARD_INJECT 触发(日志 0 次), 无 write_pending/plan_pending。
- guard 消费只在失败计数 ≥5/8 时介入, 本 run 未达到。

### 排查3: sleep 轮询是否因没收到工具结果才反复查? 结论: 是, 但根源在工具超时
- pytest 全量 >30s, execute_command 工具层 30s 先超时(即使 LLM 包 timeout 280)。
- agent 改用 `nohup pytest &` 后台 + `sleep 20/30 + tail logs` 轮询 —— 每次轮询就是一个 execute_command, 烧掉预算。
- 工具结果实际是成功的(success=True), 但 pytest 输出在后台日志里, 需要多轮 tail 才看到 —— LLM 反复 tail 是因为**每次 tail 结果被 2000 截断或输出不完整**。

### 排查4: E2E vs 当前路径差异 —— 核心发现

| 维度 | E2E 受控任务(11.2s 成功) | 自由任务(检查项目状态, 失败) |
|---|---|---|
| 工具数 | 2-3 个(write_file + read_file) | 26 个(23 execute_command) |
| 轮次 | 1-2 轮 | 8轮耗尽 + 再 8 轮 |
| 审批 | 有 write_pending 卡(老板确认) | 无审批, 全 execute_command |
| 终止 | 正常 break(msg 无 tool_calls) | **8轮自然耗尽, 最后残留 tool_calls** |
| 预算 | 远低于 16 | 两段共 26, 第一段 11 未触发 TOOL_BUDGET |
| 前端 | done 后正常 | **continue 分支(stale messages 死循环)** |

**核心契约断裂**: bridge_loop 8 轮自然耗尽时返回 `_bridge_exhausted=True`, 前端看到后本应 `break`(line 1560), 但 **SSE done payload 的 `data.choices[0].message` 是最后一条 assistant(带 tool_calls)**, 前端先命中 line 1565 的 `continue` 分支(因 `d.tool_steps 非空 && msg.tool_calls 非空`), 用**未更新的 stale messages** 继续 POST → 重复执行/死循环。

---

## 四、根因优先级

### P0(直接致败): 前端 continue 分支在 bridge_exhausted 场景误触发
- done payload 同时带 `bridge_exhausted=true` 和 `msg.tool_calls 非空` 时, 前端应先检查 `bridge_exhausted` 再检查残留 tool_calls。
- 当前顺序: line 1560 bridge_exhausted 检查在 line 1565 continue 之前, 但 **line 1565 的 continue 在 SSE done payload 路径里没经过 line 1560** —— readSSEStream 的 done 事件处理(line 437)只打日志不 break, 返回后 runAgentLoop 才检查。

### P1: 工具超时与预算
- pytest >30s: tool_timeout_ms 已配置化(30000), 但 agent 不知道可调; 建议失败后引导 agent 用 `timeout 280` 或调大配置。
- 26 工具中 23 个 execute_command, 大量重复 tail/sleep —— 缺'已完成操作去重'引导。

### P2: 结果截断
- git log/read_file 结果 2000 截断(已修复加标记+头尾), 但 live 本 run 是修复前产生的。

---

## 五、修复方案建议

1. **(P0) 前端 runAgentLoop/agentSend: done payload 先判 bridge_exhausted 再判残留 tool_calls**
   - `if (d.bridge_exhausted) { break; }` 提到 `continue` 之前, 且 SSE done 事件(line 437)也应 break。
   - 或后端: 8轮自然耗尽时, 把最后一条 assistant 的 tool_calls 清空/或返回明确 done。
2. **(P1) 后端: 8轮耗尽时若最后有未执行 tool_calls, 主动注入'已达到轮次上限, 请基于现有信息汇报结论'**
   - 让 LLM 收敛而非继续轮询。
3. **(P1) pytest 超时策略**: 失败后引导 agent 调大 tool_timeout_ms 或分文件跑, 而不是 nohup+轮询。
4. **(P2) 前端 messages 同步**: continue 前用服务端 tool_steps 更新 messages, 或直接交给后端投影。

所有修复不改数据存储结构。
