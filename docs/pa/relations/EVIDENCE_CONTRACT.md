# 证据契约 · 外联脚手架 v0

## 一次事务

一件交付 = 件 + 账 + 印 + 取刻 + 复跑，缺一不算验收。

| 要素 | 要求 |
|---|---|
| 件 | 路径、bytes、sha16 |
| 账 | 投递台账/任务板行，含 to/from/状态 |
| 印 | 件自身 sha16，非引用件 |
| 取刻 | 本地时区 ISO |
| 复跑 | 命令 + 两次同结果/反例 |

## 禁

- 件到账未记（3480 曾发生，后由 PD 补行）。
- 用引用件 sha16 冒充自身印（CW dbd5… 与 df194…）。
- 手写数字不附 bytes/mtime/命令。
- 用旧证充今证。

## 最小模板

    path: <path>
    bytes: <n>
    sha16: <16hex>
    captured_at: <ISO>
    rerun: <cmd>
    owner: <域主席>
    ledger: <row/id>
    decision: <D-id>

## C15 保鲜（脚本）

    python -X utf8 -B scripts/pa_relations.py freshness <json|文件|-> [--ttl-days 30] [--now <ISO>]
    ⇒ {ok, age_days, expires_at, errors}（29/30 日 ⇒ 0；31 日/未来/坏日期 ⇒ 2；使用错 ⇒ 3；运行错 ⇒ 1）
    python -X utf8 -B scripts/pa_evidence_register.py verify --max-age-days 30
    ⇒ 过期 ⇒ bad reason=stale；未来 ⇒ reason=future；不传 ⇒ 只校形/印（默认不变）
    python -X utf8 -B scripts/pa_evidence_register.py verify [--no-require-owner]
    ⇒ owner 读侧缺省强制（缺/空/非串 ⇒ bad reason=owner）；旧账（无主）用 --no-require-owner 方可读
    python -X utf8 -B scripts/pa_evidence_register.py supersede <path> --sha16 <旧印> --decision <D-id> --owner <席> --reason <文>
    ⇒ 追加 kind=supersede（⛔ 删/改旧行）；verify 将「已 supersede 且当前件已不同」之旧记录归 superseded（⛔ 计 bad）

## 验收门

1. 件、账、印三者可互查。
2. 反例必红（至少 1 正 1 反）。
3. 失败/限制明标，⛔ 冒绿。
