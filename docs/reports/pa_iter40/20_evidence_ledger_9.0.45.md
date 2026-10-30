# PA 迭代40 · T87 9.0.45 入账＋30 天回验

- 代发: DSH（PA）｜主: lead｜WIP=1
- 取刻: 2026-10-30T11:32+08:00
- 账径: `data/v9/pa/evidence_ledger.jsonl`；sha16 **5026ce9ebf19fff7**；bytes **836**

## 一 新增

| 件 | sha16 | owner | decision |
|---|---|---|---|
| `ClawsJoyPA-Setup-9.0.45-x64.exe` | `9d2f34a96e19aa88` | PD | D-20261030-06 |

- count 3 → 4；registered=true；
- 同键重登 ⇒ registered=false，count 仍 4（幂等零写）；
- `verify --max-age-days 30` ⇒ **ok=true / total=4 / bad=[]**。

## 二 判

- 9.0.45 内部发布已入“件—账—印”；
- 账本仍只覆盖内部发布，不冒充真 OV/EV；
- 30 天窗口回验通过，T85 保鲜门在真实账上生效。

（完）