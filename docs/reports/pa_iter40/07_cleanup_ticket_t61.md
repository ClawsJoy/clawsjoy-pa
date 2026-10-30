# PA 迭代40 · T61 ①卫生清理**六拍票 v2**（PA-ITER40-CLEAN-001 v2）

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1｜写域: `docs/reports/pa_iter40/07_cleanup_ticket_t61.md`（本件唯一写入）
> 取刻: 2026-10-30T08:18:35～08:32:45+08:00｜**⛔ 未删一件** ／ ⛔ 未改产品码 ／ ⛔ 未第二写者
> 版本关系: **v1**（`07_cleanup_ticket.md` · 9.0.39 重打中快照 · sha16 a5bf9cce7528c169）**已被本 v2 取代**；票号沿用 **PA-ITER40-CLEAN-001**，版标 **v2**。
> 时点: **T62「9.0.40 干净重打＋签名链」已于 2026-10-30T08:29:54+08:00 完成** ⇒ 本 v2 按**现况 9.0.40** 重算（Lead 许可：按 9.0.40 现有 setup 目录 + payload.prev 列表快速出 v2）。

## 〇 一页（候 ④）

| 项 | 值 |
|---|---|
| 票号／版本／状态 | **PA-ITER40-CLEAN-001 v2** ／ **待 ④ 批准**（CEO/老板；六拍第④步） |
| 现况可释放 | **69,292,758,814 B ≈ 69.29 GB**（= 可删 355,150,752 ＋ 需六拍 68,937,608,062；细目 §三） |
| 分组 | **可删** 355,150,752 B（4 项＋1 空项）／**需六拍** 68,937,608,062 B／**保留** 白名单见 §3.C |
| 硬边界 | ⛔ 本迭代不删；⛔ 不碰 data/**、现役 payload 9.0.40、最新 setup 9.0.40、_secrets；④ 未批 ⛔ 动 |
| 版本锚 | payload **9.0.40**（version.json sha16 **6fe1b819474ca895** · commit bcb48a1a… · built 2026-10-30T08:19:27+0800）；seed **0c6f**；最新 Setup **9.0.40**（806,868,232 B · sha16 **a635373eaf4f7e77**） |

## 一 六拍模板（沿用仓内口径 · 本票填写）

来源：`codex/2026-09-21-codex-⑤wps_office已落LIVE_生效待窗.md` L5（①交技总 ②核实 ③方案含回退 ④CEO 已批 ⑤发起人做 ⑥通知到）；`docs/reports/_pa_groundwork_20261027/05_目标追溯_C30三分工_v0.md` L74（六拍第④步须 CEO 批 ⇒ 出方案⇒CEO 批⇒发起人做）。

| 拍 | 内容 | 状态 | 主/据 |
|---|---|---|---|
| ① | 交件/出票（清单＋回退） | **已**（本 v2） | PD · 本件 sha16 落笔后取 |
| ② | 核实（本机实读 · 可复跑） | **已**（§二/§六 R1–R8） | PD · 取刻见表 |
| ③ | 方案（删/留/回滚/验证） | **已**（§三/§四/§五） | PD |
| ④ | **批准** | **待**（CEO/老板） | 六拍第④步；未批 ⛔ 执行 |
| ⑤ | 执行（发起人做） | **待 ④ 后**；**本迭代 ⛔** | PD/指定运维；T62 已完成，执行前仍复量 |
| ⑥ | 通知到（回执 ＋ 四验回读） | **待** | 回执帖 ＋ 技总/相关席；§五 |

## 二 快照（v1 基线 ⇄ v2 现况 · 9.0.40 后）

| 项 | v1/任务基线 | **v2 现况（9.0.40 后）** | 差/据 | 取刻 |
|---|---|---|---|---|
| .before_*（全树） | 3,875 / 160,057,701 B | **3,875 / 160,057,701 B**（fp16 **b543fac4743981a0**；本轮全树实测；删/留 fp16 **1813fcca2ef940a8** / **17166831fab8f2c8**） | 0（T62 唯动 dist ⇒ 不变） | 08:18:35–08:24:52 |
| dist（全树） | 69,805,073,833 B | **74,529,394,771 B**（419,108 件） | **+4,724,320,938 B**（9.0.40 payload/setup/prev 增量） | 08:32:45 |
| setup*（setup／setup_nsis／r2／r3／v2） | 39,404,961,713 B（22,617 件） | **41,828,259,143 B**（22,628 件） | **+2,423,297,430 B** | 08:32:45 |
| payload.prev_* | 32 份 / 361,622 件 / 29,249,596,099 B | **34 份 / 384,860 件 / 31,550,621,267 B** | **+2 份 / +23,238 件 / +2,301,025,168 B**（T62 前备用 9039） | 08:32:45 |
| git status | 174 行 | **177 行 = 63 M + 114 ??**（fp16 **f06090af4b328628**） | +3（T55–T62 迭代件；本席未写产品码） | 08:30:08 |
| 现役 payload | 9.0.39（b8191e06…） | **9.0.40**（version.json 197 B · sha16 **6fe1b819474ca895** · commit bcb48a1a… · built 08:19:27）；seed **0c6f** | 版本升级；seed 未变 | 08:30:08 |
| 最新 setup | 9.0.39（806,500,248） | **9.0.40 Setup 806,868,232 B（08:27:01 · sha16 a635373eaf4f7e77）＋ blockmap（并入 9.0.40 组 2 件/807,705,523）** | T62 已出 9.0.40 | 08:30:08 |
| win-unpacked | 534c（T52 前）旧 | **seed 0c6f（16,945 B）**；11,695 件 / 1,539,116,914 B | 已随 T62 干净重打；白名单不变 | 08:32:45 |
| PFX | 已移出／0 | **仓内 PFX = 0**（全树扫描 0）；.cer 1（780 B · sha16 **6a2a2df26f476aac**）；外部 `_secrets` 保留（⛔ 本票范围） | T53/T62 | 08:32:45 |

## 三 分组清单（可删 ／ 需六拍 ／ 保留）

### 3.A 可删（低风险、可再生；仍须 ④；**本迭代 ⛔**）

| 项 | 件/字节 | 据 |
|---|---|---|
| `_tmp/` | 21,539 / **332,168,053** | 临时根（08:32:45）；可再生 |
| 源码树 __pycache__＋.pyc | 163 dirs / 1,852 / **22,718,230** | 复跑即生 |
| core/pa/*.py.new | 11 / **256,808** | 删前逐件 diff 与主档等价 |
| `_tmp_pa016_live.py` | 1 / **7,661** | 一次性探针 |
| `.pytest_cache` | 0 / **0** | 空（未复测，v1 实测 0） |
| **小计** | **355,150,752 B** | — |

### 3.B 需六拍（destructive／发行物／历史／证据链；**本迭代 ⛔**）

| 组 | 项（精确） | 件/字节 | 保留规则（执行时复算） | 风险 |
|---|---|---|---|---|
| B1 | **.before_*** 全树删除集：同 base 留最新 1 份（含 .sha256 伴件）⇒ 删 **2,581 / 136,392,734 B**；留 **1,294 / 23,664,967 B** | 2,581 / 136,392,734 | 每 base 最新 1 份；其余删（可选 30 天外） | 备份历史；不可回 |
| B2 | **setup 旧版本集**（< max 9.0.40）：版本 **9.0.11–9.0.39 共 29 版 / 84 件 / 37,901,457,919 B**（含 9.0.39 的 `.prev_t55` 备份 2 件；单列可再议） | 84 / 37,901,457,919 | **留 max 版本集**（9.0.40：2 件／807,705,523 B）＋win-unpacked＋internal.yml＋builder-debug.yml | 旧安装包历史；不可回 |
| B3 | **setup_nsis ／ setup_nsis_r2 ／ setup_nsis_r3 ／ setup_v2** 整目录 | 10,812 / 1,579,395,489 | 全删（历史尝试 9.0.1／9.0.11 旧链） | 历史；不可回 |
| B4 | **payload.prev_***：34 份留最新 2（**payload.prev_20261030_0819_9039** 1,150,512,584 B ＋ **…_0740_9038** 1,150,512,584 B 级），余 **32 份 / 361,622 件 / 29,249,596,099 B** 删 | 361,622 / 29,249,596,099 | 留最新 2（合计 2,301,025,168 B）；余删 | 回滚用；留 2 份即可 |
| B5 | `.rollback_codex` ／ `.rollback_dsh` | 319／2 · 5,507,271／60,429 | 先归档外置；仓内不留 | 回滚快照；不可回 |
| B6 | `_pm` ／ `_ctx_落盘` ／ `_L3_静窗` ／ `_seats` ／ `codex` | 10,114／272／236／7／178 · 55,200,357／4,122,404／4,974,075／22,267／785,681 | 归档外置后删；或保留 `codex/` | 会话/历史产物 |
| B7 | `MEMORY.md.retired_*` 9 ＋ `MEMORY.md.before_*` 1 ＋ `MEMORY.md.sha256` 1（**MEMORY.md 留**） | 11 / 93,337 | 只删 retired/before/sha | 记忆归档 |
| **小计** | — | **68,937,608,062 B** | — | — |

### 3.D 清单指纹（供 ④ 后逐字核；取刻 2026-10-30T08:18:35–08:32:45+08:00）

指纹 ＝ 「排序后 path|size 行」之 sha256 前16（口径同 T42 fp16）；**T62 已完成，若再有重打/签后变动须重算**。

| 集 | 件/字节 | fp16 |
|---|---|---|
| B1 .before 删除集 / 保留集 | 2,581/136,392,734 · 1,294/23,664,967 | **1813fcca2ef940a8** / **17166831fab8f2c8** |
| B2 setup 旧集 / max 保留集 | 84/37,901,457,919 · 2/807,705,523 | **71aeae0b18413bf9** / **c6c0aa71e1f7cf1c** |
| B3 hist 四目录全文件 | 10,812/1,579,395,489 | **41904b4492b61876** |
| B4 prev 删除集（按目录 name|bytes 聚合） | 32 dirs/361,622/29,249,596,099 | **04fb4051e7501198** |
| A core/pa/*.py.new | 11/256,808 | **3f982c7d83216aab** |

### 3.C 保留（白名单 · 任何一步皆 ⛔ 碰）

- **现役 payload 9.0.40**：`dist/pa_shell/payload/`（version.json sha16 **6fe1b819474ca895**；seed **0c6f** ／ sha16 **0c6fd929884420a8**）——执行前后逐字验。
- **最新 setup 9.0.40 构建集**：`dist/pa_shell/setup/` 内 max 版本集（Setup 806,868,232 B／**a635373eaf4f7e77** ＋ blockmap；合计 2 件/807,705,523）＋ `win-unpacked/`（11,695／1,539,116,914；seed 0c6f）＋ `internal.yml` ＋ `builder-debug.yml`。
- **最新 2 份 prev**（B4 保留项，2,301,025,168 B；含 0819_9039 与 0740_9038）。
- `dist/pa_shell/ClawsJoy_Internal.cer`（780 B／**6a2a2df26f476aac**；公开证书，保留）。
- **data/***（用户数据；不量不碰）；git 工作树 **177 行（63 M／114 ??）**；docs/tests/new sources／evidence。
- `D:\paseo-workspace\_secrets\ClawsJoy_Internal.pfx`（仓外；⛔ 本票范围；仓内 PFX **0**）。

## 四 回滚与执行方案（④ 批后 · 本迭代 ⛔）

1. 外置桶：`D:\paseo-workspace\_trash_pa_iter40_<yyyyMMdd_HHmm>`（TRASH）。
2. 干跑：按 §三 生成清单（path｜size），逐项核白名单；写 `_MANIFEST.txt`（路径＋字节＋聚合 sha16）。
3. 断言（任一失败即止）：payload version sha16 **6fe1b819474ca895**；seed **0c6f**；最新 Setup max 组 sha16 **a635373eaf4f7e77**（或执行时按 max 重算一致）；**PFX 仓内 0**；TRASH 在仓外；data/** 不在清单。
4. 移：`robocopy <源> <TRASH>\<相对>\ /E /MOVE /R:2 /W:2`；顺序 **A → B4 → B2 → B3 → B1 → B5 → B6 → B7**；每步打点（件/字节）。
5. 四验回读（§五）＋ 回执（⑥）。
6. 回滚：`robocopy <TRASH>\<相对> <源> /E /MOVE` + 按 _MANIFEST 复核；30 天后才可物理销毁（另票）。
7. **中止条件**：白名单内文件、data/**、现役 payload/最新 setup/密钥、或 T62/后续重打仍在写；件/字节与清单偏差 >0 且未解释。

## 五 四验回读（执行后 · 可复算）

| 验 | 期望 |
|---|---|
| ① .before | 全树剩 **1,294 件 / 23,664,967 B**（fp16 17166831fab8f2c8）或按执行时留集逐字一致 |
| ② dist | 减 ≈ **68.94 GB**（B1 0.136 + B2 37.90 + B3 1.58 + B4 29.25 GB 量级；以执行时复算为准） |
| ③ 现役件 | payload version.json sha16 **6fe1b819474ca895**、seed **0c6fd929884420a8** 不变；最新 setup max 集 sha16 **a635373eaf4f7e77** 与清单一致；有活端仅只读 `/health` 探 |
| ④ 仓状 | git **177 行**（或执行时快照）不变；**PFX 仓内 0**；.cer 仍 1；data/** 未动 |

## 六 复跑命令（R1–R8 · pwsh 5.1 · 仓根 D:\clawsjoy_v9）

```powershell
# R1 .before 全树（件/字节/fp16）
$scope=(Get-Location).Path; $all=Get-ChildItem $scope -Recurse -Force -File -ErrorAction SilentlyContinue | Where-Object {$_.Name -like '*.before_*'}
$s=($all|Measure-Object Length -Sum); "N=$($all.Count) B=$([int64]$s.Sum)"
$rows=$all|Sort-Object FullName|ForEach-Object{$_.FullName.Replace($scope+'\','')+'|'+$_.Length}
$h=[Security.Cryptography.SHA256]::Create(); ((($h.ComputeHash([Text.Encoding]::UTF8.GetBytes(($rows -join [char]10))))|ForEach-Object{$_.ToString('x2')}) -join '').Substring(0,16)

# R2 .before 删/留 policy（同 base 留最新 1 份；两种命名式）
$g=@{}; foreach($f in $all){ $rel=$f.FullName.Replace($scope+'\',''); $b=$rel
 if($f.Name -match '^(.*)\.before_[0-9a-fA-F]{16}(\.sha256)?$'){$b=$Matches[1]} elseif($f.Name -match '^\.before_[0-9a-fA-F]{16}\.(.*)$'){$b=$Matches[1]}
 if(-not $g.ContainsKey($b)){$g[$b]=@()}; $g[$b]+=,$f }
$keep=@();$del=@(); foreach($k in $g.Keys){$x=$g[$k]|Sort-Object LastWriteTime -Descending;$keep+=$x[0]; if($x.Count -gt 1){$del+=$x[1..($x.Count-1)]}}
"KEEP=$($keep.Count)/$([int64](($keep|Measure-Object Length -Sum).Sum)) DEL=$($del.Count)/$([int64](($del|Measure-Object Length -Sum).Sum))"

# R3 dist / setup* / prev*
function DS($p){$n=0;$b=[int64]0; foreach($x in [IO.Directory]::EnumerateFiles($p,'*',[IO.SearchOption]::AllDirectories)){try{$n++;$b+=([IO.FileInfo]::new($x)).Length}catch{}}; [pscustomobject]@{N=$n;B=$b}}
$d=DS (Join-Path $scope 'dist'); "DIST=$($d.N)/$($d.B)"
$suN=0;$suB=[int64]0; Get-ChildItem 'dist/pa_shell' -Directory -Force | Where-Object {$_.Name -like 'setup*'} | ForEach-Object {$x=DS $_.FullName;$suN+=$x.N;$suB+=$x.B}; "SETUPSTAR=$suN/$suB"
$prev=Get-ChildItem 'dist/pa_shell' -Directory -Force | Where-Object {$_.Name -like 'payload.prev_*'} | Sort-Object Name -Descending
$kp=$prev|Select-Object -First 2; $dp=$prev|Select-Object -Skip 2
$dpN=0;$dpB=[int64]0; foreach($x in $dp){$t=DS $x.FullName;$dpN+=$t.N;$dpB+=$t.B}; "PREV_TOTAL=$($prev.Count) DEL_DIRS=$($dp.Count)/$dpN/$dpB"

# R4 setup 版本 groups（留 max）
$sf=Get-ChildItem 'dist/pa_shell/setup' -File -Force; $vers=@{}; foreach($f in $sf){ if($f.Name -match 'ClawsJoyPA-Setup-([0-9.]+)-x64'){$v=$Matches[1]} elseif($f.Name -match 'build-([0-9.]+)\.log'){$v=$Matches[1]} else {continue}; if(-not $vers.ContainsKey($v)){$vers[$v]=@()}; $vers[$v]+=,$f }
$max=($vers.Keys|Sort-Object {[version]$_} -Descending|Select-Object -First 1); $old=@(); foreach($v in $vers.Keys){if($v -ne $max){$old+=$vers[$v]}}
"MAX=$max OLD=$((($old|Measure-Object).Count))/$([int64](($old|Measure-Object Length -Sum).Sum))"

# R5 PFX/cer/现役
"PFX_REPO=" + ((Get-ChildItem $scope -Recurse -Force -File -Filter '*.pfx' -ErrorAction SilentlyContinue)|Measure-Object).Count
Get-FileHash 'dist/pa_shell/payload/version.json' -Algorithm SHA256
Get-FileHash 'dist/pa_shell/payload/config/pa/pa_registry_pilot_v2.json' -Algorithm SHA256

# R6 git / 最新 Setup
"GIT=" + ((git status --porcelain)|Measure-Object -Line).Lines
Get-ChildItem 'dist/pa_shell/setup' -File -Filter 'ClawsJoyPA-Setup-*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 Name,Length

# R7 可删项
(Get-ChildItem '_tmp' -Recurse -Force -File -ErrorAction SilentlyContinue|Measure-Object Length -Sum)
(Get-ChildItem core,web,scripts,tests,docs,config,shell,routes,tools,agents,engine -Recurse -Force -File -Filter '*.pyc' -ErrorAction SilentlyContinue|Measure-Object Length -Sum)
```

## 七 待裁／界

- **④ 待 CEO/老板批**；未批 **⛔ 执行**、⛔ 移、⛔ 删；本迭代 ⛔ 动。
- **版本锚**：v2 按 9.0.40 现况（T62 完成 08:29:54）；v1（9.0.39 中快照）已废；票号不变 PA-ITER40-CLEAN-001 **v2**。
- **不可逆**：B2+B3+B4 ≈68.73GB 删后不可回 ⇒ 必走外置 TRASH＋30 天；⛔ 直接 delete。
- **秘密界**：仓内 PFX 0；PFX 在 `_secrets`（仓外）⛔ 本票范围。
- **写者**：本席只写本件；⛔ 第二写者；执行需另窗、另令（⑤）。

（本件完 · 只出票不执行 · PA-ITER40-CLEAN-001 v2）
