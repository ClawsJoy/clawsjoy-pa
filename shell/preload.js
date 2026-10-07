'use strict';
/*
 * preload.js —— 壳之桥（**一处定形** · 承 pm_1657 §二.2 ／ CW `web/pa/faces/feedback.js` 之约）。
 *
 * 约：**名** ＝ `window.paShell.openFeedbackDir`｜**参** ＝ **无**（径由**壳**自算 ⇒ 桥 ⛔ 触他径）｜
 *     **返** ＝ `Promise<{ok:true,path}|{ok:false,code,message}>`｜失败之面 ⛔ 静默（面必明书因 ＋ 去处）。
 * ⛔ 出网：本档 ⛔ 引任何网络之能。
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('paShell', {
  openFeedbackDir: function () {
    return ipcRenderer.invoke('pa:open-feedback-dir');
  }
});