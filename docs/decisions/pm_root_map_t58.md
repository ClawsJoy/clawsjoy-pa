# PA 迭代40 · T58 ④ root 绝对映射 ＋ 652 全域盘点（pm_root_map_t58）

> 代发: DSH（PA）｜席：PM（pm-dev）｜WIP=1（本单）｜写域：仅本件（`docs/decisions/pm_root_map_t58.md`）｜取刻：2026-10-30T08:12:24+08:00
> 依据：`docs/decisions/README.md`（`f2d13bbfed8b89f9`）· `pm_index_v0.csv`（`3d39ba535b2392fe`）· `pm_index_v1.csv`（`ced5dd5439317998`）· `pm_index_v1_missing_triage.csv`（`f92c2404b2c0186a`）· `03_index.md`（`c34c5c2aca44f6b1`）· 外部分工表 `_分工表_PM-3403_四事_C30_v1.md`（`2b5567a777754af8`）
> 纪律：**只出映射/盘点/处置**，⛔ 编造补档、⛔ 改 `pm_index_v0/v1`；未验证的一律标「未验」；**652 不冒用**（见 §三）。

## 〇 一页（先判）

| 项 | 结论 | 依据 |
|---|---|---|
| **root 绝对映射** | **定了**：`_pm` ⇒ `D:/paseo-workspace/_pm`；`codex` ⇒ `D:/Obsidian/ClawsJoy/ClawsJoy/codex`。**v0 68/68 可验；v1 205/205 可验；repo 内 0/68（v0）、0/205（v1）** | §一／§二 |
| **652 有据？** | **不可复算**：口径（树＋命令＋正则）未存；本仓 9 种可复算口径皆非 652（最接近 **596**，差 56）⇒ **不沿用 652**，改用可复算全域基 **U=450**（13 目录全语言代码） | §三 |
| **未覆盖处置** | v0 覆盖 **95/450**（21.1%），未覆盖 **355** ＝ 有 PM 件候选 **343** ＋ 仅他席件 **11** ＋ 无件 **1**；v1 覆盖 **286/450**（63.6%），未覆盖 **164** ＝ 157／6／1 | §四／§五 |
| **是否改 v0/v1** | **否**（一字未改）；映射与扩表建议交 PD 落库 | 边界 |

## 一 root 绝对映射表（已验 · 可复算）

| 索引 root | 绝对根（本机） | v0 行 | v0 可验（bytes+sha16） | v1 行 | v1 可验 | repo 内（同 root 相对径） |
|---|---|---:|---:|---:|---:|---:|
| `_pm` | `D:/paseo-workspace/_pm` | 67 | **67/67** | 195 | **195/195** | **0/67** |
| `codex` | `D:/Obsidian/ClawsJoy/ClawsJoy/codex` | 1 | **1/1** | 10 | **10/10** | **0/1** |
| **合计** | — | **68** | **68/68** | **205** | **205/205** | **0/68** |

- **v0**：96 数据行（68 resolved ＋ 28 missing）；resolved 68 行**全部**在上述绝对根按 `root/rel_path` 命中且 bytes+sha16 一致；repo 内 `D:/clawsjoy_v9/_pm`、`D:/clawsjoy_v9/codex` 命中 **0**。
- **v1**：287 数据行（205 有 root ＋ 82 空）；205 行**全部**在绝对根命中且 bytes+sha16 一致；repo 内 **0/205**。
- 另：v0 的 68 条中 **28 条**在 `信通` 有同字节同 sha16 副本（T45 已验）；该副本不是索引 root，仅作交叉佐证。

### 1.1 根族（映射表 · 建议落成的 JSON）

```json
{
  "roots": {
    "_pm":   {"abs": "D:/paseo-workspace/_pm", "role": "索引主根", "verified": {"v0": "67/67", "v1": "195/195"}},
    "codex": {"abs": "D:/Obsidian/ClawsJoy/ClawsJoy/codex", "role": "索引主根", "verified": {"v0": "1/1", "v1": "10/10"}},
    "_auto": {"abs": "D:/paseo-workspace/_auto", "role": "补录根（deliver/send；T45 补录源件在此）"},
    "信通":   {"abs": "D:/Obsidian/ClawsJoy/ClawsJoy/内容工坊/02_协作/信通", "role": "补录根（跨收件人流水；同号多件风险）"}
  },
  "repo_relative": {"_pm": "0/67", "codex": "0/1"},
  "resolve": "abs_root + rel_path（Windows 大小写不敏感）",
  "override": "环境变量 PM_DOC_ROOTS（label=path，os.pathsep 分隔）"
}
```

> **根口径一句话**：index 的 `root` 是**逻辑标签**，不是 repo 内目录；必须经本表映射到绝对根，否则 clone 后 0 条可查证（与 v0 README「clone 后无从查证」之病同源）。
> **备选（仍建议先定主根）**：把 `_auto`／`信通` 收为「补录根族」——T45 的 25 条补录用例即落在 `_auto/deliver|send`、`_pm`、`信通` 三处。

## 二 复算（根映射 · 一条命令）

件内脚本（建议另存为 `tools/check_pm_roots.py`，**未建**；只读）：

```python
import csv, hashlib
from pathlib import Path
REPO = Path(r"D:/clawsjoy_v9")
ROOTS = {"_pm": [r"D:/paseo-workspace/_pm"], "codex": [r"D:/Obsidian/ClawsJoy/ClawsJoy/codex"]}
def sha16(b): return hashlib.sha256(b).hexdigest()[:16]
def rows(p):
    t = Path(p).read_text(encoding="utf-8-sig")
    return [r for r in csv.reader([l for l in t.split("\n") if l.strip()][1:]) if r]
def verify(rows_):
    ok = ext = 0
    for r in rows_:
        if len(r) < 5 or not r[1] or not r[2]: continue
        p = REPO / r[1] / r[2]
        if p.is_file() and str(p.stat().st_size) == r[3] and sha16(p.read_bytes()) == r[4]: ok += 1
        for base in ROOTS.get(r[1], []):
            q = Path(base) / r[2]
            if q.is_file() and str(q.stat().st_size) == r[3] and sha16(q.read_bytes()) == r[4]: ext += 1; break
    return ok, ext
for name in ("pm_index_v0.csv", "pm_index_v1.csv"):
    rs = rows(REPO / "docs/decisions" / name)
    print(name, "rows", len(rs), "repo_ok/ext_ok", verify(rs))
```

预期（本机实测）：`pm_index_v0.csv rows 96 repo_ok/ext_ok (0, 68)`；`pm_index_v1.csv rows 287 repo_ok/ext_ok (0, 205)`。

## 三 652 有据？—— **不可复算，本件不沿用**

### 3.1 出处（可核）

| 处 | 原话（逐字） | 件 |
|---|---|---|
| v0 README §三 | 「代码内唯一 id（`core/pa/*.py`） **96**；全仓 `*.py` 的 id 数为 **652**（CEO 实测）」 | `docs/decisions/README.md`（`f2d13bbfed8b89f9`） |
| PM 分工表 ④ | 「全仓 `652` id 扩表（`csv`）… `652` 覆盖表 行 ＝ id 数；每 行 径 ＋ 行 号」 | `_分工表_PM-3403_四事_C30_v1.md`（`2b5567a777754af8`） |

⇒ 652 是**任务目标数**，但**原树／命令／正则三者皆未留存**；本仓复算如下。

### 3.2 复算矩阵（本仓 · 同一正则 `(?:PM|pm)[ _-]?(\d{3,4})\b`，除注明）

| # | 口径（scope ＋ 扩展名） | 唯一 id | 说明 |
|---|---|---:|---|
| S1 | `core/pa/*.py`（v0 自述域） | **91** | 旧 96 vs 今 91：7 条迁出 core/pa、3 条新增（3406/3407/3433）、2026 为日期假号（T45 已证；96−7＋3−1＝91） |
| S2 | 13 代码目录 `*.py` | **345** | core/web/shell/scripts/tests/agents/api/routes/engine/clawsky/src/tools/config |
| S3 | 仓内 `*.py`（除 `data/`、`dist/`；含 `_pm`、`_tmp`） | **440** | 加入仓内脚本后 |
| S4 | 13 目录**全语言**（py/js/ts/vue/sh/ps1…） | **450** | **本件采用的全域基 U**（与 T45 同口径） |
| S5 | 全仓文本（除 `data/`、`dist/`；含 `.before_*` 备份；md/txt/py/js/json/csv…） | **580** | 备份件把旧 id 也计入 |
| S6 | S5 ∪ `data/` 文本 | **588** | data 新增 252 id（多为低位数假号） |
| S7 | 同 S5，正则放宽为 `\d{1,4}` | **596** | **最接近 652**，仍差 **56** |
| S8 | `*.py` ＋ `data/*.py` | **443** | 排除 data 文本后 |
| S9 | `dist/pa_shell/payload*` 34 个快照之 code 面 | **167** | 旧载荷，集合为子集；未并入 |

**判定（照实）**：上述 9 种口径**无一等于 652**；最接近 596（差 56），其次 588（差 64）。
⇒ **652 不具备可复算性**（原口径未存，且本仓树已漂）⇒ **本件不把 652 当验收数、不回落 652、不造 652 覆盖表**。
⇒ 建议：若老板/CEO 仍以 652 为验收数，**须补「树＋命令＋正则」三件**（D1，候裁）；否则本件以 **U=450** 作为「全域」口径（可复算、与 T45 同源）。

## 四 全域覆盖对账（以 U=450 为基）

| 对账 | 覆盖 | 未覆盖 | 覆盖率 | 未覆盖构成 |
|---|---:|---:|---:|---|
| **U ∩ v0** | **95 / 450** | **355** | 21.1% | PM 件候选 **343** ＋ 他席件 **11** ＋ 无件 **1** |
| **U ∩ v1** | **286 / 450** | **164** | 63.6% | PM 件候选 **157** ＋ 他席件 **6** ＋ 无件 **1** |

- v0 的 96 条中 **2026** 不在 U（日期假号，T45 已判废）；v1 的 287 条亦含 2026 同类 1 条 ⇒ 故 95、286 而非 96、287。
- 「PM 件候选」＝ 文档域存在 `序号＝id 且 from＝项目经理` 的件（T45 同法，catalog 3,081 ids）；**候选≠已验**（同号跨账、未逐条比题旨/未验 sha），⛔ 直接入册。

### 4.1 未覆盖清单（355 ＝ 343＋11＋1）

| 桶 | 数 | id 清单（完整） | 处置 |
|---|---:|---|---|
| **PM 件候选** | **343** | 略（扩表建议字段：`id, root, rel, bytes, sha16, ref_count, first_line_no, category, disposition`） | **候补录**：逐条核题旨＋验 sha16＋核同号跨账；未验前 ⛔ 入册 |
| **仅他席件** | **11** | 1106 1132 1491 1588 1629 1631 1688 1745 1796 1805 2101 | **移-归属/候判**（同号件属他席；索引不宜收为 pm 源件） |
| **无件** | **1** | 1797 | **缺/候判**（挂缺口，⛔ 编档） |

> 对 v1 未覆盖 164：PM 件候选 157（同候补录）＋ 他席件 6（1491 1588 1688 1745 1805 2101）＋ 无件 1（1797）。

## 五 落地建议 ＋ 待裁

| # | 事项 | 建议（不裁） | 谁裁 |
|---|---|---|---|
| R1 | root 映射落库 | 索引增 `root_abs`（本表 JSON）或读 `PM_DOC_ROOTS`；**不写 repo 相对径** | PD 落库／Lead |
| R2 | 652 口径 | 若沿用 ⇒ 补树/命令/正则（D1）；否则验收用 U=450 | PM/CEO/Lead |
| R3 | 覆盖表字段 | `id, root, rel, bytes, sha16, ref_count, first_line_no, category, disposition`（一处本：只存指针） | PM 编 · PD 落 |
| R4 | 扩表范围 | 先 343 候补录（逐条验），暂不碰 11 他席/1 无件 | PM · 下一迭代 |
| D1 | 652 定义补全 | 树＋命令＋正则三件；缺一即不认 652 | 老板/CEO |
| D2 | 根族边界 | `_auto`／`信通` 是否入 root 族（T45 补录已用） | PM/Lead |
| D3 | 是否改 v0/v1 | **本件不改**；改色/扩表须新件（承 T45 一处本） | Lead/PD |

## 六 证据四件套 ＋ 边界

| 件 | 径 | bytes | sha16 |
|---|---|---|---:|
| 本件 | `docs/decisions/pm_root_map_t58.md` | 见回执 | 生成后另报 |
| v0 索引 | `docs/decisions/pm_index_v0.csv` | 7,934 | `3d39ba535b2392fe` |
| v1 索引 | `docs/decisions/pm_index_v1.csv` | 25,056 | `ced5dd5439317998` |
| v1 triage | `docs/decisions/pm_index_v1_missing_triage.csv` | 21,388 | `f92c2404b2c0186a` |
| 索引 README（652 出处） | `docs/decisions/README.md` | 2,274 | `f2d13bbfed8b89f9` |
| T45 分类件 | `docs/reports/pa_iter40/03_index.md` | 17,098 | `c34c5c2aca44f6b1` |
| T45 审计脚本 | `docs/decisions/pm_index_t45_audit.py` | 18,909 | `56c9af7c640860db` |
| 分工表（652 目标） | 外 `D:/paseo-workspace/_pm/_分工表_PM-3403_四事_C30_v1.md` | 4,790 | `2b5567a777754af8` |

**复跑**
```powershell
# ① 根映射：把 §二 脚本存为 tools/check_pm_roots.py（未建）后跑；期望 v0 (0,68) · v1 (0,205)
# ② 全域 U=450 与覆盖计数（复用 T45 脚本，只读）
python -X utf8 -B docs/decisions/pm_index_t45_audit.py --check
#   期望：[code] 全域 ids 450 · v0 未覆盖 355 · 其中有 PM 件候选 343
# ③ 652 矩阵（S1–S9）为临时只读扫描（未入仓）；口径逐条见 §三 表；S4 可直接用 ② 复算
```

**边界（照实）**
1. **未改** `pm_index_v0.csv`／`v1`／`triage` 一字；未改产品码；只写本件。
2. **未编造补档**：343 仅为**候选**（序号码），⛔ 未验题旨/未验 sha/未入册；1797 挂缺口不补。
3. **652 不冒用**：本件明确「不可复算、不回落」；如需 652 请补口径（D1）。
4. **根在 repo 外**（本机绝对径）：换机无根 ⇒ 对应格记「不可验」，⛔ 臆断为缺档；建议落 `PM_DOC_ROOTS`。
5. **未覆盖口径只到 U=450**：S5/S6/S7（文本/备份/data）为**证伪 652** 用，不作验收基；如要扩到文本域须另立口径（R4/D1）。

（完 —— 本件末行 · LF 终 · 悬）
