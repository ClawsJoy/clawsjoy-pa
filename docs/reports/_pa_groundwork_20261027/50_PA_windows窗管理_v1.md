# PA 的 Windows 窗管理 v1（2026-10-27）

- 主：DSH（PA）｜问题：PA 自己的 Windows 窗怎么管；PA 怎么管别的窗（含本 DSH Web GUI）
- 一句：**PA 管 agent，不管像素；窗是 L1 最后手段。**

---

## 一 两层，别混

### A. PA 自己的窗（Electron 壳）

| 项 | 现状 |
|---|---|
| 主窗 | `1180 × 800`；最小 `900 × 600` |
| 托盘 | 有；关闭 = **隐藏**（非退出） |
| 单实例 | 有（second-instance 唤回） |
| 全局热键 | **无**（Phase 1 加） |

**Phase 1 加**：
1. `globalShortcut` `Ctrl+Shift+Space` ⇒ Summon（520×84，置顶，失焦收）；
2. 窗态保存（位置／大小／显示器）；
3. 托盘菜单：显示／隐藏／待批数／停；
4. **一主窗**，⛔ 多窗铺开；旧面收「更多」。

### B. PA 管别的窗（window adapter · L1）

**顺序不可倒**：

```
API / SDK  >  MCP / 本地服务  >  CLI  >  浏览器 CDP  >  UIA / 截图点击
```

⇒ 有 API 用 API；有 CLI 用 CLI；**最后**才用窗。窗最脆、最贵、最难审计。

---

## 二 本 DSH Web GUI：怎么管

| 路 | 法 | 判 |
|---|---|---|
| **首选** | `cli:dsh`（已 active）⇒ `dsh --profile headless "<task>"` | 一任务、打印、退出；⛔ 持久会话 |
| 次选 | DSH 本机 API / MCP | 若有，走 API；⛔ 点浏览器 |
| 最后 | Chromium CDP（若开 remote debugging）或 UIA | 高脆；只作人可见操作 |

⇒ **我现在这个窗，是给你看我的；PA 管我，不走窗。**

---

## 三 窗卡（window adapter）

| 键 | 值 |
|---|---|
| id | `win:<pid>:<hwnd>` |
| kind / class | `window` / 窗口 |
| name / process | 标题 / 进程名 |
| bounds / monitor | 矩形 / 显示器 / DPI |
| capabilities | `ui`（focus/move/click/type/screenshot） |
| boundary | 像素／UIA 依赖；elevated 不可；UAC 安全桌面不可 |
| fragility | **high** |
| cost | 每次截图／OCR／点击的时延 |
| invoke | `ui.focus` ／ `ui.click` ／ `ui.type` |
| probe | `window exists + title` |
| verified / approved | 未验 / 待批；⛔ 自动 active |

---

## 四 操作与护栏

| 操作 | 法 | 护栏 |
|---|---|---|
| 枚举 | Win32 `EnumWindows`；PID／标题／类／矩形 | 只列，⛔ 点 |
| 聚焦 | `SetForegroundWindow` | 先验 PID／标题；⛔ 抢焦点 |
| 移动／吸附 | `SetWindowPos`／Snap | 记前后矩形 |
| 读界面 | UIA 树 ＞ 截图＋OCR | UIA 优先；截图留证 |
| 点击／输入 | `SendInput`／UIA Invoke | L3 高风险：一次一码；前后截图 |
| 剪贴板 | 读写 | 敏感内容过分级；⛔ 入日志 |
| 停 | 全局 `Ctrl+.` | 1s；释放按键／鼠标 |

**硬护栏**：
1. 每次输入前**验目标**（PID ＋ 标题 ＋ 类）；
2. **UAC 安全桌面／elevated 窗** ⇒ ⛔ 自动，交人；
3. ⛔ 隐藏点击；每步前后截图 ＋ 回执；
4. 限速；⛔ 连点；
5. 窗卡 `fragility=high`，⛔ 当稳定接口。

---

## 五 Windows 特有事

- **DPI**：Per-Monitor V2；坐标换算；截图缩放；
- **多屏／虚拟桌面**：窗可能不在当前桌面；先切再点；
- **UAC／安全桌面**：不可注入；只能人操作；
- **焦点抢占**：Windows 限制 `SetForegroundWindow`；用 `AttachThreadInput` 或先最小化再恢复；
- **IME**：中文输入须切英文／用 UIA ValuePattern；
- **EDR／杀软**：`SendInput` 可能被拦；留痕；
- **Electron 窗**：优先 CDP（若开调试），比 UIA 稳；
- **Web GUI**：CDP／Playwright ＞ UIA 截图；

---

## 六 期

| 期 | 做 |
|---|---|
| Phase 1 | PA 自己窗：热键＋Summon＋窗态；**窗册只读**（枚举／列卡 pending） |
| Phase 2 | UIA 读 ＋ 聚焦／移动；点击须批；前后截图 |
| Phase 3 | 输入自动化＋CDP；L3 门；审计 |

⛔ Phase 1 不做输入自动化；先把「看得见、列得出、批得了」做实。

---

## 七 验收

1. 枚举 ≥10 窗；每窗一卡 pending；⛔ 自动 active；
2. `cli:dsh` active 优先于窗；窗只作 fallback；
3. 点前验 PID／标题；错 ⇒ 拒；
4. UAC／elevated ⇒ 拒，交人；
5. 每次点击前后截图 ＋ 账；
6. `Ctrl+.` 1s 停；
7. 窗卡 `fragility=high` 显式。

---

## 八 界

- ⛔ 隐藏点击；⛔ UAC 绕过；⛔ elevated 自动；⛔ 抢焦点；
- ⛔ 以窗充 API；⛔ 以截图充证据；
- 窗只是 L1；能用 CLI／API 就 ⛔ 用窗。

（完 —— 本件末行 · LF 终 · 悬）
