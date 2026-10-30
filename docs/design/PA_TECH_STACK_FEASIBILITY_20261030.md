# PA 技术栈可行性报告（2026-10-30）

## 0. 结论

**有条件可行。**

- 可行的是：PA 壳 + DSH CLI worker + 本地 qwen 聊天 + 异步状态机 + 账本/审批。
- 不可行的是：在 6GB 显存的本地 7B 模型上，完整复刻云端 DSH 的长任务能力。
- 正确路线：**PA 管状态与责任，DSH 管执行；本地模型做默认聊天，复杂任务显式路由。**

## 1. 现有代码证据

| 能力 | 现有件 | 状态 |
|---|---|---|
| Harness 接口 | `core/pa/harness/port.py` | 有，协议完整 |
| DSH adapter | `core/pa/harness/dsh.py` | 有，跑 `dsh --profile headless` |
| Mock adapter | `core/pa/harness/mock.py` | 有，测试用 |
| Run 账 | `core/pa/harness/store.py` | 有，JSONL |
| 模型路由 | `core/pa/providers.py` | 有，默认 local:ollama |
| 本地 provider 路由 | `core/gateway/v9_chat/provider_route.py` | 有，provider-aware |
| 取消 | `routes/session.py` + `turn_registry` | 已修，关 RUNNING |
| 旧窗口发送 | `web/pa/faces/window.js` | 已改直达 sendAgent |
| 异步 | `turn_registry` / threads | 有基础，无队列 |

**关键缺口：DshHarness 未接进 `/v9/agent/chat` 主路径。**

## 2. 本地模型可行性

- 模型：`qwen2.5:7b-instruct-q4_0-gpu`
- 显存：RTX 2060 6GB；`/api/ps` size_vram 4.496GB
- ctx：4096
- 实测：无 tools 直接聊天可用；带 tools 偶发 400（tool-call JSON 不闭合）

**判断：**

- 简单对话/单步：可行。
- 多步工具/长任务：不可靠，需要 DSH/云模型。
- 必须做：本地 tools 失败回退、上下文压缩、任务分级。

## 3. DSH 运行时可行性

- `DshHarness.run` 以子进程跑 `dsh --profile headless <task>`。
- 可给 PA 提供：run_id/状态/成本/产物/回执。
- 限制：
  - 不是库内调用，是 CLI 进程；
  - 流式/恢复需按 port 语义补；
  - 每任务启动开销；
  - 需要 DSH 在装根可用。

**判断：** 作为 P0 worker 可行；先做“一个任务一个 run”，不要一上来做全双工。

## 4. 异步两车道可行性

- 后端：Flask + 线程/队列 + `turn_registry` 可行。
- 状态：`CREATED/RUNNING/DETACHED/CANCELLED/COMPLETED/FAILED/STALE` 已有。
- 缺：每 session 队列、对话/执行分流、SSE/轮询契约。
- **约束：单主/WIP=1 必须保留。**

## 5. 记忆/证据可行性

- 账本、二脑、决策总表已有。
- 需统一：session 记忆、任务回执、证据四件套、第二大脑同步。

## 6. 风险

1. 本地 7B 工具调用不稳。
2. 旧聊天路径与新 harness 双轨。
3. 单主与异步的边界。
4. 6GB 显存下并发模型。
5. live/dev 真源分叉（v9_chat AGENTS）。
6. UI 假状态/假“已发”。

## 7. 分期

### P0（当前）

- 本地 tools 400 回退。
- PA 聊天主路径接 DSH HarnessPort（CLI worker）。
- 发送/停止/排队状态机。
- 用户路径 E2E。

### P1

- 审批分级。
- 记忆复用。
- 错误人话化。
- 单发送链（删旧窗口重复路）。

### P2

- 多席编排。
- 成本/预算。
- 恢复/回放。
- 发布/签名/更新。

## 8. 验收

- 无 key 本地一句话有回应。
- 发送有 run_id。
- 停止 active 立即清。
- 任务可排队。
- 完成有回执。
- 关窗再开任务在。
