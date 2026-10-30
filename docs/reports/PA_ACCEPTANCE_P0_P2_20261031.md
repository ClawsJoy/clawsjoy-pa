# PA P0–P2 用户路径验收报告（2026-10-31）

## 版本

- 安装：**9.0.75**
- 主程序/54 exe/Setup：Authenticode Valid
- 构建：icon_tool_called=False

## P0

| 项 | 证据 | 结果 |
|---|---|---|
| 本地无 key 聊天 | `POST /v9/agent/runs model=ollama` → done，content_len=37 | ✅ |
| 发送有受理 | UI/API 202 + run_id + queued/position | ✅ |
| 停止清 active | 长任务 running→cancel_requested→cancelled；active_turns=[] | ✅ |
| 任务可恢复 | 刷新后 run_id 恢复 running 并轮询到 done | ✅ |
| running 中途刷新 | 385bbf5a 刷新后 state=running，最终 done | ✅ |

## P1

| 项 | 证据 | 结果 |
|---|---|---|
| 单发送链 | work/dev 只走 `/v9/agent/runs`，无静默 SSE 回退 | ✅ |
| 审批分级 | 本地纯聊天不弹停手卡；CDP card=false | ✅ |
| 记忆复用 | 第二轮 run task 含第一轮问答；回答“老板” | ✅ |

## P2

| 项 | 证据 | 结果 |
|---|---|---|
| 多席 API | `seats=[PM,PD]` 202→done；output.seats=2 | ✅ |
| 多席 UI | `多席:PM,PD` 跳过 ask 门；页面各席+综合 | ✅ |
| 多席可发现性 | 主窗 Summon 输入下方 `pa-summon-hint` 490×15 可见 | ✅ |
| 成本/回执 | 消息附「耗时 N s · 本地模型 0 元 · run_id 尾8」；recordPaTurn 一次 | ✅ |
| 恢复 | 队列持久化；running 重启→failed process_restart | ✅ 单测 |
| 发布 | 9.0.75 全签安装；远端 API 同步（9.0.73） | ✅/⚠待补推 |
| DSH cloud runner | 无 key 400 `dsh_requires_key`；有 key 可跑 | ✅ fail-closed |
| DSH 本地 provider | 当前 DSH 仅 deepseek-official，无本地 provider 配置 | ❌ 外部限制 |

## 真实 run 样本

- local: `5b6e47e164ee47e1b22a1baad81f25fa` state=done content_len=37
- seats: `a30a20b65d094d41a735cd7bab0e5f15` state=done seats=2
- dsh: HTTP 400 `dsh_requires_key`
- stop: `60a4cf8c94ea4c81bc359507c25e0a91` state=cancelled

## 未完成/边界

1. DSH 本地 provider 当前不支持；DSH 只能 cloud deepseek（需用户 key）。
2. 远端 9.0.74/9.0.75 还需补推。
3. 真 OV/EV 仍 blocked（自签仅本机受信）。
