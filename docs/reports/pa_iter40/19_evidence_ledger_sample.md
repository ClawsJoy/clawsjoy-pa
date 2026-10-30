# PA 迭代40 · T84 evidence ledger 首条真实交付

- 代发: DSH（PA）｜主: lead｜WIP=1
- 取刻: 2026-10-30T11:10+08:00
- 账径: `data/v9/pa/evidence_ledger.jsonl`；sha16 **bb8ea81b29055ca7**；bytes **610**
- 工具: `scripts/pa_evidence_register.py`（T82）

## 一 三条真实记录

| # | 件 | sha16 | owner | decision |
|---|---|---|---|---|
| 1 | `dist/pa_shell/setup/ClawsJoyPA-Setup-9.0.44-x64.exe` | `88e9b3a3f142dd7f` | PD | D-20261030-05 |
| 2 | `docs/reports/pa_iter40/ACCEPTANCE.md` | `ba81fdebd7255113` | PA | D-20261030-05 |
| 3 | `core/pa/relations.py` | `ad42e425f9687bb6` | PD | D-20261030-05 |

## 二 实跑

- 三条 `registered=true`，计数 1→2→3；
- 同键重登：`registered=false`，count 仍 3（幂等，零写）；
- `verify`：**ok=true / total=3 / bad=[]**；
- 账本 fsync、O_APPEND、JSONL 单行。

## 三 意义

- 这是“件—账—印”第一次落到真实交付，不是测试夹具；
- 9.0.44 Setup 的印与 T83 报一致；
- 后续交付应走同一 CLI：先件、后账、回验；
- 账本目前只记录 D-05（内部发布），不冒充真 OV/EV。

## 四 界

- 未改产品码；未伪造印；未把 9.0.44 自签冒成真 OV/EV；
- 账本可回读；篡改/缺件会由 verify 抓出（T82 测已覆盖）。

（完）