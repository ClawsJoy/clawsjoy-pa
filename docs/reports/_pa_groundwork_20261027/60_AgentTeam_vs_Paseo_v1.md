# Agent Team vs Paseo（2026-10-27）

- 主：DSH（PA）｜问题：`@deepseek-ai/dsh-experimental-agent-team` 能否代替 Paseo
- 判：**不能整替；能替 PA 内部“任务型小组”，不能替 Paseo 的“常驻多提供方席位层”。**

---

## 一 两者是什么

| 项 | DSH Agent Team | Paseo |
|---|---|---|
| 形态 | **会话内 Lead＋具名 teammate**；工具 `spawn/send/task/wait/interrupt` | **本机 daemon＋CLI＋GUI**；15 席 |
| 成员 | Lead＋最多 **16**；名字永久；fresh／fork | 15 个独立席；Codex／DSH／PI |
| 消息 | 目标 inbox；持久；⛔ 不重试／不保证序 | seat 消息/队列；UI 可见 |
| 任务 | **共享任务板**：DAG／依赖／CAS／owner／write scopes | **主面不是任务板**；CLI 无 task 命令 |
| 工作区 | **共享同一 cwd**；⛔ 独立 cwd | 每席可独立 cwd／worktree |
| 跨进程 | ⛔ 同进程/同会话 | ✓ daemon/CLI/GUI 跨进程 |
| 持久 | roster/tasks 写 Lead session；冷恢复 teammate | daemon／seat session 独立 |
| 成熟度 | **实验性 0.2.1-rc.3** | 0.13.2；有 v4／并发锁 bug |

---

## 二 分项判

| 维度 | Agent Team | Paseo | 胜 |
|---|---|---|---|
| 成员 roster | 4/5 | 5/5 | Paseo |
| 直接消息 | 4/5 | 4/5 | 平 |
| **共享任务/DAG/写域** | **5/5** | 2/5 | **Agent Team** |
| 多提供方（Codex/PI/云） | 1/5 | 5/5 | Paseo |
| 独立 cwd／worktree | 1/5 | 5/5 | Paseo |
| 常驻席／GUI／daemon | 1/5 | 5/5 | Paseo |
| 运维简单（少一个 app） | 5/5 | 3/5 | Agent Team |
| 实验风险 | 2/5 | 4/5 | Paseo |

---

## 三 可替代度

| 场景 | 可替代 |
|---|---|
| PA 内部 2–8 人、同仓、任务型开发 | **70–80%** |
| PA 内部评审／审计／文档并行 | **70–80%** |
| 15 席异构 agent 组织 | **20–30%** |
| 常驻席／跨进程／云 VM／移动端 | **0–10%** |

---

## 四 建议架构

```
PA 编排层（DSH / PA）
  ├─ Agent Team：同仓任务小组（开发/审/文档）—— 默认
  ├─ Paseo：常驻异构席（Codex/PI/云/VM）—— 保留
  └─ PA 自册：席位卡/边界/成本/审批 —— 唯一真源
```

- **Agent Team 成员 = 任务性 teammate**，⛔ 当常驻席；不写进 PA seat 册；
- **Paseo 席位 = 常驻能力**，仍由 PA 自册管；
- 两者不互写；消息/任务不混账。

---

## 五 PA v1.1 试点（建议）

| 角色 | 写域 | 任务 |
|---|---|---|
| `shell-dev` | `shell/` | S1 全局热键＋Summon 浮层 |
| `agents-dev` | `web/pa/faces/` | S2 Agents 接 registry |
| `api-dev` | `core/pa/`＋`tests/` | S2 `/v9/pa/registry` |
| Lead（PA） | — | 验收 A1–A5／合并 |

- 3 个 teammate；write scopes 不重叠；Lead 复核；
- 指标：完成时间／消息数/任务／冲突数／返工／成本；
- 若 1 周内达标 ⇒ PA 内部默认 Agent Team；Paseo 只留常驻席。

---

## 六 结论

**不能整替 Paseo；应“分工”：Agent Team 管同仓任务小组，Paseo 管常驻异构席。**
对 PA v1.1，**先用 Agent Team 试点 3 人**，比继续加 Paseo 席更轻。

（完 —— 本件末行 · LF 终 · 悬）
