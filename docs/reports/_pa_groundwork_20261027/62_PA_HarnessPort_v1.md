# PA HarnessPort v1（2026-10-27）

- 主：DSH（PA）｜目标：PA 依赖 **harness 能力**，不依赖 DSH／Paseo／Obsidian 某一家
- 一句：**PA 核心自有；harness 可换；Paseo／Obsidian 是外设。**

---

## 一 依赖倒置

```
PA core（自有）
  registry / ledger / vault / doors / policy / memory / Today / Focus
        │  只依赖
        ▼
HarnessPort（接口）
  run / resume / cancel / stream / permissions / cost / audit / team?
        │  由 adapter 实现
        ├─ DshHarness（当前 reference）
        ├─ CodexHarness / ClaudeHarness / ApiHarness
        ├─ PaseoSeatHarness（可选，异构席）
        └─ MockHarness（测试）

外设（可选）：ObsidianExporter ／ Paseo UI ／ 移动端
```

---

## 二 HarnessPort 最小面

| 方法 | 语义 | 必 |
|---|---|---|
| `probe()` | 可用性＋版本＋刻 | ✓ |
| `run(spec)` | 起一次任务；返回 `run_id/session_id/stream` | ✓ |
| `resume(session_id)` | 续会话；不回放历史则显式声明 | ✓ |
| `cancel(run_id)` | 停；1s 内 | ✓ |
| `stream(run_id)` | 增量输出 | ✓ |
| `permissions()` | 门／级别／待批 | ✓ |
| `cost(run_id)` | tokens／金额／轮次 | ✓ |
| `audit(run_id)` | 回执／产物／哈希 | ✓ |
| `team()` | spawn／message／tasks | 选 |

`run(spec)` 的 spec：`task, cwd, tools, permission_level, timeout, model, resume_id`。

---

## 三 PA 自有记录（不外包）

```json
{
  "run_id": "pa-run-...",
  "harness": "dsh|codex|api|paseo",
  "session_id": "harness-native-id",
  "model": "...",
  "cwd": "...",
  "started_at": "...",
  "ended_at": "...",
  "status": "ok|failed|cancelled",
  "cost": {"tokens": 0, "cny": 0},
  "artifacts": [],
  "receipt_sha16": "...",
  "harness_meta": {}
}
```

- **PA ledger** 存 canonical `RunRecord`；
- **PA vault** 存产物/摘要；
- **PA registry** 存席位卡/边界/成本；
- ⛔ 让 DSH v3/v4 session 格式成为 PA 账本真源；
- ⛔ 让 Obsidian 成为唯一存储。

---

## 四 适配器规则

1. `core/pa` 只 import `core.pa.harness.port`，**不 import** `dsh`／`paseo` 包；
2. DSH 适配器在 `core/pa/harness/dsh.py`；Paseo 在 `paseo.py`；Obsidian 在 `export/obsidian.py`；
3. 适配器负责 session 格式（v3/v4）与历史；PA 不解析；
4. 历史不回放 ⇒ 适配器显式 `history_replay=false`；PA 用自有回执/摘要补；
5. `team` 是可选能力；DSH Agent Team 只作 `team` adapter。

---

## 五 验收

| # | 判 |
|---|---|
| H1 | **MockHarness** 跑一任务，PA registry/ledger/vault 正常；无 DSH import |
| H2 | DSH adapter 跑一任务，canonical record 落 PA 账；DSH session 只作 meta |
| H3 | 移除 Paseo／Obsidian，PA Today/Agents/Ledger 仍可运行 |
| H4 | DSH v3/v4 切换不改变 PA 账本 schema |
| H5 | `core/pa` import 检查：0 个 DSH/Paseo 直接依赖 |

---

## 六 迁移步

1. 落 `port.py`＋`MockHarness`＋H1 测试；
2. 把 `cli:dsh`／headless 收进 `DshHarness`；
3. Agent Team 收进 `team` 可选能力；
4. Paseo 收进 `PaseoSeatHarness`（可选）；
5. Obsidian 收进 exporter（可选）；
6. PA v1.2 起只对 Port 编程。

---

## 七 为什么现在做

- DSH v4/v3 与 Paseo 并发锁已证明：**harness 私有格式/会话会变**；
- PA 的账、册、库不能跟着变；
- Paseo 可由 Agent Team 替代内部团队；Obsidian 可由 Vault/Markdown 替代；
- 所以 **PA 核心与 harness 解耦**，是产品化的前提。

（完 —— 本件末行 · LF 终 · 悬）
