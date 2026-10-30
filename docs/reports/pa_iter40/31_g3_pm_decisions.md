# PA 迭代40 · T105 G3 PM 三裁（31_g3_pm_decisions）

> 代发: DSH（PA）｜席：PM（pm-dev）｜WIP=1（本单）｜写域：仅本件｜取刻：2026-10-30T14:47+08:00
> 依据：T102（28_g3_route_b4 · sha16 b2c0b0b9631f01fb）之「需 PM/PD 三裁」；D-11（D-20261030-11）；T77/18_g3（B1–B5）；旧 9/9 quick 面（WSL verify.py · sha16 f9ba9bede5620350）
> 边界：本件只裁 **PM 分内口径**；⛔ 建端、⛔ 改产品码/数据、⛔ 替 PD 裁 API 语义与实现。

## 〇 三裁一页（先判）

| 裁 | 事项 | PM 裁定 | 一手依据 | 生效 |
|---|---|---|---|---|
| 裁 1 | C1/C2 roster 基准（活端 6／文件 14／旧 obsidian_brain） | **以「活端 6」为基**；C1/C2 改为「源默认 6 ＝ 运行时 6」；**⛔ 再期待 obsidian_brain**；文件 14 不入 9/9 基准 | 源默认 _DEFAULT_CARDS＝6（ds_chat,lingxi,lingxi_local_api,blender,local_vlm,v9_agent）；活端 /v9/pa/roster count＝6 同集；装根可写根 data/v9/pa **空（无 roster.json）** ⇒ 活端即默认；仓内 data/v9/pa/roster.json＝14（多 8 外接 Q0/L0 卡） | 即刻（供重基线引用） |
| 裁 2 | C12/C13 quick 面 N/A 可否 | **可接受 N/A，但换口径**：quick 面记 N/A（reason＝skip_scan 未扫），**不计 PASS**；汇总三列 PASS／FAIL／N/A；⛔ 报 9/9 全绿；C13 full 面另挂 blocked（B3） | 旧码 quick 面 skip_scan=1 下 C12 codex_n=None、C13 直接 True ⇒ 面内自动非真验（T102 §二） | 即刻 |
| 裁 3 | 重基线后验收判据 | **9 条齐全／三态／反例必红／面标＋旧值／两跑同数**；quick 面收口口径＝**7 PASS ＋ 2 N/A ＋ 0 FAIL**，非 9/9 全绿 | T102 §二/§四；旧证 0545 九项旧值；D-11 授权 | 即刻；C5/C7/C10 API 语义由 **PD 裁** |

**一句话**：PM 裁「以活端 6 为基、C12/C13 可 N/A 但不充绿、收口改 7 PASS＋2 N/A」；文件 14 非 9/9 基准；旧 obsidian_brain 期待作废。**⛔ 本件未建端、未改码、未替 PD 裁 API。**

## 一 事实（一手 · 本刻实测）

| 事实 | 值／径 |
|---|---|
| 旧 9/9 quick 面 | C1,C2,C5,C6,C7,C10,C12,C13,C9（WSL 旧路由 L952-961 run_checks(skip_scan=skip, live_http=False)；源 sha16 f9ba9bede5620350，9,675 B） |
| v5 旧期待 | C1/C2 断言 obsidian_brain（旧 roster 9 ids 含该 id；0545 旧证 sha16 9b049df04bb3f11d） |
| 现役源默认 | core/pa/roster.py 17,150 B／81fc0103e5deaff8；_DEFAULT_CARDS **6 张**：ds_chat,lingxi,lingxi_local_api,blender,local_vlm,v9_agent |
| 现役活端 | GET 127.0.0.1:5102/v9/pa/roster ⇒ count＝**6**，ids 同源默认集，无 obsidian_brain；/health＝9.0.47 |
| 装根可写根 | C:/Users/flybo/AppData/Local/ClawsJoyPA/data/v9/pa **存在且为空**（无 roster.json）⇒ 活端走默认 6 |
| 仓内 dev 册 | data/v9/pa/roster.json 18,054 B／0fd20b441ff0cbd5；**14 张**（6＋codex,pi,dsh,claude,ollama,paseo_daemon,v9_gateway,dsh_wsl；多 Q0／claude L0） |
| 装根 payload | 有 data/ 目录但**无 roster.json** |
| D-11 | 「G3 9/9 最小复制获批：仅 verify.py/旧路由/CLI/旧证/两份清单入 legacy_verify，不改旧库；⛔ WSL 运行时依赖；14/14 暂缓」（DECISION_LEDGER sha16 13bd1fcc21ba5867） |

## 二 裁 1（roster 基准）—— 以「活端 6」为基

1. **C1**：改为断言「roster.py 可解析且 _DEFAULT_CARDS ids 集 ＝ 活端 6 id 集」；**不再**断言含 obsidian_brain。
2. **C2**：改为断言「运行时 roster（缺文件时之默认 6）ids 集 ＝ C1 源默认 6 集」；装根无 roster.json ⇒ 以默认初始化 6 为运行值，evidence 明标「默认初始化」。
3. **文件 14 不采**为 9/9 基准：仓内 data/v9/pa/roster.json 14 张属 **dev 附册**（8 外接卡多 Q0／L0、未入装根、活端不显示）；若采 14 等于要求装根携带 dev 扫描产物，与「payload 无 data/seed」红线冲突。**不删、不改**该文件；产品化另议（另立登记册完整性检查，非 G3 面）。
4. **旧 obsidian_brain 期待作废**：v5 roster 9 ids 与现役源/运行/文件三面皆不符；在本裁下 B4 **不再构成 C1/C2 阻断**（C5/C7/C10 阻断仍在，承 T102）。

**裁 1 判据（可机检）**
- 正控：_DEFAULT_CARDS ids 长度＝6 ∧ 活端 6 且集合相等 ⇒ C1/C2 PASS；
- 反控必红：删／加一张致两边不等 ⇒ C1/C2 FAIL；硬塞 14 张为基 ⇒ 报「口径不符本裁」不通过；
- 面标：evidence 写面（quick／runtime-default／source-default）＋sha16（源、live 集）。

## 三 裁 2（C12/C13 N/A）—— 可接受，但换口径

1. **可接受 N/A**：quick 面（skip_scan=1）C12/C13 未扫 ⇒ 记 N/A（reason＝skip_scan 未扫），**不计入 PASS**。
2. **面标与分母**：汇总三列 PASS／FAIL／N/A；quick 面**不得**报 9/9 全绿，只能报「n PASS ／ m FAIL ／ k N/A」。
3. **full 面另案**：C13 full 面 blocked（B3：缺 vault_manifest_win.txt／vault_missing_win.txt ＋ B2 API）；C12 full 面须真扫（API 等价由 PD 裁）。
4. **⛔ 假绿底线**：把 N/A 记 PASS、或把 quick N/A 计入 9/9 者，按假绿判 FAIL（本裁之反例）。

## 四 裁 3（重基线验收判据 · 可机检）

| # | 判据 | 机检期望 |
|---|---|---|
| K1 | 9 条齐全、无缺项、无塌面 | 一次 GET /v9/pa/verify?skip_scan=1（或 CLI --skip-scan）返回 9 个 id（C1,C2,C5,C6,C7,C10,C12,C13,C9）；当前 C5 异常会塌 C6–C13（T102 实证）⇒ 必修 |
| K2 | 三态：每检 ∈ {PASS,FAIL,N/A}，N/A 带 reason | 输出逐项 status＋reason；N/A 不计 PASS |
| K3 | C1/C2 按裁 1、C12/C13 按裁 2 | 面标齐 |
| K4 | 反例必红（每检至少 1 例） | 源默认 vs 活端不等 ⇒ C1/C2 FAIL；删 1 件 SOP／改 sops_dir ⇒ C5/C6 FAIL；改 scan 谓词例 ⇒ C7 FAIL；杀 agent_gateway／源码 mtime 晚于进程 ⇒ C9 FAIL；N/A 被填 PASS ⇒ 假绿 FAIL |
| K5 | 面标＋旧值留档 | 每检 evidence 带面（quick/full）＋旧值（0545）＋取刻；旧证/旧码留档 |
| K6 | 两跑同数（1 正 1 反 1 反例） | 同命令连跑两次一致；反例跑必红 |
| K7 | 不改旧库／不改产品码 | 重基线只动 legacy_verify；D-11 扩权另批 |

**收口口径（本裁）**：满足 K1–K7 ⇒ quick 面可报 **「7 PASS ＋ 2 N/A ＋ 0 FAIL」**（7＝C1,C2,C5,C6,C7,C10,C9）；⛔ 不报 9/9 全绿；full 面（14/14）另案 blocked。
> K4 中 C5/C7/C10 的等价判据与 API 适配**由 PD 裁**；PM 只裁「须有 1 正 1 反」之验收口径，不裁 API 形。

## 五 分工与边界

| 项 | 谁 | 说明 |
|---|---|---|
| 裁 1/2/3 口径 | PM（本件） | 已裁；可被 Lead/老板推翻，推翻须新件留痕 |
| C5/C7/C10 API 等价与实现 | **PD**（⛔ 本件不裁） | PM 只要求反例必红＋面标 |
| 重基线落码／legacy_verify | PD／后端（D-11 扩权后） | ⛔ 本件不建端、不改码 |
| 旧库/旧证 | 只读留档 | ⛔ 不改旧库 |
| 收口验收汇总 | Lead | 按 §四 K1–K7 收 |

**边界**：① 只裁口径，未建端／未改产品码/数据/旧库；② 不替 PD 裁 API；③ N/A 不充绿、旧 9/9 不作今日证；④ 文件 14 不删不改（处置另议）。

## 六 复跑（只读 · 本刻可跑）

```powershell
# ① 源默认 6 与活端 6
python -X utf8 -B -c "import re;t=open('core/pa/roster.py',encoding='utf-8').read();m=re.search(r'_DEFAULT_CARDS\s*=\s*\[([\s\S]*?)\n\]',t);print(re.findall(r'\"id\":\s*\"([^\"]+)\"',m.group(1)))"
try { $r=(Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/roster' -TimeoutSec 5 -UseBasicParsing).Content | ConvertFrom-Json; 'count=' + $r.count; ($r.rows | ForEach-Object { $_.id }) -join ',' } catch { 'ERR' }
# ② 装根可写根（期望空）、仓内 dev 册（期望 14）
Test-Path 'C:/Users/flybo/AppData/Local/ClawsJoyPA/data/v9/pa/roster.json'   # 期望 False
node -e "const d=require('D:/clawsjoy_v9/data/v9/pa/roster.json');console.log('dev cards',d.cards.length)"
# ③ 旧 9/9 面与旧期待
wsl.exe bash -lc "sed -n '952,961p' /home/flybo/clawsjoy_v5/core/pa/gateway_routes.py"
node -e "const d=require('D:/Obsidian/ClawsJoy/ClawsJoy/dsh/_verify/pa_verify_20260928_0545.json');for(const id of ['C1','C2']){const x=d.results.find(r=>r.id===id);console.log(id,x.evidence)}"
# ④ D-11
Select-String -Path docs\\pa\\relations\\DECISION_LEDGER.md -Pattern 'D-20261030-11'
```

## 七 证据四件套 ＋ 边界

| 件 | 径 | bytes | sha16 |
|---|---|---|---:|
| 本件 | docs/reports/pa_iter40/31_g3_pm_decisions.md | 见回执 | 生成后另报 |
| T102 评估 | docs/reports/pa_iter40/28_g3_route_b4.md | 11,392 | b2c0b0b9631f01fb |
| 现役 roster 源 | core/pa/roster.py | 17,150 | 81fc0103e5deaff8 |
| 仓内 dev 册 | data/v9/pa/roster.json | 18,054 | 0fd20b441ff0cbd5 |
| 旧验器源 | WSL /home/flybo/clawsjoy_v5/core/pa/verify.py | 9,675 | f9ba9bede5620350 |
| 旧证 0545 | 外 D:/Obsidian/ClawsJoy/ClawsJoy/dsh/_verify/pa_verify_20260928_0545.json | 1,871 | 9b049df04bb3f11d |
| D-11 裁决 | docs/pa/relations/DECISION_LEDGER.md | 2,392 | 13bd1fcc21ba5867 |
| G3 源定位 | docs/reports/pa_iter40/17_g3_source.md | 11,483 | b96eee4d9153592d |
| G3 授权包 | docs/reports/pa_iter40/18_g3_authorization.md | 2,132 | 42bb63ecc40fec05 |

**边界（照实）**
1. 只读：未改产品码／数据／旧库；未建端。
2. 三裁均为**口径之裁**；C5/C7/C10 **API 语义与实现由 PD 裁**，本件不越权。
3. ⛔ 假绿：C12/C13 N/A 不充 PASS；quick 面收口＝7 PASS＋2 N/A＋0 FAIL，不写 9/9 全绿。
4. 文件 14 不删不改；产品化另裁（不属 G3 9/9 面）。
5. 本裁可被 Lead/老板推翻；推翻须新件留痕（一处本）。

（完 —— 本件末行 · LF 终 · 悬）
