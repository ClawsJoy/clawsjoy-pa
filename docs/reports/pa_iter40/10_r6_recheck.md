# PA 迭代40 · T63 C-30 PM R6 版本一致性重验（9.0.40）

> 代发: DSH（PA）｜席：PM（pm-dev）｜WIP=1（本单）｜写域：仅本件（`docs/reports/pa_iter40/10_r6_recheck.md`）｜取刻：2026-10-30T08:35:18+08:00
> 输入：T62 9.0.40 干净包（Setup sha256[:16] `a635373eaf4f7e77`、payload version 9.0.40）；T48 `06_pm.md`（`b086b3cd996670df`）R6 旧态
> 纪律：**只读重验**，⛔ 改产品码/索引、⛔ 编造绿；未实测的（如 9.0.40 安装后装根）一律标「未实测」。

## 〇 一页（先判）

| 项 | 结论 |
|---|---|
| **版本六处（代码 4 ＋ 包 2）** | **全部 9.0.40**：`core/lib/version.py` ／ `pyproject.toml` ／ `core/lib/platform_client.py` 字面 ／ `shell/package.json` ／ payload `version.json` ／ Setup FileVersion ＋ win-unpacked FileVersion |
| **装根 / 活端（本机 dev）** | **仍旧值**：repo `version.json` ＝ **9.0.11**；活端 `/health` 三值（build 9.0.11 ／ update.current 9.0.11 ／ 顶层 version **9.0.38**）——属本机旧安装/旧进程，**不是 9.0.40 包**；9.0.40 安装后装根 **未实测**（不编造） |
| **14/14 vs 9/9 分母** | **未修**：分母来源已查明（§三），但验器源不在本仓、payload 亦无、活端 `/v9/pa/verify` ⇒ **404** ⇒ **不可复算**，仅存 2026-09-28 旧证 |
| **R6 现判** | **黄（部分改善；⛔ 不升绿）**：①版本值一致 **绿**；②定义点=1 **红**（platform_client 手写字面 ＋ 装根旧值）；③分母带面标可复算 **红** |

**一句话**：9.0.40 把「版本值」拉齐了（六处一致，含 Setup/win-unpacked FileVersion），但 **R6 仍未过**——定义点不唯一（手写字面＋装根旧）、分母未归一。⇒ 红 → 黄，距绿还差 3 件（§四 G1–G3）。

## 一 版本六处逐项值（本刻实测）

| # | 处 | 值 | 证据（径 / 字段） | bytes | sha16 |
|---|---|---|---:|---|---:|
| 1 | 代码唯一真源 | **9.0.40** | `core/lib/version.py` 之 `__version__` | 1,293 | `d46143f57bbb915f` |
| 2 | 构建 | **9.0.40** | `pyproject.toml` 之 `version` | 2,389 | `83bb5c523ee195e2` |
| 3 | 平台注册字面 | **9.0.40** | `core/lib/platform_client.py:55` 之 `"version": "9.0.40"` | 4,406 | `dca8d67780a0fcb7` |
| 4 | 壳 | **9.0.40** | `shell/package.json` 之 `version` | 1,462 | `92f39f6fa9218850` |
| 5 | **payload 装根元数据** | **9.0.40**（built_at 2026-10-30T08:19:27+0800 · commit `bcb48a1a` · tree `901dab22`） | `dist/pa_shell/payload/version.json` | 197 | `6fe1b819474ca895` |
| 6a | **Setup FileVersion / ProductVersion** | **9.0.40 / 9.0.40** | `dist/pa_shell/setup/ClawsJoyPA-Setup-9.0.40-x64.exe`（806,868,232 B） | 806,868,232 | `a635373eaf4f7e77` |
| 6b | **win-unpacked FileVersion / ProductVersion** | **9.0.40 / 9.0.40.0** | `dist/pa_shell/setup/win-unpacked/ClawsJoyPA.exe`（246,253,832 B · mtime 08:23:12） | 246,253,832 | `fa8d1639509f04b5` |

> 判：**六处值一致 = 9.0.40**（ProductVersion `9.0.40.0` 为四段显示，同版）。构建日志 `dist/pa_shell/setup/build-9.0.40.log`（49,042 B ／ `7a2529ac85aedc71`）含 `building target=nsis file=…9.0.40-x64.exe` 与 `signing file=…9.0.40-x64.exe subject=CN=ClawsJoy Internal`，与本表互证。

## 二 装根 / 活端（本机 dev · 旧值并存，非 9.0.40 包）

| 处 | 值 | 取刻/据 | 性质 |
|---|---|---|---|
| 仓根 `version.json`（本机装根元数据） | **9.0.11**（commit `9e5def93` · built_at 2026-10-08T09:58:23+0800） | 197 B ／ `4b54ee930555bcca` | **旧安装残留**；与 9.0.40 包 payload 不一致 |
| 活端 `GET /health` 之 `build.version` | **9.0.11** | 2026-10-30T08:35 实测（旧进程） | 读的正是上面那份旧 `version.json` |
| 活端 `/health` 之 `update.current_version` | **9.0.11** | 同上 | 更新面被旧装根钉住 |
| 活端 `/health` 之顶层 `version` | **9.0.38** | 同上 | **进程启动时之代码版本**（旧进程，未重启到 9.0.40） |

⇒ 本机存在**三值并存**（9.0.40 包 ／ 9.0.11 装根 ／ 9.0.38 活进程）。这是 R6「两套真相」在 **dev 机**的残留，不等于 9.0.40 包有问题；**9.0.40 全新安装后的装根值未实测**（本件只读，不安装）。

## 三 14/14 vs 9/9 分母（来源 ＋ 现状）

**旧证**（2026-09-28，三份同结果）：`dsh/_verify/pa_verify_20260928_0520/0530/0545.json`（2,037/1,871/1,871 B ／ `32cdbf88375651d8`／`a9d025b2cb5cc938`／`9b049df04bb3f11d`）：
- 顶层 `pass=14 / total=14`；results id ＝ `C1,C2,C3,C4,C5,C6,C7,C10,C12,C13,C14,C8,C9,C11`；
- 其中 `C11` evidence 逐字：`GET /v9/pa/verify -> ok=True pass=9/9`。

**分母来源（已查明）**：
- **14** ＝ `dsh_pa_verify` CLI 汇总：**13 个本地检查**（C1–C10／C12–C14，C8／C9 在内）＋ **追加 1 条 C11**（探 `/v9/pa/verify` 活端）；
- **9** ＝ **活端** `/v9/pa/verify` 自报的 pass/total（活端只有 9 项）；
- ⇒ **两个分母不是同一集合**，且输出**无面标**说明「通过」指哪个面 ⇒ 同一次「全绿」对外部读者有二义。

**现状（本刻）**：
- 仓内 **无** `core/pa/verify.py`；**payload 内亦无**（`dist/pa_shell/payload/core/pa/verify.py` MISSING）；
- 活端 `GET /v9/pa/verify?skip_scan=1` ⇒ **HTTP 404**（verifier 面未暴露）；
- 最新旧证仍为 **2026-09-28**（此后无新证）。
⇒ 14/14 vs 9/9 **未修复且不可复算**；⛔ 不可把旧证当 9.0.40 的 R6 绿。

## 四 R6 判据 × 现状（RAG）

| 判据 | 目标 | 现状 | 判 |
|---|---|---|---|
| ① 版本值一致（六处） | 全部同一版本 | **6/6 = 9.0.40**（含 Setup/win-unpacked FileVersion） | **绿** |
| ② 同一事实定义点=1 | 无手写重复、装根=真源 | `platform_client.py:55` **手写** `"version": "9.0.40"`（第二定义点，下次改版必漂）；仓根 `version.json`＝9.0.11（旧装根）；活端另有 9.0.38 | **红** |
| ③ 每个数带面标 / 分母唯一可复算 | 一个分母＋面标 | 14/14 vs 9/9 无映射；验器源缺、活端 404、仅 09-28 旧证 | **红** |

**R6 综合＝黄**（1 绿 2 红；红→黄，因 ① 由旧态 9.0.11／9.0.38 改善为六处 9.0.40）。**复判为绿须 G1–G3 三件齐**；缺一件**不得**报绿。

### 剩余缺口（本件只列，不代裁）

| # | 缺口 | 由谁 |
|---|---|---|
| **G1** | `platform_client.py:55` 手写版本字面 ⇒ 应改为引用 `core.lib.version.__version__`（唯一的第二定义点） | 后端（CW 线） |
| **G2** | 装根 `version.json` 旧 9.0.11 ＋ 活端旧进程 9.0.38 ⇒ 需**干净安装 9.0.40 后读装根/health** 取证（本件不装） | PD／T46 出包门 |
| **G3** | 分母未归一：验器源入仓（或明示外部归属）＋输出**每个数带面标**（14 与 9 的映射写清）＋活端恢复 `/v9/pa/verify` | 后端＋PD/Lead 裁归属 |
| G4 | Setup 签名/时间戳/分发属 T46 域，**不混入 R6** | PD |

## 五 复跑（只读 · 本刻可跑）

```powershell
# ① 版本六处
Select-String -Path core\\lib\\version.py -Pattern '__version__'
Select-String -Path pyproject.toml -Pattern '^version'
Select-String -Path core\\lib\\platform_client.py -Pattern '\"version\": \"9\\.0\\.40\"'
(Get-Content shell\\package.json | Select-String '\"version\"')
Get-Content dist\\pa_shell\\payload\\version.json -Raw
(Get-Item dist\\pa_shell\\setup\\ClawsJoyPA-Setup-9.0.40-x64.exe).VersionInfo | Format-List FileVersion,ProductVersion
(Get-Item dist\\pa_shell\\setup\\win-unpacked\\ClawsJoyPA.exe).VersionInfo | Format-List FileVersion,ProductVersion
# ② 旧证分母（三份同结果）
Select-String -Path 'D:\\Obsidian\\ClawsJoy\\ClawsJoy\\dsh\\_verify\\pa_verify_20260928_0545.json' -Pattern 'pass|C11'
# ③ 活端分母面（期望 404）
try { (Invoke-WebRequest 'http://127.0.0.1:5102/v9/pa/verify?skip_scan=1' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 'HTTP 404/ERR' }
# ④ 本机装根/活端旧值
Get-Content version.json -Raw
(Invoke-WebRequest 'http://127.0.0.1:5102/health' -TimeoutSec 5 -UseBasicParsing).Content | Select-String '\"version\"'
```

**预期**：六处皆 9.0.40（Setup/win-unpacked FileVersion 同）；旧证 pass=14 且 C11 pass=9/9；活端 verify ⇒ 404；仓根 version.json ⇒ 9.0.11；health 含 9.0.11／9.0.38。

## 六 证据四件套 ＋ 边界

| 件 | 径 | bytes | sha16 |
|---|---|---|---:|
| 本件 | `docs/reports/pa_iter40/10_r6_recheck.md` | 见回执 | 生成后另报 |
| 代码真源 | `core/lib/version.py` | 1,293 | `d46143f57bbb915f` |
| 构建版本 | `pyproject.toml` | 2,389 | `83bb5c523ee195e2` |
| 平台字面 | `core/lib/platform_client.py` | 4,406 | `dca8d67780a0fcb7` |
| 壳版本 | `shell/package.json` | 1,462 | `92f39f6fa9218850` |
| payload 装根元数据 | `dist/pa_shell/payload/version.json` | 197 | `6fe1b819474ca895` |
| Setup 9.0.40 | `dist/pa_shell/setup/ClawsJoyPA-Setup-9.0.40-x64.exe` | 806,868,232 | `a635373eaf4f7e77` |
| win-unpacked exe | `dist/pa_shell/setup/win-unpacked/ClawsJoyPA.exe` | 246,253,832 | `fa8d1639509f04b5` |
| 构建日志 | `dist/pa_shell/setup/build-9.0.40.log` | 49,042 | `7a2529ac85aedc71` |
| 本机装根（旧） | `version.json` | 197 | `4b54ee930555bcca` |
| 旧证 0545 | 外 `D:/Obsidian/ClawsJoy/ClawsJoy/dsh/_verify/pa_verify_20260928_0545.json` | 1,871 | `9b049df04bb3f11d` |
| 旧证 0530 | 外 `同目录/pa_verify_20260928_0530.json` | 1,871 | `a9d025b2cb5cc938` |
| 旧证 0520 | 外 `同目录/pa_verify_20260928_0520.json` | 2,037 | `32cdbf88375651d8` |

**边界（照实）**
1. **只读**：未改产品码/索引/配置；未安装 9.0.40 Setup；未重启活端。
2. **不编造绿**：六处版本值虽一致，但 R6 因「定义点≠1 ＋ 分母未归一」判 **黄**；9.0.40 安装后的装根值 **未实测**，只报「未实测」。
3. **分母不可复算**：本仓/payload 均无 `verify.py`、活端 404；14/14 与 9/9 仅来自 2026-09-28 旧证，⛔ 当 9.0.40 绿证。
4. **不替 PM 终判**：G1–G4 为缺口与建议，整改归属/优先级由 Lead/PM 裁。

（完 —— 本件末行 · LF 终 · 悬）
