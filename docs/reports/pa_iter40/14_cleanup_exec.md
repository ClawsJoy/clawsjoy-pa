# PA 迭代40 · T70 ①**外置执行（不 purge · 9.0.42 后）**

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1｜写域: `dist/pa_shell`（迁移动作）＋本件 `docs/reports/pa_iter40/14_cleanup_exec.md`
> 取刻: 2026-10-30T09:52:13～10:09:27+08:00｜**⑤ 执行（CEO D1 已批外置／老板按推荐）**｜**⛔ purge ／ ⛔ delete ／ ⛔ 动 data/ ／ ⛔ 动现役 payload ／ ⛔ 动最新 setup**
> 依据: T54/T61 六拍票（PA-ITER40-CLEAN-001 v2）；task-70 令「候选移 D:\paseo-workspace\_trash_pa_iter40_<ts>\（robocopy\ /MOVE + _MANIFEST），30 天回滚；⑤后四验」

## 〇 结果（一句话）

**已外置 409,627 文件 / 72,784,438,237 B 至 `D:\paseo-workspace\_trash_pa_iter40_20261030_0952`（_MANIFEST ＋ _PLAN），仓内对应件已移出；⛔ 未 purge、⛔ 未 delete；白名单（payload 9.0.42/最新 setup/最新 2 份 prev/.cer/data）逐字未动；30 天内可回滚。**

## 一 批准与硬边界

- 批准：CEO D1「批外置」；老板按推荐；⑤＝外置不 purge（task-70 description）。
- ⛔ 本执行不 purge、不物理删除、不碰 `data/`、不碰现役 payload、不碰最新 setup、不碰 `_secrets` PFX。
- 白名单（执行前后逐字验，见 §六③）：`dist/pa_shell/payload/`、`dist/pa_shell/setup/` 之 9.0.42 集＋`win-unpacked/`＋`internal.yml`＋`builder-debug.yml`、最新 2 份 `payload.prev_*`、`ClawsJoy_Internal.cer`、`data/**`、git 工作树。

## 二 执行前快照（9.0.42 · 09:52–09:55）

| 项 | 值 | 取刻 |
|---|---|---|
| .before_* 全树 | 3,875 / 160,057,701 B（fp16 b543fac4743981a0） | 09:47:24 |
| dist | 78,445,928,013 B / 442,354 件 | 09:47–09:51 |
| setup* | 43,443,762,499 B（setup 41,864,367,010 ＋ hist 1,579,395,489） | 09:47–09:51 |
| payload.prev_* | 36 份 / 408,098 件 / 33,851,648,961 B（最新 0938_9041、0846_9040） | 09:47–09:51 |
| git status | 184 行 = 66 M + 118 ?? | 09:47 |
| 现役 payload | 9.0.42 · version.json sha16 **7c52a74b5b3047aa** · commit 63002c7b… | 09:47 |
| 最新 Setup | ClawsJoyPA-Setup-9.0.42-x64.exe 806,868,992 B／sha16 **63a47980f0875401** | 09:47 |
| PFX | 仓内 **0**；.cer 1（780 B／6a2a2df26f476aac） | 09:47 |

## 三 核（白名单／PFX／B6 活域／唯一副本）

| 核 | 结果 | 据 |
|---|---|---|
| 白名单 | 全部在且哈希不变（§六③） | payload/Setup/unpacked/prev/cer/data |
| PFX | **仓内 0**（全树扫描 0）；.cer 保留；外部 `_secrets` 不在本动 | 09:47 / 10:09 |
| B6 活域（codex ／ _pm ／ _ctx_落盘 ／ _L3_静窗 ／ _seats） | **非活域**：皆非 reparse；最近 24h 新写 **0**；最后写 ≤ 2026-10-29 01:31 ⇒ 可外置 | 09:47 取刻逐目录 |
| `_tmp/` | **活域**：最近 24h 3,766 件（最后 2026-10-30 08:44）⇒ **排除，不动** | 09:47 |
| 唯一副本（.before） | 59 件其 base 已不存在（唯一副本）⇒ **排除保留**；data 下删除候选 1,288 件按⛔data 亦排除 | 计划 09:52–09:55 |
| tracked 件 | 删除候选内 git-tracked **0** ⇒ 不碰产品码 | 计划 |
| 计划禁止项 | 白名单/ data/ 9.0.42/payload/keep prev/cer 命中 **0** | 09:56 执行前断言 |

## 四 移出清单（已执行 · 组级）

| 组 | 内容 | 件 / 字节 |
|---|---|---|
| A | __pycache__ 163 dirs ＋ core/pa/*.py.new 11 ＋ _tmp_pa016_live.py | 1,866 / 23,020,121 |
| B1 | .before_*（922? 实移 921；data/唯一副本/keep 除外） | 921 / 43,773,785 |
| B2 | setup 旧版本集 9.0.11–9.0.41（留 max 9.0.42） | 118 / 39,517,457,584 |
| B3 | setup_nsis ／ _r2 ／ _r3 ／ setup_v2 四目录 | 10,812 / 1,579,395,489 |
| B4 | payload.prev_* 34 dirs（留最新 2 份） | 384,860 / 31,550,621,267 |
| B5 | .rollback_codex ／ .rollback_dsh | 321 / 5,567,700 |
| B6 | _pm ／ codex ／ _ctx_落盘 ／ _L3_静窗 ／ _seats 五目录 | 10,807 / 65,104,784 |
| B7 | MEMORY.md.retired_*/before_*/sha256（MEMORY.md 留） | 11 / 93,337 |
| **并集** | 去重后 | **409,627 / 72,784,438,237** |

> 组级和 409,716 / 72,785,034,067；并集少 89 件 / 595,830 B ＝ B1 已移件落在 B6 目录内（后随整目录一并外置，不重复计）。

## 五 外置落点与 _MANIFEST（可回滚）

- 落点：`D:\paseo-workspace\_trash_pa_iter40_20261030_0952`（与仓同卷 D:）。
- `_MANIFEST.txt`：45,788,862 B；列 `relpath|bytes`；**409,627 行**；排序后 sha256 前16 ＝ **f0f57b73eb76ce83**。
- `_PLAN.tsv`：91,693 B（执行前计划：类型/组/源/字节）。
- **回滚**：`robocopy <trash>\<相对> <仓>\<相对> /E /MOVE`（或按 _MANIFEST 逐件移回）；**保留至 2026-11-29（30 天）**；到期物理销毁须另票（⛔ 本单不 purge）。

## 六 ⑤后四验回读（10:01–10:09 取刻）

| 验 | 期望 | 实测 | 判 |
|---|---|---|---|
| ① .before | 全树按计划减（data 不动） | **2,335 / 106,507,482 B**（fp16 1e16d423b6a7757a）；其中 **data 2,059 / 103,348,472 B 逐字未动** | **绿**（非 data 减 921 ＋随 B6 整目录外置其 keep 件；data 全在） |
| ② dist | 减 B2+B3+B4 ＝ 72,647,474,340 | **5,798,453,673 B**（78,445,928,013 − 72,647,474,340 ＝ 精确）；setup* **2,346,909,426 B**；hist 四目录 **已移出**；setup 版本 **唯 9.0.42**；prev **2 份 / 2,301,027,694 B** | **绿** |
| ③ 白名单 | 逐字不变 | payload version sha16 **7c52a74b5b3047aa**；seed **0c6fd929884420a8**；Setup 9.0.42 **63a47980f0875401**；win-unpacked seed **0c6f**；.cer **6a2a2df26f476aac**；**PFX 仓内 0**；data top 34／173,822 件／4,687,506,195 B | **绿** |
| ④ 仓状 | 无产品码改动／无 tracked 删／PFX 0 | git **159 行 = 66 M + 93 ??**（前 184＝66 M + 118 ??；−25 为移出的 untracked/ignored 候选）；**D=0**；M 66 不变；PFX 0 | **绿** |

## 七 残余（**未移**，照实）

- `_tmp/`：活域（24h 3,766 件；21,539 件／332,168,053 B）—— 按活域纪律没动。
- .before：data 下删除候 1,288 件（⛔data）；唯一副本（base 缺失）59 件；B1 keep 集；均留在仓内。
- 未动：`data/**`、现役 payload、最新 setup 集、最新 2 份 prev、.cer、git 工作树、`_secrets`。
- 本单**无 purge／无物理删除**；trash 全量可回滚。

## 八 证据四件套（径 ＋ sha16 ＋ 取刻 ＋ 复跑）

| # | 对象 | sha16/计数 | 取刻 | 复跑 |
|---|---|---|---|---|
| E1 | trash 合计 | 409,627 件 / 72,784,438,237 B（含元数据 409,629／72,830,318,792） | 10:00:52 | R1 |
| E2 | _MANIFEST | fps16 **f0f57b73eb76ce83**；409,627 行；45,788,862 B | 10:00:52 | R2 |
| E3 | dist 前/后 | 78,445,928,013 → **5,798,453,673** | 09:47 / 10:01 | R3 |
| E4 | Setup 9.0.42 | **63a47980f0875401**（806,868,992 B） | 09:47 | R4 |
| E5 | payload 9.0.42 | version **7c52a74b5b3047aa**；seed **0c6fd929884420a8** | 09:47 / 10:01 | R4 |
| E6 | data | 2,059 .before／103,348,472 B；top 34；173,822 件／4,687,506,195 B | 10:01／10:09 | R5 |
| E7 | B6 活域 | 5 目录 recent24h=0；非 reparse；最后写 ≤10-29 01:31 | 09:47 | R6 |
| E8 | PFX | 仓内 0（全树）；.cer 1 | 09:47／10:09 | R7 |
| E9 | git | 159＝66 M+93 ??；D=0 | 10:09 | R8 |

```powershell
# R1 trash 合计
function DS($p){$n=0;$b=[int64]0; foreach($x in [IO.Directory]::EnumerateFiles($p,'*',[IO.SearchOption]::AllDirectories)){try{$n++;$b+=([IO.FileInfo]::new($x)).Length}catch{}}; [pscustomobject]@{N=$n;B=$b}}
DS 'D:\paseo-workspace\_trash_pa_iter40_20261030_0952'
# R2 manifest fp16
$mf='D:\paseo-workspace\_trash_pa_iter40_20261030_0952\_MANIFEST.txt'; $l=[IO.File]::ReadAllLines($mf)|Where-Object{$_ -and -not $_.StartsWith('#')}; "LINES=$($l.Count)"
$h=[Security.Cryptography.SHA256]::Create(); ((($h.ComputeHash([Text.Encoding]::UTF8.GetBytes((($l|Sort-Object)-join [char]10))))|ForEach-Object{$_.ToString('x2')}) -join '').Substring(0,16)
# R3 dist/setup/prev
DS 'dist'
DS 'dist/pa_shell/payload'; DS 'dist/pa_shell/setup'
(Get-ChildItem 'dist/pa_shell' -Directory | Where-Object {$_.Name -like 'payload.prev_*'}) | ForEach-Object { $_.Name }
# R4 whitelist
(Get-FileHash 'dist/pa_shell/payload/version.json' -Algorithm SHA256).Hash.ToLower().Substring(0,16)
(Get-FileHash 'dist/pa_shell/payload/config/pa/pa_registry_pilot_v2.json' -Algorithm SHA256).Hash.ToLower().Substring(0,16)
(Get-FileHash 'dist/pa_shell/setup/ClawsJoyPA-Setup-9.0.42-x64.exe' -Algorithm SHA256).Hash.ToLower().Substring(0,16)
# R5 data
Get-ChildItem 'data' -Recurse -Force -File -Filter '*.before_*' | Measure-Object Length -Sum
(Get-ChildItem 'data' -Force | Measure-Object).Count
# R6 B6 活域（已移出，改核 trash 目标）
foreach($d in '_pm','codex','_ctx_落盘','_L3_静窗','_seats'){ 'TRASH_EXISTS=' + $d + '=' + (Test-Path (Join-Path 'D:\paseo-workspace\_trash_pa_iter40_20261030_0952' $d)) }
# R7 pfx
(Get-ChildItem . -Recurse -Force -File -Filter '*.pfx' -ErrorAction SilentlyContinue | Measure-Object).Count
# R8 git
git status --porcelain | Measure-Object -Line
```

## 九 界

- 本单唯「移」不「删」；未 purge；30 天回滚窗口至 2026-11-29。
- 未动 data/**、现役 payload、最新 setup 集、最新 2 份 prev、.cer、git 工作树、`_secrets` PFX。
- 唯一写入：本件 ＋ dist/pa_shell 迁移动作；⛔ 第二写者。

（本件完 · T70 外置不 purge · ⑤后四验）
