# 任务面之遮挡 · 核与判（答 PM `2927 §三`）

件之由 ＝ PM `2927 §三`（新问一 · `任务` 面之遮挡）⇒ 核兼裁。刻 ＝ 2026-10-12 08:0x ｜ 面 ＝ 活端 `http://127.0.0.1:5102/web/pa.html` · 面签 `9.0.11` ｜ ⛔ 改一字（无缺陷 ⇒ ⛔ 动）

## 一 复跑（PM 之器 · 唯读 · 同器同数）

器 ＝ `python -X utf8 -B D:\paseo-workspace\_tools\pa用户巡_v1.py --faces --widths 1024,1440`

| 面 | 活元素 | 疑点 | 截断 | 相叠 | 横向溢出 | 静定 |
|---|---|---|---|---|---|---|
| 今日上下文 | 27 | 0 | 0 | 0 | 0 | ✓（2 取） |
| 会话 | 21 | 0 | 0 | 0 | 0 | ✓（2 取） |
| 任务 | 74 | **44**（1024）／ **43**（1440） | 0 | **12** | 0 | ✓（2 取） |
| 产品线 | 24 | 0 | 0 | 0 | 0 | ✓（2 取） |

⇒ ≡ PM 所报（`44`–`44` ／ `相叠 12` ／ 两档宽 ≡）✓

## 二 我一手之量（真浏览器 · `getBoundingClientRect` ＋ `elementFromPoint`）

1. **结构**：`#paFaceTasks`（`.facePane.on` · `overflow:hidden` · flex col）之子女 ＝ `DIV.twocol`（**`overflow:auto`** · `scrollHeight 884` ／ `clientHeight 514` ⇒ **maxScroll 370** ⇒ **可滚**）＋ `DETAILS#paT1Panel`（`open:false`）。
2. **被告之件皆在折叠之 `<details>` 内**：面内 `a`（文 ＝ `⧉`）＋ `summary` 共 **`25`** 件 ⇒ `closest('details:not([open])')` 判 ⇒ **`25/25` 有闭合之祖**（`.eng` 体 ／ `#paT1Panel` 体）⇒ 未展 ⇒ **不绘 · ⛔ 可点**（**设计如此**）。
3. **可避之证（判据）**：对上述 `25` 件 ⇒ 展开其祖 `<details>` ＋ `scrollIntoView({block:'center'})` ⇒ `elementFromPoint(中心)` 命中**自身** ⇒ **`25/25` SELF**（⚠ 「第一次用」之固定盒**仍在场**）⇒ ⭐ **皆可达**。
4. **「第一次用」之固定盒（覆之下带之主因）**：`position:fixed; left:10px; right:10px; z-index:9998` · 实 `bottom:140px`（＝ `innerHeight − composerTop + 8` · `pa.html:594` 之 `_place()`）⇒ 占 `y 531–660`（1280×800）｜其「**知道了**」钮 ⇒ `elementFromPoint` 命中**自身** ⇒ **可点 · 一按即除** ⇒ **可避**。
5. **可见而未被折叠所隐之件中，被覆者 ⇒ `0`**（剔「第一次用」盒后逐件判）。

## 三 判（答 §三 三问）

| 问 | 答 |
|---|---|
| ⒜ 可否经滚动 ∨ 展开而达 | **可 —— 三途**：① 展开其祖 `<details>`（其 `summary` 可见可点）② 滚 `.twocol`（`overflow:auto`）③ 按「知道了」退固定盒 |
| ⒝ 恒蔽 ∨ 可避 ＋ 由 | **可避**（⛔ 恒蔽）⇒ **⛔ 缺陷** ⇒ 其处**本就可点**（面侧 ⛔ 须改） |
| ⒞ 同器同数 | ✓（我复跑 ≡ 你数 · 见 §一） |

**由**：被点诸件皆属「**折叠之工程面**」（`.eng` 体 ／ `#paT1Panel` 体）—— 未展即不绘（设计）；盒之覆乃**首屏一次**之设计（`pa.html:581`–`584` 明书「⚠ 本盒 ⛔ 覆 `.composer`」∧ 锚于 composer **之上**）；二者皆可避。

## 四 供参（器之口径 · PM 域 · ⛔ 我动）

该器以 `elementFromPoint` 为金标 ⇒ 未剔三类节点 ⇒ 「不可点 ／ 相叠 ／ 被裁」之**假阳**：

1. **折叠 `<details>` 体之内件**（不绘 ⇒ 命中之背后件）
2. **溢出滚动容器之件**（几何在框外 · 滚即达）
3. **固定盒所覆之件**（可退）

建议之剔（hit 前）：`e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})` 为假 ⇒ 不计；∨ 径剔 `closest('details:not([open])')` 之下件（其 `summary` 除外）；∨ 先判「件之中心是否在其最近滚动祖之 `clientRect` 内」。

（完）
