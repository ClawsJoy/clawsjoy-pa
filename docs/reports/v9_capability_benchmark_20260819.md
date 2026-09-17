# V9 当前能力基准测试报告 — 5 个极简任务

- 日期: 2026-08-19
- 环境: 沙箱网关 5003 (含 P0-P3 + #1/#2/#8/#9 全部改动), DeepSeek deepseek-v4-flash
- 方法: 每任务独立 session, 记录工具调用序列 + turn_end reason + 最终输出

---

## 一、结果总览

| # | 任务 | 结果 | turn_end | 根因 |
|---|---|---|---|---|
| T1 | 读 clawsjoy_dev/BRIEF.md 第一行 | ❌ | max_tokens | 沙箱不含项目文件(路径感知) |
| T2 | 列出 clawsjoy_dev/ 目录 | ✅ | completed | —(修复后) |
| T3 | 读 core/gateway/session_log.py 前 10 行 | ❌ | max_tokens | 沙箱不含项目文件(路径感知) |
| T4 | 写 hello.txt 再读回 | ⏸ | blocked | 写审批门(设计内, 老板确认后完成) |
| T5 | 执行 echo ok | ✅ | completed | —(修复后) |

**结论: V9 修复后可完成简单读/列/执行任务(2/5 完成 + 1 审批中); 读项目源码类任务因沙箱路径隔离失败。**

## 二、修复前失败根因(基准暴露的 3 个 bug)

### Bug 1: 守卫误拒全部读工具(#2 快照污染) — 最严重
- 现象: read_file 全被拒 "当前任务要求代码修改，禁止仅使用读取工具"; list_dir/query_index 被拒 "当前模式不支持该工具"
- 根因: #2 运行时快照以 **role=user** 注入, 内容含 "任务类型：修改(实际修改 + 验证)" "写策略：...write_file..."
  → ForcedToolGuard(扫描最后一条 user 消息) 见 "修改" → 拒读; ModeGuard 模式误判 → 拒 list_dir
- 修复: ① 快照改 role=system(守卫只扫 user 消息); ② 新增 last_user_task_msg() 跳过 "[系统]" 注入消息,
  接入 ForcedToolGuard/ModeGuard/sandbox_ops 读配额/exec 模式/任务分类

### Bug 2: 模式关键词缺读/列 → 简单读任务默认 minimal(拒 list_dir/query_index)
- _ANALYSIS_KEYWORDS 无 "读取/列出/查看..." → get_mode 默认 minimal → list_dir 被 mode_guard 拒
- 修复: 补 "读取/列出/列表/查看/浏览/统计/目录/内容/打印" (写关键词仍优先 → 写任务不受影响)

### Bug 3: 最终回复未落 messages/日志 → 误判空回复(need_more)
- 现象: T2/T5 工具执行成功且模型产出最终内容, 但 done payload reason=need_more "模型未产出有效内容"
- 根因: bridge_loop "无 tool_calls 且有 content" 的完成路径 **break 前不 append/log 最终 assistant 消息**
  → stream/non-stream done payload 扫描 messages 找不到最终回复 → 空回复兜底
- 修复: 正常完成时 append 最终 assistant 到 messages + 写 assistant_message 事件(turn 协议一致)

## 三、修复后任务明细

### T2 list_dir ✅
`list_dir('clawsjoy_dev/') → OK` → 最终回复 "clawsjoy_dev/ 目录下包含以下内容：..."

### T5 echo ✅
`execute_command('echo ok') → OK` → 最终回复 "命令执行成功，汇报如下：..."

### T1 读 BRIEF.md ❌ (max_tokens)
`read_file('clawsjoy_dev/BRIEF.md') → FAIL 文件不存在: .../base_T1/clawsjoy_dev/BRIEF.md`
- 会话沙箱 = data/projects/bench/{sid}/clawsjoy_dev/ (空目录, 只有 goals/data/v8/.agent_state.json)
- workspace 的 BRIEF.md 在沙箱外(../..); 模型在沙箱内探索 12 步后预算耗尽
- 未尝试 ../ 相对路径逃逸(绝对路径 find / 被沙箱拒 "禁止读取系统路径")

### T3 读 session_log.py ❌ (max_tokens)
- 同 T1: read_file('core/gateway/session_log.py') → 沙箱内不存在; 探索 14 步(含 find . -name "*.py")
  后预算耗尽; 模型最终误判"文件不存在，可能要创建"(读变写幻觉)

### T4 写 hello.txt ⏸ (blocked)
- write_file → 写审批门 write_pending → 老板确认后完成(设计内)

## 四、最小修复清单

| # | 修复 | 状态 |
|---|---|---|
| 1 | 快照 role=user → system(#2 快照污染守卫/分类) | ✅ 已修 |
| 2 | last_user_task_msg(): 守卫/配额/分类跳过 [系统] 注入消息 | ✅ 已修 |
| 3 | 模式关键词补读/列 → 简单读任务 full 模式 | ✅ 已修 |
| 4 | 最终 assistant 回复落 messages + 事件日志(防 need_more 误判) | ✅ 已修 |
| 5 | **沙箱路径映射(核心待修)**: 会话沙箱不含项目文件 — read/list 对
     "clawsjoy_dev/BRIEF.md"/"core/..." 解析到沙箱内(不存在)。
     建议: 沙箱建立时把项目根镜像/符号链接进沙箱(如 sandbox/clawsjoy_dev ↔ 项目根),
     或 read/list 路径解析回退到项目根 | ⏳ 待实施 |
| 6 | 写审批: 极简写任务(显式 hello.txt)可考虑免审批通道(权衡) | ⏳ 可选 |

## 五、验证
- 修复后新增回归测试 tests/unit/test_bench_regression.py (5 用例): 快照不毒守卫 /
  真实修改任务仍拒读 / 模式关键词 / 最终消息持久化 / 快照 system 角色
- 相关回归 65 passed(guard/quota/context/cancel/notify/concurrent/replay/p3/turn)
- 全量: 485 passed + 1 flaky(test_full_flow::test_response_time, v5 端点 LLM 延迟 ~1.8s,
  与本次改动无关 — 今日 DeepSeek API 延迟波动; 此前全量 486 通过)
