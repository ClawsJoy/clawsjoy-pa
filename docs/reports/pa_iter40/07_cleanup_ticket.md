# PA 迭代40 · T54 ①卫生清理**六拍票**（PA-ITER40-CLEAN-001）

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1（本单）｜写域: `docs/reports/pa_iter40/07_cleanup_ticket.md`（本件唯一写入）
> 取刻: 2026-10-30T07:36:57～07:50:10+08:00｜**⛔ 未删一件** ／ ⛔ 未改产品码 ／ ⛔ 未第二写者
> 票之性质: **只出票，⛔ 不执行**；六拍之 ④ 未批 ⇒ ⛔ 动。依据：T42 `01_hygiene.md`（sha16 8eb561266c552105）；六拍模板（来源见 §一）。

## 〇 一页（候 ④）

| 项 | 值 |
|---|---|
| 票号／状态 | **PA-ITER40-CLEAN-001** ／ **待 ④ 批准**（CEO/老板；六拍第④步须 CEO 批） |
| 快照可释放 | **66,528,019,501 B ≈ 66.53 GB**（十进制；07:47 快照；07:51 重算 66,527,543,089 B；T55 在建，执行前复量） |
| 分组 | **可删** 355,190,838 B（5 项）／**需六拍** 66,172,828,663 B／**保留** 见白名单 |
| 硬边界 | ⛔ 本迭代不删；⛔ 不碰 data/**、现役 payload、最新 setup、_secrets；④ 未批 ⛔ 动 |
| 时点风险 | **T55 正在重打 9.0.39**（07:40–07:46：新 payload.prev_20261030_0740_9038、Setup 9.0.39、build-9.0.39.log）⇒ **执行前必复量**（§四/§六） |

## 一 六拍模板（本票填写 · 沿用仓内口径）

模板来源（一手）：`codex/2026-09-21-codex-⑤wps_office已落LIVE_生效待窗.md` L5 —— 「①交技总 ②核实（本机实读）③方案（含回退路径）④CEO 已批 ⑤发起人做 ⑥通知到」；`docs/reports/_pa_groundwork_20261027/05_目标追溯_C30三分工_v0.md` L74 ——「六拍第④步须 CEO 批 ⇒ 出方案 ⇒ CEO 批 ⇒ 发起人做」；`14_作战计划_72h_v1.md` P2-1 ——「六拍 ④ 批 ＋ 四验回读」。

| 拍 | 内容 | 本票状态 | 主/据 |
|---|---|---|---|
| ① | 交件/出票（含清单＋回退） | **已**（本件） | PD · 本件 sha16 落笔后取 |
| ② | 核实（本机实读 · 可复跑） | **已**（§二/§六 R1–R8） | PD · 取刻见各表 |
| ③ | 方案（删/留/回滚/验证） | **已**（§三/§四/§五） | PD |
| ④ | **批准** | **待**（CEO/老板） | 六拍第④步；未批 ⛔ 执行 |
| ⑤ | 执行（发起人做） | **待 ④ 后**；**本迭代 ⛔** | PD/指定运维；T55/T56 完成且复量后再动 |
| ⑥ | 通知到（回执 ＋ 四验回读） | **待** | 回执帖 ＋ 技总/相关席；§五 四验 |

## 二 快照（任务基线 ⇄ 本票实测 · 同刻可复算）

| 项 | 任务基线 | 本票快照 | 差/据 | 取刻 |
|---|---|---|---|---|
| .before_*（全树） | **3,875 / 160,057,701 B** | **3,875 / 160,057,701 B**（fp16 **b543fac4743981a0**） | 同（未变） | 07:36:57–07:42:34 |
| dist（全树） | **69,805,073,833 B** | **69,805,071,176 B**（395,859 件） | −2,657 B（T55 在建巨动前的秒级差） | 07:36:57–07:42:34 |
| setup*（setup／setup_nsis／_r2／_r3／setup_v2） | **39.40 GB** | **39,404,961,713 B**（22,617 件） | 同 | 07:36:57–07:42:34 |
| payload.prev_* | **29.25 GB** | **32 份 / 361,622 件 / 29,249,596,099 B**（T55 后又生 9038） | 同口径；T55 新增 **payload.prev_20261030_0740_9038** | 07:42:34 |
| git status | **174 行** | **175 行 = 62 M + 113 ??**（fp16 **a1c8bc64c1282520**） | +1（疑 T55/T56 新件；本席未写产品码） | 07:37:03 / 07:48:03 |
| 现役 payload | 洁净 | **version 9.0.39**（version.json 197 B · sha16 **b8191e0678c4f8e4** · commit 56d80f3c… · built 2026-10-30T07:40:26+0800）；种子 0c6f | T55 已把载荷升 9.0.39 | 07:50:10 |
| 最新 setup | 9.0.38 | **9.0.39**：Setup 806,500,248 B（07:45:58）＋blockmap 836,770 B＋build log 18,246 B | T55 出包中 | 07:50:10 |
| PFX | 已移出／0 | **仓内 PFX = 0**（全树扫描 0；git 0；targeted 0）；**PFX 0**；.cer 1（780 B · sha16 6a2a2df26f476aac） | T53 已移出；`D:\paseo-workspace\_secrets\ClawsJoy_Internal.pfx` 2,590 B（T46 实测 sha16 21efc82549da6e3a）**保留，⛔ 本票范围** | 07:34 / 07:42:34 |

> ⚠ **动态警告**：07:40–07:50 期间 T55 正在重打 9.0.39（新 payload／Setup／payload.prev_9038），故 §三 仍按**取刻快照**给数；**执行（⑤）前必须重跑 §六 并在票上附着新快照**（否则删错「最新」）。

## 三 分组清单（可删 ／ 需六拍 ／ 保留）

### 3.A 可删（低风险、可再生；仍须 ④；**本迭代 ⛔**）

| 项 | 件/字节 | 据 | 回滚性 |
|---|---|---|---|
| `_tmp/` | 21,547 / **332,208,139** | pytest/工具临时根（07:37:03） | 可再生（留最近 1 轮亦可） |
| 源码树 __pycache__＋.pyc | 163 dirs / 1,852 / **22,718,230** | core/web/scripts/tests/docs/config/shell/routes/tools/agents/engine | 复跑即生 |
| core/pa/*.py.new | 11 / **256,808** | 删前逐件 diff 与主档等价（T42 已列） | 若等价则无值 |
| `_tmp_pa016_live.py` | 1 / **7,661** | 一次性探针 | 无 |
| `.pytest_cache` | 0 / **0** | 空 cache | 无 |
| **小计** | **355,190,838 B** | — | — |

### 3.B 需六拍（destructive／发行物／历史／证据链；**本迭代 ⛔**）

| 组 | 项（精确） | 件/字节 | 保留规则（执行时复算） | 风险 |
|---|---|---|---|---|
| B1 | **.before_*** 全树删除集：按「同 base 留最新 1 份（含 .sha256 伴件）」⇒ 删 **2,581 / 136,392,734 B**；留 **1,294 / 23,664,967 B**（删/留 fp16 **1813fcca2ef940a8** / **17166831fab8f2c8**） | 2,581 / 136,392,734 | 每 base 最新 1 份；其余删（可选：30 天外） | 备份历史；删后不可回（须移外置） |
| B2 | **setup 旧版本集**（setup 目录内）：版本集 **9.0.11–9.0.38 共 28 版**；07:47 实测 107 件／36,287,186,452 B；**07:51 复量 80 件／36,286,710,040 B**（T55 在建变动；执行按公式重算） | 107 / 36,287,186,452（07:47） | **留 max 版本集**（07:47：3 件／807,355,264 B；07:51：2／807,337,018 B；执行取 max）＋win-unpacked＋internal.yml＋builder-debug.yml | 旧安装包历史；不可回 |
| B3 | **setup_nsis ／ setup_nsis_r2 ／ setup_nsis_r3 ／ setup_v2** 整目录 | 10,812 / 1,579,395,489 | 全删（历史尝试：9.0.1／9.0.11 旧链） | 历史；不可回 |
| B4 | **payload.prev_***：32 份留最新 2（快照 **payload.prev_20261030_0740_9038** 1,150,512,584 B ＋ **…_0646_9037** 1,150,507,932 B），余 **31 份 / 350,003 件 / 28,099,088,167 B** 删 | 350,003 / 28,099,088,167 | 留最新 2；余删（可改「留 1」更省） | 回滚用；保留 2 份即可 |
| B5 | `.rollback_codex` ／ `.rollback_dsh` | 319／2 · 5,507,271／60,429 | 先归档外置；仓内不留 | 回滚快照；不可回 |
| B6 | `_pm` ／ `_ctx_落盘` ／ `_L3_静窗` ／ `_seats` ／ `codex` | 10,114／272／236／7／178 · 55,200,357／4,122,404／4,974,075／22,267／785,681 | 归档外置后删；或保留 `codex/`（历史正文） | 会话/历史产物 |
| B7 | `MEMORY.md.retired_*` 9 ＋ `MEMORY.md.before_*` 1 ＋ `MEMORY.md.sha256` 1（**MEMORY.md 本人保留**） | 11 / 93,337 | 只删 retired/before/sha；**MEMORY.md 留** | 记忆归档 |
| **小计** | — | **66,172,828,663 B**（07:47 快照；07:51 重算 66,172,352,251 B，差 −476,412 由 T55 在建所致） | — | — |

### 3.D 清单指纹（供 ④ 后逐字核；取刻 2026-10-30T07:51:18+08:00）

指纹 ＝ 「排序后 path|size 行」之 sha256 前16（口径同 T42 fp16）；T55 在建 ⇒ 执行前按 §六 R2/R4 重算，**旧指纹随快照作废**。

| 集 | 件/字节 | fp16 | 备注 |
|---|---|---|---|
| B1 .before 删除集 / 保留集 | 2,581/136,392,734 · 1,294/23,664,967 | **1813fcca2ef940a8** / **17166831fab8f2c8** | 07:47:56 |
| B2 setup 旧集 / max 保留集 | 107/36,287,186,452 · 3/807,355,264（07:51：80/36,286,710,040 · 2/807,337,018） | **a7ca7c32401d4b83** / **e745d77abb8e8592** | 07:51:18；T55 在建 |
| B3 hist 四目录全文件 | 10,812/1,579,395,489 | **41904b4492b61876** | 07:51:18 |
| B4 prev 删除集（按目录 name|bytes 聚合） | 31 dirs/350,003/28,099,088,167 | **675f08c29d5e31a4** | 07:51:18 |
| A core/pa/*.py.new | 11/256,808 | **3f982c7d83216aab** | 07:51:18 |

### 3.C 保留（白名单 · 任何一步皆 ⛔ 碰）

- **现役 payload**：`dist/pa_shell/payload/`（9.0.39；version.json sha16 **b8191e0678c4f8e4**；seed 0c6f ／ sha16 **0c6fd929884420a8**）——执行前后须逐字验。
- **最新 setup 构建集**：`dist/pa_shell/setup/` 内 max 版本集（快照 9.0.39：Setup 806,500,248 B ＋ blockmap 836,770 B ＋ build log 18,246 B；**以执行为准取 max**）＋ `win-unpacked/`（11,695／1,538,354,857）＋ `internal.yml`（360）＋ `builder-debug.yml`（7,718）。
- **最新 2 份 prev**（B4 保留项，2,301,020,516 B）。
- `dist/pa_shell/ClawsJoy_Internal.cer`（780 B／**6a2a2df26f476aac**；公开证书，保留）。
- **data/***（用户数据；本票不量不碰）；git 工作树 **175 行（62 M／113 ??）**（产品码/测试/文档，保留）；docs/tests/new sources／evidence。
- `D:\paseo-workspace\_secrets\ClawsJoy_Internal.pfx`（**仓外**；2,590 B／21efc82549da6e3a；⛔ 本票删除范围；亦不入仓）。

## 四 回滚与执行方案（④ 批后 · 本迭代 ⛔）

**原则**：不删（delete）→ **移外置保管（move）**；保留 30 天可回。

1. 外置桶：`D:\paseo-workspace\_trash_pa_iter40_<yyyyMMdd_HHmm>`（以下称 TRASH）。
2. 干跑：按 §三 生成白名单／删除清单（path｜size），**逐项核对**；写 `_MANIFEST.txt`（路径＋字节＋聚合 sha16）。
3. 断言（任一失败即止）：现役 payload version.json sha16 ＝快照；最新 setup 文件名/size 与快照一致或按「max 版本」重算后一致；**PFX 仓内 0**；TRASH 在仓外。
4. 移：`robocopy <源> <TRASH>\<相对>\ /E /MOVE /R:2 /W:2`，按 A → B4 → B2 → B3 → B1 → B5 → B6 → B7 顺序；每步后打点（件/字节）。
5. 四验回读（§五）＋ 回执（⑥）。
6. 回滚：`robocopy <TRASH>\<相对> <源> /E /MOVE`；按 _MANIFEST 复核件数/字节；30 天后才可物理销毁（另需新票）。
7. **中止条件**：任一步发现白名单内文件、data/**、现役 payload、最新 setup、PFX/密钥、或 T55/T56 仍在写；或件/字节与清单偏差 >0 且未解释。

## 五 四验回读（执行后 · 可复算）

| 验 | 期望 |
|---|---|
| ① .before | 全树剩 **1,294 件 / 23,664,967 B**（fp16 17166831fab8f2c8）；或按执行时复算之「留集」逐字一致 |
| ② dist | 体积减 ≈ setup 旧集＋hist dirs＋prev 删集（快照 65,965,670,108 B）±T55 新件；按 §六 R3/R4 逐组核 |
| ③ 现役件 | payload version.json sha16 **b8191e0678c4f8e4**、seed **0c6fd929884420a8** 不变；最新 setup max 集 sha16 与清单一致；有活端则 `/_health` 200（仅只读探） |
| ④ 仓状 | git status **175 行**（或执行时快照）不变；**PFX 仓内 0**；.cer 仍 1；data/** 未动 |

## 六 复跑命令（R1–R8 · pwsh 5.1 · 仓根 D:\clawsjoy_v9）

```powershell
# R1 .before 全树（件/字节/fp16）
$scope=(Get-Location).Path; $all=Get-ChildItem $scope -Recurse -Force -File -ErrorAction SilentlyContinue | Where-Object {$_.Name -like '*.before_*'}
$s=($all|Measure-Object Length -Sum); "N=$($all.Count) B=$([int64]$s.Sum)"
$rows=$all|Sort-Object FullName|ForEach-Object{$_.FullName.Replace($scope+'\','')+'|'+$_.Length}
$h=[Security.Cryptography.SHA256]::Create(); ((($h.ComputeHash([Text.Encoding]::UTF8.GetBytes(($rows -join [char]10))))|ForEach-Object{$_.ToString('x2')}) -join '').Substring(0,16)

# R2 .before 删/留 policy（每 base 留最新 1 份；两命名式皆认）
$g=@{}; foreach($f in $all){ $rel=$f.FullName.Replace($scope+'\',''); $b=$rel
 if($f.Name -match '^(.*)\.before_[0-9a-fA-F]{16}(\.sha256)?$'){$b=$Matches[1]} elseif($f.Name -match '^\.before_[0-9a-fA-F]{16}\.(.*)$'){$b=$Matches[1]}
 if(-not $g.ContainsKey($b)){$g[$b]=@()}; $g[$b]+=,$f }
$keep=@();$del=@(); foreach($k in $g.Keys){$x=$g[$k]|Sort-Object LastWriteTime -Descending;$keep+=$x[0]; if($x.Count -gt 1){$del+=$x[1..($x.Count-1)]}}
"KEEP=$($keep.Count)/$([int64](($keep|Measure-Object Length -Sum).Sum)) DEL=$($del.Count)/$([int64](($del|Measure-Object Length -Sum).Sum))"

# R3 dist / setup* / prev*
function DS($p){$n=0;$b=[int64]0; foreach($x in [IO.Directory]::EnumerateFiles($p,'*',[IO.SearchOption]::AllDirectories)){try{$n++;$b+=([IO.FileInfo]::new($x)).Length}catch{}}; [pscustomobject]@{N=$n;B=$b}}
$d=DS (Join-Path $scope 'dist'); "DIST=$($d.N)/$($d.B)"
$su=@();$suB=[int64]0;$suN=0; Get-ChildItem 'dist/pa_shell' -Directory -Force | Where-Object {$_.Name -like 'setup*'} | ForEach-Object {$x=DS $_.FullName;$suN+=$x.N;$suB+=$x.B}; "SETUPSTAR=$suN/$suB"
$prev=Get-ChildItem 'dist/pa_shell' -Directory -Force | Where-Object {$_.Name -like 'payload.prev_*'} | Sort-Object Name -Descending
$delPrev=$prev|Select-Object -Skip 2; $pn=0;$pb=[int64]0; foreach($x in $delPrev){$t=DS $x.FullName;$pn+=$t.N;$pb+=$t.B}; "PREV_TOTAL=$($prev.Count) DEL_DIRS=$($delPrev.Count)/$pn/$pb"

# R4 setup 旧版本集（留 max 版本）
$sf=Get-ChildItem 'dist/pa_shell/setup' -File -Force; $vers=@{}; foreach($f in $sf){ if($f.Name -match 'ClawsJoyPA-Setup-([0-9.]+)-x64'){$v=$Matches[1]} elseif($f.Name -match 'build-([0-9.]+)\.log'){$v=$Matches[1]} else {continue}; if(-not $vers.ContainsKey($v)){$vers[$v]=@()}; $vers[$v]+=,$f }
$max=($vers.Keys|Sort-Object {[version]$_} -Descending|Select-Object -First 1); $old=@(); foreach($v in $vers.Keys){if($v -ne $max){$old+=$vers[$v]}}
"MAX=$max OLD=$((($old|Measure-Object).Count))/$([int64](($old|Measure-Object Length -Sum).Sum))"

# R5 PFX / cer / 现役 payload
"PFX_REPO=" + ((Get-ChildItem $scope -Recurse -Force -File -Filter '*.pfx' -ErrorAction SilentlyContinue)|Measure-Object).Count
Get-FileHash 'dist/pa_shell/payload/version.json' -Algorithm SHA256
Get-FileHash 'dist/pa_shell/payload/config/pa/pa_registry_pilot_v2.json' -Algorithm SHA256

# R6 git / 白名单现役 setup
"GIT=" + ((git status --porcelain)|Measure-Object -Line).Lines
Get-ChildItem 'dist/pa_shell/setup' -File -Filter 'ClawsJoyPA-Setup-*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 Name,Length

# R7 可删项
(Get-ChildItem '_tmp' -Recurse -Force -File -ErrorAction SilentlyContinue|Measure-Object Length -Sum)
(Get-ChildItem core,web,scripts,tests,docs,config,shell,routes,tools,agents,engine -Recurse -Force -File -Filter '*.pyc' -ErrorAction SilentlyContinue|Measure-Object Length -Sum)
```

## 七 待裁／界

- **④ 待 CEO/老板批**（六拍第④步）；未批 **⛔ 执行**、⛔ 移、⛔ 删。本迭代 ⛔ 动。
- **T55/T56 在建**：9.0.39 仍在出（Setup 9.0.39 07:45；payload.prev_9038）；⑤ 必须待其完成并**重新快照**，否则「最新」可能被误当旧件。
- **不可逆**：dist 旧 setup＋prev 删集约 **64.39 GB**（36.29＋28.10）删后不可回 ⇒ 必走外置 TRASH＋30 天；⛔ 直接 delete。
- **秘密界**：PFX 已移 `_secrets`（仓外）；**仓内 PFX 0**（§二/§六 R5）；本票不含密钥操作；.cer 公开件保留。
- **WIP／写者**：本席只写本件；⛔ 第二写者；执行需另窗、另令（⑤）。

（本件完 · 只出票不执行 · 07_cleanup_ticket）
