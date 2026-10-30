# 壳主进程 Object destroyed 修复 v1（2026-10-28 14:0x）

- 主：DSH（PA · Lead）｜现象：托盘/菜单点击 ⇒ `TypeError: Object has been destroyed at click`（main process）
- 判：**`win` 已销毁但仍被 `if (win)` 当真；已加 liveWin/showMain 守卫并热补当前 9.0.14。**

---

## 一 根因

- 主窗关闭/销毁后，全局 `win` 变量**仍非 null**；
- 托盘「显示/隐藏」「打开留言板」、双点、菜单「打开留言板」、退出保存窗态等路径只判 `if (win)` ⇒ 调 `win.show()/hide()/getNormalBounds()` ⇒ Object destroyed。

---

## 二 修（shell/main.js）

- 新增 `liveWin()`（`win && !win.isDestroyed()`）与 `showMain()`（无窗则重建，再 show/focus）；
- 托盘：显示／隐藏／打开留言板／双点全部走 liveWin/showMain；
- 菜单：打开留言板走 showMain；
- `reloadPage`／`saveWindowState`／`showLines` 弹窗／second-instance 全部加 destroyed 守卫；
- `node --check` rc0；4 shell tests **20 passed**。

---

## 三 当前安装热补

- 解 app.asar → 换入修后 main.js → 重 pack → 替换；旧 asar 备份：`app.asar.before_destroyfix_20261028`；
- 重启 9.0.14：进程起、主窗立、5102 起、页面载；无启动错误；
- 注意：这是**热补**，包哈希/安装器未变。

---

## 四 边界

- 9.0.14 安装包**不含**本修；9.0.15 统一出；
- 旧窗仍是当前主窗；新 v1 无密钥/设置；
- 9.0.14 不发布；P0-2 Program Files 未验。

（完 —— 本件末行 · LF 终 · 悬）
