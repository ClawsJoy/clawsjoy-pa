# legacy_verify · PROVENANCE（D-11 最小复制）

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1｜写域: `legacy_verify/`（本件及范围内复制件）
> 取刻: 2026-10-30T14:38:56～14:40:00+08:00｜裁定: **D-11**（`docs/pa/relations/DECISION_LEDGER.md:39`）——「G3 9/9 最小复制获批：仅 verify.py/旧路由/CLI/旧证/两份清单入 legacy_verify，不改旧库；⛔ WSL 运行时依赖；14/14 暂缓」
> 纪律：**只读复制**；⛔ 改旧库；⛔ 建端/改产品码；⛔ 本目录被产品 import／执行／作 WSL 运行时依赖。

## 一 范围与逐件（D-11）

| # | 目标（相对本仓） | 源径 | 字节 | **sha16** | 源 mtime | 状态 |
|---|---|---|---|---|---|---|
| 1 | `legacy_verify/core/pa/verify.py` | WSL `/home/flybo/clawsjoy_v5/core/pa/verify.py` | 9,675 | **f9ba9bede5620350** | 2026-09-28 04:54:52 | ✅ 复制，sha 同 |
| 2 | `legacy_verify/core/pa/gateway_routes.py.L952-961.txt` | 同树 `core/pa/gateway_routes.py` **L952-961（10 行）**；父件 sha16 **ad29de68fe5d4a99** | 781 | **1f1bf995853e2c79** | 父件 2026-09-28 07:00:11 | ✅ 摘录（非全文件），sha 自证 |
| 3 | `legacy_verify/dsh/tools/dsh_pa_verify.py` | 旧库镜像 `D:\Obsidian\ClawsJoy\ClawsJoy\dsh\tools\dsh_pa_verify.py` | 2,160 | **5b73141e84cc294e** | 2026-09-28 04:21:29 | ✅ 复制，sha 同 |
| 4 | `legacy_verify/dsh/_verify/pa_verify_20260928_0545.json` | 旧库镜像 `D:\Obsidian\ClawsJoy\ClawsJoy\dsh\_verify\pa_verify_20260928_0545.json` | 1,871 | **9b049df04bb3f11d** | 2026-09-28 06:01:42 | ✅ 复制，sha 同 |
| 5 | `legacy_verify/data/v9/vault_manifest_win.txt` | WSL `/home/flybo/clawsjoy_v5/data/v9/vault_manifest_win.txt` | 722,197 | **98cf4c34a491b574** | 2026-09-28 05:38:15 | ✅ 找到并复制，sha 同 |
| 6 | `legacy_verify/data/v9/vault_missing_win.txt` | WSL `/home/flybo/clawsjoy_v5/data/v9/vault_missing_win.txt` | 1,436 | **d396aefaf6b7fc51** | 2026-09-28 04:49:27 | ✅ 找到并复制，sha 同 |

**缺项：无**（两份清单均在 WSL 旧树找到）。补充：WSL `/home/flybo/clawsjoy_v5/brain/dsh/_verify/` 只有 0420／0432／0436／0437／0500／0515 六件，**无 0545**；故 0545 取自旧库镜像（与 T77 06_pm 证一致），来源已记明。

**来源锚**：WSL 旧树 git `28b41c85e675720db84a39d843644dc420a8426c`（T77 一手）；当前仓 HEAD `8e23b02ce236beedb8ab45f329dce0fd90d41467`（master）。本复制仅读，未改旧库。

## 二 只读／完整性自证

- 复制方式：`Copy-Item -LiteralPath <源> -Destination legacy_verify/...`；摘录用 `read 952-961` 写入并加来源头；**未对源做写操作**。
- 复制后目标 sha16 **逐件等于源 sha16**（上表）；源在复制前后同一 sha（§四 R2/R3）。
- 复制件置 **ReadOnly 属性**（6/6，$true）；PROVENANCE.md 本体可写（记录用）。
- **未改旧库**：旧件 before/after 同 sha；未用 WSL 运行时；复制命令仅读 UNC/PowerShell 读源。
- **未建端/未改产品码**：本目录**无** import／路由注册／启动引用；仓内 `core/pa/verify.py` 仍不存在、`/v9/pa/verify` 仍 404（T77 结论未变）；D-11 明标 **14/14 暂缓**，本目录不作为 9/9 运行期依赖。
- 本任务唯一新增：`legacy_verify/**`；未触碰 `core/`、`scripts/`、`web/`、`dist/`、`data/`、旧库。

## 三 用途与边界（给后来者）

- 本目录是 **源留档（provenance）**，供 G3 恢复评估/复跑时比对；**不是运行时**：⛔ 加进 `sys.path`、⛔ import `legacy_verify`、⛔ 作为 WSL/网关依赖。
- 9/9 面＝旧路由 quick 面（`run_checks(skip_scan=1, live_http=False)`）；14/14 面暂缓（D-11）。
- 旧路由摘录里 `methods=["GET","POST"]` 是**旧形留档**；将来建端须按 T77 方案只读化（唯 GET、环回 200/非环回 403、⛔ token、1 正 1 反），不在本目录实施。

## 四 复跑与核验命令

```powershell
Set-Location D:\clawsjoy_v9
# R1 目标逐件 hash（应与 §一 同）
Get-ChildItem 'legacy_verify' -Recurse -File | ForEach-Object {
  $h=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower().Substring(0,16)
  '{0}|{1}|{2}' -f $_.FullName.Replace((Get-Location).Path+'\',''),$_.Length,$h
}
# R2 旧源 now（sha 应与 T77 同、复制前后不变）
Get-FileHash 'D:\Obsidian\ClawsJoy\ClawsJoy\dsh\tools\dsh_pa_verify.py' -Algorithm SHA256
Get-FileHash 'D:\Obsidian\ClawsJoy\ClawsJoy\dsh\_verify\pa_verify_20260928_0545.json' -Algorithm SHA256
wsl -d Ubuntu -- sha256sum /home/flybo/clawsjoy_v5/core/pa/verify.py /home/flybo/clawsjoy_v5/data/v9/vault_manifest_win.txt /home/flybo/clawsjoy_v5/data/v9/vault_missing_win.txt
wsl -d Ubuntu -- sha256sum /home/flybo/clawsjoy_v5/core/pa/gateway_routes.py
# R3 只读属性
Get-ChildItem 'legacy_verify' -Recurse -File | ForEach-Object { '{0}|RO={1}' -f $_.Name,(($_.Attributes -band [IO.FileAttributes]::ReadOnly) -ne 0) }
# R4 产品未动/未建端（应：False／404）
Test-Path core/pa/verify.py
try { (Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/verify' -UseBasicParsing -TimeoutSec 5).StatusCode } catch { $_.Exception.Message }
# R5 本任务范围外改动（本单只应新增 legacy_verify/；其余 M/?? 为前序迭代既有，非本单）
git status --porcelain -- legacy_verify core scripts web dist data
```

## 五 取刻／版本

- 复制取刻：2026-10-30T14:38:56～14:39:26+08:00（Copy-Item）；核验取刻 14:39:36+08:00。
- 旧树：WSL `/home/flybo/clawsjoy_v5`（commit 28b41c85…，2026-09-28）；旧库镜像 `D:\Obsidian\ClawsJoy\ClawsJoy`。
- 当前仓：`D:\clawsjoy_v9`（HEAD 8e23b02…，master）；`legacy_verify` 为新增、未入产品运行路径。

（本件完 · D-11 最小复制 · 14/14 暂缓）
