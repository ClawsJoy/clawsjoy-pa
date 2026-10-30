# PA 迭代40 · T90 ledger 刷新 relations 新印

- 代发: DSH（PA）｜主: lead｜WIP=1
- 取刻: 2026-10-30T11:45+08:00
- 账径: `data/v9/pa/evidence_ledger.jsonl`；sha16 **36c3c85b5d6a7e08**；bytes **1028**

## 一 追加

| line | 件 | sha16 | decision |
|---|---|---|---|
| 3（旧） | `core/pa/relations.py` | `ad42e425f9687bb6` | D-05 |
| 5（新） | `core/pa/relations.py` | `af0f69ca7c19b81e` | D-07 |

- registered=true；count 4 → 5；
- 旧记录**保留不删**，按重算印判 stale（superseded）；
- `verify --max-age-days 30`：**ok=false / total=5 / bad=1**。

## 二 bad 原文（照实）

    line 3 path=D:\clawsjoy_v9\core\pa\relations.py
    expected ad42e425f9687bb6 / 10989B
    actual   af0f69ca7c19b81e / 11453B
    reason   印不符（疑篡改）

这是**正确的审计行为**：文件已因 T89 合法变更，旧记录应过期，不应被手工消掉。

## 三 判

- 账本当前 **4/5**，不是全绿；
- 旧记录标 superseded，新记录 D-07 已入；
- 若要求账面全绿，只能新增/迁移记录，不能删历史或伪造；
- owner 门 T89 已强制，本账 5 条 owner 全在，owner 面无误伤。

（完）