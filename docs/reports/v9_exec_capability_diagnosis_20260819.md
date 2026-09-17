# V9 执行能力全链路诊断报告 — 5 任务实测

- 日期: 2026-08-19
- 方式: 实机 5 任务(从易到难) + session_log 轨迹逐段分析
- 网关: 沙箱 5003 (P0-P2 + Turn 协议 全量代码)

---

## 一、5 任务结果总览

| # | 任务 | 完成 | reason | 失败环节 |
|---|---|---|---|---|
| T1 | 写 hello.py | 部分(卡审批) | blocked | write_pending 审批门(正常行为, 需老板确认) |
| T2 | 读 notifications.json 统计 | 否 | max_tokens | 路径漂移: 8轮探索未找到文件, 耗尽 |
| T3 | git 状态+最近3次提交 | **是** | completed | 无(3 工具, 干净完成) |
| T4 | 统计 core/ Python 行数 | 否 | max_tokens | 路径漂移: 8轮 find/ls 找不到 core, 耗尽 |
| T5 | 找 TODO 注释 | 否 | error | **400: 失败注入破坏投影配对** |

**成功率: 1/5 完整完成(T3), 1/5 卡审批(T1 正常), 3/5 失败(T2/T4/T5)**

---

## 二、逐任务诊断

### T1 写文件 — reason=blocked(正常审批行为) [部分成功]
- 轨迹: execute_command(pwd) → write_file → write_pending 卡
- 结论: **V9 正确暂停等待审批, 非缺陷**。若老板确认可继续(已实测 E2E 11.2s 闭环)。

### T2 读文件 — reason=max_tokens [失败: 路径漂移]
- 轨迹(9 工具): list_dir('.') → pwd+find / -name notifications → cd .. → cd 绝对路径 → cat 绝对路径...
- 根因: **沙箱 cwd 是 `data/projects/diag/diag_T2_read/clawsjoy_dev`(空项目), 真实文件在 `data/v8/`, Agent 不知道上两级**, 8轮探索路径耗尽。
- 表现: 大量 `cd ..`/`find /`/绝对路径探测, 未找到目标。

### T3 git 状态 — reason=completed [✅ 完整成功]
- 轨迹(3 工具): pwd+git status → git log -3 --stat → git log -3 --pretty=format
- 结论: **命令任务在 cwd 内有 git 时能干净完成**。这是 5 个任务里唯一真成功的。

### T4 统计行数 — reason=max_tokens [失败: 路径漂移]
- 轨迹(10 工具): find / -type d -name core → find . -maxdepth 6 → ls 绝对路径 → cd .. → cd 绝对路径...
- 根因: 同 T2, **沙箱空项目, Agent 找不到真实 core/**, `find /` 超时/权限失败, 8轮耗尽。

### T5 找 TODO — reason=error [失败: 400 投影断裂] ★核心缺陷
- 轨迹: search_files(TODO) → list_dir → read_file(.agent_state) → execute_command(pwd+ls+find) → **3 次 `cd /home/...` 越权被拒** → 第6轮 400
- **根因(已定位到行)**: `core/gateway/tool_router.py:52`
  ```python
  if _n >= 5:  # 连续失败5次
      log_event(session_id, "user_message", {"role": "system", "content": "已连续失败5次...", "source": "failure_pause"})
  ```
  → 在 assistant tool_call(seq 28) 与 tool_result(seq 31) **之间**插入 user_message 事件
  → derive_messages 投影出 system 消息插在配对中间
  → DeepSeek 400: 'assistant message with tool_calls must be followed by tool messages'

---

## 三、V9 断点定位(哪一环断了)

### 断点 1(核心, 导致 400): failure_pause 注入破坏投影配对 — tool_router.py:52
- 连续失败 ≥5 时, 直接把 system 消息写成 user_message 事件, 插进 tool_call/tool_result 之间
- **修复**: 改为注入到 `_bmsg["content"]`(像 bridge_loop 的 GUARD_INJECT 一样), 或延迟到下一轮轮首注入, 不在工具执行中落盘

### 断点 2(导致 T2/T4 失败): 沙箱路径认知缺失 — 环境感知
- 沙箱 cwd 是空项目目录, Agent 不知道 `data/`、`core/` 在上级
- 系统提示只说了 'cwd 已是项目根', 没给真实项目结构
- **修复**: 启动时注入真实项目树(类似 workbench 的 fileTree), 或让 sandbox_base 直接指向真实项目根

### 断点 3(T2/T4 加重): 越权命令被拒后 Agent 反复重试同路径
- 3 次 `cd /home/...` 全被 escape guard 拒绝, 但 Agent 不改策略(失败注入没生效或太迟)
- 与断点1相关: 失败提示要到第5次才注入, 且注入方式破坏投影

---

## 四、修复优先级

| 优先级 | 修复 | 对应断点 |
|---|---|---|
| P0 | failure_pause 注入改方式: 不落 user_message 事件, 改为追加到当前 assistant content 或下一轮首条消息 | 1(400) |
| P1 | 沙箱启动注入真实项目结构树(让 Agent 知道 data/ core/ 在哪) | 2(T2/T4) |
| P1 | 越权被拒后立即注入'换路径'引导(不等5次) | 3 |
| P2 | T1 审批流已正常, 无需改 | - |

**一句话结论: V9 工具执行/审批/命令都正常, 断在 (1) failure_pause 注入破坏 P2b 投影配对导致 400, (2) 沙箱空项目导致 Agent 路径漂移耗光预算。**

---

## 五、验证方式

- T3(git) 证明: 工具执行+守卫+reason 链路健康
- T1(write) 证明: 审批门正常
- T5(400) 复现: 连续失败注入后必现 400(可写回归测试)
- T2/T4(路径) 复现: 空沙箱任务必漂移
