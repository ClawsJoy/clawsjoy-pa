# 决策总表 · 外联脚手架 v0

- 一条裁决只写一次；新证据只能“追加”，不能改写已生效裁决。
- 每条必须有 owner、范围、状态、证据、失效/重开条件。

## 字段

| 字段 | 说明 |
|---|---|
| id | D-YYYYMMDD-NN |
| 日期 | 裁决日 |
| 裁决 | 一句话 |
| owner | 最终负责席 |
| 范围 | 适用/不适用 |
| 状态 | proposed/approved/executing/done/blocked |
| 证据 | 径+sha16 |
| 重开条件 | 何时可重议 |

## 已生效（3480）

| id | 裁决 | owner | 状态 | 证据 |
|---|---|---|---|---|
| D-20261030-01 | ①六拍④：批外置（_trash+manifest+30天回滚），⛔ purge；真删候老板 | 老板/CEO | approved | 3480 / 裁件 |
| D-20261030-02 | ④ 652 不沿用，定 U=450；303 候补、40 存疑 | CEO | approved | 3480 |
| D-20261030-03 | C-30 PD 采内部自签内测边界，⛔ 冒绿；真证书候老板 | CEO | approved | 3480 |
| D-20261030-04 | C-30 PM D1–D8 转 PM 域终判；未回前记红 | CEO | transferred | 3480 |
| D-20261030-05 | 9.0.44 内部发布（publisher=ClawsJoy Internal；非真 OV/EV） | PD | done | T84 ledger |
| D-20261030-06 | 9.0.45 内部发布（publisher=ClawsJoy Internal；非真 OV/EV） | PD | done | T87 ledger |
| D-20261030-07 | relations.py 新印（af0f69ca）入账；旧 ad42 标 superseded | PD | done | T90 ledger |
| D-20261030-08 | 真账 supersede ad42（旧印退役，历史保留） | PA | done | T94 ledger |
| D-20261030-09 | 9.0.47 内部发布入账 | PD | done | T97 ledger |
| D-20261030-10 | 3481 CEO 申报件入账 | PA | done | T98 ledger |

## 使用

1. 新裁决先查是否已有同 id/同范围。
2. 有 ⇒ 只引用，不重开；除非触发重开条件。
3. 执行任务必须引用 decision id。
| D-20261030-11 | G3 9/9 最小复制获批：仅 verify.py/旧路由/CLI/旧证/两份清单入 legacy_verify，不改旧库；⛔ WSL 运行时依赖；14/14 暂缓 | 老板 | approved | 老板口述 2026-10-30 |
| D-20261030-12 | C-30 PD 走内部自签内测边界，暂不采购真 OV/EV；对外分发再议 | 老板 | approved | 老板口述 2026-10-30 |
| D-20261030-13 | ① 不 purge；trash 保留 30 天，到期再审 | 老板 | approved | 老板口述 2026-10-30 |
| D-20261030-14 | C-30 PM R8 AG-10 保留 MANUAL；C5/验器源/14-9 面标由 PM 补 | 老板 | approved | 老板口述 2026-10-30 |
| D-20261030-11a | legacy_verify 7+2 本地面签核（C2活端6全等/C10真扫/C12C13 N/A；非route/9-9/14-14；建端另批） | PD/PA | done | T115/T116 |
| D-20261030-11b | G3 7+2 产品化新路径 /v9/pa/verify/legacy_7_2 只读路由获批（非 9-9/14-14；旧 /v9/pa/verify 仍 404；C2活端6/C10真扫/C12C13 N/A；⛔写账） | PD/PA | done | T125/T128 |
| D-20261030-15 | 最终收口：7+2 为 G3 新基线；14/14 退休；旧 `/v9/pa/verify` 继续404；9/9仅历史 | 老板 | approved | 老板口述 2026-10-30 |
| D-20261030-16 | C-30 PM partial accepted：R2 黄/R8 MANUAL/25挂 PM backlog；⛔ 冒绿 | 老板 | approved | 老板口述 2026-10-30 |
| D-20261030-17 | 12777 交 CEO/DSH；PA 只读复核，⛔ 删/清/猜 | 老板 | approved | 老板口述 2026-10-30 |
