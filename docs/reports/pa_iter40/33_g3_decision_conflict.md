# PA 迭代40 · T107 G3 三裁对账（C10/7+2 冲突）

- 代发: DSH（PA）｜主: lead｜WIP=1
- 取刻: 2026-10-30T14:47+08:00
- 依据: T105 `31_g3_pm_decisions.md` f825a9f8543a2734；T106 `32_g3_pd_decisions.md`；T102

## 一 冲突

| 源 | 口径 |
|---|---|
| PM T105 | **7 PASS＋2 N/A**（C1/C2 以活端6为基；C12/C13 N/A；C10 未单列） |
| PD T106 | C7 可适配；**C10 blocked**（无 last_walk_errors，不得假绿）；C6/C9 可适配；C12–C14 legacy/blocked |

## 二 按 9 检推演（C5 修复后）

| 检 | 判 | 依据 |
|---|---|---|
| C1/C2 | PASS | PM 裁活端6基准 |
| C5 | PASS（修 schema 后） | T105 K1 必修 |
| C6 | PASS | PD 适配 sops_dir |
| C7 | PASS | PD adapter 复刻顶层/静态/归一 |
| C9 | PASS | BASE=5102/health 200 |
| **C10** | **blocked/FAIL** | PD：无 last_walk_errors；旧「skip_scan 未验即 pass」不可用 |
| C12 | N/A | skip_scan 未扫；不计 PASS |
| C13 | N/A | quick 面；full 另 B3 |

⇒ 至多 **6 PASS ＋ 1 FAIL（C10）＋ 2 N/A**，**不是 7 PASS＋2 N/A**。

## 三 请 PM/PD 合裁（未合裁前 ⛔ 建端/⛔ 出绿）

1. **C10** 算 **FAIL**、**N/A**，还是另立 adapter 面？
2. PM 的 **7 PASS 第七条**是哪条？若把 C10 算 PASS，请说明与 PD blocked 如何相容；
3. 最终验收口径：**6+1+2**，还是 C5/C7/C10 另加 adapter 后重算？
4. 若无法合裁：G3 9/9 记 **blocked**，保留旧面，不建端。

## 四 界

- 本件只对账，不建端、不改码、不替 PM/PD 裁；
- C12/C13 N/A 不充 PASS；C10 blocked 不充 PASS；
- 旧 9/9 仅历史，不作今日证。

（完）