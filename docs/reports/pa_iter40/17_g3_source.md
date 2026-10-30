# PA 迭代40 · T77 G3 验器源定位／只读恢复评估

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1｜写域: `docs/reports/pa_iter40/17_g3_source.md`（本件唯一写入）
> 取刻: 2026-10-30T10:32:13～10:37:20+08:00｜**唯只读定位**：⛔ 未建端 ／ ⛔ 未改产品码 ／ ⛔ 造假端／假绿
> 判据: G3 缺 `/v9/pa/verify` 只读端；核 14/14 与 9/9 面标；源若找到出只读恢复方案（环回 200／非环回 403、⛔ 引 token、1 正 1 反）

## 〇 结论（先判）

| 项 | 结论 | 据 |
|---|---|---|
| 验器源 | **找到（一手）** | WSL 旧树 `/home/flybo/clawsjoy_v5/core/pa/verify.py`（sha16 **f9ba9bede5620350**）；旧路由 `core/pa/gateway_routes.py` L952-961（sha16 **ad29de68fe5d4a99**） |
| 14/14 面标 | **CLI 全量面**（含 live / scan / pytest） | CLI `dsh_pa_verify.py`（sha16 **5b73141e84cc294e**）L29-41：13 检 ＋ 追加 C11 ＝ **14/14** |
| 9/9 面标 | **路由 quick 面**（skip_scan、live_http=False） | 旧路由 L959 调 `run_checks(skip_scan=skip, live_http=False)`；CLI C11 L31 请求 `?skip_scan=1` ⇒ 9 检（见 §三） |
| 旧证 | **找到（旧树镜像）** `D:\Obsidian\ClawsJoy\ClawsJoy\dsh\_verify\pa_verify_20260928_0545.json` 1,871 B／sha16 **9b049df04bb3f11d**（与 06_pm 一致）；WSL `brain/dsh/_verify` 只有 0420–0515 六件，**无 0545** | 一手取件 |
| 仓内现状 | **仍缺**：`core/pa/verify.py` 不存在；`/v9/pa/verify` 在 5102 **404**（GET ／ `?skip_scan=1` 皆 404）；仓内路由 grep **0** | 09:47–10:37 活端/源扫 |
| 恢复评估 | **9/9 路由只读面：可恢复（源在）；14/14 文件面：不可直接复跑**（v5 依赖/数据/权限三道缺口，见 §五） | §四/§五 |

**一句话**：源与旧证**确在旧树**（WSL v5 ＋ Obsidian 旧库镜像），但**不是 drop-in**——`verify.py` 依赖的 `_scan_excluded`／`last_walk_errors`／v5 清单件在当前仓已无；14/14 不能照搬为今日绿。**本单未建端、未造假。**

## 一 源径与哈希（一手 · 径＋sha16＋取刻）

| 对象 | 径 | 大小／mtime | sha16 | 取刻 |
|---|---|---|---|---|
| 验器源（WSL 旧树） | `/home/flybo/clawsjoy_v5/core/pa/verify.py` | 9,675 B／2026-09-28 04:54:52 | **f9ba9bede5620350** | 10:35:23 |
| 旧路由（WSL 旧树） | `/home/flybo/clawsjoy_v5/core/pa/gateway_routes.py` | 47,216 B／2026-09-28 07:00:11 | **ad29de68fe5d4a99** | 10:35:09 |
| 验器 CLI（旧库镜像） | `D:\Obsidian\ClawsJoy\ClawsJoy\dsh\tools\dsh_pa_verify.py` | 2,160 B／2026-09-28 04:21:29 | **5b73141e84cc294e** | 10:34:41 |
| 验器 CLI（WSL 项目副本） | `/home/flybo/clawsjoy_v5/data/projects/web_1783219071801/session_1783388196051/clawsjoy_dev/tools/dsh_pa_verify.py` | 同 sha | **5b73141e84cc294e** | 10:36:33 |
| 旧证 0545 | `D:\Obsidian\ClawsJoy\ClawsJoy\dsh\_verify\pa_verify_20260928_0545.json` | 1,871 B／2026-09-28 06:01:42 | **9b049df04bb3f11d** | 10:34:41 |
| WSL _verify 全列 | `/home/flybo/clawsjoy_v5/brain/dsh/_verify/` | 6 件：0420／0432／0436／0437／0500／0515（无 0545） | — | 10:36:33 |
| 旧树 provenance | `/home/flybo/clawsjoy_v5`（git） | commit **28b41c85e675720db84a39d843644dc420a8426c**（PA(WSL): 写穿不删…） | — | 10:36:33 |
| 当前仓 | `D:\clawsjoy_v9` | HEAD **8e23b02ce236beedb8ab45f329dce0fd90d41467**；version **9.0.42** | — | 10:36:33 |

## 二 仓内／活端现状（G3 缺的一手）

| 检查 | 实测 |
|---|---|
| `core/pa/verify.py` | **不存在** |
| `/v9/pa/verify` 活端 | `/health` 200；`GET /v9/pa/verify` **404**；`GET /v9/pa/verify?skip_scan=1` **404** |
| 仓内路由 grep `/v9/pa/verify` ／ `core.pa.verify` | core/pa/agent_gateway/web **0 命中** |
| 路由挂载点 | `core/pa/pa_routes_common.py:773 register_pa_routes` 惰引 11 簇（L781-791），无 verify 簇 |
| 现役 roster（旧 C1/C2 依赖） | live ids ＝ `ds_chat, lingxi, lingxi_local_api, blender, local_vlm, v9_agent`（**无 obsidian_brain**） |
| 旧 C13/C14 数据 | `data/v9/vault_manifest_win.txt`／`vault_missing_win.txt` **均不存在** |
| 旧 C7/C10/C12 依赖 | `precision_inject` 无 `_scan_excluded`／`last_walk_errors`（现为 `_rel_excluded`／`_scan_vault`，语义不同） |
| 现役 loopback 工具 | `core/pa/owner_guard.py:24 is_loopback`；`deny()` 403 现成（可复用） |

## 三 14/14 与 9/9 面标（精确到件）

**14/14＝CLI「files_full」面**（旧证 `verifier: dsh_pa_verify v2 (core/pa/verify.py)`）：
- CLI L29 `run_checks(skip_scan=False, live_http=True)` ⇒ 13 检：`C1,C2,C3,C4,C5,C6,C7,C10,C12,C13,C14,C8,C9`；
- CLI L30-37 追加 **C11**（GET 路由可达）⇒ **results 共 14**；旧证 pass=14／total=14。

**9/9＝route「route_skip_scan」面**：
- 旧路由 L952-961：`/v9/pa/verify`（GET/POST）→ `run_checks(skip_scan=skip, live_http=False)`；
- CLI C11 L31 请求 `/v9/pa/verify?skip_scan=1` ⇒ core `run_checks`：
  - `live_http=False` ⇒ 跳过 C3/C4；
  - `skip_scan=True` ⇒ 跳过 C8、C14（C13 记 skip）；
  - core 无 C11；⇒ 实得 **C1,C2,C5,C6,C7,C10,C12,C13,C9＝9**；旧证 C11 evidence 逐字 `GET /v9/pa/verify -> ok=True pass=9/9`。
- **面标缺陷**：旧证顶层 `pass=14` 与 C11 内 `9/9` 无「面」标签 ⇒ 外部读者易混。恢复输出须**分面**：`files_full: 14/14` 与 `route_skip_scan: 9/9`，⛔ 扁平化。

## 四 只读恢复方案（**本单不实施**）

**前置授权（blocked 门）**：源在私人 Obsidian 库／WSL 旧树 ⇒ 须 owner（老板/库主）＋ CEO 批才可入仓；DSH 提供 WSL 取件环境。⛔ 本单未复制、未改码。

1. **入仓文件**
   - 新 `core/pa/verify.py`（自 sha16 f9ba9bede5620350 起动；按 §四.2 适配）。
   - 新 `core/pa/pa_routes_verify.py`（自旧路由 L952-961 抽取，只读化）。
   - `core/pa/pa_routes_common.py:791` 后追加 `from core.pa import pa_routes_verify  # noqa: F401`（同簇挂载）。
   - 新 `tests/unit/test_pa_verify_route_readonly.py`（1 正 1 反，见 §四.3）。
2. **verify.py 适配（关键：⛔ copy-paste 假绿）**
   - 径：`V9` 默认改仓根（`Path(__file__).resolve().parents[2]`）＋ env 覆；`VAULT` 用 `core.lib.paths.vault_root()`；`BASE` 用 `core.lib.port_config.gateway_base_url()`；去掉 `/home/flybo/clawsjoy_v5`、5002。
   - C1–C4：v5 的 `obsidian_brain` 断言 vs 现役 6 id roster ⇒ **重基线或标 legacy 不计**（⛔ 造假 PASS）。
   - C5/C6：现役 `precision_inject` 有 `_vault_path/_KNOWLEDGE_FILES/_obsidian_cfg` ⇒ 可接。
   - C7/C10/C12：旧依赖 `_scan_excluded`／`last_walk_errors` 缺失 ⇒ 用现役 `_rel_excluded`／`_scan_vault` 重写＋补语义测试（不可原样）。
   - C13/C14：`data/v9/vault_manifest_win.txt`／`vault_missing_win.txt` 缺失 ⇒ 从旧数据恢复（须授权）或改判面；缺则 **14/14 blocked**。
   - C8：现役 `tests/unit/test_roster.py` 在；C9：按现役 pid/health 重写。
3. **只读路由规格**
   - **唯 GET**（旧为 GET/POST ⇒ POST 去掉，POST ⇒ 405）。
   - 环回：`is_loopback(request)` ⇒ 200；否则 `owner_guard.deny()` ⇒ **403** `code=owner_required`；**⛔ 引 token**（不读 Authorization）；仅 GET 只读，⛔ 写盘/⛔ 自 HTTP（`live_http=False`）。
   - 响应分面：`{"ok":…, "face":"route_skip_scan", "pass":9,"total":9, "files_face":{"state":"blocked|ok","pass":14,"total":14,"source":"cli_full"}, "results":[…] }`；若文件面未复基 ⇒ `files_face.state="blocked"`＋因，⛔ 用 9/9 冒充 14/14。
   - 1 正 1 反：① 环回 GET 200 且只读（前后文件 mtime/无写探针）；② 非环回 `REMOTE_ADDR=192.168.3.9` ⇒ 403；③ 反控 POST ⇒ 405；④ ⛔ token 旁路（无 Authorization 亦仅环回 200）。
4. **复跑（建后）**：`pytest tests/unit/test_pa_verify_route_readonly.py -q`；`curl` 环回/非环回；`dsh_pa_verify.py all --json`（CLI 面）与 `?skip_scan=1`（路由面）分别报面标。

## 五 阻塞（照实 · 谁提供）

| # | 阻塞 | 需谁 |
|---|---|---|
| B1 | 源/证在**私人 Obsidian 库 ＋ WSL 旧树**；入仓须授权（且 WSL 0545 缺，需用 Windows 旧库镜像件） | 老板/库主 ＋ CEO（D1 授权）；DSH（WSL 取件） |
| B2 | C7/C10/C12 旧依赖 `_scan_excluded`／`last_walk_errors` 现役无 ⇒ 须重写 | PD/后端（本席可出 patch，另单） |
| B3 | C13/C14 旧数据 `vault_manifest_win.txt`／`vault_missing_win.txt` 现役无 ⇒ 14/14 完整文件面 **不可直接复跑** | 数据源主（老板/旧库）；或裁「旧面不复」 |
| B4 | C1–C4 v5 roster `obsidian_brain` 已不在现役 6 id 中 ⇒ 须 PM/PD 重基线 | PM/PD |
| B5 | 现役 `/v9/pa/verify` 404，G3 仍红；建端后须 1 正 1 反 复跑方可判绿 | PD（授权/移植后） |

**结论**：**源存在且可读（9/9 路由 quick 面有完整源，可直接恢复）；14/14 full 面因 v5 依赖/数据/授权三道缺口，当前判 blocked，⛔ 不得以旧证冒充今日绿。** G3 在 B1–B5 清前仍红。

## 六 证据四件套（径＋sha16＋取刻＋复跑）

| # | 对象 | sha16/值 | 取刻 | 复跑 |
|---|---|---|---|---|
| E1 | WSL verify.py | **f9ba9bede5620350**（9,675 B） | 10:35:23 | R1 |
| E2 | WSL gateway_routes.py | **ad29de68fe5d4a99**（47,216 B；L952 route） | 10:35:09 | R2 |
| E3 | CLI dsh_pa_verify.py | **5b73141e84cc294e**（2,160 B；WSL 副本同 sha） | 10:34:41 | R3 |
| E4 | 旧证 0545 | **9b049df04bb3f11d**（1,871 B） | 10:34:41 | R4 |
| E5 | 14/14 面 | CLI 13 检 ＋ C11＝14；旧证 pass=14/total=14 | 10:34:41 | R5 |
| E6 | 9/9 面 | route skip_scan：C1,C2,C5,C6,C7,C10,C12,C13,C9 | 10:37:20 | R6 |
| E7 | 仓内缺 | verify.py=False；grep=0；live `/v9/pa/verify` 404（health 200） | 10:36:48 | R7 |
| E8 | 现役阻断点 | roster ids 6（无 obsidian_brain）；两份 v9 清单件缺；`_scan_excluded`／`last_walk_errors` 缺 | 10:36:48 | R8 |

```powershell
# R1 WSL 验器哈希
wsl -d Ubuntu -- sha256sum /home/flybo/clawsjoy_v5/core/pa/verify.py
# R2 旧路由与行
wsl -d Ubuntu -- sed -n '952,961p' /home/flybo/clawsjoy_v5/core/pa/gateway_routes.py
# R3/R4 旧库镜像 CLI/证 hash
Get-FileHash 'D:\Obsidian\ClawsJoy\ClawsJoy\dsh\tools\dsh_pa_verify.py' -Algorithm SHA256
Get-FileHash 'D:\Obsidian\ClawsJoy\ClawsJoy\dsh\_verify\pa_verify_20260928_0545.json' -Algorithm SHA256
# R5 旧证面读（pass/total + C11）
Get-Content 'D:\Obsidian\ClawsJoy\ClawsJoy\dsh\_verify\pa_verify_20260928_0545.json' -Raw
# R6 /v9/pa/verify 现状
try { (Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/verify' -UseBasicParsing -TimeoutSec 5).StatusCode } catch { $_.Exception.Message }
# R7 仓内缺
Test-Path core/pa/verify.py
Select-String -Path core/pa/*.py,agent_gateway_enhanced.py,web/pa/**/*.js -Pattern '/v9/pa/verify|core\\.pa\\.verify'
# R8 现役依赖核
Select-String -Path core/gateway/precision_inject.py -Pattern '_scan_excluded|last_walk_errors'
Test-Path data/v9/vault_manifest_win.txt; Test-Path data/v9/vault_missing_win.txt
```

## 七 界

- 本单唯只读：未建端、未改产品码/路由、未复制私库件、未以旧证充今日绿。
- 旧树为 v5（2026-09-28）；与现役 9.0.42 有代码/数据/roster 漂移 ⇒ 恢复须按 §四 重基线并 1 正 1 反。
- 纯拿到「9/9 可恢复」不等于「14/14 可判绿」；后者待 B1–B5。

（本件完 · T77 G3 源定位/只读恢复评估）
