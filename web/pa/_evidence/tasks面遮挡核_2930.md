# 证据 · `任务` 面「派件表单被覆」之核 · 承 PM `2930 §二`

> CW `b2a5182` · 刻 `2026-10-12 08:0x` · **唯只读** · 真浏览器 · 视口 `1280×800`（Paseo 内嵌 · ⛔ 1024／1440 —— 本条 ⛔ 涉宽度）

## 一 器与法

1. 器：本机活端 `http://127.0.0.1:5102/web/pa.html`（真 Chrome · headless）。
2. **可见交** ＝ 该件之 rect ∩（诸 `overflow != visible` 之祖 rect）∩ 视口 —— ⛔ 唯 rect（**rect 之投影 != 在屏**）。
3. 命中 ＝ `document.elementFromPoint(可见交之中心)`。

## 二 现态（`任务` 面 · `.twocol.scrollTop = 0` · 初始之貌）

| 件 | rect y | 可见交 h | `elementFromPoint` | 判 |
|---|---|---|---|---|
| `#paSubInput` | `861`-`889` | `0` | **`null`** | 在屏外 |
| `#paSubSend` | `861`-`889` | `0` | **`null`** | 在屏外 |
| `#paSeatSel` | `914`-`933` | `0` | **`null`** | 在屏外 |
| `#paSeatSend` | `911`-`934` | `0` | **`null`** | 在屏外 |
| `L2 · v9_gateway`（`summary`）| `730`-`747` | `0` | `#paChatNoHand.chatnohand` | 在屏外 |
| `L2 · dsh_wsl`（`summary`）| `758`-`775` | `0` | **`SPAN#paChatSysGo.chip`** | ← 即 PM 所见之「被覆」 |

裁之者 ＝ `.twocol`：`overflow: auto` ／ rect `y128`-`642` ／ `scrollHeight 884` ／ `clientHeight 514` ⇒ **`maxScroll = 370`**。

⚠ 故 `#paSubInput` 之 rect **投影**落于 composer 带（`#paChatSysGo` 之 rect）⇒ 「覆 `94`-`98%`」＝ **投影之数 · 非在屏之实**。

## 三 滚即达（`.twocol.scrollTop = 370` ＝ max）

| 件 | rect y | 可见交 h | `elementFromPoint` |
|---|---|---|---|
| `#paSubInput` | `491`-`519` | `28` | **`INPUT#paSubInput`（自身）** |
| `#paSubSend` | `491`-`519` | `28` | **`BUTTON#paSubSend`（自身）** |
| `L2 · v9_gateway` | `360`-`377` | `17` | **`SUMMARY`（自身）** |
| `L2 · dsh_wsl` | `388`-`405` | `17` | **`SUMMARY`（自身）** |
| `#paSeatSel` | `544`-`563` | `19` | `DIV`（＝「第一次用」固定盒）|
| `#paSeatSend` | `541`-`564` | `19` | `DIV`（同上）|

「第一次用」固定盒：`position:fixed; left:10px; right:10px; bottom:140px; z-index:9998` ⇒ rect `x10`-`1270` ／ `y531`-`660`（**全宽 · 129 高**）· 由 `GET /v9/pa/first_run` 驱动（`pa.html:591`-`604`）。

## 四 退盒后（真点「知道了」· 唯 `display:none` · ⛔ 写盘 ／ ⛔ 网 ／ ⛔ localStorage）

| 件 | `elementFromPoint` |
|---|---|
| `#paSeatSel` | **`SELECT#paSeatSel`（自身）** |
| `#paSeatSend` | **`BUTTON#paSeatSend`（自身）** |

⇒ 四件 ＋ 二 `summary` **皆可达** ⇒ **可避**（⛔ 恒蔽）。

## 五 判（承 `2928 §二.5` 之三族）

1. PM 之「被 `#paChatSysGo` 覆 `94`-`98%`」＝ **第三族（溢出滚动容器之件）之假阳** —— 其件被 `.twocol` 裁出视口 ⇒ rect 投影落于 composer 带。
2. PM 器今唯剔 ⒜折叠体 ⒝`checkVisibility` 为假者 —— **未剔本族**（`clipBy()` 已算而**仅报**，且 `cb` 反入 `bad`）。
3. **静定验**：同 scrollTop 二巡取同 · 两档宽之报皆同族（PM 一手）· ⛔ 涉宽度。

## 六 字号（同族另条 · 见回件 §二）

在屏之 SEL 件（`button, a, input, select, textarea, [role=button], summary, .chip, .btn, [onclick]`）中 `font < 12px` 者：

| 面 | < 12px 且在屏之数 |
|---|---|
| `今日上下文` | `0` |
| `会话` | `0` |
| `任务` | `7` ⇒ 落改后 **`0`** |

`任务` 面之 `7` 件：`.gates button` ×3（`改令` ／ `中止本线程` ／ `接管 · 待立项`）`11px` ｜ `#paSubInput` `11.5` ｜ `#paSubSend` `11.5` ｜ `#paSubPop`（`.pachbtn`）`10.5` ｜ `交付面`（`summary`）`11.5`。

## 七 限（照实）

1. 视口唯 `1280×800`（Paseo 内嵌浏览器之定尺）⇒ 宽度二档（`1024` ／ `1440`）**未取**；本条之现象与宽度无关（PM 一手之两档宽数 ≡）。
2. 「更多」抽屉面**未尝**（`details.msub>summary` `11px` 等）⇒ ⛔ 入本件之射程。

（完 —— 本件末行 · LF 终 · ⛔ 悬）
