# Summon 可拖拽＋默认右下角 v1（2026-10-28）

- 主：DSH（PA · Lead）｜问题：缩小窗不可移动；默认位置？
- 判：**可拖拽已修；默认右下角（距工作区右/下各 16px）；位置可记忆。**

---

## 一 改动（仅 shell/main.js）

| 项 | 改 |
|---|---|
| 默认位 | `summonBounds()` 改为工作区右下：`x=wa.x+wa.w-520-16`，`y=wa.y+wa.h-84-16`（随光标所在屏） |
| 可拖 | 壳侧注入 `-webkit-app-region:drag` 到 `.pa-summon`；`input/textarea/button/.pa-chips/.pa-summon-foot` 设 `no-drag` |
| 记忆 | 拖动后存 `%LOCALAPPDATA%\ClawsJoyPA\summon_pos.json`（350ms 防抖）；下次按保存位开；越界夹回工作区 |
| 不改 | 520×84、Esc/失焦/热键 toggle、全局热键、托盘兜底、单实例 |

---

## 二 验证

- `node --check shell/main.js` ⇒ rc 0；
- 4 个 shell 测试件 ⇒ **20 passed**；
- 位置文件无档时 ⇒ 右下；有档时 ⇒ 记忆位（夹在工作区内）；
- 拖拽区域：卡片背景可拖，输入/按钮/芯片/底栏不拖。

---

## 三 界

- 本改动在当前 9.0.13 工作树；**未重打安装包**（9.0.13 仍因 P0-2 安装根写点停发）；
- 下一步 9.0.14：P0-2（data/engine.log 迁出装根）＋本改动一起重打；
- 位置文件用户可删以复位。

（完 —— 本件末行 · LF 终 · 悬）
