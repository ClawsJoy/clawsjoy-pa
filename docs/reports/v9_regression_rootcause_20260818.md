# V9 重复执行 / 步骤错乱 / pytest 超时重试 / cd /root 环境感知 — 根因排查报告

- 日期: 2026-08-18
- 方式: 只读排查(不改代码), 基于 live session_log 事件流 + 代码路径逐段核对
- 证据源: /home/<user>/clawsjoy_v5/data/session_logs/session_1783388196051.jsonl (32 事件)

---

## 一、结论速览

| # | 问题 | 根因 | 严重度 |
|---|---|---|---|
| 1 | list_dir/git log 重复执行 | tool_result 2000字符硬截断(无标记) 导致 LLM 看到残缺输出重跑; 桥接路径无已完成去重引导 | 高 |
| 2 | 步骤计数 2/8-4/16-12/16 错乱 | total_steps 两处硬编码不一致(8 vs 16) | 中 |
| 3 | pytest 超时后盲目重试 | 工具层 timeout=30 先于 timeout 280 包装; failure_pause_guard 提示从未注入 LLM | 高 |
| 4 | cd /root 环境感知错误 | 系统提示声明 cwd=项目根, 但 LLM 仍用绝对路径 /root; 沙箱 cwd 无 /root | 低-中 |

---

## 二、问题1: 重复执行同一批命令 (list_dir/git log 两遍)

### 实证 (live session_log)

[3] assistant tc=['list_dir', 'execute_command']      <- 第0轮
[4-5] list_dir 执行成功 (len=791)
[6-7] execute_command(git log) 成功 (len=2000)  <-- 硬截断!
[8] assistant tc=['execute_command', 'list_dir']      <- 第1轮 重复!
[9-12] 又执行一遍

### 根因链

1. tool_result 2000 字符硬截断: log_event(tool_result, content=json.dumps(_btr)[:2000]) (agent_gateway_enhanced.py:2020 · 2026-08-18 之面 · 今漂)。seq=7 的 git log 结果正好 2000 字符, 截断在 Untracked files 中间, 无任何截断标记。
2. LLM 看到残缺的 git 输出(看不到完整历史/状态) - 认为信息不足 - 下一轮重新执行 git log/list_dir。
3. 桥接路径缺少已完成操作去重引导: 注入逻辑只在 v9_agent_chat 的 _session_artifacts 分支(3452-3459), 且依赖 _session_artifacts 非空; bridge_loop 每轮 derive_messages 重建后历史完整但 tool_result 内容残缺 - 重跑。
4. 前端 seenRounds 去重仅限单次 SSE 流内(key=round:tool:arg[:40]), 跨请求(审批恢复/续跑)时 round 重置, 同工具再次渲染 - 加剧观感。

### 修复方向

- tool_result 截断处补标记: 尾部追加 ...[截断, 原文 N 字符] + 保留 head+tail 各一段(如 git log 头尾都要)。
- bridge_loop 每轮注入一次性系统提示: 基于本会话 tool_steps 去重, 明确已执行工具清单勿重复。

---

## 三、问题2: 步骤计数 2/8 - 4/16 - 12/16 错乱

### 根因: total_steps 两处定义不一致

# bridge_loop 内部 (line 1896) - 被 write_pending/plan_pending/escalation 返回使用
def _ts_progress():
    return {..., 'total_steps': _max_total_tools}   # =16

# stream wrapper (line 3688) + _stream_on_round(3720) + done(3766) + jsonify(3784)
'progress': {..., 'total_steps': 8}              # 硬编码 8 (旧8轮上限)

### 前端渲染 (workbench.html:1985 · 2026-08-18 之面 · 今漂)

执行进度 {done}/{total}({pct}%) · 步骤 {step_index}/{total_steps}

- progress 事件: 2/16 · 步骤 2/8
- done 事件: 12/16 · 步骤 12/8 或 12/16 (来源不同)
- 用户看到的 2/8、4/16、12/16 就是两套 total_steps 混着显示。

### 修复方向

- 统一 total_steps 为 _max_total_tools(=16, 与 total 一致), 删掉 3688/3720/3766/3784 的硬编码 8。
- 前端 progress.step_index 应改用 done 而非独立计数。

---

## 四、问题3: pytest 超时后盲目重试

### 实证

[27] execute_command: python -m pytest -q 2>&1 | tail -20
[28] tool_result success=False: timed out after 30 seconds
[29-30] 重试: timeout 280 python -m pytest -q -x ...
[31] tool_result success=False: 又 timed out after 30 seconds
[32] assistant tc=['execute_command']  <- 仍在重试

### 根因链

1. execute_command 硬编码 timeout=30 (core/tools/execute_command.py:39,60): 全量 pytest 跑不完 30 秒 - 工具层先超时, LLM 的 timeout 280 包装永远轮不到生效(外层 30s 先杀)。
2. FailurePauseGuard 提示未注入: guard 的 inject_message(>=5次) 和 paused(>=8次) 写入 payload[guard_results], 但 bridge_loop 的 run_post_guards(...) 返回值从未被读取 (grep 确认: 无 inject_message/paused 消费代码)。
3. 后果: LLM 拿到 timed out after 30 seconds 错误, 但没有任何已连续失败 N 次请换策略的引导 - 盲目重复同一 pytest 命令。

### 修复方向

- execute_command 的 timeout 改为配置化/可调(或至少 60s+), 支持 LLM 传 timeout 参数。
- bridge_loop 消费 run_post_guards 返回: 检测 guard_results.inject_message 追加到 messages, paused 时终止循环并回报。
- 失败重试策略: 连续失败 >=3 次时注入改为分文件运行 pytest 或换验证方式。

---

## 五、问题4: cd /root 环境感知错误

### 实证

[19] execute_command: cd /root && python -m pytest --collect-only ...
[20] tool_result: stderr=/bin/sh: 1: cd: can't cd to /root

### 根因

- 沙箱 cwd = data/projects/{uid}/{sid}/clawsjoy_dev, 无 /root 目录; execute_command 以 cwd=base 执行 (execute_command.py:39)。
- 系统提示(agent_system.md:8)已声明 cwd 已是项目根, 但 LLM 仍输出 cd /root - 提示未在 bridge_loop 的 messages[0] 中被强化, 或 LLM 训练偏见覆盖。
- 工具层对 cd /root 只返回 stderr 错误, 没有主动纠正提示。

### 修复方向

- bridge_loop 每轮在 system 注入绝对 cwd 路径, 并强调不要 cd 绝对路径。
- execute_command 对 cd /root、cd /home 等系统目录命令预检, 直接返回沙箱内提示(不执行)。

---

## 六、上下文吸收优化评估 (方向5)

### 现状

1. 400KB 截断 (3550-3560): system_msgs + tool_msgs + learning_msgs[-3:] + tail - 保留 system+最近工具+学习消息3条+尾部3条。
2. token 分层压缩 (_compress_messages, keep=15/10/8/5): 压缩作用在请求载荷, 不影响 session_log(append-only)。
3. tool_result 2000 截断发生在落盘时 (2020): 这是最关键的吸收缺陷 - 日志里存的就是截断版, derive_messages 投影给 LLM 的永远是残缺结果。

### 优化建议 (按优先级)

| 优先级 | 优化 | 理由 |
|---|---|---|
| P0 | tool_result 截断加标记 + 保留头尾 | 消除信息残缺导致重复执行的主根因 |
| P1 | tool_result 分级保留: 大结果(>2000)用 head+tail 摘要 | 平衡上下文与完整性 |
| P2 | 压缩时保留最近 N 轮完整 tool 对, 旧轮仅保留 summary | 当前 keep 尾部可能截断成对性, 但 _safe_compress 已处理配对 |
| P3 | execute_command stdout 超长时自动提示 stdout 已截断可 grep 定向查看 | 引导 LLM 用精确查询而非全量重跑 |

### session_log 压缩评估: 结论

- session_log 从不截断(append-only), 压缩只改请求载荷 - 投影时序本身无缺陷(live 日志完整: assistant+tool_call+tool_result 全在)。
- 用户怀疑的压缩后日志截断缺历史不成立; 真正的历史缺失是 tool_result 内容 2000 截断(内容级, 非事件级)。

---

## 七、修复优先级建议

1. (P0) tool_result 截断标记+头尾保留 - 治重复执行主因
2. (P0) bridge_loop 消费 failure_pause_guard 的 inject_message/paused - 治 pytest 盲目重试
3. (P1) 统一 total_steps=16 - 治步骤计数错乱
4. (P1) execute_command timeout 配置化 - 支持长测试
5. (P2) system 注入绝对 cwd + cd 预检 - 治 /root 感知
6. (P2) 桥接路径已执行工具去重引导 - 双保险

所有修复均不改数据存储结构(session_log append-only 保持)。
