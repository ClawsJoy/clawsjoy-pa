# PA 迭代40 · T42 ①卫生审计（不删）

> 代发: DSH（PA）｜执行席: pd-dev｜WIP=1（本单选做）｜写域: `docs/reports/pa_iter40/01_hygiene.md`（本件唯一写入）
> 取刻: 2026-10-30T07:03:26～07:26:00+08:00｜活端: 免（唯只读）｜产品码/测试/配置/载荷: **未改一字**｜**⛔ 未删一件**
> 基线来源: `docs/reports/pa_iter40/README.md`（T41 · sha16 4464fb9278e26a8b · 3,663 B · 2026-10-30）

## 一 结论（先判）

| 项 | 本刻实测 | 基线（T41 README） | 判 |
|---|---|---|---|
| .before_* | 全树 **3,875 件 / 160,057,701 B**（fp16 b543fac4743981a0）；T41 自述七面口径 **891 / 44,963,527 B**（fp16 33e635731898ea3c） | 47 件 / 3,464,692 B（"仅 core/web/docs/shell/tests/scripts/config 面"） | **红：不可复算**（差 3,828 件 ／ 19× 件；见 §2.1） |
| git status | **174 行 = 61 M + 113 ??**（fp16 dfec90a98d7e95e4 · 07:14:14） | 173 行 | 黄：+1 行（本席未写仓；疑队友新件，待 T41 复量） |
| payload | **11,619 件 / 1,150,512,651 B**；data/profile/notes/workspace/seed **全 false**；.before=0；runtime 外 .pyc=0；version **9.0.38**（sha16 c68f363b0073385d） | 无 data/profile/notes/workspace/seed | **绿：洁净** |
| 个人路径 | 源 registry **已清**（0 处，sha16 0c6fd929884420a8）；**当前 payload 内旧 seed 仍 8×D:\Obsidian + 1×C:\Users\flybo**（sha16 534cb87ae100304f） | "已改 PA_VAULT_ROOT/家目录" | 黄/红：源合规、**现役载荷未闭环**（P1 · T51） |
| 生成物 | **dist 69,805,073,833 B**（setup 37.83 GB + payload.prev_* 29.25 GB ≈ 67.08 GB） | — | 黄：空间风险，清理候六拍 |

**授受一句**：payload 本身无 data/profile/notes/workspace/seed 脏物，唯 **P1 旧 seed 个人路径仍在当前载荷**；卫生面最大存量是 **dist 68 GB 级生成物**。**本迭代 ⛔ 删**：删除候老板/六拍。

## 二 清单（可复算）

### 2.1 .before_*（三口径 · 同一树同一刻）

| 口径 | 件 | 字节 | fp16（排序 path+len 之 sha256 前16） |
|---|---|---|---|
| 全树（含 data/_tmp/_pm/_ctx/_L3/_seats/codex/.rollback*） | 3,875 | 160,057,701 | b543fac4743981a0 |
| 七面（T41 自述：core/web/docs/shell/tests/scripts/config） | 891 | 44,963,527 | 33e635731898ea3c |
| 七面去重（按内容 sha256） | 875 | 43,579,320 | — |

七面分解：core 302/14,382,089；web 404/26,724,617；tests 76/880,990；scripts 87/2,593,197；docs 11/339,232；config 11/43,402；shell 0。
全树大面：data 2,059/103,348,472；_pm 461/4,632,721；web 404/26,724,617；core 302/14,382,089；.rollback_codex 209/4,840,696；scripts 87/2,593,197；tests 76/880,990；余 ≤ 23 件/面。

**判**：基线 47 件/3,464,692 B 在本树**任何自洽口径皆不可复算**（全树 82× 件、46× 字节；七面 19× 件、13× 字节；去重亦非）。疑为另一树/另一时刻/另法（如按目录聚合、去重、或仅计 16hex 新名）。**请 T41 复量并指定口径**；本件以「命令 + 取刻 + sha16」为准（§五 R1）。

### 2.2 git status（174 = 61 M + 113 ??）

- fp16 dfec90a98d7e95e4（`git status --porcelain` 原文（git 输出序）之 sha256 前16）· 取刻 07:14:14。
- ?? 113 分类：iter40 新品（core/pa 新路由/notes/voice/screen/harness/owner_guard 30、tests 23、docs 13、tools 10、web 7、shell 2、config/pa 1）；生成/临时（core/pa/*.py.new 11、_tmp_pa016_live.py、_tmp/、_ctx_落盘/、_L3_静窗/、_seats/、MEMORY.md*）；证据目录（web/pa/_evidence/、faces/_evidence/）。
- M 61：产品码/测试/配置（含 9.0.13 P0 修根、9.0.38 面与测试；**保留**，待真 ref）。
- 判：未见第二写者冲突（本席只读）；+1 行差请 T41 复核。

### 2.3 payload 洁净（绿）

| 检查 | 实测 |
|---|---|
| 件数/字节 | 11,619 / 1,150,512,651 |
| 禁入面 data/profile/notes/workspace/seed | false ×5（全部不存在） |
| .before_* / runtime 外 .pyc | 0 / 0（runtime 内 .pyc=1,473 属发行版 stdlib/site-packages，合法） |
| version.json | 9.0.38 · commit 7ce240a8c05294e5ce3abbbe0767f5e148be2b64 · built 2026-10-30T06:46:17+0800 · sha16 c68f363b0073385d |
| 大面 | models 486,213,474 B；runtime 492,582,800 B；wheel 93,856,550 B；web 70,629,153 B；core 5,475,572 B |

### 2.4 个人路径（P1 · 源已清，载荷未闭环）

| 对象 | sha16 / 字节 | 个人路径命中 | 取刻 |
|---|---|---|---|
| 源 config/pa/pa_registry_pilot_v2.json | 0c6fd929884420a8 / 16,945 B | D:\Obsidian **0**；Users\flybo **0**（T51 已清源） | 07:22:11 |
| payload/config/pa/pa_registry_pilot_v2.json | 534cb87ae100304f / 17,012 B | **"cwd": "D:\Obsidian\ClawsJoy\…" 8 处；"C:\Users\flybo\.codex" 1 处** | 07:22:11 |

- 合规样例：core/pa/projects_face.py（sha16 384705b29181e970 · 3,240 B）＝ `os.getenv("PA_VAULT_ROOT")` 优先，缺省 `~/Obsidian/ClawsJoy`（家目录；⛔ 开发机绝对径）——符合 T41 所述。
- 非入包残余（P2，不阻发）：config/alert_config.json、config/scheduler_config.json 含个人邮箱（**payload 无此二件**）；tools/* 绝对径（**payload 无 tools/**）；scripts/win_pa/install_win_pa.py:568 为「开发机径 denylist」自测字面（非用户数据）。
- 判：**P1 未闭环**——源已清但 9.0.38 载荷仍旧；须「重打载荷 → payload 复验 0 处」（§五 R5/R8）。T51 已列。

### 2.5 生成物与体积（清理主候选）

| 面 | 件 | 字节 |
|---|---|---|
| dist/pa_shell 合计 | 395,860 | 69,805,073,833 |
| ├ setup（旧安装包） | 11,805 | 37,825,566,224 |
| ├ payload.prev_*（32 份 · 最早 20261008，最新 20261030_0646_9037） | 361,622 | 29,249,596,099 |
| ├ payload（现役） | 11,619 | 1,150,512,651 |
| ├ setup_nsis_r2 / r3 / setup_nsis / setup_v2 | 10,807 / 3 / 1 / 1 | 1,240,882,712 / 334,123,741 / 2,198,028 / 2,191,008 |
| └ ClawsJoy_Internal.pfx / .cer | 1 / 1 | 2,590 / 780（**私钥在仓内 ⇒ 安全建议 §四.5**） |
| _tmp | 21,520 | 332,187,539 |
| _pm / .rollback_codex / _L3_静窗 / _ctx_落盘 / codex / .rollback_dsh / _seats | 10,114 / 319 / 236 / 272 / 178 / 2 / 7 | 55,200,357 / 5,507,271 / 4,974,075 / 4,122,404 / 785,681 / 60,429 / 22,267 |
| 源码树 __pycache__ / .pyc；.pytest_cache | 163 dirs / 1,852 / 1 | 22,718,230 |
| _share | — | **不在**（Test-Path=False） |

## 三 分类（可删 / 需六拍 / 保留）

### 3.1 可删（低风险、可复算再生；老板一次批准后再执行 · **本迭代 ⛔ 删**）

| 项 | 量 | 据/注意 |
|---|---|---|
| _tmp/ | 21,520 件 / 332,187,539 B | pytest/工具临时根；建议留最近 1 轮 |
| 源码树 __pycache__ + .pyc | 163 dirs / 1,852 / 22,718,230 B | 复跑即生；不入包 |
| .pytest_cache | 1 处 | 同上 |
| core/pa/*.py.new | 11 件 / 256,808 B | 删前逐件 diff 与主档等价（六拍外之核对） |
| _tmp_pa016_live.py | 1 件 / 7,661 B | 一次性探针 |

### 3.2 需六拍（destructive / 发行物 / 历史 / 证据链 · **本迭代 ⛔ 删**）

| 项 | 量 | 处置建议 |
|---|---|---|
| dist/pa_shell/setup*（含 setup、setup_nsis_r2、r3、setup_v2） | ≈ 39,404,961,713 B（39.40 GB） | 保留最新 1 份安装包；余六拍清 |
| dist/pa_shell/payload.prev_* 32 份 | 29,249,596,099 B（29.25 GB） | 保留最近 1–2 份；余六拍清 |
| .before_* | 全树 160,057,701 B（七面 44,963,527 B） | 每 base 留最新 1 份 + 30 天外清；出 dry-run 后再六拍 |
| .rollback_codex / .rollback_dsh | 5,507,271 / 60,429 B | 回滚快照；六拍 |
| _pm / _ctx_落盘 / _L3_静窗 / _seats / codex | 55,200,357 / 4,122,404 / 4,974,075 / 22,267 / 785,681 B | 会话/历史产物；六拍（留档或归档） |
| MEMORY.md.retired_* 9 件 + .sha256 | 未量（小） | 记忆归档；六拍 |

### 3.3 保留

- dist/pa_shell/payload（现役 9.0.38 载荷 1.15 GB）＋ version.json；payload 内 models/runtime/wheel（发行必需）。
- config/pa/pa_registry_pilot_v2.json（**T51 已清源**，待重打载荷）。
- 61 M：产品码/测试/配置（9.0.13 P0 修根、9.0.38 面、测试基线更新）——待真 ref 收口，⛔ 勿删。
- 113 ?? 中 iter40 新品：core/pa 30、tests 23、docs 13、tools 10、web 7、shell 2、config/pa 1。
- data/**（用户数据；本件未量，⛔ 勿删）；web/pa/_evidence、faces/_evidence（验收证据，归档后再定）。
- dist/pa_shell/ClawsJoy_Internal.pfx/.cer：**保留但须移出仓/入密钥库**（§四.5；⛔ 本席未动）。

## 四 建议（不执行）

1. **先复量基线**：T41 按 §五 R1 在七面/全树二口径择一重跑并写死 README；今 47/3,464,692 不可复算 ⇒ 卫生门暂不可判绿。
2. **收益最大（六拍一次）**：清 dist 旧物，保留 payload + 最近 1 份 prev + 最新 1 份 setup ⇒ 约释放 **68.6 GB**；删前出 dry-run 清单。
3. **.before**：按「每 base 留最新 1 份；30 天外全清」；预计 3,875→数百；六拍。
4. **P1 闭环链**：T51 清源（已）→ 重打 payload（T52）→ 复验 payload 0 个人路径（R5）→ 再出包。
5. **安全（P0 · 非删除）**：dist/pa_shell/ClawsJoy_Internal.pfx 私钥在仓内 ⇒ 移出仓、轮换、入密钥库；勿入包；另单处置。
6. **防再生**：写入器（core/lib/paths.py 之 .before_<sha16>）加保留上限/清理入口（产品码改动，另单）。
7. P2：config 邮箱、tools 绝对径、install_win_pa denylist 字面 ⇒ env 化/移出仓（不入包，不阻发）。

## 五 证据四件套（径 + sha16 + 取刻 + 复跑）

| # | 径/对象 | sha16 | 取刻 | 复跑 |
|---|---|---|---|---|
| R1 | .before_* 全树 / 七面 | b543fac4743981a0 / 33e635731898ea3c | 07:03:26–07:05:19 / 07:23–07:24 | 见下 B1/B2 |
| R2 | git status 174 行 | dfec90a98d7e95e4 | 07:14:14 | `git status --porcelain` |
| R3 | payload 计数/禁入面 | version.json c68f363b0073385d | 07:14:14 | 见 B3 |
| R4 | payload .before=0 / runtime 外 pyc=0 | — | 07:20:09 / 07:20:48 | 见 B4 |
| R5 | registry 源 / payload | 0c6fd929884420a8 / 534cb87ae100304f | 07:22:11 | 见 B5 |
| R6 | projects_face PA_VAULT_ROOT | 384705b29181e970 | 07:22:11 | 见 B6 |
| R7 | dist 合计 / prev_* / setup* | — | 07:24–07:26 | 见 B7 |
| R8 | 源码树 pycache | — | 07:26 | 见 B8 |
| R9 | 本件自证 | 落笔后取 | 落笔后 | `Get-FileHash docs/reports/pa_iter40/01_hygiene.md` |

复跑命令（pwsh 5.1 · 仓根 D:\clawsjoy_v9）：

```powershell
# B1 全树 .before + fp16
$scope=(Get-Location).Path; $all=Get-ChildItem -LiteralPath $scope -Recurse -Force -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*.before_*' }
$sum=($all|Measure-Object Length -Sum); "N=$($all.Count) B=$([int64]$sum.Sum)"
$rows=$all|Sort-Object FullName|ForEach-Object{ $_.FullName.Replace($scope+'\','')+'|'+$_.Length }
$h=[System.Security.Cryptography.SHA256]::Create(); ((($h.ComputeHash([Text.Encoding]::UTF8.GetBytes(($rows -join [char]10))))|%{$_.ToString('x2')}) -join '').Substring(0,16)

# B2 七面口径
$dirs=@('core','web','docs','shell','tests','scripts','config'); $it=@(); foreach($d in $dirs){ $it+=Get-ChildItem $d -Recurse -Force -File -ErrorAction SilentlyContinue | Where-Object {$_.Name -like '*.before_*'} }
($it|Measure-Object Length -Sum).Sum

# B3 payload + 禁入面
$pl='dist/pa_shell/payload'; $f=Get-ChildItem $pl -Recurse -Force -File; "FILES=$($f.Count) BYTES=$([int64](($f|Measure-Object Length -Sum).Sum))"
'data','profile','notes','workspace','seed' | ForEach-Object { "$_=" + (Test-Path (Join-Path $pl $_)) }
(Get-FileHash (Join-Path $pl 'version.json') -Algorithm SHA256).Hash.ToLower().Substring(0,16)

# B4 payload 洁净
($f|Where-Object{$_.Name -like '*.before_*'}).Count
($f|Where-Object{$_.Extension -eq '.pyc' -and $_.FullName -notlike '*\runtime\*'}).Count

# B5 个人路径（源 vs payload）
$src='config/pa/pa_registry_pilot_v2.json'; $dst=Join-Path $pl 'config/pa/pa_registry_pilot_v2.json'
foreach($p in @($src,$dst)){ "FILE=$p"; (Select-String -Path $p -Pattern 'D:\\\\Obsidian').Count; (Select-String -Path $p -SimpleMatch 'Users\\flybo').Count }

# B6 PA_VAULT_ROOT 合规
Select-String -Path core/pa/projects_face.py -Pattern 'PA_VAULT_ROOT|expanduser'
(Get-FileHash core/pa/projects_face.py -Algorithm SHA256).Hash.ToLower().Substring(0,16)

# B7 dist 体积（快法：.NET 枚举）
function DS($p){ $n=0;$b=[int64]0; foreach($x in [IO.Directory]::EnumerateFiles($p,'*',[IO.SearchOption]::AllDirectories)){ $n++; $b+=([IO.FileInfo]::new($x)).Length }; [pscustomobject]@{N=$n;B=$b} }
DS 'dist/pa_shell'
(Get-ChildItem 'dist/pa_shell' -Directory -Force | Where-Object {$_.Name -like 'payload.prev_*'}).Count

# B8 pycache
(Get-ChildItem core,web,scripts,tests,docs,config,shell,routes,tools,agents,engine -Recurse -Force -File -Filter *.pyc -ErrorAction SilentlyContinue | Measure-Object Length -Sum)
```

## 六 界与风险

- **本席界**：唯只读；唯一写入本件；⛔ 删件、⛔ 改产品码/配置/测试、⛔ T46（等 T42+T51+T52 全清后由 Lead 释放）。
- **基线红**：47/3,464,692 不可复算 ⇒ 卫生门须 T41 复量；本件不认旧基线为真。
- **P1 红**：9.0.38 现役载荷仍含个人路径；源已清（T51）⇒ 重打后必复验，否则发包即泄漏。
- **P0 安全**：签名私钥在 dist（pfx）⇒ 另单移出/轮换。
- **清理可逆性**：dist 39.4 GB + prev 29.25 GB 删后不可回；六拍前 ⛔ 动。
- 未量 data/** 体积（用户数据，不涉清理）；_share 不在本树。

（本件完 · 唯只读审计 · 未删一件）
