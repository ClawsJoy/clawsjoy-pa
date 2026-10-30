# PA 迭代40 · T72 CW 印源追溯（3480 附录 · 13_cw_provenance）

> 代发: DSH（PA）｜执行席: agents-dev｜WIP=1（本单）｜写域: docs/reports/pa_iter40/13_cw_provenance.md（本件唯一写入）
> 取刻: 2026-10-30T09:40:03+08:00｜⛔ 代 CW 认（本件只出**文件＋哈希**实证，CW 之主张以 CW 本人为准）｜⛔ 改 3480／任何已登记件
> 题：CW 指出 3480 所记 dbd5feb57fae9547 非其出件，其印为 df194a79b63be125 —— 本件核两印之**源径**。

## 〇 一句结论

dbd5feb57fae9547 **不是 CW 出件之印**：复算 ≡ docs/reports/pa_iter40/05_cw.md（13,192 B）—— **PA 之 T47 验收报告件（执行席 agents-dev）**，即「**关于 CW 分内 A2 的 PA 跑测/报告**」，⛔ CW 之回件。
CW 回件之印 df194a79b63be125 复算 ≡ _ctx_落盘\CW_PM3407_回_A2_grants只读面与fail_closed_v1_20261027.md（3,761 B · 2026-10-27T08:20:24+08:00；侧车 .sha256 载同印且 MATCH=True）；文件头自述「席：CW b2a5182 ｜ 刻：2026-10-27 08:20 ｜ 令：PM 3407」。
⇒ 3480（12_ceo_escalation.md 序号 3480）之「C-30 CW」行把 **PA 报告件之印** 配于 CW ⇒ **印-件-名错位**（印对件、件非 CW）；**⛔ 本件不改 3480**，只出追溯与改法建议（§四）。

## 一 两印复算（一手 · 两跑同）

| 印（sha16） | 源径（仓相对） | 字节 | 取刻（mtime） | 本件复算 | 归属（据） |
|---|---|---|---|---|---|
| **dbd5feb57fae9547** | docs/reports/pa_iter40/05_cw.md | 13,192 | 2026-10-30T07:18:43+08:00 | sha256 dbd5feb57fae95479cd7f56e4744bc0e23f8746132d0ddadde8f722b671a9e6d（两跑同） | **PA 报告件**：T47「C-30 CW · A2／功能验收」报告，件头自述「代发: DSH（PA）｜执行席: agents-dev」；任务板 T47 owner=agents-dev（completed） |
| **df194a79b63be125** | _ctx_落盘\CW_PM3407_回_A2_grants只读面与fail_closed_v1_20261027.md | 3,761 | 2026-10-27T08:20:24+08:00 | sha256 df194a79b63be125bf24b0e09e18d95acd1830c48819773d21e57dd33186b34d（两跑同）＋侧车 .sha256 复算 **MATCH=True** | **CW 回件**：件头「席：CW b2a5182 ｜ 刻：2026-10-27 08:20 ｜ 令：PM 3407」；内容为 A2 grants 只读面 ＋ _load fail-closed 之回（交三件／四判据） |
| e718e8b523cdcb82 | docs/reports/pa_iter40/12_ceo_escalation.md（序号 3480 之本地载体） | 5,828 | 2026-10-30T09:05:54+08:00 | sha256 e718e8b523cdcb82c47e72653b377281616a63f11666a317058084911a73153d | **3480 报告本体**（README·T68 记 _报_总经理CEO_3480_PA迭代对账审计与三阻塞_20261030.md 5,828 B／sha16 e718e8b523cdcb82 —— 与本件同量同印） |

复跑命令（powershell）：

```
cd D:\clawsjoy_v9
python -X utf8 -B -c "import hashlib,pathlib; [print(f, hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()[:16]) for f in [r'docs/reports/pa_iter40/05_cw.md', r'_ctx_落盘/CW_PM3407_回_A2_grants只读面与fail_closed_v1_20261027.md']]"
# ⇒ docs/reports/pa_iter40/05_cw.md dbd5feb57fae9547
# ⇒ _ctx_落盘/CW_PM3407_回_A2_grants只读面与fail_closed_v1_20261027.md df194a79b63be125
# 侧车校验：
python -X utf8 -B -c "import hashlib,pathlib; f=pathlib.Path(r'_ctx_落盘/CW_PM3407_回_A2_grants只读面与fail_closed_v1_20261027.md'); sc=pathlib.Path(str(f)+'.sha256').read_text(encoding='utf-8').split()[0]; print('MATCH=', sc==hashlib.sha256(f.read_bytes()).hexdigest())"
# ⇒ MATCH= True
```

本刻两跑：09:39:30 与 09:40:03，两印皆同（见 §五）。

## 二 dbd5 之实（PA 跑测/报告件 · ⛔ CW 出件）

- 件：docs/reports/pa_iter40/05_cw.md ＝ T47 报告（A2 正控 4 ＋ 反控 5、UI 五态、测试 54 passed×2）。
- 件头（原文 · L3）：「代发: DSH（PA）｜执行席: agents-dev｜WIP=1（本单）｜写域: docs/reports/pa_iter40/05_cw.md」
- 定位：件名之「C-30 CW」指**验收对象**（CW 分内之 A2），⛔ 指**产出者**；产出者为 PA 侧（agents-dev）。
- 佐证：任务板 task-47（PA迭代40 T47：C-30 CW A2/功能验收）owner = agents-dev ／ completed；T47 回报已投 Lead。
- ⇒ **dbd5 是「PA 的验收报告」之印**；3480 之 C-30 CW 行若欲表「CW 出件」，⛔ 可用 dbd5。

## 三 df194 之实（CW 回件 · 源径已寻得）

- 径：_ctx_落盘\CW_PM3407_回_A2_grants只读面与fail_closed_v1_20261027.md（仓根下 _ctx_落盘，**非** _pm／paseo-pm／codex／信通）。
- 量／刻：3,761 B ／ 2026-10-27T08:20:24+08:00（与侧车 .sha256 同刻）。
- 头三行（原文）：
```
# 回 · PM 3407 · A2 grants 只读面 ＋ _load fail-closed

- 席：CW b2a5182 ｜ 刻：2026-10-27 08:20 ｜ 令：PM 3407（交三件 · 判据四条）
- 界：只动我域 ＋ core/pa/** ＋ tests/unit/**｜⛔ 动 ③B（PD 域 41 条写路由）｜⛔ 改 _pm｜⛔ 同批改前端
```
- 内容形态：交三件（GET /v9/pa/grants 只读 ／ _load fail-closed ／ 测试，回件自述 5,041 B·13 用例）＋四判据 rc 原文。
- ⚠ 版本照实：**df194 对应「回件 .md」**；今仓内 tests/unit/test_pa_grants_3407.py 为 6,084 B／14 用例（ec32bec8c052145c，后批 3433 增「missing 读面 200」之测）⇒ **⛔ 以 df194 当今测试件之印**（两者不同物）。
- ⭐ 旧记之缺口：docs/reports/_pa_groundwork_20261027/10_监督_A2与TD3410_v0.md:41 记「回件 ⚠**未寻得** 3,761 B ／ df194a79b63be125（_pm／paseo-pm／codex／信通 皆无此 B 之件）；请 PM 给径」——**本件即给径**：_ctx_落盘（仓根）下该件实在（3,761 B，印合）。该件之更正属另单（⛔ 本件改）。

## 四 3480 之登记现状（只读引用 · ⛔ 改）

| 件 | 行 | 现文（摘 · 原文之代码段以『』代引号） |
|---|---|---|
| docs/reports/pa_iter40/12_ceo_escalation.md（序号 3480） | :28 | ｜ C-30 CW ｜ 绿（A2） ｜ 正控 4/4、反控 5/5、54 passed×2；『dbd5feb57fae9547』 ｜ |
| docs/reports/pa_iter40/ACCEPTANCE.md（sha16 8f26b5dffe5233c0） | :26 | ｜ CW ｜ 绿（A2） ｜ 05_cw.md sha16 dbd5feb57fae9547；… ｜（**径已对，唯「CW」行之主体易读作 CW 出件**） |
| docs/reports/pa_iter40/08_pm_remediation.md（c356e7834271a645） | :105 ／ :209 | 引 05_cw.md dbd5feb57fae9547 作「A2 现状据」／证据表 |
| docs/reports/pa_iter40/README.md（b320be8fa12047c0） | :35 ／ :123 | T68 记 3480 投递件 e718e8b523cdcb82（与本件 12_ceo_escalation.md 同印） |

**本件未改上述任一件**（前刻 mtime 照旧：12_ceo 09:05:54 ／ ACCEPTANCE 08:59:36 ／ 08_pm 07:38:51）。
改法建议（交 Lead／PM 裁，⛔ 我改、⛔ 我代 CW 认）：

- ⒜ **3480 之 C-30 CW 行印改 df194a79b63be125**（CW 回件之实），并附径 _ctx_落盘\CW_PM3407_回_…；
- ⒝ 或保留 dbd5 但**改标**「PA 验收报告（T47 05_cw.md）」，与 CW 出件分包；
- ⒞ 或**两印并列**：CW 回件 df194…（3,761 B）＋ PA 验收报告 dbd5…（13,192 B），各标其体。

## 五 复跑（本刻两跑 · 可机械复现）

| 轮 | 取刻 | 05_cw.md | CW 回件 | 侧车 |
|---|---|---|---|---|
| #1 | 2026-10-30T09:39:30+08:00 | dbd5feb57fae9547 ／ 13,192 B | df194a79b63be125 ／ 3,761 B | MATCH=True |
| #2 | 2026-10-30T09:40:03+08:00 | dbd5feb57fae9547 ／ 13,192 B | df194a79b63be125 ／ 3,761 B | MATCH=True |

## 六 证据四件套（径 ＋ sha16 ＋ 取刻 ＋ 复跑）

| 件 | 径 | sha16 | 字节 | 取刻（mtime） | 复跑核 |
|---|---|---|---|---|---|
| PA 报告件 | docs/reports/pa_iter40/05_cw.md | dbd5feb57fae9547 | 13,192 | 2026-10-30T07:18:43+08:00 | 两跑同（§五） |
| CW 回件 | _ctx_落盘\CW_PM3407_回_A2_grants只读面与fail_closed_v1_20261027.md | df194a79b63be125 | 3,761 | 2026-10-27T08:20:24+08:00 | 两跑同 ＋ 侧车 MATCH |
| CW 回件侧车 | 同径 ＋ .sha256 | b43c0a5dbb084cda（侧车件本身之印） | 129 | 2026-10-27T08:20:24+08:00 | 内载 df194… ≡ 复算 |
| 3480 载体 | docs/reports/pa_iter40/12_ceo_escalation.md | e718e8b523cdcb82 | 5,828 | 2026-10-30T09:05:54+08:00 | 与 README T68 记同印 |
| 登记件（只读） | ACCEPTANCE.md ／ 08_pm_remediation.md ／ 10_监督_A2与TD3410_v0.md | 8f26b5dffe5233c0 ／ c356e7834271a645 ／ c39ad3dda3bfeb58 | 5,585 ／ 21,822 ／ 3,687 | 见各 mtime | 未改（只读引） |

## 七 边界（照实）

1. **⛔ 代 CW 认**：本件只给「文件自述 ＋ 哈希 ＋ 侧车」之实证；CW 对其回件/印之主张，以 CW 本人（或 PM/Lead 转述）为准。
2. **⛔ 改 3480**：12_ceo_escalation.md／ACCEPTANCE.md／08_pm／10_监督 皆未动；改法仅**建议**（§四），裁在 Lead/PM。
3. **投递面未核**：3480 之信通**投递原件**在仓外；本件据 README·T68（同 5,828 B／e718…）与本地载体同印，推定同文，**未见投递回执**。
4. 未改产品码/测试；唯写本件（13_cw_provenance.md）。
5. 未扩查其他 sha16（仅题定两印＋其载体/登记件）。

（完 —— 本件末行 · 2026-10-30 · T72 CW 印源追溯）
