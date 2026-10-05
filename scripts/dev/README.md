# scripts/dev —— 编器（provenance）

承 **PM 1189 §四⒜**：**编器之落点 ＝ `scripts/dev/`**（入库）· **通用与 recipes 分家**。

- **归**：技术总监（`f202f89`）
- **义**（共享器）：**众席可调 · 唯作者可改 · 改须先报 PM**（承 PM 1189 §四⒜）

## 一 分家

| 位 | 何物 |
|---|---|
| `safe_edit.py` | **通用之器**：`sub` ／ `lines` ／ `append` ／ 存底 ／ **读印** ／ `assert`。⛔ 含某批之字面。 |
| `recipes/edit_<批>_<题>.py` | **各批之字面**（按批编号）：只定 `EDITS` ／ `ORDER` ／ `BASES`，调 `safe_edit`。 |
| `tests/` | 器之验（反控：**写后回读** vs **算后即报**）。 |

## 二 硬律（落于此器）

1. **印须取自读 · ⛔ 取自算**（PM 1183 §二）＋ **同批之「改前」「改后」两印须同法**。
2. **存底粒度 ＝ 「改」· ⛔ 「件」**（一改一底 · PM 1178 §五）：底之名 ≡ 其值（**正形** ＝ 〈件名〉.before_〈改前印〉 · 承 PM 1292 §四 · 点前缀之旧形 .before_〈改前印〉.〈件名〉 ⛔ 再生 · ⛔ 删底）。
3. **`assert` 是冗余之闸 · ⛔ 代出处**（PM 1187 §二⒜）：所报之「改后」＝ **写后回读之值**（⛔ 内存算）。

## 三 何批之改 ⇒ 用何器之印

### 1055 批 · `recipes/edit_1055_源标与拒答与死件直读.py`（五改五底）

| 键 | 件 | 底（改前印） | 出（改后印） | 题 |
|---|---|---|---|---|
| A | `core/pa/gateway_routes.py` | `abe08578671ffbb5` | `ba41c213da539bb5` | 拒答之辞 ⇒ canonical ＋ 响应 `refusal_canon` |
| B | `core/pa/dialog.py` | `703f2b2796a62b1a` | `2e1989eff6a34db1` | 档行之源标（加性三键） |
| C | `core/pa/gateway_routes.py` | `ba41c213da539bb5` | `3c2f4a3a7e74524f` | 源标透传（`/ask` ／ `/turn` ／ `/dialog`） |
| C | `core/pa/pa_core.py` | `ea11b5233b4e5544` | `5dba11f023edb883` | 同上（`dialog_post` 路） |
| D | `core/pa/gateway_routes.py` | `3c2f4a3a7e74524f` | `1cf3948d22ee26df` | 死件账之直读路（`_ask_deadfile`） |
| E | `core/pa/gateway_routes.py` | `1cf3948d22ee26df` | `783012f8a1550279` | docstring 前缀 `u` ⇒ `r`（SyntaxWarning） |

### 1057 批 · `recipes/edit_1057_元问答话与死件路界与器病.py`（八改八底）

| 键 | 件 | 底（改前印） | 出（改后印） | 题 |
|---|---|---|---|---|
| F | `core/pa/dialog.py` | `2e1989eff6a34db1` | `c34b0ae7ddb1ef37` | 档行键 `src` ⇒ `origin`（一名一义） |
| G | `core/pa/pa_core.py` | `5dba11f023edb883` | `7cb7d13ed66ca4de` | 同（透传键） |
| H | `core/pa/gateway_routes.py` | `783012f8a1550279` | `78652e53e372724f` | 同（`pa_dialog` ＋ `pa_turn_record`） |
| I | `core/pa/gateway_routes.py` | `78652e53e372724f` | `5e720bd71630dd21` | `context_missing` 空答 ⇒ 人话句 |
| J | `08_工具/落台账_行.py` | `4f1a239ea0383d4b` | `b95b4004b4aa678e` | 面之快照「取数刻」被吞（器病 · 低） |
| K | `.gitignore` | `621b07950bacd199` | `b9e7c0771af9910f` | 准入存底两形（`*.before_*` ／ `.before_*`） |
| L | `core/pa/gateway_routes.py` | `5e720bd71630dd21` | `0f34ad396fa2ef6e` | 死件路：账不可读 ⇒ ⛔ 劫持全问 |
| M | `core/pa/gateway_routes.py` | `0f34ad396fa2ef6e` | `4f2b0a4e661157d0` | `PA_FACES_VERSION` .8 ⇒ .9 |

## 四 用法

```bash
python -X utf8 -B recipes/edit_1057_元问答话与死件路界与器病.py --verify   # ⭐ 由「底」回放 · 比对记录之「出」（⛔ 不碰活件）
python -X utf8 -B recipes/edit_1057_元问答话与死件路界与器病.py all        # 演（⛔ 不写盘）
python -X utf8 -B recipes/edit_1057_元问答话与死件路界与器病.py F --apply  # 真写（一改一底 · 写后回读）
python -X utf8 -B tests/test_safe_edit.py                                 # 反控（写后回读 vs 算后即报）
```

退出码：0 = 过 ／ 1 = 回放不合 ／ 用法错。

## 五 来源（scratch 之原本 · 移毕即删）

| 今 | 原（`_tmp\ts_scratch\p102\`） |
|---|---|
| `recipes/edit_1055_….py` | `p103_edit.py`（A–D）＋ `p103_fixE.py`（E） |
| `recipes/edit_1057_….py` | `p104_edit.py`（F–M） |
| `tests/test_safe_edit.py` | `p104_recheck.py` |

## 六 界

- ⛔ 本器 ⛔ 自动「起服」／⛔ 平台动作 ／⛔ 碰 `~/.codex` ／ `D:\codex-home`。
- ⛔ 借批之机扩面：一件一落行 · 一改一底。

## 七 器之自印（收者可核 · ⛔ 自评「已通过」）

| 器 | 印（sha256[:16]） | 字节 |
|---|---|---|
| `safe_edit.py` | `f7ade117a440a147` | 6,747 |
| `recipes/edit_1055_源标与拒答与死件直读.py` | `5ebf027001e8af2a` | 21,216 |
| `recipes/edit_1057_元问答话与死件路界与器病.py` | `544357ad96abe65a` | 8,220 |
| `tests/test_safe_edit.py` | `c2e51a483c01de8b` | 2,230 |

- ⚠ **本件（`README.md`）⛔ 自列**：自载己印 ＝ **自指之凭**（承「**载径 ⛔ 载值**」之族）⇒ 其印须在件外取（`Get-FileHash README.md`）。
- ⚠ **器之印随改**：改任一件 ⇒ 本表须**同批**更（承 PM 1190 §四：docstring 之改 ／ 印表之更 ／ 复跑回放 ／ commit ＝ **同批一次动印**）。
- ⭐ **回放**（改后必复跑）：`--verify` 须仍 `6/6` ＋ `8/8`；`tests/test_safe_edit.py` 须 `PASS`。
- ⚠ **⛔ 载批之内容**：「通用器 ⛔ 载批之内容」之义在**代码级**（`sub` ／ `lines` ／ `append` ／ 印 ／ `assert` 无批号）；**批号 ⛔ 入** `safe_edit.py`（含 docstring）—— 本 README 例外（其职即「批 ⇒ 器」之册）。
