# PA 迭代40 · T103 G3 9/9 不可达/挂起

- 代发: DSH（PA）｜主: lead｜WIP=1
- 取刻: 2026-10-30T14:45+08:00
- 依据: T102 `28_g3_route_b4.md` b2c0b0b9631f01fb；D-11

## 一 判

旧 9/9 quick 面直跑：**1 绿 / 5 红 / 1 未录 / 2 N/A**，**9/9 不可达**。

| 检 | 判 | 因 |
|---|---|---|
| C1 | 红 | 现役 roster.py 无 obsidian_brain（B4） |
| C2 | 红 | roster.json/活端无 obsidian_brain（B4） |
| C5 | 红 | `_KNOWLEDGE_FILES` schema 漂移（sandbox_rel/无 rel）⇒ KeyError，塌 C6–C13 |
| C6 | 未录 | 修 C5 后可达 PASS |
| C7 | 红 | 无 `_scan_excluded`（B2） |
| C10 | 红 | 无 `_scan_excluded`/`last_walk_errors`（B2） |
| C12 | N/A | skip_scan 自动 True，非真验 |
| C13 | N/A | quick 面自动 True；full 另缺清单 B3 |
| C9 | 绿 | health 200，需 BASE 5102 适配 |

## 二 结论

- **B4 不是唯一阻断**：补 obsidian_brain 仍被 C5 schema、C7/C10 API 挡住；
- 因此**不建 9/9 假端**，不把旧证 9/9 当今日绿；
- 14/14 仍按 D-11 暂缓。

## 三 两方案（候 PM/PD 三裁）

- **A 重基线后 9/9**：只动 legacy_verify；判据=skip_scan 输出 9 条无缺项/三态/C12-C13标N/A/反例必红/面标/旧证留档/两跑同数；需 D-11 扩权＋三裁。
- **B 保留旧面 blocked**：明标 blocked，下迭代再议。

建议 A，但**不代裁**。

（完）