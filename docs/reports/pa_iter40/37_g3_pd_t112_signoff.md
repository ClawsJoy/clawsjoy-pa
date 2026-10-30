# PA 迭代40 · T113 PD 签核 T112 C10 walker

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1｜写域: `docs/reports/pa_iter40/37_g3_pd_t112_signoff.md`（本件唯一写入）
> 取刻: 2026-10-30T14:59:39～15:02:00+08:00｜只读复核：⛔ 建端 ／ ⛔ 改码/产品 ／ ⛔ 冒绿
> 复核对象: T112（task-112，api-dev · 写域 `legacy_verify/adapters`／`run_quick.py`／`tests`）；T106 条件 `32_g3_pd_decisions.md`（**10d3b65055fe029f**）；PM 裁 1 `31_g3_pm_decisions.md`（**f825a9f8543a2734**）

## 〇 签核结论（先判）

| 项 | 结论 | 一句话 |
|---|---|---|
| **C10 walker 技术子项** | **签** | 自含容错 walker（scandir 保已读＋错误入册＋清单补面）、`legacy_walk_errors()->list`、34 tests 全绿、C10 真跑 8,683 件/0 错；无产品 import/无端点 |
| **7 PASS＋2 N/A 作为 G3 重基线** | **不签（现刻）** | **C2 是假 PASS**：run_quick C2 读仓内 dev `data/v9/pa/roster.json`（14 张），仅判 `defaults_subset`，与 PM 裁 1「活端 6 为基／文件 14 不采」冲突；7 PASS 不成立 |
| 若修 C2＋面标＋授权台账 | **可再签** | 修后 7+2 可作 **本地 legacy_7_2 面** 的 G3 重基线；仍 ⛔ 9/9、⛔ 路 quick 假面 |

**总判**：**T112 的 C10 walker 实现本身合格（技术签）；但 T112 报的「7 PASS」因 C2 假绿不能整体签**。不签 7+2，列缺口见 §二/§三。

## 一 T106 最小条件逐条核（C10 部分）

| # | T106 条件 | T112 实据 | 判 |
|---|---|---|---|
| 1 | D-11 扩权/新批，adapter 只落 `legacy_verify/` | task-112 由 Lead 派单，写域明列 `legacy_verify/adapters`／`run_quick.py`／`tests`（新批）；**DECISION_LEDGER 仅 D-11 源复制行（L39），无扩权台账行** | **技术满足；G3 基线须补台账/裁** |
| 2 | 自含旧容错 walker（scandir 保已读＋错误入册＋可选清单补面） | `legacy_verify/adapters/legacy_walker.py`（5,487 B／**084cbb4efc4060ee**）：L54-87 scandir 递归、L67-69 中途错保已读、L99-125 清单补面 | **过** |
| 3 | 暴露 `legacy_walk_errors()->list`；只读；根取现役 | L34-36、L143-157 返回 `list`；`precision_inject_v9.legacy_walk` 根取 `vault_root_or_none()`（L98-113）；只读 | **过** |
| 4 | C10 判据：list 存在（可空表 PASS）；quick 面 N/A | `run_quick.py` L130-158：walker id／state ok／有读数／`isinstance(errs,list)`；空 list 可 PASS。**但本件 C10 是本地真扫，不是 route skip_scan** | **技术过；面义须标清** |
| 5 | 反例必红：正常、注 OSError、保已读、清单缺、两跑同数、不 9/9 | `tests/test_adapters.py` L172-255（注入 `PermissionError`／中途 OSError 保已读／清单补面/缺失）；`test_run_quick.py` L57-64、L150-158（⛔ 9/9、C10 非 PASS 面漂移） | **过** |
| 6 | 无产品 import／无端点／无假面 | `test_product_does_not_import_legacy_verify` 过；`core` grep `legacy_verify` **0**；`core/pa/verify.py` 仍无、活端 `/v9/pa/verify` 仍 **404**；`legacy_walker` 无 Flask/Blueprint | **过** |

**C10 真跑（15:00:38/15:01:29 两跑）**：`face=legacy_7_2`，`file_count=8683`，`error_count=0`，`errors=[]`，`walker=legacy_v5_tolerant`，`manifest` 在；**无空表假绿**（真扫有读数，且 errors 为 list）。⇒ **C10 walker 技术子项签。**

## 二 不签 7+2 的原因（关键缺口）

### G1（阻断）C2 假 PASS：读 dev 14 张，非活端 6

- PM 裁 1（`31_g3_pm_decisions.md` L11／L33／L34）：**以活端 6 为基**；C1/C2＝「源默认 6 ＝ 运行时 6」；**文件 14 不采**（dev 附册，装根无 roster.json）。
- T112 `legacy_verify/run_quick.py`：
  - L59：`p = ROOT / "data" / "v9" / "pa" / "roster.json"`（**仓内 dev 文件**，非活端/装根）；
  - L88：`ok = bool(ids) and set(defaults) <= set(ids) and "obsidian_brain" not in ids`（**只判子集**，14 张即可过）；
  - 实测 `check_c2()`：`{"runtime_ids":[…14 张…],"n":14,"defaults_subset":true}`，`status=PASS`（run_quick 同一证据）。
- 现役活端：`GET 127.0.0.1:5102/v9/pa/roster` ⇒ `count=6`，ids＝`ds_chat,lingxi,lingxi_local_api,blender,local_vlm,v9_agent`。
- **判**：C2 的 PASS 是 **假绿**（14 ≠ 6；只判子集）；7 PASS 里含此条 ⇒ **7 不能作为 G3 重基线**。修法：C2 改读活端 6（或装根默认 6），断言 `set(ids)==set(defaults)` 且 `len(ids)==6`，并加「dev 14 ⇒ FAIL」反例。

### G2（面义）legacy_7_2 是本地真扫面，不是 route quick/9/9

- `run_quick.py` C10（L130-158）在本地 **真跑** `legacy_walker`（8,683 件）；这与旧 `/v9/pa/verify?skip_scan=1` 的 quick 面（不扫）**语义不同**。
- T112 输出 `face=legacy_7_2`（7 PASS＋2 N/A）已自标；**⛔ 不得**把它写成 route quick、⛔ 不得报 9/9；C12/C13 N/A 是 skip_scan 未扫，符合。
- 若 G3 重基线采用此本地面，须 **PM/PD 明示接受**「本地真扫 C10＋C12/C13 N/A」；否则 C10 仍属 full 面/旧 quick N/A。

### G3（授权/台账）D-11 扩权仅任务级，台账未记

- `docs/pa/relations/DECISION_LEDGER.md:39` 只有 D-11「源复制」；无「legacy_verify adapter 扩权」行。task-112 是 Lead 新派单（新批）＋写域，**任务级**可做；但 **G3 重基线** 需在台账/裁定中留痕，否则后续审计对不上「D-11 扩权另批」。
- 本项不否 C10 技术签，但否「7+2 直接作 G3 基线」的合规性。

## 三 签核/缺口清单

| 项 | 签？ | 缺口/条件 |
|---|---|---|
| C10 walker（scandir 保已读/错误 list/清单补面/反例/无产品） | **签** | 无技术缺口；仅面义需标「本地 legacy_7_2」 |
| C2 运行时 roster（活端 6） | **不签** | 读 dev 14 且只判子集；改读活端/装根默认 6＋全等断言＋dev14 反例 |
| 7 PASS＋2 N/A（legacy_7_2） | **不签（现刻）** | G1 阻断；G2 面义需 PM/PD 接受；G3 台账需补 |
| 9/9 或 route quick 全绿 | **⛔ 不签** | C12/C13 N/A 不充 PASS；C10 本地面非 route |

**修后预期**：C2 改活端 6、G2/G3 留痕 ⇒ 可复核为 **legacy_7_2：7 PASS（C1,C2,C5,C6,C7,C10,C9）＋2 N/A（C12,C13）＋0 FAIL**；仍 **⛔ 9/9**、仍非 14/14。

## 四 证据四件套（径＋sha16＋取刻＋复跑）

| # | 对象 | 径 | bytes | sha16 | 取刻 |
|---|---|---|---|---|---|
| E1 | legacy walker | `legacy_verify/adapters/legacy_walker.py` | 5,487 | **084cbb4efc4060ee** | 15:01:29 |
| E2 | 适配面 | `legacy_verify/adapters/precision_inject_v9.py` | 6,347 | **f80a47578549148b** | 15:01:29 |
| E3 | run_quick | `legacy_verify/run_quick.py` | 11,069 | **27219c00bad3d641** | 15:01:29 |
| E4 | tests/adapters | `legacy_verify/tests/test_adapters.py` | 10,036 | **e1954c7ccdbe3e40** | 15:01:29 |
| E5 | tests/run_quick | `legacy_verify/tests/test_run_quick.py` | 5,736 | **82fa4a703de37b41** | 15:01:29 |
| E6 | PM 裁 1/7+2 | `docs/reports/pa_iter40/31_g3_pm_decisions.md` | 9,773 | **f825a9f8543a2734** | 14:46:27 |
| E7 | T106 条件 | `docs/reports/pa_iter40/32_g3_pd_decisions.md` | 11,467 | **10d3b65055fe029f** | 14:47:30 |
| E8 | run_quick 两跑 | stdout JSON（15:00:38／15:01:29）：face legacy_7_2、pass 7／fail 0／na 2、C10 file_count 8683／error_count 0 | — | — | 15:00–15:01 |
| E9 | 测试 | `python -m pytest -p no:cacheprovider legacy_verify/tests -q` ⇒ **34 passed** | — | — | 15:00:38 |
| E10 | 产品/端点 | `core/pa/verify.py` 无；`/v9/pa/verify` **404**；`core` grep `legacy_verify`=0 | — | — | 15:01:29 |

```powershell
Set-Location D:\clawsjoy_v9
# R1 测试
python -X utf8 -B -m pytest -p no:cacheprovider legacy_verify/tests -q
# R2 两跑（应 7/0/2，C10 PASS）
python -X utf8 -B legacy_verify/run_quick.py
python -X utf8 -B legacy_verify/run_quick.py
# R3 C2 反例（当前：n=14 PASS ⇒ 修前假绿）
python -X utf8 -B -c "from legacy_verify import run_quick as R; import json; print(json.dumps(R.check_c2(),ensure_ascii=False))"
# R4 活端 6
try { $j=(Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/roster' -UseBasicParsing -TimeoutSec 5).Content|ConvertFrom-Json; 'count=' + $j.count; ($j.rows|ForEach-Object{$_.id}) -join ',' } catch { $_.Exception.Message }
# R5 产品/端点/范围
Test-Path core/pa/verify.py
try { (Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/verify' -UseBasicParsing -TimeoutSec 3).StatusCode } catch { '404' }
Select-String -Path core/*.py,core/**/*.py -Pattern 'legacy_verify' -ErrorAction SilentlyContinue
git status --porcelain -- core scripts web; git status --porcelain | Measure-Object -Line
```

## 五 界

- 本单只签名/复核：未建端、未改 T112 代码/测试、未改产品码/旧库；唯一写入本件。
- **签 C10 walker 技术子项**；**不签 7+2/G3 重基线**（C2 假绿为阻断；面义/台账为条件）。
- 修 G1（C2 活端 6 全等）＋G2（面义 PM/PD 接受）＋G3（台账）后，可再签「legacy_7_2：7 PASS＋2 N/A」；仍 ⛔ 9/9、⛔ 14/14。
- 旧 9/9、旧证、quick 未验均不充今日 PASS。

（本件完 · T113 PD 签核 T112 C10 walker）
