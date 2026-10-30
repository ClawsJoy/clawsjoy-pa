# PA 迭代40 · T60 ④ 343 PM 候补录核验（09_pm_candidates）

> 代发: DSH（PA）｜席：PM（pm-dev）｜WIP=1（本单）｜写域：仅 `docs/decisions/pm_candidates_t60.csv` ＋ 本件
> 取刻：2026-10-30T08:26+08:00（实跑段 08:18–08:26）
> 输入：T58 `pm_root_map_t58.md` 之「U=450，未覆盖 355 ＝ PM 件候选 343 ＋ 他席 11 ＋ 无件 1」；本件**只核 343**（他席 11／无件 1 不在本件范围）
> 纪律：⛔ 编造补档、⛔ 改 `pm_index_v0/v1`、⛔ 替 PM 终判。本件结论一律为**机检建议**，入册与否由 PM/Lead 定。

## 〇 一页（先判）

| 项 | 数 | 说明 |
|---|---:|---|
| 核验对象 | **343** | T58 的「PM 件候选」全集（每个 id 一条） |
| 绝对根命中 | **343/343** | 候选件全部在本机绝对根可读（`_pm` 259 条 ／ `_auto` 84 条） |
| bytes+sha16 一致 | **343/343** | 逐件**重读盘**复核，0 条不符（`cand_sha_ok=yes`） |
| 题旨命中（exact/base/heading/quote） | **309** | exact 63 ／ base 213 ／ heading 24 ／ quote 9 |
| 题旨不合（有 token、件中无） | **8** | 存疑-题旨不合待判 |
| 题旨不可判（代码上下文无 §／引文 token） | **26** | 存疑-题旨不可判 |
| 同号多件（同一 id 多份 PM 件） | **266** | 其中 **333/343** 为**单源多副本**（同 sha16，多根各存一份） |
| **真跨账歧义（>1 个不同 sha16）** | **10** | 11／46／53／76／77／78／86／1040／1041／1042（见 §三） |
| **机检建议** | **303** | 301 直接建议 ＋ 2 条「题旨已定向但同号另有异件」 |
| **存疑（不入册，候判）** | **40** | 同号多件皆合 6 ＋ 题旨不合 8 ＋ 题旨不可判 26 |

**一句话**：343 条**指针层全过**（根/字节/sha16），题旨层 **309 命中、8 不合、26 不可判**；真跨账歧义只有 **10 个 id**。⇒ 303 条可作**候补录建议**，40 条**存疑候 PM 判**——⛔ 本件不入册、不补档、不改 v0/v1。

## 一 口径（逐条核什么）

1. **指针核（硬）**：候选件在**绝对根**可读，且盘上 `bytes`＝记录值 ∧ `sha256[:16]`＝记录值；任一不符 ⇒ 该条判不合。
2. **题旨核（软 · 分档）**：取代码首引上下文（径:行号 ＋ 原文），抽 token：
   - `§X.Y` 精确命中 ⇒ `exact`；`§X` 基号命中 ⇒ `base`；
   - 文档标题 `## X` 命中 ⇒ `heading`（弱）；
   - 引号/反引号短词命中 ⇒ `quote`；
   - 有 token 但全不中 ⇒ `不合`；无 token ⇒ `不可判`（**不硬判不合**）。
3. **同号跨账核**：同一 id 的 PM 件数、**不同 sha16 数**、所在根；**同 sha＝同件多副本**（不算歧义），**多 sha＝真跨账**（须判谁是源）。
4. **选件规则**：优先「题旨命中档位最高」者；同档按根优先 `_pm > _auto > 信通 > codex > paseo-pm`（§二 CSV `cand_root` 即所选）。
5. **字段**（CSV 20 列）：`id, ref_core_pa, ref_wide, first_ref, cand_root, cand_rel, cand_bytes, cand_sha16, cand_sha_ok, cand_from, cand_date, cand_type, pm_docs, unique_sha, roots, match_level, match_tokens, cross_verdict, verdict`。

## 二 结果（按 verdict 分桶 · 逐条处置）

| verdict | 数 | 处置（本件只建议） |
|---|---:|---|
| **候补录-建议** | **301** | 可进「候补录」复核清单；入册前仍须 PM 抽验题旨 |
| 候补录-建议（题旨base；同号另有 2 件不同 sha16） | **1**（id 53） | 题旨定向这条，但**同号另有异件**⇒ 入册前须先定源 |
| 候补录-建议（题旨exact；同号另有 1 件不同 sha16） | **1**（id 1042） | 同上（异件 1） |
| **存疑-同号多件皆合待判** | **6** | 46／76／77／78／1040／1041：同号多件**皆题旨合**⇒ 须 PM 判谁是源（⛔ 本件不裁） |
| **存疑-题旨不合待判** | **8** | 1071／1297／1581／1617／1698／1862／2074／2091：所选件与代码上下文题旨不合 ⇒ 要么另有源、要么代码引用泛指 ⇒ 候判 |
| **存疑-题旨不可判** | **26** | 11／86／994／1000／1001／1013／1220／1548／1577／1578／1598／1607／1652／1779／1792／1798／1810／1886／1890／1897／1936／2729／2740／2750／2758／3413：代码上下文无 §／引文 token（多为泛指「承 pm_XXXX」）⇒ 无法机判题旨，候 PM 人工抽验 |

> **合计 343**。所有 343 条的**绝对根/bytes/sha16 全过**（CSV `cand_sha_ok` 全 `yes`）；上表只分「题旨/跨账」两维。

## 三 真跨账歧义（10 个 id · 同号多件不同 sha16）

| id | 不同 sha16 数 | 所在根 | 机检建议 |
|---|---:|---|---|
| 11 | 7 | `_auto`（事） | 题旨不可判 ＋ 7 件异文 ⇒ **候判**（最不确定） |
| 46 | 2 | `_auto` | 多件皆合 ⇒ 候判 |
| 53 | 3 | `_auto` | 题旨定向 1 件，另 2 件异文 ⇒ 候判（先定源） |
| 76 | 3 | `_auto` | 多件皆合 ⇒ 候判 |
| 77 | 3 | `_auto` | 多件皆合 ⇒ 候判 |
| 78 | 3 | `_auto` | 多件皆合 ⇒ 候判 |
| 86 | 3 | `_auto` | 题旨不可判 ＋ 3 件异文 ⇒ 候判 |
| 1040 | 2 | `_auto` | 多件皆合 ⇒ 候判 |
| 1041 | 2 | `_auto` | 多件皆合 ⇒ 候判 |
| 1042 | 2 | `_auto` | 题旨定向 1 件，另 1 件异文 ⇒ 候判 |

> 其余 333 条的「同号多件」皆为**同 sha16 多副本**（`_pm`／`_auto`／`信通` 各存一份）⇒ **不构成源歧义**，只需在落库时钉一个根（建议 `_pm` 或 `_auto`）。

## 四 抽检样本（8 条 · 可回看 CSV 行）

| id | 候选（根/径） | bytes | sha16 | 题旨档 | verdict |
|---|---|---:|---|---|---|
| 11 | `_auto/deliver/_to_td_011.md` | 4,540 | `1fb29bc7a0162044` | none | 存疑-题旨不可判 |
| 46 | `_auto/deliver/_to_td_046.md` | 8,230 | `fada13fd1044e5dc` | base | 存疑-同号多件皆合待判 |
| 53 | `_auto/deliver/_to_td_053.md` | 5,713 | `d454650718c56e89` | base | 建议（题旨定向；同号另有 2 件） |
| 76 | `_auto/deliver/_to_td_076.md` | 3,497 | `4f63c00363b7767f` | base | 存疑-同号多件皆合待判 |
| 77 | `_auto/deliver/_to_td_077.md` | 5,592 | `892a7cf9ccc4b42e` | base | 存疑-同号多件皆合待判 |
| 78 | `_auto/deliver/_to_td_078.md` | 4,732 | `af19838105d35434` | base | 存疑-同号多件皆合待判 |
| 86 | `_auto/deliver/_to_td_086.md` | 3,607 | `6da700860215a8d8` | none | 存疑-题旨不可判 |
| 973 | `_auto/send/pm_973_cw_M0_plugin_reuse_and_form_v2.md` | 10,289 | `bf7a64a1bb88d2e6` | heading | 候补录-建议 |

## 五 复算（算法 · 只读；生成脚本为临时件未入仓）

1. 取全域：`python docs/decisions/pm_index_t45_audit.py --check` ⇒ 全域 ids 450、v0 未覆盖 355、PM 候选 343（与 T58 同口径）。
2. 对 343 id 逐条：
   - 由 T45 `build_catalog` 取同号 PM 件（`序号==id ∧ from 含 项目经理`）；按根优选 + 题旨档优选出 1 件；
   - 盘上重读 `bytes` 与 `sha256[:16]` 比对；
   - 抽 §／引文 token 分档判题旨；统计 `unique_sha` 判跨账；
   - 落 20 列 CSV（本件 `pm_candidates_t60.csv`，343 行）。
3. CSV 自检：`rows=343 · cand_sha_ok=yes 343/343 · roots={_pm:259,_auto:84} · match_level={exact:63,base:213,heading:24,quote:9,none:34}`。

## 六 证据四件套 ＋ 边界

| 件 | 径 | bytes | sha16 |
|---|---|---|---:|
| **本件 CSV** | `docs/decisions/pm_candidates_t60.csv` | 140,022 | `9e259f98a79af66d` |
| 本件 MD | `docs/reports/pa_iter40/09_pm_candidates.md` | 见回执 | 生成后另报 |
| T58 全域盘点 | `docs/decisions/pm_root_map_t58.md` | 11,705 | `715718dd06c0de02` |
| T45 审计脚本 | `docs/decisions/pm_index_t45_audit.py` | 18,909 | `56c9af7c640860db` |
| T45 分类件 | `docs/reports/pa_iter40/03_index.md` | 17,098 | `c34c5c2aca44f6b1` |
| v0 索引 | `docs/decisions/pm_index_v0.csv` | 7,934 | `3d39ba535b2392fe` |
| v1 索引 | `docs/decisions/pm_index_v1.csv` | 25,056 | `ced5dd5439317998` |

**复跑**
```powershell
# ① 全域与候选数（只读）
python -X utf8 -B docs/decisions/pm_index_t45_audit.py --check
#   期望：全域 ids 450 · v0 未覆盖 355 · 有 PM 件候选 343
# ② 本件 CSV 自检（行数/判据/分桶；用 Import-Csv 防逗号字段误切）
$c = Import-Csv docs/decisions/pm_candidates_t60.csv
'rows=' + $c.Count
'sha_ok=' + ($c | Where-Object cand_sha_ok -eq 'yes').Count
$c | Group-Object verdict | Sort-Object Count -Descending | ForEach-Object { $_.Name + '=' + $_.Count }
# ③ 抽 1 条重验：sha256[:16] 与 CSV 记录比对（示例 id=11）
node -e "const fs=require('fs'),c=require('crypto');const b=fs.readFileSync('D:/paseo-workspace/_auto/deliver/_to_td_011.md');console.log(b.length,c.createHash('sha256').update(b).digest('hex').slice(0,16))"
```

**边界（照实）**
1. **未改** `pm_index_v0/v1` 与任何产品码；只写本件两文件。
2. **未编造补档**：CSV 只记**既有件**的 根/径/bytes/sha16；未新建任何 pm 文档、未入册。
3. **⛔ 替 PM 终判**：303 条是**机检建议**（题旨分档为启发式），40 条存疑**候 PM 判**；本件不裁「谁是源」「是否入册」。
4. **题旨判别力有限**：`heading` 为弱命中；`26` 条无 token 者标「不可判」而非「不合」；⛔ 用本件建议替代人工抽验。
5. **根/环境依赖**：`_pm`／`_auto` 为 repo 外绝对根；换机无根则 343 条全不可验（非「缺档」）。
6. **同号多件**：`266` 条同号多件中仅 `10` 条为**不同 sha16**；余为同件多副本，落库时钉一根即可。

（完 —— 本件末行 · LF 终 · 悬）
