# PA 迭代40 · T108 PM 对账 7+2（34_g3_pm_reconcile）

> 代发: DSH（PA）｜席：PM（pm-dev）｜WIP=1（本单）｜写域：仅本件｜取刻：2026-10-30T14:50:55+08:00
> 依据：T105（31_g3_pm_decisions · f825a9f8543a2734）· T106（32_g3_pd_decisions · 10d3b65055fe029f）· T107（33_g3_decision_conflict · 6c33b07d849e5975）· T102（28_g3_route_b4 · b2c0b0b9631f01fb）
> 边界：只读对账；⛔ 建端、⛔ 改码/改旧件、⛔ 冒绿。本件修订 T105 之收口口径；31 原文保留不改。

## 〇 四问答（先判）

| # | 问 | PM 答 |
|---|---|---|
| ① | 7 PASS 逐条名单（9 检中哪 7 条） | T105 原列 7 ＝ C1,C2,C5,C6,C7,**C10**,C9（**第七条＝C10**）；C10 经 T106 判 blocked ⇒ **7+2 不成立** |
| ② | 若 C10 不可 pass，是否接受 6 PASS＋1 FAIL(C10)＋2 N/A | **接受**：**6 PASS（C1,C2,C5,C6,C7,C9）＋1 FAIL（C10·blocked B2）＋2 N/A（C12,C13）** |
| ③ | 若坚持 7+2，给 C10/第七条证据 | **无证据可给，撤回 7+2**：现役无 last_walk_errors（hasattr=False）、无 _scan_excluded；旧 9/9 的 C10 是 bool(skip_scan) 的「未验 pass」（假绿路径），不能作 PASS 证据 |
| ④ | 最终口径 | quick 面 **6+1+2**；**G3 未收口（不绿）**；⛔ 不写 7+2、9/9、7/7；full 14/14 按 D-11 暂缓 blocked |

**一句话**：PM 认账——T105「7 PASS」第七条是 C10；C10 不可 PASS（无等价 API）⇒ 改判 **6 PASS＋1 FAIL(C10)＋2 N/A**；G3 仍**未收口**，不冒绿。

## 一 7 PASS 逐条名单（原 7 ＋ 第七条定性）

| 检 | T105 原判 | 本对账判 | 依据／条件 |
|---|---|---|---|
| C1 | PASS | **PASS** | 裁 1：源默认 6 ＝ 活端 6（ds_chat,lingxi,lingxi_local_api,blender,local_vlm,v9_agent）；⛔ 再期待 obsidian_brain |
| C2 | PASS | **PASS** | 同上；运行值＝默认初始化 6（装根 data/v9/pa 空、无 roster.json） |
| C5 | PASS（修 schema 后） | **PASS（条件项）** | 须按 T105 K1 改用 _resolve_knowledge_path（现役 _KNOWLEDGE_FILES 为 sandbox_rel）；⛔ 现在直跑仍 KeyError |
| C6 | PASS | **PASS（适配后）** | sops_dir=工作区/SOPs/SOPs exists=True；PD 裁「空 _vault_path() ⇒ FAIL 显因，⛔ 落 CWD」 |
| C7 | PASS | **PASS（适配后）** | PD T106：须复刻「顶层＋静态＋归一」；现役 _rel_excluded 任一段/配置源 ⇒ 不等价，⛔ 原样 |
| **C10** | **PASS（原第七）** | **FAIL（blocked）** | 见 §二：无等价 API；旧 skip_scan 未验 pass 是假绿 |
| C9 | PASS | **PASS（适配后）** | BASE 5102（env＞port_config 真源）；本刻 health 200、5002 CLOSED、/health 9.0.47 |
| C12 | N/A | **N/A** | skip_scan 未扫；⛔ 计 PASS |
| C13 | N/A | **N/A** | quick 面未扫；full 面 blocked（B3 缺两份清单；清单件在 legacy_verify 只读） |

> 重要限定：上表 PASS 为「按已裁口径重基线实现后应达」之**条件项**；本刻 /v9/pa/verify 仍 **404**、legacy_verify/core/pa/verify.py 仍是原样 f9ba9bede5620350（未适配）⇒ **⛔ 把本表当今日已绿**。G3 现判：未收口。

## 二 C10 计性（核心）

| 计法 | 是否成立 | 由 |
|---|---|---|
| 计 **PASS** | **✗ 假绿** | 旧 9/9 中 C10 ＝ (errs is not None) or bool(skip_scan) ⇒ skip_scan 下**未验即 pass**（WSL verify.py L149-153 逐字：rec("C10", (errs is not None) or bool(skip_scan), ... "skip_scan：未验")）；现役 last_walk_errors **不存在**（hasattr=False），无等价观测 |
| 计 **N/A** | **✗ 不成立** | N/A 仅限「面内跳过、full 面可补」（C12/C13）；C10 在 quick/full 两面**均无等价 API**（PD T106：_walk_warn 仅 print、os.walk(onerror) 不保已读条、无 _LAST_WALK_ERRORS）⇒ 不是「未扫」而是「不可验」 |
| 计 **FAIL（blocked）** | **✓ 本裁** | 验收未过；原因＝B2 API 缺失；报告须写 **「FAIL·blocked(B2)」**，不写 PASS/未验绿 |

**PM 计性规则（本件定）**
1. **PASS**：须有等价观测（1 正控 ＋ 1 反控），且反例必红；
2. **N/A**：仅「该面内跳过、另一面可补」，且须带 reason；
3. **C10 归 FAIL（blocked）**：无等价观测 ⇒ 不 PASS；非「面内跳过」⇒ 不 N/A；不得以旧 skip_scan 未验充 PASS；
4. 后续若 C10 要 PASS：须 PD/TD 恢复等价 _LAST_WALK_ERRORS 或另立 legacy adapter 面并分别 1 正 1 反；**PM 不裁 API 实现**（T106 已裁 C10 现 API blocked）。

## 三 最终口径（本件为准）

| 项 | 口径 |
|---|---|
| quick 面 9 条 | **6 PASS（C1,C2,C5,C6,C7,C9）＋1 FAIL（C10·blocked B2）＋2 N/A（C12,C13）＝ 6+1+2** |
| G3 判 | **未收口（红/blocked）**；⛔ 不写 7+2、9/9、7/7 |
| full 14/14 | D-11 暂缓，blocked（B1–B5 未清） |
| 收口条件 | ①重基线实现（C1/C2 裁1、C5 schema、C6/C7/C9 适配）；②C10 等价面另裁后重算——**若 C10 可 PASS ⇒ 7 PASS+2 N/A，但 9/9 仍非全绿（C12/C13 N/A 不计绿）**；③两跑同数＋反例必红＋面标＋旧证留档；④D-11 扩权 |
| 分工 | PM：计性与口径（本件）；PD：C5/C7/C10 API 语义与实现（T106）；Lead：收口汇总；⛔ 本件不建端 |

## 四 留痕与冲突结案（O-10）

- **冲突**：T105（7+2）vs T106（C10 blocked）vs T107（至多 6+1+2）。
- **结案（PM 侧）**：采纳 **6+1+2**；撤回 T105 之 7+2（第七条 C10 降 FAIL）。不改 31 原文；本件 34 为修订、引用为准（一处本）。
- C10 的「另立 adapter 面」属 PD/TD 后续；在等价实现前，**C10 永不得 PASS**（防假绿）。
- 若 Lead/老板裁「可接受 6+1+2」，则 G3 quick 面口径定案；若要求 7+2，须先给 C10 等价证据（本件无）。

## 五 复跑（只读 · 本刻可跑）

```powershell
# ① 本刻 C10 无等价 API（期望 False/False）
python -X utf8 -B -c "import sys;sys.path.insert(0,'.');from core.gateway import precision_inject as PI;print(hasattr(PI,'last_walk_errors'),hasattr(PI,'_scan_excluded'),hasattr(PI,'_rel_excluded'))"
# ② 旧 C10 的「未验 pass」代码（期望 rec C10 ... bool(skip_scan) / "skip_scan：未验"）
wsl.exe bash -lc "sed -n '149,153p' /home/flybo/clawsjoy_v5/core/pa/verify.py"
# ③ 活端/端口（期望 5102=200、5002 CLOSED、/v9/pa/verify=404）
try { (Invoke-WebRequest 'http://127.0.0.1:5102/health' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { '5102 ERR' }
try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',5002); '5002 OPEN'; $c.Close() } catch { '5002 CLOSED' }
try { (Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/verify?skip_scan=1' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 'verify 404/ERR' }
# ④ 旧件 sha（31=f825a9f8…、32=10d3b650…、33=6c33b07d…、legacy verify=f9ba…）
node -e "const fs=require('fs'),c=require('crypto');for(const f of ['docs/reports/pa_iter40/31_g3_pm_decisions.md','docs/reports/pa_iter40/32_g3_pd_decisions.md','docs/reports/pa_iter40/33_g3_decision_conflict.md','legacy_verify/core/pa/verify.py']){const b=fs.readFileSync(f);console.log(f,b.length,c.createHash('sha256').update(b).digest('hex').slice(0,16))}"
```

## 六 证据四件套 ＋ 边界

| 件 | 径 | bytes | sha16 |
|---|---|---|---:|
| 本件 | docs/reports/pa_iter40/34_g3_pm_reconcile.md | 见回执 | 生成后另报 |
| PM 三裁（原） | docs/reports/pa_iter40/31_g3_pm_decisions.md | 9,773 | f825a9f8543a2734 |
| PD 裁 C7/C10 | docs/reports/pa_iter40/32_g3_pd_decisions.md | 11,467 | 10d3b65055fe029f |
| 冲突对账 | docs/reports/pa_iter40/33_g3_decision_conflict.md | 1,635 | 6c33b07d849e5975 |
| T102 评估 | docs/reports/pa_iter40/28_g3_route_b4.md | 11,392 | b2c0b0b9631f01fb |
| T103 挂起 | docs/reports/pa_iter40/29_g3_route_hold.md | 1,377 | 62aae9aba44ed9fc |
| CEO 3483 | docs/reports/pa_iter40/30_ceo_3483.md | 1,505 | d0ff41df8b2eb726 |
| legacy 验器 | legacy_verify/core/pa/verify.py | 9,675 | f9ba9bede5620350 |
| 现役扫描模块 | core/gateway/precision_inject.py | 62,294 | 54f24605e473a950 |
| 旧清单 | legacy_verify/data/v9/vault_manifest_win.txt | 722,197 | 98cf4c34a491b574 |
| 旧缺项册 | legacy_verify/data/v9/vault_missing_win.txt | 1,436 | d396aefaf6b7fc51 |

**边界（照实）**
1. 只读对账：未建端、未改码、未改旧件（31 原文保留）。
2. ⛔ 冒绿：6 PASS 为「重基线实现后条件项」，本刻 verify 端 404、legacy 未适配 ⇒ **G3 未收口**；不写 7+2/9-9。
3. C10 计 **FAIL·blocked(B2)**：不 PASS、不 N/A、不得以旧 skip_scan 未验充绿。
4. 不替 PD 裁 API：C10 等价实现与 adapter 面由 PD/TD 后续裁/做。
5. 本对账可被 Lead/老板推翻；推翻须新件留痕（一处本）。

（完 —— 本件末行 · LF 终 · 悬）
