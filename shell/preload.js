'use strict';
/*
 * preload.js —— 壳之桥（**一处定形** · 承 pm_1657 §二.2 ／ pm_1885 §三.3 ／ pm_1890 §一 ／ pm_1896 §三）。
 *
 * 约（照 `openFeedbackDir` 之族）：**名** ／ **参** ／ **返** 之形唯在此处出（⛔ 二处各写）；
 *   ⛔ 出网：本档 ⛔ 引任何网络之能（唯本机 ipc）。
 *
 * ① `openFeedbackDir()` ⇒ `Promise<{ok:true,path}|{ok:false,code,message}>`（**参 ＝ 无** · 径由壳自算）。
 * ② `shellUpdateState()` ⇒ **收壳层更新之态**（幂等 · 只读 · ⛔ 副作用）—— ⭐ **态之唯一真源（拉）**（pm_1890 §一.2）。
 *    返：成 `{ok:true, phase, current, latest, progress}` ∨ 败 `{ok:false, phase, code, message}`
 *      （`phase` ∈ 八字 · `code` ∈ 七码 · `message` ＝ 人话 ＋ 去处 · ⛔ 行话上屏 · ⛔ 本机径 ／ ⛔ 端点）。
 * ③ `shellUpdateInstall()` ⇒ **触发「重启并安装」**（⭐ 唯由用户之点 ⇒ ⛔ 自动装 ／ ⛔ 偷重启 · pm_1885 §三.2）。
 * ④ `onShellUpdate(cb)` ⇒ 壳**唤面再拉**（⭐ **⛔ 传态** —— 免得「拉与推不一」而用户见二真相 · pm_1890 §一.2）；
 *    返**退订之器**（`function () {}` · 面之清理用）。
 * ⚠ 失败之面 ⛔ 静默：面必明书**因 ＋ 去处**（`message` 已载 ⇒ 面直接显示 · ⛔ 再拼）。
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('paShell', {
  openFeedbackDir: function () {
    return ipcRenderer.invoke('pa:open-feedback-dir');
  },
  shellUpdateState: function () {
    return ipcRenderer.invoke('pa:shell-update-state');
  },
  shellUpdateInstall: function () {
    return ipcRenderer.invoke('pa:shell-update-install');
  },
  onShellUpdate: function (cb) {
    if (typeof cb !== 'function') { return function () { }; }
    const h = function () { try { cb(); } catch (e) { /* 面之错 ⛔ 阻壳 */ } };
    ipcRenderer.on('pa:shell-update-ping', h);
    return function () { try { ipcRenderer.removeListener('pa:shell-update-ping', h); } catch (e) { } };
  }
});
