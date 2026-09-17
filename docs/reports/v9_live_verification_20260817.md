# V9 工作区实机验证报告（子任务/深度/重复提醒/结构化错误）

> 日期：2026-08-17 | 方式：Flask test client 模拟 HTTP + 注入 live DeepSeek key，子任务**真实调用 DeepSeek API 执行**（非 mock）
> 结果：**14/14 全部通过**

---

## 验证项与结果

### ① 子任务正常执行 ✅
- 提交 `sub_1786976163971_1` → queued → **done**
- **VerificationChain 五步 passed=True**, failures=0
- 产出文件 `verify_output.md` 内容精确为 **"V9验证成功 值=42"**（write_file 真实写入）
- 独立沙箱 + git 基线（2 commits：baseline → state: running）+ **归档成功**（archive/subtasks/）
- 顺带触发 filter_net 自学习（write_file/verify_output.md used=4）

### ② depth 预算生效 ✅
- POST `depth=3` → 路由 `resolve_depth(3)=4` > maxDepth=3 → **`SUBTASK_DEPTH_EXCEEDED`**（HTTP 200, success=false, 含 depth/max_depth 字段）
- 未创建线程池任务，纯逻辑拒绝

### ③ 工具重复调用提醒 ✅
- `observe` 连续 3 次同参数（`read_file({"path":"a.py"})`）→ 第 3 次返回 `[重复提醒] 你已连续 3 次调用同一工具 read_file(...)`
- 第 4 次不重复提醒（3/5/8 分档语义）
- `reset` 后重新计到第 5 次提醒（详细版含参数）
- 不同参数不算重复

### ④ 失败路径结构化错误码 ✅
- `_struct_error` → `{code, message, detail}` 精确匹配
- 异常分类：`ConnectionError` → **NETWORK**、`"API错误: 402 balance"` → **LLM_API**
- 回调降级：`_notify_fail_to_text({code:TIMEOUT,...})` → `"[TIMEOUT] 超过最大轮次"`
- `reason: dict` 注解回调收到结构化 `{code: "TOOL_EXEC", message: ...}`

---

## 验证产物

```
data/projects/verify_u1/verify_s1_76163/clawsjoy_dev/archive/subtasks/sub_1786976163971_1/verify_output.md
→ V9验证成功 值=42
```

git log 快照：
```
7148f91 state: running
7b02845 subtask baseline: sub_1786976163971_1
```

---

## 验证日志关键行

```
[VerificationChain] task=请用 write_file 工具写入文件 verify_output.md... passed=True failures=0
[FILTER_NET] #81 自学习完成: write_file/verify_output.md used=4 ignored=0 w=0.000
[AUTO_ARCHIVE] _save_state(done) 归档 -> data/plans/verify_s1_76163/report_20260817_221654.md
[AUTO_MERGE] task_progress 最近 3 条未全部 completed，跳过合并
```

---

## 覆盖映射

| 验证项 | 对应实现 | 相关提交 |
|---|---|---|
| 子任务执行 | `subtask_executor._run` + `_execute_agent_task` | cd5ea12 / 系列修复 |
| depth 预算 | `resolve_depth`/`check_depth`/`SubtaskDepthError` | b377374 |
| 重复提醒 | `repeat_tool_reminder.observe`（3/5/8 分档） | b5e7bbd |
| 结构化错误 | P1 `_struct_error`/`_classify_exception` + P2 失败记录 + P3 回调 | 32d901e / 359ec46 / 1f662c0 |

---

## 附注

- 临时验证脚本 `_tmp_verify_v9.py` 已删除；工作区仅 `core/lib/filter_net.json` 运行时自学习累计（正常产物）
- 真实链路覆盖：HTTP 路由 → 线程池 → 独立沙箱 → 真实 LLM → 验证链 → 审计 → 归档
