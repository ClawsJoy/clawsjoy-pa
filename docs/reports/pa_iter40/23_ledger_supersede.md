# PA 迭代40 · T94 真账 supersede ad42（D-08）

- 代发: DSH（PA）｜主: lead｜WIP=1
- 取刻: 2026-10-30T12:09+08:00
- 账径: `data/v9/pa/evidence_ledger.jsonl`；sha16 **ec3bbe73f3711126**；bytes **1252**

## 一 动作

    supersede core/pa/relations.py --sha16 ad42e425f9687bb6
      --decision D-20261030-08 --owner PA
      --reason "T93/T89 合法改件；旧印退役，历史保留"

- count 5 → **6**（5 条证据 + 1 条 supersede）；
- 旧 line 3 **保留**，不删、不改；
- D-08 声明旧印退役。

## 二 回验

- `verify --max-age-days 30`：**ok=true / total=5 / bad=[] / superseded=1**；
- superseded 项：line 3 `ad42…` → actual `af0f…`，reason `superseded`；
- `preflight`：**RC0 / verdict PASS_WITH_MANUAL**；
  - anti_goals 9 PASS / 0 FAIL / **1 MANUAL（AG-10）**；
  - ledger ok / total 5；
  - **不是 PASS**：MANUAL 显式保留。

## 三 意义

- 旧印 stale 不再被当 bad，但历史仍可查；
- supersede 是显式治理动作，不是删除/覆盖；
- preflight 现在能作为交付前门：无 FAIL + ledger ok，MANUAL 单独亮出。

## 四 界

- 未删旧行、未改历史、未造绿；
- AG-10 仍 MANUAL，C5/验器源/14-9 面标仍属 C-30 PM 未清；
- 账域 5 条证据，非全量。

（完）