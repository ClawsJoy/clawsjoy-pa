# PA 迭代40 · T106 G3 PD 裁：C7/C10 API 等价与 legacy_verify 适配

> 代发: DSH（PA）｜执行席: pd-dev（PD）｜WIP=1｜写域: `docs/reports/pa_iter40/32_g3_pd_decisions.md`（本件唯一写入）
> 取刻: 2026-10-30T14:44:45～14:46:00+08:00｜**判裁＋设计，不实现**：⛔ 建端 ／ ⛔ 改产品码 ／ ⛔ 改旧库
> 上位: D-11（最小复制 `legacy_verify/`；14/14 暂缓）｜T77（源定位 f9ba…／ad29…／5b73…／9b049…）｜T102（C7/C10 旧 API 缺）

## 〇 结论（先判）

| API | 旧（v5 · 2026-09-28） | 现役（v9.0.42） | 等价？ | PD 裁 |
|---|---|---|---|---|
| C7 谓词 | `_scan_excluded(rel)`：**唯顶层段**、**静态**集 `{.obsidian,Templates,_垃圾箱,_冷区}`、先把反斜杠归一为 `/` | `_rel_excluded(rel, skip)`：**任一段**命中、`skip` 来自配置 `obsidian.exclude_dirs`（缺省同四名）、不归一反斜杠 | **否**（顶层 vs 任一、静态 vs 配置、1 vs 2 参） | **须适配**（复刻顶层/静态；⛔ 直接用现役谓词） |
| C10 遍历留痕 | `last_walk_errors()`：上次容错 scandir 的 `dir :: err` 列表 | **无对应**；现役 `_walk_warn(err)` 只 **print**，`os.walk(onerror=)` 不保已读条目，无 `_LAST_WALK_ERRORS` | **否**（无 API；行为亦不同） | **blocked**（C10 不得假绿） |
| C12/C13/C14 | 依赖旧 `_walk_md` 容错 ＋ `data/v9/vault_manifest_win.txt` 补面 | 现役 `_scan_vault` 无容错留痕、无 manifest 补面、无 mtime 缓存 | **输出形似、行为不等** | **legacy 面/blocked**（⛔ 以现役 scan 冒充旧面） |
| C6 | `PI._vault_path()` ＋ `_obsidian_cfg()["sops_dir"]` | 同名 `_obsidian_cfg`（同件同键）；`_vault_path()` 走 `vault_root()`，未接返 **空串** | API 可适配 | **适配**（空根显形，⛔ `Path("")`→CWD） |
| C9（及 C3/C4） | `BASE` 默认 **5002**（硬编） | 真实端口 **5102**（配置真源；活端 /health 200；5002 关闭） | 值不等，须解析 | **适配**（env ＞ 配置真源；⛔ 5002 字面） |

**一句话**：C7 可做最小适配（不碰产品）；C10 当前不可等价（blocked/面标，不得 pass）；C6/C9 有明确适配点（C9 BASE=5102）；C12–C14 属 legacy 面，不得借现役 scan 冒充。

## 一 一手证据（径＋sha16＋取刻）

| # | 对象 | 径 | 大小／mtime | sha16 | 取刻 |
|---|---|---|---|---|---|
| E1 | 旧 v5 扫描模块 | WSL `/home/flybo/clawsjoy_v5/core/gateway/precision_inject.py` | 60,693 B／2026-09-28 05:39:24 | **266337973917d5fd** | 14:44:45 |
| E2 | 旧验器（legacy 复制件） | `legacy_verify/core/pa/verify.py`（源 f9ba…） | 9,675 B／2026-09-28 04:54:52 | **f9ba9bede5620350** | 14:45:17 |
| E3 | 现役扫描模块 | `core/gateway/precision_inject.py` | 62,294 B／2026-10-06 20:17:24 | **54f24605e473a950** | 14:45:17 |
| E4 | 旧清单（legacy 复制） | `legacy_verify/data/v9/vault_manifest_win.txt`／`…vault_missing_win.txt` | 722,197／1,436 B | **98cf4c34a491b574**／**d396aefaf6b7fc51** | 14:45:17 |
| E5 | 旧证 0545（legacy 复制） | `legacy_verify/dsh/_verify/pa_verify_20260928_0545.json` | 1,871 B／2026-09-28 06:01:42 | **9b049df04bb3f11d** | 14:45:17 |
| E6 | 活端/端口 | `127.0.0.1:5102/health` **200**；`127.0.0.1:5002` **关闭** | — | — | 14:45:17 |
| E7 | 行锚 | 旧：`_scan_excluded` L77-83；`_walk_md` L162；`last_walk_errors` L206-208；`_scan_vault` L211；旧验器 C7 L130-148／C10 L149-153／C6 L118-124／C9 L202-226。现役：`_vault_path` L43／`_exclude_dirs` L96／`_walk_warn` L106／`_rel_excluded` L127／`_scan_vault` L132／`_obsidian_cfg` L571 | — | — | 14:45 |

## 二 C7：逐语义对照（须适配）

| 语义点 | 旧 `_scan_excluded` | 现役 `_rel_excluded` | 判 |
|---|---|---|---|
| 匹配范围 | **唯顶层目录**（`split("/",1)[0]`） | **任一段**（`any(seg in skip)`） | **不等**：嵌套同名会被现役多排 |
| 排除集来源 | **静态常量** `_SCAN_SKIP_TOP` | 配置 `obsidian.exclude_dirs`（缺省同四项） | **不等**：配置一改即漂 |
| 分隔符 | 先 `replace(chr(92), "/")` 归一 | 只按 `/` 切；反斜杠不归一 | **不等**：Windows 形路径旧判 top、现役判整串 |
| 形参 | 1（rel） | 2（rel, skip） | **不等**（调用点必改） |

**反例（一手实测 · 14:45:46；现役 skip=set(_exclude_dirs())）**：

```
CASE='_冷区/x.md'            old=True  cur=True
CASE='_垃圾箱/P/d.md'         old=True  cur=True
CASE='.obsidian/x.md'        old=True  cur=True
CASE='Templates/t.md'        old=True  cur=True
CASE='工作区/SOPs/SOPs/a.md'  old=False cur=False
CASE='dsh/a.md'              old=False cur=False
CASE='工作区/_冷区/x.md'      old=**False** cur=**True**   ← 现役多排（任一 vs 顶层）
```

加推：`Templates\t.md`（反斜杠形）旧经归一 top=`Templates` ⇒ True；现役整串无 `/` ⇒ False。二者皆需 legacy 适配。

## 三 C10／C12–C14：无等价 API（不得假绿）

| 旧 | 现役 | 缺口 |
|---|---|---|
| `_LAST_WALK_ERRORS` 列表；`_walk_md` 容错 `scandir`：出错前条目**保留**、错误入册，且 Windows 清单**逐路径补面** | `_walk_vault_md`：`os.walk(onerror=_walk_warn)`；`_walk_warn` **仅 print**；无错误列表、无清单补面；读件异常吞掉 | ①无 `last_walk_errors`（`hasattr=False` 实测）；②抛错时整棵子树丢（≠旧「保留已读」）；③旧 C13/C14 依赖的清单补面现役无 |
| C10（full）：`errs is not None` → 记录 | 无 errs；`skip_scan=True` 时旧 C10 走 `bool(skip_scan)` ⇒ **「未验」即 pass** | **9/9 面含 C10「未验 pass」** ⇒ 不能拿 9/9 当 C10 绿；14/14 必 blocked |
| C13/C14：旧 `_walk_md` 用 `vault_manifest_win.txt` 补面后比缺项/ENAMETOOLONG | 现役 scan 无 manifest 补面（`legacy_verify/` 件亦未被产品读取） | 面/数据源不同；**legacy 面，⛔ 冒充现役** |

**PD 裁**：C10 在现役 API 下 **blocked**；若要观测，可另加 adapter 捕获 `_walk_warn` 的「`current_walk_warn`」面，但**不得**计为旧 C10 pass；C12–C14 同（legacy face/blocked）。

## 四 legacy_verify 最小适配层（设计 · **本单不实现**）

**位置（未来）**：`legacy_verify/adapters/precision_inject_v9.py`（纯 Python，⛔ 产品 import 它；⛔ 改 `core/gateway/precision_inject.py`）。本层只供遗留验器/证据面调用。

```python
# 伪代码（最小适配；不实现于本单）
LEGACY_SKIP_TOP = (".obsidian", "Templates", "_垃圾箱", "_冷区")

def legacy_scan_excluded(rel):
    top = str(rel).replace(chr(92), "/").split("/", 1)[0]
    return top in LEGACY_SKIP_TOP

def legacy_walk_errors():
    # 现役无等价 API ⇒ 明确 blocked（不伪造空表）
    return {"state": "blocked", "face": "legacy_C10_unavailable",
            "reason": "current precision_inject lacks last_walk_errors(); os.walk(onerror) != v5 tolerant scandir"}

def vault_root_or_none():
    s = str(_pi._vault_path() or "").strip()
    return Path(s) if s and s != "." else None   # 旧 Path("")->CWD 之病，adapter 必显形

def sops_dir():
    return str((_pi._obsidian_cfg() or {}).get("sops_dir") or "SOPs")

def scan_notes():
    return _pi._scan_vault()   # 形似；C12–C14 仅可作现役 scan 面，⛔ 旧面

def base_url():
    env = (os.environ.get("PA_VERIFY_BASE") or "").strip()
    if env:
        return env.rstrip("/")
    from core.lib.port_config import gateway_base_url   # 真源 5102
    return gateway_base_url()
```

**C6 适配点**：`_obsidian_cfg()` 同件同键（`sops_dir`）；空 `_vault_path()` ⇒ C6 **FAIL 显因**（⛔ 落 CWD 扫/立）；根用现役 `_vault_path()`，⛔ 旧 WSL 绝对径。
**C9 适配点**：① `BASE` ⇒ `base_url()`（env `PA_VERIFY_BASE` ＞ `port_config.gateway_base_url()` ⇒ **5102**；⛔ 5002 字面）；② 进程起点 `psutil` 同旧；③ 新鲜源表用现役 `core/pa/roster.py`／`core/gateway/precision_inject.py`／`config/v9/execution_policy.yaml`；④ `/health` 200 为活端唯一据（5002 关闭，不得回退）。
**C3/C4**：同 `base_url()`。

**适配反例（未来测试断言）**：

| # | 输入/态 | 旧 | 现役直用 | adapter 期望 |
|---|---|---|---|---|
| A1 | `工作区/_冷区/x.md` | False | **True** | False（顶层语义） |
| A2 | `Templates\t.md` | True | **False** | True（归一后 top） |
| A3 | 配置 `exclude_dirs=["X"]` ＋ `X/a.md` | False（静态） | **True**（配置） | False（legacy 静态） |
| A4 | `last_walk_errors` | list | **不存在** | `{"state":"blocked"}`（⛔ 空表假绿） |
| A5 | 空 vault（`_vault_path()=""`） | `Path("")`→CWD（旧病） | `_scan_vault()→[]+显形` | C6 FAIL 显因，⛔ 扫 CWD |
| A6 | `BASE` | 5002 | 5102 | adapter=5102（env 可覆） |

## 五 判据汇总（给后续实现）

1. **C7**：adapter 必须复刻「顶层＋静态＋归一」；以 A1–A3 三反例钉；⛔ 用现役 `_rel_excluded` 原样（多排嵌套）。
2. **C10**：标 **blocked**（A4）；9/9 面之 C10 是 `skip_scan`「未验 pass」，**面标**须写 `C10:未验`；14/14 不得据此判绿。
3. **C12–C14**：legacy face／blocked（C13/C14 需旧清单补面；现役 scan 不等价）；最多作为现役 scan 面单列。
4. **C6**：`vault_root_or_none` ＋ `_obsidian_cfg` 同键；空根 FAIL 显因。
5. **C9**：`BASE=5102`（env>真源）；⛔ 5002；`/health` 200 与进程起点同验。
6. **不触产品**：适配只落 `legacy_verify/adapters/`；⛔ 改 `core/`、⛔ 建 `/v9/pa/verify`（另单，T77 方案）。

## 六 复跑（径＋sha16＋取刻）

```powershell
Set-Location D:\clawsjoy_v9
# R1 旧/新扫描模块 sha16
wsl -d Ubuntu -- sha256sum /home/flybo/clawsjoy_v5/core/gateway/precision_inject.py
Get-FileHash core/gateway/precision_inject.py -Algorithm SHA256
# R2 legacy 验器/清单/证据
Get-ChildItem legacy_verify -Recurse -File | ForEach-Object { $h=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower().Substring(0,16); '{0}|{1}|{2}' -f $_.FullName.Replace((Get-Location).Path+'\',''),$_.Length,$h }
# R3 C7 语义探针（需 PYTHONPATH=仓根）
$env:PYTHONPATH='D:\clawsjoy_v9'
python -X utf8 -B -c "from core.gateway import precision_inject as PI; skip=set(PI._exclude_dirs()); L={'.obsidian','Templates','_垃圾箱','_冷区'}; top=lambda r:str(r).replace(chr(92),'/').split('/',1)[0]; print([(c,top(c) in L,PI._rel_excluded(c,skip)) for c in ['_冷区/x.md','工作区/_冷区/x.md']]); print('last_walk_errors',hasattr(PI,'last_walk_errors'))"
# R4 端口/活端
try { (Invoke-WebRequest 'http://127.0.0.1:5102/health' -UseBasicParsing -TimeoutSec 3).StatusCode } catch { $_.Exception.Message }
try { (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1',5002); '5002_OPEN' } catch { '5002_CLOSED' }
# R5 行锚
Select-String -Path core/gateway/precision_inject.py -Pattern 'def _vault_path|def _rel_excluded|def _scan_vault|def _walk_warn|def _obsidian_cfg'
```

## 七 界

- 本单仅裁/设计，未实现 adapter、未建端、未改产品码/旧库；legacy_verify 原样（D-11）。
- 14/14 仍按 D-11 暂缓；C10 在等价实现前 **永不得 pass**；9/9 面须显式面标（C10/C13 在 skip_scan 为「未验」）。
- C6/C9 适配属 legacy 验器复跑范围，不改变产品行为；`BASE` 以现役真源 5102 为准。

（本件完 · T106 PD 裁 C7/C10 API 等价）
