# `core/lib/_SEALED.md` —— 已封（死件）清册

> 承 pm `1364 §二.1`（裁「注之据」＝ ⒝ · 锚须**在仓内且入 git**）／ 承 pm `1359 §五`（封之式 ＝ ⒝「件头明标」）
> ／ 承 CW `1363 §三.5`（请裁一）⇒ **本册即七件之注所引之「据」**。
> 本册 ＝ **静态之记**（CW 一手按名扫 · 承 CW `1335 §三` ／ `1339 §三` · ⛔ 器自跑）⇒ 改件时**同步修订**。

## 一 二账 ⛔ 同轴（释名 · 必读）

| 账 | 面之径 | 所记 | 入 git |
|---|---|---|---|
| **本册** | `core/lib/_SEALED.md` | **模块缺源** ⇒ 件在而**载入即死**（`ImportError`） | ✅ 入 |
| 彼账 | `data/v9/pa/deadfile_ledger.json`（器 `core/lib/scan_dead_registry.py`） | **YAML 声明之径** ⇒ 盘上无者 | ⛔ 不入（`data/**` ＝ 运行态） |

⇒ ⭐ **二物 ⛔ 同轴**（⛔ 混 · 承「一名一义」）。实证（CW 一手 · 2026-10-06）：七件 ＋ `memory_simple` 于彼账 **`0` 命中**（`rg` rc `1`）。

## 二 总根 `A1`（真缺 · ⛔ 在）

| 号 | 面之径（逐字） | 字节 | 印16 | 补之门（其家 · 逐字） |
|---|---|---|---|---|
| A1 | `core/lib/memory_simple.py` | ⛔ 在 | — | `D:\clawsjoy\lib\memory_simple.py`（2,659 B · `f253928af035e56d` · `class SimpleMemory` · `memory = SimpleMemory()`） |

## 三 已封 `B1`–`B7`（皆 `from core.lib.memory_simple import memory` ⇒ 载入即 `ImportError`）

| 号 | 面之径（逐字） | 字节 | 改前印16 | 缺 | 封注 |
|---|---|---|---|---|---|
| B1 | `core/lib/video_planner.py` | 2,827 | `eb2bb7d97a7ceeca` | `core/lib/memory_simple.py` | 件头一行 |
| B2 | `core/agents/builtin/memory_manager.py` | 2,295 | `0aaca019575ce069` | 同上 | 件头**二**行（封 ＋ C1） |
| B3 | `core/lib/analysis_utils.py` | 647 | `9752fed09f587f06` | 同上 | 件头一行 |
| B4 | `core/lib/channel_analyzer.py` | 2,435 | `5eb35824562dd16d` | 同上 | 件头一行 |
| B5 | `core/lib/data_contract.py` | 1,222 | `0e27a4802df37919` | 同上 | 件头一行 |
| B6 | `core/lib/error_knowledge_v1_0_00_20260517.py` | 7,213 | `eea9aa5debe350f7` | 同上 | 件头一行 |
| B7 | `core/lib/task_quality_scorer_v1_0_00_20260517.py` | 5,076 | `8f7e8d3d7ffbc3fe` | 同上 | 件头一行 |

## 四 解封之门（唯一之途 · **自足**）

⒈ 置 `core/lib/memory_simple.py`（迁自 `D:\clawsjoy\lib\memory_simple.py`）。
⒉ **重校七件之 API**（今 ⛔ 知谁用 ⇒ ⛔ 径删注了事 · 承 pm `1359 §五` 裁二）。
⒊ 逐件删其封注（**一件一 `commit`**）。
⚠ 旁记：pm `1359 §五` 裁二之 `L7` ＝ **本机之簿**（`_pm\` · ⛔ 入仓）⇒ **本 §四 自足 · ⛔ 倚之**。

## 五 其据 ＋ 器之限（照实）

- 按名扫 1,361 个 `.py` ＋ 非 `.py` 面 ⇒ 六名 `0` 命中；`memory_simple` 唯 `2` 命中（皆**数据文件** `Path("data/memory_simple.json")` · ⛔ 模块）。
- 唯三件可自跑（`video_planner` ／ `error_knowledge…` ／ `task_quality_scorer…` 有 `if __name__ == "__main__"`）⇒ **自测之用 ⇒ ⛔ 谓活**。
- ⚠ **器之限**：唯静态（AST · 按名）⇒ 「`0` 引」**⛔ 即「无调用」**（⛔ 及动态导入 ／ 字符串注册表 ／ YAML 装配）。
- `C1`（`core/agents/builtin/memory_manager.py` **原** `:13`）：`from agents.base_agent import BaseAgent` ⇒ 实家 `core/agents/base/base_agent.py` ⇒ **径误** · 宿主为死件（B2）⇒ ⛔ 单修（记 · 备其真活时）。
