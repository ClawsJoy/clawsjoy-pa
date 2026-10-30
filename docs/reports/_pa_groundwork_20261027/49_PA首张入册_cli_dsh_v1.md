# PA 首张入册 · cli:dsh（pilot v1）

- 取刻：2026-10-27T15:23:13+08:00｜批准：**老板**（本轮委托）
- 产物：`data/tmp/pa_registry_pilot.json`（pilot · ⛔ 产品 `roster.json`）

---

## 一 身份（先分清三张）

| 张 | 是什么 | 态 |
|---|---|---|
| `self:pa` | **PA 自身**（老板 PA） | active |
| `cli:dsh` | **DSH CLI 执行手**（我跑在其上） | **active（首张试点）** |
| `seat:*` | Paseo 15 席 | pending |

⇒ 我不是 Paseo 席；`cli:dsh` 是 CLI 卡；`self` 是 PA 本体。

## 二 卡（cli:dsh）

| 键 | 值 |
|---|---|
| id ／ kind ／ class | `cli:dsh` ／ `cli` ／ CLI |
| provider | `dsh` 0.1.5-rc.1 |
| capabilities | code ／ file ／ terminal ／ review ／ plan |
| boundary | **单任务打印即退**；⛔ 持久会话（除 web/tui profile）；⛔ GUI |
| fragility | model／profile 依赖；headless 无交互；**超时须自带** |
| cost | model-dependent；见 `/v9/pa/cost` |
| invoke | `dsh --profile headless "<task>"` |
| probe | `dsh --version` ⇒ `0.1.5-rc.1` |
| verified ／ approved_by | `true` ／ **老板** |
| approval_ref | 老板本轮委托：首张试点 |

## 三 读数

- 卡 **19**：active **2**（`self:pa` ＋ `cli:dsh`）／ pending **17**；
- pending 17 **不可派**；⛔ 自动信任；
- 别队册只读；`DSH技术复核` 仍 pending external。

## 四 为什么不是产品 `roster.json`

- 产品 `data/v9/pa/roster.json`（18,054 B）有既有 schema／测试；
- 本轮只做 **pilot**：`data/tmp/pa_registry_pilot.json`；
- Phase 1 Agents 面接此 pilot；PD／CW 再决定落产品册；⛔ 我改产品 schema。

## 五 下一手

1. Agents 面显「**待入册 17**」；
2. 逐卡 probe（`paseo agent inspect` ／ CLI `--version`）；
3. 老板再批下一张；⛔ 批量自动批；
4. 派活只从 active 选；`cli:dsh` 首单须带 timeout。

（完 —— 本件末行 · LF 终 · 悬）
