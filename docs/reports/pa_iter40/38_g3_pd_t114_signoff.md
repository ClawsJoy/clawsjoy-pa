# PA 迭代40 · T115 PD 复签 T114 7+2 本地真扫面

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1｜写域: `docs/reports/pa_iter40/38_g3_pd_t114_signoff.md`（本件唯一写入）
> 取刻: 2026-10-30T15:04:00～15:06:00+08:00｜只读复核：⛔ 建端 ／ ⛔ 改码/产品 ／ ⛔ 冒绿
> 对象: T114（task-114，api-dev · 修 C2；写域 `legacy_verify/run_quick.py`、`legacy_verify/tests`）｜T113 前签 `37_g3_pd_t112_signoff.md`（0b35f476b7c8d864）｜PM 裁 1 `31_g3_pm_decisions.md`（f825a9f8543a2734）

## 〇 签核结论

| 项 | 签？ | 边界 |
|---|---|---|
| **7 PASS＋2 N/A＝legacy_7_2 本地真扫面** | **签** | C2 活端 6 全等；40 tests；两跑 7/0/2；C10 真扫 8,683 件；仅**本地脚本面** |
| **route quick／9/9** | **不签** | 不得称 `/v9/pa/verify?skip_scan=1` 或 9/9；C12/C13 N/A 不充 PASS |
| **14/14** | **不签** | D-11 暂缓；B1–B5 未清 |
| **建只读路由** | **本单不授权** | 须另批（D-11 扩权/台账＋PM/PD）；端点现仍 404 |

**一句话**：T113 的 G1（C2 假绿）已修实——C2 改读活端 5102 且 count=6/ids 全等；dev14、端点不可用、count6-id 不等皆反例红。**签 legacy_7_2 本地 7 PASS＋2 N/A；⛔ 签 route/9/9/14/14。**

## 一 C2 活端 6 全等

| 核 | 实据 | 判 |
|---|---|---|
| 只读活端 5102 | `run_quick.py` L41 `LIVE_ROSTER_URL="http://127.0.0.1:5102/v9/pa/roster"`；L61-74 `_fetch_live_roster` | **过** |
| 移除 dev 回落 | `check_c2` L88-112；源内无 `_roster_runtime_ids`／`roster.json`；`test_c2_source_does_not_read_dev_roster_json` | **过** |
| count=6 ∧ ids 全等 | L105-106：`len(ids)==len(defaults) and sorted(ids)==sorted(defaults)`；L106 `count==6` 且 len=6；L107 无 obsidian_brain | **过** |
| 反例红 | `test_c2_dev14_subset_is_red`（14 FAIL）、`test_c2_endpoint_unavailable_fail`、`test_c2_count6_but_ids_not_equal_fail`、`test_c2_rows_not_six_fail` | **过** |
| 实跑 | C2 evidence：`count=6, rows_n=6, exact_eq=true, ids=[ds_chat,lingxi,lingxi_local_api,blender,local_vlm,v9_agent]`，`status=PASS` | **过** |

**G1 关闭**：T113 的 C2 假绿（dev 14 子集）不存在；现 C2 只认活端 6 全等，端点不可用即 FAIL（⛔ 回落）。

## 二 7+2 本地真扫面（实跑两同）

| 项 | 实测（15:05:25 两跑一致） |
|---|---|
| 面 | `face=legacy_7_2` |
| 计数 | `pass=7, fail=0, na=2`（7＝C1,C2,C5,C6,C7,C10,C9；N/A＝C12,C13） |
| C10 | `walker=legacy_v5_tolerant`，`state=ok`，`file_count=8683`，`error_count=0`，`errors=[]`（list） |
| C9 | `base_url=http://127.0.0.1:5102`，`health=200`，`port=5102`，进程起点 2026-10-30T12:22:46 新鲜 |
| C1/C5/C6/C7 | 源默认 6；SOP 三件存在；sops_dir 存在；C7 八反例全 ok（含 `工作区/_冷区/x.md=False`、反斜杠 `Templates\t.md=True`） |
| C12/C13 | `status=N/A`，`not_pass=true`，reason=skip_scan 未扫（⛔ 计 PASS） |
| 退出码 | 0；两跑同数 |

**判**：**7 PASS＋2 N/A 成立（仅本地 legacy_7_2 面）**；C10 是真容错 walker（非空表假绿），C2 已活端全等。T113 的 G1 闭环。

## 三 面义与限制（明标）

1. **本地面**：`legacy_verify/run_quick.py` 是本地复跑器；`face=legacy_7_2` **不是** `/v9/pa/verify?skip_scan=1` 的 route quick 面。
2. **C10 真扫 ≠ 旧 quick**：T114 的 C10 真跑 8,683 件（本地 walker）；旧 route quick 不扫（旧 C10 为「skip_scan：未验」自动 pass）。二者不可互证。
3. **⛔ 9/9**：7 PASS＋2 N/A ≠ 9 全绿；C12/C13 N/A 永不充 PASS；旧 9/9 旧证不作今日证。
4. **14/14 仍 blocked**：D-11 暂缓；B1–B5 未清。
5. **C2 依赖活端 5102**：端点不可用 ⇒ C2 FAIL（⛔ 回落 dev 14）；本地面须在本机活端上跑。

## 四 若建只读路由：边界（**本单不建，仅定义**）

将来另批建 `GET /v9/pa/verify`（只读）时，**只准**暴露本地面，且须同时满足：

| # | 边界 | 机检 |
|---|---|---|
| B1 | **仅本地 legacy_7_2 面** | 响应 `face=legacy_7_2`、7 PASS＋2 N/A；⛔ 报 9/9/14/14 |
| B2 | **唯 GET 只读** | POST/PUT/PATCH/DELETE ⇒ 405；不写盘/不改 data/不 import 产品 legacy |
| B3 | **环回 200／非环回 403** | `owner_guard.is_loopback(request)` 真 ⇒ 200；否则 `owner_guard.deny` ⇒ 403 `code=owner_required` |
| B4 | **⛔ 引 token** | 不读 Authorization；无 token 旁路；403 不降级 |
| B5 | **1 正 1 反** | 正：环回 GET ⇒ 200 且 body face/7/2；反：`REMOTE_ADDR=192.168.3.9` ⇒ 403；反：POST ⇒ 405 |
| B6 | **C10 真读数** | 响应含 `walker=legacy_v5_tolerant`、`errors` 为 list、`file_count>0` 或 `error_count>0`；⛔ 空表假绿 |
| B7 | **授权/台账** | 建端前须 D-11 扩权/新裁入 `DECISION_LEDGER`＋PM/PD 明示接受「本地真扫 C10＋C12/C13 N/A」；⛔ 以本签视为建端授权 |

**现刻状态**：`core/pa/verify.py` 无；`GET /v9/pa/verify` **404**；本签不改变端点、不建端。

## 五 签核/缺口

| 项 | 签？ | 说明 |
|---|---|---|
| C2 活端 6 全等 | **签** | dev14／端点不可用／count6-id 不等皆反例红 |
| 7 PASS＋2 N/A（legacy_7_2 本地） | **签** | 两跑同数；C10 真扫；C12/C13 N/A |
| route quick／9/9 | **⛔ 不签** | 面义不同；N/A 不充 PASS |
| 14/14 | **⛔ 不签** | D-11 暂缓；B1–B5 |
| 建只读路由 | **本单不授权** | 须另批；按 §四 B1–B7 |

**残余**：无阻断本地签缺口；仅「建端」须另批（授权/台账＋§四边界）。

## 六 证据四件套（径＋sha16＋取刻＋复跑）

| # | 对象 | 径 | bytes | sha16 | 取刻 |
|---|---|---|---|---|---|
| E1 | run_quick（T114 修后） | `legacy_verify/run_quick.py` | 12,660 | **ed736e36e2095552** | 15:05:50 |
| E2 | tests/run_quick | `legacy_verify/tests/test_run_quick.py` | 8,422 | **47ab34152e6bfd23** | 15:05:50 |
| E3 | tests/adapters | `legacy_verify/tests/test_adapters.py` | 10,036 | **e1954c7ccdbe3e40** | 15:05:50 |
| E4 | C10 walker | `legacy_verify/adapters/legacy_walker.py` | 5,487 | **084cbb4efc4060ee** | 15:05:50 |
| E5 | 适配面 | `legacy_verify/adapters/precision_inject_v9.py` | 6,347 | **f80a47578549148b** | 15:05:50 |
| E6 | 测试 | `python -m pytest -p no:cacheprovider legacy_verify/tests -q` ⇒ **40 passed** | — | — | 15:05:25 |
| E7 | run_quick 两跑 | face legacy_7_2、7/0/2、C10 8683/0、C2 6 全等、C9 5102/200 | — | — | 15:05:25 |
| E8 | 产品/端点 | `core/pa/verify.py` 无；`/v9/pa/verify` 404；`core` grep `legacy_verify`=0 | — | — | 15:05:50 |

```powershell
Set-Location D:\clawsjoy_v9
# R1 40 tests
python -X utf8 -B -m pytest -p no:cacheprovider legacy_verify/tests -q
# R2 两跑（应 face=legacy_7_2, 7/0/2）
python -X utf8 -B legacy_verify/run_quick.py
python -X utf8 -B legacy_verify/run_quick.py
# R3 C2 活端 6 全等（应 count=6, exact_eq=true）
python -X utf8 -B -c "from legacy_verify import run_quick as R; import json; print(json.dumps(R.check_c2(),ensure_ascii=False))"
# R4 活端
try { $j=(Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/roster' -UseBasicParsing -TimeoutSec 5).Content|ConvertFrom-Json; 'count=' + $j.count; ($j.rows|ForEach-Object{$_.id}) -join ',' } catch { $_.Exception.Message }
# R5 产品/端点/范围
Test-Path core/pa/verify.py
try { (Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/verify' -UseBasicParsing -TimeoutSec 3).StatusCode } catch { '404' }
Select-String -Path core/*.py,core/**/*.py -Pattern 'legacy_verify' -ErrorAction SilentlyContinue
git status --porcelain -- core scripts web; git status --porcelain | Measure-Object -Line
```

## 七 界

- 本单只复核/签：未建端、未改 T114 代码/测试、未改产品码/旧库；唯一写入本件。
- **签**：C2 活端 6 全等；**legacy_7_2 本地面 7 PASS＋2 N/A**（C10 真扫）。
- **不签**：route quick／9/9／14/14；**不授权建端**（须另批，按 §四 B1–B7）。
- 面义：本地真扫 C10＋C12/C13 N/A；旧 9/9、旧证、route quick 均不充今日 PASS。

（本件完 · T115 PD 复签 T114 7+2 本地真扫面）
