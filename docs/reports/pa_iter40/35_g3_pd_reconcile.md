# PA 迭代40 · T109 PD 对账：C10 反证与最小 adapter 条件

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1｜写域: `docs/reports/pa_iter40/35_g3_pd_reconcile.md`（本件唯一写入）
> 取刻: 2026-10-30T14:48:36～14:50:00+08:00｜只读对账：⛔ 建端 ／ ⛔ 改产品码/旧库 ／ ⛔ 把 N/A/未验充 PASS
> 对账对象: PM T105 `31_g3_pm_decisions.md`（9,773 B／sha16 **f825a9f8543a2734**）｜T107 `33_g3_decision_conflict.md`（1,635 B／**6c33b07d849e5975**）｜PD T106 `32_g3_pd_decisions.md`（11,467 B／**10d3b65055fe029f**）｜T102 `28_g3_route_b4.md`（11,392 B／**b2c0b0b9631f01fb**）

## 〇 结论（先判）

1. **PM 的第七条就是 C10**（`31_g3_pm_decisions.md` L61：7＝C1,C2,C5,C6,C7,**C10**,C9）。**C10 当前不可判 PASS**：现役无 `last_walk_errors`，无 `_LAST_WALK_ERRORS`，`_walk_warn` 只 print；旧 C10 证据不可复跑。
2. **quick 面 C10 亦不得充 PASS**：旧码 C10 在 `skip_scan=True` 时以 `bool(skip_scan)` 自动 pass，evidence 逐字 **「skip_scan：未验」**（旧 `verify.py` L149-153）。按 PM 裁 2/裁 3 自身「N/A/未验不计 PASS」，此条只能是 **N/A**，不是 PM 的 7 PASS 之一。
3. **计数纠正（quick 9 条 · C5 修后、C1/C2 按 PM 裁 1）**：**6 PASS（C1,C2,C5,C6,C7,C9）＋ 3 N/A（C10,C12,C13）＋ 0 FAIL**；C10 的 full 面为 **blocked**（无等价 API）。⇒ **PM 的「7 PASS＋2 N/A」算术不成立**；除非另立 C10 adapter 且改 quick 口径为真扫（不建议/非 quick），否则 7 不能含 C10。
4. **最小 adapter 条件**（若要做 C10 full 面）：adapter 必须自含旧容错 walker（`scandir` 保已读＋错误入册＋可选清单补面），**⛔ 不能只包现役 `os.walk(onerror)_walk_warn`**；条件见 §三。**本单不实现**。
5. **N/A/未验不充 PASS**：C10 quick 记 N/A（reason=skip_scan 未验/API 缺）；C12/C13 记 N/A；full C10 blocked；⛔ 旧 9/9 不作今日证。

## 一 反证：PM 第七条＝C10，不能算 PASS

| # | 反证点 | 一手据 |
|---|---|---|
| R1 | **符号不存在** | 现役 `core/gateway/precision_inject.py`（62,294 B／sha16 **54f24605e473a950**）grep `last_walk_errors`／`_LAST_WALK_ERRORS` **0 命中**；`hasattr(PI,"last_walk_errors")=False`（探针实测 14:45:46） |
| R2 | **现役只有 print，无留痕** | `_walk_warn` L106-109 只 `print`；`_walk_vault_md` L120 `os.walk(..., onerror=_walk_warn)`；无列表、无返回、无 `last_walk_errors` |
| R3 | **旧 C10 证据依赖旧 API** | 旧证 0545（1,871 B／**9b049df04bb3f11d**）C10 逐字 `{"id":"C10","pass":true,"evidence":"遍历留痕 last_walk_errors=[]"}`；该空表只能由旧 `last_walk_errors()` 产出，现役无此出口 |
| R4 | **quick 的 C10 是「未验 pass」，不是真 PASS** | 旧 `verify.py` L149-153：`rec("C10", (errs is not None) or bool(skip_scan), ... "skip_scan：未验" ...)`；`skip_scan=1` ⇒ pass=True，evidence=「未验」。PM 裁 2/裁 3 明定 N/A/未验不计 PASS ⇒ 此条与「7 PASS」自相矛盾 |
| R5 | **旧容错语义无法用现役 API 复刻** | 旧 v5 PI（60,693 B／**266337973917d5fd**）L162-208：容错 `scandir` 保留出错前条目＋错误入 `_LAST_WALK_ERRORS`＋`vault_manifest_win.txt` 逐路径补面；现役 `os.walk` 的 `onerror` 不保子树、无清单补面、无错误表 ⇒ 即使捕获 `_walk_warn` 也非旧 C10 等价 |
| R6 | **C10 判据强度也不同** | 旧 C10 只要 `errs is not None`（列表存在即可，错误可为非空）；现役连「列表存在」都无 ⇒ 不能以「未抛异常」或「scan 返回 notes」替代 |

**反证一句话**：PM 第七条 C10 的「PASS」只有两种可能来源：把旧 quick「未验 pass」当真，或把旧证空表当今日值；二者在本仓均不可复跑。故 **C10 不可判 PASS**。

## 二 逐条：C10 无等价 API（承 T106，补实据）

| 旧（v5） | 现役（v9.0.42） | 等价结论 |
|---|---|---|
| `_LAST_WALK_ERRORS` 列表（L128），`_walk_md` reset＋入册（L167/178） | 无同名/同义变量；无 reset/写入点 | **缺** |
| `last_walk_errors()`（L206-208）返回 `list` | 无此函数；无 `__getattr__` 代理 | **缺** |
| 容错 `scandir`（L131-159）：出错前条目**保留**并继续；错误入册（L176-185） | `os.walk` + `onerror=_walk_warn`（L120）；`onerror` 不保出错子树；无入册 | **行为不等** |
| `_walk_md` 以 `vault_manifest_win.txt` 对漏件逐路径补面（L186-201） | 无 manifest 补面（`legacy_verify/data/v9/…` 未被产品读取） | **缺** |
| 旧 C10 输出 `last_walk_errors=[]` | 现役 `_scan_vault` 只返 notes；读件异常 `except: continue`（L151-154） | **无出口** |

**结论**：C10 **不是改名/换签名**，而是**能力缺失**（无错误集合出口＋遍历容错语义不同）。T106 判 blocked 成立；PM 将 C10 计入 7 PASS 与一手不符。

## 三 最小 adapter 条件（若要做 C10；**本单不实现**）

要 C10 从 blocked → 可判（full 面）**至少**满足：

1. **授权范围**：D-11 扩权/新批，允许在 `legacy_verify/adapters/` 增代码（现 D-11 仅列复制件；adapter 属新码，⛔ 本单越权）。
2. **自含旧 walker**：adapter 内实现 `_scandir_tolerant` + `_walk_md` 等价（保留出错前条目、重置/写入错误表、排序、可选 `legacy_verify/data/v9/vault_manifest_win.txt` 补面）；**⛔ 不得**以现役 `os.walk(onerror)_walk_warn` 冒充。
3. **暴露同义 API**：`legacy_walk_errors() -> list`（可空表，但**必须存在**）；`legacy_scan_notes()` 只读；根取现役 `_vault_path()`/`PA_VAULT_ROOT`；⛔ 写盘/⛔ 改产品。
4. **C10 判据**：full 面调用后 `isinstance(errs, list)` 才可判；**空表也是 PASS**（旧语义是「有留痕」，非「零错」）；quick 面（skip_scan）仍记 **N/A**，不得 PASS。
5. **反例必红**：① 无错 → 空表 PASS；② 注入 `scandir` 在返回 1 条后抛 OSError → 错误列表非空且**已读条目保留**（旧语义）；③ 未注入但 API 缺失 → **blocked**（不得用空表冒充）；④ quick → N/A；⑤ 两跑同数；⑥ adapter 不被产品 import（`grep` 断言）。
6. **宿主边界**：adapter 只落 `legacy_verify/`；⛔ 改 `core/`／⛔ 建 `/v9/pa/verify`；full 14/14 仍按 D-11 暂缓；本单仅出条件。

**注意**：即使 adapter 完成，它只可能让 **full 面 C10 PASS**；**quick 面 C10 仍为 N/A**（skip_scan 未扫）——因此「quick 7 PASS＋2 N/A」在「N/A 不充 PASS」纪律下**仍不成立**；quick 只能是 **6 PASS＋3 N/A**（或 C10 单列 blocked）。

## 四 计数与三态（照实）

| 面 | 9 条/14 条 | PASS | N/A／blocked | FAIL | 口径 |
|---|---|---|---|---|---|
| quick（skip_scan=1） | C1,C2,C5,C6,C7,C10,C12,C13,C9 | **6**：C1,C2,C5,C6,C7,C9（C5 修 schema 后；C7 经 adapter） | **3**：C10（skip_scan 未验／full blocked）、C12、C13 | 0 | **6 PASS＋3 N/A＋0 FAIL**；⛔ 7+2；⛔ 9/9 全绿 |
| full（14/14） | C1–C14 除 C11 由 CLI 追加 | 未定（C1/C2 活端6、C5/C6/C7/C9 修后；C10 blocked；C12/C13/C14 旧面/B3） | C10 blocked；C12–C14 legacy/blocked | — | **14/14 blocked**（D-11 暂缓） |

- **N/A 不充 PASS**：C10/C12/C13 在 quick 面逐条 status=N/A（带 reason），不计入 PASS；PM 7 PASS 的第七条 C10 在此被剔除。
- **旧 9/9 不作今日证**：旧证 0545 的 C10 是旧 API 产物；旧 quick 的 C10 是 `bool(skip_scan)` 自动 pass（「未验」），皆非今日 PASS。

## 五 证据四件套（径＋sha16＋取刻＋复跑）

| # | 对象 | 径 | bytes | sha16 | 取刻 |
|---|---|---|---|---|---|
| E1 | PM 7+2 裁 | `docs/reports/pa_iter40/31_g3_pm_decisions.md` | 9,773 | **f825a9f8543a2734** | 14:46:27 |
| E2 | T107 冲突 | `docs/reports/pa_iter40/33_g3_decision_conflict.md` | 1,635 | **6c33b07d849e5975** | 14:47:59 |
| E3 | PD T106 | `docs/reports/pa_iter40/32_g3_pd_decisions.md` | 11,467 | **10d3b65055fe029f** | 14:47:30 |
| E4 | T102 | `docs/reports/pa_iter40/28_g3_route_b4.md` | 11,392 | **b2c0b0b9631f01fb** | 14:43:03 |
| E5 | 现役 PI | `core/gateway/precision_inject.py` | 62,294 | **54f24605e473a950** | 14:49:09 |
| E6 | 旧 v5 PI | WSL `/home/flybo/clawsjoy_v5/core/gateway/precision_inject.py` | 60,693 | **266337973917d5fd** | 14:49:09 |
| E7 | 旧验器 | `legacy_verify/core/pa/verify.py` | 9,675 | **f9ba9bede5620350** | 14:45:17 |
| E8 | 旧证 0545 | `legacy_verify/dsh/_verify/pa_verify_20260928_0545.json` | 1,871 | **9b049df04bb3f11d** | 14:45:17 |
| E9 | 活端 | `127.0.0.1:5102/health`＝200；5002 closed | — | — | 14:45:17 |

```powershell
Set-Location D:\clawsjoy_v9
# R1 PM 第七条与 7 名单
Select-String -Path docs/reports/pa_iter40/31_g3_pm_decisions.md -Pattern '7 PASS|7＝|C10'
# R2 C10 无 API
python -X utf8 -B -c "import sys;sys.path.insert(0,'.');from core.gateway import precision_inject as PI;print('last_walk_errors',hasattr(PI,'last_walk_errors'));print('_LAST_WALK_ERRORS',hasattr(PI,'_LAST_WALK_ERRORS'))"
Select-String -Path core/gateway/precision_inject.py -Pattern 'last_walk_errors|_LAST_WALK_ERRORS|def _walk_warn|onerror='
# R3 旧 C10 自动 pass 码
Get-Content legacy_verify/core/pa/verify.py | Select-Object -Skip 148 -First 6
# R4 旧证 C10
node -e "const d=require('./legacy_verify/dsh/_verify/pa_verify_20260928_0545.json');console.log(JSON.stringify(d.results.find(r=>r.id==='C10')))"
# R5 旧/新 PI sha16
wsl -d Ubuntu -- sha256sum /home/flybo/clawsjoy_v5/core/gateway/precision_inject.py
Get-FileHash core/gateway/precision_inject.py -Algorithm SHA256
# R6 端口
try { (Invoke-WebRequest 'http://127.0.0.1:5102/health' -UseBasicParsing -TimeoutSec 3).StatusCode } catch { $_.Exception.Message }
try { (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1',5002); '5002_OPEN' } catch { '5002_CLOSED' }
```

## 六 界

- 本单只读对账：未建端、未改产品码/旧库、未实现 adapter、未把 N/A/未验当 PASS；唯一写入本件。
- **C10 现状＝blocked**（full）／**N/A**（quick）；PM 第七条 C10 **不可判 PASS**；7+2 现不成立；quick 照实 6 PASS＋3 N/A＋0 FAIL。
- 若要做 C10 full PASS，须 D-11 扩权＋§三 最小 adapter 条件全满足；quick 仍 N/A，不得以 adapter 反推 7 PASS。
- 旧 9/9、旧证 0545 仅历史，不作今日证；14/14 按 D-11 暂缓。

（本件完 · T109 PD 对账 C10 反证）
