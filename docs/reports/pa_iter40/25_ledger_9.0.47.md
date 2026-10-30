# PA 迭代40 · T97 9.0.47 入账＋preflight

- 代发: DSH（PA）｜主: lead｜WIP=1
- 取刻: 2026-10-30T12:24+08:00
- 账径: `data/v9/pa/evidence_ledger.jsonl`；sha16 **88ab1d027bc98f58**；bytes **1478**

## 一 新增

| 件 | sha16 | owner | decision |
|---|---|---|---|
| `ClawsJoyPA-Setup-9.0.47-x64.exe` | `0047fb56c51dca2a` | PD | D-20261030-09 |

- count 6 → 7（6 证据 + 1 supersede）；
- verify --max-age-days 30 ⇒ **ok=true / total=6 / bad=[] / superseded=1**；
- superseded：line3 ad42 → af0f，D-08；
- preflight ⇒ **RC0 / PASS_WITH_MANUAL**；AG-10 MANUAL 显式。

## 二 判

- 9.0.47 已入件—账—印；
- 旧印退役、历史保留；
- preflight 通过但**不是 PASS**：MANUAL 1 条；
- 账域 6 条证据，非全量。

（完）