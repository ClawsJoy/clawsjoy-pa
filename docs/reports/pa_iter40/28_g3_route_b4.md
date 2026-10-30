# PA 迭代40 · T102 G3 9/9 路由 B4 影响评估（28_g3_route_b4）

> 代发: DSH（PA）｜席：PM（pm-dev）｜WIP=1（本单）｜写域：仅本件｜取刻：2026-10-30T14:42:31+08:00
> 依据：D-11（9/9 最小复制获批，D-20261030-11）、T77（17_g3_source）、18_g3（B1–B5）、WSL 旧树 verify.py（只读）、0545 旧证
> 纪律：**只读评估**；⛔ 建端／改产品码／复制旧库／假绿。B4＝旧 verify.py 的 C1/C2 断言 `obsidian_brain` 而现役 roster 无该 id。

## 〇 一页（先判）

**9/9 quick 面（skip_scan=1、live_http=False）＝ C1,C2,C5,C6,C7,C10,C12,C13,C9**（WSL 旧路由 L952-961 逐字：`run_checks(skip_scan=skip, live_http=False)`；旧码 C3/C4 跳、C8 跳、C14 不入面）。

| 结论 | 判 |
|---|---|
| **B4 是否阻断 9/9** | **是阻断项之一，但⛔不是唯一**：B4 直接挂 **C1/C2**；另有 **C5 schema 漂移**、**C7/C10 API 改名漂移（B2）** 独立阻断；**C12/C13 仅为 skip_scan 面内自动 True（非真验）**；C9 现役可过 |
| **9/9 当前可达？** | **不可达**：直跑旧 verify.py ⇒ 1 绿（C9）／5 红（C1,C2,C5,C7,C10）／1 未录（C6 被 C5 异常塌）／2 面内自动非真（C12,C13） |
| **是否需重基线** | **需（PM/PD 裁口径）**：B4 之外仍有 B2 API 与 C5 schema 两处，B4 单独补齐仍到不了 9/9 |
| 方案 | **A 重基线后 9/9（建议）** vs **B 保留旧面 blocked**（§四，均附判据；⛔ 本件不代裁） |

## 一 口径（源／现役／面）

- **旧源**：WSL `/home/flybo/clawsjoy_v5/core/pa/verify.py` ｜9,675 B｜sha16 **f9ba9bede5620350**（sha256 `f9ba9bede562035061499a8a1818a22a788fb02b1e14aaabc5fd2dd49732f259`，只读，未复制）。
- **旧路由**：`core/pa/gateway_routes.py` L952-961（sha16 `ad29de68fe5d4a99`，承 T77）；quick 面 ＝ `skip_scan=1` ＋ `live_http=False`。
- **现役**：仓 `D:/clawsjoy_v9`；活端 `127.0.0.1:5102`（`/health`=**9.0.47**）；vault 根 `D:/Obsidian/ClawsJoy/ClawsJoy`。
- **旧证**：`pa_verify_20260928_0545.json`（1,871 B／sha16 **9b049df04bb3f11d**）——9/9 旧值见 §二。

## 二 9 检逐条（v5 判据 × 现役实测）

| 检 | v5 判据（旧 verify.py） | v5 旧值（0545） | 现役实测（径／值） | 直跑判 | 需改点 | B4 相关 |
|---|---|---|---|---|---|---|
| **C1** | `roster.py` 源含 `obsidian_brain` | sha16 f62d60c473a8c07d／True | `core/pa/roster.py` 17,150 B／sha16 **81fc0103e5deaff8**／**无 obsidian_brain** | **红** | 断言改现役 roster 口径 | **是** |
| **C2** | `data/v9/pa/roster.json` cards 含 `obsidian_brain` | ids 9（含 obsidian_brain）／sha16 344ae3ef5a417ef6 | `data/v9/pa/roster.json` 18,054 B／sha16 **0fd20b441ff0cbd5**／ids **14（无 obsidian_brain）**；活端 `/v9/pa/roster` count=**6**（ds_chat,lingxi,lingxi_local_api,blender,local_vlm,v9_agent，无该 id） | **红** | 同上＋file/live 口径裁 | **是** |
| **C5** | `PI._KNOWLEDGE_FILES[k]["rel"]` 三件皆 file | F1 三键 True | 现役 schema 为 `file/desc/keywords/sandbox_rel`，**无 `rel` 键 ⇒ KeyError**；改 `_resolve_knowledge_path` 后三件皆在（工作区/SOPs/SOPs/平台发布工作流.md 等 3/3 True） | **红（异常塌面）** | 改用 `_resolve_knowledge_path`／`sandbox_rel` | 否 |
| **C6** | `_obsidian_cfg().sops_dir` 且目录在 | sops_dir=工作区/SOPs/SOPs exists=True | 同值 **exists=True**（`工作区/SOPs/SOPs`） | **未录**（C5 抛错塌整块）→ 修 C5 后**可达 PASS** | 无（随 C5 解锁） | 否 |
| **C7** | `_scan_excluded` 谓词 6 例全合 ∧ leaked=0 | 谓词不符={}／leaked=0 | **无 `_scan_excluded`**（现役有 `_rel_excluded`，语义不同） | **红** | 按 B2 重写或加兼容层（语义须 PM/PD 核） | 否 |
| **C10** | `_scan_excluded` ＋ `last_walk_errors` | last_walk_errors=[] | **两符号皆无**（现役 `_scan_vault` 无同名留痕） | **红** | 同上（B2） | 否 |
| **C12** | 全扫 codex md>0（容错恢复） | md=1310 | skip_scan=1 ⇒ codex_n=None ⇒ **面内自动 True（未扫，非真验）** | **N/A（非真绿）** | 面标 N/A；真验走 full 面 | 否 |
| **C13** | 全扫 Windows 清单通道 miss==缺项册 | non_excluded=3193／scan=3188／missing=5 | skip_scan=1 ⇒ **面内自动 True（未扫）**；full 面缺 `vault_manifest_win.txt`/`vault_missing_win.txt`（B3） | **N/A（非真绿）** | 面标 N/A；full 面待 B3 | 否 |
| **C9** | live health 200 ＋ 进程 start ≥ 最新源码 mtime | health=200／pid=29153／proc_start=06:01:18 ≥ newest=05:39:24 | 活端 health=200；agent_gateway 进程 pid **31340** start **2026-10-30T12:22:46**；最新源码 `config/v9/execution_policy.yaml` mtime **2026-10-06T20:36:45** ⇒ start≥newest ✓（注：旧码 BASE 缺省 5002，现役 5102，需环境适配） | **绿（需 BASE 适配）** | BASE 5102 | 否 |

**直跑汇总**：绿 1（C9）／红 5（C1,C2,C5,C7,C10）／未录 1（C6，被 C5 塌）／面内自动非真 2（C12,C13）⇒ **9/9 不可达**。
> ⚠ **塌面机制**：旧码 C5–C13 同处一个 `try`；C5 的 `KeyError` 直接跳到外层 `except` ⇒ 只记 C5 False，**C6/C7/C10/C12/C13 全不录** ⇒ 旧码直跑连「9 条」都不齐（≤4 条）。

## 三 B4 结论

1. **B4 直接阻断 C1/C2（2/9）**：v5 断言 `obsidian_brain`（源＋roster.json 双处），现役源/文件/活端三面皆无该 id（活端 6、文件 14）。
2. **B4 不是唯一阻断**：
   - **C5**：现役 `_KNOWLEDGE_FILES` schema 已由 `rel` 改 `sandbox_rel` ＋ `_resolve_knowledge_path` ⇒ 旧码 KeyError（且塌 C6）；
   - **C7/C10**：`_scan_excluded`／`last_walk_errors` 现役不存在（B2），**与 B4 无关**；
   - **C12/C13**：quick 面本就 skip ⇒ 自动 True 非真验；C13 full 面 blocked B3。
3. ⇒ **仅补 B4（把 obsidian_brain 加回 roster）不能恢复 9/9**；9/9 要恢复必须同时清 **B4 ＋ C5 schema ＋ B2 API**，且 **C12/C13 面标 N/A**——即 **需重基线**。
4. **需否 PM/PD 重基线**：**需**（口径三裁：C1/C2 以哪套 roster 为基〔活端 6／文件 14〕；C7/C10 新旧 API 语义等价性；C12/C13 quick 面 N/A 是否可接受）。

## 四 两方案 ＋ 判据（⛔ 本件不代裁）

### 方案 A（建议）：重基线后 9/9（现役口径）

- **做法**（只动 `legacy_verify`，不改旧库／产品码）：C1/C2 改为「现役 roster 自洽」口径（roster.py／roster.json／live 三方一致或按 PM/PD 裁的基准）；C5 改用 `_resolve_knowledge_path`；C7/C10 用 `_rel_excluded`／`_scan_vault` 重写（语义须核）；C12/C13 quick 面标 **N/A**；C9 用现役 BASE 5102＋进程判据。
- **判据（全满足才算 9/9 绿）**：
  1. 一次 `GET /v9/pa/verify?skip_scan=1`（或 CLI `--skip-scan`）**输出 9 条、无缺项、无异常塌面**；
  2. 每检仅 **PASS/FAIL/N/A** 三态；**C12/C13 标 N/A，⛔ 计绿**；
  3. 反例必红：删 1 件 SOP ⇒ C5 红；roster 三方不一致 ⇒ C1/C2 红；杀 agent_gateway ⇒ C9 红；改最新源码 mtime 晚于进程 ⇒ C9 红；
  4. 旧证 0545／旧码留档（一处本）；不改旧库；报告标「面标＋旧值」，不拿旧 14/14 冒今绿；
  5. 全跑两次同数（1 正 1 反）。
- **依赖**：D-11 扩权（现 D-11 仅批源复制，重基线属改语义 ⇒ 需补裁）；PM/PD 三裁（§三.4）。
- **风险**：重写 C7/C10 语义可能改变判据强度；C12/C13 N/A 须观感接受（否则 9/9 永久含 2 N/A）。

### 方案 B（兜底）：保留旧面 blocked

- **做法**：不重基线；9/9 明标 **blocked（B1–B5 未清）**；本件只出评估；R6 G3 维持红。
- **判据**：① 所有出口明标「blocked」、⛔ 出绿；② 旧证仅历史；③ 旧库不动、不建端；④ 下一迭代以新裁再议。
- **风险**：G3 不能收口，R6 持续黄/红；但**不假绿**。

## 五 复跑（只读 · 本刻可跑）

```powershell
# ① 旧源与面（只读）
wsl.exe bash -lc "sha256sum /home/flybo/clawsjoy_v5/core/pa/verify.py"
wsl.exe bash -lc "sed -n '952,961p' /home/flybo/clawsjoy_v5/core/pa/gateway_routes.py"
# ② 现役 C1/C2/C5/C6/C7/C10（期望：C1/C2 无 obsidian_brain；C5 schema 无 rel；C7/C10 缺符号；C6 目录在）
Select-String -Path core\\pa\\roster.py -Pattern 'obsidian_brain' -Quiet
node -e "const d=require('D:/clawsjoy_v9/data/v9/pa/roster.json');console.log(d.cards.map(c=>c.id))"
python -X utf8 -B -c "import sys;sys.path.insert(0,'.');from core.gateway import precision_inject as PI;print([k for k in PI._KNOWLEDGE_FILES['平台发布工作流']]);print(PI._resolve_knowledge_path('平台发布工作流'));print(hasattr(PI,'_scan_excluded'),hasattr(PI,'last_walk_errors'))"
# ③ 活端／进程／C9（期望 health 200；pid 31340 start 12:22:46 ≥ newest 10-06）
try { (Invoke-WebRequest 'http://127.0.0.1:5102/health' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 'ERR' }
try { $r=(Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/roster' -TimeoutSec 5 -UseBasicParsing).Content | ConvertFrom-Json; $r.count; ($r.rows | Where-Object id -eq 'obsidian_brain') } catch { 'ERR' }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'agent_gateway' } | Select-Object ProcessId,CreationDate
# ④ 旧证 9/9 值
node -e "const d=require('D:/Obsidian/ClawsJoy/ClawsJoy/dsh/_verify/pa_verify_20260928_0545.json');for(const id of ['C1','C2','C5','C6','C7','C10','C12','C13','C9']){const x=d.results.find(r=>r.id===id);console.log(id,x.pass,x.evidence)}"
```

## 六 证据四件套 ＋ 边界

| 件 | 径 | bytes | sha16 |
|---|---|---|---:|
| **本件** | `docs/reports/pa_iter40/28_g3_route_b4.md` | 见回执 | 生成后另报 |
| 旧验器源 | WSL `/home/flybo/clawsjoy_v5/core/pa/verify.py` | 9,675 | `f9ba9bede5620350` |
| 旧路由（quick 面） | WSL `core/pa/gateway_routes.py` L952-961 | 47,216 | `ad29de68fe5d4a99` |
| 现役 roster 源 | `core/pa/roster.py` | 17,150 | `81fc0103e5deaff8` |
| 现役 roster 数据 | `data/v9/pa/roster.json` | 18,054 | `0fd20b441ff0cbd5` |
| 现役 precision_inject | `core/gateway/precision_inject.py` | 62,294 | `54f24605e473a950` |
| D-11 裁决 | `docs/pa/relations/DECISION_LEDGER.md` | 2,392 | `13bd1fcc21ba5867` |
| 旧证 0545 | 外 `D:/Obsidian/ClawsJoy/ClawsJoy/dsh/_verify/pa_verify_20260928_0545.json` | 1,871 | `9b049df04bb3f11d` |
| G3 源定位 | `docs/reports/pa_iter40/17_g3_source.md` | 11,483 | `b96eee4d9153592d` |
| G3 授权包 | `docs/reports/pa_iter40/18_g3_authorization.md` | 2,132 | `42bb63ecc40fec05` |

**边界（照实）**
1. **只读**：未复制 WSL/私库源、未建 `/v9/pa/verify` 端、未改产品码/路由/配置/旧库。
2. **⛔ 假绿**：C12/C13 面内自动 True 明标 **N/A（非真验）**；C9 明标需 BASE 适配；旧 9/9 不作今日证。
3. **未代裁**：方案 A/B 只给内容与判据；B4 口径、C7/C10 语义、C12/C13 N/A 是否可接受，均**候 PM/PD 裁**。
4. **面数风险**：旧码 C5 一挂即塌 C6–C13 ⇒ 「9/9」在当前仓连条数都不齐；此为本件一手代码事实（verify.py L74-176）。
5. **现役版本**：活端 `/health`=9.0.47（取刻 14:42）；本评估针对「现役仓＋活端面」，不代表 9.0.42/9.0.45 旧态。

（完 —— 本件末行 · LF 终 · 悬）
