---
type: 报
from: 老板 PA（代发：DSH）
to: 总经理CEO（440488b）
date: 2026-10-30
序号: 3480
类别: 报
status: open
action: 报
动作需求: 请裁对账口径、①六拍④、C-30 PD 真 OV/EV、C-30 PM D1-D8 与验器源
---

# 报 · PA 迭代 40 对账/审计与三阻塞

**动作需求**：请 CEO 裁对账口径与归属、批①六拍④、给 C-30 PD 真证书路径、裁 C-30 PM D1-D8/验器源。

## §〇 一行

`②③④＋C-30 CW 已可验收；① 候④批；C-30 PD 仅剩真 OV/EV；C-30 PM 仍红（R1 余项/R6 G3/R2/R8）；9.0.41 已装未发布；目标 blocked`

## §一 已完成（有据）

| 件 | 判 | 证据（sha16） |
|---|---|---|
| ② 分层 | 绿 | 103/103 rc=0；13 件；最大 799 行；基线 `454e322e6cdc0171`；split_audit `787e8212655e0041` |
| ③ 授权 | 绿 | grants 200/403/deny/409；owner guard 55/55；route_guard 9 passed；`674e9e11aff31777` / `8bcb30796b50af64` |
| ④ 索引 | 绿（v0） | 96 数据行/28 处置/EXIT0；`c34c5c2aca44f6b1`；root 映射 `715718dd06c0de02`；343 候选 `9e259f98a79af66d` |
| C-30 CW | 绿（A2） | 正控 4/4、反控 5/5、54 passed×2；`dbd5feb57fae9547` |
| ① 卫生 | 红 | 审计 `8eb561266c552105`；六拍票 v2 `1b066720cb13f094`；未删一件 |
| C-30 PD | blocked | 9.0.41 Setup `6d7728b088922169`/Valid/TSA；54/54 内包 exe；blockmap `03099574…`；internal.yml `df06f1b37c813954` |
| C-30 PM | 红 | `06_pm.md b086b3cd…`；R1 空件已修；R6 黄；G2 通过（`11_r6_g2.md`） |

9.0.41 已本地安装：`/health` 顶层/build 均 9.0.41，build.commit `348083eb…`，装根 payload 9.0.41，exe ProductVersion 9.0.41.0。**未发布**。

## §二 对账差异（请裁）

| # | 两值/差异 | 根因/现状 | 建议口径 |
|---|---|---|---|
| 1 | v0 **69 行** vs **96 数据行** | 69 为 PowerShell 5.1 ANSI 解码吞 LF 的假数；96 为 v0 实际数据行（97 LF） | 以 96 为准；T45/T58 已复算 |
| 2 | 全域 **652** vs 可复算 **U=450** | 652 仅见 v0 README/分工表，树/命令/正则未留存；本仓 9 种口径 91/345/440/450/580/588/596/443/167，无一=652（最近差56） | 652 不可复算，不沿用；改 U=450；若仍要 652 作验收数，须补口径（D1） |
| 3 | 可释放 **66.53GB** vs **69.29GB** | 66.53 为 T54（9.0.39 前）快照；T61 v2 按 9.0.40/41 重算 | 以 T61 v2 `69,292,758,814B` 为准；⑤前再复量 |
| 4 | 旧 **9.0.38** vs 新 **9.0.41** | 旧装/旧进程；9.0.41 已重打/自签/本地安装 | 以 9.0.41 为当前装根；发布另批 |
| 5 | internal.yml sha512 **≠** 已签 Setup（旧） | T57 前 internal.yml 对未签 exe；T66 后 9.0.41 match=True | 已收口；发布前仍须每次重对账 |
| 6 | **14/14** vs **9/9** | 14=dsh_pa_verify CLI 13+C11；9=活端 `/v9/pa/verify` 自报；两分母无面标；本仓/payload 无 verify.py，活端 404 | G3：验器源入仓/授权外部归属＋面标；未做前 R6 不升绿 |
| 7 | 68/68 指针 repo 内 **0** 可查 | root 是逻辑标签；`_pm` 映射 `D:/paseo-workspace/_pm`，`codex` 映射 `D:/Obsidian/ClawsJoy/ClawsJoy/codex` | 采纳 `PM_DOC_ROOTS`；root 落库由 PD |
| 8 | **343 候选** vs **303 建议/40 存疑** | 343 指针层全过；题旨层 309 命中/8 不合/26 不可判；真跨账 10 id | 303 候补录、40 存疑；未验不入册；终判权在 PM/CEO |

## §三 审计/安全

- **PFX**：仓内 0；外部 `D:\paseo-workspace\_secrets\ClawsJoy_Internal.pfx`，2,590B，sha16 `21efc82549da6e3a`；签名须显式外部路径。
- **个人路径**：源 `config/pa/pa_registry_pilot_v2.json` 0 处；payload/win-unpacked seed 均 `0c6f`；9.0.41 setup 内 seed 0c6f。
- **数据**：payload 无 `data/profile/notes/workspace/seed`；未删数据、未动用户数据。
- **签名**：9.0.41 Setup Authenticode Valid、CN=ClawsJoy Internal、公开 TSA；publisherName 由证书 CN 自动写入。**净机仍 Unknown Publisher**（自签非公开身份）。
- **清理**：①票 v2 69.29GB；候选删除/外移，回滚 30 天；**未批未动**。
- **发布**：9.0.41 仅本地安装；`_share`/公开分发未动。

## §四 请 CEO 裁/办

### D1 ① 六拍④

- 票：`PA-ITER40-CLEAN-001 v2`（`1b066720cb13f094`），69.29GB；①已 ②已 ③已 **④待批** ⑤未执行 ⑥待。
- **请裁**：批/不批；批则按票外置 `_trash` + `_MANIFEST` + 30 天回滚，⑤后四验。

### D2 ④ 对账口径

- **D1**：652 是否必须作验收数？若必须，请给树/命令/正则；否则按 **U=450** 定案。
- **root**：是否采纳 `PM_DOC_ROOTS`（`_pm`/`codex`/`_auto`/信通）为唯一映射？
- **候选**：303 是否可入册、40 存疑谁终判（PM/CEO）。

### D3 C-30 PD 真 OV/EV

- 现状：9.0.41 内部自签链已收口；**真 OV/EV 未得**，净机 Unknown Publisher。
- **请裁**：给真证书/采购路径；或明确接受“内部自签内测边界”，PD 按内测判，不冒绿。

### D4 C-30 PM 产品决策/验器源

- **D3**：C15 ttl/owner 取值；**D8**：反目标清单定稿；**D2**：真源以外部指针为准。
- **G3**：提供/授权 WSL 旧验器源，或恢复 `/v9/pa/verify`；给 14/14 与 9/9 的面标映射。
- **R2/R8**：确认主责/是否本迭代补。

## §五 界/候

**界**：未删件、未发布、未上传；9.0.41 仅本地安装；未改未授权产品码；所有件标 `代发: DSH（PA）`。
**候**：CEO 裁 D1-D4；候老板一字；目标 blocked，不自动续跑。

**证据索引**：`docs/reports/pa_iter40/ACCEPTANCE.md`、`README.md`、`01_hygiene.md`、`03_index.md`、`04_pd.md`、`05_cw.md`、`06_pm.md`、`07_cleanup_ticket_t61.md`、`10_r6_recheck.md`、`11_r6_g2.md`、`pm_root_map_t58.md`、`pm_candidates_t60.csv`。

（完 —— 本件末行 · LF 终 · 候 CEO 裁）
